"""Deterministic capacity-first allocation baseline."""

from __future__ import annotations

import pandas as pd

from app.optimization.solver import AllocationResult, _candidate_rooms, _overlaps


def greedy_allocate(timetable: pd.DataFrame, rooms: pd.DataFrame) -> AllocationResult:
	"""Assign largest courses first to the smallest suitable available room."""
	if timetable.empty:
		return AllocationResult(True, pd.DataFrame(), 0.0, 0.0, "Greedy")
	assignments: list[dict] = []
	used: list[pd.Series] = []
	for _, course in timetable.sort_values("enrolled_count", ascending=False).iterrows():
		options = _candidate_rooms(course, rooms).sort_values(["capacity", "room_id"])
		chosen = None
		for _, room in options.iterrows():
			if not any(existing["room_id"] == room["room_id"] and _overlaps(course, existing) for existing in used):
				chosen = room
				break
		if chosen is None:
			return AllocationResult(False, pd.DataFrame(assignments), None, 0.0, "GreedyInfeasible", f"No available room for {course['timetable_id']}")
		record = {
			"timetable_id": course["timetable_id"],
			"room_id": chosen["room_id"],
			"enrolled_count": float(course["enrolled_count"]),
			"capacity": float(chosen["capacity"]),
			"unused_capacity": float(chosen["capacity"] - course["enrolled_count"]),
			"day_of_week": course["day_of_week"],
			"start_time": course["start_time"],
			"end_time": course["end_time"],
		}
		assignments.append(record)
		assigned_course = course.copy()
		assigned_course["room_id"] = chosen["room_id"]
		used.append(assigned_course)
	frame = pd.DataFrame(assignments)
	return AllocationResult(True, frame, float(frame["unused_capacity"].sum()), 0.0, "Greedy")
