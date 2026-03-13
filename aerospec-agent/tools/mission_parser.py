"""Mission parsing tool."""
from __future__ import annotations

import re
from typing import Any

from core.schemas import MissionInput


TARGET_HINTS = {
    "cloud": r"cirrus|cloud|icing",
    "water": r"water|runway flooding|flood|puddle",
    "moisture": r"moisture|humidity|wet|water vapor",
    "vegetation": r"vegetation|crop|plant|stress",
}


def parse_mission(raw: dict[str, Any]) -> MissionInput:
    """Parse and normalize mission input into a typed schema."""
    goal = str(raw.get("mission_goal", "")).strip()
    if not goal:
        raise ValueError("mission_goal is required.")

    inferred_target = raw.get("target_type", "custom")
    if inferred_target not in {"cloud", "water", "moisture", "vegetation", "custom"}:
        inferred_target = "custom"

    low_goal = goal.lower()
    if inferred_target == "custom":
        for target, pattern in TARGET_HINTS.items():
            if re.search(pattern, low_goal):
                inferred_target = target
                break

    return MissionInput(
        mission_goal=goal,
        target_type=inferred_target,
        platform_type=raw.get("platform_type", "airborne"),
        max_bands=int(raw.get("max_bands", 6)),
        photon_flux_condition=raw.get("photon_flux_condition", "medium"),
        priority=raw.get("priority", "accuracy"),
        wavelength_range_min_nm=raw.get("wavelength_range_min_nm"),
        wavelength_range_max_nm=raw.get("wavelength_range_max_nm"),
        notes=str(raw.get("notes", "")),
    )
