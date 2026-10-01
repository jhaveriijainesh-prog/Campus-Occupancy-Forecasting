"""
Unit Tests for Advanced XGBoost Forecaster (app/forecasting/model.py).
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project
"""

import numpy as np
import pandas as pd
import pytest

from app.forecasting.model import OccupancyForecaster


@pytest.fixture
def toy_data():
    """Create a minimal toy dataframe with categorical and numeric features."""
    np.random.seed(42)
    n = 60
    return pd.DataFrame({
        "room_id": np.random.choice(["R101", "R102"], size=n),
        "building_id": np.random.choice(["B01", "B02"], size=n),
        "room_type": np.random.choice(["Lecture Hall", "Computer Lab"], size=n),
        "hour": np.random.randint(8, 18, size=n),
        "day_of_week": np.random.randint(0, 6, size=n),
        "is_scheduled": np.random.choice([0, 1], size=n),
        "capacity": 100,
        "actual_headcount": np.random.randint(0, 80, size=n).astype(float)
    })


def test_forecaster_fit_and_predict(toy_data):
    feature_cols = ["room_id", "building_id", "room_type", "hour", "day_of_week", "is_scheduled", "capacity"]
    forecaster = OccupancyForecaster(params={"n_estimators": 10, "max_depth": 3})

    forecaster.fit(train_df=toy_data, feature_cols=feature_cols, target_col="actual_headcount")
    preds = forecaster.predict(toy_data)

    assert len(preds) == len(toy_data)
    assert np.all(preds >= 0.0)
    assert np.all(preds <= 100.0)  # Clamped to capacity


def test_forecaster_save_and_load(toy_data, tmp_path):
    feature_cols = ["room_id", "building_id", "room_type", "hour", "day_of_week", "is_scheduled", "capacity"]
    forecaster = OccupancyForecaster(params={"n_estimators": 10, "max_depth": 3})
    forecaster.fit(train_df=toy_data, feature_cols=feature_cols, target_col="actual_headcount")

    preds_before = forecaster.predict(toy_data)

    # Save
    forecaster.save(tmp_path)
    assert (tmp_path / "model.json").exists()
    assert (tmp_path / "feature_metadata.json").exists()

    # Load
    loaded = OccupancyForecaster()
    loaded.load(tmp_path)
    preds_after = loaded.predict(toy_data)

    np.testing.assert_allclose(preds_before, preds_after, rtol=1e-5)


def test_feature_importances(toy_data):
    feature_cols = ["room_id", "building_id", "room_type", "hour", "day_of_week", "is_scheduled", "capacity"]
    forecaster = OccupancyForecaster(params={"n_estimators": 10, "max_depth": 3})
    forecaster.fit(train_df=toy_data, feature_cols=feature_cols, target_col="actual_headcount")

    importances = forecaster.get_feature_importances()
    assert len(importances) == len(feature_cols)
    assert all(isinstance(v, float) for v in importances.values())
    assert sum(importances.values()) > 0.0
