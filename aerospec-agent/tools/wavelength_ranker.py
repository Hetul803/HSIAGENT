"""Deterministic wavelength scoring and ranking."""
from __future__ import annotations

from core.constants import PRIORITY_WEIGHTS, SCORING_WEIGHTS
from core.schemas import CandidateRegion, MissionInput, ScoredCandidate
from core.utils import clamp
from tools.photon_flux_estimator import estimate_photon_flux_penalty


def _compactness_score(width_nm: float) -> float:
    return clamp(1.0 - width_nm / 500.0, 0.2, 1.0)


def _coverage_score(mission: MissionInput, c: CandidateRegion) -> float:
    overlap = len(set(mission.targets).intersection(c.target_tags))
    return clamp(overlap / max(len(mission.targets), 1))


def _reference_bonus(c: CandidateRegion) -> float:
    return 0.9 if c.context_band else 0.45


def _overlap_bonus(c: CandidateRegion) -> float:
    return clamp(len(c.target_tags) / 3.0)


def score_wavelength_candidates(mission: MissionInput, candidates: list[CandidateRegion]) -> list[ScoredCandidate]:
    scored: list[ScoredCandidate] = []
    for c in candidates:
        width = c.wavelength_max_nm - c.wavelength_min_nm
        photon_flux_suitability = 1.0 - estimate_photon_flux_penalty(c.wavelength_min_nm, c.wavelength_max_nm, mission.photon_flux_condition)

        components = {
            "target_coverage": _coverage_score(mission, c),
            "photon_flux_suitability": photon_flux_suitability,
            "interpretability": c.interpretability,
            "compactness": _compactness_score(width),
            "robustness": c.robustness,
            "knowledge_confidence": clamp((c.confidence + c.evidence_score) / 2),
            "reference_context_bonus": _reference_bonus(c),
            "overlap_bonus": _overlap_bonus(c),
        }

        base_score = sum(components[n] * SCORING_WEIGHTS[n] for n in SCORING_WEIGHTS)
        priority_weights = PRIORITY_WEIGHTS[mission.priority]
        priority_score = sum(components.get(k, 0.0) * w for k, w in priority_weights.items())
        raw_score = clamp(base_score * 0.8 + priority_score * 0.2)

        scored.append(
            ScoredCandidate(
                id=c.id,
                label=f"{c.id} ({c.wavelength_min_nm:.0f}-{c.wavelength_max_nm:.0f} nm)",
                wavelength_min_nm=c.wavelength_min_nm,
                wavelength_max_nm=c.wavelength_max_nm,
                target_tags=c.target_tags,
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

    return sorted(scored, key=lambda x: x.raw_score, reverse=True)
