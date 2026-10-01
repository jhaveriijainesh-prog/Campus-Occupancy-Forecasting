"""Deterministic Streamlit tests for the room forecast explorer."""

import json
from pathlib import Path

import httpx
import pytest
from streamlit.testing.v1 import AppTest

from app.dashboard.views.forecasting import _forecast_figure
from app.schemas.forecast import ForecastResponse


APP_PATH = Path(__file__).parents[2] / "app" / "dashboard" / "app.py"


def _forecast_payload(room_id="B01-R101", interval_method="point_estimate_only", interval=None):
	return {
		"room_id": room_id,
		"timestamp": "2026-09-29T10:00:00+00:00",
		"horizon_hours": 1,
		"predicted_headcount": 18.0,
		"prediction_interval": interval if interval is not None else {"p10": 18.0, "p50": 18.0, "p90": 18.0},
		"confidence_levels": [0.1, 0.5, 0.9],
		"interval_method": interval_method,
		"horizon_semantics": "one_step_ahead_hourly",
		"model_version": "xgboost-v1",
	}


def _install_api(
	monkeypatch,
	*,
	forecast_status=200,
	readiness_status=200,
	model_status=200,
	forecast_exception=None,
	malformed_forecast=False,
):
	calls = []

	def fake_request(method, url, **kwargs):
		calls.append((method, url, kwargs))
		if url.endswith("/health"):
			return httpx.Response(200, json={
				"status": "healthy",
				"timestamp": "2026-09-29T10:00:00Z",
				"service": "campus-occupancy-api",
			})
		if url.endswith("/health/ready"):
			if readiness_status == 503:
				return httpx.Response(503, json={"detail": {
					"status": "not_ready",
					"missing_dependencies": ["xgboost_model"],
					"checks": {"api": "healthy", "xgboost_model": "missing"},
				}})
			return httpx.Response(200, json={"status": "ready", "checks": {"api": "healthy"}, "missing_dependencies": []})
		if url.endswith("/metrics/utilization"):
			return httpx.Response(200, json={
				"scope": "campus",
				"room_id": None,
				"building_id": None,
				"metrics": {
					"seat_utilization_rate": 0.62,
					"room_frequency_of_use": 0.41,
					"wasted_seat_hours": 180.0,
					"peak_occupancy": 75.0,
					"observations": 20,
				},
				"time_window": {"start": None, "end": None},
				"source_timestamp": "2026-09-29T09:00:00Z",
			})
		if url.endswith("/forecast/model/info"):
			if model_status != 200:
				return httpx.Response(
					model_status,
					json={"detail": "secret-key C:\\private\\model.json"},
					headers={"Retry-After": "15"},
				)
			return httpx.Response(200, json={
				"model_type": "xgboost",
				"version": "xgboost-v1",
				"trained_at": "2026-09-01T00:00:00Z",
				"best_iteration": 10,
				"feature_count": 8,
				"top_features": {},
				"hyperparameters": {},
				"supported_horizon_hours": 1,
			})
		if "/forecast/predict/" in url:
			if forecast_exception is not None:
				raise forecast_exception
			if forecast_status != 200:
				return httpx.Response(
					forecast_status,
					json={"detail": "secret-key C:\\private\\traceback"},
					headers={"Retry-After": "15"},
				)
			room_id = url.rsplit("/", 1)[-1]
			payload = _forecast_payload(room_id)
			if malformed_forecast:
				payload.pop("predicted_headcount")
			return httpx.Response(200, json=payload)
		pytest.fail(f"Unexpected API request: {url}")

	monkeypatch.setattr(httpx, "request", fake_request)
	monkeypatch.setenv("FASTAPI_INTERNAL_URL", "http://api:8000")
	monkeypatch.setenv("FASTAPI_API_KEY", "test-key")
	return calls


def _open_forecast(monkeypatch, **api_options):
	calls = _install_api(monkeypatch, **api_options)
	app = AppTest.from_file(str(APP_PATH)).run()
	app.radio[0].set_value("Forecast Explorer")
	app.run()
	return app, calls


def _submit(app, room_id):
	app.text_input(key="forecast_room_id").set_value(room_id)
	app.button(key="forecast_submit").click()
	return app.run()


def test_forecast_success_uses_one_hour_and_displays_truthful_single_point(monkeypatch):
	app, calls = _open_forecast(monkeypatch)
	assert not app.exception
	assert any(item.label == "Forecast readiness" and item.value == "Ready" for item in app.metric)
	assert any(item.label == "Forecast model" and item.value == "xgboost-v1" for item in app.metric)
	assert [item.label for item in app.selectbox] == []
	assert [item.label for item in app.slider] == []

	app = _submit(app, " B01-R101 ")
	assert not app.exception
	request = next(call for call in calls if "/forecast/predict/" in call[1])
	assert request[1].endswith("/B01-R101")
	assert request[2]["params"]["horizon_hours"] == 1
	assert any("API forecast timestamp: 2026-09-29T10:00:00+00:00" in item.value for item in app.caption)
	assert any("Model version: xgboost-v1" in item.value for item in app.caption)
	assert any(item.label == "Predicted headcount" and item.value == "18.0 people" for item in app.metric)
	assert any("point-estimate-only" in item.value for item in app.caption)
	assert len(app.get("plotly_chart")) == 1
	assert sum("forecast/predict/" in call[1] for call in calls) == 1


@pytest.mark.parametrize(("room_id", "message"), [
	("", "Enter a room ID"),
	("B01 / private", "format is invalid"),
])
def test_empty_and_invalid_room_ids_are_inline_and_do_not_call_forecast(monkeypatch, room_id, message):
	app, calls = _open_forecast(monkeypatch)
	app = _submit(app, room_id)
	assert not app.exception
	assert any(message in item.value for item in app.error)
	assert not any("/forecast/predict/" in call[1] for call in calls)


def test_unknown_room_is_inline_safe_and_offers_explicit_retry(monkeypatch):
	app, calls = _open_forecast(monkeypatch, forecast_status=404)
	app = _submit(app, "B99-R999")
	assert not app.exception
	errors = " ".join(item.value for item in app.error)
	assert "not found" in errors
	assert "secret-key" not in errors and "private" not in errors and "traceback" not in errors
	assert any(button.label == "Retry forecast" for button in app.button)
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1


@pytest.mark.parametrize(("status", "safe_text"), [
	(401, "not authorized"),
	(403, "not authorized"),
	(422, "request is invalid"),
	(429, "Retry in 15 seconds"),
	(503, "unavailable"),
	(500, "could not complete"),
])
def test_service_errors_are_safe_inline_and_not_retried_automatically(monkeypatch, status, safe_text):
	app, calls = _open_forecast(monkeypatch, forecast_status=status)
	app = _submit(app, "B01-R101")
	assert not app.exception
	errors = " ".join(item.value for item in app.error)
	assert safe_text in errors
	assert "secret-key" not in errors and "private" not in errors and "traceback" not in errors
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1
	if status == 429:
		assert "Retry is available in 15 seconds" in " ".join(item.value for item in app.caption)
		assert any(button.label == "Check retry availability" for button in app.button)
		assert not any(button.label == "Retry forecast" for button in app.button)
		model_info_calls = sum("/forecast/model/info" in call[1] for call in calls)
		app.button(key="forecast_retry_check").click()
		app.run()
		assert sum("/forecast/predict/" in call[1] for call in calls) == 1
		assert sum("/forecast/model/info" in call[1] for call in calls) == model_info_calls
		return

	assert any(button.label == "Retry forecast" for button in app.button)

	app.button(key="forecast_submit").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 2

	app.button(key="forecast_retry").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 3


def test_readiness_and_model_unavailable_do_not_crash_or_expose_details(monkeypatch):
	app, calls = _open_forecast(monkeypatch, readiness_status=503, model_status=503)
	assert not app.exception
	assert any(item.label == "Forecast readiness" and item.value == "Not ready" for item in app.metric)
	assert any(item.label == "Forecast model" and item.value == "Unavailable" for item in app.metric)
	visible_text = " ".join(item.value for item in [*app.caption, *app.error])
	assert "secret-key" not in visible_text and "private" not in visible_text
	assert not any("/forecast/predict/" in call[1] for call in calls)


def test_model_info_unavailable_blocks_forecast_after_ready_probe(monkeypatch):
	app, calls = _open_forecast(monkeypatch, model_status=503)
	assert not app.exception
	assert any(item.label == "Forecast readiness" and item.value == "Ready" for item in app.metric)
	assert any(item.label == "Forecast model" and item.value == "Unavailable" for item in app.metric)
	assert not any("/forecast/predict/" in call[1] for call in calls)


@pytest.mark.parametrize("status", [401, 403])
def test_model_info_auth_failures_are_visible_safe_and_retryable(monkeypatch, status):
	app, calls = _open_forecast(monkeypatch, model_status=status)
	assert not app.exception
	assert any("not authorized" in item.value for item in app.error)
	assert any(button.label == "Retry readiness and model status" for button in app.button)
	visible_text = " ".join(item.value for item in [*app.caption, *app.error])
	assert "secret-key" not in visible_text and "private" not in visible_text
	assert not any("/forecast/predict/" in call[1] for call in calls)


def test_model_info_rate_limit_uses_manual_retry_after_without_repolling(monkeypatch):
	from app.dashboard.views import forecasting as forecast_view

	now = {"value": 100.0}
	monkeypatch.setattr(forecast_view, "_monotonic_time", lambda: now["value"])
	app, calls = _open_forecast(monkeypatch, model_status=429)
	assert not app.exception
	assert any("Retry in 15 seconds" in item.value for item in app.error)
	assert any(button.label == "Check retry availability" for button in app.button)
	assert not any("/forecast/predict/" in call[1] for call in calls)
	model_info_calls = sum("/forecast/model/info" in call[1] for call in calls)

	app.button(key="forecast_status_retry_check").click()
	app.run()
	assert sum("/forecast/model/info" in call[1] for call in calls) == model_info_calls
	assert not any("/forecast/predict/" in call[1] for call in calls)


def test_model_info_rate_limit_recovers_after_wait_with_manual_check(monkeypatch):
	from app.dashboard.views import forecasting as forecast_view

	now = {"value": 100.0}
	model_attempts = {"count": 0}
	monkeypatch.setattr(forecast_view, "_monotonic_time", lambda: now["value"])
	calls = _install_api(monkeypatch)
	original_request = httpx.request

	def rate_limit_once(method, url, **kwargs):
		if url.endswith("/forecast/model/info") and model_attempts["count"] == 0:
			model_attempts["count"] += 1
			calls.append((method, url, kwargs))
			return httpx.Response(
				429,
				json={"detail": "private rate limiter details"},
				headers={"Retry-After": "15"},
			)
		return original_request(method, url, **kwargs)

	monkeypatch.setattr(httpx, "request", rate_limit_once)
	app = AppTest.from_file(str(APP_PATH)).run()
	app.radio[0].set_value("Forecast Explorer")
	app.run()
	assert any("Retry in 15 seconds" in item.value for item in app.error)
	status_count = sum("/forecast/model/info" in call[1] for call in calls)
	app.button(key="forecast_status_retry_check").click()
	app.run()
	assert sum("/forecast/model/info" in call[1] for call in calls) == status_count

	now["value"] = 116.0
	app.button(key="forecast_status_retry_check").click()
	app.run()
	assert any(item.label == "Forecast model" and item.value == "xgboost-v1" for item in app.metric)
	app.text_input(key="forecast_room_id").set_value("B01-R101")
	app.button(key="forecast_submit").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1
	assert any(item.label == "Predicted headcount" for item in app.metric)


def test_rate_limit_retry_unlocks_only_after_user_checks_elapsed_wait(monkeypatch):
	from app.dashboard.views import forecasting as forecast_view

	now = {"value": 100.0}
	monkeypatch.setattr(forecast_view, "_monotonic_time", lambda: now["value"])
	app, calls = _open_forecast(monkeypatch, forecast_status=429)
	app = _submit(app, "B01-R101")

	assert any(button.label == "Check retry availability" for button in app.button)
	assert not any(button.label == "Retry forecast" for button in app.button)
	app.button(key="forecast_submit").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1
	model_info_calls = sum("/forecast/model/info" in call[1] for call in calls)
	app.button(key="forecast_retry_check").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1
	assert sum("/forecast/model/info" in call[1] for call in calls) == model_info_calls

	now["value"] = 116.0
	app.button(key="forecast_retry_check").click()
	app.run()
	assert any(button.label == "Retry forecast" for button in app.button)
	app.button(key="forecast_retry").click()
	app.run()
	assert sum("/forecast/predict/" in call[1] for call in calls) == 2


@pytest.mark.parametrize(("exception", "safe_text"), [
	(httpx.TimeoutException("private timeout"), "timed out"),
	(httpx.ConnectError("private network failure"), "Check API availability"),
])
def test_network_errors_are_safe_and_offer_manual_retry(monkeypatch, exception, safe_text):
	app, calls = _open_forecast(monkeypatch, forecast_exception=exception)
	app = _submit(app, "B01-R101")
	assert not app.exception
	assert safe_text in " ".join(error.value for error in app.error)
	assert "private" not in " ".join(error.value for error in app.error)
	assert any(button.label == "Retry forecast" for button in app.button)
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1


def test_empty_forecast_response_has_explicit_empty_state(monkeypatch):
	from app.dashboard.api_client import APIClient

	def empty_forecast(client, room_id, horizon_hours=1):
		assert isinstance(client, APIClient)
		assert room_id == "B01-R101"
		assert horizon_hours == 1
		return None

	monkeypatch.setattr(APIClient, "forecast", empty_forecast)
	app, _ = _open_forecast(monkeypatch)
	app = _submit(app, "B01-R101")
	assert not app.exception
	assert any("No forecast was returned" in item.value for item in app.info)


def test_malformed_forecast_response_is_safe_and_retryable(monkeypatch):
	app, calls = _open_forecast(monkeypatch, malformed_forecast=True)
	app = _submit(app, "B01-R101")
	assert not app.exception
	errors = " ".join(item.value for item in app.error)
	assert "unexpected response" in errors
	assert "secret-key" not in errors and "private" not in errors
	assert any(button.label == "Retry forecast" for button in app.button)
	assert sum("/forecast/predict/" in call[1] for call in calls) == 1


def test_point_only_quantiles_are_not_drawn_as_intervals():
	forecast = ForecastResponse.model_validate(_forecast_payload())
	figure = _forecast_figure(forecast)
	assert len(figure.data) == 1
	assert len(figure.data[0].x) == 1
	assert figure.to_plotly_json()["data"][0].get("error_y") is None


@pytest.mark.parametrize("bounds", [
	{"p10": 20.0, "p50": 18.0, "p90": 10.0},
	{"p10": 10.0, "p50": 18.0, "p90": 17.0},
])
def test_reversed_or_excluding_interval_bounds_are_not_rendered(bounds):
	payload = _forecast_payload(interval_method="api_interval", interval=bounds)
	forecast = ForecastResponse.model_validate(payload)
	figure = _forecast_figure(forecast)
	assert figure.to_plotly_json()["data"][0].get("error_y") is None


def test_ordered_interval_is_visually_distinct_and_never_reversed():
	payload = _forecast_payload(
		interval_method="api_interval",
		interval={"p10": 12.0, "p50": 18.0, "p90": 25.0},
	)
	figure = _forecast_figure(ForecastResponse.model_validate(payload))
	error = figure.data[0].error_y
	assert error is not None
	assert list(error.array) == [7.0]
	assert list(error.arrayminus) == [6.0]
	assert json.loads(figure.to_json())["data"][0]["error_y"]["symmetric"] is False