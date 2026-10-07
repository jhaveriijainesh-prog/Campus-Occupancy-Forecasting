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
    catalog_rooms = set(
        timetable.loc[~timetable["course_code"].str.startswith("SYN-"), "room_id"]
    )
    assert set(synthetic_sessions["room_id"]) == set(rooms["room_id"]) - catalog_rooms
    assert synthetic_sessions["room_id"].value_counts().eq(3).all()
