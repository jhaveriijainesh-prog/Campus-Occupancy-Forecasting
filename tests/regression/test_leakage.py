"""
Regression & Automated Leakage Prevention Test Suite
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project
Test Target: app/features/engineering.py (FeatureEngineer)

Guarantees:
  1. Causal lag invariance: feature at t depends ONLY on past observations (<= t - H).
  2. Perturbation isolation: altering target at t has ZERO effect on features at t.
  3. Rolling window exclusion: rolling statistics at t exclude observation y_t.
  4. Spatial room isolation: room A's features are independent of room B.
  5. Strict chronological split: max(train) < min(val) < min(test).
"""

from datetime import datetime, timedelta

import numpy as np
import pandas as pd
import pytest

from app.features.engineering import FeatureEngineer


@pytest.fixture
def synthetic_time_series():
    """Create a minimal, controlled 2-room, 100-hour synthetic sequence."""
    records = []
    base_ts = datetime(2026, 8, 3, 0, 0, 0)
    for room_id in ["R101", "R102"]:
        for h in range(100):
            ts = base_ts + timedelta(hours=h)
            records.append({
                "observation_id": f"OBS-{room_id}-{h:03d}",
                "timestamp": ts.isoformat() + "Z",
                "date": ts.date().isoformat(),
                "hour": ts.hour,
                "day_of_week": ts.strftime("%A"),
                "room_id": room_id,
                "capacity": 100 if room_id == "R101" else 50,
                "is_scheduled": True if 9 <= ts.hour <= 16 else False,
                "scheduled_enrollment": 70 if room_id == "R101" else 35,
                "actual_headcount": (h * 2) if room_id == "R101" else (h * 5),
                "is_holiday": False,
                "event_type": "normal",
                "anomaly_flag": "none"
            })
    return pd.DataFrame(records)


def test_temporal_split_chronological_boundaries(synthetic_time_series):
    """Assert train, validation, and test splits have strict disjoint temporal boundaries."""
    fe = FeatureEngineer(forecast_horizon=1)
    feat_df = fe.create_features(synthetic_time_series)

    train, val, test = fe.temporal_split(
        feat_df,
        train_end_date="2026-08-04",
        val_end_date="2026-08-05"
    )

    assert not train.empty
    assert not val.empty
    assert not test.empty

    train_max = train["timestamp"].max()
    val_min = val["timestamp"].min()
    val_max = val["timestamp"].max()
    test_min = test["timestamp"].min()

    assert train_max < val_min, f"Temporal leakage: train_max ({train_max}) >= val_min ({val_min})"
    assert val_max < test_min, f"Temporal leakage: val_max ({val_max}) >= test_min ({test_min})"


def test_lag_causality_exact_antecedent_alignment(synthetic_time_series):
    """Assert that lag_1h at timestamp t equals exactly actual_headcount at timestamp (t - 1)."""
    fe = FeatureEngineer(forecast_horizon=1)
    feat_df = fe.create_features(synthetic_time_series)

    # For room R101, row at index i (where i >= 1) must have lag_1h == actual_headcount of row (i - 1)
    r101_df = feat_df[feat_df["room_id"] == "R101"].sort_values("timestamp").reset_index(drop=True)

    for i in range(1, len(r101_df)):
        expected_lag1 = r101_df.loc[i - 1, "actual_headcount"]
        actual_lag1 = r101_df.loc[i, "lag_1h"]
        assert actual_lag1 == expected_lag1, (
            f"Lag leakage/mismatch at step {i}: lag_1h={actual_lag1}, expected={expected_lag1}"
        )


def test_rolling_statistics_exclude_current_target(synthetic_time_series):
    """
    CRITICAL PERTURBATION TEST:
    Artificially modifying target y_t at time t must produce ZERO difference
    in any feature calculated for time t (including rolling means and lags).
    If a rolling mean changes when y_t changes, lookahead leakage is proven.
    """
    fe = FeatureEngineer(forecast_horizon=1)

    # 1. Base run
    feat_base = fe.create_features(synthetic_time_series)
    target_idx = 30  # Arbitrary row index
    target_room = synthetic_time_series.loc[target_idx, "room_id"]
    target_ts = synthetic_time_series.loc[target_idx, "timestamp"]

    orig_rolling_mean = feat_base.loc[target_idx, "rolling_mean_4h"]
    orig_lag1 = feat_base.loc[target_idx, "lag_1h"]

    # 2. Perturb actual_headcount at target_idx by +10,000
    perturbed_df = synthetic_time_series.copy()
    perturbed_df.loc[target_idx, "actual_headcount"] += 10000

    feat_perturbed = fe.create_features(perturbed_df)
    new_rolling_mean = feat_perturbed.loc[target_idx, "rolling_mean_4h"]
    new_lag1 = feat_perturbed.loc[target_idx, "lag_1h"]

    # Invariant: Features at time t must be completely invariant to changes in y_t
    assert new_rolling_mean == orig_rolling_mean, (
        f"LEAKAGE DETECTED: rolling_mean_4h changed from {orig_rolling_mean} to {new_rolling_mean} "
        f"when target y_t was perturbed!"
    )
    assert new_lag1 == orig_lag1, (
        f"LEAKAGE DETECTED: lag_1h changed from {orig_lag1} to {new_lag1} when target y_t was perturbed!"
    )


def test_forecast_horizon_shift_protection(synthetic_time_series):
    """
    When forecast_horizon = 24 (day-ahead prediction),
    the most immediate lag feature must be at least (t - 24).
    Observations from (t - 23) to t must NEVER be present.
    """
    h = 24
    fe = FeatureEngineer(forecast_horizon=h)
    feat_df = fe.create_features(synthetic_time_series)

    r101_df = feat_df[feat_df["room_id"] == "R101"].sort_values("timestamp").reset_index(drop=True)

    # At row 25, lag_1h corresponds to lag_1 with effective shift: 1 + (24 - 1) = 24
    for i in range(24, len(r101_df)):
        expected_lag = r101_df.loc[i - 24, "actual_headcount"]
        actual_lag = r101_df.loc[i, "lag_1h"]
        assert actual_lag == expected_lag, (
            f"Horizon shift error at index {i}: actual={actual_lag}, expected={expected_lag}"
        )


def test_room_spatial_isolation(synthetic_time_series):
    """Assert that room A's lags and rolling statistics are never computed from room B's data."""
    fe = FeatureEngineer(forecast_horizon=1)
    feat_df = fe.create_features(synthetic_time_series)

    # Row 0 of room R102 must have NaN for lag_1h (first observation of that room),
    # not the last observation of room R101!
    r102_first_row = feat_df[feat_df["room_id"] == "R102"].iloc[0]
    assert pd.isna(r102_first_row["lag_1h"]), (
        f"Spatial leakage: First row of room R102 inherited lag '{r102_first_row['lag_1h']}' from previous room!"
    )
