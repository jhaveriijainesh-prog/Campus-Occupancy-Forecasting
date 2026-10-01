# BDS-06 Takeover Baseline

Date: 2026-09-27

## Verified Current State

| Area | Status | Evidence | Gap |
| --- | --- | --- | --- |
| Data validation and cleaning | PARTIAL | `app/data/validation.py`, `app/data/cleaning.py`; focused tests pass | Ingestion and 15/60-minute harmonization are not complete |
| Temporal feature engineering | PARTIAL | `app/features/engineering.py`; leakage tests pass | Broader model/horizon contract is not complete |
| Forecast model | PARTIAL | `app/forecasting/model.py`; model tests and checked-in artifact | Prediction intervals are synthetic multipliers, not calibrated quantiles |
| Forecast API | PARTIAL | `/api/v1/forecast/predict/{room_id}` returns 200 with checked-in artifacts | Horizon semantics and model metadata need hardening |
| Utilization metrics | PARTIAL | Implemented in `app/analytics/metrics.py` and `/api/v1/metrics/utilization`; focused tests pass | Building/department/time aggregation and response schemas need expansion |
| Clustering | MISSING | `app/clustering/cluster.py` is placeholder-only | Implement interpretable room profiles and validation |
| Scenario simulation | MISSING | `app/simulation/simulator.py` is placeholder-only | Implement reproducible outage/enrollment/schedule scenarios |
| Constraint-aware optimization | MISSING | Optimization modules are placeholder-only | Implement MILP, heuristic baseline, and infeasibility diagnosis |
| Dashboard | MISSING | Streamlit entrypoint/views are placeholder-only | Implement planner workflow and API client |
| Security | PARTIAL | API-key and sanitization utilities; metrics auth test passes | Remove default secret, add role/PII/security tests |
| Tests | PARTIAL | 32 full-suite tests pass in configured `.venv-2`; 42% coverage | API/domain/dashboard coverage is largely absent |
| Container/reproducibility | NEEDS VERIFICATION | Dockerfile, Compose, CI exist | Docker build/startup and clean-environment run not verified |
| Academic evidence | PARTIAL | Requirements, architecture, baseline/XGBoost experiment artifacts exist | Report dossier, model cards, runbook, screenshots, and contribution evidence remain |
| Git evidence | NEEDS VERIFICATION | `git` reports workspace is not a repository | Branch/PR/review history cannot be verified here |

## Completed During Takeover

- Declared the existing XGBoost runtime dependency in `requirements.txt`.
- Fixed the FastAPI permission dependency factory.
- Fixed router-level rate-limit dependency registration.
- Restored missing `data` and `optimization` router objects with explicit `501` responses.
- Implemented utilization calculations and a secured metrics endpoint with CSV/Parquet fallback.
- Fixed forecast inference to use the model's actual `predict` signature and CSV/Parquet fallback.
- Added focused metrics and API regression tests.

## Current Verification

- Full configured-environment suite: `32 passed`.
- Focused API/forecast/metrics suite: `7 passed`.
- Coverage from full suite: `42%`.
- Forecast smoke request for `B01-R101`: HTTP `200`.
- Metrics smoke request: HTTP `200`.
- Remaining warning: Starlette/httpx compatibility deprecation in the active environment.

## Phase 2/3/4/5 Evidence Added

- `app/data/ingestion.py`: supported source formats, provenance, normalization, and PII rejection.
- `app/data/harmonizer.py`: timezone-aware timetable interval and event alignment.
- `app/clustering/cluster.py`: deterministic room profiles, silhouette-selected K-Means, labels, and PCA coordinates.
- `app/simulation/simulator.py`: reproducible occupancy, closure, capacity, and enrollment scenarios.
- `app/optimization/solver.py`: PuLP CBC MILP with capacity, room-type, assignment, and overlap constraints.
- `app/optimization/heuristics.py`: capacity-first greedy comparison baseline.
- API routes now expose clustering, simulation, and heuristic-versus-MILP comparison results.
- Phase tests: ingestion/harmonization `5 passed`; clustering `4 passed`; simulation `3 passed`; optimization core `3 passed`.
- Full regression after integration: `46 passed`, `72%` coverage.

## Final Acceptance Checkpoint

- End-to-end real-data workflow test: `1 passed`.
- Browser runtime check: fresh Streamlit instance rendered overview KPIs, forecast output, room archetypes, scenario controls, and optimization controls; API status reported healthy.
- Explainability artifacts regenerated: feature importance and error slices under `experiments/comparison/explainability/`.
- Analytics evidence regenerated: clustering silhouette `0.4378954459`, scenario WSH delta `-1543.6`, CBC `Optimal` with objective `187.0` and runtime `1.199315s`.
- Final full suite: `64 passed`, `74%` coverage.
- Local `pip check` and Python compilation: passed.
- Docker/Compose: environment-blocked because `docker` is unavailable.
- Git history/status: environment-blocked because the workspace is not a Git repository.

## Highest-Priority Remaining Work

1. Implement data ingestion/harmonization and typed API schemas.
2. Complete metrics aggregation and response contracts.
3. Make forecast horizon and interval semantics honest and tested.
4. Implement clustering, simulation, MILP optimization, and baseline comparison.
5. Build the dashboard workflow and API client.
6. Verify Docker/CI, remove committed development secret defaults, and produce release evidence.
