"""
Structured JSON Logging and Telemetry Setup.

Provides production-ready structured logging with:
- JSON formatting for log aggregation (ELK, Datadog, etc.)
- Correlation ID propagation across async boundaries
- Contextual enrichment (request_id, user_id, room_id, etc.)
- Configurable log levels per module
"""

import json
import logging
import re
import sys
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.core.config import get_settings


# Context variables for correlation ID propagation
correlation_id_var: ContextVar[Optional[str]] = ContextVar("correlation_id", default=None)
request_id_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)
user_id_var: ContextVar[Optional[str]] = ContextVar("user_id", default=None)
room_id_var: ContextVar[Optional[str]] = ContextVar("room_id", default=None)

_SENSITIVE_LOG_KEYS = {
    "api_key", "authorization", "client_host", "forwarded_for", "ip", "ip_address",
    "mac", "mac_address", "device_id", "password", "raw_payload", "payload",
    "actual_headcount", "student_id", "roll_no", "user_id", "room_id",
}
_SENSITIVE_TEXT_PATTERNS = (
    re.compile(r"(?i)(x-api-key|authorization)\s*[:=]\s*[^\s,]+"),
    re.compile(r"(?i)\b(?:secret|token|password|credential)[-_][A-Za-z0-9._-]+\b"),
    re.compile(r"(?i)[A-Za-z]:\\[^\s\"']+"),
    re.compile(r"(?i)\b[A-Za-z0-9._-]+\.(?:json|csv|parquet|pem|key)\b"),
    re.compile(r"(?i)(?:[A-Za-z]:\\|/)[^\s\"']+\.(?:json|csv|parquet|pem|key)"),
    re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b"),
    re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
)


def _sanitize_log_text(value: str) -> str:
    """Redact common secret and identifier patterns from operational log text."""
    result = value
    for pattern in _SENSITIVE_TEXT_PATTERNS:
        result = pattern.sub("[REDACTED]", result)
    return result


def _sanitize_log_fields(fields: dict) -> dict:
    """Drop sensitive fields while retaining low-cardinality operational fields."""
    sanitized = {}
    for key, value in fields.items():
        if key.lower() in _SENSITIVE_LOG_KEYS:
            continue
        if isinstance(value, str):
            sanitized[key] = _sanitize_log_text(value)
        elif isinstance(value, dict):
            sanitized[key] = _sanitize_log_fields(value)
        else:
            sanitized[key] = value
    return sanitized


class JSONFormatter(logging.Formatter):
    """JSON log formatter with structured fields."""

    def __init__(self, service_name: str = "campus-occupancy-api"):
        super().__init__()
        self.service_name = service_name

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        # Base log structure
        log_entry: Dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": _sanitize_log_text(record.getMessage()),
            "service": self.service_name,
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation/context IDs if present
        correlation_id = correlation_id_var.get()
        if correlation_id:
            log_entry["correlation_id"] = correlation_id

        request_id = request_id_var.get()
        if request_id:
            log_entry["request_id"] = request_id

        user_id = user_id_var.get()
        # Add extra fields from record
        if hasattr(record, "extra_fields"):
            log_entry.update(_sanitize_log_fields(record.extra_fields))

        # Add exception info if present
        if record.exc_info:
            log_entry["exception"] = _sanitize_log_text(self.formatException(record.exc_info))

        return json.dumps(log_entry, ensure_ascii=False)


class ContextFilter(logging.Filter):
    """Filter to inject context variables into log records."""

    def filter(self, record: logging.LogRecord) -> bool:
        # Inject context variables as extra fields
        extra = dict(getattr(record, "extra_fields", {}))

        correlation_id = correlation_id_var.get()
        if correlation_id:
            extra["correlation_id"] = correlation_id

        request_id = request_id_var.get()
        if request_id:
            extra["request_id"] = request_id

        user_id = user_id_var.get()
        if user_id:
            extra["user_id"] = user_id

        room_id = room_id_var.get()
        if room_id:
            extra["room_id"] = room_id

        if extra:
            record.extra_fields = extra

        return True


def setup_logging(
    level: str = "INFO",
    json_format: bool = True,
    service_name: str = "campus-occupancy-api",
) -> logging.Logger:
    """
    Configure application-wide structured logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        json_format: Use JSON formatter if True, else plain text
        service_name: Service identifier for log entries

    Returns:
        Configured root logger
    """
    settings = get_settings()

    # Override with settings if not explicitly provided
    level = getattr(settings, "log_level", level)
    json_format = getattr(settings, "log_format", "json") == "json"

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper(), logging.INFO))

    if json_format:
        console_handler.setFormatter(JSONFormatter(service_name=service_name))
    else:
        console_handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )

    console_handler.addFilter(ContextFilter())
    root_logger.addHandler(console_handler)

    # Configure specific loggers
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.INFO)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name."""
    return logging.getLogger(name)


def set_correlation_id(correlation_id: Optional[str] = None) -> str:
    """Set correlation ID for current context. Generates new UUID if not provided."""
    if correlation_id is None:
        correlation_id = str(uuid.uuid4())[:8]
    correlation_id_var.set(correlation_id)
    return correlation_id


def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return correlation_id_var.get()


def set_request_context(
    request_id: Optional[str] = None,
    user_id: Optional[str] = None,
    room_id: Optional[str] = None,
) -> None:
    """Set request context variables."""
    if request_id:
        request_id_var.set(request_id)
    if user_id:
        user_id_var.set(user_id)
    if room_id:
        room_id_var.set(room_id)


def clear_request_context() -> None:
    """Clear all request context variables."""
    request_id_var.set(None)
    user_id_var.set(None)
    room_id_var.set(None)


class LoggingContext:
    """Context manager for structured logging with automatic correlation ID."""

    def __init__(
        self,
        correlation_id: Optional[str] = None,
        request_id: Optional[str] = None,
        user_id: Optional[str] = None,
        room_id: Optional[str] = None,
    ):
        self.correlation_id = correlation_id
        self.request_id = request_id
        self.user_id = user_id
        self.room_id = room_id
        self._previous_correlation_id = None
        self._previous_request_id = None
        self._previous_user_id = None
        self._previous_room_id = None

    def __enter__(self) -> "LoggingContext":
        self._previous_correlation_id = correlation_id_var.get()
        self._previous_request_id = request_id_var.get()
        self._previous_user_id = user_id_var.get()
        self._previous_room_id = room_id_var.get()

        set_correlation_id(self.correlation_id)
        set_request_context(self.request_id, self.user_id, self.room_id)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        # Restore previous context
        correlation_id_var.set(self._previous_correlation_id)
        request_id_var.set(self._previous_request_id)
        user_id_var.set(self._previous_user_id)
        room_id_var.set(self._previous_room_id)
