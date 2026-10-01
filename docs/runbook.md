# BDS-06 Local Runbook

**Release evidence date:** 2026-10-01  
**Scope:** Local Windows demonstration with Docker Desktop Linux containers. This is a development/capstone runbook, not production deployment guidance.

## Prerequisites

- Windows with Docker Desktop installed and running in Linux-container mode using its WSL 2 backend.
- A working Docker Engine and Compose plugin. The verified environment reported Docker Engine 29.8.1, Docker Desktop 4.93.0, Compose v5.5.1, context `desktop-linux`, 4 CPUs, and approximately 3.8 GiB memory.
- A checkout of this project at the repository root.

Before launching, verify the engine:

```powershell
docker version
docker compose version
docker info
```

`docker version` must show both Client and Server. The verified host had a top-level Compose `version` deprecation warning; it was ignored by Compose and did not prevent validation or startup.

## Start

From the project root:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps
```

Expected services:

- API: `http://localhost:8000`
- OpenAPI docs: `http://localhost:8000/docs`
- Streamlit dashboard: `http://localhost:8501`

The `dashboard` service waits for the API healthcheck. Its internal API address is `http://api:8000`; `localhost` is used only for host-published URLs.

## Health and Readiness

```powershell
(Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/live' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing).StatusCode
(Invoke-WebRequest -Uri 'http://localhost:8501/_stcore/health' -UseBasicParsing).StatusCode
```

Expected status is 200 for the verified artifact set. Readiness checks processed rooms, occupancy, timetable, events, XGBoost model, and model metadata. A 503 response identifies missing dependencies; it is not equivalent to basic API liveness.

## Logs and Status

```powershell
docker compose ps --all
docker compose logs --tail=100 api dashboard
```

Do not paste logs into public channels without checking for sensitive operational details. The Task 3.2 runtime scan found no dashboard key, traceback, or `ERROR` in the inspected recent logs.

## Rebuild and Restart

The accepted launch command was executed successfully:

```powershell
docker compose up --build -d
```

The full stop/rebuild/restart cycle was also verified:

```powershell
docker compose down
docker compose --progress plain build
docker compose up -d --no-build
docker compose ps --all
```

The API returned healthy after restart; dashboard readiness, campus metrics, one-hour forecast, host HTTP, and authentication checks passed. Container restart counts were zero.

## Shutdown

```powershell
docker compose down
```

Project data and model files are bind-mounted from the working tree, so `down` removes containers/network but does not remove those host files.

## Missing Artifact Troubleshooting

1. Check the API readiness response at `/api/v1/health/ready`.
2. Confirm `data/processed/occupancy.parquet`, `rooms.parquet`, `timetable.parquet`, and `events.parquet` exist.
3. Confirm `experiments/xgboost/model.json` and `feature_metadata.json` exist.
4. Check `docker compose logs --tail=100 api dashboard` for the named dependency failure.
5. Confirm `data`, `experiments`, and `configs` mounts are present in the Compose configuration.
6. Rebuild/restart only after the missing host artifact or configuration has been corrected.

## Credentials and Security

The Compose configuration is for local development. It contains development fallbacks and sets development/debug settings; these are not production credentials or a production deployment profile. `.env` is ignored by Git. If a local `.env` is used, create distinct, private values for `API_SECRET_KEY` and `API_READ_KEY`, and never commit or publish it. Compose fixes the dashboard internal URL to `http://api:8000` and derives the dashboard credential from `API_READ_KEY`; `FASTAPI_INTERNAL_URL` and `FASTAPI_API_KEY` template entries are for direct/local dashboard runs and are overridden in Compose. The dashboard receives only the configured read key; the API master key must remain separate. Do not expose the development stack to an untrusted network.

For request paths, permissions, and example payloads, see [API Examples](runbook_api_examples.md).
