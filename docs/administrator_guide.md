# BDS-06 Administrator Guide

**Audience:** Technical operator running the local capstone MVP.  
**Deployment boundary:** Two-service Docker Compose stack on a Windows host with Docker Desktop and WSL 2. No production cloud or remote deployment is claimed.

## 1. Prerequisites

- Windows with Docker Desktop installed and running in Linux-container mode.
- Docker Engine and Compose plugin available to the current user.
- Project files at the repository root.

The verified environment used Docker Engine 29.8.1, Docker Desktop 4.93.0, Compose v5.5.1, Linux/amd64 under WSL 2. The Compose file emits a non-blocking warning that its top-level `version` field is obsolete.

## 2. Configuration and Credentials

Compose reads only values referenced through `${...}` substitutions from `.env`; other Compose service settings are fixed in `docker-compose.yml`. In particular, Compose deliberately sets the dashboard's internal URL to `http://api:8000` and derives its `FASTAPI_API_KEY` from `API_READ_KEY`. The `FASTAPI_INTERNAL_URL` and `FASTAPI_API_KEY` entries in `.env.example` are for direct/local dashboard configuration and do not override those Compose values. The checked-in stack sets `APP_ENV=development` and `DEBUG=true`, so it is not a production deployment configuration.

For local use:

1. Copy `.env.example` to `.env` if you need local overrides.
2. Set unique, distinct values for `API_SECRET_KEY` and `API_READ_KEY` using a private local secret-generation method.
3. Keep `.env` out of source control and do not share terminal output containing values.
4. Do not publish this development stack on a public or untrusted network.

`API_READ_KEY` is the least-privilege dashboard credential for read/forecast operations. Optimization requires the API key with optimization permission. No user administration, key rotation service, or production secret manager is included.

## 3. Start and Validate

From the repository root in PowerShell:

```powershell
docker version
docker compose version
docker info
docker compose config --quiet
docker compose up --build -d
docker compose ps --all
```

The API publishes port 8000, and the dashboard publishes port 8501. The dashboard uses Compose DNS (`http://api:8000`) internally. Open:

- Dashboard: `http://localhost:8501`
- API docs: `http://localhost:8000/docs`
- Basic health: `http://localhost:8000/api/v1/health`
- Readiness: `http://localhost:8000/api/v1/health/ready`

A healthy API container is necessary but not sufficient for readiness. Readiness also checks the processed datasets and XGBoost artifacts mounted into `/app`.

## 4. Operations

```powershell
docker compose ps --all
docker compose logs --tail=100 api dashboard
(Invoke-WebRequest -Uri 'http://localhost:8000/api/v1/health/ready' -UseBasicParsing).StatusCode
```

Restart without rebuilding:

```powershell
docker compose restart api dashboard
```

Rebuild and restart using the verified stack procedure:

```powershell
docker compose down
docker compose --progress plain build
docker compose up -d --no-build
docker compose ps --all
```

The exact accepted launch command `docker compose up --build -d` and the separate down/rebuild/start cycle were both verified on 2026-10-01.

Shutdown:

```powershell
docker compose down
```

## 5. Artifact and Backup Notes

The API requires these checked-in artifacts:

- `data/processed/occupancy.parquet` (CSV fallback also exists)
- `data/processed/rooms.parquet`
- `data/processed/timetable.parquet`
- `data/processed/events.parquet`
- `experiments/xgboost/model.json`
- `experiments/xgboost/feature_metadata.json`
- `configs/config.yaml`

The Compose file bind-mounts project data, experiments, configs, models, and logs. Back up the source data/artifact directories and any locally generated logs before replacing them. Do not treat the empty `models/` directory as the active forecaster location; the API loads the model under `experiments/xgboost`.

## 6. Troubleshooting

- **Docker command unavailable:** Start/install Docker Desktop and verify both client and server with `docker version`.
- **API container unhealthy:** Check `docker compose logs --tail=100 api`; query `/api/v1/health/ready`; verify data and model files above.
- **Dashboard cannot connect:** Verify `FASTAPI_INTERNAL_URL` resolves to `http://api:8000` inside Compose and that API is healthy.
- **401 response:** Provide the configured `X-API-Key` to protected API routes; never send credentials in a URL.
- **403 response:** The key authenticated but lacks the route permission. The dashboard read key is not an optimization/admin key.
- **422 response:** Check JSON fields, room identifiers, and the only supported forecast horizon (1 hour).
- **Large cold build:** The verified images were about 3.71 GB each, and the first dependency/image export took several minutes. Allow sufficient disk and build time.

## 7. Security and Limits

The application uses static API keys and an in-memory rate limiter. It has no production identity provider, TLS termination, managed secret store, user-management console, or external monitoring service configured here. No vulnerability scanner result is claimed. Use synthetic data for demonstrations; do not add real student or device-identifying data without a separate approved privacy review.
