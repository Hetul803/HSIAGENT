"""Constants used by deterministic scoring and checks."""
from __future__ import annotations

SCORING_WEIGHTS = {
    "mission_relevance": 0.27,
    "photon_flux_suitability": 0.18,
    "interpretability": 0.14,
    "compactness": 0.14,
    "robustness": 0.15,
    "knowledge_confidence": 0.12,
}

PHOTON_FLUX_FACTORS = {
    "low": {"visible": 1.0, "nir": 0.78, "swir": 0.5, "tir": 0.45},
    "medium": {"visible": 1.0, "nir": 0.92, "swir": 0.76, "tir": 0.68},
    "high": {"visible": 1.0, "nir": 1.0, "swir": 0.96, "tir": 0.88},
}

DOMAIN_HINTS = {
    (400, 700): "visible",
    (700, 1000): "nir",
    (1000, 2500): "swir",
    (8000, 14000): "tir",
}

PRIORITY_WEIGHTS = {
    "accuracy": {"mission_relevance": 0.55, "knowledge_confidence": 0.45},
    "robustness": {"robustness": 0.7, "photon_flux_suitability": 0.3},
    "compactness": {"compactness": 0.75, "interpretability": 0.25},
    "interpretability": {"interpretability": 0.8, "knowledge_confidence": 0.2},
}

DEFAULT_CONFIDENCE = 0.62
