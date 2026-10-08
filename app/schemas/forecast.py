"""Forecast request and response models for the API contract."""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, field_validator


class ForecastRequest(BaseModel):
    """Request model for occupancy forecast."""

    room_ids: List[str] = Field(..., min_length=1, description="List of room IDs to forecast")
    horizon_hours: int = Field(default=1, ge=1, le=1, description="Supported one-step-ahead forecast horizon in hours")
    start_time: str | None = Field(default=None, description="Forecast start time (ISO 8601), defaults to now")
    confidence_levels: List[float] = Field(
        default=[0.1, 0.5, 0.9],
        min_length=2,
        description="Strictly increasing quantile levels between 0 and 1",
    )

    @field_validator("room_ids")
    @classmethod
    def validate_room_ids(cls, room_ids: List[str]) -> List[str]:
        if any(not room_id.strip() for room_id in room_ids):
            raise ValueError("room_ids must contain non-empty identifiers")
        return room_ids

    @field_validator("confidence_levels")
    @classmethod
    def validate_confidence_levels(cls, levels: List[float]) -> List[float]:
        if any(not 0.0 < level < 1.0 for level in levels):
            raise ValueError("confidence_levels must be strictly between 0 and 1")
        if levels != sorted(set(levels)):
            raise ValueError("confidence_levels must be unique and strictly increasing")
        return levels


class ForecastResponse(BaseModel):
    """Response model for occupancy forecast."""

    room_id: str
    timestamp: str
    horizon_hours: int
    predicted_headcount: float
    capacity: float | None = None
    is_scheduled: bool = False
    scheduled_enrollment: int = 0
    scheduled_course_code: str | None = None
    prediction_interval: dict
    confidence_levels: List[float]
    interval_method: str = "point_estimate_only"
    horizon_semantics: str = "one_step_ahead_hourly"
    model_version: str


class ForecastSchedule(BaseModel):
    """A timetable entry available as a forecast example."""

    room_id: str
    day_of_week: str
    start_time: str
    end_time: str
    enrolled_count: int
    course_code: str | None = None
    course_name: str | None = None


class BatchForecastResponse(BaseModel):
    """Response model for batch forecast."""

    forecasts: List[ForecastResponse]
    generated_at: str
    model_version: str
    total_rooms: int
    horizon_semantics: str = "one_step_ahead_hourly"


class ModelInfoResponse(BaseModel):
    """Response model for model information."""

    model_type: str
    version: str
    trained_at: str
    best_iteration: int | None
    feature_count: int
    top_features: dict
    hyperparameters: dict
    supported_horizon_hours: int = 1
