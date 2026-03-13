"""Knowledge retrieval tool from local spectral rule base."""
from __future__ import annotations

from pathlib import Path

from core.schemas import CandidateRegion, MissionInput
from core.utils import clamp, load_json


def _keyword_match_score(mission: MissionInput, keywords: list[str]) -> float:
    text = f"{mission.mission_goal.lower()} {' '.join(mission.targets)} {mission.notes.lower()}"
    hits = sum(1 for k in keywords if k.lower() in text)
    return clamp(hits / max(len(keywords), 1))


def _target_match_score(mission_targets: list[str], candidate_tags: list[str]) -> float:
    overlap = len(set(mission_targets).intersection(candidate_tags))
    if overlap == 0 and "custom" in candidate_tags:
        return 0.4
    return clamp(overlap / max(len(set(mission_targets)), 1))


def _dedupe_candidates(candidates: list[CandidateRegion]) -> tuple[list[CandidateRegion], int]:
    merged: dict[tuple[int, int], CandidateRegion] = {}
    merges = 0
    for c in candidates:
        key = (int(c.wavelength_min_nm // 10), int(c.wavelength_max_nm // 10))
        if key not in merged:
            c.fusion_meta = {"merged_ids": [c.id], "merge_count": 0}
            merged[key] = c
            continue

        merges += 1
        existing = merged[key]
        existing.target_tags = sorted(set(existing.target_tags + c.target_tags))
        existing.evidence_score = max(existing.evidence_score, c.evidence_score)
        existing.retrieval_reason = f"{existing.retrieval_reason}; merged={c.id}"
        existing.fusion_meta["merged_ids"].append(c.id)
        existing.fusion_meta["merge_count"] = len(existing.fusion_meta["merged_ids"]) - 1
    return list(merged.values()), merges


def retrieve_candidate_regions(mission: MissionInput, rules_path: Path) -> list[CandidateRegion]:
    rules = load_json(rules_path)
    candidates: list[CandidateRegion] = []

    for item in rules:
        tags = item.get("target_tags") or [item.get("target", "custom")]
        key_score = _keyword_match_score(mission, item.get("keywords", []))
        target_score = _target_match_score(mission.targets, tags)
        evidence_score = clamp(0.65 * target_score + 0.35 * key_score)

        if evidence_score < 0.23:
            continue

        candidate = CandidateRegion(
            id=item["id"],
            wavelength_min_nm=item["wavelength_min_nm"],
            wavelength_max_nm=item["wavelength_max_nm"],
            target_tags=tags,
            rationale=item["rationale"],
            confidence=item["confidence"],
            caution=item["caution"],
            reference=item["reference"],
            interpretability=item.get("interpretability", 0.7),
            robustness=item.get("robustness", 0.7),
            context_band=item.get("context_band", False),
            evidence_score=evidence_score,
            retrieval_reason=f"target_score={target_score:.2f}, keyword_score={key_score:.2f}",
        )

        if mission.wavelength_range_min_nm and candidate.wavelength_max_nm < mission.wavelength_range_min_nm:
            continue
        if mission.wavelength_range_max_nm and candidate.wavelength_min_nm > mission.wavelength_range_max_nm:
            continue

        candidates.append(candidate)

    deduped, merges = _dedupe_candidates(candidates)
    for c in deduped:
        c.fusion_meta["global_dedup_merges"] = merges
    return sorted(deduped, key=lambda x: x.evidence_score, reverse=True)
