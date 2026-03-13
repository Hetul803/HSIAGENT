"""Photon flux suitability estimator."""
from __future__ import annotations

from core.constants import DOMAIN_HINTS, PHOTON_FLUX_FACTORS


def _domain_for_range(wmin: float, wmax: float) -> str:
    center = (wmin + wmax) / 2
    for (lo, hi), domain in DOMAIN_HINTS.items():
        if lo <= center <= hi:
            return domain
    return "visible"


def estimate_photon_flux_penalty(wmin: float, wmax: float, flux_condition: str) -> float:
    """Returns penalty in [0,1], where higher means worse in current flux conditions."""
    domain = _domain_for_range(wmin, wmax)
    factor = PHOTON_FLUX_FACTORS.get(flux_condition, PHOTON_FLUX_FACTORS["medium"]).get(domain, 0.75)
    return 1.0 - factor
