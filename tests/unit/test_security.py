"""Behavioral tests for API security, rate limiting, and safe failures."""

import json
import logging
import sys

import pytest
from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.config import get_settings
from app.core.exceptions import handle_exception
from app.core.logging import JSONFormatter
from app.core.security import APIKeyManager, RateLimiter, _api_key_manager, _rate_limiter, sanitize_for_logging


API_KEY = "bds06-super-secret-development-key-change-in-prod"
READ_API_KEY = "bds06-super-secret-read-only-development-key-change-in-prod"


def test_production_requires_explicit_secret_keys(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.delenv("API_SECRET_KEY", raising=False)
    monkeypatch.delenv("API_READ_KEY", raising=False)

    with pytest.raises(RuntimeError, match="API_SECRET_KEY|API_READ_KEY"):
        APIKeyManager()

    with pytest.raises(RuntimeError, match="API_SECRET_KEY|API_READ_KEY"):
        get_settings()


def test_protected_read_route_requires_valid_api_key():
    client = TestClient(create_app())

    missing = client.get("/api/v1/metrics/utilization")
    invalid = client.get("/api/v1/metrics/utilization", headers={"X-API-Key": "invalid-key"})

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert "api_key" not in missing.text.lower()
    assert "api_key" not in invalid.text.lower()


def test_dashboard_read_key_cannot_write_data():
    client = TestClient(create_app())
    permissions = _api_key_manager.get_permissions(READ_API_KEY)

    metrics = client.get("/api/v1/metrics/utilization", headers={"X-API-Key": READ_API_KEY})
    forecast = client.get("/api/v1/forecast/predict/B01-R101", headers={"X-API-Key": READ_API_KEY})
    ingestion = client.post(
        "/api/v1/data/ingest",
        headers={"X-API-Key": READ_API_KEY},
        data={"dataset_name": "rooms"},
        files={"file": ("rooms.csv", "room_id,capacity\nB01-R101,100\n", "text/csv")},
    )

    assert permissions == {"read", "forecast"}
    assert metrics.status_code == 200, metrics.text
    assert forecast.status_code == 200, forecast.text
    assert ingestion.status_code == 403


def test_public_health_route_remains_available_and_has_security_headers():
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["X-Request-ID"]


def test_detailed_health_and_version_require_read_access():
    client = TestClient(create_app())

    assert client.get("/api/v1/health/detailed").status_code == 401
    assert client.get("/api/v1/version").status_code == 401
    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code in {200, 503}


def test_rate_limiter_rejects_requests_after_configured_limit():
    limiter = RateLimiter(max_requests=2, window_seconds=60)

    assert limiter.check_rate_limit("client")[0] is True
    assert limiter.check_rate_limit("client")[0] is True
    allowed, retry_after = limiter.check_rate_limit("client")

    assert allowed is False
    assert retry_after >= 1
    limiter.reset()
    assert limiter.check_rate_limit("client")[0] is True


def test_api_rate_limit_returns_429_and_retry_after(monkeypatch):
    client = TestClient(create_app())
    original_limit = _rate_limiter.max_requests
    original_window = _rate_limiter.window_seconds
    _rate_limiter.max_requests = 1
    _rate_limiter.window_seconds = 60
    _rate_limiter.reset()

    try:
        first = client.get("/api/v1/metrics/utilization", headers={"X-API-Key": API_KEY})
        second = client.get("/api/v1/metrics/utilization", headers={"X-API-Key": API_KEY})
    finally:
        _rate_limiter.max_requests = original_limit
        _rate_limiter.window_seconds = original_window
        _rate_limiter.reset()

    assert first.status_code == 200
    assert second.status_code == 429
    assert second.headers["Retry-After"].isdigit()
    assert second.json()["detail"] == "Rate limit exceeded"


def test_auth_logs_do_not_contain_ip_or_api_key(caplog):
    client = TestClient(create_app())
    secret = "api-key-with-sensitive-value-1234567890"

    with caplog.at_level(logging.WARNING):
        client.get(
            "/api/v1/metrics/utilization",
            headers={"X-API-Key": secret, "X-Forwarded-For": "198.51.100.10"},
        )

    messages = " ".join(record.getMessage() for record in caplog.records)
    assert secret not in messages
    assert "198.51.100.10" not in messages
    assert "api_key_prefix" not in messages
    assert "client_host" not in messages


def test_sanitized_logging_removes_sensitive_values():
    result = sanitize_for_logging({
        "email": "planner@example.com",
        "mac": "AA:BB:CC:DD:EE:FF",
        "room_id": "B01-R101",
    })

    assert result["email"] == "[REDACTED]"
    assert result["mac"] == "[REDACTED]"
    assert result["room_id"] == "B01-R101"


def test_unexpected_error_response_does_not_expose_exception_details():
    error = handle_exception(ValueError("C:\\private\\secret-model.json"))

    assert error.status_code == 500
    assert error.message == "Internal server error"
    assert "secret-model" not in json.dumps(error.to_dict())


def test_json_request_logs_contain_operational_fields_only():
    record = logging.LogRecord("api", logging.INFO, "main.py", 1, "API request completed", (), None)
    record.extra_fields = {
        "endpoint": "/api/v1/metrics/utilization",
        "request_id": "request-123",
        "duration_ms": 4.2,
        "status_code": 200,
    }

    payload = json.loads(JSONFormatter().format(record))

    assert payload["service"] == "campus-occupancy-api"
    assert payload["endpoint"] == "/api/v1/metrics/utilization"
    assert payload["request_id"] == "request-123"
    assert "X-API-Key" not in json.dumps(payload)
    assert "actual_headcount" not in json.dumps(payload)


def test_json_formatter_redacts_sensitive_extra_fields_and_exception_text():
    record = logging.LogRecord(
        "api",
        logging.ERROR,
        "main.py",
        1,
        "failed for 198.51.100.10",
        (),
        None,
    )
    record.extra_fields = {
        "api_key": "secret-token",
        "actual_headcount": 42,
        "endpoint": "/health",
    }

    payload = json.loads(JSONFormatter().format(record))

    assert "secret-token" not in json.dumps(payload)
    assert "198.51.100.10" not in json.dumps(payload)
    assert "actual_headcount" not in json.dumps(payload)
    assert payload["endpoint"] == "/health"


def test_json_formatter_redacts_exception_tokens_and_paths():
    try:
        raise ValueError("secret-token at C:\\private\\secret-model.json")
    except ValueError:
        record = logging.LogRecord("api", logging.ERROR, "main.py", 1, "Unhandled exception", (), sys.exc_info())

    payload = json.loads(JSONFormatter().format(record))
    rendered = json.dumps(payload)

    assert "secret-token" not in rendered
    assert "private" not in rendered
    assert "secret-model.json" not in rendered
