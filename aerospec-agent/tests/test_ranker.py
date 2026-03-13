from core.schemas import CandidateRegion, MissionInput
from tools.wavelength_ranker import score_wavelength_candidates


def test_ranker_handles_multi_target_scoring():
    mission = MissionInput(mission_goal="cloud and water sweep", targets=["cloud", "water"], max_bands=4)
    cands = [
        CandidateRegion(
            id="cloud_nir_865",
            wavelength_min_nm=845,
            wavelength_max_nm=885,
            target_tags=["cloud", "water"],
            rationale="multi-target",
            confidence=0.8,
            caution="",
            reference="seed",
        ),
        CandidateRegion(
            id="veg_rededge_720",
            wavelength_min_nm=705,
            wavelength_max_nm=740,
            target_tags=["vegetation"],
            rationale="other",
            confidence=0.8,
            caution="",
            reference="seed",
        ),
    ]
    ranked = score_wavelength_candidates(mission, cands)
    assert ranked[0].id == "cloud_nir_865"
    assert 0 <= ranked[0].normalized_score <= 1
