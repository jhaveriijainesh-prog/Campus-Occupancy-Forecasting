# ==============================================================================
# BDS-06: Campus Occupancy Forecasting - Development Makefile
# ==============================================================================
# Usage: make <target>
#   make help                 - Show this help message
#   make install              - Install all dependencies
#   make generate-data        - Generate synthetic campus datasets
#   make clean-data           - Run data cleaning & validation pipeline
#   make train-baseline       - Train and evaluate baseline models
#   make train-xgboost        - Train and evaluate XGBoost model
#   make compare              - Compare baseline vs XGBoost forecasts
#   make test                 - Run full test suite with coverage
#   make test-unit            - Run unit tests only
#   make test-integration     - Run integration tests only
#   make test-leakage         - Run temporal leakage prevention tests
#   make test-optimization    - Run optimization invariant tests
#   make lint                 - Run code quality checks (ruff, mypy)
#   make format               - Auto-format code (ruff format, black)
#   make serve-api            - Start FastAPI development server
#   make serve-dashboard      - Start Streamlit dashboard
#   make docker-build         - Build Docker images
#   make docker-up            - Start services with Docker Compose
#   make docker-down          - Stop Docker Compose services
#   make clean                - Remove generated artifacts and cache
# ==============================================================================

.PHONY: help install generate-data clean-data train-baseline train-xgboost compare \
        test test-unit test-integration test-leakage test-optimization \
        lint format serve-api serve-dashboard docker-build docker-up docker-down clean

# Default target
help:
	@echo "BDS-06: Campus Occupancy Forecasting - Available Commands"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}'

install: ## Install all Python dependencies
	pip install --upgrade pip
	pip install -r requirements.txt

generate-data: ## Generate synthetic campus datasets (rooms, timetable, events, occupancy)
	python scripts/generate_data.py --seed 42 --weeks 16 --output-dir data/raw

clean-data: ## Run complete data cleaning & validation pipeline
	python -m app.data.cleaning

train-baseline: ## Run baseline forecasting experiment (HistoricalSeasonalProfile, etc.)
	python scripts/run_baseline.py --data-path data/processed/occupancy.parquet --output-dir experiments/baseline

train-xgboost: ## Train advanced XGBoost forecaster with experiment tracking
	python scripts/train_forecaster.py --data-dir data/processed --output-dir experiments/xgboost --baseline-dir experiments/baseline

compare: ## Compare baseline vs XGBoost forecasts with error slicing
	python scripts/compare_forecasts.py --baseline-path experiments/baseline/test_predictions.parquet --xgboost-path experiments/xgboost/test_predictions.parquet

test: ## Run full test suite with coverage
	pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

test-unit: ## Run unit tests only
	pytest tests/unit -v

test-integration: ## Run integration tests only
	pytest tests/integration -v

test-leakage: ## Run temporal leakage prevention regression tests
	pytest tests/regression/test_leakage.py -v

test-optimization: ## Run optimization invariant tests
	pytest tests/optimization/test_solver.py -v

lint: ## Run code quality checks (ruff + mypy)
	ruff check app/ scripts/ tests/
	mypy app/ scripts/ --ignore-missing-imports

format: ## Auto-format code with ruff and black
	ruff format app/ scripts/ tests/
	black app/ scripts/ tests/

serve-api: ## Start FastAPI development server with hot reload
	uvicorn app.api.main:app --host 0.0.0.0 --port 8000 --reload

serve-dashboard: ## Start Streamlit analytical dashboard
	streamlit run app/dashboard/app.py --server.port 8501 --server.address 0.0.0.0

docker-build: ## Build Docker images for API and Dashboard
	docker compose build

docker-up: ## Start all services with Docker Compose
	docker compose up -d

docker-down: ## Stop Docker Compose services
	docker compose down

docker-logs: ## View Docker Compose logs
	docker compose logs -f

clean: ## Remove generated artifacts, cache, and temporary files
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf htmlcov .coverage
	rm -rf data/processed/*.parquet data/processed/*.csv
	rm -rf experiments/baseline/* experiments/xgboost/* experiments/comparison/*
	rm -rf models/*.joblib models/*.json

# Complete pipeline: data -> clean -> baseline -> xgboost -> compare
pipeline: generate-data clean-data train-baseline train-xgboost compare
	@echo "Complete ML pipeline executed successfully!"

# Development workflow shortcuts
dev-setup: install generate-data clean-data ## One-time development setup
	@echo "Development environment ready!"

quick-test: test-leakage test-optimization test-unit ## Fast test subset for development