"""Measure a local authenticated forecast endpoint and persist run provenance."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from urllib.parse import urlparse

import httpx
import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import get_settings


def _sha256(path: Path) -> str:
	checksum = hashlib.sha256()
	with path.open("rb") as source:
		for block in iter(lambda: source.read(1024 * 1024), b""):
			checksum.update(block)
	return checksum.hexdigest()


def benchmark(base_url: str, room_id: str, repeats: int, timeout_seconds: float) -> dict:
	parsed = urlparse(base_url)
	if parsed.scheme not in {"http", "https"} or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
		raise ValueError("API benchmark is restricted to localhost; no external request is made")
	if repeats < 1 or timeout_seconds <= 0:
		raise ValueError("repeats and timeout must be positive")

	settings = get_settings()
	endpoint = f"/api/v1/forecast/predict/{room_id}"
	measurements = []
	statuses = []
	with httpx.Client(
		base_url=base_url.rstrip("/"),
		timeout=timeout_seconds,
		headers={"X-API-Key": settings.api_secret_key},
	) as client:
		started = time.perf_counter()
		cold_response = client.get(endpoint)
		cold_latency_ms = (time.perf_counter() - started) * 1000
		statuses.append(cold_response.status_code)
		for _ in range(repeats):
			started = time.perf_counter()
			response = client.get(endpoint)
			measurements.append((time.perf_counter() - started) * 1000)
			statuses.append(response.status_code)

	generated = datetime.now(timezone.utc)
	run_id = generated.strftime("%Y%m%dT%H%M%S%fZ")
	inputs = {
		"base_url": base_url.rstrip("/"),
		"method": "GET",
		"endpoint_template": "/api/v1/forecast/predict/{room_id}",
		"room_id": room_id,
		"cold_requests": 1,
		"warm_requests": repeats,
		"timeout_seconds": timeout_seconds,
		"authentication": "X-API-Key from local application settings; credential value omitted",
	}
	tracked = [
		"scripts/benchmark_forecast_api.py",
		"app/api/main.py",
		"app/api/routes/forecast.py",
		"app/features/engineering.py",
		"app/forecasting/model.py",
		"data/processed/occupancy.csv",
		"data/processed/rooms.csv",
		"data/processed/events.csv",
		"experiments/xgboost/model.json",
	]
	provenance = {
		relative: _sha256(ROOT_DIR / relative)
		for relative in tracked
		if (ROOT_DIR / relative).exists()
	}
	warm = np.asarray(measurements, dtype=float)
	result = {
		"run_id": run_id,
		"generated_at_utc": generated.isoformat(),
		"environment": {
			"python": platform.python_version(),
			"platform": platform.platform(),
			"cpu_count": __import__("os").cpu_count(),
			"httpx": version("httpx"),
		},
		"inputs": inputs,
		"status_codes": statuses,
		"success": all(status == 200 for status in statuses),
		"latency_ms": {
			"first_request_in_benchmark": cold_latency_ms,
			"warm_p50": float(np.percentile(warm, 50)),
			"warm_p95": float(np.percentile(warm, 95)),
			"warm_p99": float(np.percentile(warm, 99)),
			"warm_max": float(np.max(warm)),
			"warm_samples": measurements,
		},
		"provenance_sha256": provenance,
		"scope": "localhost HTTP wall time including routing, authentication, model inference, and response serialization; no memory/CPU sampling",
		"first_request_caveat": "This process may already be warm; the first measured request is not guaranteed to represent process cold start.",
	}
	output_dir = ROOT_DIR / "experiments" / "advanced_validation"
	output_dir.mkdir(parents=True, exist_ok=True)
	output = output_dir / f"api_benchmark_{run_id}.json"
	output.write_text(json.dumps(result, indent=2, allow_nan=False) + "\n", encoding="utf-8")
	print(json.dumps({"output": str(output.relative_to(ROOT_DIR)), "success": result["success"], "latency_ms": result["latency_ms"]}, indent=2))
	return result


if __name__ == "__main__":
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument("--base-url", default="http://127.0.0.1:8000")
	parser.add_argument("--room-id", default="B01-R101")
	parser.add_argument("--repeats", type=int, default=20)
	parser.add_argument("--timeout-seconds", type=float, default=15)
	args = parser.parse_args()
	benchmark(args.base_url, args.room_id, args.repeats, args.timeout_seconds)