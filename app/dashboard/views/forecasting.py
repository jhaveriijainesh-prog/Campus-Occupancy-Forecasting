"""Read-only room forecast explorer for the supported one-hour horizon."""

import math
import re
from collections.abc import Mapping
from time import monotonic

import plotly.graph_objects as go
import streamlit as st

from app.dashboard.api_client import APIClient, APIClientError, APIErrorCategory
from app.schemas.forecast import ForecastResponse


_ROOM_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_ERROR_GUIDANCE = {
	APIErrorCategory.AUTHENTICATION: "Check the dashboard API credential configuration, then retry.",
	APIErrorCategory.AUTHORIZATION: "This dashboard credential is not authorized for forecasting.",
	APIErrorCategory.VALIDATION: "Check the room ID and supported one-hour horizon, then retry.",
	APIErrorCategory.NOT_FOUND: "That room was not found. Check its ID and retry.",
	APIErrorCategory.RATE_LIMITED: "Wait for the retry interval shown above, then submit again.",
	APIErrorCategory.SERVICE_UNAVAILABLE: "The forecast data or model is unavailable. Retry after it is restored.",
	APIErrorCategory.TIMEOUT: "The API took too long to respond. Retry when it is responsive.",
	APIErrorCategory.NETWORK: "Check API availability, then submit the request again.",
	APIErrorCategory.SERVER: "The service could not complete this request. Retry later.",
	APIErrorCategory.UNEXPECTED: "Review the room ID and retry the request.",
	APIErrorCategory.MALFORMED_RESPONSE: "The API response was unexpected. Retry or contact the technical operator.",
}


def _monotonic_time() -> float:
	return monotonic()


def _retry_seconds_remaining() -> int:
	deadline = st.session_state.get("forecast_retry_deadline")
	if not isinstance(deadline, (int, float)):
		return 0
	return max(0, math.ceil(deadline - _monotonic_time()))


def _set_retry_deadline(error: APIClientError) -> None:
	if error.category == APIErrorCategory.RATE_LIMITED and error.retry_after_seconds:
		st.session_state["forecast_retry_deadline"] = _monotonic_time() + error.retry_after_seconds


def _status_retry_control(category: APIErrorCategory | None = None) -> None:
	remaining = _retry_seconds_remaining()
	if category == APIErrorCategory.RATE_LIMITED and remaining > 0:
		st.caption(f"Retry is available in {remaining} seconds. Wait, then check availability before retrying.")
		st.button("Check retry availability", key="forecast_status_retry_check")
	else:
		st.button("Retry readiness and model status", key="forecast_status_retry")


def _render_status_snapshot(snapshot: dict[str, object]) -> None:
	st.markdown("#### Service status")
	readiness_column, model_column = st.columns(2)
	readiness_column.metric("Forecast readiness", str(snapshot["readiness"]))
	model_column.metric("Forecast model", str(snapshot["model"]))
	if snapshot.get("readiness_note"):
		readiness_column.caption(str(snapshot["readiness_note"]))
	if snapshot.get("model_note"):
		model_column.caption(str(snapshot["model_note"]))


def _show_status(client: APIClient) -> bool:
	if _retry_seconds_remaining() > 0:
		snapshot = st.session_state.get("forecast_status_snapshot")
		if snapshot:
			_render_status_snapshot(snapshot)
			if snapshot.get("status_error"):
				st.error(str(snapshot["status_error"]))
				category = snapshot.get("status_error_category")
				if isinstance(category, APIErrorCategory):
					st.caption(_ERROR_GUIDANCE.get(category, "Wait before retrying service status."))
				_status_retry_control(category if isinstance(category, APIErrorCategory) else None)
			return bool(snapshot.get("can_request"))

	try:
		readiness = client.readiness()
	except APIClientError as error:
		snapshot = {
			"readiness": "Unavailable", "model": "Not verified",
			"readiness_note": "Readiness could not be checked; forecast requests are paused.",
			"status_error": error.message,
			"status_error_category": error.category,
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		st.error(error.message)
		st.caption(_ERROR_GUIDANCE.get(error.category, "Check service access and retry."))
		_set_retry_deadline(error)
		_status_retry_control(error.category)
		return False
	except Exception:
		snapshot = {
			"readiness": "Unavailable", "model": "Not verified",
			"readiness_note": "Readiness returned an unexpected result; forecast requests are paused.",
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		st.error("Readiness returned an unexpected result.")
		_status_retry_control()
		return False

	if readiness.status != "ready":
		note = "Unavailable forecast dependencies are reported by the API." if readiness.missing_dependencies else "The API reports that one or more required dependencies are unavailable."
		snapshot = {
			"readiness": "Not ready", "model": "Unavailable",
			"readiness_note": note,
			"model_note": "Forecast requests are paused until readiness returns.",
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		_status_retry_control()
		return False

	try:
		model = client.model_info()
	except APIClientError as error:
		snapshot = {
			"readiness": "Ready", "model": "Unavailable",
			"model_note": "Forecast requests are paused until model information is available.",
			"status_error": error.message,
			"status_error_category": error.category,
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		st.error(error.message)
		st.caption(_ERROR_GUIDANCE.get(error.category, "Check model access and retry."))
		_set_retry_deadline(error)
		_status_retry_control(error.category)
		return False
	except Exception:
		snapshot = {
			"readiness": "Ready", "model": "Unavailable",
			"model_note": "Forecast requests are paused because model information was unexpected.",
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		st.error("Model information returned an unexpected result.")
		_status_retry_control()
		return False

	if model.supported_horizon_hours != 1:
		snapshot = {
			"readiness": "Ready", "model": model.version,
			"model_note": "The model does not report the supported one-hour horizon.",
			"can_request": False,
		}
		st.session_state["forecast_status_snapshot"] = snapshot
		_render_status_snapshot(snapshot)
		_status_retry_control()
		return False

	snapshot = {
		"readiness": "Ready", "model": model.version,
		"model_note": model.model_type,
		"can_request": True,
	}
	st.session_state["forecast_status_snapshot"] = snapshot
	_render_status_snapshot(snapshot)
	return True


def _show_request_error(error: APIClientError) -> None:
	st.error(error.message)
	st.caption(_ERROR_GUIDANCE.get(error.category, "Review the room ID and submit the request again."))


def _valid_interval(forecast: ForecastResponse) -> tuple[float, float] | None:
	"""Return ordered bounds only when the API identifies a real interval."""
	if forecast.interval_method == "point_estimate_only":
		return None
	interval = forecast.prediction_interval
	if not isinstance(interval, Mapping):
		return None
	lower = interval.get("p10")
	upper = interval.get("p90")
	prediction = forecast.predicted_headcount
	if any(isinstance(value, bool) or not isinstance(value, (int, float)) for value in (lower, upper)):
		return None
	if not all(math.isfinite(value) for value in (lower, upper, prediction)):
		return None
	if lower > upper or lower > prediction or prediction > upper:
		return None
	return float(lower), float(upper)


def _forecast_figure(forecast: ForecastResponse) -> go.Figure:
	figure = go.Figure()
	point = {
		"x": [forecast.timestamp],
		"y": [forecast.predicted_headcount],
		"mode": "markers",
		"name": "Forecast",
		"marker": {"color": "#167D83", "size": 12, "line": {"color": "#FFFFFF", "width": 2}},
		"hovertemplate": "%{x}<br>Predicted: %{y:.1f} people<extra></extra>",
	}
	interval = _valid_interval(forecast)
	if interval is not None:
		lower, upper = interval
		point["error_y"] = {
			"type": "data",
			"symmetric": False,
			"array": [upper - forecast.predicted_headcount],
			"arrayminus": [forecast.predicted_headcount - lower],
			"color": "#D17A22",
			"thickness": 2,
			"width": 8,
		}
	figure.add_trace(go.Scatter(**point))
	figure.update_layout(
		height=310,
		margin={"l": 12, "r": 20, "t": 18, "b": 52},
		showlegend=False,
		xaxis={"title": "API forecast timestamp", "type": "date"},
		yaxis={"title": "Predicted headcount (people)", "rangemode": "tozero"},
	)
	return figure


def show_forecast(client: APIClient) -> None:
	"""Render a single-point forecast with explicit status and failure states."""
	st.subheader("Forecast Explorer")
	st.caption("Supported horizon: 1 hour · one-step-ahead hourly forecast")
	can_request = _show_status(client)
	retry_seconds = _retry_seconds_remaining()
	st.divider()

	with st.form("forecast_request"):
		room_id = st.text_input(
			"Room ID",
			key="forecast_room_id",
			placeholder="For example, B01-R101",
			help="Enter a room identifier. The API verifies whether that room exists.",
		)
		st.caption("Horizon: 1 hour")
		submitted = st.form_submit_button(
			"Generate forecast",
			type="primary",
			disabled=not can_request or retry_seconds > 0,
			key="forecast_submit",
		)

	if submitted and can_request and retry_seconds == 0:
		clean_room_id = room_id.strip()
		st.session_state.pop("forecast_result", None)
		st.session_state.pop("forecast_result_room", None)
		st.session_state.pop("forecast_request_error", None)
		if not clean_room_id:
			st.session_state["forecast_request_error"] = "empty"
		elif not _ROOM_ID_PATTERN.fullmatch(clean_room_id):
			st.session_state["forecast_request_error"] = "invalid"
		else:
			_run_forecast(client, clean_room_id)

	if not can_request:
		st.info("A one-hour forecast cannot be requested until API readiness and model information are available.")
		return

	request_error = st.session_state.get("forecast_request_error")
	if request_error == "empty":
		st.error("Enter a room ID to request a forecast.")
	elif request_error == "invalid":
		st.error("Room ID format is invalid. Use letters, numbers, hyphens, or underscores.")
	elif request_error == "unexpected":
		st.error("The forecast request returned an unexpected result. Retry or contact the technical operator.")
	elif isinstance(request_error, APIClientError):
		_show_request_error(request_error)
		remaining_retry_seconds = _retry_seconds_remaining()
		if request_error.category == APIErrorCategory.RATE_LIMITED and remaining_retry_seconds > 0:
			st.caption(f"Retry is available in {remaining_retry_seconds} seconds. Wait, then check availability before retrying.")
			st.button("Check retry availability", key="forecast_retry_check")
		elif st.button("Retry forecast", key="forecast_retry"):
			_run_forecast(client, st.session_state.get("forecast_request_room", room_id.strip()))
			st.rerun()
	elif request_error == "empty_result":
		st.info("No forecast was returned for this room. Check the room ID and request again.")

	forecast = st.session_state.get("forecast_result")
	if forecast is None:
		if request_error is None:
			st.info("Enter a room ID and request a forecast to see its one-hour result.")
		return
	if st.session_state.get("forecast_result_room") != room_id.strip():
		st.info("Submit the selected room ID to load its forecast.")
		return
	if not isinstance(forecast, ForecastResponse):
		st.info("No forecast was returned for this room. Check the room ID and request again.")
		return

	st.markdown("#### Forecast result")
	metric_column, method_column = st.columns(2)
	metric_column.metric("Predicted headcount", f"{forecast.predicted_headcount:,.1f} people")
	method_column.metric("Horizon", "1 hour")
	st.caption(
		f"Room: {forecast.room_id} · API forecast timestamp: {forecast.timestamp} · "
		f"Model version: {forecast.model_version}"
	)
	st.plotly_chart(_forecast_figure(forecast), width="stretch", config={"displayModeBar": False})
	st.caption("This API response contains one forecast point; historical and scheduled context is not available here.")
	st.caption("A room capacity reference is not included in this API response.")
	if forecast.interval_method == "point_estimate_only":
		st.caption("The API reports point-estimate-only output; no prediction interval is shown.")
	elif forecast.prediction_interval and _valid_interval(forecast) is None:
		st.warning("The API interval bounds were invalid or unordered and were not rendered.")
	elif _valid_interval(forecast) is not None:
		st.caption(f"Prediction interval · API-reported method: {forecast.interval_method}")


def _run_forecast(client: APIClient, room_id: str) -> None:
	"""Issue one user-triggered request and retain only its safe result or error."""
	st.session_state.pop("forecast_result", None)
	st.session_state.pop("forecast_result_room", None)
	st.session_state.pop("forecast_request_error", None)
	st.session_state.pop("forecast_retry_deadline", None)
	st.session_state["forecast_request_room"] = room_id
	try:
		with st.spinner("Requesting one-hour forecast"):
			result = client.forecast(room_id, horizon_hours=1)
	except APIClientError as error:
		st.session_state["forecast_request_error"] = error
		_set_retry_deadline(error)
	except Exception:
		st.session_state["forecast_request_error"] = "unexpected"
	else:
		if result is None:
			st.session_state["forecast_request_error"] = "empty_result"
		else:
			st.session_state["forecast_result"] = result
			st.session_state["forecast_result_room"] = room_id
