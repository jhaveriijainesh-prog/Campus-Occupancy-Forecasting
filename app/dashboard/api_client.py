"""Typed, user-safe gateway from Streamlit to the FastAPI read API."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
import re
from typing import Any, Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, Field, ValidationError

from app.schemas.forecast import (
	BatchForecastResponse,
	ForecastRequest,
	ForecastResponse,
	ModelInfoResponse,
)
from app.schemas.health import (
	DetailedHealthResponse,
	HealthResponse,
	LivenessResponse,
	VersionResponse,
)
from app.schemas.metrics import UtilizationResponse


class APIErrorCategory(str, Enum):
	"""Stable dashboard-facing categories for API failures."""

	AUTHENTICATION = "authentication"
	AUTHORIZATION = "authorization"
	VALIDATION = "validation"
	NOT_FOUND = "not_found"
	RATE_LIMITED = "rate_limited"
	SERVICE_UNAVAILABLE = "service_unavailable"
	TIMEOUT = "timeout"
	NETWORK = "network"
	SERVER = "server_error"
	UNEXPECTED = "unexpected"
	MALFORMED_RESPONSE = "malformed_response"


class APIClientError(RuntimeError):
	"""A safe dashboard error that contains no backend response or exception text."""

	def __init__(
		self,
		category: APIErrorCategory,
		message: str,
		status_code: int | None = None,
		retry_after_seconds: int | None = None,
		request_id: str | None = None,
	):
		self.category = category
		self.status_code = status_code
		self.message = message
		self.retry_after_seconds = retry_after_seconds
		self.request_id = request_id
		super().__init__(message)

	def __str__(self) -> str:
		return self.message


class ReadinessState(BaseModel):
	status: Literal["ready", "not_ready"]
	timestamp: datetime | None = None
	checks: dict[str, str]
	missing_dependencies: list[str] = Field(default_factory=list)


_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9_-]{1,64}$")
_SAFE_MESSAGES = {
	401: "Access is not authorized for this read operation.",
	403: "Access is not authorized for this read operation.",
	404: "The requested room or scope was not found.",
	422: "The request is invalid. Check the selected filters, room, timestamp, and supported forecast horizon.",
	429: "Too many requests. Please wait and retry.",
	503: "The analytics API or a required data/model dependency is unavailable.",
}


class APIClient:
	"""Configured dashboard gateway; every successful typed call validates its contract."""

	def __init__(self, base_url: str, api_key: str = "", timeout: float = 10.0):
		if timeout <= 0:
			raise ValueError("timeout must be positive")
		self.base_url = base_url.rstrip("/")
		self._api_key = api_key
		self.timeout = timeout

	@staticmethod
	def _request_id(response: httpx.Response) -> str | None:
		request_id = response.headers.get("X-Request-ID", "")
		return request_id if _SAFE_REQUEST_ID.fullmatch(request_id) else None

	@staticmethod
	def _http_error(response: httpx.Response) -> APIClientError:
		status_code = response.status_code
		category = {
			401: APIErrorCategory.AUTHENTICATION,
			403: APIErrorCategory.AUTHORIZATION,
			404: APIErrorCategory.NOT_FOUND,
			422: APIErrorCategory.VALIDATION,
			429: APIErrorCategory.RATE_LIMITED,
			503: APIErrorCategory.SERVICE_UNAVAILABLE,
		}.get(status_code, APIErrorCategory.SERVER if status_code >= 500 else APIErrorCategory.UNEXPECTED)
		message = _SAFE_MESSAGES.get(
			status_code,
			"The analytics API could not complete the request." if status_code >= 500
			else "The request could not be completed.",
		)
		retry_header = response.headers.get("Retry-After", "")
		retry_after_seconds = int(retry_header) if retry_header.isdecimal() else None
		if status_code == 429 and retry_after_seconds is not None:
			message = f"{message} Retry in {retry_after_seconds} seconds."
		return APIClientError(
			category=category,
			status_code=status_code,
			message=message,
			retry_after_seconds=retry_after_seconds,
			request_id=APIClient._request_id(response),
		)

	def _request(
		self,
		method: str,
		path: str,
		response_model: type[BaseModel] | None = None,
		*,
		authenticated: bool = True,
		allow_not_ready: bool = False,
		**kwargs: Any,
	) -> Any:
		if authenticated and not self._api_key:
			raise APIClientError(
				APIErrorCategory.AUTHENTICATION,
				_SAFE_MESSAGES[401],
				status_code=401,
			)

		headers = {"X-API-Key": self._api_key} if authenticated else {}
		try:
			response = httpx.request(
				method,
				f"{self.base_url}{path}",
				headers=headers,
				timeout=self.timeout,
				**kwargs,
			)
		except httpx.TimeoutException:
			raise APIClientError(
				APIErrorCategory.TIMEOUT,
				"The API request timed out. Please retry.",
			) from None
		except httpx.HTTPError:
			raise APIClientError(
				APIErrorCategory.NETWORK,
				"The request could not be completed. Check API availability and retry.",
			) from None

		if allow_not_ready and response.status_code == 503 and response_model is not None:
			try:
				body = response.json()
				return response_model.model_validate(body["detail"])
			except (KeyError, TypeError, ValueError, ValidationError):
				pass

		if not 200 <= response.status_code < 300:
			raise self._http_error(response)

		try:
			body = response.json()
			if response_model is None:
				if not isinstance(body, dict):
					raise TypeError
				return body
			return response_model.model_validate(body)
		except (TypeError, ValueError, ValidationError):
			raise APIClientError(
				APIErrorCategory.MALFORMED_RESPONSE,
				"The analytics API returned an unexpected response. Please retry or contact support.",
				status_code=response.status_code,
				request_id=self._request_id(response),
			) from None

	def health(self) -> HealthResponse:
		return self._request("GET", "/api/v1/health", HealthResponse, authenticated=False)

	def liveness(self) -> LivenessResponse:
		return self._request("GET", "/api/v1/health/live", LivenessResponse, authenticated=False)

	def readiness(self) -> ReadinessState:
		return self._request(
			"GET", "/api/v1/health/ready", ReadinessState,
			authenticated=False, allow_not_ready=True,
		)

	def detailed_health(self) -> DetailedHealthResponse:
		return self._request("GET", "/api/v1/health/detailed", DetailedHealthResponse)

	def version(self) -> VersionResponse:
		return self._request("GET", "/api/v1/version", VersionResponse)

	def metrics(
		self,
		scope: Literal["campus", "building", "room"] = "campus",
		room_id: str | None = None,
		building_id: str | None = None,
		start_time: str | None = None,
		end_time: str | None = None,
		day_of_week: str | None = None,
		time_of_day: str | None = None,
	) -> UtilizationResponse:
		params = {
			"scope": scope,
			"room_id": room_id,
			"building_id": building_id,
			"start_time": start_time,
			"end_time": end_time,
			"day_of_week": day_of_week,
			"time_of_day": time_of_day,
		}
		return self._request(
			"GET", "/api/v1/metrics/utilization", UtilizationResponse,
			params={key: value for key, value in params.items() if value is not None},
		)

	@staticmethod
	def _validated_forecast_request(
		room_ids: list[str],
		horizon_hours: int,
		start_time: str | None = None,
		confidence_levels: list[float] | None = None,
	) -> ForecastRequest:
		try:
			return ForecastRequest.model_validate({
				"room_ids": room_ids,
				"horizon_hours": horizon_hours,
				"start_time": start_time,
				"confidence_levels": confidence_levels if confidence_levels is not None else [0.1, 0.5, 0.9],
			})
		except ValidationError:
			raise APIClientError(
				APIErrorCategory.VALIDATION,
				_SAFE_MESSAGES[422],
				status_code=422,
			) from None

	def forecast(
		self,
		room_id: str,
		horizon_hours: int = 1,
		confidence_levels: list[float] | None = None,
	) -> ForecastResponse:
		request = self._validated_forecast_request([room_id], horizon_hours, confidence_levels=confidence_levels)
		params = {
			"horizon_hours": request.horizon_hours,
			"confidence_levels": ",".join(str(level) for level in request.confidence_levels),
		}
		return self._request(
			"GET", f"/api/v1/forecast/predict/{quote(room_id, safe='')}", ForecastResponse,
			params=params,
		)

	def batch_forecast(
		self,
		room_ids: list[str],
		horizon_hours: int = 1,
		start_time: str | None = None,
		confidence_levels: list[float] | None = None,
	) -> BatchForecastResponse:
		request = self._validated_forecast_request(room_ids, horizon_hours, start_time, confidence_levels)
		return self._request(
			"POST", "/api/v1/forecast/predict", BatchForecastResponse,
			json=request.model_dump(exclude_none=True),
		)

	def model_info(self) -> ModelInfoResponse:
		return self._request("GET", "/api/v1/forecast/model/info", ModelInfoResponse)

	# Keep the already exposed deferred pages working; they remain outside the MVP client contracts.
	def clusters(self) -> dict[str, Any]:
		return self._request("GET", "/api/v1/clustering/rooms")

	def scenario(self, **payload: Any) -> dict[str, Any]:
		return self._request("POST", "/api/v1/simulation/run", json=payload)

	def optimization_comparison(self) -> dict[str, Any]:
		return self._request("POST", "/api/v1/optimize/compare")
