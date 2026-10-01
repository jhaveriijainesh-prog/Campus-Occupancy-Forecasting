"""Response contracts for public health probes and protected service metadata."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
	status: Literal["healthy"]
	timestamp: datetime
	service: str


class ReadinessResponse(BaseModel):
	status: Literal["ready"]
	timestamp: datetime
	checks: dict[str, str]


class ReadinessUnavailableDetail(BaseModel):
	status: Literal["not_ready"]
	missing_dependencies: list[str]
	checks: dict[str, str]


class ReadinessUnavailableResponse(BaseModel):
	detail: ReadinessUnavailableDetail


class LivenessResponse(BaseModel):
	status: Literal["alive"]
	timestamp: datetime


class DetailedHealthResponse(BaseModel):
	status: Literal["healthy", "degraded"]
	timestamp: datetime
	service: str
	version: str
	checks: dict[str, str]
	environment: str


class VersionResponse(BaseModel):
	service: str
	version: str
	api_version: str
	build_date: str
	python_version: str
	features: list[str]