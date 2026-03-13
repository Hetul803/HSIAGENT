"""Constants used by deterministic scoring and checks."""
from __future__ import annotations

SCORING_WEIGHTS = {
    "target_coverage": 0.24,
    "photon_flux_suitability": 0.16,
    "interpretability": 0.12,
    "compactness": 0.1,
    "robustness": 0.12,
    "knowledge_confidence": 0.1,
    "reference_context_bonus": 0.08,
    "overlap_bonus": 0.08,
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
    "accuracy": {"target_coverage": 0.5, "knowledge_confidence": 0.25, "robustness": 0.25},
    "robustness": {"robustness": 0.6, "photon_flux_suitability": 0.4},
    "compactness": {"compactness": 0.7, "target_coverage": 0.3},
    "interpretability": {"interpretability": 0.8, "reference_context_bonus": 0.2},
}

DEFAULT_CONFIDENCE = 0.6
