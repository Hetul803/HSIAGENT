"""Constraint and optimization tool for budget and feasibility checks."""
from __future__ import annotations

from core.schemas import MissionInput, ScoredCandidate
from core.utils import clamp


def _overlap_ratio(a: ScoredCandidate, b: ScoredCandidate) -> float:
    lo = max(a.wavelength_min_nm, b.wavelength_min_nm)
    hi = min(a.wavelength_max_nm, b.wavelength_max_nm)
    if hi <= lo:
        return 0.0
    width = max(a.wavelength_max_nm - a.wavelength_min_nm, b.wavelength_max_nm - b.wavelength_min_nm, 1.0)
    return (hi - lo) / width


def _priority_adjustment(mission: MissionInput, c: ScoredCandidate) -> float:
    if mission.priority == "compactness":
        return 0.08 * c.components.get("compactness", 0.0)
    if mission.priority == "robustness":
        return 0.08 * c.components.get("robustness", 0.0)
    if mission.priority == "interpretability":
        return 0.08 * c.components.get("reference_context_bonus", 0.0)
    return 0.08 * c.components.get("target_coverage", 0.0)


def _marginal_gain(c: ScoredCandidate, selected: list[ScoredCandidate], uncovered_targets: set[str], mission: MissionInput) -> float:
    coverage_gain = 0.27 * len(uncovered_targets.intersection(c.target_tags))
    redundancy_penalty = sum(_overlap_ratio(c, s) * 0.22 for s in selected)
    repeated_target_penalty = 0.05 * len(set(c.target_tags).intersection({t for s in selected for t in s.target_tags}))
    return c.raw_score + coverage_gain + _priority_adjustment(mission, c) - redundancy_penalty - repeated_target_penalty


def enforce_band_budget(mission: MissionInput, ranked: list[ScoredCandidate]) -> list[ScoredCandidate]:
    """Greedy constrained optimizer to build a multi-target band plan under budget."""
    feasible = [r for r in ranked if r.raw_score >= 0.35]
    selected: list[ScoredCandidate] = []
    uncovered_targets = set(mission.targets)

    while feasible and len(selected) < mission.max_bands:
        best = max(feasible, key=lambda c: _marginal_gain(c, selected, uncovered_targets, mission))
        feasible.remove(best)

        if any(_overlap_ratio(best, s) > 0.85 for s in selected):
            continue

        selected.append(best)
        uncovered_targets -= set(best.target_tags)

    if not selected:
        selected = ranked[: mission.max_bands]

    for idx, cand in enumerate(selected):
        cand.components["diminishing_returns_penalty"] = round(clamp(idx * 0.06, 0, 0.35), 3)
        cand.components["selection_order"] = float(idx + 1)
        cand.components["budget_utilization"] = round((idx + 1) / mission.max_bands, 3)

    return selected
