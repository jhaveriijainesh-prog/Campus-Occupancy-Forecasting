"""MILP and heuristic allocation tests."""

import pandas as pd

from app.optimization.heuristics import greedy_allocate
from app.optimization.solver import optimize_allocation


def _rooms() -> pd.DataFrame:
    return pd.DataFrame([
        {"room_id": "R1", "capacity": 100, "room_type": "Lecture Hall"},
        {"room_id": "R2", "capacity": 60, "room_type": "Lecture Hall"},
    ])


def _timetable() -> pd.DataFrame:
    return pd.DataFrame([
        {"timetable_id": "C1", "room_id": "R1", "enrolled_count": 55, "room_type_required": "Lecture Hall", "day_of_week": "Monday", "start_time": "09:00:00", "end_time": "10:00:00"},
        {"timetable_id": "C2", "room_id": "R1", "enrolled_count": 90, "room_type_required": "Lecture Hall", "day_of_week": "Monday", "start_time": "09:00:00", "end_time": "10:00:00"},
    ])


def test_milp_assigns_feasible_rooms_without_overlap_or_capacity_violation():
    result = optimize_allocation(_timetable(), _rooms())

    assert result.feasible
    assert len(result.assignments) == 2
    assert (result.assignments["capacity"] >= result.assignments["enrolled_count"]).all()
    assert result.assignments["room_id"].nunique() == 2


def test_heuristic_produces_measurable_baseline():
    result = greedy_allocate(_timetable(), _rooms())

    assert result.feasible
    assert result.objective_value == 15.0


def test_heuristic_checks_overlap_against_assigned_room():
    rooms = pd.DataFrame([
        {"room_id": "R1", "capacity": 60, "room_type": "Lecture Hall"},
        {"room_id": "R2", "capacity": 100, "room_type": "Lecture Hall"},
    ])

    result = greedy_allocate(_timetable(), rooms)

    assert result.feasible
    assert result.assignments["room_id"].nunique() == 2


def test_milp_reports_infeasibility():
    courses = _timetable().copy()
    courses.loc[0, "enrolled_count"] = 101
    result = optimize_allocation(courses, _rooms())

    assert not result.feasible
    assert result.infeasibility_reason
