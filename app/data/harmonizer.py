"""Deterministic timetable, occupancy, and event alignment."""

from __future__ import annotations

import pandas as pd


def _minutes(value: pd.Series) -> pd.Series:
	parsed = pd.to_timedelta(value.astype(str), errors="coerce")
	return parsed.dt.total_seconds().div(60)


def harmonize_sources(
	occupancy: pd.DataFrame,
	timetable: pd.DataFrame,
	events: pd.DataFrame | None = None,
	*,
	timezone: str = "UTC",
) -> pd.DataFrame:
	"""Derive schedule and event context for each occupancy observation.

	Matching is performed on room, local day, and half-open timetable intervals.
	The input frames are never mutated and unmatched observations are retained.
	"""
	required_occupancy = {"room_id", "timestamp", "actual_headcount"}
	required_timetable = {"room_id", "day_of_week", "start_time", "end_time"}
	missing_occupancy = required_occupancy.difference(occupancy.columns)
	missing_timetable = required_timetable.difference(timetable.columns)
	if missing_occupancy or missing_timetable:
		raise ValueError(
			f"Missing harmonization columns: occupancy={sorted(missing_occupancy)}, "
			f"timetable={sorted(missing_timetable)}"
		)

	result = occupancy.copy()
	timestamps = pd.to_datetime(result["timestamp"], utc=True, errors="coerce")
	if timestamps.isna().any():
		raise ValueError("occupancy contains invalid timestamps")
	local = timestamps.dt.tz_convert(timezone)
	result["date"] = local.dt.date.astype("string")
	result["hour"] = local.dt.hour.astype("int64")
	result["day_of_week"] = local.dt.day_name()
	result["_time_minutes"] = local.dt.hour * 60 + local.dt.minute

	schedule = timetable.copy()
	schedule["_start_minutes"] = _minutes(schedule["start_time"])
	schedule["_end_minutes"] = _minutes(schedule["end_time"])
	if schedule[["_start_minutes", "_end_minutes"]].isna().any().any():
		raise ValueError("timetable contains invalid start_time or end_time")
	schedule = schedule.rename(columns={
		"course_code": "_schedule_course_code",
		"enrolled_count": "_schedule_enrollment",
		"timetable_id": "_schedule_timetable_id",
	})
	joined = result.merge(schedule, on=["room_id", "day_of_week"], how="left", suffixes=("", "_schedule"))
	matches = joined[
		(joined["_time_minutes"] >= joined["_start_minutes"])
		& (joined["_time_minutes"] < joined["_end_minutes"])
	].copy()
	selected = matches.sort_values(["observation_id", "_start_minutes"]).drop_duplicates("observation_id") if "observation_id" in matches else matches.drop_duplicates(["room_id", "timestamp"])
	schedule_columns = {
		"scheduled_course_code": "_schedule_course_code",
		"scheduled_enrollment": "_schedule_enrollment",
		"timetable_id": "_schedule_timetable_id",
	}
	for output_column, source_column in schedule_columns.items():
		if source_column in selected.columns:
			key = "observation_id" if "observation_id" in result.columns else None
			if key:
				mapping = selected.set_index(key)[source_column]
				result[output_column] = result[key].map(mapping)
			else:
				mapping = selected.set_index(["room_id", "timestamp"])[source_column]
				result[output_column] = result.set_index(["room_id", "timestamp"]).index.map(mapping)
	result["is_scheduled"] = result["scheduled_course_code"].notna()
	result["scheduled_enrollment"] = pd.to_numeric(result["scheduled_enrollment"], errors="coerce").fillna(0)

	if events is not None and not events.empty and "date" in events.columns:
		event_frame = events.copy()
		event_frame["date"] = pd.to_datetime(event_frame["date"], errors="coerce").dt.date.astype("string")
		event_frame = event_frame.drop_duplicates("date").rename(columns={
			"event_type": "campus_event_type",
			"impact_factor": "campus_event_impact_factor",
		})
		result = result.merge(
			event_frame[["date", "campus_event_type", "campus_event_impact_factor"]],
			on="date",
			how="left",
		)
	result = result.drop(columns=["_time_minutes"], errors="ignore")
	return result
