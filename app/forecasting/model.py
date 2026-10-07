"""
BDS-06: Advanced XGBoost Occupancy Forecasting Model
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Provides an advanced, production-grade gradient boosting forecaster:
  - Built with XGBoost (Hist gradient boosted regression trees)
  - Native categorical feature handling
  - Early stopping against chronological validation partition
  - Causal, leakage-free feature matrix ingestion
  - Model serialization, feature attribution & metadata tracking
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

import numpy as np
import pandas as pd
import xgboost as xgb

from app.forecasting.baseline import compute_metrics


class OccupancyForecaster:
    """Advanced gradient boosting forecaster for university campus occupancy."""

    DEFAULT_PARAMS: Dict[str, Any] = {
        "n_estimators": 500,
        "learning_rate": 0.05,
        "max_depth": 6,
        "subsample": 0.8,
        "colsample_bytree": 0.8,
        "min_child_weight": 3,
        "tree_method": "hist",
        "objective": "reg:squarederror",
        "eval_metric": "mae",
        "random_state": 42,
        "n_jobs": -1,
    }

    CATEGORICAL_COLUMNS: List[str] = [
        "room_id",
        "building_id",
        "room_type",
    ]

    def __init__(
        self,
        params: Optional[Dict[str, Any]] = None,
        random_seed: int = 42
    ):
        self.params = dict(self.DEFAULT_PARAMS)
        if params:
            self.params.update(params)
        self.params["random_state"] = random_seed
        self.random_seed = random_seed

        self.model_: Optional[xgb.XGBRegressor] = None
        self.feature_names_: List[str] = []
        self.categorical_features_: List[str] = []
        self.best_iteration_: Optional[int] = None

    def _prepare_matrix(
        self,
        df: pd.DataFrame,
        feature_cols: List[str],
        is_train: bool = False
    ) -> pd.DataFrame:
        """
        Prepare feature matrix: ensure exact column alignment and categorical dtypes.
        Does not alter or fit statistics on test data.
        """
        X = df[feature_cols].copy()

        # Convert every string feature to pandas category for native XGBoost support.
        categorical_columns = set(self.CATEGORICAL_COLUMNS)
        categorical_columns.update(
            column
            for column in X.columns
            if pd.api.types.is_string_dtype(X[column].dtype)
        )
        for cat_col in categorical_columns.intersection(X.columns):
            X[cat_col] = X[cat_col].astype("category")

        # Convert booleans to integers
        for c in X.columns:
            if X[c].dtype == bool:
                X[c] = X[c].astype(int)

        return X

    def fit(
        self,
        train_df: pd.DataFrame,
        feature_cols: List[str],
        target_col: str = "actual_headcount",
        val_df: Optional[pd.DataFrame] = None,
        early_stopping_rounds: int = 30
    ) -> "OccupancyForecaster":
        """
        Train XGBoost model using chronological training and validation partitions.

        Args:
            train_df: Chronological training partition.
            feature_cols: List of valid explanatory feature column names.
            target_col: Name of target variable column.
            val_df: Optional chronological validation partition for early stopping.
            early_stopping_rounds: Early stopping patience.
        """
        self.feature_names_ = list(feature_cols)
        self.categorical_features_ = [
            column
            for column in self.feature_names_
            if column in self.CATEGORICAL_COLUMNS
            or pd.api.types.is_string_dtype(train_df[column].dtype)
        ]

        X_train = self._prepare_matrix(train_df, self.feature_names_, is_train=True)
        y_train = train_df[target_col].values.astype(np.float64)

        self.model_ = xgb.XGBRegressor(
            enable_categorical=True,
            early_stopping_rounds=early_stopping_rounds if val_df is not None else None,
            **self.params
        )

        eval_set = [(X_train, y_train)]
        if val_df is not None:
            X_val = self._prepare_matrix(val_df, self.feature_names_, is_train=False)
            y_val = val_df[target_col].values.astype(np.float64)
            eval_set.append((X_val, y_val))

        self.model_.fit(
            X_train,
            y_train,
            eval_set=eval_set,
            verbose=False
        )

        if val_df is not None and hasattr(self.model_, "best_iteration"):
            self.best_iteration_ = int(self.model_.best_iteration)

        return self

    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Generate predicted headcounts, clamped to physically non-negative values."""
        if self.model_ is None:
            raise RuntimeError("Model has not been trained yet. Call fit() first.")

        X = self._prepare_matrix(df, self.feature_names_, is_train=False)
        raw_preds = self.model_.predict(X)

        # Enforce physical non-negativity constraint
        clamped_preds = np.maximum(0.0, raw_preds)

        # Enforce room capacity ceiling if capacity column is present
        if "capacity" in df.columns:
            capacities = df["capacity"].values.astype(np.float64)
            clamped_preds = np.minimum(clamped_preds, capacities)

        return clamped_preds

    def get_feature_importances(self) -> Dict[str, float]:
        """Return normalized feature importances (gain-based)."""
        if self.model_ is None:
            raise RuntimeError("Model has not been trained yet.")

        booster = self.model_.get_booster()
        score_dict = booster.get_score(importance_type="gain")
        total_score = sum(score_dict.values()) if score_dict else 1.0

        # Map to all features (including 0.0 for unused)
        importances = {}
        for f in self.feature_names_:
            raw_gain = score_dict.get(f, 0.0)
            importances[f] = round(raw_gain / total_score, 6) if total_score > 0 else 0.0

        # Sort descending by importance
        return dict(sorted(importances.items(), key=lambda item: item[1], reverse=True))

    def save(self, output_dir: Union[str, Path]) -> Dict[str, str]:
        """Serialize trained model and feature metadata to directory."""
        if self.model_ is None:
            raise RuntimeError("Cannot save untrained model.")

        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)

        model_file = out_path / "model.json"
        self.model_.save_model(str(model_file))

        metadata = {
            "model_type": "XGBRegressor",
            "random_seed": self.random_seed,
            "best_iteration": self.best_iteration_,
            "feature_names": self.feature_names_,
            "categorical_features": self.categorical_features_,
            "params": {k: v for k, v in self.params.items() if isinstance(v, (int, float, str, bool))},
            "top_features": dict(list(self.get_feature_importances().items())[:15]),
        }

        meta_file = out_path / "feature_metadata.json"
        with open(meta_file, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2)

        return {
            "model_path": str(model_file),
            "metadata_path": str(meta_file),
        }

    def load(self, model_dir: Union[str, Path]) -> "OccupancyForecaster":
        """Load trained model and feature metadata from directory."""
        in_path = Path(model_dir)
        model_file = in_path / "model.json"
        meta_file = in_path / "feature_metadata.json"

        if not model_file.exists() or not meta_file.exists():
            raise FileNotFoundError(f"Model artifacts not found in {model_dir}")

        with open(meta_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)

        self.feature_names_ = metadata["feature_names"]
        self.categorical_features_ = metadata.get("categorical_features", [])
        self.random_seed = metadata.get("random_seed", 42)
        self.best_iteration_ = metadata.get("best_iteration")

        self.model_ = xgb.XGBRegressor()
        self.model_.load_model(str(model_file))

        return self
