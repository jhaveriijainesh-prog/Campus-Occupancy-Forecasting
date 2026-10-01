"""Dashboard API gateway contract and failure-state tests."""

import logging
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from app.dashboard.api_client import APIClient, APIClientError, APIErrorCategory
from app.dashboard import app as dashboard_app


def _response(payload, status_code=200, headers=None):
    return httpx.Response(status_code, json=payload, headers=headers)


def _forecast(room_id="B01-R101"):
    return {
        "room_id": room_id,
        "timestamp": "2026-09-29T10:00:00+00:00",
        "horizon_hours": 1,
        "predicted_headcount": 18.0,
        "prediction_interval": {"p10": 18.0, "p50": 18.0, "p90": 18.0},
        "confidence_levels": [0.1, 0.5, 0.9],
        "interval_method": "point_estimate_only",
        "horizon_semantics": "one_step_ahead_hourly",
        "model_version": "xgboost-v1",
    }


def test_health_and_not_ready_responses_are_typed_and_public(monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if url.endswith("/health/ready"):
            return _response({"detail": {
                "status": "not_ready",
                "missing_dependencies": ["xgboost_model"],
                "checks": {"api": "healthy", "xgboost_model": "missing"},
            }}, 503)
        return _response({
            "status": "healthy",
            "timestamp": "2026-09-29T10:00:00+00:00",
            "service": "campus-occupancy-api",
        })

    monkeypatch.setattr(httpx, "request", fake_request)
    client = APIClient("http://api:8000/", "secret")

    assert client.health().status == "healthy"
    readiness = client.readiness()
    assert readiness.status == "not_ready"
    assert readiness.missing_dependencies == ["xgboost_model"]
    assert calls[0][1] == "http://api:8000/api/v1/health"
    assert calls[0][2]["headers"] == {}
    assert calls[1][1] == "http://api:8000/api/v1/health/ready"


def test_liveness_detailed_health_and_version_are_typed(monkeypatch):
    def fake_request(method, url, **kwargs):
        if url.endswith("/health/live"):
            return _response({"status": "alive", "timestamp": "2026-09-29T10:00:00Z"})
        if url.endswith("/health/detailed"):
            return _response({
                "status": "degraded",
                "timestamp": "2026-09-29T10:00:00Z",
                "service": "campus-occupancy-api",
                "version": "1.0.0",
                "checks": {"api": "healthy", "rooms_data": "missing"},
                "environment": "development",
            })
        return _response({
            "service": "campus-occupancy-api",
            "version": "1.0.0",
            "api_version": "v1",
            "build_date": "2026-09-25",
            "python_version": "3.11+",
            "features": ["forecasting", "analytics"],
        })

    monkeypatch.setattr(httpx, "request", fake_request)
    client = APIClient("http://api:8000", "secret")

    assert client.liveness().status == "alive"
    assert client.detailed_health().checks["rooms_data"] == "missing"
    assert client.version().api_version == "v1"


def test_metrics_parses_empty_result_and_filters(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, **kwargs)
        return _response({
            "scope": "room",
            "room_id": "B01-R101",
            "building_id": None,
            "metrics": {
                "seat_utilization_rate": 0,
                "room_frequency_of_use": 0,
                "wasted_seat_hours": 0,
                "peak_occupancy": 0,
                "observations": 0,
            },
            "time_window": {"start": "2026-09-01", "end": "2026-09-02"},
            "source_timestamp": None,
        })

    monkeypatch.setattr(httpx, "request", fake_request)
    result = APIClient("http://api:8000", "secret").metrics(
        scope="room", room_id="B01-R101", start_time="2026-09-01", end_time="2026-09-02",
    )

    assert result.scope == "room"
    assert result.metrics.observations == 0
    assert captured["params"] == {
        "scope": "room", "room_id": "B01-R101", "start_time": "2026-09-01", "end_time": "2026-09-02",
    }
    assert captured["headers"] == {"X-API-Key": "secret"}


def test_metrics_validation_failure_is_normalized(monkeypatch):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: _response(
        {"detail": "backend includes private implementation details"}, 422,
    ))

    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000", "secret").metrics(scope="room", building_id="B01")

    assert raised.value.category is APIErrorCategory.VALIDATION
    assert "private" not in str(raised.value)


def test_single_and_batch_forecasts_use_real_contracts(monkeypatch):
    calls = []

    def fake_request(method, url, **kwargs):
        calls.append((method, url, kwargs))
        if method == "GET":
            return _response(_forecast())
        return _response({
            "forecasts": [_forecast(), _forecast("B01-R102")],
            "generated_at": "2026-09-29T10:00:00+00:00",
            "model_version": "xgboost-v1",
            "total_rooms": 2,
            "horizon_semantics": "one_step_ahead_hourly",
        })

    monkeypatch.setattr(httpx, "request", fake_request)
    client = APIClient("http://api:8000", "secret")

    single = client.forecast("B01-R101", confidence_levels=[0.1, 0.5, 0.9])
    batch = client.batch_forecast(["B01-R101", "B01-R102"], start_time="2026-09-29T10:00:00Z")

    assert single.horizon_hours == 1
    assert single.horizon_semantics == "one_step_ahead_hourly"
    assert calls[0][0:2] == ("GET", "http://api:8000/api/v1/forecast/predict/B01-R101")
    assert calls[0][2]["params"]["horizon_hours"] == 1
    assert calls[1][0:2] == ("POST", "http://api:8000/api/v1/forecast/predict")
    assert calls[1][2]["json"]["room_ids"] == ["B01-R101", "B01-R102"]
    assert calls[1][2]["json"]["start_time"] == "2026-09-29T10:00:00Z"
    assert batch.total_rooms == 2


def test_unknown_room_batch_failure_is_not_dropped_or_exposed(monkeypatch):
    captured = {}

    def fake_request(method, url, **kwargs):
        captured.update(method=method, url=url, body=kwargs["json"])
        return _response({"detail": {"unknown_room_ids": ["private-room-id"]}}, 404)

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000", "secret").batch_forecast(["B01-R101", "private-room-id"])

    assert captured["body"]["room_ids"] == ["B01-R101", "private-room-id"]
    assert raised.value.category is APIErrorCategory.NOT_FOUND
    assert "private-room-id" not in str(raised.value)


def test_unsupported_horizon_fails_before_request(monkeypatch):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: pytest.fail("request must not be sent"))
    client = APIClient("http://api:8000", "secret")

    with pytest.raises(APIClientError) as error:
        client.forecast("B01-R101", 24)

    assert error.value.category is APIErrorCategory.VALIDATION
    assert error.value.status_code == 422


@pytest.mark.parametrize(("status", "category"), [
    (401, APIErrorCategory.AUTHENTICATION),
    (403, APIErrorCategory.AUTHORIZATION),
    (404, APIErrorCategory.NOT_FOUND),
    (422, APIErrorCategory.VALIDATION),
    (429, APIErrorCategory.RATE_LIMITED),
    (500, APIErrorCategory.SERVER),
    (503, APIErrorCategory.SERVICE_UNAVAILABLE),
])
def test_http_failures_are_normalized_without_backend_details(monkeypatch, status, category):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: _response(
        {"detail": "secret-key internal path C:\\private\\model.json"},
        status,
        headers={"X-Request-ID": "0123456789abcdef"},
    ))

    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000", "secret-key").metrics()

    error = raised.value
    assert error.category is category
    assert error.status_code == status
    assert "secret-key" not in str(error)
    assert "private" not in str(error)
    assert error.request_id == "0123456789abcdef"


def test_rate_limit_exposes_retry_after_without_retrying(monkeypatch):
    calls = []

    def fake_request(*args, **kwargs):
        calls.append(args)
        return _response({"detail": "internal limiter state"}, 429, {"Retry-After": "12"})

    monkeypatch.setattr(httpx, "request", fake_request)
    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000", "secret").metrics()

    assert raised.value.retry_after_seconds == 12
    assert "12 seconds" in str(raised.value)
    assert len(calls) == 1


@pytest.mark.parametrize(("exception", "category"), [
    (httpx.TimeoutException("secret-key at http://internal/private"), APIErrorCategory.TIMEOUT),
    (httpx.ConnectError("secret-key at http://internal/private"), APIErrorCategory.NETWORK),
])
def test_network_failures_are_safe(monkeypatch, caplog, exception, category):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: (_ for _ in ()).throw(exception))

    with caplog.at_level(logging.DEBUG), pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000", "secret-key").metrics()

    assert raised.value.category is category
    assert "secret-key" not in str(raised.value)
    assert "internal" not in str(raised.value)
    assert "secret-key" not in caplog.text


@pytest.mark.parametrize("payload", [
    {"status": "healthy"},
    ["not", "an", "object"],
])
def test_malformed_success_responses_fail_safely(monkeypatch, payload):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: _response(payload))

    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000").health()

    assert raised.value.category is APIErrorCategory.MALFORMED_RESPONSE
    assert "service" not in str(raised.value)


def test_invalid_json_response_fails_safely(monkeypatch):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: httpx.Response(200, text="not-json"))

    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000").health()

    assert raised.value.category is APIErrorCategory.MALFORMED_RESPONSE
    assert "not-json" not in str(raised.value)


def test_missing_credentials_fail_locally_for_protected_routes(monkeypatch):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: pytest.fail("request must not be sent"))

    with pytest.raises(APIClientError) as raised:
        APIClient("http://api:8000").metrics()

    assert raised.value.category is APIErrorCategory.AUTHENTICATION
    assert raised.value.status_code == 401


def test_model_info_is_typed(monkeypatch):
    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: _response({
        "model_type": "XGBRegressor",
        "version": "1.0.0",
        "trained_at": "2026-09-20T00:00:00Z",
        "best_iteration": 12,
        "feature_count": 3,
        "top_features": {"hour": 0.5},
        "hyperparameters": {"max_depth": 4},
        "supported_horizon_hours": 1,
    }))

    info = APIClient("http://api:8000", "secret").model_info()
    assert info.supported_horizon_hours == 1
    assert info.top_features["hour"] == 0.5


def test_dashboard_client_uses_local_configuration_and_safe_startup_failure(monkeypatch):
    monkeypatch.delenv("FASTAPI_INTERNAL_URL", raising=False)
    monkeypatch.delenv("FASTAPI_API_KEY", raising=False)
    monkeypatch.setattr(dashboard_app, "get_settings", lambda: SimpleNamespace(
        fastapi_public_url="http://localhost:8000",
        api_secret_key="configured-secret",
        api_read_key="configured-read-secret",
        dashboard_api_timeout_seconds=4.5,
    ))
    client = dashboard_app.build_api_client()
    assert client.base_url == "http://localhost:8000"
    assert client.timeout == 4.5
    assert client._api_key == "configured-read-secret"

    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("private detail")))
    with pytest.raises(APIClientError, match="Check API availability"):
        client.health()


def test_streamlit_startup_handles_api_unavailable_without_traceback(monkeypatch):
    from streamlit.testing.v1 import AppTest

    monkeypatch.setattr(httpx, "request", lambda *args, **kwargs: (_ for _ in ()).throw(httpx.ConnectError("private detail")))
    app_path = Path(__file__).parents[2] / "app" / "dashboard" / "app.py"

    app_test = AppTest.from_file(str(app_path)).run()

    assert not app_test.exception
    assert any("API status unavailable" in str(element.value) for element in app_test.error)
    assert any("Check API availability" in str(element.value) for element in app_test.error)
