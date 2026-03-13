"""Mission parsing tool."""
from __future__ import annotations

import re
from typing import Any

from core.schemas import MissionInput

TARGET_HINTS = {
    "cloud": r"cirrus|cloud|icing|overcast",
    "water": r"water|runway flooding|flood|puddle|standing water",
    "moisture": r"moisture|humidity|wet|water vapor",
    "vegetation": r"vegetation|crop|plant|stress|red-edge",
}


def parse_mission(raw: dict[str, Any]) -> MissionInput:
    goal = str(raw.get("mission_goal", "")).strip()
    if not goal:
        raise ValueError("mission_goal is required.")

    explicit_targets = raw.get("targets") or []
    valid_targets = {"cloud", "water", "moisture", "vegetation", "custom"}
    targets = [t for t in explicit_targets if t in valid_targets]

    low_goal = goal.lower()
    inferred = [t for t, pattern in TARGET_HINTS.items() if re.search(pattern, low_goal)]
    merged = list(dict.fromkeys(targets + inferred))
    if not merged:
        merged = ["custom"]

    return MissionInput(
        mission_goal=goal,
        targets=merged,
        platform_type=raw.get("platform_type", "airborne"),
        max_bands=int(raw.get("max_bands", 6)),
        photon_flux_condition=raw.get("photon_flux_condition", "medium"),
        priority=raw.get("priority", "accuracy"),
        wavelength_range_min_nm=raw.get("wavelength_range_min_nm"),
        wavelength_range_max_nm=raw.get("wavelength_range_max_nm"),
        notes=str(raw.get("notes", "")),
    )
