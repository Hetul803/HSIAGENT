from core.schemas import MissionInput, ScoredCandidate
from tools.constraint_checker import enforce_band_budget


def test_optimizer_respects_budget_and_spread():
    mission = MissionInput(mission_goal="cloud+water", targets=["cloud", "water"], max_bands=2)
    ranked = [
        ScoredCandidate(id="a", label="a", wavelength_min_nm=840, wavelength_max_nm=880, target_tags=["water"], raw_score=0.9, normalized_score=0.0, components={}, rationale="", caution="", reference=""),
        ScoredCandidate(id="b", label="b", wavelength_min_nm=845, wavelength_max_nm=878, target_tags=["water"], raw_score=0.88, normalized_score=0.0, components={}, rationale="", caution="", reference=""),
        ScoredCandidate(id="c", label="c", wavelength_min_nm=1360, wavelength_max_nm=1400, target_tags=["cloud"], raw_score=0.82, normalized_score=0.0, components={}, rationale="", caution="", reference=""),
    ]
    selected = enforce_band_budget(mission, ranked)
    assert len(selected) <= 2
    assert any("cloud" in s.target_tags for s in selected)
