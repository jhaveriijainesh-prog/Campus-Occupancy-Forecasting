"""
Domain-specific Exception Hierarchy.

Provides a structured exception hierarchy for the Campus Occupancy Forecasting system,
enabling precise error handling and API error responses.
"""

from typing import Any, Dict, Optional


class CampusOccupancyError(Exception):
    """Base exception for all campus occupancy domain errors."""

    def __init__(
        self,
        message: str,
        error_code: str = "INTERNAL_ERROR",
        details: Optional[Dict[str, Any]] = None,
        status_code: int = 500,
    ):
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.status_code = status_code

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API responses."""
        return {
            "error": self.error_code,
            "message": self.message,
            "details": self.details,
        }


# Configuration & Environment Errors
class ConfigurationError(CampusOccupancyError):
    """Raised when configuration is invalid or missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="CONFIGURATION_ERROR",
            details=details,
            status_code=500,
        )


class EnvironmentError(CampusOccupancyError):
    """Raised when required environment variables are missing."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="ENVIRONMENT_ERROR",
            details=details,
            status_code=500,
        )


# Data & Validation Errors
class DataValidationError(CampusOccupancyError):
    """Raised when data fails validation checks."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="DATA_VALIDATION_ERROR",
            details=details,
            status_code=400,
        )


class DataIntegrityError(CampusOccupancyError):
    """Raised when data integrity constraints are violated."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="DATA_INTEGRITY_ERROR",
            details=details,
            status_code=400,
        )


class DataNotFoundError(CampusOccupancyError):
    """Raised when requested data is not found."""

    def __init__(self, resource: str, identifier: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"{resource} not found: {identifier}",
            error_code="DATA_NOT_FOUND",
            details={"resource": resource, "identifier": identifier, **(details or {})},
            status_code=404,
        )


class DataProcessingError(CampusOccupancyError):
    """Raised when data processing pipeline fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="DATA_PROCESSING_ERROR",
            details=details,
            status_code=500,
        )


# Forecasting & Model Errors
class ModelError(CampusOccupancyError):
    """Base exception for model-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="MODEL_ERROR",
            details=details,
            status_code=500,
        )


class ModelNotTrainedError(ModelError):
    """Raised when attempting to use an untrained model."""

    def __init__(self, model_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Model '{model_name}' has not been trained yet",
            details={"model_name": model_name, **(details or {})},
        )


class ModelNotFoundError(ModelError):
    """Raised when model artifacts are not found."""

    def __init__(self, model_path: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Model not found at path: {model_path}",
            details={"model_path": model_path, **(details or {})},
        )


class ForecastError(ModelError):
    """Raised when forecasting fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="FORECAST_ERROR",
            details=details,
            status_code=500,
        )


class TemporalLeakageError(ModelError):
    """Raised when temporal leakage is detected in features."""

    def __init__(self, feature_name: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Temporal leakage detected in feature: {feature_name}",
            details={"feature_name": feature_name, **(details or {})},
            status_code=400,
        )


# Optimization Errors
class OptimizationError(CampusOccupancyError):
    """Base exception for optimization-related errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="OPTIMIZATION_ERROR",
            details=details,
            status_code=500,
        )


class InfeasibleOptimizationError(OptimizationError):
    """Raised when optimization problem is infeasible."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="INFEASIBLE_OPTIMIZATION",
            details=details,
            status_code=400,
        )


class SolverTimeoutError(OptimizationError):
    """Raised when solver exceeds time limit."""

    def __init__(self, timeout_seconds: float, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Solver timeout after {timeout_seconds} seconds",
            details={"timeout_seconds": timeout_seconds, **(details or {})},
            status_code=504,
        )


class ConstraintViolationError(OptimizationError):
    """Raised when hard constraints are violated."""

    def __init__(self, constraint: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"Hard constraint violated: {constraint}",
            details={"constraint": constraint, **(details or {})},
            status_code=400,
        )


# API & Authentication Errors
class AuthenticationError(CampusOccupancyError):
    """Raised when authentication fails."""

    def __init__(self, message: str = "Authentication failed", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="AUTHENTICATION_ERROR",
            details=details,
            status_code=401,
        )


class AuthorizationError(CampusOccupancyError):
    """Raised when authorization fails."""

    def __init__(self, message: str = "Insufficient permissions", details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="AUTHORIZATION_ERROR",
            details=details,
            status_code=403,
        )


class RateLimitError(CampusOccupancyError):
    """Raised when rate limit is exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message,
            error_code="RATE_LIMIT_EXCEEDED",
            details={"retry_after_seconds": retry_after, **(details or {})},
            status_code=429,
        )


# External Service Errors
class ExternalServiceError(CampusOccupancyError):
    """Raised when external service calls fail."""

    def __init__(self, service: str, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            f"External service '{service}' error: {message}",
            error_code="EXTERNAL_SERVICE_ERROR",
            details={"service": service, **(details or {})},
            status_code=502,
        )


# Utility function for error handling
def handle_exception(exc: Exception) -> CampusOccupancyError:
    """
    Convert any exception to a CampusOccupancyError.

    Args:
        exc: The exception to convert

    Returns:
        CampusOccupancyError instance
    """
    if isinstance(exc, CampusOccupancyError):
        return exc

    return CampusOccupancyError(
        message="Internal server error",
        error_code="INTERNAL_ERROR",
        details={},
        status_code=500,
    )
