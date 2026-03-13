"""Knowledge retrieval tool from local spectral rule base."""
from __future__ import annotations

from pathlib import Path

from core.schemas import CandidateRegion, MissionInput
from core.utils import clamp, load_json


def _keyword_match_score(mission: MissionInput, keywords: list[str]) -> float:
    text = f"{mission.mission_goal.lower()} {mission.target_type} {mission.notes.lower()}"
    hits = sum(1 for k in keywords if k.lower() in text)
    return clamp(hits / max(len(keywords), 1))


def retrieve_candidate_regions(mission: MissionInput, rules_path: Path) -> list[CandidateRegion]:
    """Retrieve and score candidate regions from local trusted seed knowledge."""
    rules = load_json(rules_path)
    candidates: list[CandidateRegion] = []

    for item in rules:
        keywords = item.get("keywords", [])
        key_score = _keyword_match_score(mission, keywords)
        target_match = 1.0 if item["target"] == mission.target_type else (0.55 if item["target"] == "custom" else 0.0)
        evidence_score = clamp(0.6 * target_match + 0.4 * key_score)
        if evidence_score < 0.35:
            continue

        c = CandidateRegion(
            **{k: v for k, v in item.items() if k != "keywords"},
            evidence_score=evidence_score,
            retrieval_reason=(
                f"target_match={target_match:.2f}, keyword_match={key_score:.2f}; "
                f"selected from seed rule base"
            ),
        )

        if mission.wavelength_range_min_nm and c.wavelength_max_nm < mission.wavelength_range_min_nm:
            continue
        if mission.wavelength_range_max_nm and c.wavelength_min_nm > mission.wavelength_range_max_nm:
            continue

        candidates.append(c)

    return sorted(candidates, key=lambda x: x.evidence_score, reverse=True)
