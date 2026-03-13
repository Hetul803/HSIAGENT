"""Rule-based recommendation verification."""
from __future__ import annotations

from core.constants import DEFAULT_CONFIDENCE
from core.schemas import MissionInput, ScoredCandidate, VerificationResult
from core.utils import clamp, safe_div


def _tier(conf: float) -> str:
    if conf >= 0.8:
        return "High"
    if conf >= 0.6:
        return "Moderate"
    return "Exploratory"


def verify_recommendation(mission: MissionInput, selected: list[ScoredCandidate]) -> VerificationResult:
    warnings: list[str] = []
    if not selected:
        return VerificationResult(
            status="fail",
            confidence_tier="Exploratory",
            confidence=0.2,
            warnings=["No feasible bands selected after constraints."],
            checks={"count": 0, "target_coverage_ratio": 0.0},
            target_coverage={t: 0 for t in mission.targets},
        )

    coverage = {t: 0 for t in mission.targets}
    for band in selected:
        for t in mission.targets:
            if t in band.target_tags:
                coverage[t] += 1

    covered_targets = sum(1 for x in coverage.values() if x > 0)
    coverage_ratio = safe_div(covered_targets, len(mission.targets))
    avg_photon = safe_div(sum(c.components.get("photon_flux_suitability", 0.0) for c in selected), len(selected))
    avg_score = safe_div(sum(c.raw_score for c in selected), len(selected))

    if coverage_ratio < 1.0:
        missing = [t for t, c in coverage.items() if c == 0]
        warnings.append(f"Not all requested targets are covered. Missing: {missing}.")
    if len(mission.targets) >= 3 and mission.max_bands <= len(mission.targets):
        warnings.append("Tight band budget for multi-target mission; compromise plan expected.")
    if mission.photon_flux_condition == "low" and mission.priority == "accuracy":
        warnings.append("Low photon flux and accuracy priority may conflict in operational conditions.")
    if len(selected) >= 2 and all(abs(((s.wavelength_min_nm + s.wavelength_max_nm) / 2) - ((selected[0].wavelength_min_nm + selected[0].wavelength_max_nm) / 2)) < 120 for s in selected[1:]):
        warnings.append("Selected set is spectrally narrow; consider adding contextual spread.")

    confidence = clamp(DEFAULT_CONFIDENCE * 0.3 + avg_score * 0.35 + coverage_ratio * 0.25 + avg_photon * 0.1 - 0.08 * len(warnings))
    status = "pass" if len(warnings) == 0 else ("caution" if len(warnings) <= 2 else "fail")

    return VerificationResult(
        status=status,
        confidence_tier=_tier(confidence),
        confidence=confidence,
        warnings=warnings,
        checks={
            "count": len(selected),
            "target_coverage_ratio": coverage_ratio,
            "avg_photon_suitability": avg_photon,
            "avg_raw_score": avg_score,
            "priority": mission.priority,
        },
        target_coverage=coverage,
    )
