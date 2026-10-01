"""Model-native feature importance and forecast error slicing utilities.

This module deliberately reports XGBoost gain importance and point-forecast
error slices. It does not produce SHAP values, prediction intervals, or
calibration claims.
"""

import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import numpy as np
import pandas as pd

from app.forecasting.baseline import compute_metrics


def load_model_native_importance(metadata_path: str | Path) -> Dict[str, Any]:
	"""Load normalized gain importances from a checked-in model metadata file."""
	path = Path(metadata_path)
	with path.open("r", encoding="utf-8") as handle:
		metadata = json.load(handle)

	top_features = metadata.get("top_features")
	feature_names = metadata.get("feature_names")
	if not isinstance(top_features, dict) or not isinstance(feature_names, list):
		raise ValueError("Model metadata must contain feature_names and top_features")

	return {
		"method": "xgboost_gain",
		"model_type": metadata.get("model_type", "unknown"),
		"best_iteration": metadata.get("best_iteration"),
		"feature_count": len(feature_names),
		"features": [
			{"feature": name, "normalized_gain": float(gain)}
			for name, gain in top_features.items()
		],
	}


def _metric_row(
	frame: pd.DataFrame,
	prediction_column: str,
	model_name: str,
	slice_name: str,
	slice_value: str,
) -> Dict[str, Any]:
	metrics = compute_metrics(frame["actual_headcount"], frame[prediction_column])
	return {
		"model": model_name,
		"slice": slice_name,
		"value": slice_value,
		"sample_count": int(len(frame)),
		**metrics,
	}


def _slice_frames(frame: pd.DataFrame) -> Iterable[tuple[str, str, pd.DataFrame]]:
	"""Yield deterministic, operationally meaningful point-forecast slices."""
	yield "overall", "all", frame

	hour_bins = {
		"night (00-07)": frame["hour"].between(0, 7),
		"morning (08-11)": frame["hour"].between(8, 11),
		"afternoon (12-17)": frame["hour"].between(12, 17),
		"evening (18-23)": frame["hour"].between(18, 23),
	}
	for value, mask in hour_bins.items():
		yield "hour_band", value, frame[mask]

	occupancy_bins = {
		"idle (0-5)": frame["actual_headcount"].between(0, 5),
		"moderate (6-35)": frame["actual_headcount"].between(6, 35),
		"high (36+)": frame["actual_headcount"] >= 36,
	}
	for value, mask in occupancy_bins.items():
		yield "actual_occupancy", value, frame[mask]

	if "is_scheduled" in frame.columns:
		for value, mask in (("scheduled", frame["is_scheduled"].astype(bool)),
							("unscheduled", ~frame["is_scheduled"].astype(bool))):
			yield "schedule_status", value, frame[mask]


def build_error_slices(
	predictions: pd.DataFrame,
	prediction_column: str = "predicted_headcount",
	model_name: str = "xgboost",
) -> List[Dict[str, Any]]:
	"""Compute finite metrics for non-empty slices of point forecasts."""
	required = {"actual_headcount", prediction_column, "hour"}
	missing = required.difference(predictions.columns)
	if missing:
		raise ValueError(f"Prediction data is missing columns: {sorted(missing)}")

	rows = []
	for slice_name, slice_value, frame in _slice_frames(predictions):
		if frame.empty:
			continue
		rows.append(_metric_row(frame, prediction_column, model_name, slice_name, slice_value))
	return rows


def generate_explainability_artifacts(
	model_metadata_path: str | Path,
	xgboost_predictions_path: str | Path,
	output_dir: str | Path,
	baseline_predictions_path: Optional[str | Path] = None,
) -> Dict[str, str]:
	"""Generate model-native importance and point-forecast error artifacts."""
	output_path = Path(output_dir)
	output_path.mkdir(parents=True, exist_ok=True)

	xgb = pd.read_csv(xgboost_predictions_path)
	if baseline_predictions_path is not None:
		baseline = pd.read_csv(baseline_predictions_path)
		baseline_columns = ["observation_id", "pred_HistoricalSeasonalProfile", "actual_headcount"]
		merged = xgb.merge(baseline[baseline_columns], on="observation_id", validate="one_to_one", suffixes=("", "_baseline"))
		if not np.array_equal(
			merged["actual_headcount"].to_numpy(),
			merged["actual_headcount_baseline"].to_numpy(),
		):
			raise ValueError("Actual headcounts differ between prediction artifacts")
		merged = merged.drop(columns=["actual_headcount_baseline"])
	else:
		merged = xgb

	importance = load_model_native_importance(model_metadata_path)
	importance_path = output_path / "feature_importance.json"
	importance_path.write_text(json.dumps(importance, indent=2), encoding="utf-8")

	slice_rows = build_error_slices(merged, model_name="xgboost")
	if "pred_HistoricalSeasonalProfile" in merged.columns:
		slice_rows.extend(build_error_slices(
			merged,
			prediction_column="pred_HistoricalSeasonalProfile",
			model_name="historical_seasonal_baseline",
		))
	slices_path = output_path / "error_slices.json"
	slices_path.write_text(json.dumps(slice_rows, indent=2), encoding="utf-8")
	pd.DataFrame(slice_rows).to_csv(output_path / "error_slices.csv", index=False)

	return {
		"feature_importance": str(importance_path),
		"error_slices": str(slices_path),
		"error_slices_csv": str(output_path / "error_slices.csv"),
	}
