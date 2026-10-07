"""End-to-end MVP read workflow through FastAPI and the Streamlit client."""

from pathlib import Path

import httpx
import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest
from app.api.main import app as api_app
from app.api.routes import forecast as forecast_routes
from app.core.config import get_settings
from app.dashboard.api_client import APIClient, APIClientError, APIErrorCategory


PROJECT_ROOT = Path(__file__).parents[2]
DASHBOARD_APP = PROJECT_ROOT / "app" / "dashboard" / "app.py"
API_KEY = get_settings().api_read_key
TEST_SERVER = "http://testserver"


def _bind_client_to_testserver(monkeypatch, test_client: TestClient):
	calls = []

	def request(method, url, **kwargs):
		assert url.startswith(TEST_SERVER)
		path = url.removeprefix(TEST_SERVER)
		headers = kwargs.pop("headers", {})
		kwargs.pop("timeout", None)
		response = test_client.request(method, path, headers=headers, **kwargs)
		calls.append((method, path, headers, response))
		return response

	monkeypatch.setattr(httpx, "request", request)
	monkeypatch.setenv("FASTAPI_INTERNAL_URL", TEST_SERVER)
	monkeypatch.setenv("FASTAPI_API_KEY", API_KEY)
	return calls


def test_typed_client_read_workflow_uses_real_fastapi_testclient(monkeypatch):
	with TestClient(api_app) as test_client:
		calls = _bind_client_to_testserver(monkeypatch, test_client)
		client = APIClient(TEST_SERVER, API_KEY)

		health = client.health()
		readiness = client.readiness()
		metrics = client.metrics(scope="room", room_id="B01-R101")
		model = client.model_info()
		forecast = client.forecast("B01-R101", horizon_hours=1)

		assert health.status == "healthy"
		assert readiness.status == "ready"
		assert metrics.scope == "room"
		assert metrics.room_id == "B01-R101"
		assert metrics.metrics.observations > 0
		assert model.supported_horizon_hours == 1
		assert forecast.room_id == "B01-R101"
		assert forecast.horizon_hours == 1
		assert forecast.horizon_semantics == "one_step_ahead_hourly"
		assert forecast.interval_method == "point_estimate_only"
		assert 0 <= forecast.predicted_headcount <= 120
		assert isinstance(forecast.is_scheduled, bool)
		assert forecast.scheduled_enrollment >= 0
		schedules_without_key = test_client.get("/api/v1/forecast/schedules")
		schedules = test_client.get(
			"/api/v1/forecast/schedules",
			headers={"X-API-Key": API_KEY},
		)
		assert schedules_without_key.status_code == 401
		assert schedules.status_code == 200
		assert {
			"room_id": "B01-R101",
			"day_of_week": "Friday",
			"start_time": "09:00:00",
			"end_time": "10:00:00",
			"enrolled_count": 95,
			"course_code": "DS101",
			"course_name": "Intro to Data Science",
		} in schedules.json()
		assert all(method == "GET" for method, _, _, _ in calls)
		assert all(response.headers.get("X-Request-ID") for _, _, _, response in calls)
		assert all("actual_headcount" not in response.text for _, _, _, response in calls)

		without_key = test_client.get("/api/v1/metrics/utilization")
		invalid_key = test_client.get("/api/v1/metrics/utilization", headers={"X-API-Key": "invalid-key"})
		unknown_room = test_client.get(
			"/api/v1/forecast/predict/UNKNOWN",
			headers={"X-API-Key": API_KEY},
		)
		unsupported_horizon = test_client.get(
			"/api/v1/forecast/predict/B01-R101",
			headers={"X-API-Key": API_KEY},
			params={"horizon_hours": 6},
		)
		assert without_key.status_code == 401
		assert invalid_key.status_code == 401
		assert unknown_room.status_code == 404
		assert unsupported_horizon.status_code == 422
		read_only_write = test_client.post(
			"/api/v1/data/ingest",
			headers={"X-API-Key": API_KEY},
			data={"dataset_name": "rooms"},
			files={"file": ("rooms.csv", "room_id,capacity\nB01-R101,100\n", "text/csv")},
		)
		assert read_only_write.status_code == 403

		with pytest.raises(APIClientError) as error:
			APIClient(TEST_SERVER, "invalid-key").metrics()
		assert error.value.category is APIErrorCategory.AUTHENTICATION
		assert "invalid-key" not in str(error.value)


def test_forecast_uses_campus_local_time_for_timetable_features(monkeypatch):
	observed = []

	class CapturingForecaster:
		def predict(self, features):
			row = features.iloc[0]
			observed.append({
				"hour": int(row["hour"]),
				"is_scheduled": int(row["is_scheduled"]),
				"scheduled_enrollment": int(row["scheduled_enrollment"]),
			})
			return [float(row["scheduled_enrollment"])]

	monkeypatch.setattr(
		forecast_routes,
		"get_forecaster",
		lambda: CapturingForecaster(),
	)

	with TestClient(api_app) as test_client:
		response = test_client.get(
			"/api/v1/forecast/predict/B01-R101",
			headers={"X-API-Key": API_KEY},
			params={
				"horizon_hours": 1,
				"start_time": "2026-10-09T09:00:00+05:30",
			},
		)
		unscheduled_response = test_client.get(
			"/api/v1/forecast/predict/B01-R101",
			headers={"X-API-Key": API_KEY},
			params={
				"horizon_hours": 1,
				"start_time": "2026-10-08T08:00:00+05:30",
			},
		)

	assert response.status_code == 200, response.text
	assert unscheduled_response.status_code == 200, unscheduled_response.text
	assert observed[0] == {
		"hour": 9,
		"is_scheduled": 1,
		"scheduled_enrollment": 95,
	}
	assert observed[1] == {
		"hour": 8,
		"is_scheduled": 0,
		"scheduled_enrollment": 0,
	}
	result = response.json()
	assert result["timestamp"] == "2026-10-09T03:30:00+00:00"
	assert result["predicted_headcount"] == 95
	assert result["is_scheduled"] is True
	assert result["scheduled_enrollment"] == 95
	assert result["scheduled_course_code"] == "DS101"
	unscheduled = unscheduled_response.json()
	assert unscheduled["is_scheduled"] is False
	assert unscheduled["scheduled_enrollment"] == 0
	assert unscheduled["scheduled_course_code"] is None


def test_dashboard_overview_to_forecast_uses_real_fastapi_and_selected_room(monkeypatch):
	with TestClient(api_app) as test_client:
		calls = _bind_client_to_testserver(monkeypatch, test_client)
		st.cache_resource.clear()
		try:
			page = AppTest.from_file(str(DASHBOARD_APP)).run()
			assert not page.exception
			assert any(metric.label.startswith("SUR") for metric in page.metric)
			assert any(metric.label.startswith("RFU") for metric in page.metric)
			assert any(metric.label.startswith("WSH") for metric in page.metric)

			page.selectbox(key="overview_scope").set_value("Room")
			page.run()
			page.text_input(key="overview_room_id").set_value("B01-R101")
			page.button(key="overview_apply_filters").click()
			page.run()
			assert not page.exception
			assert any(button.label == "Open Forecast Explorer" for button in page.button)

			page.button(key="overview_open_forecast").click()
			page.run()
			assert not page.exception
			assert page.radio[0].value == "Forecast Explorer"
			assert page.text_input(key="forecast_room_id").value == "B01-R101"
			page.button(key="forecast_submit").click()
			page.run()
			assert not page.exception
			assert any(metric.label == "Predicted headcount" for metric in page.metric)
			assert any("Model version:" in item.value for item in page.caption)
			assert sum(path == "/api/v1/metrics/utilization" for _, path, _, _ in calls) >= 2
			assert any(path == "/api/v1/forecast/predict/B01-R101" for _, path, _, _ in calls)
			assert all(method == "GET" for method, _, _, _ in calls)
		finally:
			st.cache_resource.clear()
