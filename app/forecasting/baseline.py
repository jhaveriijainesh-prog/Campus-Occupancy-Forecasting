"""
BDS-06: Baseline Forecasting Engine
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Provides interpretable, seasonal, and heuristic baselines for campus occupancy:
  1. HistoricalSeasonalProfileBaseline (Primary Champion Baseline: Room x DOW x Hour Mean)
  2. SeasonalLastWeekBaseline (Weekly Naive Lag: y_{t-168})
  3. StaticTimetableBaseline (Administrative Enrollment Rule)
"""

from typing import Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd


def compute_metrics(y_true: Union[pd.Series, np.ndarray], y_pred: Union[pd.Series, np.ndarray]) -> Dict[str, float]:
    """
    Compute standard forecasting evaluation metrics.

    Calculates:
      - MAE: Mean Absolute Error
      - RMSE: Root Mean Squared Error
      - R2: Coefficient of Determination
      - WAPE: Weighted Absolute Percentage Error (preferred for counts with zeros)
      - Mean Absolute Percentage Error (sMAPE)
    """
    y_t = np.asarray(y_true, dtype=np.float64)
    y_p = np.asarray(y_pred, dtype=np.float64)

    # Clamping predictions to physically non-negative values
    y_p = np.maximum(y_p, 0.0)

    # Residuals
    diff = y_t - y_p
    abs_err = np.abs(diff)
    sq_err = diff ** 2

    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(sq_err)))

    # R-squared (variance explained)
    total_ss = np.sum((y_t - np.mean(y_t)) ** 2)
    residual_ss = np.sum(sq_err)
    if total_ss > 1e-9:
        r2 = float(1.0 - (residual_ss / total_ss))
    else:
        r2 = 0.0

    # WAPE (sum of abs error / sum of actuals)
    actual_sum = np.sum(y_t)
    if actual_sum > 1e-9:
        wape = float(np.sum(abs_err) / actual_sum)
    else:
        wape = 0.0

    # sMAPE
    denominator = (np.abs(y_t) + np.abs(y_p)) / 2.0
    valid_idx = denominator > 1e-6
    if np.any(valid_idx):
        smape = float(np.mean(abs_err[valid_idx] / denominator[valid_idx])) * 100.0
    else:
        smape = 0.0

    return {
        "MAE": round(mae, 4),
        "RMSE": round(rmse, 4),
        "R2": round(r2, 4),
        "WAPE": round(wape, 4),
        "sMAPE": round(smape, 4),
    }


class HistoricalSeasonalProfileBaseline:
    """
    Primary Heuristic Baseline: Room x Day-of-Week x Hour Historical Stratified Mean.

    Concept:
      Calculates the historical average occupancy for every specific room, day of the week,
      and hour of the day observed strictly in the training partition.
      Smooths single-week anomalies and provides a robust, interpretable seasonal expectation.
    """

    def __init__(self, stratify_by_schedule: bool = True):
        self.stratify_by_schedule = stratify_by_schedule
        self.profile_lookup_: Dict[Tuple, float] = {}
        self.fallback_room_hour_: Dict[Tuple[str, int], float] = {}
        self.fallback_room_: Dict[str, float] = {}
        self.global_mean_: float = 0.0

    def fit(self, train_df: pd.DataFrame, target_col: str = "actual_headcount") -> "HistoricalSeasonalProfileBaseline":
        """Fit seasonal profile strictly on historical training observations."""
        df = train_df.copy()
        y = df[target_col].astype(float)
        self.global_mean_ = float(y.mean())

        # Fallback 1: Room-level mean
        self.fallback_room_ = df.groupby("room_id")[target_col].mean().to_dict()

        # Fallback 2: Room x Hour mean
        self.fallback_room_hour_ = df.groupby(["room_id", "hour"])[target_col].mean().to_dict()

        # Primary profile: Room x Day-of-Week x Hour (and optional is_scheduled)
        if self.stratify_by_schedule and "is_scheduled" in df.columns:
            group_cols = ["room_id", "day_of_week", "hour", "is_scheduled"]
        else:
            group_cols = ["room_id", "day_of_week", "hour"]

        grouped = df.groupby(group_cols)[target_col].mean()
        self.profile_lookup_ = grouped.to_dict()

        return self

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        """Generate point forecasts for target timestamps."""
        preds = []

        for _, row in test_df.iterrows():
            r_id = str(row["room_id"])
            dow = str(row["day_of_week"])
            h = int(row["hour"])

            if self.stratify_by_schedule and "is_scheduled" in test_df.columns:
                sched = int(row["is_scheduled"])
                key = (r_id, dow, h, sched)
            else:
                key = (r_id, dow, h)

            # Hierarchical lookup with fallbacks
            if key in self.profile_lookup_:
                val = self.profile_lookup_[key]
            elif (r_id, h) in self.fallback_room_hour_:
                val = self.fallback_room_hour_[(r_id, h)]
            elif r_id in self.fallback_room_:
                val = self.fallback_room_[r_id]
            else:
                val = self.global_mean_

            preds.append(max(0.0, val))

        return np.array(preds, dtype=np.float64)


class SeasonalLastWeekBaseline:
    """
    Weekly Naive Baseline: Same-Day-Same-Hour Last Week Lag (y_{t - 168}).

    Concept:
      Assumes occupancy today at 10:00 AM matches exactly what was observed
      in the identical room 7 days (168 hours) ago.
    """

    def __init__(self, lag_hours: int = 168):
        self.lag_hours = lag_hours
        self.historical_map_: Dict[Tuple[str, pd.Timestamp], float] = {}
        self.fallback_room_hour_: Dict[Tuple[str, int], float] = {}
        self.global_mean_: float = 0.0

    def fit(self, train_df: pd.DataFrame, target_col: str = "actual_headcount") -> "SeasonalLastWeekBaseline":
        """Store historical time series observations for lag lookup."""
        df = train_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        self.global_mean_ = float(df[target_col].mean())
        self.fallback_room_hour_ = df.groupby(["room_id", "hour"])[target_col].mean().to_dict()

        # Build fast lookup map: (room_id, timestamp) -> actual_headcount
        for _, row in df.iterrows():
            self.historical_map_[(str(row["room_id"]), row["timestamp"])] = float(row[target_col])

        return self

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        """Lookup observation from exactly lag_hours prior; fallback if outside training set."""
        df = test_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        preds = []

        delta = pd.Timedelta(hours=self.lag_hours)

        for _, row in df.iterrows():
            r_id = str(row["room_id"])
            target_ts = row["timestamp"]
            prior_ts = target_ts - delta
            key = (r_id, prior_ts)

            if key in self.historical_map_:
                val = self.historical_map_[key]
            else:
                # Fallback to room x hour mean
                h = int(row["hour"])
                val = self.fallback_room_hour_.get((r_id, h), self.global_mean_)

            preds.append(max(0.0, val))

        return np.array(preds, dtype=np.float64)


class StaticTimetableBaseline:
    """
    Administrative Baseline: Timetable Scheduled Enrollment.

    Concept:
      Assumes occupancy equals the enrolled course strength if booked, and 0 otherwise.
    """

    def fit(self, train_df: pd.DataFrame, target_col: str = "actual_headcount") -> "StaticTimetableBaseline":
        """No statistical parameter estimation required."""
        return self

    def predict(self, test_df: pd.DataFrame) -> np.ndarray:
        """Return scheduled_enrollment when is_scheduled is True, else 0."""
        preds = []
        for _, row in test_df.iterrows():
            is_sched = bool(row.get("is_scheduled", False))
            if is_sched:
                enroll = float(row.get("scheduled_enrollment", 0))
                preds.append(enroll)
            else:
                preds.append(0.0)
        return np.array(preds, dtype=np.float64)
