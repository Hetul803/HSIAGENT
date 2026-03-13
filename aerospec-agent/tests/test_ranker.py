from core.schemas import CandidateRegion, MissionInput
from tools.wavelength_ranker import score_wavelength_candidates


def test_ranker_orders_by_score_desc():
    mission = MissionInput(mission_goal="standing water", target_type="water")
    cands = [
        CandidateRegion(
            id="water_nir_860",
            target="water",
            wavelength_min_nm=840,
            wavelength_max_nm=880,
            rationale="water contrast",
            confidence=0.8,
            caution="",
            reference="x",
            interpretability=0.8,
            robustness=0.9,
        ),
        CandidateRegion(
            id="visible_ref_green",
            target="custom",
            wavelength_min_nm=540,
            wavelength_max_nm=570,
            rationale="reference",
            confidence=0.7,
            caution="",
            reference="y",
            interpretability=0.9,
            robustness=0.7,
        ),
    ]
    ranked = score_wavelength_candidates(mission, cands)
    assert ranked[0].raw_score >= ranked[1].raw_score
    assert 0.0 <= ranked[0].normalized_score <= 1.0
