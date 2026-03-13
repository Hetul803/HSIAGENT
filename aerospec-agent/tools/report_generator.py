"""Final report generator."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from core.schemas import MissionInput, RecommendationBundle, VerificationResult


def _target_rationale(mission: MissionInput, recommendations: list[dict[str, Any]]) -> dict[str, list[str]]:
    out = {t: [] for t in mission.targets}
    for rec in recommendations:
        for t in mission.targets:
            if t in rec["target_tags"]:
                out[t].append(f"{rec['id']} ({rec['range_nm'][0]}-{rec['range_nm'][1]} nm)")
    return out


def generate_report(
    mission: MissionInput,
    bundle: RecommendationBundle,
    verification: VerificationResult,
    workflow_log: list[str],
    mode_label: str,
) -> dict[str, Any]:
    def _pack(items):
        return [
            {
                "id": i.id,
                "range_nm": [i.wavelength_min_nm, i.wavelength_max_nm],
                "target_tags": i.target_tags,
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

    best_overall = _pack(bundle.best_overall)
    target_map = _target_rationale(mission, best_overall)
    assumptions = [
        "Seed demo spectral rules are not scientifically exhaustive and should be expanded.",
        "Band recommendations are mission-planning support, not autonomous flight authorization.",
        "Final deployment requires sensor calibration and atmospheric validation.",
    ]

    return {
        "timestamp": datetime.utcnow().isoformat(),
        "mode": mode_label,
        "mission_summary": mission.model_dump(),
        "inferred_targets": mission.targets,
        "recommendations": {
            "best_overall": best_overall,
            "best_compact": _pack(bundle.best_compact),
            "best_robust": _pack(bundle.best_robust),
        },
        "target_coverage_rationale": target_map,
        "verification": verification.model_dump(),
        "confidence": verification.confidence,
        "confidence_tier": verification.confidence_tier,
        "warnings": verification.warnings,
        "assumptions": assumptions,
        "workflow_steps": workflow_log,
        "executive_summary": (
            f"{mode_label}: Designed a {len(best_overall)}-band constrained plan for targets={mission.targets} "
            f"under photon_flux={mission.photon_flux_condition} and priority={mission.priority}. "
            f"Verification status={verification.status}, confidence={verification.confidence:.2f} ({verification.confidence_tier})."
        ),
    }
