"""Scenario simulation tests."""

import pandas as pd
import pytest

from app.simulation.simulator import simulate_scenario


def _occupancy() -> pd.DataFrame:
    return pd.DataFrame([
        {"room_id": "R1", "capacity": 100, "actual_headcount": 50, "is_scheduled": True, "scheduled_enrollment": 80},
        {"room_id": "R2", "capacity": 60, "actual_headcount": 20, "is_scheduled": True, "scheduled_enrollment": 40},
    ])


def test_scenario_is_reproducible_and_preserves_baseline():
    baseline = _occupancy()
    first = simulate_scenario(baseline, occupancy_multiplier=1.2, closed_rooms=["R2"])
    second = simulate_scenario(baseline, occupancy_multiplier=1.2, closed_rooms=["R2"])

    assert first.scenario_id == second.scenario_id
    assert first.scenario_data.loc[1, "actual_headcount"] == 0
    assert first.scenario_data.loc[0, "actual_headcount"] == 60
    assert first.metric_deltas["peak_occupancy"] == 10.0
    pd.testing.assert_frame_equal(baseline, _occupancy())


def test_capacity_adjustment_clamps_occupancy():
    result = simulate_scenario(_occupancy(), occupancy_multiplier=2, capacity_adjustments={"R1": 70})

    assert result.scenario_data.loc[0, "capacity"] == 70
    assert result.scenario_data.loc[0, "actual_headcount"] == 70


def test_invalid_scenarios_fail_explicitly():
    with pytest.raises(ValueError, match="positive"):
        simulate_scenario(_occupancy(), occupancy_multiplier=0)
    with pytest.raises(ValueError, match="unknown rooms"):
        simulate_scenario(_occupancy(), closed_rooms=["R9"])
    with pytest.raises(ValueError, match="empty"):
        simulate_scenario(pd.DataFrame())
