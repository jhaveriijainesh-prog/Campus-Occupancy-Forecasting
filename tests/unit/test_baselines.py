"""
Unit Tests for Baseline Forecasting Models (app/forecasting/baseline.py).
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project
"""

import numpy as np
import pandas as pd
import pytest

from app.forecasting.baseline import (
    HistoricalSeasonalProfileBaseline,
    SeasonalLastWeekBaseline,
    StaticTimetableBaseline,
    compute_metrics,
)


@pytest.fixture
def sample_dataset():
    """Create a minimal toy time series for baseline validation."""
    records = []
    base_ts = pd.Timestamp("2026-08-03 08:00:00", tz="UTC")
    for r in ["R1", "R2"]:
        for i in range(48):  # 2 days of hourly data
            ts = base_ts + pd.Timedelta(hours=i)
            dow = ts.strftime("%A")
            h = ts.hour
            is_sched = (9 <= h <= 12)
            records.append({
                "observation_id": f"OBS-{r}-{i}",
                "timestamp": ts,
                "date": str(ts.date()),
                "hour": h,
                "day_of_week": dow,
                "room_id": r,
                "is_scheduled": is_sched,
                "scheduled_enrollment": 50 if is_sched else 0,
                "actual_headcount": 40 if is_sched else 2
            })
    return pd.DataFrame(records)


def test_compute_metrics_accuracy():
    y_true = np.array([10.0, 20.0, 30.0, 40.0])
    y_pred = np.array([12.0, 18.0, 33.0, 37.0])

    metrics = compute_metrics(y_true, y_pred)
    # Residuals: +2, -2, +3, -3 -> MAE = (2+2+3+3)/4 = 2.5
    assert metrics["MAE"] == 2.5
    # Sq errors: 4, 4, 9, 9 -> RMSE = sqrt(26/4) = sqrt(6.5) ≈ 2.5495
    assert abs(metrics["RMSE"] - np.sqrt(6.5)) < 1e-3
    assert metrics["R2"] > 0.90
    assert metrics["WAPE"] == round(10.0 / 100.0, 4)


def test_historical_seasonal_profile_fit_predict(sample_dataset):
    # Split chronologically by timestamp so both rooms R1 and R2 are in train and test
    median_ts = sample_dataset["timestamp"].median()
    train_df = sample_dataset[sample_dataset["timestamp"] <= median_ts].copy()
    test_df = sample_dataset[sample_dataset["timestamp"] > median_ts].copy()

    model = HistoricalSeasonalProfileBaseline(stratify_by_schedule=True)
    model.fit(train_df)
    preds = model.predict(test_df)

    assert len(preds) == len(test_df)
    assert np.all(preds >= 0.0)
    # Check that scheduled slots predict ~40, unscheduled predict ~2
    sched_mask = test_df["is_scheduled"].values
    assert np.mean(preds[sched_mask]) > 30.0
    assert np.mean(preds[~sched_mask]) < 5.0


def test_seasonal_last_week_baseline(sample_dataset):
    model = SeasonalLastWeekBaseline(lag_hours=24)
    model.fit(sample_dataset)
    preds = model.predict(sample_dataset)

    assert len(preds) == len(sample_dataset)
    assert np.all(preds >= 0.0)


def test_static_timetable_baseline(sample_dataset):
    model = StaticTimetableBaseline()
    model.fit(sample_dataset)
    preds = model.predict(sample_dataset)

    assert len(preds) == len(sample_dataset)
    for i, row in sample_dataset.reset_index(drop=True).iterrows():
        if row["is_scheduled"]:
            assert preds[i] == row["scheduled_enrollment"]
        else:
            assert preds[i] == 0.0
