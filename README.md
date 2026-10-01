# BDS-06: Campus Occupancy Forecasting with Spatiotemporal Analytics and Capacity Optimization

**Academic Level:** Third Year B.Sc. Data Science (T.Y. B.Sc. DS) – Semester V Capstone Project  
**System Architecture:** Modular Python application with FastAPI, Streamlit, and Docker Compose  
**Verified MVP:** Synthetic-data utilization analytics, a one-hour XGBoost point forecast, API-backed Overview and Forecast Explorer, and local Compose deployment  

---

## 1. Project Overview

The authoritative capstone brief frames a planning hypothesis: scheduled enrollment and nominal capacity may not reflect actual room use, potentially leaving some spaces underused while others experience peaks. No campus field observations or stakeholder interviews are present in this repository, so this framing is not presented as a measured fact about a specific institution.

The current checked-in prototype demonstrates:
1. **Synthetic data preparation:** Seed-42 room, timetable, event, and hourly occupancy data with validation/cleaning and processed Parquet/CSV artifacts.
2. **Forecasting:** XGBoost room-level one-hour point forecasts evaluated on a chronological holdout; the serving artifact does not provide calibrated quantile intervals or multi-horizon forecasts.
3. **Utilization analytics:** Campus, building, and room SUR, RFU, and WSH through FastAPI and the read-only Streamlit Overview.
4. **Additional analytical modules:** K-Means room clustering, deterministic what-if simulation, a capacity-first greedy allocator, and PuLP/CBC MILP comparison through API/offline evidence. These are not pages in the two-page dashboard MVP.
5. **Local deployment:** FastAPI and Streamlit services orchestrated with Docker Compose and verified locally on 2026-10-01.

The synthetic results are not evidence of real campus occupancy or operational savings. See the [final report](docs/final_report.md) and [requirements-to-evidence matrix](docs/bds06_evidence_matrix.md) for scope and limitations.

### Startup MVP Boundary

The dashboard exposes only `Overview` and `Forecast Explorer`. It supports aggregate campus/building/room metrics and a one-room, one-hour XGBoost point forecast. Clustering, simulation, and room allocation are API/offline analytical capabilities, not dashboard pages. Live sensor integration, model retraining, calibrated forecast intervals, and forecast horizons beyond one hour are not part of the verified startup MVP.

For detailed documentation:
- 📄 **[Requirements Specification (SRS)](docs/01_requirements.md)**
- 🏛️ **[Technical Architecture & Design](docs/02_architecture.md)**
- 📊 **[Evaluation Dossier](docs/evaluation_dossier.md)**
- 🧾 **[Model and System Card](docs/model_system_card.md)**
- ✅ **[Final Evidence Matrix](docs/bds06_evidence_matrix.md)**
- **[Local Runbook](docs/runbook.md)**
- **[Administrator Guide](docs/administrator_guide.md)**
- **[Planner User Guide](docs/user_guide.md)**
- **[Demo Script](docs/demo_script.md)**
- **[Final Report Content](docs/final_report.md)**
- **[Presentation Content](docs/presentation_deck.md)**
- **[Industry Problem Brief](docs/industry_problem_brief.md)**
- **[Current Solution Design Pack](docs/solution_design_pack.md)**
- **[API Examples](docs/runbook_api_examples.md)**
- **[Docker Runtime Evidence](docs/task3_2_runtime_evidence.md)**
- **[Submission Checklist](docs/submission_checklist.md)**

---

## 2. Directory Structure & Component Purposes

The project layout follows a clean, modular monolith design where core analytical modules are decoupled from web and visualization frameworks:

```
Campus-Occupancy-Forecasting/
├── .github/
│   └── workflows/
│       └── ci.yml                 # Automated GitHub Actions CI workflow (tests, coverage, leakage checks)
├── app/                           # Core Application Source Code
│   ├── __init__.py                # Package root
│   ├── api/                       # FastAPI REST Gateway Layer
│   │   ├── deps.py                # Dependency injection providers (auth, services)
│   │   └── routes/                # Endpoint routers (health, data, forecast, optimization, metrics)
│   ├── core/                      # Cross-Cutting Infrastructure
│   │   ├── config.py              # Pydantic BaseSettings environment loader
│   │   ├── exceptions.py          # Domain-specific exception hierarchy
│   │   ├── logging.py             # Structured JSON logger with correlation IDs
│   │   └── security.py            # API key authentication & Zero-PII sanitization
│   ├── data/                      # Ingestion, Cleaning & Harmonization
│   │   ├── cleaner.py             # Outlier detection (IQR), missing imputation, deduplication
│   │   ├── generator.py           # Statistically realistic synthetic campus data generator
│   │   ├── harmonizer.py          # Timetable and sensor time-series temporal alignment
│   │   └── ingestion.py           # Raw CSV/JSON/XLSX file ingestion parsers
│   ├── features/                  # Causal Feature Engineering
│   │   └── engineer.py            # Temporal, cyclical, calendar & causal lag feature transformers
│   ├── forecasting/               # Baselines, XGBoost inference, and evaluation
│   │   ├── baseline.py            # Historical/static/seasonal baselines
│   │   ├── evaluation.py          # Evaluation metrics harness
│   │   └── model.py               # XGBoost artifact loading and point inference
│   ├── clustering/                # Spatial Behavioral Analytics
│   │   └── cluster.py             # Room behavior profiles and K-Means clustering
│   ├── optimization/              # Operations Research & Allocation
│   │   ├── constraints.py         # Hard and soft mathematical constraint definitions
│   │   ├── heuristics.py          # Fast greedy priority allocator fallback engine
│   │   └── solver.py              # PuLP Mixed-Integer Linear Program (MILP) solver
│   ├── simulation/                # Scenario Simulation Engine
│   │   └── simulator.py           # What-if scenario disruption and outage simulator
│   ├── analytics/                 # Metric Formulations & Interpretability
│   │   ├── explainability.py      # TreeSHAP feature attribution & error slicing engine
│   │   └── metrics.py             # Seat Utilization Rate (SUR), RFU, Wasted Seat-Hours (WSH)
│   ├── schemas/                   # Data Contracts & Schemas
│   │   ├── forecast.py            # Forecast request and response Pydantic models
│   │   ├── metrics.py             # Utilization and cluster response schemas
│   │   ├── occupancy.py           # Sensor telemetry and cleaned parquet schemas
│   │   ├── optimization.py        # Constraint definitions and reallocation schemas
│   │   └── timetable.py           # Timetable slot and master schedule schemas
│   ├── services/                  # Application Service Orchestration Layer
│   │   └── pipeline_service.py    # High-level orchestrator connecting data, ML, and solver
│   └── dashboard/                 # Streamlit Overview and Forecast Explorer
│       ├── api_client.py          # Typed HTTP client communicating with FastAPI gateway
│       ├── app.py                 # Multi-page dashboard navigation hub
│       └── views/                 # Overview and forecast MVP views; other modules are not MVP pages
├── configs/                       # Declarative System Configurations
│   ├── config.yaml                # Campus operational parameters, cleaning thresholds, solver limits
│   └── model_params.yaml          # ML hyperparameters, temporal split definitions, feature flags
├── data/                          # Persistent Storage Partition
│   ├── raw/                       # Immutable raw input files (CSV, JSON)
│   └── processed/                 # Cleaned columnar Parquet datasets (timetable, occupancy, rooms)
├── docs/                          # Comprehensive Documentation
│   ├── 01_requirements.md         # Full requirements specification (FR-01 to FR-20, NFRs)
│   └── 02_architecture.md         # Complete system architecture and sequence diagrams
├── models/                        # Reserved model directory placeholder
│   └── .gitkeep                   # Current XGBoost inference artifact is under experiments/xgboost/
├── monitoring/                    # Operational Telemetry & System Monitoring
│   ├── logger_config.json         # Python logging configuration (JSON & console formatters)
│   └── metrics_collector.py       # Latency, p95 timers, and system resource collectors
├── notebooks/                     # Exploratory Data Science Research
│   └── .gitkeep                   # Jupyter notebooks for exploratory analysis and experiments
├── scripts/                       # Automation & Batch Execution Scripts
│   ├── evaluate_models.py         # Batch model training and benchmark table generation
│   ├── generate_synthetic_data.py # Synthetic campus dataset generation utility
│   └── run_pipeline.py            # End-to-end data ingestion, cleaning, and optimization script
├── tests/                         # Automated Testing Harness
│   ├── conftest.py                # Pytest fixtures, test data generators, and mock environments
│   ├── integration/               # API route integration tests via TestClient
│   ├── optimization/              # Optimization invariant tests (0 hard constraint violations)
│   ├── regression/                # Strict temporal split and causal leakage assertions
│   └── unit/                      # Unit tests for schemas, cleaning, and math formulas
├── .env.example                   # Environment configuration template
├── .gitignore                     # Git ignore rules for Python, Parquet, and models
├── Dockerfile                     # Multi-purpose container image for API and Dashboard
├── docker-compose.yml             # Orchestration for FastAPI and Streamlit services
└── requirements.txt               # Python dependency constraints (minimum versions, not exact pins)
```

---

## 3. Quickstart & Local Setup

### 3.1 Prerequisites
- Python 3.11 or higher
- Git
- Docker and Docker Compose (recommended for containerized execution)

### 3.2 Local Environment Installation
```bash
# 1. Clone repository and navigate to root
cd Campus-Occupancy-Forecasting

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# 3. Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

In PowerShell, use `Copy-Item .env.example .env` to copy the template and `.\.venv\Scripts\Activate.ps1` to activate the virtual environment. `.env.example` contains development defaults only; use private, distinct credentials and do not expose them in logs or screenshots.

### 3.3 Running via Docker Compose (Recommended)
```bash
# Build and run all services
docker compose up --build -d

# Services will be accessible at:
# - Streamlit Analytical Dashboard: http://localhost:8501
# - FastAPI Interactive API Docs:    http://localhost:8000/docs
# - API Healthcheck:                 http://localhost:8000/api/v1/health
```

#### Stop and diagnose
```bash
docker compose ps
docker compose logs --tail=100 api dashboard
curl.exe -i http://localhost:8000/api/v1/health/ready
docker compose down
```

`/api/v1/health` confirms the API process is responding; `/api/v1/health/ready` checks required processed data and forecast artifacts. A `503` readiness response lists missing dependencies. If a dependency is missing, verify the corresponding repository files and Compose mounts before restarting the stack. The two-service stack was built, started, exercised, stopped, rebuilt, and restarted on 2026-10-01 with Docker Desktop 4.93.0, Engine 29.8.1, and Compose 5.5.1. This is local runtime evidence, not production hosting evidence.

### 3.4 Running Automated Tests
```bash
# Run complete test suite with coverage
pytest tests/ --cov=app --cov-report=term-missing

# Run temporal leakage prevention tests only
pytest tests/regression/test_leakage.py -v

# Run optimization invariant tests only
pytest tests/optimization/test_solver.py -v
```

---

## 4. Key Architectural Guarantees
- **Privacy boundary:** The ingestion validator rejects configured PII-like columns; the checked-in dataset is synthetic and aggregate. This is not an institutional privacy certification.
- **Temporal causal controls:** Chronological split and causal-lag invariants are checked by the leakage test suite; this is evidence for the tested paths, not proof of all future data pipelines.
- **Allocation constraints:** The current solver enforces room capacity, eligible room type when specified, one assignment per session, and no overlapping bookings in one room. Broader travel/equipment/accessibility requirements remain incomplete.

## 5. Evidence and Limitations
- [Evaluation dossier](docs/evaluation_dossier.md) records measured forecast, clustering, scenario, optimization, and explainability results.
- [Model and system card](docs/model_system_card.md) documents intended use, assumptions, limitations, and reproducibility.
- [Security review](docs/security_review.md) records verified controls and remaining risks.
- [BDS-06 evidence matrix](docs/bds06_evidence_matrix.md) maps requirements to implementation and evidence.
- Docker Compose runtime is locally verified as recorded in `docs/release_notes.md`; public hosting and production hardening are not claimed.
