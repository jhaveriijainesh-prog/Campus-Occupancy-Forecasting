"""Typed contracts for space utilization responses."""

from datetime import datetime

from pydantic import BaseModel, Field


class UtilizationMetrics(BaseModel):
	"""Aggregated utilization measures for a selected scope."""

	seat_utilization_rate: float = Field(ge=0)
	room_frequency_of_use: float = Field(ge=0, le=1)
	wasted_seat_hours: float = Field(ge=0)
	peak_occupancy: float = Field(ge=0)
	observations: int = Field(ge=0)


class TimeWindow(BaseModel):
	"""Optional request window echoed in a metrics response."""

	start: str | None = None
	end: str | None = None


class UtilizationResponse(BaseModel):
	"""Stable response contract for campus, building, and room metrics."""

	scope: str
	room_id: str | None = None
	building_id: str | None = None
	metrics: UtilizationMetrics
	time_window: TimeWindow
	source_timestamp: datetime | None = None
