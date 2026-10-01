"""Bounded, low-cardinality request telemetry for the API process."""

from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
from typing import Any

import numpy as np


class RequestMetrics:
	"""Aggregate request counts and recent latency samples by route template."""

	def __init__(self, sample_capacity: int = 1000) -> None:
		if sample_capacity < 1:
			raise ValueError("sample_capacity must be positive")
		self._sample_capacity = sample_capacity
		self._counts: dict[tuple[str, str], dict[str, int]] = defaultdict(
			lambda: {"requests": 0, "4xx": 0, "5xx": 0}
		)
		self._latencies: dict[tuple[str, str], deque[float]] = defaultdict(
			lambda: deque(maxlen=sample_capacity)
		)
		self._lock = Lock()

	def record_request(self, method: str, route: str, status_code: int, duration_ms: float) -> None:
		"""Record one completed request without retaining request values or headers."""
		key = (method.upper(), route)
		with self._lock:
			counts = self._counts[key]
			counts["requests"] += 1
			if 400 <= status_code < 500:
				counts["4xx"] += 1
			elif status_code >= 500:
				counts["5xx"] += 1
			self._latencies[key].append(max(0.0, float(duration_ms)))

	def snapshot(self) -> dict[str, Any]:
		"""Return process-local counts and latency percentiles by route template."""
		with self._lock:
			result: dict[str, Any] = {}
			for method, route in sorted(self._counts):
				key = (method, route)
				latencies = np.asarray(self._latencies[key], dtype=float)
				result[f"{method} {route}"] = {
					**self._counts[key],
					"latency_samples_retained": int(len(latencies)),
					"latency_sample_capacity": self._sample_capacity,
					"latency_ms_p50": float(np.percentile(latencies, 50)) if len(latencies) else None,
					"latency_ms_p95": float(np.percentile(latencies, 95)) if len(latencies) else None,
					"latency_ms_p99": float(np.percentile(latencies, 99)) if len(latencies) else None,
				}
			return result

	def reset(self) -> None:
		"""Clear observations; intended for deterministic tests and process resets."""
		with self._lock:
			self._counts.clear()
			self._latencies.clear()
