"""Focused tests for model-native explainability artifacts."""

import json
from pathlib import Path

import pandas as pd

from app.analytics.explainability import (
    build_error_slices,
    generate_explainability_artifacts,
    load_model_native_importance,
)


ROOT = Path(__file__).resolve().parents[2]


def test_build_error_slices_has_finite_point_metrics():
    predictions = pd.DataFrame({
        "hour": [0, 10, 18, 12],
        "is_scheduled": [False, True, False, True],
        "actual_headcount": [0, 40, 2, 50],
        "predicted_headcount": [0, 35, 3, 45],
    })

    rows = build_error_slices(predictions)

    assert {row["slice"] for row in rows} == {"overall", "hour_band", "actual_occupancy", "schedule_status"}
    assert all(row["sample_count"] > 0 for row in rows)
    assert all(row["MAE"] >= 0 and row["RMSE"] >= 0 for row in rows)


def test_generate_artifacts_from_checked_in_predictions(tmp_path):
    paths = generate_explainability_artifacts(
        ROOT / "experiments/xgboost/feature_metadata.json",
        ROOT / "experiments/xgboost/test_predictions.csv",
        tmp_path,
        ROOT / "experiments/baseline/test_predictions.csv",
    )

    importance = json.loads(Path(paths["feature_importance"]).read_text(encoding="utf-8"))
    slices = json.loads(Path(paths["error_slices"]).read_text(encoding="utf-8"))

    assert importance["method"] == "xgboost_gain"
    assert importance["feature_count"] == 48
    assert len(importance["features"]) == 15
    assert {row["model"] for row in slices} == {"xgboost", "historical_seasonal_baseline"}
    assert len(slices) >= 10
    assert all(row["sample_count"] > 0 for row in slices)
    assert all(row["MAE"] >= 0 and row["RMSE"] >= 0 for row in slices)


def test_importance_rejects_incomplete_metadata(tmp_path):
    metadata_path = tmp_path / "metadata.json"
    metadata_path.write_text(json.dumps({"feature_names": []}), encoding="utf-8")

    try:
        load_model_native_importance(metadata_path)
    except ValueError as exc:
        assert "top_features" in str(exc)
    else:
        raise AssertionError("Incomplete metadata should be rejected")