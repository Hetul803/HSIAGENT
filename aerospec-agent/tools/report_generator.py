"""Final report generator."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core.schemas import MissionInput, RecommendationBundle, VerificationResult


def _trust_tier(confidence: float) -> str:
    if confidence >= 0.8:
        return "High"
    if confidence >= 0.6:
        return "Moderate"
    return "Exploratory"


def generate_report(
    mission: MissionInput,
    bundle: RecommendationBundle,
    verification: VerificationResult,
    workflow_log: list[str],
) -> dict[str, Any]:
    def _pack(items):
        return [
            {
                "id": i.id,
                "range_nm": [i.wavelength_min_nm, i.wavelength_max_nm],
                "score": round(i.raw_score, 3),
                "normalized_score": round(i.normalized_score, 3),
                "rationale": i.rationale,
                "retrieval_reason": i.retrieval_reason,
                "caution": i.caution,
                "reference": i.reference,
                "components": {k: round(v, 3) for k, v in i.components.items()},
            }
            for i in items
        ]

    assumptions = [
        "This uses seed demo spectral rules and is not exhaustive remote-sensing science.",
        "Instrument SRF, atmospheric correction, and scene BRDF should be validated before flight ops.",
        "Recommendations are mission-design decision support, not autonomous mission authorization.",
    ]

    trust_tier = _trust_tier(verification.confidence)
    primary_count = len(bundle.best_overall)
    caution_phrase = "with no critical rule conflicts detected" if verification.passed else "with verification warnings requiring analyst review"

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "mission_summary": mission.model_dump(),
        "recommendations": {
            "best_overall": _pack(bundle.best_overall),
            "best_compact": _pack(bundle.best_compact),
            "best_robust": _pack(bundle.best_robust),
        },
        "verification": verification.model_dump(),
        "confidence": verification.confidence,
        "confidence_tier": trust_tier,
        "warnings": verification.warnings,
        "assumptions": assumptions,
        "workflow_steps": workflow_log,
        "executive_summary": (
            f"AeroSpec Agent recommends {primary_count} primary spectral regions for {mission.target_type} sensing "
            f"on a {mission.platform_type} platform under {mission.photon_flux_condition} photon conditions, {caution_phrase}. "
            f"Confidence tier: {trust_tier} ({verification.confidence:.2f})."
        ),
    }
