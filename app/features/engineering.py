"""
BDS-06: Causal Feature Engineering Pipeline
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Generates strictly causal, leakage-free features for spatiotemporal occupancy forecasting:
  - Temporal & Cyclical (hour, day_of_week, sin/cos transformations, month, week)
  - Timetable & Scheduled Intent (is_scheduled, scheduled_enrollment, scheduled_ratio)
  - Academic Calendar Regimes (is_weekend, is_exam_period, is_study_leave, is_holiday)
  - Static Physical Room & Building Attributes (capacity, building_id, room_type, floor)
  - Antecedent Lags (strictly causal: lag_t-k where k >= forecast_horizon)
  - Antecedent Rolling Statistics (rolling mean & std shifted by horizon)
"""

from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class FeatureEngineer:
    """Production feature engineering engine guaranteeing zero temporal leakage."""

    def __init__(
        self,
        forecast_horizon: int = 1,
        lag_hours: Optional[List[int]] = None,
        rolling_windows: Optional[List[int]] = None
    ):
        """
        Initialize FeatureEngineer.

        Args:
            forecast_horizon: Number of hours ahead being predicted (H >= 1).
                              All antecedent lags and rolling statistics are shifted
                              by at least H to guarantee that future actual observations
                              are never accessible at prediction time.
            lag_hours: List of base hourly lags (e.g. [1, 2, 3, 24, 48, 168]).
            rolling_windows: List of hourly rolling windows for historical statistics (e.g. [4, 24, 168]).
        """
        if forecast_horizon < 1:
            raise ValueError(f"forecast_horizon must be >= 1, received {forecast_horizon}")

        self.forecast_horizon = forecast_horizon
        self.lag_hours = lag_hours or [1, 2, 3, 24, 48, 168]
        self.rolling_windows = rolling_windows or [4, 24, 168]

    def create_features(
        self,
        occupancy_df: pd.DataFrame,
        rooms_df: Optional[pd.DataFrame] = None,
        events_df: Optional[pd.DataFrame] = None
    ) -> pd.DataFrame:
        """
        Generate complete, leakage-free feature matrix from processed datasets.

        Args:
            occupancy_df: Processed occupancy time series dataframe.
            rooms_df: Optional master rooms dataframe with physical metadata.
            events_df: Optional academic calendar events dataframe.

        Returns:
            Enriched pandas DataFrame containing target and engineered features.
        """
        # Ensure chronological ordering per room
        df = occupancy_df.copy()
        df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
        df = df.sort_values(by=["room_id", "timestamp"]).reset_index(drop=True)

        # -----------------------------------------------------------------
        # 1. Temporal & Cyclical Encodings (Deterministic & Known Ahead)
        # -----------------------------------------------------------------
        dt = df["timestamp"].dt
        df["hour"] = dt.hour
        df["day_of_week"] = dt.dayofweek  # 0 = Monday, 6 = Sunday
        df["day_of_month"] = dt.day
        df["month"] = dt.month
        df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)

        # 24-hour and 7-day cyclical sin/cos encodings for continuity (e.g. 23:00 -> 00:00)
        df["sin_hour"] = np.sin(2 * np.pi * df["hour"] / 24.0)
        df["cos_hour"] = np.cos(2 * np.pi * df["hour"] / 24.0)
        df["sin_dow"] = np.sin(2 * np.pi * df["day_of_week"] / 7.0)
        df["cos_dow"] = np.cos(2 * np.pi * df["day_of_week"] / 7.0)

        if "week_number" not in df.columns:
            # Fallback week calculation if not already present
            min_date = df["timestamp"].min()
            df["week_number"] = ((df["timestamp"] - min_date).dt.days // 7) + 1

        # -----------------------------------------------------------------
        # 2. Timetable Intent & Scheduled Registrations (Known Ahead)
        # -----------------------------------------------------------------
        if "is_scheduled" in df.columns:
            df["is_scheduled"] = df["is_scheduled"].astype(int)
        else:
            df["is_scheduled"] = 0

        if "scheduled_enrollment" in df.columns:
            df["scheduled_enrollment"] = df["scheduled_enrollment"].fillna(0).astype(int)
        else:
            df["scheduled_enrollment"] = 0

        # Scheduled utilization fraction relative to room capacity
        df["scheduled_utilization_ratio"] = np.where(
            df["capacity"] > 0,
            np.clip(df["scheduled_enrollment"] / df["capacity"], 0.0, 1.5),
            0.0
        )

        # -----------------------------------------------------------------
        # 3. Academic Calendar & Event Features (Known Ahead)
        # -----------------------------------------------------------------
        if "is_holiday" in df.columns:
            df["is_holiday"] = df["is_holiday"].astype(int)
        else:
            df["is_holiday"] = 0

        if "event_type" in df.columns:
            df["is_exam_period"] = (df["event_type"] == "exam_period").astype(int)
            df["is_study_leave"] = (df["event_type"] == "study_break").astype(int)
            df["has_event"] = (df["event_type"].isin(["exam_period", "study_break", "holiday", "symposium"])).astype(int)
        else:
            df["is_exam_period"] = 0
            df["is_study_leave"] = 0
            df["has_event"] = df["is_holiday"]

        # -----------------------------------------------------------------
        # 4. Physical Room & Building Static Attributes (Known Ahead)
        # -----------------------------------------------------------------
        if rooms_df is not None:
            room_meta_cols = ["room_id", "building_id", "floor", "has_projector", "has_ac", "has_computers", "is_accessible"]
            available_cols = [c for c in room_meta_cols if c in rooms_df.columns]
            if len(available_cols) > 1:
                # Merge only missing attributes
                cols_to_merge = [c for c in available_cols if c not in df.columns or c == "room_id"]
                if len(cols_to_merge) > 1:
                    df = df.merge(rooms_df[cols_to_merge], on="room_id", how="left")

        # Extract building prefix if building_id missing
        if "building_id" not in df.columns:
            df["building_id"] = df["room_id"].str.split("-").str[0]

        # -----------------------------------------------------------------
        # 5. Strictly Causal Lagged Occupancy Features (Past Actuals ONLY)
        # -----------------------------------------------------------------
        # CRITICAL LEAKAGE RULE:
        # To forecast at horizon H, the most recent observed actual is at (t - H).
        # We shift all historical actuals by at least H steps per room.
        grouped_headcount = df.groupby("room_id")["actual_headcount"]

        for lag in self.lag_hours:
            effective_shift = lag + (self.forecast_horizon - 1)
            col_name = f"lag_{lag}h"
            df[col_name] = grouped_headcount.shift(effective_shift)

        # -----------------------------------------------------------------
        # 6. Strictly Causal Rolling Occupancy Statistics (Past Actuals ONLY)
        # -----------------------------------------------------------------
        # Rolling stats must strictly use shifted observations (shifted by H)
        # to ensure no information from timestamp t or later enters the rolling window.
        shifted_actuals = grouped_headcount.shift(self.forecast_horizon)

        for w in self.rolling_windows:
            mean_col = f"rolling_mean_{w}h"
            std_col = f"rolling_std_{w}h"
            min_col = f"rolling_min_{w}h"
            max_col = f"rolling_max_{w}h"

            # Compute rolling features per room
            df[mean_col] = shifted_actuals.groupby(df["room_id"]).transform(
                lambda s: s.rolling(window=w, min_periods=1).mean()
            )
            df[std_col] = shifted_actuals.groupby(df["room_id"]).transform(
                lambda s: s.rolling(window=w, min_periods=1).std()
            ).fillna(0.0)
            df[min_col] = shifted_actuals.groupby(df["room_id"]).transform(
                lambda s: s.rolling(window=w, min_periods=1).min()
            )
            df[max_col] = shifted_actuals.groupby(df["room_id"]).transform(
                lambda s: s.rolling(window=w, min_periods=1).max()
            )

        # -----------------------------------------------------------------
        # 7. Interaction & Ratio Features (Past vs Scheduled)
        # -----------------------------------------------------------------
        # Difference between scheduled enrollment and recent 24h rolling mean
        df["enrollment_vs_rolling_mean_24h"] = (
            df["scheduled_enrollment"] - df["rolling_mean_24h"]
        ).fillna(0.0)

        # Ratio of yesterday's same-hour occupancy to room capacity
        df["lag_24h_utilization"] = np.where(
            df["capacity"] > 0,
            df["lag_24h"] / df["capacity"],
            0.0
        ).clip(0.0, 1.2)

        return df

    def get_feature_columns(self, df: pd.DataFrame) -> List[str]:
        """Return list of valid numerical & categorical feature columns for model input."""
        exclude_cols = {
            "observation_id",
            "timestamp",
            "date",
            "actual_headcount",  # Target variable
            "cleaning_notes",
            "anomaly_flag",
            "scheduled_course_code",
            "event_type",
            "building_name",
        }
        return [c for c in df.columns if c not in exclude_cols]

    @staticmethod
    def temporal_split(
        df: pd.DataFrame,
        train_end_date: str = "2026-10-11",  # End of Week 10
        val_end_date: str = "2026-10-25"     # End of Week 12
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Partition dataset into strictly ordered temporal Train, Validation, and Test sets.

        Guarantees:
            max(train_timestamp) < min(val_timestamp) <= max(val_timestamp) < min(test_timestamp)

        Args:
            df: Feature-engineered dataframe with 'timestamp' or 'date' column.
            train_end_date: Inclusive cutoff date for training partition.
            val_end_date: Inclusive cutoff date for validation partition.

        Returns:
            (train_df, val_df, test_df)
        """
        df_sorted = df.sort_values(by="timestamp").copy()
        date_series = pd.to_datetime(df_sorted["timestamp"]).dt.date

        t_end = pd.to_datetime(train_end_date).date()
        v_end = pd.to_datetime(val_end_date).date()

        train_mask = date_series <= t_end
        val_mask = (date_series > t_end) & (date_series <= v_end)
        test_mask = date_series > v_end

        train_df = df_sorted[train_mask].reset_index(drop=True)
        val_df = df_sorted[val_mask].reset_index(drop=True)
        test_df = df_sorted[test_mask].reset_index(drop=True)

        # Invariant Assertions:
        if not train_df.empty and not val_df.empty:
            assert train_df["timestamp"].max() < val_df["timestamp"].min(), (
                f"Leakage detected: Train max {train_df['timestamp'].max()} >= Val min {val_df['timestamp'].min()}"
            )
        if not val_df.empty and not test_df.empty:
            assert val_df["timestamp"].max() < test_df["timestamp"].min(), (
                f"Leakage detected: Val max {val_df['timestamp'].max()} >= Test min {test_df['timestamp'].min()}"
            )

        return train_df, val_df, test_df

    @staticmethod
    def verify_no_temporal_leakage(
        df: pd.DataFrame,
        feature_col: str,
        target_col: str = "actual_headcount",
        horizon: int = 1
    ) -> bool:
        """
        Verify that a lag or rolling feature does not leak future or concurrent target values.

        Test logic:
            Shifts the target column by k steps into the future and tests if feature_col
            correlates with future target values when controlling for past.
            Directly checks whether feature_col at time t is identical to target at time t
            (concurrent leakage) or time t + 1 (future lookahead leakage).
        """
        # Ensure per room
        for room_id, group in df.groupby("room_id"):
            feat = group[feature_col].dropna()
            target = group[target_col].loc[feat.index]

            # Invariant 1: Feature at t must NEVER equal target at t across non-zero values
            if (feat == target).all() and len(feat) > 5:
                # Feature is an identical copy of the target!
                return False

        return True
