# BDS-06 Security and Privacy Review

**Review date:** 2026-10-01
**Scope:** API authentication, uploads, PII handling, configuration, and local dependency/runtime checks.

## Verified Controls

- API-key authentication is applied to read, forecast, optimization, clustering, simulation, and ingestion routes.
- Upload filenames are reduced to their basename; path traversal names are rejected.
- Uploads are limited to 10 MB and validated in a temporary file before atomic replacement.
- CSV, JSON, and Excel inputs are restricted to the supported extensions.
- PII-like source columns such as student names/IDs, email, phone, MAC, and IP fields are rejected at ingestion.
- Dashboard uses the separate configurable `API_READ_KEY` in Compose; it grants only `read` and `forecast` permissions. The master `API_SECRET_KEY` remains reserved for administrative/write operations.
- `.env` is ignored by the repository ignore rules; no `.env` file is present in the workspace.
- Local dependency validation passed with `pip check`.
- Python source compilation passed for `app`, `tests`, and `scripts`.
- Protected read routes return `401` without a key or with an invalid key; public health remains available.
- Non-health routes enforce the configurable in-memory limiter and return `429` with `Retry-After` when exceeded.
- API responses include `X-Request-ID`, `X-Content-Type-Options`, `X-Frame-Options`, and `Referrer-Policy`.
- Authentication logs do not retain client IPs, API-key prefixes, headers, or tokens.
- Unexpected API errors return a generic `500 Internal server error` contract without exception details.

## Limitations

- The development fallback master `API_SECRET_KEY` remains visible in development configuration and grants all configured permissions. The separate development `API_READ_KEY` is also a documented fallback but grants only `read` and `forecast`; application startup rejects either fallback outside development/test environments. Production deployment must provide distinct unique credentials through environment management.
- No Bandit, pip-audit, or equivalent security scanner is installed or claimed as executed.
- The available `pip check` command passed; it verifies dependency consistency, not vulnerability absence.
- Task 1.5 behavior tests cover authentication, rate limiting, safe errors, security headers, privacy redaction, and structured request telemetry.
- Task 3.1 integration/security tests verify the dashboard read credential can complete the MVP read workflow and is forbidden from using the ingestion endpoint.
- Task 3.1 verification: `tests/integration` passed 3 tests; full suite passed 176 tests with 643 warnings in `.venv-2` on Python 3.14.7. The existing `coverage.xml` snapshot records an 86.48% line rate; it was not regenerated during this handoff.
- Task 3.2 runtime verification on 2026-10-01: Docker Desktop 4.93.0, Engine 29.8.1, Compose v5.5.1. Images built; exact `docker compose up --build -d` passed; API health/readiness, dashboard, API network, metrics, one-hour forecast, key permissions, and down/rebuild/start passed. Recent logs had no dashboard read-key value, traceback, or `ERROR` in the inspected tail. This is local development evidence, not production certification.
- Docker Compose emits an obsolete top-level `version` warning; it is ignored and did not prevent config validation or runtime.
- Compose uses development/debug configuration and fallback development keys. Do not publish this stack to untrusted networks or treat those values as production secrets.
- Git history and review evidence cannot be checked because this workspace is not a Git repository.

## Evidence

- Full suite after Task 1.5: `106 passed`, `0 failed`, `643 warnings`, `29.65s` in the configured `.venv-2` environment.
- Focused upload/auth/API tests pass in `tests/unit/test_metrics_api.py`.
- Task 1.5 focused security/API tests: `42 passed` in `tests/unit/test_security.py`, `tests/unit/test_monitoring.py`, and `tests/unit/test_metrics_api.py`.
- Source review covered `app/core/security.py`, `app/data/ingestion.py`, `app/api/routes/data.py`, `.env.example`, `.gitignore`, `Dockerfile`, and `docker-compose.yml`.
