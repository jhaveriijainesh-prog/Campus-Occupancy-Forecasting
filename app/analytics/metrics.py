"""Seat Utilization Rate, Frequency of Use, Wasted Seat-Hours."""

from __future__ import annotations

import pandas as pd

REQUIRED_COLUMNS = {
	"room_id",
	"capacity",
	"actual_headcount",
	"is_scheduled",
	"scheduled_enrollment",
}

TIME_OF_DAY_WINDOWS = {
	"morning": (7, 12),
	"midday": (12, 14),
	"afternoon": (14, 17),
	"evening": (17, 21),
}
VALID_DAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}

def calculate_utilization_metrics(
	occupancy: pd.DataFrame,
	*,
	slot_duration_hours: float = 1.0,
	operating_hours_start: int | None = None,
	operating_hours_end: int | None = None,
	available_slot_hours: int | None = None,
) -> dict:
	"""Calculate SUR, RFU, and WSH from cleaned occupancy observations."""
	missing = REQUIRED_COLUMNS.difference(occupancy.columns)
	if missing:
		raise ValueError(f"Occupancy data missing required columns: {sorted(missing)}")
	if occupancy.empty:
		return {
			"seat_utilization_rate": 0.0,
			"room_frequency_of_use": 0.0,
			"wasted_seat_hours": 0.0,
			"peak_occupancy": 0.0,
			"observations": 0,
		}

	frame = occupancy.copy()
	capacity = pd.to_numeric(frame["capacity"], errors="coerce").fillna(0).clip(lower=0)
	actual = pd.to_numeric(frame["actual_headcount"], errors="coerce").fillna(0).clip(lower=0)
	scheduled = pd.to_numeric(frame["scheduled_enrollment"], errors="coerce").fillna(0).clip(lower=0)
	scheduled = scheduled.where(frame["is_scheduled"].fillna(False).astype(bool), 0)
	valid_capacity = capacity > 0
	utilization = (actual[valid_capacity] / capacity[valid_capacity]).clip(lower=0)
	if "hour" in frame.columns and operating_hours_start is not None and operating_hours_end is not None:
		hours = pd.to_numeric(frame["hour"], errors="coerce")
		operating_slots = hours.ge(operating_hours_start) & hours.lt(operating_hours_end)
		if available_slot_hours is None and "timestamp" in frame.columns:
			dates = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce").dt.date.nunique()
			rooms = frame["room_id"].nunique()
			available_slot_hours = dates * rooms * (operating_hours_end - operating_hours_start)
	else:
		operating_slots = pd.Series(True, index=frame.index)
	occupied_slots = int(((actual > 0) & operating_slots).sum())
	total_slots = available_slot_hours if available_slot_hours is not None else int(operating_slots.sum())

	return {
		"seat_utilization_rate": round(float(actual[valid_capacity].sum() / capacity[valid_capacity].sum()) if not utilization.empty else 0.0, 6),
		"room_frequency_of_use": round(occupied_slots / total_slots if total_slots else 0.0, 6),
		"wasted_seat_hours": round(float((scheduled.sub(actual).clip(lower=0) * slot_duration_hours).sum()), 6),
		"peak_occupancy": round(float(actual.max()), 6),
		"observations": total_slots,
	}

def add_building_id(occupancy: pd.DataFrame) -> pd.DataFrame:
	"""Add a building identifier when processed occupancy only contains room IDs."""
	frame = occupancy.copy()
	if "building_id" not in frame.columns:
		frame["building_id"] = frame["room_id"].astype(str).str.split("-", n=1).str[0]
	return frame

def filter_occupancy(
	occupancy: pd.DataFrame,
	*,
	scope: str,
	room_id: str | None = None,
	building_id: str | None = None,
	start_time: str | None = None,
	end_time: str | None = None,
	day_of_week: str | None = None,
	time_of_day: str | None = None,
) -> pd.DataFrame:
	"""Apply bounded, non-telemetry filters for a metrics request."""
	frame = add_building_id(occupancy)
	if scope not in {"campus", "building", "room"}:
		raise ValueError("scope must be one of: campus, building, room")
	if scope == "room" and not room_id:
		raise ValueError("room_id is required for room scope")
	if scope == "building" and not building_id:
		raise ValueError("building_id is required for building scope")
	if room_id:
		frame = frame[frame["room_id"] == room_id]
	if building_id:
		frame = frame[frame["building_id"] == building_id]
	if start_time or end_time:
		if "timestamp" not in frame.columns:
			raise ValueError("timestamp is required for time filtering")
		timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
		if timestamps.isna().any():
			raise ValueError("occupancy data contains invalid timestamps")
		try:
			start = pd.Timestamp(start_time, tz="UTC") if start_time else None
			end = pd.Timestamp(end_time, tz="UTC") if end_time else None
		except (TypeError, ValueError) as exc:
			raise ValueError("start_time and end_time must be valid ISO timestamps") from exc
		if start is not None and end is not None and start > end:
			raise ValueError("start_time must be earlier than or equal to end_time")
		if start_time:
			frame = frame[timestamps >= start]
		if end_time:
			frame = frame[timestamps <= end]
	if day_of_week:
		if "day_of_week" not in frame.columns:
			raise ValueError("day_of_week is unavailable in occupancy data")
		day = day_of_week.casefold()
		if day not in VALID_DAYS:
			raise ValueError("day_of_week must be a valid weekday name")
		frame = frame[frame["day_of_week"].astype(str).str.casefold() == day]
	if time_of_day:
		window = TIME_OF_DAY_WINDOWS.get(time_of_day.casefold())
		if window is None:
			raise ValueError("time_of_day must be one of: morning, midday, afternoon, evening")
		if "hour" not in frame.columns:
			raise ValueError("time_of_day is unavailable in occupancy data")
		hour = pd.to_numeric(frame["hour"], errors="coerce")
		if hour.isna().any():
			raise ValueError("occupancy data contains invalid hours")
		frame = frame[hour.ge(window[0]) & hour.lt(window[1])]
	return frame
