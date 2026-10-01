# Campus Occupancy Forecasting Startup MVP Tasks

## MVP Definition

**Selected slice:** A facilities planner can open the Streamlit dashboard, confirm the API is live and ready, inspect campus/building/room utilization metrics, request a forecast for one or more rooms over a bounded horizon, and understand the result through a room time-series view. The same workflow is usable through documented FastAPI JSON endpoints.

**Primary users:** Facilities/space planner and technical operator. The MVP is read-only for operational data and forecasts; ingestion and retraining remain controlled setup jobs until the read path is reliable.

**Original requirement anchors:**
- FR-03.1-03.4: SUR, RFU, WSH and campus/building/department/time slices.
- FR-04.1, FR-04.3-04.4: bounded multi-horizon occupancy forecasts, prediction intervals, and temporal features.
- FR-09.1: campus heatmap and room time-series explorer.
- FR-10.1-10.2: health, metrics, forecast routers and structured OpenAPI JSON.
- FR-11.1-11.2: pytest unit/integration coverage.
- FR-12.1-12.3: request validation and actionable 422 responses.
- FR-13.1-13.4: authenticated sensitive routes, zero-PII boundary, and rate limiting.
- FR-15.1-15.4: strict temporal split and leakage tests.
- FR-17.1-17.3: structured logs, latency, and error records.
- FR-18.1-18.4: reproducible Docker Compose execution.
- NFR-01, NFR-04, NFR-05, NFR-07, NFR-08: interactive latency, privacy, graceful failures, maintainability, and container portability.

**Preserved architecture:** Keep the existing modular monolith: `app/data`, `app/features`, `app/forecasting`, `app/analytics`, `app/schemas`, `app/api`, and `app/dashboard`; the dashboard communicates with FastAPI through `app/dashboard/api_client.py` and does not read model/storage internals directly (Architecture sections 1, 2, 4, 8, and 9).

**Explicitly deferred from startup MVP:** clustering, optimization/MILP, what-if simulation, SHAP UI, model dossier/model cards, arbitrary file upload, live sensor integrations, user administration, and write/retraining endpoints. These remain roadmap work under FR-05, FR-06, FR-07, FR-09.1's optimizer/simulation/diagnostics portions, FR-13.2's Planner/Admin workflows, FR-16, and FR-19-20.

## Phased Sequence

### Phase 0: Baseline and operational contract

### [x] Task 0.1: Establish the runnable baseline
**Description:** Install the pinned project dependencies in the supported environment, run the existing test command, and document the actual data/model artifacts used by local and Docker runs. Resolve only blockers required to execute the MVP checks; do not refactor unrelated modules.

**Acceptance criteria:**
- `pytest tests/ --cov=app --cov-report=term-missing` has a recorded result and failures are classified as implementation gaps, environment gaps, or regressions.
- The supported local Python version and dependency installation path are explicit and consistent with README section 3.1.
- `data/processed` and `experiments/xgboost` artifact prerequisites for forecast/readiness are documented.

**Evidence checks:** `python --version`; `pip install -r requirements.txt`; `pytest tests/ --cov=app --cov-report=term-missing`; `docker compose config`.

**Dependencies:** None.

**References:** README sections 3.1-3.4; FR-11; FR-18; Architecture sections 2 and 14.

### Phase 1: API read path

### [x] Task 1.1: Implement shared schemas and dataset access for the MVP
**Description:** Replace the empty forecast/metrics response contracts and service shell with typed Pydantic models and a small read-only service that loads the existing processed parquet files and model metadata. Keep paths configuration-driven through `Settings`; return domain errors rather than leaking pandas/file exceptions.

**Acceptance criteria:**
- Forecast requests validate non-empty room IDs, ISO timestamps, supported horizons, and confidence levels; invalid payloads return structured HTTP 422 details.
- Metrics responses have stable fields for SUR, RFU, WSH, scope, time window, and the source data timestamp.
- Missing processed data or model artifacts produces an actionable HTTP 503 response and does not crash the process.
- No individual identifiers, IP addresses, or MAC addresses are accepted or returned.

**Evidence checks:** Pydantic boundary tests; missing-artifact tests; response schema/OpenAPI validation; PII field rejection test.

**Dependencies:** Task 0.1.

**References:** FR-03; FR-04; FR-12; FR-13.3; Architecture sections 4.1-4.2, 8, and 10.

### [x] Task 1.2: Complete health, readiness, and version behavior
**Description:** Make `/api/v1/health`, `/api/v1/health/detailed`, `/api/v1/health/ready`, `/api/v1/health/live`, and `/api/v1/version` accurately report API, processed-data, and forecast-model availability. Align readiness semantics with what the forecast and metrics routes actually require.

**Acceptance criteria:**
- Liveness and basic health remain fast and return stable JSON.
- Readiness returns 200 only when required processed data and model artifacts are available; otherwise returns 503 with named missing dependencies.
- Detailed health distinguishes healthy, missing, and degraded checks and exposes no secrets.
- OpenAPI includes the health contracts when debug/docs are enabled.

**Evidence checks:** FastAPI `TestClient` tests for healthy, missing-artifact, and malformed configuration cases; `GET /api/v1/health/ready`; OpenAPI snapshot/contract assertion.

**Dependencies:** Task 1.1.

**References:** FR-10.1-10.2; FR-17; FR-18.3; Architecture sections 2, 8, and 14; README section 3.3.

### [x] Task 1.3: Implement utilization metrics endpoint
**Description:** Implement the existing `/api/v1/metrics` router for read-only campus, building, and room queries over a bounded time window. Calculate SUR, RFU, and WSH using the formulas in the requirements and support time-of-day/day-of-week filters where the available data supports them.

**Acceptance criteria:**
- `GET /api/v1/metrics/utilization` returns deterministic values for campus, building, and room scopes.
- SUR, RFU, and WSH match hand-calculated fixtures, including zero-capacity/empty-data handling without division errors.
- Invalid room/building/time-window filters return 4xx responses with actionable details.
- A query cannot expose raw telemetry rows or PII.

**Evidence checks:** `tests/unit/test_metrics.py` mathematical fixtures; API integration tests for each scope and invalid filters; response-time measurement on the repository fixture.

**Dependencies:** Tasks 0.1 and 1.1.

**References:** FR-03.1-03.4; FR-10.1; FR-11.2; FR-12.2-12.3; verification matrix item 3.

### [x] Task 1.4: Make forecast inference operational and honest about horizons
**Description:** Complete `/api/v1/forecast/predict` and the single-room route around the existing `OccupancyForecaster` and `FeatureEngineer`. Ensure the requested horizon is either genuinely honored by the feature/model path or explicitly constrained to the supported artifact capability; do not label scaled point predictions as calibrated quantiles unless the model artifact supports them.

**Acceptance criteria:**
- Single-room and batch requests return stable room, timestamp, horizon, model version, point prediction, and interval fields.
- Predictions are non-negative and do not exceed known room capacity.
- Unknown rooms return 404; unavailable data/model artifacts return 503; malformed confidence levels return 422.
- The response states the supported horizon semantics and generated timestamp; p10/p50/p90 ordering is guaranteed when intervals are provided.
- `GET /api/v1/forecast/model/info` reports artifact metadata without exposing filesystem internals.

**Evidence checks:** API integration tests with the checked-in artifact; interval-order and capacity-boundary tests; a bounded p95 latency check for one-room inference aligned to NFR-01.

**Dependencies:** Tasks 0.1, 1.1, and 1.2.

**References:** FR-04.1-04.4; FR-08.1-08.2; FR-10.1; FR-15; NFR-01; Architecture sections 6, 6.2, and 8.

### [x] Task 1.5: Enforce the read-only security and operational boundary
**Description:** Apply the existing API-key/read dependency patterns consistently to forecast, metrics, detailed health, and version routes; retain rate limiting on non-health routes. Add request correlation and structured duration/status logging at the API boundary.

**Acceptance criteria:**
- Read routes require the documented viewer/read credential where configured; health liveness/basic health remain suitable for container health checks.
- Missing/invalid credentials return consistent 401/403 responses without revealing secrets.
- Repeated requests above the configured limit receive a controlled 429 response.
- JSON logs include timestamp, level, service, endpoint, request ID/correlation ID, duration, and status code; unhandled exceptions log stack traces and return structured errors.

**Evidence checks:** auth and rate-limit integration tests; log-record shape test; exception-handler test; Docker healthcheck still succeeds.

**Dependencies:** Tasks 1.2-1.4.

**References:** FR-13.1-13.4; FR-17.1-17.3; NFR-04-05; Architecture sections 1.2, 11, and 12.

### Phase 2: Usable dashboard workflow

### [x] Task 2.1: Build the typed dashboard API client and failure states
**Description:** Implement `app/dashboard/api_client.py` as the only dashboard-to-backend gateway. Add typed calls for health/readiness, metrics, forecast, and model info, with configured base URL, timeout, auth header, and user-safe error messages.

**Acceptance criteria:**
- The client can call every MVP API read route using the Docker internal URL and local public URL configuration.
- Timeout, 401/403, 404, 422, 429, and 503 responses render as actionable dashboard states rather than uncaught exceptions.
- Client response parsing is covered with representative JSON fixtures.

**Evidence checks:** client unit tests with mocked HTTP responses; local configuration test; dashboard startup smoke test with API unavailable.

**Dependencies:** Tasks 1.2-1.5.

**References:** FR-09.1; FR-10.1-10.2; FR-13; Architecture section 9; README section 3.3.

### [x] Task 2.2: Implement the operational overview page
**Description:** Replace the empty Streamlit entrypoint/overview view with a compact planner workflow: service/readiness indicator, campus KPI values, selected building/room filters, and an occupancy density visualization based on metrics data. Keep the view read-only and avoid direct storage/model access.

**Acceptance criteria:**
- A user can open the dashboard and see whether the API is ready, current data/model status, and campus-level SUR/RFU/WSH.
- Building and room filters update the displayed metrics without page crashes.
- Empty, degraded, unauthorized, and unavailable API states are visible and understandable.
- The page works at the documented `http://localhost:8501` endpoint and remains usable on a narrow viewport.

**Evidence checks:** Streamlit smoke test or scripted component test; browser/Playwright capture of the overview with seeded data; API-call audit confirming all data comes through `APIClient`.

**Dependencies:** Tasks 1.3, 1.5, 2.1.

**References:** FR-09.1; FR-10; NFR-05; Architecture sections 2 and 9.

### [x] Task 2.3: Implement the room forecast explorer
**Description:** Implement the forecasting view with room selection, bounded horizon control, forecast request, actual/scheduled context when available, and point/interval time-series visualization. Label the model version and forecast timestamp.

**Acceptance criteria:**
- A user can select a valid room and horizon, request a forecast, and see a readable time-series result.
- Prediction intervals are visually distinct and never rendered with reversed bounds.
- Validation and service errors are shown inline with a retry path; no raw traceback is shown to the user.
- The view does not claim unsupported real-time, 7-14 day, or calibrated uncertainty behavior.

**Evidence checks:** forecast view smoke test with mocked API; browser capture for success and API-unavailable states; one end-to-end dashboard-to-FastAPI request against seeded artifacts.

**Dependencies:** Tasks 1.4, 2.1, and 2.2.

**References:** FR-04.1, FR-04.3-04.4; FR-09.1; FR-10.2; NFR-01; Architecture sections 6 and 9.

### Phase 3: Release hardening and handoff

### [x] Task 3.1: Add MVP integration, regression, and leakage gates
**Description:** Replace placeholder integration tests and add focused route tests for health, metrics, forecast, auth, validation, error responses, and OpenAPI. Preserve and run the existing forecaster, baseline, cleaning, optimization, and leakage suites; add only tests needed to protect the MVP contract.

**Acceptance criteria:**
- `tests/integration/test_api.py` exercises the complete MVP read workflow through `TestClient`.
- Existing leakage assertions prove train/validation/test ordering and causal lag behavior (FR-15.1-15.4).
- Metric correctness, forecast bounds, auth, and graceful dependency failure are covered.
- Coverage is reported honestly; the NFR-07 85% target is a release goal, not a reason to hide unimplemented scope.

**Evidence checks:** `pytest tests/ --cov=app --cov-report=term-missing`; `pytest tests/integration -v`; `pytest tests/regression/test_leakage.py -v`; OpenAPI route assertion.

**Dependencies:** Tasks 1.1-1.5 and 2.1-2.3.

**References:** FR-11.1-11.2; FR-15.1-15.4; NFR-07; verification matrix items 9-15.

### [x] Task 3.2: Make Docker Compose a reproducible MVP launch
**Description:** Validate and adjust only the container configuration needed to launch the API and dashboard against the repository’s checked-in data/model artifacts. Keep the two-service topology and health-gated dashboard dependency.

**Acceptance criteria:**
- `docker compose up --build` starts `api` and `dashboard` without manual path changes.
- The API healthcheck becomes healthy, the dashboard is reachable, and the dashboard can call the API over the internal URL.
- Configuration does not embed production secrets; development defaults are clearly identified.
- A short runbook section records startup, health, dashboard, docs, shutdown, and common missing-artifact behavior.

**Evidence checks:** `docker compose config`; `docker compose up --build`; `curl http://localhost:8000/api/v1/health`; browser check at `http://localhost:8501`; `docker compose down`.

**Dependencies:** Tasks 2.1-2.3 and 3.1.

**References:** FR-18.1-18.4; NFR-08; README sections 3.1-3.4; Architecture sections 2, 9, and 14.

### [x] Task 3.3: Define MVP handoff evidence and known limits
**Description:** Update the project documentation only as needed to describe the shipped workflow, endpoint examples, supported forecast semantics, seeded-data assumptions, authentication setup, and deferred capabilities. Record evidence from the release checks without claiming unmet academic targets.

**Acceptance criteria:**
- README/runbook instructions let a new operator install, launch, check health, open docs/dashboard, run tests, and diagnose missing artifacts.
- Endpoint examples match the implemented OpenAPI contracts.
- The documentation names the deferred optimization, clustering, simulation, explainability, ingestion, and retraining scope.
- The release note records latency, test, coverage, and Docker results with date and environment.

**Evidence checks:** Documentation link/command audit; clean-environment setup rehearsal; review against FR-20.1-20.3.

**Dependencies:** Tasks 3.1 and 3.2.

**References:** FR-18; FR-20; NFR-06-08; Architecture section 15.

## MVP Release Gate

The MVP is ready for real-user trial only when all of the following are true:

- Health and readiness are reliable, documented, and covered by integration tests.
- A facilities planner can complete the metrics-to-forecast dashboard workflow using seeded processed data.
- Forecast and metrics routes have stable validation, auth, error, and OpenAPI contracts.
- No PII enters the read/API contract; logs contain operational fields but no secrets or raw payloads.
- Focused pytest checks pass, full-suite failures are classified, and coverage is reported.
- `docker compose up --build` provides the documented API and Streamlit entry points.
- Deferred capabilities are explicitly labeled as roadmap work rather than presented as operational MVP features.
