"""LangGraph nodes for AeroSpec agent workflow."""
from __future__ import annotations

from pathlib import Path

from core.llm_provider import provider
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
    mode = provider.mode
    try:
        if provider.available:
            mission = parse_mission(provider.normalize_mission(MISSION_INTERPRETER_PROMPT, user_input))
        else:
            mission = parse_mission(user_input)

        retrieval_query = {
            "targets": mission.targets,
            "goal": mission.mission_goal,
            "constraints": {
                "max_bands": mission.max_bands,
                "photon_flux": mission.photon_flux_condition,
                "range": [mission.wavelength_range_min_nm, mission.wavelength_range_max_nm],
            },
        }
        return {
            "mode": mode,
            "mission": mission.model_dump(),
            "retrieval_query": retrieval_query,
            "workflow_log": _log(
                state,
                f"[1/5] Mission Interpreter: extracted targets={mission.targets}, priority={mission.priority}, max_bands={mission.max_bands} ({mode}).",
            ),
        }
    except Exception as exc:
        mission = parse_mission(user_input)
        return {
            "mode": "Deterministic fallback mode",
            "mission": mission.model_dump(),
            "retrieval_query": {"targets": mission.targets, "goal": mission.mission_goal},
            "errors": _error(state, "mission_interpreter", str(exc)),
            "workflow_log": _log(
                state,
                f"[1/5] Mission Interpreter: fallback parsing used after provider error; targets={mission.targets}.",
            ),
        }


def knowledge_retriever_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    candidates = retrieve_candidate_regions(mission, RULES_PATH)
    target_count = len(mission.targets)

    if not candidates:
        return {
            "candidates": [],
            "errors": _error(state, "knowledge_retriever", "No candidate regions found in seed knowledge base."),
            "workflow_log": _log(state, "[2/5] Knowledge Retriever: retrieved 0 candidates; mission is underconstrained/unsupported by seed rules."),
        }

    total_merges = max((c.fusion_meta.get("global_dedup_merges", 0) for c in candidates), default=0)
    multi_target_candidates = sum(1 for c in candidates if len(c.target_tags) > 1)
    return {
        "candidates": [c.model_dump() for c in candidates],
        "workflow_log": _log(
            state,
            f"[2/5] Knowledge Retriever: retrieved {len(candidates)} candidates across {target_count} targets (multi-target candidates={multi_target_candidates}, dedup merges={total_merges}).",
        ),
    }


def constraint_and_ranking_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    candidates = [CandidateRegion(**c) for c in state.get("candidates", [])]
    scored = score_wavelength_candidates(mission, candidates)
    selected = enforce_band_budget(mission, scored)

    best_compact = sorted(scored, key=lambda s: s.components["compactness"], reverse=True)[: mission.max_bands]
    best_robust = sorted(scored, key=lambda s: s.components["robustness"], reverse=True)[: mission.max_bands]
    feasible_count = len([s for s in scored if s.raw_score >= 0.35])
    avg_photon = round(sum(s.components.get("photon_flux_suitability", 0.0) for s in selected) / len(selected), 3) if selected else 0.0

    return {
        "ranking_summary": {
            "candidate_count": len(candidates),
            "scored_count": len(scored),
            "selected_count": len(selected),
            "feasible_count": feasible_count,
        },
        "ranked": [s.model_dump() for s in scored],
        "selected": [s.model_dump() for s in selected],
        "alternatives": {
            "best_overall": [s.model_dump() for s in selected],
            "best_compact": [s.model_dump() for s in best_compact],
            "best_robust": [s.model_dump() for s in best_robust],
        },
        "workflow_log": _log(
            state,
            f"[3/5] Constraint + Ranking: applied budget={mission.max_bands}, photon={mission.photon_flux_condition}, priority={mission.priority}; selected {len(selected)} of {feasible_count} feasible candidates (avg photon suitability={avg_photon}).",
        ),
    }


def verification_node(state: AgentState) -> AgentState:
    mission = MissionInput(**state["mission"])
    selected_models = [ScoredCandidate(**x) for x in state.get("selected", [])]
    result = verify_recommendation(mission, selected_models)
    return {
        "verification": result.model_dump(),
        "workflow_log": _log(
            state,
            f"[4/5] Verification: status={result.status}, coverage={result.checks.get('target_coverage_ratio', 0):.2f}, confidence={result.confidence:.2f}, warnings={len(result.warnings)}.",
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
    verification = VerificationResult(**state.get("verification", {"status": "fail", "confidence_tier": "Exploratory", "confidence": 0.2, "warnings": ["No verification result"], "checks": {}, "target_coverage": {}}))
    report = generate_report(mission, bundle, verification, state.get("workflow_log", []), state.get("mode", "Deterministic fallback mode"))
    if state.get("errors"):
        report["errors"] = state["errors"]

    return {
        "report": report,
        "workflow_log": _log(state, "[5/5] Report Agent: produced executive brief, target coverage rationale, alternatives, and trust summary."),
    }
