"""Constraint-aware room allocation using PuLP CBC."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

import pandas as pd
import pulp


def _minutes(value: object) -> int:
	parsed = pd.to_timedelta(str(value), errors="coerce")
	if pd.isna(parsed):
		raise ValueError(f"Invalid timetable time: {value}")
	return int(parsed.total_seconds() // 60)


def _overlaps(left: pd.Series, right: pd.Series) -> bool:
	return (
		left["day_of_week"] == right["day_of_week"]
		and _minutes(left["start_time"]) < _minutes(right["end_time"])
		and _minutes(right["start_time"]) < _minutes(left["end_time"])
	)


@dataclass(frozen=True)
class AllocationResult:
	"""Auditable output of an allocation attempt."""

	feasible: bool
	assignments: pd.DataFrame
	objective_value: float | None
	runtime_seconds: float
	solver_status: str
	infeasibility_reason: str | None = None


def _candidate_rooms(course: pd.Series, rooms: pd.DataFrame) -> pd.DataFrame:
	candidates = rooms[rooms["capacity"] >= course["enrolled_count"]]
	required_type = str(course.get("room_type_required", "")).strip()
	if required_type:
		candidates = candidates[candidates["room_type"].astype(str) == required_type]
	return candidates


def optimize_allocation(
	timetable: pd.DataFrame,
	rooms: pd.DataFrame,
	*,
	timeout_seconds: float = 30.0,
) -> AllocationResult:
	"""Minimize unused seats while enforcing assignment and overlap constraints."""
	started = perf_counter()
	required_timetable = {"timetable_id", "day_of_week", "start_time", "end_time", "room_id", "enrolled_count"}
	required_rooms = {"room_id", "capacity", "room_type"}
	if missing := required_timetable.difference(timetable.columns):
		raise ValueError(f"timetable missing optimization columns: {sorted(missing)}")
	if missing := required_rooms.difference(rooms.columns):
		raise ValueError(f"rooms missing optimization columns: {sorted(missing)}")
	if timetable.empty:
		return AllocationResult(True, pd.DataFrame(), 0.0, perf_counter() - started, "Empty")

	courses = timetable.reset_index(drop=True).copy()
	rooms_frame = rooms.drop_duplicates("room_id").reset_index(drop=True).copy()
	candidates: dict[int, list[str]] = {}
	for index, course in courses.iterrows():
		options = _candidate_rooms(course, rooms_frame)
		if options.empty:
			return AllocationResult(False, pd.DataFrame(), None, perf_counter() - started, "Infeasible", f"No suitable room for {course['timetable_id']}")
		candidates[index] = options["room_id"].astype(str).tolist()

	problem = pulp.LpProblem("campus_room_allocation", pulp.LpMinimize)
	variables = {
		(index, room_id): pulp.LpVariable(f"assign_{index}_{room_id}", cat="Binary")
		for index, room_ids in candidates.items() for room_id in room_ids
	}
	problem += pulp.lpSum(
		variables[index, room_id] * float(rooms_frame.loc[rooms_frame["room_id"] == room_id, "capacity"].iloc[0] - courses.loc[index, "enrolled_count"])
		for index, room_ids in candidates.items() for room_id in room_ids
	)
	for index in candidates:
		problem += pulp.lpSum(variables[index, room_id] for room_id in candidates[index]) == 1
	for room_id in rooms_frame["room_id"].astype(str):
		for left in candidates:
			if room_id not in candidates[left]:
				continue
			for right in range(left + 1, len(courses)):
				if room_id in candidates.get(right, []) and _overlaps(courses.loc[left], courses.loc[right]):
					problem += variables[left, room_id] + variables[right, room_id] <= 1

	status = problem.solve(pulp.PULP_CBC_CMD(msg=False, timeLimit=timeout_seconds))
	status_name = pulp.LpStatus[status]
	if status_name != "Optimal":
		return AllocationResult(False, pd.DataFrame(), None, perf_counter() - started, status_name, "No allocation satisfies all hard constraints")

	records = []
	for index, room_ids in candidates.items():
		assigned = next(room_id for room_id in room_ids if pulp.value(variables[index, room_id]) > 0.5)
		capacity = float(rooms_frame.loc[rooms_frame["room_id"] == assigned, "capacity"].iloc[0])
		records.append({
			"timetable_id": courses.loc[index, "timetable_id"],
			"room_id": assigned,
			"enrolled_count": float(courses.loc[index, "enrolled_count"]),
			"capacity": capacity,
			"unused_capacity": capacity - float(courses.loc[index, "enrolled_count"]),
			"day_of_week": courses.loc[index, "day_of_week"],
			"start_time": courses.loc[index, "start_time"],
			"end_time": courses.loc[index, "end_time"],
		})
	return AllocationResult(True, pd.DataFrame(records), float(pulp.value(problem.objective)), perf_counter() - started, status_name)
