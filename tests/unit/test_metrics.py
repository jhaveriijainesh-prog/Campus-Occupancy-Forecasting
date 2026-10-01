"""Unit Tests: Mathematical Correctness of SUR, RFU, WSH."""

import pandas as pd

from app.analytics.metrics import calculate_utilization_metrics, filter_occupancy


def test_metrics_handle_empty_and_zero_capacity_frames():
	frame = pd.DataFrame(
		[
			{"room_id": "B01-R101", "capacity": 0, "actual_headcount": 10, "is_scheduled": True, "scheduled_enrollment": 20},
		]
	)

	result = calculate_utilization_metrics(frame)
	assert result["seat_utilization_rate"] == 0.0
	assert result["wasted_seat_hours"] == 10.0
	empty = frame.iloc[0:0]
	assert calculate_utilization_metrics(empty)["observations"] == 0


def test_time_of_day_and_day_filters_are_bounded():
	frame = pd.DataFrame(
		[
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 10, "is_scheduled": True, "scheduled_enrollment": 20, "timestamp": "2026-08-03T08:00:00Z", "hour": 8, "day_of_week": "Monday"},
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 20, "is_scheduled": True, "scheduled_enrollment": 30, "timestamp": "2026-08-03T13:00:00Z", "hour": 13, "day_of_week": "Monday"},
		]
	)

	filtered = filter_occupancy(frame, scope="room", room_id="B01-R101", time_of_day="morning", day_of_week="monday")
	assert len(filtered) == 1
	assert filtered.iloc[0]["hour"] == 8


def test_frequency_uses_configured_operating_slots():
	frame = pd.DataFrame(
		[
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 10, "is_scheduled": True, "scheduled_enrollment": 20, "hour": 8, "timestamp": "2026-08-03T08:00:00Z"},
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 0, "is_scheduled": False, "scheduled_enrollment": 0, "hour": 22, "timestamp": "2026-08-03T22:00:00Z"},
		]
	)

	assert calculate_utilization_metrics(frame, operating_hours_start=7, operating_hours_end=21)["room_frequency_of_use"] == round(1 / 14, 6)


def test_aggregate_sur_weights_occupancy_by_capacity():
	frame = pd.DataFrame(
		[
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 100, "is_scheduled": True, "scheduled_enrollment": 100},
			{"room_id": "B01-R102", "capacity": 10, "actual_headcount": 0, "is_scheduled": True, "scheduled_enrollment": 0},
		]
	)

	assert calculate_utilization_metrics(frame)["seat_utilization_rate"] == round(100 / 110, 6)


def test_wasted_seat_hours_ignore_unscheduled_enrollment():
	frame = pd.DataFrame(
		[
			{"room_id": "B01-R101", "capacity": 100, "actual_headcount": 0, "is_scheduled": False, "scheduled_enrollment": 80},
		]
	)

	assert calculate_utilization_metrics(frame)["wasted_seat_hours"] == 0.0
