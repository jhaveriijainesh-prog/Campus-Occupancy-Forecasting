"""
Service Health and Status Endpoints.

Provides health checks, readiness probes, and system status information.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.security import require_read
from app.schemas.health import (
    DetailedHealthResponse,
    HealthResponse,
    LivenessResponse,
    ReadinessResponse,
    ReadinessUnavailableResponse,
    VersionResponse,
)


router = APIRouter()
logger = get_logger(__name__)


def _dependency_status() -> dict:
    """Return structured dependency checks for health and readiness reporting."""
    settings = get_settings()

    parquet_or_csv = lambda path_stem: (settings.processed_data_dir / f"{path_stem}.parquet").exists() or (settings.processed_data_dir / f"{path_stem}.csv").exists()

    checks = {
        "api": "healthy",
        "data_directory": "healthy" if settings.raw_data_dir.exists() else "degraded",
        "processed_directory": "healthy" if settings.processed_data_dir.exists() else "degraded",
        "models_directory": "healthy" if settings.models_dir.exists() else "degraded",
        "configs_directory": "healthy" if settings.configs_dir.exists() else "degraded",
        "rooms_data": "healthy" if parquet_or_csv("rooms") else "missing",
        "occupancy_data": "healthy" if parquet_or_csv("occupancy") else "missing",
        "timetable_data": "healthy" if parquet_or_csv("timetable") else "missing",
        "events_data": "healthy" if parquet_or_csv("events") else "missing",
        "xgboost_model": "healthy" if (settings.experiments_dir / "xgboost" / "model.json").exists() else "missing",
        "xgboost_metadata": "healthy" if (settings.experiments_dir / "xgboost" / "feature_metadata.json").exists() else "missing",
    }

    return checks


@router.get("/health", response_model=HealthResponse, summary="Basic health check")
async def health_check():
    """Basic health check endpoint used by infrastructure and container health probes."""
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "campus-occupancy-api",
    }


@router.get(
    "/health/detailed",
    response_model=DetailedHealthResponse,
    summary="Detailed health check with dependencies",
)
async def detailed_health_check(request: Request, _: str = Depends(require_read)):
    """Detailed health check including dependency verification and missing-artifact reporting."""
    settings = get_settings()
    checks = _dependency_status()
    all_healthy = all(v == "healthy" for v in checks.values())

    return {
        "status": "healthy" if all_healthy else "degraded",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "service": "campus-occupancy-api",
        "version": "1.0.0",
        "checks": checks,
        "environment": settings.app_env,
    }


@router.get(
    "/health/ready",
    response_model=ReadinessResponse,
    responses={503: {"model": ReadinessUnavailableResponse, "description": "Required data or model dependencies are unavailable"}},
    summary="Kubernetes readiness probe",
)
async def readiness_probe():
    """Return 200 only when the required processed data and model artifacts are present."""
    settings = get_settings()
    checks = _dependency_status()
    missing = [name for name, value in checks.items() if value != "healthy"]

    if not missing:
        return {
            "status": "ready",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "checks": checks,
        }

    raise HTTPException(
        status_code=503,
        detail={
            "status": "not_ready",
            "missing_dependencies": missing,
            "checks": checks,
        },
    )


@router.get("/health/live", response_model=LivenessResponse, summary="Kubernetes liveness probe")
async def liveness_probe():
    """Kubernetes liveness probe endpoint."""
    return {"status": "alive", "timestamp": datetime.now(timezone.utc).isoformat()}


@router.get("/version", response_model=VersionResponse, summary="Get service version information")
async def version_info(_: str = Depends(require_read)):
    """Return authenticated version metadata without exposing internal secrets."""
    return {
        "service": "campus-occupancy-api",
        "version": "1.0.0",
        "api_version": "v1",
        "build_date": "2026-09-25",
        "python_version": "3.11+",
        "features": [
            "forecasting",
            "optimization",
            "clustering",
            "analytics",
            "dashboard",
        ],
    }
