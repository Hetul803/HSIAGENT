"""Constraint tool for budget and feasibility checks."""
from __future__ import annotations

from core.schemas import MissionInput, ScoredCandidate


def _overlap(a: ScoredCandidate, b: ScoredCandidate) -> float:
    lo = max(a.wavelength_min_nm, b.wavelength_min_nm)
    hi = min(a.wavelength_max_nm, b.wavelength_max_nm)
    if hi <= lo:
        return 0.0
    return (hi - lo) / max((a.wavelength_max_nm - a.wavelength_min_nm), 1.0)


def enforce_band_budget(mission: MissionInput, ranked: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Enforce max bands and reduce redundancy while preserving score quality."""
    feasible = [r for r in ranked if r.raw_score >= 0.42]
    selected: list[ScoredCandidate] = []
    for cand in feasible:
        if len(selected) >= mission.max_bands:
            break
        if any(_overlap(cand, s) > 0.7 for s in selected):
            continue
        selected.append(cand)

    if not selected:
        return feasible[: mission.max_bands]
    return selected
