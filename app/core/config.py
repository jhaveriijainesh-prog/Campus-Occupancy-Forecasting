"""
Pydantic Application Settings and Environment Management.

Loads configuration from environment variables with sensible defaults.
Supports .env file for local development.
"""

import os
from pathlib import Path
from typing import List, Optional

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

DEFAULT_API_SECRET_KEY = "bds06-super-secret-development-key-change-in-prod"
DEFAULT_API_READ_KEY = "bds06-super-secret-read-only-development-key-change-in-prod"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application Environment
    app_env: str = Field(default="development", description="Environment: development, staging, production")
    debug: bool = Field(default=True, description="Enable debug mode")

    # API Configuration
    api_host: str = Field(default="0.0.0.0", description="API server host")
    api_port: int = Field(default=8000, description="API server port")
    api_secret_key: str = Field(
        default=DEFAULT_API_SECRET_KEY,
        description="Admin secret key for API authentication. In production, supply in .env or a platform secret store; default values are only permitted for development/test.",
    )
    api_read_key: str = Field(
        default=DEFAULT_API_READ_KEY,
        description="Least-privilege dashboard credential for read and forecast routes. In production, supply in .env or a platform secret store; default values are only permitted for development/test.",
    )
    api_cors_origins: List[str] = Field(
        default_factory=lambda: ["http://localhost:8501", "http://localhost:3000"],
        description="Allowed CORS origins. Keep this environment-configurable for future hosted deployments.",
    )
    rate_limit_requests: int = Field(default=100, ge=1, description="Maximum requests per rate-limit window")
    rate_limit_window_seconds: int = Field(default=60, ge=1, description="Rate-limit window duration")

    # Data Directories
    data_dir: Path = Field(default=Path("data"), description="Root data directory")
    raw_data_dir: Path = Field(default=Path("data/raw"), description="Raw data directory")
    processed_data_dir: Path = Field(default=Path("data/processed"), description="Processed data directory")
    models_dir: Path = Field(default=Path("models"), description="Model artifacts directory")
    logs_dir: Path = Field(default=Path("logs"), description="Application logs directory")
    configs_dir: Path = Field(default=Path("configs"), description="Configuration files directory")
    experiments_dir: Path = Field(default=Path("experiments"), description="Experiment artifacts directory")

    # Forecasting Configuration
    forecast_horizon_hours: int = Field(default=1, description="Default forecast horizon in hours")
    default_forecast_horizons: List[int] = Field(
        default=[1, 6, 24], description="Default forecast horizons for multi-horizon prediction"
    )
    confidence_levels: List[float] = Field(
        default=[0.1, 0.5, 0.9], description="Quantile confidence levels for prediction intervals"
    )

    # Model Configuration
    model_random_seed: int = Field(default=42, description="Random seed for reproducibility")
    xgboost_n_estimators: int = Field(default=300, description="XGBoost number of estimators")
    xgboost_learning_rate: float = Field(default=0.05, description="XGBoost learning rate")
    xgboost_max_depth: int = Field(default=6, description="XGBoost max tree depth")
    xgboost_early_stopping_rounds: int = Field(default=40, description="Early stopping patience")

    # Optimization Configuration
    solver_engine: str = Field(default="PULP_CBC_CMD", description="MILP solver engine")
    solver_timeout_seconds: float = Field(default=30.0, description="Solver timeout in seconds")
    solver_mip_gap: float = Field(default=0.02, description="MIP gap tolerance")

    # Monitoring & Logging
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="json", description="Log format: json or text")
    metrics_enabled: bool = Field(default=True, description="Enable metrics collection")
    metrics_port: int = Field(default=9090, description="Prometheus metrics port")

    # Dashboard Configuration
    dashboard_host: str = Field(default="0.0.0.0", description="Dashboard host")
    dashboard_port: int = Field(default=8501, description="Dashboard port")
    fastapi_internal_url: str = Field(default="http://api:8000", description="Internal FastAPI URL for dashboard")
    fastapi_public_url: str = Field(default="http://127.0.0.1:8000", description="Public FastAPI URL")
    dashboard_api_timeout_seconds: float = Field(default=0.5, gt=0, description="Dashboard API request timeout")

    # Academic Calendar Configuration
    semester_start_date: str = Field(default="2026-08-03", description="Semester start date (YYYY-MM-DD)")
    semester_weeks: int = Field(default=16, description="Number of weeks in semester")
    operational_hours_start: int = Field(default=7, description="Campus operational start hour")
    operational_hours_end: int = Field(default=21, description="Campus operational end hour")
    slot_duration_minutes: int = Field(default=60, description="Time slot duration in minutes")
    time_zone: str = Field(default="Asia/Kolkata", description="Campus timezone")

    def get_data_paths(self) -> dict:
        """Return all configured data paths as a dictionary."""
        return {
            "raw": self.raw_data_dir,
            "processed": self.processed_data_dir,
            "models": self.models_dir,
            "logs": self.logs_dir,
            "configs": self.configs_dir,
            "experiments": self.experiments_dir,
        }

    def ensure_directories(self) -> None:
        """Create all configured directories if they don't exist."""
        for path in self.get_data_paths().values():
            path.mkdir(parents=True, exist_ok=True)

    @model_validator(mode="after")
    def validate_production_secrets(self):
        """Protect the production boundary from blank, default, or local-dev secrets."""
        app_env = (self.app_env or "").strip().lower()
        if app_env not in {"development", "test"}:
            local_dev_secrets = {
                DEFAULT_API_SECRET_KEY,
                DEFAULT_API_READ_KEY,
                "local-dev-admin-key",
                "local-dev-read-key",
            }
            if not self.api_secret_key or self.api_secret_key in local_dev_secrets:
                raise ValueError("API_SECRET_KEY must be configured via environment or platform secret store in production")
            if not self.api_read_key or self.api_read_key in local_dev_secrets:
                raise ValueError("API_READ_KEY must be configured via environment or platform secret store in production")
            if self.api_secret_key == self.api_read_key:
                raise ValueError("API_READ_KEY must differ from API_SECRET_KEY in production")
        return self


def get_settings() -> Settings:
    """Get the current environment-backed settings instance.

    The config is intentionally re-read each time so tests and runtime
    environment changes can reflect the latest secret configuration without
    leaving a stale cached snapshot behind. Production ignores the local .env
    file so dev-only keys cannot silently satisfy the runtime requirements.
    """
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    env_file = ".env" if app_env in {"development", "test", ""} else None
    try:
        return Settings(_env_file=env_file)
    except ValueError as exc:
        raise RuntimeError(str(exc)) from exc


# Convenience function for dependency injection
def get_config() -> Settings:
    """FastAPI dependency for settings."""
    return get_settings()
