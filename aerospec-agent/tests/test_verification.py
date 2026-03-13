from core.schemas import MissionInput, ScoredCandidate
from tools.verification import verify_recommendation


def test_verification_warns_on_low_alignment():
    mission = MissionInput(mission_goal="cloud mission", target_type="cloud", max_bands=3)
    selected = [
        ScoredCandidate(
            id="water_nir_860",
            label="x",
            wavelength_min_nm=840,
            wavelength_max_nm=880,
            raw_score=0.7,
            normalized_score=0.8,
            components={},
            rationale="",
            caution="",
            reference="",
        )
    ]
    result = verify_recommendation(mission, selected)
    assert any("alignment" in w.lower() for w in result.warnings)
    assert 0 <= result.confidence <= 1
