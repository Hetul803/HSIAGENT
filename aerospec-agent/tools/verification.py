"""Rule-based recommendation verification."""
from __future__ import annotations

from core.constants import DEFAULT_CONFIDENCE
from core.schemas import MissionInput, ScoredCandidate, VerificationResult
from core.utils import clamp, safe_div


def verify_recommendation(mission: MissionInput, selected: list[ScoredCandidate]) -> VerificationResult:
    warnings: list[str] = []
    if not selected:
        return VerificationResult(
            passed=False,
            confidence=0.2,
            warnings=["No feasible bands selected after constraints."],
            checks={"count": 0, "target_alignment": 0.0, "provenance_coverage": 0.0},
        )

    target_hits = sum(1 for c in selected if mission.target_type in c.id)
    alignment = safe_div(target_hits, len(selected))
    provenance_coverage = safe_div(sum(1 for c in selected if c.reference.startswith("SeedDemo-")), len(selected))
    avg_photon = safe_div(sum(c.components.get("photon_flux_suitability", 0.0) for c in selected), len(selected))
    avg_conf = safe_div(sum(c.components.get("knowledge_confidence", 0.0) for c in selected), len(selected))

    if len(selected) > mission.max_bands:
        warnings.append("Band budget exceeded after selection.")
    if mission.photon_flux_condition == "low" and avg_photon < 0.72:
        warnings.append("Low photon scenario but selected set has low photon suitability.")
    if alignment < 0.35:
        warnings.append("Low direct target alignment in selected bands.")
    if provenance_coverage < 0.8:
        warnings.append("Some selected bands are missing trusted seed-reference provenance.")
    if avg_conf < 0.6:
        warnings.append("Knowledge confidence is modest; treat plan as exploratory.")

    mean_score = safe_div(sum(c.raw_score for c in selected), len(selected))
    confidence = clamp(DEFAULT_CONFIDENCE * 0.35 + mean_score * 0.35 + avg_conf * 0.3 - 0.07 * len(warnings))

    return VerificationResult(
        passed=len(warnings) <= 2,
        confidence=confidence,
        warnings=warnings,
        checks={
            "count": len(selected),
            "target_alignment": alignment,
            "provenance_coverage": provenance_coverage,
            "mean_raw_score": mean_score,
            "avg_photon_suitability": avg_photon,
            "avg_knowledge_confidence": avg_conf,
        },
    )
