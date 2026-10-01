"""Read-only operational overview for campus utilization."""

from datetime import date
from time import monotonic

import plotly.graph_objects as go
import streamlit as st

from app.dashboard.api_client import APIClient, APIClientError, APIErrorCategory
from app.dashboard.api_client import HealthResponse, ReadinessState


_DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_TIMES_OF_DAY = ("morning", "midday", "afternoon", "evening")
_DEFAULT_FILTERS = {"scope": "campus"}
_DEPENDENCY_LABELS = {
	"api": "API",
	"data_directory": "raw data directory",
	"processed_directory": "processed data directory",
	"models_directory": "model artifacts directory",
	"configs_directory": "configuration directory",
	"rooms_data": "room data",
	"occupancy_data": "occupancy data",
	"timetable_data": "timetable data",
	"events_data": "event data",
	"xgboost_model": "forecast model",
	"xgboost_metadata": "forecast model metadata",
}


def _monotonic_time() -> float:
	return monotonic()


def _open_forecast_explorer(room_id: str) -> None:
	st.session_state["forecast_room_id"] = room_id
	st.session_state["dashboard_page"] = "Forecast Explorer"


def _reset_filter_widgets() -> None:
	"""Reset form controls before Streamlit recreates their widgets."""
	st.session_state["overview_scope"] = "Campus"
	st.session_state["overview_building_id"] = ""
	st.session_state["overview_room_id"] = ""
	st.session_state["overview_date_range"] = ()
	st.session_state["overview_day"] = "Any day"
	st.session_state["overview_time_of_day"] = "Any time"


def _scope_changed() -> None:
	"""Clear scope-specific identifiers and apply the newly selected scope."""
	filters = dict(st.session_state.get("overview_applied_filters", _DEFAULT_FILTERS))
	filters.pop("building_id", None)
	filters.pop("room_id", None)
	filters["scope"] = st.session_state["overview_scope"].casefold()
	st.session_state["overview_applied_filters"] = filters
	st.session_state["overview_building_id"] = ""
	st.session_state["overview_room_id"] = ""


def _date_bounds(value: date | tuple[date, ...] | None) -> tuple[str | None, str | None]:
	if isinstance(value, date):
		start_date = end_date = value
	elif value:
		start_date = value[0]
		end_date = value[-1]
	else:
		return None, None
	return (
		f"{start_date.isoformat()}T00:00:00",
		f"{end_date.isoformat()}T23:59:59.999999",
	)


def build_metrics_params(
	scope: str,
	building_id: str = "",
	room_id: str = "",
	date_range: date | tuple[date, ...] | None = None,
	day: str = "Any day",
	time_of_day: str = "Any time",
) -> dict[str, str]:
	"""Translate the visible overview filters into the metrics API contract."""
	params = {"scope": scope.casefold()}
	if scope == "Building" and building_id.strip():
		params["building_id"] = building_id.strip()
	elif scope == "Room" and room_id.strip():
		params["room_id"] = room_id.strip()

	start_time, end_time = _date_bounds(date_range)
	if start_time:
		params["start_time"] = start_time
		params["end_time"] = end_time or start_time
	if day != "Any day":
		params["day_of_week"] = day.casefold()
	if time_of_day != "Any time":
		params["time_of_day"] = time_of_day.casefold()
	return params


def _dependency_state(checks: dict[str, str], keys: tuple[str, ...]) -> str:
	values = [checks[key] for key in keys if key in checks]
	if not values:
		return "Unknown"
	if all(value == "healthy" for value in values):
		return "Available"
	if any(value == "missing" for value in values):
		return "Unavailable"
	return "Degraded"


def _show_readiness(health: HealthResponse, readiness: ReadinessState) -> None:
	checks = readiness.checks
	data_state = _dependency_state(checks, ("occupancy_data", "rooms_data"))
	model_state = _dependency_state(checks, ("xgboost_model", "xgboost_metadata"))
	readiness_label = "Ready" if readiness.status == "ready" else "Degraded"

	if readiness.status == "ready":
		st.success("API available · service ready")
	else:
		st.warning("API available · service readiness is degraded. Utilization metrics may still be available.")

	api_column, data_column, model_column = st.columns(3)
	api_column.metric("API", "Available" if health.status == "healthy" else "Unavailable")
	data_column.metric("Occupancy data", data_state)
	model_column.metric("Forecast model", model_state)
	if readiness.missing_dependencies:
		labels = [_DEPENDENCY_LABELS.get(key, "required service dependency") for key in readiness.missing_dependencies]
		st.caption("Unavailable dependencies: " + ", ".join(labels))
	st.caption(f"Overall readiness: {readiness_label}")


def _show_readiness_error(error: APIClientError) -> None:
	st.error(f"API status unavailable: {error.message}")
	st.caption("Check that the API is running and authorized, then select Refresh overview to retry.")


def _show_metrics_error(error: APIClientError) -> None:
	st.error(error.message)
	guidance = {
		APIErrorCategory.AUTHENTICATION: "Check the dashboard API credential configuration.",
		APIErrorCategory.AUTHORIZATION: "This dashboard credential is not authorized for metrics access.",
		APIErrorCategory.VALIDATION: "Review the selected scope, identifier, and time filters.",
		APIErrorCategory.NOT_FOUND: "Check the building or room ID, or choose a broader scope.",
		APIErrorCategory.RATE_LIMITED: "Wait for the retry interval shown above before refreshing.",
		APIErrorCategory.SERVICE_UNAVAILABLE: "Required occupancy data may be unavailable; retry after the dependency is restored.",
		APIErrorCategory.TIMEOUT: "The API took too long to respond; retry when the service is responsive.",
		APIErrorCategory.NETWORK: "Check API availability, then refresh the overview.",
		APIErrorCategory.SERVER: "The service could not complete this request; retry later.",
		APIErrorCategory.UNEXPECTED: "Review the filters and retry the request.",
		APIErrorCategory.MALFORMED_RESPONSE: "The API response was unexpected; retry or contact the technical operator.",
	}
	st.caption(guidance.get(error.category, "Review the filters and retry the request."))


def _show_density(sur: float) -> None:
	"""Show one aggregate utilization measure without implying spatial resolution."""
	axis_max = max(1.0, sur * 1.15)
	figure = go.Figure(go.Bar(
		x=[sur],
		y=["Selected scope"],
		orientation="h",
		marker_color="#167D83",
		hovertemplate="Aggregate SUR: %{x:.1%}<extra></extra>",
	))
	figure.update_layout(
		height=150,
		margin={"l": 8, "r": 16, "t": 8, "b": 28},
		showlegend=False,
		xaxis={"range": [0, axis_max], "tickformat": ".0%", "title": "Seat utilization rate"},
		yaxis={"showticklabels": False},
	)
	st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})
	st.caption(f"Aggregate density: SUR is {sur:.1%} for the selected scope. This is not spatially resolved.")


def show_overview(client: APIClient) -> None:
	"""Render readiness, scope filters, aggregate utilization, and safe states."""
	title_column, refresh_column = st.columns([5, 1])
	title_column.subheader("Operational overview")
	refresh_column.button("Refresh overview", key="overview_refresh")

	try:
		with st.spinner("Checking API and dependency readiness"):
			health = client.health()
			readiness = client.readiness()
	except APIClientError as error:
		_show_readiness_error(error)
		return

	_show_readiness(health, readiness)
	st.divider()
	st.markdown("#### Utilization by scope")
	if "overview_scope" not in st.session_state:
		st.session_state["overview_scope"] = "Campus"
	if "overview_applied_filters" not in st.session_state:
		st.session_state["overview_applied_filters"] = dict(_DEFAULT_FILTERS)

	scope = st.selectbox("Scope", ("Campus", "Building", "Room"), key="overview_scope", on_change=_scope_changed)
	with st.form("overview_filters"):
		building_id = ""
		room_id = ""
		if scope == "Building":
			building_id = st.text_input("Building ID", key="overview_building_id", placeholder="For example, B01")
		elif scope == "Room":
			room_id = st.text_input("Room ID", key="overview_room_id", placeholder="For example, B01-R101")

		date_range = st.date_input("Date range (optional)", value=(), key="overview_date_range")
		day_column, time_column = st.columns(2)
		with day_column:
			day = st.selectbox("Day of week", ("Any day", *_DAYS), key="overview_day")
		with time_column:
			time_of_day = st.selectbox("Time of day", ("Any time", *_TIMES_OF_DAY), key="overview_time_of_day")
		apply_column, reset_column = st.columns(2)
		with apply_column:
			apply_filters = st.form_submit_button("Apply filters", type="primary", key="overview_apply_filters")
		with reset_column:
			reset_filters = st.form_submit_button("Reset filters", on_click=_reset_filter_widgets, key="overview_reset_filters")

	if reset_filters:
		filters = dict(_DEFAULT_FILTERS)
		st.session_state["overview_applied_filters"] = filters
	elif apply_filters:
		filters = build_metrics_params(scope, building_id, room_id, date_range, day, time_of_day)
		st.session_state["overview_applied_filters"] = filters
	else:
		filters = st.session_state["overview_applied_filters"]
	if filters["scope"] == "building" and not filters.get("building_id"):
		st.info("Enter a building ID and apply the filters to view building utilization.")
		return
	if filters["scope"] == "room" and not filters.get("room_id"):
		st.info("Enter a room ID and apply the filters to view room utilization.")
		return

	rate_error = st.session_state.get("overview_rate_limit_error")
	if isinstance(rate_error, APIClientError):
		_show_metrics_error(rate_error)
		deadline = st.session_state.get("overview_rate_limit_deadline")
		remaining = max(0, int((deadline or 0) - _monotonic_time() + 0.999))
		if remaining:
			st.caption(f"Metrics can be retried in {remaining} seconds. Checking availability will not send an API request.")
			if st.button("Check metrics retry availability", key="overview_metrics_retry_check"):
				st.rerun()
		else:
			if st.button("Retry metrics", key="overview_metrics_retry"):
				st.session_state.pop("overview_rate_limit_error", None)
				st.session_state.pop("overview_rate_limit_deadline", None)
				st.rerun()
		return

	try:
		with st.spinner("Loading utilization metrics"):
			response = client.metrics(**filters)
	except APIClientError as error:
		if error.category == APIErrorCategory.RATE_LIMITED:
			st.session_state["overview_rate_limit_error"] = error
			if error.retry_after_seconds:
				st.session_state["overview_rate_limit_deadline"] = _monotonic_time() + error.retry_after_seconds
		_show_metrics_error(error)
		if error.category == APIErrorCategory.RATE_LIMITED and error.retry_after_seconds:
			st.caption(f"Metrics can be retried in {error.retry_after_seconds} seconds. Checking availability will not send an API request.")
			st.button("Check metrics retry availability", key="overview_metrics_retry_check")
		return

	if response.metrics.observations == 0:
		st.info("No occupancy data matches this scope and time window. Broaden the time window, check the selected ID, or return to campus scope.")
		st.caption(f"Scope: {response.scope.title()} · Source timestamp: not available for an empty result")
		return

	sur = response.metrics.seat_utilization_rate
	rfu = response.metrics.room_frequency_of_use
	wsh = response.metrics.wasted_seat_hours
	kpi_columns = st.columns(3)
	kpi_columns[0].metric("SUR · Seat Utilization Rate", f"{sur:.1%}")
	kpi_columns[1].metric("RFU · Room Frequency of Use", f"{rfu:.1%}")
	kpi_columns[2].metric("WSH · Wasted Seat-Hours", f"{wsh:,.1f}")

	period = response.time_window
	window_label = "All available time" if not (period.start or period.end) else f"{period.start or 'start'} to {period.end or 'end'}"
	context = [f"Scope: {response.scope.title()}", f"Time window: {window_label}"]
	if filters.get("day_of_week"):
		context.append(f"Day: {filters['day_of_week'].title()}")
	if filters.get("time_of_day"):
		context.append(f"Time of day: {filters['time_of_day'].title()}")
	st.caption(" · ".join(context))
	if response.source_timestamp:
		st.caption(f"Latest source data: {response.source_timestamp.strftime('%Y-%m-%d %H:%M UTC')}")
	else:
		st.caption("Source timestamp was not provided by the API.")

	st.markdown("#### Occupancy density")
	_show_density(sur)
	if response.scope == "room" and response.room_id:
		st.button(
			"Open Forecast Explorer",
			on_click=_open_forecast_explorer,
			args=(response.room_id,),
			key="overview_open_forecast",
		)
