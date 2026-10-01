"""Deterministic what-if occupancy and room-availability simulation."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json

import pandas as pd

from app.analytics.metrics import calculate_utilization_metrics


@dataclass(frozen=True)
class ScenarioResult:
	"""Reproducible scenario state and metric comparison."""

	scenario_id: str
	parameters: dict
	scenario_data: pd.DataFrame
	baseline_metrics: dict
	scenario_metrics: dict

	@property
	def metric_deltas(self) -> dict:
		return {
			key: round(self.scenario_metrics[key] - self.baseline_metrics[key], 6)
			for key in self.baseline_metrics
			if isinstance(self.baseline_metrics[key], (int, float))
		}


def simulate_scenario(
	occupancy: pd.DataFrame,
	*,
	occupancy_multiplier: float = 1.0,
	closed_rooms: list[str] | None = None,
	capacity_adjustments: dict[str, float] | None = None,
	enrollment_multiplier: float = 1.0,
) -> ScenarioResult:
	"""Apply validated scenario changes without mutating baseline data."""
	if occupancy.empty:
		raise ValueError("Cannot simulate an empty occupancy dataset")
	if occupancy_multiplier <= 0 or enrollment_multiplier <= 0:
		raise ValueError("scenario multipliers must be positive")
	closed = sorted(set(closed_rooms or []))
	known_rooms = set(occupancy["room_id"].astype(str))
	unknown_rooms = set(closed).difference(known_rooms)
	if unknown_rooms:
		raise ValueError(f"closed_rooms contains unknown rooms: {sorted(unknown_rooms)}")
	adjustments = capacity_adjustments or {}
	if set(adjustments).difference(known_rooms):
		raise ValueError("capacity_adjustments contains unknown rooms")
	if any(float(value) <= 0 for value in adjustments.values()):
		raise ValueError("capacity adjustments must be positive")

	parameters = {
		"occupancy_multiplier": float(occupancy_multiplier),
		"closed_rooms": closed,
		"capacity_adjustments": {key: float(adjustments[key]) for key in sorted(adjustments)},
		"enrollment_multiplier": float(enrollment_multiplier),
	}
	scenario_id = hashlib.sha256(json.dumps(parameters, sort_keys=True).encode()).hexdigest()[:12]
	result = occupancy.copy(deep=True)
	result["actual_headcount"] = (
		pd.to_numeric(result["actual_headcount"], errors="coerce").fillna(0)
		* occupancy_multiplier
	).clip(lower=0)
	result["scheduled_enrollment"] = (
		pd.to_numeric(result["scheduled_enrollment"], errors="coerce").fillna(0)
		* enrollment_multiplier
	).clip(lower=0)
	for room_id, capacity in adjustments.items():
		result.loc[result["room_id"] == room_id, "capacity"] = float(capacity)
	if closed:
		closed_mask = result["room_id"].isin(closed)
		result.loc[closed_mask, ["actual_headcount", "scheduled_enrollment"]] = 0
		result.loc[closed_mask, "is_scheduled"] = False
	result["actual_headcount"] = result[["actual_headcount", "capacity"]].min(axis=1)

	return ScenarioResult(
		scenario_id=scenario_id,
		parameters=parameters,
		scenario_data=result,
		baseline_metrics=calculate_utilization_metrics(occupancy),
		scenario_metrics=calculate_utilization_metrics(result),
	)
