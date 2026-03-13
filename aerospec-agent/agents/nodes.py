"""LangGraph nodes for AeroSpec agent workflow."""
from __future__ import annotations

import json
from pathlib import Path

from langchain_openai import ChatOpenAI

from config import settings
from core.schemas import CandidateRegion, MissionInput, RecommendationBundle, ScoredCandidate, VerificationResult
from tools.constraint_checker import enforce_band_budget
from tools.knowledge_retriever import retrieve_candidate_regions
from tools.mission_parser import parse_mission
from tools.report_generator import generate_report
from tools.verification import verify_recommendation
from tools.wavelength_ranker import score_wavelength_candidates

from .prompts import MISSION_INTERPRETER_PROMPT
from .state import AgentState

RULES_PATH = Path(__file__).resolve().parent.parent / "data" / "spectral_rules.json"


def _log(state: AgentState, line: str) -> list[str]:
    logs = list(state.get("workflow_log", []))
    logs.append(line)
    return logs


def _error(state: AgentState, stage: str, message: str) -> list[dict[str, str]]:
    errors = list(state.get("errors", []))
    errors.append({"stage": stage, "message": message})
    return errors


def mission_interpreter_node(state: AgentState) -> AgentState:
    user_input = state["user_input"]
    try:
        if settings.openai_api_key:
            llm = ChatOpenAI(model=settings.openai_model, temperature=0.0, api_key=settings.openai_api_key)
            prompt = f"{MISSION_INTERPRETER_PROMPT}\nInput:\n{json.dumps(user_input)}"
            response = llm.invoke(prompt)
            mission = parse_mission(json.loads(response.content))
            log_line = "[1/5] Mission Interpreter: normalized user mission fields via constrained LLM schema mode."
        else:
            mission = parse_mission(user_input)
            log_line = "[1/5] Mission Interpreter: normalized mission deterministically (no API key set)."

        retrieval_query = {
            "target_type": mission.target_type,
            "mission_goal": mission.mission_goal,
            "constraints": {
                "max_bands": mission.max_bands,
                "photon_flux_condition": mission.photon_flux_condition,
                "range": [mission.wavelength_range_min_nm, mission.wavelength_range_max_nm],
            },
        }
        return {
            "mission": mission.model_dump(),
            "retrieval_query": retrieval_query,
            "workflow_log": _log(state, log_line),
        }
    except Exception as exc:
        mission = parse_mission(user_input)
        return {
            "mission": mission.model_dump(),
            "retrieval_query": {"target_type": mission.target_type, "mission_goal": mission.mission_goal},
            "errors": _error(state, "mission_interpreter", str(exc)),
            "workflow_log": _log(state, "[1/5] Mission Interpreter: recovered with deterministic parser after LLM/schema error."),
        }


def knowledge_retriever_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    candidates = retrieve_candidate_regions(mission, RULES_PATH)
    if not candidates:
        return {
            "candidates": [],
            "errors": _error(state, "knowledge_retriever", "No candidate regions found in seed knowledge base."),
            "workflow_log": _log(state, "[2/5] Knowledge Retriever: no matched seed rules; downstream stages will report low confidence."),
        }

    top_evidence = max(c.evidence_score for c in candidates)
    return {
        "candidates": [c.model_dump() for c in candidates],
        "workflow_log": _log(
            state,
            f"[2/5] Knowledge Retriever: selected {len(candidates)} candidate regions from local rules (top evidence={top_evidence:.2f}).",
        ),
    }


def constraint_and_ranking_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    candidates = [CandidateRegion(**c) for c in state.get("candidates", [])]
    scored = score_wavelength_candidates(mission, candidates)
    selected = enforce_band_budget(mission, scored)

    best_compact = sorted(scored, key=lambda s: s.components["compactness"], reverse=True)[: mission.max_bands]
    best_robust = sorted(scored, key=lambda s: s.components["robustness"], reverse=True)[: mission.max_bands]
    summary = {
        "candidate_count": len(candidates),
        "scored_count": len(scored),
        "selected_count": len(selected),
        "average_score": round(sum(x.raw_score for x in selected) / len(selected), 3) if selected else 0.0,
    }

    return {
        "ranking_summary": summary,
        "ranked": [s.model_dump() for s in scored],
        "selected": [s.model_dump() for s in selected],
        "alternatives": {
            "best_overall": [s.model_dump() for s in selected],
            "best_compact": [s.model_dump() for s in best_compact],
            "best_robust": [s.model_dump() for s in best_robust],
        },
        "workflow_log": _log(
            state,
            f"[3/5] Constraint + Ranking: scored {len(scored)} candidates and retained {len(selected)} within band budget={mission.max_bands}.",
        ),
    }


def verification_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    selected_models = [ScoredCandidate(**x) for x in state.get("selected", [])]
    result = verify_recommendation(mission, selected_models)
    status = "PASS" if result.passed else "ATTENTION"
    return {
        "verification": result.model_dump(),
        "workflow_log": _log(
            state,
            f"[4/5] Verification: {status}, confidence={result.confidence:.2f}, warnings={len(result.warnings)}.",
        ),
    }


def report_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    alternatives = state.get("alternatives", {"best_overall": [], "best_compact": [], "best_robust": []})

    bundle = RecommendationBundle(
        best_overall=[ScoredCandidate(**x) for x in alternatives.get("best_overall", [])],
        best_compact=[ScoredCandidate(**x) for x in alternatives.get("best_compact", [])],
        best_robust=[ScoredCandidate(**x) for x in alternatives.get("best_robust", [])],
    )
    verification = VerificationResult(**state.get("verification", {"passed": False, "confidence": 0.2, "warnings": ["No verification result"], "checks": {}}))
    report = generate_report(mission, bundle, verification, state.get("workflow_log", []))
    if state.get("errors"):
        report["errors"] = state["errors"]

    return {
        "report": report,
        "workflow_log": _log(state, "[5/5] Report Agent: generated executive summary, alternatives, trust notes, and artifacts."),
    }
