# Task 3.2 Docker Runtime Evidence

**Date:** 2026-10-01  
**Scope:** Local Windows / Docker Desktop runtime for BDS-06. This is not production hosting evidence. Secrets are intentionally omitted.

## Environment

Commands executed:

```powershell
docker desktop status
docker version
docker compose version
docker info
docker context show
```

Observed:

- Docker Desktop status: running.
- Docker Client 29.8.1; Server Docker Desktop 4.93.0; Engine 29.8.1; Linux/amd64.
- Docker Compose v5.5.1; context `desktop-linux`.
- Docker info: WSL 2 kernel 6.18.40.1, 4 CPUs, approximately 3.8 GiB memory.

## Configuration and Image Build

`docker compose config --quiet` exited 0. Compose prints a warning that the top-level `version` attribute is obsolete; the field is ignored and did not block configuration or runtime.

Successful build command:

```powershell
docker compose --progress plain build
```

Both `campus-occupancy-forecasting-api:latest` and `campus-occupancy-forecasting-dashboard:latest` were built from the repository Dockerfile. The full cold build resolved/installed project Python dependencies and exported both tagged images. The build output showed image sizes of approximately 3.71 GB each. One initial progress-flag invocation failed before the corrected successful build; no success is attributed to that failed invocation.

The exact Task 3.2 acceptance command also succeeded:

```powershell
docker compose up --build -d
```

Compose reported both images built, the API healthy, and the dashboard running.

## Services and Readiness

Final observed `docker compose ps --all` state:

| Service | State | Published port | Restarts |
| --- | --- | --- | ---: |
| `api` | running / healthy | 8000 | 0 |
| `dashboard` | running | 8501 | 0 |

Host endpoints returned:

- `/api/v1/health`: HTTP 200, healthy; request ID and security headers present.
- `/api/v1/health/live`: HTTP 200, alive.
- `/api/v1/health/ready`: HTTP 200, ready.
- Streamlit `/_stcore/health`: HTTP 200, body `ok`.
- Dashboard root: HTTP 200.

## Artifact Availability

Inside the API container, all following files existed:

- `/app/data/processed/occupancy.parquet`
- `/app/data/processed/rooms.parquet`
- `/app/data/processed/timetable.parquet`
- `/app/data/processed/events.parquet`
- `/app/experiments/xgboost/model.json`
- `/app/experiments/xgboost/feature_metadata.json`
- `/app/configs/config.yaml`

The dashboard container had `FASTAPI_INTERNAL_URL=http://api:8000`, a read credential configured, and no master key. The API read/master values were distinct. Values are not printed here.

## Live API Results

- Missing and invalid metrics credentials: HTTP 401.
- Read credential, campus metrics: HTTP 200; SUR `0.025218`, RFU `0.423988`, WSH `31402.0`, peak occupancy `220`, RFU denominator field `observations=50176`.
- Read credential, building `B01`: HTTP 200; SUR `0.023273`, RFU `0.422768`, WSH `6254.0`, peak `88`, denominator `15680`.
- Read credential, room `B01-R101`: HTTP 200; SUR `0.024898`, RFU `0.408163`, WSH `2638.0`, peak `88`, denominator `1568`.
- Model info: HTTP 200; XGBRegressor; 48 features; supported horizon 1 hour.
- Forecast `B01-R101`, horizon 1: HTTP 200; prediction approximately `1.3063`, nonnegative and below room capacity 120; method `point_estimate_only`; model version `xgboost-v1`.
- Unsupported horizon 2: HTTP 422.
- Unknown room: HTTP 404; dashboard AppTest rendered a safe user-facing message without an exception.
- Optimizer with dashboard read key: HTTP 403; without credentials: HTTP 401.
- Live `POST /api/v1/optimize/compare`: greedy and CBC both feasible, each unused-capacity objective 187 for 50 assignments; CBC status Optimal, runtime approximately 1.73 seconds. This is one synthetic instance and shows parity, not superiority.
- Live scenario with occupancy x1.15, enrollment x1.10, closed `B01-R101`: WSH delta `-1543.6`, SUR delta `+0.002174`, RFU delta `-0.008475`, peak delta `+33`. The persisted 2026-09-27 artifact for the same parameters has SUR delta `+0.002845`; discrepancy remains unresolved.

## Dashboard Evidence

Inside the dashboard container, the actual APIClient reached the API over Compose DNS and returned readiness, campus metrics, and a one-hour forecast. Streamlit AppTest results:

- Overview: 0 exceptions; readiness success; API/data/model status plus SUR/RFU/WSH rendered.
- Forecast Explorer valid room: 0 exceptions; readiness/model/one-hour point output rendered.
- Unknown room: 0 exceptions; safe inline not-found message rendered.

No browser screenshot or recorded video is claimed.

## Latency Sample

Twenty sequential warmed forecasts through the dashboard container's `APIClient` over Compose DNS:

- p50: 138.29 ms
- nearest-rank p95: 157.95 ms
- maximum: 544.25 ms

This small one-host sample is not production performance certification. A separate ten-call Windows PowerShell sample had a 245.6 ms tail including shell/client overhead; it is retained as a host-side observation, not server-only latency.

## Security and Logs

Read-key/master-key separation and permissions were checked without printing credentials. The recent container log scan after the final `up --build` found:

- dashboard read key present: `False`
- traceback present: `False`
- `ERROR` present: `False`

This is a bounded local log inspection, not a vulnerability scan or production security certification.

## Rebuild and Restart

The following cycle passed:

```powershell
docker compose down
docker compose --progress plain build
docker compose up -d --no-build
docker compose ps --all
```

After restart, API health/readiness returned 200, dashboard HTTP returned 200, the dashboard APIClient returned ready/campus metrics/forecast, no-key metrics returned 401, and both containers had zero restarts.

## Repository Changes During Task 3.2

No Dockerfile, Compose, application source, or environment-template changes were made. The Task 3.2 marker was updated in `project-tasks/startup-mvp-tasklist.md`. This evidence note is part of the later Task 3.3 documentation package.
