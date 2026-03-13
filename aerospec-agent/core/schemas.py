"""Typed schemas for AeroSpec Agent."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class MissionInput(BaseModel):
    mission_goal: str
    target_type: Literal["cloud", "water", "moisture", "vegetation", "custom"] = "custom"
    platform_type: Literal["airborne", "satellite", "runway-side", "drone"] = "airborne"
    max_bands: int = Field(default=6, ge=1, le=20)
    photon_flux_condition: Literal["low", "medium", "high"] = "medium"
    priority: Literal["accuracy", "robustness", "compactness", "interpretability"] = "accuracy"
    wavelength_range_min_nm: float | None = None
    wavelength_range_max_nm: float | None = None
    notes: str = ""


class CandidateRegion(BaseModel):
    id: str
    target: str
    wavelength_min_nm: float
    wavelength_max_nm: float
    rationale: str
    confidence: float
    caution: str
    reference: str
    interpretability: float = 0.7
    robustness: float = 0.7
    retrieval_reason: str = ""
    evidence_score: float = 0.5


class ScoredCandidate(BaseModel):
    id: str
    label: str
    wavelength_min_nm: float
    wavelength_max_nm: float
    raw_score: float
    normalized_score: float
    components: dict[str, float]
    rationale: str
    caution: str
    reference: str
    retrieval_reason: str = ""


class RecommendationBundle(BaseModel):
    best_overall: list[ScoredCandidate]
    best_compact: list[ScoredCandidate]
    best_robust: list[ScoredCandidate]


class VerificationResult(BaseModel):
    passed: bool
    confidence: float
    warnings: list[str]
    checks: dict[str, Any]


class AgentError(BaseModel):
    stage: str
    message: str
