"""
FastAPI Application Entry Point.

Main application factory with all routes, middleware, and lifecycle events.
"""

from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from uuid import uuid4

from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import clustering, data, forecast, health, metrics, optimization, simulation
from app.core.config import get_settings
from app.core.exceptions import CampusOccupancyError, handle_exception
from app.core.logging import LoggingContext, get_logger, setup_logging
from app.core.security import rate_limit_dependency
from monitoring.metrics_collector import RequestMetrics


logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown."""
    settings = get_settings()

    # Startup
    logger.info("Starting Campus Occupancy Forecasting API", extra={"version": "1.0.0"})
    settings.ensure_directories()

    # Initialize logging
    setup_logging(level=settings.log_level, json_format=settings.log_format == "json")

    logger.info("Application startup complete")

    yield

    # Shutdown
    logger.info("Shutting down Campus Occupancy Forecasting API")


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = get_settings()

    app = FastAPI(
        title="Campus Occupancy Forecasting API",
        description="Spatiotemporal occupancy forecasting and capacity optimization for university campuses",
        version="1.0.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
        lifespan=lifespan,
    )
    app.state.request_metrics = RequestMetrics()

    @app.middleware("http")
    async def request_telemetry(request: Request, call_next):
        started = perf_counter()
        request_id = uuid4().hex
        status_code = 500
        with LoggingContext(request_id=request_id):
            try:
                response = await call_next(request)
                status_code = response.status_code
                response.headers["X-Request-ID"] = request_id
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["Referrer-Policy"] = "no-referrer"
                return response
            finally:
                route = request.scope.get("route")
                route_template = getattr(route, "path", "unmatched")
                duration_ms = (perf_counter() - started) * 1000
                app.state.request_metrics.record_request(
                    request.method, route_template, status_code, duration_ms,
                )
                logger.info(
                    "API request completed",
                    extra={
                        "extra_fields": {
                            "method": request.method,
                            "endpoint": route_template,
                            "duration_ms": round(duration_ms, 3),
                            "status_code": status_code,
                        },
                    },
                )

    # CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.api_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Global exception handler
    @app.exception_handler(CampusOccupancyError)
    async def campus_exception_handler(request: Request, exc: CampusOccupancyError):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict(),
        )

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception", extra={"path": request.url.path})
        handled = handle_exception(exc)
        return JSONResponse(
            status_code=handled.status_code,
            content=handled.to_dict(),
        )

    # Include routers
    app.include_router(health.router, prefix="/api/v1", tags=["Health"])
    rate_limit = Depends(rate_limit_dependency)
    app.include_router(data.router, prefix="/api/v1/data", tags=["Data"], dependencies=[rate_limit])
    app.include_router(forecast.router, prefix="/api/v1/forecast", tags=["Forecasting"], dependencies=[rate_limit])
    app.include_router(optimization.router, prefix="/api/v1/optimize", tags=["Optimization"], dependencies=[rate_limit])
    app.include_router(metrics.router, prefix="/api/v1/metrics", tags=["Metrics"], dependencies=[rate_limit])
    app.include_router(clustering.router, prefix="/api/v1/clustering", tags=["Clustering"], dependencies=[rate_limit])
    app.include_router(simulation.router, prefix="/api/v1/simulation", tags=["Simulation"], dependencies=[rate_limit])

    # Root endpoint
    @app.get("/", include_in_schema=False)
    async def root():
        return {
            "service": "Campus Occupancy Forecasting API",
            "version": "1.0.0",
            "status": "operational",
            "docs": "/docs",
            "health": "/api/v1/health",
        }

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        "app.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
    )