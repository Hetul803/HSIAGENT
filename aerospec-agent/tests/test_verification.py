from core.schemas import MissionInput, ScoredCandidate
from tools.verification import verify_recommendation


def test_verification_flags_missing_target_coverage():
    mission = MissionInput(mission_goal="cloud water moisture", targets=["cloud", "water", "moisture"], max_bands=3)
    selected = [
        ScoredCandidate(
            id="water_nir_860",
            label="x",
            wavelength_min_nm=840,
            wavelength_max_nm=880,
            target_tags=["water"],
            raw_score=0.72,
            normalized_score=0.7,
            components={"photon_flux_suitability": 0.8},
            rationale="",
            caution="",
            reference="",
        )
    ]
    result = verify_recommendation(mission, selected)
    assert result.status in {"caution", "fail"}
    assert any("Missing" in w for w in result.warnings)
