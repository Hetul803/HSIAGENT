from core.schemas import MissionInput, ScoredCandidate
from tools.constraint_checker import enforce_band_budget


def test_enforce_band_budget_limits_count():
    mission = MissionInput(mission_goal="test", max_bands=2)
    ranked = [
        ScoredCandidate(
            id=f"c{i}",
            label="x",
            wavelength_min_nm=500,
            wavelength_max_nm=510,
            raw_score=0.9 - i * 0.1,
            normalized_score=0.0,
            components={},
            rationale="",
            caution="",
            reference="",
        )
        for i in range(4)
    ]
    selected = enforce_band_budget(mission, ranked)
    assert len(selected) == 2
