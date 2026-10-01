"""Deterministic Streamlit tests for the operational overview."""

from datetime import date
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.dashboard.views import overview as overview_view
from app.dashboard.views.overview import build_metrics_params


APP_PATH = Path(__file__).parents[2] / "app" / "dashboard" / "app.py"


def _health_payload():
	return {
		"status": "healthy",
		"timestamp": "2026-09-29T10:00:00Z",
		"service": "campus-occupancy-api",
	}


def _readiness_payload(status="ready", checks=None):
	return {
		"status": status,
		"timestamp": "2026-09-29T10:00:00Z" if status == "ready" else None,
		"checks": checks or {
			"api": "healthy",
			"occupancy_data": "healthy",
			"rooms_data": "healthy",
			"xgboost_model": "healthy",
			"xgboost_metadata": "healthy",
		},
		"missing_dependencies": [],
	}


def _metrics_payload(scope="campus", observations=20):
	return {
		"scope": scope,
		"room_id": "B01-R101" if scope == "room" else None,
		"building_id": "B01" if scope == "building" else None,
		"metrics": {
			"seat_utilization_rate": 0.62,
			"room_frequency_of_use": 0.41,
			"wasted_seat_hours": 180.0,
			"peak_occupancy": 75.0,
			"observations": observations,
		},
		"time_window": {"start": None, "end": None},
		"source_timestamp": "2026-09-29T09:00:00Z" if observations else None,
	}


def _install_api(
	monkeypatch,
	*,
	metrics_status=200,
	observations=20,
	readiness_status=200,
	malformed_metrics=False,
	metrics_limited_once=False,
):
	calls = []
	metrics_request_count = 0

	def fake_request(method, url, **kwargs):
		nonlocal metrics_request_count
		calls.append((method, url, kwargs))
		if url.endswith("/health"):
			return httpx.Response(200, json=_health_payload())
		if url.endswith("/health/ready"):
			if readiness_status == 503:
				return httpx.Response(503, json={"detail": {
					"status": "not_ready",
					"missing_dependencies": ["xgboost_model", "xgboost_metadata"],
					"checks": {
						"api": "healthy",
						"occupancy_data": "healthy",
						"rooms_data": "healthy",
						"xgboost_model": "missing",
						"xgboost_metadata": "missing",
					},
				}})
			return httpx.Response(200, json=_readiness_payload())
		if metrics_status != 200:
			metrics_request_count += 1
			if not (metrics_limited_once and metrics_request_count > 1):
				return httpx.Response(metrics_status, json={"detail": "secret-key C:\\private\\occupancy.csv"}, headers={"Retry-After": "15"})
		params = kwargs.get("params", {})
		payload = _metrics_payload(params.get("scope", "campus"), observations)
		if malformed_metrics:
			payload["metrics"]["seat_utilization_rate"] = "malformed"
		return httpx.Response(200, json=payload)

	monkeypatch.setattr(httpx, "request", fake_request)
	return calls


def _run_overview():
	return AppTest.from_file(str(APP_PATH)).run()


def test_dashboard_uses_branded_campus_operations_shell():
	app = _run_overview()
	assert not app.exception
	assert any("Campus Operations" in item.value for item in app.markdown)
	assert any(item.value == "Overview" for item in app.radio)


def test_overview_displays_readiness_kpis_source_time_and_aggregate_chart(monkeypatch):
	calls = _install_api(monkeypatch)
	app = _run_overview()

	assert not app.exception
	assert [(metric.label, metric.value) for metric in app.metric] == [
		("API", "Available"),
		("Occupancy data", "Available"),
		("Forecast model", "Available"),
		("SUR · Seat Utilization Rate", "62.0%"),
		("RFU · Room Frequency of Use", "41.0%"),
		("WSH · Wasted Seat-Hours", "180.0"),
	]
	assert len(app.get("plotly_chart")) == 1
	assert any("not spatially resolved" in item.value for item in app.caption)
	assert any("2026-09-29 09:00 UTC" in item.value for item in app.caption)
	assert calls[-1][1].endswith("/api/v1/metrics/utilization")
	assert calls[-1][2]["params"] == {"scope": "campus"}


def test_not_ready_model_does_not_hide_available_utilization(monkeypatch):
	_install_api(monkeypatch, readiness_status=503)
	app = _run_overview()

	assert not app.exception
	assert any("readiness is degraded" in item.value for item in app.warning)
	assert next(metric.value for metric in app.metric if metric.label == "Occupancy data") == "Available"
	assert next(metric.value for metric in app.metric if metric.label == "Forecast model") == "Unavailable"
	assert any(metric.label.startswith("SUR") for metric in app.metric)


def test_empty_metrics_result_is_not_shown_as_zero_utilization(monkeypatch):
	_install_api(monkeypatch, observations=0)
	app = _run_overview()

	assert not app.exception
	assert any("No occupancy data matches" in item.value for item in app.info)
	assert not any(metric.label.startswith(("SUR", "RFU", "WSH")) for metric in app.metric)
	assert len(app.get("plotly_chart")) == 0


def test_malformed_metrics_response_is_safe_and_does_not_render_chart(monkeypatch):
	_install_api(monkeypatch, malformed_metrics=True)
	app = _run_overview()

	assert not app.exception
	assert any("unexpected response" in item.value for item in app.error)
	assert len(app.get("plotly_chart")) == 0


@pytest.mark.parametrize("status", [401, 403, 422, 429, 500, 503])
def test_metrics_failures_are_safe_and_actionable(monkeypatch, status):
	_install_api(monkeypatch, metrics_status=status)
	app = _run_overview()

	assert not app.exception
	rendered_errors = " ".join(item.value for item in app.error)
	assert rendered_errors
	assert "secret-key" not in rendered_errors
	assert "private" not in rendered_errors
	assert "occupancy.csv" not in rendered_errors
	assert not any(metric.label.startswith("SUR") for metric in app.metric)


def test_filter_parameters_match_supported_metrics_contract():
	date_range = (date(2026, 9, 1), date(2026, 9, 7))
	assert build_metrics_params("Campus") == {"scope": "campus"}
	assert build_metrics_params("Building", building_id=" B01 ") == {
		"scope": "building", "building_id": "B01",
	}
	assert build_metrics_params("Room", room_id="B01-R101") == {
		"scope": "room", "room_id": "B01-R101",
	}
	assert build_metrics_params(
		"Campus", date_range=date_range, day="Monday", time_of_day="midday",
	) == {
		"scope": "campus",
		"start_time": "2026-09-01T00:00:00",
		"end_time": "2026-09-07T23:59:59.999999",
		"day_of_week": "monday",
		"time_of_day": "midday",
	}


def test_streamlit_scope_filters_submit_correct_ids_and_reset(monkeypatch):
	calls = _install_api(monkeypatch)
	app = _run_overview()

	app.selectbox(key="overview_scope").set_value("Building")
	app.run()
	assert not app.exception
	assert [(item.label, item.value) for item in app.text_input] == [("Building ID", "")]
	app.text_input(key="overview_building_id").set_value(" B01 ")
	app.date_input(key="overview_date_range").set_value((date(2026, 9, 1), date(2026, 9, 7)))
	app.selectbox(key="overview_day").set_value("Monday")
	app.selectbox(key="overview_time_of_day").set_value("midday")
	app.button(key="overview_apply_filters").click()
	app.run()
	assert not app.exception
	assert calls[-1][2]["params"] == {
		"scope": "building",
		"building_id": "B01",
		"start_time": "2026-09-01T00:00:00",
		"end_time": "2026-09-07T23:59:59.999999",
		"day_of_week": "monday",
		"time_of_day": "midday",
	}

	app.selectbox(key="overview_scope").set_value("Room")
	app.run()
	assert [(item.label, item.value) for item in app.text_input] == [("Room ID", "")]
	app.text_input(key="overview_room_id").set_value("B01-R101")
	app.button(key="overview_apply_filters").click()
	app.run()
	assert calls[-1][2]["params"]["scope"] == "room"
	assert calls[-1][2]["params"]["room_id"] == "B01-R101"
	assert "building_id" not in calls[-1][2]["params"]

	app.button(key="overview_reset_filters").click()
	app.run()
	assert not app.exception
	assert calls[-1][2]["params"] == {"scope": "campus"}


def test_room_scope_handoff_opens_forecast_with_selected_room(monkeypatch):
	calls = _install_api(monkeypatch)
	app = _run_overview()
	app.selectbox(key="overview_scope").set_value("Room")
	app.run()
	app.text_input(key="overview_room_id").set_value("B01-R101")
	app.button(key="overview_apply_filters").click()
	app.run()
	assert any(button.label == "Open Forecast Explorer" for button in app.button)

	app.button(key="overview_open_forecast").click()
	app.run()

	assert not app.exception
	assert app.radio[0].value == "Forecast Explorer"
	assert app.text_input(key="forecast_room_id").value == "B01-R101"
	assert not any("/forecast/predict/" in call[1] for call in calls)


def test_overview_rate_limit_wait_does_not_repeat_metrics_until_manual_retry(monkeypatch):
	now = {"value": 100.0}
	monkeypatch.setattr(overview_view, "_monotonic_time", lambda: now["value"])
	calls = _install_api(monkeypatch, metrics_status=429, metrics_limited_once=True)
	app = _run_overview()
	metrics_calls = sum(call[1].endswith("/metrics/utilization") for call in calls)
	assert any("Retry in 15 seconds" in item.value for item in app.error)
	assert any(button.label == "Check metrics retry availability" for button in app.button)

	app.button(key="overview_metrics_retry_check").click()
	app.run()
	assert sum(call[1].endswith("/metrics/utilization") for call in calls) == metrics_calls

	now["value"] = 116.0
	app.button(key="overview_metrics_retry_check").click()
	app.run()
	assert any(button.label == "Retry metrics" for button in app.button)
	app.button(key="overview_metrics_retry").click()
	app.run()
	assert sum(call[1].endswith("/metrics/utilization") for call in calls) == metrics_calls + 1
	assert any(metric.label.startswith("SUR") for metric in app.metric)