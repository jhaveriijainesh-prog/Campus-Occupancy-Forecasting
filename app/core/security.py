"""
API Key Authentication and Zero-PII Sanitization.

Provides:
- API key based authentication for FastAPI endpoints
- PII detection and sanitization for logs and data exports
- Request validation and rate limiting utilities
"""

import hashlib
import re
import time
from threading import Lock
from typing import Optional, Set

from fastapi import Depends, Header, HTTPException, Request, status
from fastapi.security import APIKeyHeader

from app.core.config import DEFAULT_API_SECRET_KEY, DEFAULT_API_READ_KEY, get_settings
from app.core.exceptions import AuthenticationError, AuthorizationError
from app.core.logging import get_logger


logger = get_logger(__name__)

# API Key header scheme
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

# PII Patterns for detection and sanitization
PII_PATTERNS = {
    "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),
    "phone": re.compile(r"\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
    "student_id": re.compile(r"\b(?:STU|STUDENT)[-\s]?\d{6,10}\b", re.IGNORECASE),
    "mac_address": re.compile(r"\b(?:[0-9A-Fa-f]{2}[:-]){5}(?:[0-9A-Fa-f]{2})\b"),
    "ip_address": re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b"),
    "ssn": re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
    "credit_card": re.compile(r"\b(?:\d{4}[-\s]?){3}\d{4}\b"),
    "api_key": re.compile(r"\b(?:sk|pk|api)[-_]?[a-zA-Z0-9]{20,}\b"),
}

# Allowed fields that can contain PII-like patterns (false positives)
PII_ALLOWLIST_FIELDS = {
    "room_id", "building_id", "course_code", "instructor_id",
    "observation_id", "timetable_id", "event_id",
}


def sanitize_pii(text: str, replacement: str = "[REDACTED]") -> str:
    """
    Sanitize PII from text using regex patterns.

    Args:
        text: Input text to sanitize
        replacement: String to replace PII with

    Returns:
        Sanitized text with PII replaced
    """
    if not isinstance(text, str):
        return text

    sanitized = text
    for pii_type, pattern in PII_PATTERNS.items():
        sanitized = pattern.sub(replacement, sanitized)

    return sanitized


def sanitize_dict(data: dict, replacement: str = "[REDACTED]") -> dict:
    """
    Recursively sanitize PII from dictionary values.

    Args:
        data: Dictionary to sanitize
        replacement: String to replace PII with

    Returns:
        Sanitized dictionary
    """
    if not isinstance(data, dict):
        return data

    sanitized = {}
    for key, value in data.items():
        if key.lower() in PII_ALLOWLIST_FIELDS:
            sanitized[key] = value
        elif isinstance(value, str):
            sanitized[key] = sanitize_pii(value, replacement)
        elif isinstance(value, dict):
            sanitized[key] = sanitize_dict(value, replacement)
        elif isinstance(value, list):
            sanitized[key] = [
                sanitize_dict(item, replacement) if isinstance(item, dict)
                else sanitize_pii(item, replacement) if isinstance(item, str)
                else item
                for item in value
            ]
        else:
            sanitized[key] = value

    return sanitized


def hash_sensitive_value(value: str, salt: str = "campus-occupancy") -> str:
    """
    Create a deterministic hash of a sensitive value for logging/identification.

    Args:
        value: Value to hash
        salt: Salt for hashing

    Returns:
        Truncated SHA256 hash
    """
    combined = f"{salt}:{value}"
    return hashlib.sha256(combined.encode()).hexdigest()[:16]


class APIKeyManager:
    """Manages API key validation and permissions."""

    def __init__(self):
        self.settings = get_settings()
        self._valid_keys: Set[str] = set()
        self._key_permissions: dict = {}
        self._load_keys()

    def _load_keys(self) -> None:
        """Load API keys from environment/settings."""
        app_env = self.settings.app_env.casefold()
        master_key = self.settings.api_secret_key
        read_key = self.settings.api_read_key

        if app_env not in {"development", "test"}:
            if not master_key or master_key == DEFAULT_API_SECRET_KEY:
                raise RuntimeError("API_SECRET_KEY must be configured via environment or platform secret store in production")
            if not read_key or read_key == DEFAULT_API_READ_KEY:
                raise RuntimeError("API_READ_KEY must be configured via environment or platform secret store in production")

        if not master_key:
            master_key = DEFAULT_API_SECRET_KEY
        if not read_key:
            read_key = DEFAULT_API_READ_KEY

        self._valid_keys.add(master_key)
        self._key_permissions[master_key] = {"admin", "read", "write", "forecast", "optimize"}

        if read_key == master_key:
            raise RuntimeError("API_READ_KEY must differ from API_SECRET_KEY")
        self._valid_keys.add(read_key)
        self._key_permissions[read_key] = {"read", "forecast"}

        if app_env in {"development", "test"}:
            legacy_master = DEFAULT_API_SECRET_KEY
            legacy_read = DEFAULT_API_READ_KEY
            if legacy_master != master_key:
                self._valid_keys.add(legacy_master)
                self._key_permissions[legacy_master] = {"admin", "read", "write", "forecast", "optimize"}
            if legacy_read != read_key:
                self._valid_keys.add(legacy_read)
                self._key_permissions[legacy_read] = {"read", "forecast"}

        # Additional keys can be added via environment variable
        # API_KEYS="key1:read,write;key2:admin"
        # This is a simplified implementation

    def validate_key(self, api_key: str) -> bool:
        """Validate an API key."""
        return api_key in self._valid_keys

    def get_permissions(self, api_key: str) -> Set[str]:
        """Get permissions for an API key."""
        return self._key_permissions.get(api_key, set())

    def has_permission(self, api_key: str, permission: str) -> bool:
        """Check if API key has a specific permission."""
        return permission in self.get_permissions(api_key)


# Global API key manager instance
_api_key_manager = APIKeyManager()


async def get_api_key(
    api_key: Optional[str] = Depends(api_key_header),
    request: Request = None,
) -> str:
    """
    FastAPI dependency to extract and validate API key.

    Args:
        api_key: API key from X-API-Key header
        request: FastAPI request object

    Returns:
        Validated API key

    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not api_key:
        logger.warning("Missing API key")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required. Provide via X-API-Key header.",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    if not _api_key_manager.validate_key(api_key):
        logger.warning("Invalid API key attempt")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "ApiKey"},
        )

    return api_key


def require_permission(permission: str):
    """
    FastAPI dependency factory for permission-based authorization.

    Args:
        permission: Required permission string

    Returns:
        Dependency function that validates permission
    """
    async def _check_permission(api_key: str = Depends(get_api_key)) -> str:
        if not _api_key_manager.has_permission(api_key, permission):
            logger.warning(
                "Permission denied",
                extra={"extra_fields": {"required_permission": permission}},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}",
            )
        return api_key

    return _check_permission


# Convenience dependencies for common permissions
require_read = require_permission("read")
require_write = require_permission("write")
require_forecast = require_permission("forecast")
require_optimize = require_permission("optimize")
require_admin = require_permission("admin")


def get_client_identifier(request: Request) -> str:
    """
    Get a unique identifier for the client (for rate limiting).

    Args:
        request: FastAPI request object

    Returns:
        Client identifier string
    """
    # Prefer API key if available
    api_key = request.headers.get("X-API-Key")
    if api_key:
        return hash_sensitive_value(api_key)

    # Fall back to IP address
    client_host = request.client.host if request.client else "unknown"
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_host = forwarded_for.split(",")[0].strip()

    return hash_sensitive_value(client_host, salt="rate-limit")


class RateLimiter:
    """Simple in-memory rate limiter (use Redis in production)."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        if max_requests < 1 or window_seconds < 1:
            raise ValueError("rate limiter limits must be positive")
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict = {}
        self._lock = Lock()

    def check_rate_limit(self, identifier: str) -> tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            identifier: Client identifier

        Returns:
            Tuple of (allowed: bool, retry_after_seconds: int)
        """
        now = time.monotonic()
        window_start = now - self.window_seconds
        with self._lock:
            active = [ts for ts in self._requests.get(identifier, []) if ts > window_start]
            if len(active) >= self.max_requests:
                oldest = min(active)
                retry_after = int(oldest + self.window_seconds - now) + 1
                self._requests[identifier] = active
                return False, max(retry_after, 1)
            active.append(now)
            self._requests[identifier] = active
            return True, 0

    def reset(self) -> None:
        """Clear counters for deterministic tests and process resets."""
        with self._lock:
            self._requests.clear()


# Global rate limiter instance
_rate_limiter = RateLimiter(
    max_requests=get_settings().rate_limit_requests,
    window_seconds=get_settings().rate_limit_window_seconds,
)


async def rate_limit_dependency(request: Request) -> None:
    """
    FastAPI dependency for rate limiting.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If rate limit exceeded
    """
    identifier = get_client_identifier(request)
    allowed, retry_after = _rate_limiter.check_rate_limit(identifier)

    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )


def sanitize_for_logging(data: dict) -> dict:
    """
    Sanitize data dictionary for safe logging.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data safe for logging
    """
    return sanitize_dict(data)


def sanitize_for_export(data: dict) -> dict:
    """
    Sanitize data dictionary for export (CSV, JSON, etc.).

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data safe for export
    """
    return sanitize_dict(data)
