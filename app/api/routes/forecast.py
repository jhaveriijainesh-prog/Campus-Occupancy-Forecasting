"""
Occupancy Forecasting Inference Endpoints.

Provides REST endpoints for occupancy forecasting including:
- Single room forecasts
- Multi-room batch forecasts
- Multi-horizon predictions with confidence intervals
- Model metadata and feature importance
"""

from datetime import datetime, timezone
from functools import lru_cache
import json
from pathlib import Path
from typing import List, Optional

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import ValidationError

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import require_forecast
from app.data.harmonizer import harmonize_sources
from app.forecasting.model import OccupancyForecaster
from app.features.engineering import FeatureEngineer
from app.schemas.forecast import (
    BatchForecastResponse,
    ForecastSchedule,
    ForecastRequest,
    ForecastResponse,
    ModelInfoResponse,
)


router = APIRouter()
logger = get_logger(__name__)

SUPPORTED_HORIZON_HOURS = 1
HORIZON_SEMANTICS = "one_step_ahead_hourly"

# Global model cache
_forecaster: Optional[OccupancyForecaster] = None
_feature_engineer: Optional[FeatureEngineer] = None


@router.get(
    "/schedules",
    response_model=List[ForecastSchedule],
    summary="List scheduled class times for forecast examples",
)
async def list_forecast_schedules(_: str = Depends(require_forecast)):
    """Return the timetable entries used to choose meaningful forecast examples."""
    try:
        timetable_df = _read_processed_frame("timetable")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Processed timetable data is unavailable: {exc}") from exc

    required_columns = {"room_id", "day_of_week", "start_time", "end_time", "enrolled_count"}
    missing = sorted(required_columns.difference(timetable_df.columns))
    if missing:
        raise HTTPException(
            status_code=503,
            detail=f"Processed timetable data is missing required columns: {missing}",
        )

    optional_columns = ["course_code", "course_name"]
    columns = [
        "room_id",
        "day_of_week",
        "start_time",
        "end_time",
        "enrolled_count",
        *[column for column in optional_columns if column in timetable_df.columns],
    ]
    schedules = timetable_df[columns].copy()
    schedules["enrolled_count"] = pd.to_numeric(schedules["enrolled_count"], errors="coerce")
    schedules = schedules.dropna(subset=["room_id", "day_of_week", "start_time", "end_time", "enrolled_count"])
    schedules["enrolled_count"] = schedules["enrolled_count"].astype(int)
    schedules = schedules.sort_values(["day_of_week", "start_time", "room_id"])
    return schedules.astype(object).where(pd.notna(schedules), None).to_dict(orient="records")


def _read_processed_frame(name: str):
    """Read a processed artifact using the repository's Parquet/CSV fallback."""
    settings = get_settings()
    parquet_path = settings.processed_data_dir / f"{name}.parquet"
    csv_path = settings.processed_data_dir / f"{name}.csv"
    if parquet_path.exists():
        path = parquet_path
    elif csv_path.exists():
        path = csv_path
    else:
        raise FileNotFoundError(f"Processed {name} data not found")
    stat = path.stat()
    return _load_processed_frame(str(path.resolve()), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=8)
def _load_processed_frame(path: str, modified_ns: int, size_bytes: int) -> pd.DataFrame:
    """Cache immutable processed tables until their path or file metadata changes."""
    source = Path(path)
    if source.suffix == ".parquet":
        return pd.read_parquet(source)
    return pd.read_csv(source)

def get_forecaster() -> OccupancyForecaster:
    """Get or load the trained forecaster model."""
    global _forecaster
    if _forecaster is None:
        settings = get_settings()
        model_path = settings.experiments_dir / "xgboost"
        if not (model_path / "model.json").exists():
            raise HTTPException(
                status_code=503,
                detail="Model not trained. Run training pipeline first."
            )
        try:
            _forecaster = OccupancyForecaster()
            _forecaster.load(model_path)
        except Exception as exc:
            raise HTTPException(status_code=503, detail=f"Forecast model artifacts are unavailable: {exc}") from exc
    return _forecaster


def get_feature_engineer() -> FeatureEngineer:
    """Get or create the feature engineer."""
    global _feature_engineer
    if _feature_engineer is None:
        settings = get_settings()
        _feature_engineer = FeatureEngineer(forecast_horizon=1)
    return _feature_engineer


@router.post(
    "/predict",
    response_model=BatchForecastResponse,
    summary="Generate occupancy forecasts",
    responses={404: {"description": "One or more requested rooms are unknown"}, 422: {"description": "Invalid request or unsupported horizon"}, 503: {"description": "Forecast data or model artifacts are unavailable"}},
)
async def predict_occupancy(
    request: ForecastRequest,
    _: str = Depends(require_forecast),
):
    """
    Generate occupancy forecasts for specified rooms.

    Args:
        request: Forecast request with room IDs, horizon, and confidence levels

    Returns:
        Batch forecast with predictions and confidence intervals
    """
    if request.horizon_hours != SUPPORTED_HORIZON_HOURS:
        raise HTTPException(
            status_code=422,
            detail=(
                f"This forecast artifact supports only a {SUPPORTED_HORIZON_HOURS}-hour "
                "one-step-ahead horizon"
            ),
        )

    forecaster = get_forecaster()
    feature_engineer = get_feature_engineer()
    settings = get_settings()

    # Load processed data for feature engineering
    occupancy_df = None
    rooms_df = None
    events_df = None

    try:
        occupancy_df = _read_processed_frame("occupancy")
        rooms_df = _read_processed_frame("rooms")
        events_df = _read_processed_frame("events")
        timetable_df = _read_processed_frame("timetable")
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Processed forecast data is unavailable: {exc}") from exc

    # Keep the requested instant for the response, but align inference features
    # to the campus wall clock used by the generated occupancy/timetable data.
    try:
        if request.start_time:
            start_time = pd.Timestamp(request.start_time)
            start_time = start_time.tz_localize("UTC") if start_time.tzinfo is None else start_time.tz_convert("UTC")
        else:
            start_time = pd.Timestamp.now(tz="UTC")
        campus_start_time = start_time.tz_convert(settings.time_zone)
        model_start_time = campus_start_time.tz_localize(None).tz_localize("UTC")
    except (TypeError, ValueError) as exc:
        raise HTTPException(
            status_code=422,
            detail="start_time or configured campus timezone is invalid",
        ) from exc

    required_columns = {"room_id", "timestamp", "capacity", "actual_headcount"}
    for name, frame in (
        ("occupancy", occupancy_df),
        ("rooms", rooms_df),
        ("events", events_df),
        ("timetable", timetable_df),
    ):
        if name == "occupancy" and not required_columns.issubset(frame.columns):
            missing = sorted(required_columns.difference(frame.columns))
            raise HTTPException(status_code=503, detail=f"Processed {name} data is missing required columns: {missing}")
        if "room_id" not in frame.columns and name in {"rooms", "timetable"}:
            raise HTTPException(status_code=503, detail=f"Processed {name} data is missing required column: room_id")
    required_timetable_columns = {"day_of_week", "start_time", "end_time"}
    if not required_timetable_columns.issubset(timetable_df.columns):
        missing = sorted(required_timetable_columns.difference(timetable_df.columns))
        raise HTTPException(status_code=503, detail=f"Processed timetable data is missing required columns: {missing}")

    requested_room_rows = occupancy_df["room_id"].isin(request.room_ids)
    found_rooms = {
        str(room_id)
        for room_id in occupancy_df.loc[requested_room_rows, "room_id"].dropna().unique()
    }
    unknown_rooms = sorted(set(request.room_ids).difference(found_rooms))
    if unknown_rooms:
        raise HTTPException(status_code=404, detail={"unknown_room_ids": unknown_rooms})

    # The one-hour artifact may only use observations available by t-1h.
    requested_occupancy = occupancy_df.loc[requested_room_rows].copy()
    occupancy_timestamps = pd.to_datetime(requested_occupancy["timestamp"], utc=True, errors="coerce")
    if occupancy_timestamps.isna().any():
        raise HTTPException(status_code=503, detail="Processed occupancy data contains invalid timestamps")
    history_cutoff = model_start_time - pd.Timedelta(hours=request.horizon_hours)
    history_mask = occupancy_timestamps.le(history_cutoff)
    available_history = requested_occupancy.loc[history_mask].copy()
    available_history["timestamp"] = occupancy_timestamps.loc[history_mask]

    required_lag_history = max(feature_engineer.lag_hours, default=1) + request.horizon_hours - 1
    required_rolling_history = max(feature_engineer.rolling_windows, default=1) + request.horizon_hours - 1
    history_rows = max(required_lag_history, required_rolling_history)
    available_history = (
        available_history.sort_values("timestamp")
        .groupby("room_id", group_keys=False)
        .tail(history_rows)
    )

    rooms_without_history = sorted(set(request.room_ids).difference(available_history["room_id"].astype(str)))
    if rooms_without_history:
        raise HTTPException(
            status_code=404,
            detail={"rooms_without_causal_history": rooms_without_history},
        )

    latest_history = (
        available_history.sort_values("timestamp")
        .groupby("room_id")
        .tail(1)
        .copy()
    )
    target_rows = latest_history.copy()
    target_rows["timestamp"] = model_start_time
    target_rows["actual_headcount"] = float("nan")
    target_rows["observation_id"] = target_rows["room_id"].map(lambda room_id: f"forecast-{room_id}")
    target_rows["is_imputed"] = 0
    target_rows["was_clamped"] = 0
    target_rows = target_rows.drop(
        columns=["is_scheduled", "scheduled_course_code", "scheduled_enrollment", "timetable_id", "event_type"],
        errors="ignore",
    )

    semester_start = pd.Timestamp(settings.semester_start_date, tz="UTC").date()
    target_date = model_start_time.date()
    target_rows["week_number"] = ((target_date - semester_start).days // 7) + 1

    try:
        target_context = harmonize_sources(target_rows, timetable_df, events_df)
        if "campus_event_type" in target_context:
            target_context["event_type"] = target_context["campus_event_type"].fillna("normal")
        else:
            target_context["event_type"] = "normal"
        target_context["is_holiday"] = target_context["event_type"].eq("holiday")

        model_input = pd.concat([available_history, target_context], ignore_index=True, sort=False)
        all_features = feature_engineer.create_features(model_input, rooms_df, events_df)
        latest_features = all_features[all_features["observation_id"].astype(str).str.startswith("forecast-")].copy()
        latest_features = latest_features.sort_values("room_id").reset_index(drop=True)
        if len(latest_features) != len(request.room_ids):
            raise ValueError("Could not construct one causal forecast row per requested room")
        predictions = forecaster.predict(latest_features)
    except (KeyError, TypeError, ValueError, RuntimeError) as exc:
        raise HTTPException(status_code=503, detail=f"Forecast inference data is invalid or unavailable: {exc}") from exc

    # Build response
    forecasts = []

    for idx, row in latest_features.iterrows():
        room_id = row["room_id"]
        pred = predictions[idx]

        # The current XGBoost artifact is point-estimate only. Keep the interval
        # keys for API compatibility, but do not present fabricated uncertainty.
        intervals = {}
        for cl in request.confidence_levels:
            intervals[f"p{int(cl*100)}"] = float(pred)
        intervals = dict(sorted(intervals.items(), key=lambda item: int(item[0][1:])))
        capacity = pd.to_numeric(pd.Series([row.get("capacity")]), errors="coerce").iloc[0]
        predicted_headcount = max(0.0, float(pred))
        if pd.notna(capacity):
            predicted_headcount = min(predicted_headcount, max(0.0, float(capacity)))
        intervals = {key: predicted_headcount for key in intervals}

        forecasts.append(ForecastResponse(
            room_id=room_id,
            timestamp=start_time.isoformat(),
            horizon_hours=request.horizon_hours,
            predicted_headcount=predicted_headcount,
            is_scheduled=bool(row.get("is_scheduled", 0)),
            scheduled_enrollment=int(row.get("scheduled_enrollment", 0)),
            scheduled_course_code=(
                None
                if pd.isna(row.get("scheduled_course_code"))
                else str(row.get("scheduled_course_code"))
            ),
            prediction_interval=intervals,
            confidence_levels=request.confidence_levels,
            interval_method="point_estimate_only",
            horizon_semantics=HORIZON_SEMANTICS,
            model_version="xgboost-v1",
        ))

    return BatchForecastResponse(
        forecasts=forecasts,
        generated_at=datetime.now(timezone.utc).isoformat(),
        model_version="xgboost-v1",
        total_rooms=len(forecasts),
        horizon_semantics=HORIZON_SEMANTICS,
    )


@router.get(
    "/predict/{room_id}",
    response_model=ForecastResponse,
    summary="Forecast single room",
    responses={404: {"description": "Requested room is unknown"}, 422: {"description": "Invalid request or unsupported horizon"}, 503: {"description": "Forecast data or model artifacts are unavailable"}},
)
async def predict_single_room(
    room_id: str,
    horizon_hours: int = Query(default=1, ge=1, le=168),
    confidence_levels: str = Query(default="0.1,0.5,0.9"),
    start_time: str | None = Query(default=None, description="Forecast target time (ISO 8601)"),
    _: str = Depends(require_forecast),
):
    """
    Generate forecast for a single room.

    Args:
        room_id: Room identifier
        horizon_hours: Forecast horizon in hours
        confidence_levels: Comma-separated confidence levels

    Returns:
        Single room forecast
    """
    try:
        levels = [float(x.strip()) for x in confidence_levels.split(",")]
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="confidence_levels must be comma-separated numbers") from exc
    try:
        request = ForecastRequest(
            room_ids=[room_id],
            horizon_hours=horizon_hours,
            start_time=start_time,
            confidence_levels=levels,
        )
    except ValidationError as exc:
        detail = [
            {key: error[key] for key in ("type", "loc", "msg")}
            for error in exc.errors()
        ]
        raise HTTPException(status_code=422, detail=detail) from exc
    batch_response = await predict_occupancy(request, _)

    if not batch_response.forecasts:
        raise HTTPException(status_code=404, detail=f"No forecast generated for room {room_id}")

    return batch_response.forecasts[0]


@router.get(
    "/model/info",
    response_model=ModelInfoResponse,
    summary="Get model metadata",
    responses={503: {"description": "Forecast model artifacts are unavailable"}},
)
async def get_model_info(_: str = Depends(require_forecast)):
    """
    Get information about the currently loaded forecasting model.

    Returns:
        Model metadata including version, features, and hyperparameters
    """
    forecaster = get_forecaster()
    settings = get_settings()

    model_path = settings.experiments_dir / "xgboost"
    metadata_path = model_path / "feature_metadata.json"

    metadata = {}
    if not metadata_path.exists():
        raise HTTPException(status_code=503, detail="Forecast model metadata is unavailable")
    try:
        with open(metadata_path, encoding="utf-8") as f:
            metadata = json.load(f)
    except (OSError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=503, detail=f"Forecast model metadata is unavailable: {exc}") from exc
    if not isinstance(metadata, dict):
        raise HTTPException(status_code=503, detail="Forecast model metadata must be a JSON object")

    return ModelInfoResponse(
        model_type=metadata.get("model_type", "XGBRegressor"),
        version="1.0.0",
        trained_at=metadata.get("trained_at", "unknown"),
        best_iteration=metadata.get("best_iteration"),
        feature_count=len(forecaster.feature_names_),
        top_features=forecaster.get_feature_importances(),
        hyperparameters=metadata.get("params", {}),
        supported_horizon_hours=SUPPORTED_HORIZON_HOURS,
    )


@router.get("/model/features", summary="Get feature importance")
async def get_feature_importance(_: str = Depends(require_forecast)):
    """
    Get feature importance rankings from the trained model.

    Returns:
        Dictionary of feature names and their importance scores
    """
    forecaster = get_forecaster()
    return {
        "feature_importances": forecaster.get_feature_importances(),
        "feature_count": len(forecaster.feature_names_),
        "categorical_features": forecaster.categorical_features_,
    }
