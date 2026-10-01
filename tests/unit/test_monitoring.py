"""Tests for bounded request telemetry and API middleware integration."""

import json
import logging

from fastapi.testclient import TestClient

from app.api.main import create_app
from app.core.logging import ContextFilter, JSONFormatter, LoggingContext
from monitoring.metrics_collector import RequestMetrics


def test_request_metrics_aggregate_status_and_bound_latency_samples():
	metrics = RequestMetrics(sample_capacity=2)
	metrics.record_request("get", "/api/v1/rooms/{room_id}", 200, 10)
	metrics.record_request("GET", "/api/v1/rooms/{room_id}", 422, 20)
	metrics.record_request("GET", "/api/v1/rooms/{room_id}", 503, 30)

	entry = metrics.snapshot()["GET /api/v1/rooms/{room_id}"]
	assert entry["requests"] == 3
	assert entry["4xx"] == 1
	assert entry["5xx"] == 1
	assert entry["latency_samples_retained"] == 2
	assert entry["latency_sample_capacity"] == 2
	assert entry["latency_ms_p50"] == 25


def test_api_middleware_records_route_template_and_request_id():
	app = create_app()
	client = TestClient(app)

	response = client.get("/api/v1/health?diagnostic=not-a-metric-label")

	assert response.status_code == 200
	assert response.headers["X-Request-ID"]
	metrics = app.state.request_metrics.snapshot()
	entry = metrics["GET /health"]
	assert entry["requests"] == 1
	assert entry["4xx"] == 0
	assert entry["5xx"] == 0
	assert "diagnostic" not in " ".join(metrics)


def test_json_request_log_keeps_telemetry_and_context_fields():
	record = logging.LogRecord("api", logging.INFO, "main.py", 1, "API request completed", (), None)
	record.extra_fields = {"endpoint": "/health", "duration_ms": 1.25, "status_code": 200}

	with LoggingContext(request_id="request-123"):
		ContextFilter().filter(record)
		payload = json.loads(JSONFormatter().format(record))

	assert payload["request_id"] == "request-123"
	assert payload["endpoint"] == "/health"
	assert payload["duration_ms"] == 1.25
	assert payload["status_code"] == 200