# React Dashboard Mapping

This mapping records the FastAPI contract consumed by the existing React dashboard. Streamlit remains a separate local dashboard and fallback; React does not call its Python dashboard gateway.

## Existing Streamlit feature → API endpoint → React page/component

| Existing Streamlit feature                            | Existing API endpoint                                                                         | Existing behavior                                                                | React implementation                                                                                |
| ----------------------------------------------------- | --------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| Overview: service status                              | `GET /api/v1/health`                                                                          | Returns API status, timestamp, and service                                       | `OverviewPage` API status card and shell badge                                                      |
| Overview: readiness                                   | `GET /api/v1/health/ready`                                                                    | Returns ready/not-ready and dependency state                                     | `OverviewPage` readiness card                                                                       |
| Overview: utilization KPI row                         | `GET /api/v1/metrics/utilization`                                                             | Campus/building/room SUR, RFU, WSH, peak occupancy, source timestamp             | `OverviewPage` KPI cards and summaries                                                              |
| Overview: API and readiness status                    | `GET /api/v1/health`, `GET /api/v1/health/ready`                                              | Returns API health, readiness, and dependency state                              | `AppShell` live status badge and `OverviewPage` status panels                                       |
| Overview: campus utilization KPIs                     | `GET /api/v1/metrics/utilization?scope=campus`                                                | Returns campus SUR, RFU, WSH, peak occupancy, observations, and source timestamp | `OverviewPage` KPI cards and snapshot chart                                                         |
| Forecast Explorer: room selection and request context | `GET /api/v1/forecast/model/info`                                                             | Returns model metadata, version, and supported horizon                           | `ForecastPage` model status and controls                                                            |
| Forecast Explorer: one-hour point forecast            | `GET /api/v1/forecast/predict/{room_id}?horizon_hours=1&start_time=...`                       | Generates a room forecast for the requested target time                          | `ForecastPage` result panel                                                                         |
| Forecast Explorer: model metadata                     | `GET /api/v1/forecast/model/info`                                                             | Returns model type, version, and supported one-hour horizon                      | `ForecastPage` model status and forecast controls                                                   |
| Dashboard shell status + service health               | `GET /api/v1/health`                                                                          | Returns live API status and timestamp                                            | `AppShell` live status badge                                                                        |
| Room-level analysis                                   | `GET /api/v1/metrics/utilization?scope=room&room_id=...`, `GET /api/v1/clustering/rooms`       | Returns selected-room KPIs and cluster profile metadata                          | `RoomsPage` user-selected metrics and cluster metadata                                             |
| What-if scenario                                       | `POST /api/v1/simulation/run`                                                                | Returns baseline and scenario metrics for occupancy/enrollment factors and room closures | `OptimizationPage` interactive inputs and comparison results                                |
| MILP allocation comparison                             | `POST /api/v1/optimize/compare`                                                               | Compares allocation strategies; requires the `optimize` permission               | Kept separate from the read-only user-facing what-if planner                                       |
| System health dashboard                               | `GET /api/v1/health`, `GET /api/v1/health/ready`, `GET /api/v1/health/detailed`               | Real observability and dependency state                                          | `HealthPage`                                                                                        |

## Observed verified boundaries

- The React product accepts analytical inputs but does not mutate source data. Existing Streamlit workflows remain unchanged.
- Occupancy values come from the project's synthetic demonstration dataset, not live campus sensors.
- The verified forecast contract is strictly one room and one hour: `horizon_hours = 1` and point-estimate-only output.
- The UI must not claim support for multi-hour, interval-heavy, or probabilistic forecasting unless the backend contract explicitly provides it.
- MILP allocation comparison remains a privileged backend capability. Room clustering and what-if simulation are exposed in the React demo.

## React route mapping

- `/` → Guided demo welcome page with task shortcuts; no authentication is simulated
- `/dashboard` → Campus overview page
- `/forecast` → Room forecast page with API-provided room choices and manual-entry fallback
- `/rooms` → Room metrics page with API-provided room choices and manual-entry fallback
- `/optimization` → Scenario planner with plain-language occupancy/enrollment choices
- `/health` → System status page

React calls same-origin `/api` paths. Local Vite attaches the configured read credential to upstream FastAPI requests server-side; the Render Nginx proxy does the same with its platform-managed key. Neither key is compiled into browser assets. The read-only key is sufficient for forecasts, room metrics, clustering, and non-mutating simulations. Only the separate allocation-comparison endpoint requires the elevated `optimize` permission.

The detailed health response includes an environment field, but React intentionally omits it and displays only health/readiness, service version, and dependency checks.

## Source contract used by the React app

- `frontend/src/api/client.ts` is the React API client; the Vite development proxy keeps the read credential server-side.
- `app/dashboard/api_client.py` remains the separate typed gateway used by Streamlit.
- `app/schemas/forecast.py` defines the forecast request and response structure.
- `app/schemas/metrics.py` defines utilization response structure.
- `app/core/config.py` contains local API URL configuration and supported read-only credentials.
- `app/core/security.py` defines the local API key boundary and permissions.
- `app/api/routes/health.py` exposes readiness and detailed dependency health checks.
- `app/api/routes/metrics.py` exposes utilization metrics.
- `app/api/routes/forecast.py` exposes model metadata and the supported single-room forecast route.
- `app/api/routes/optimization.py` exposes analytical optimization comparison.
- `app/api/routes/simulation.py` exposes validated non-mutating scenario simulation.
- `app/api/routes/clustering.py` exposes room clustering metadata.

## Screenshot Evidence

Real browser captures are indexed in [react_dashboard_screenshots.md](react_dashboard_screenshots.md). Their values are from the running local API and synthetic demonstration data.

## Implementation rule

The React dashboard must use the same backend responses as the existing Streamlit app and must not fabricate metrics, charts, or room capabilities beyond the verified data contract.
