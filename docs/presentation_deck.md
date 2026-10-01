# BDS-06 Capstone Presentation Content

**Target:** 22-slide academic/industry presentation. This is slide content, not an exported PowerPoint deck. Existing `docs/assets/` contains forecast analysis plots; no dashboard screenshot or recording is claimed.

## Slide 1 — Title
- BDS-06: Campus Occupancy Forecasting with Spatiotemporal Analytics and Capacity Optimization
- T.Y. B.Sc. Data Science, Semester V
- Add verified student/team and institution details before submission.

**Speaker cue:** Introduce a stakeholder-testable prototype using aggregate room occupancy and capacity-planning analyses.

## Slide 2 — Industry Problem
- Nominal enrollment and timetable alone do not show actual room usage.
- Planners need aggregate evidence on occupancy, unused capacity, and near-term room demand.
- This project studies the workflow on a synthetic campus dataset.

## Slide 3 — Stakeholders
- Facilities/space planner: inspect utilization and short-term room demand.
- Academic scheduler: review room assignment constraints.
- Technical operator: deploy and monitor readiness.
- Evaluator: inspect reproducibility, leakage controls, baselines, and limitations.

**Note:** Personas in the SRS are illustrative design personas; interviews are not evidenced.

## Slide 4 — Objectives and Scope
- Read-only dashboard for readiness, utilization, and one-hour forecast.
- Clustering, scenario simulation, and allocation are implemented as API/offline capabilities.
- Live sensors, real campus integration, and production operation are not verified.

## Slide 5 — Product Overview
- FastAPI on port 8000.
- Streamlit on port 8501.
- Synthetic processed Parquet/CSV data and checked-in XGBoost artifacts.
- Compose network route: dashboard to `http://api:8000`.

## Slide 6 — Architecture
- Modular Python monolith separates data, features, analytics, models, API, and UI.
- Dashboard requests use the typed API client.
- API reads configured processed data and `experiments/xgboost` artifacts.

**Visual:** Draw the actual topology; label `api`, `dashboard`, and mounted artifacts.

## Slide 7 — Data Pipeline
- Seed-42 synthetic rooms, timetable, events, and hourly occupancy.
- Validation/cleaning creates processed Parquet/CSV files.
- Processed snapshot: 86,016 occupancy rows, 32 rooms, 50 timetable rows.

## Slide 8 — Data Governance
- Aggregate synthetic counts; no live sensor data.
- No person-level tracking or individual attendance decisions intended.
- Real deployment requires approved provenance and privacy review.

## Slide 9 — Utilization Analytics
- SUR: aggregate observed headcount / aggregate capacity.
- RFU: occupied room-hours / available operating room-hours.
- WSH: positive scheduled-enrollment minus observed occupancy, times slot duration.
- Live Compose checks covered campus, building B01, and room B01-R101.

## Slide 10 — Forecasting Method
- XGBoost regressor; seed 42; 48 features; one-hour horizon.
- Calendar/timetable/room context plus causal lags and rolling features.
- Served artifact is point-estimate-only; no calibrated quantiles.

## Slide 11 — Leakage Controls
- Chronological train/validation/test split.
- Train through 2026-10-11; validation 2026-10-12 to 2026-10-25; test 2026-10-26 to 2026-11-22.
- Leakage regression tests are present and passed in the recorded suite.

## Slide 12 — Forecast Holdout Results
| Model | MAE | RMSE | R2 | WAPE | sMAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Historical seasonal profile | 2.5975 | 10.1839 | 0.2335 | 102.72% | 163.6674% |
| XGBoost | 1.2775 | 4.3961 | 0.8572 | 50.52% | 155.5725% |

**Speaker cue:** This is descriptive synthetic holdout evidence; no confidence intervals or significance test. Percentage errors remain high with low/zero observations.

## Slide 13 — Error Slices
- Day-peak MAE reduction vs baseline: 69.11%, 3,584 observations.
- Night slice is 4.66% worse; Sunday is 9.04% worse.
- These are forecast-error slices, not peak detection precision/recall.

## Slide 14 — Room Clustering
- Seeded K-Means on five room behavior/capacity profile features.
- 32 rooms, 6 clusters, silhouette 0.4378954459.
- One saved run; no stability analysis or expert interpretation study.

## Slide 15 — Scenario Simulation
- Occupancy x1.15; enrollment x1.10; close B01-R101.
- Saved experiment: WSH -1543.6, SUR +0.002845, RFU -0.008475, peak +33.
- Live API run: WSH -1543.6, SUR +0.002174, RFU -0.008475, peak +33.
- SUR discrepancy is unresolved; WSH reduction coincides with a higher peak, so it is a tradeoff.

## Slide 16 — Constraint-Aware Allocation
- CBC MILP assigns each timetable session to an eligible room.
- Implemented constraints: capacity, room type when specified, assignment uniqueness, and no overlapping room use.
- Broad SRS requirements for travel, equipment, and accessibility are not fully modeled.

## Slide 17 — Heuristic Comparison
- Greedy baseline: largest sessions first, smallest suitable available room.
- Live run: both greedy and CBC feasible; both objective values 187 for 50 assignments.
- CBC status Optimal, about 1.73 s; this instance shows objective parity, not MILP superiority.

## Slide 18 — Dashboard Walkthrough
- Overview: readiness, typed scope filters, SUR/RFU/WSH, aggregate density bar.
- Forecast Explorer: typed room ID, fixed one-hour request, point estimate and metadata.
- No optimizer/scenario/clustering pages in the current dashboard.

## Slide 19 — Deployment
- Docker Desktop 4.93.0 / Engine 29.8.1 / Compose 5.5.1.
- Exact `docker compose up --build -d` built and started the stack.
- API healthy; dashboard reachable; internal API calls and rebuild/restart passed.

## Slide 20 — Security and Robustness
- Dashboard uses a separate read/forecast key.
- Missing/invalid credentials returned 401; read key was denied optimizer access with 403.
- Unsupported horizon returned 422; unknown room was rendered as safe inline error.
- Development defaults/debug mode are not production configuration.

## Slide 21 — Limitations and Future Work
- Synthetic data and no stakeholder field study.
- One-hour point forecast only; no calibrated intervals.
- No formal peak detector, scenario stability analysis, or broad load test.
- No remote CI run, Git review evidence, actual demo recording, or verified individual hours.
- Future: approved real data, more horizons/calibration, usability and robustness studies, fuller constraints, production identity/secrets operations.

## Slide 22 — Conclusion and Q&A
- Local end-to-end prototype is containerized and runtime-verified.
- Strongest evidence: temporal forecast comparison, aggregate metrics, leakage tests, and Compose deployment.
- Human actions remain: verified contribution record, institutional review, actual recording, and final formatted export.
