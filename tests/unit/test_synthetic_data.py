"""Regression tests for the synthetic campus demo data."""

import numpy as np

from scripts.generate_data import generate_rooms, generate_timetable


def test_timetable_covers_every_room_with_capacity_safe_non_overlapping_sessions():
    rooms = generate_rooms()
    timetable = generate_timetable(rooms, np.random.default_rng(42))

    assert set(timetable["room_id"]) == set(rooms["room_id"])

    capacities = rooms.set_index("room_id")["capacity"]
    for row in timetable.itertuples():
        assert row.enrolled_count <= capacities[row.room_id]

    for _, room_schedule in timetable.groupby(["room_id", "day_of_week"]):
        ordered = room_schedule.sort_values("start_time")
        end_times = ordered["end_time"].tolist()
        start_times = ordered["start_time"].tolist()
        assert all(
            previous_end <= next_start
            for previous_end, next_start in zip(end_times, start_times[1:])
        )

    synthetic_sessions = timetable.loc[timetable["course_code"].str.startswith("SYN-")]
    catalog_timetable = timetable.loc[~timetable["course_code"].str.startswith("SYN-")]
    catalog_hours = catalog_timetable.groupby("room_id")["duration_hours"].sum()
    catalog_hours = catalog_hours.reindex(rooms["room_id"], fill_value=0)
    expected_synthetic_rooms = set(
        catalog_hours[catalog_hours < 15].index
    )
    assert set(synthetic_sessions["room_id"]) == expected_synthetic_rooms
    weekly_room_hours = timetable.groupby("room_id")["duration_hours"].sum()
    assert weekly_room_hours.ge(15).all()

    synthetic_capacities = synthetic_sessions["room_id"].map(capacities)
    expected_enrollment = synthetic_capacities.mul(0.7).round().clip(lower=1)
    assert synthetic_sessions["enrolled_count"].reset_index(drop=True).equals(
        expected_enrollment.reset_index(drop=True).astype(int)
    )
