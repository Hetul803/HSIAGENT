"""Deterministic wavelength scoring and ranking."""
from __future__ import annotations

from core.constants import PRIORITY_WEIGHTS, SCORING_WEIGHTS
from core.schemas import CandidateRegion, MissionInput, ScoredCandidate
from core.utils import clamp
from tools.photon_flux_estimator import estimate_photon_flux_penalty


def _compactness_score(width_nm: float) -> float:
    return clamp(1.0 - (width_nm / 500.0), 0.2, 1.0)


def _range_conflict_penalty(mission: MissionInput, c: CandidateRegion) -> float:
    penalty = 0.0
    if mission.wavelength_range_min_nm and c.wavelength_min_nm < mission.wavelength_range_min_nm:
        penalty += 0.1
    if mission.wavelength_range_max_nm and c.wavelength_max_nm > mission.wavelength_range_max_nm:
        penalty += 0.1
    if mission.photon_flux_condition == "low" and c.wavelength_min_nm > 1500:
        penalty += 0.08
    return penalty


def score_wavelength_candidates(mission: MissionInput, candidates: list[CandidateRegion]) -> list[ScoredCandidate]:
    scored: list[ScoredCandidate] = []
    for c in candidates:
        width = c.wavelength_max_nm - c.wavelength_min_nm
        mission_relevance = clamp(1.0 if c.target == mission.target_type else 0.64)
        photon_flux_suitability = 1.0 - estimate_photon_flux_penalty(
            c.wavelength_min_nm,
            c.wavelength_max_nm,
            mission.photon_flux_condition,
        )
        compactness = _compactness_score(width)
        components = {
            "mission_relevance": mission_relevance,
            "photon_flux_suitability": photon_flux_suitability,
            "interpretability": c.interpretability,
            "compactness": compactness,
            "robustness": c.robustness,
            "knowledge_confidence": clamp((c.confidence + c.evidence_score) / 2),
        }

        base_score = sum(components[n] * SCORING_WEIGHTS[n] for n in SCORING_WEIGHTS)
        priority_map = PRIORITY_WEIGHTS[mission.priority]
        priority_score = sum(components.get(k, 0.0) * v for k, v in priority_map.items())
        penalty = _range_conflict_penalty(mission, c)
        raw_score = clamp(base_score * 0.8 + priority_score * 0.2 - penalty, 0.0, 1.0)

        scored.append(
            ScoredCandidate(
                id=c.id,
                label=f"{c.id} ({c.wavelength_min_nm:.0f}-{c.wavelength_max_nm:.0f} nm)",
                wavelength_min_nm=c.wavelength_min_nm,
                wavelength_max_nm=c.wavelength_max_nm,
                raw_score=raw_score,
                normalized_score=0.0,
                components=components,
                rationale=c.rationale,
                caution=c.caution,
                reference=c.reference,
                retrieval_reason=c.retrieval_reason,
            )
        )

    if not scored:
        return []

    max_raw, min_raw = max(s.raw_score for s in scored), min(s.raw_score for s in scored)
    denom = max(max_raw - min_raw, 1e-6)
    for s in scored:
        s.normalized_score = clamp((s.raw_score - min_raw) / denom)

    return sorted(scored, key=lambda x: (x.raw_score, x.components["knowledge_confidence"]), reverse=True)
