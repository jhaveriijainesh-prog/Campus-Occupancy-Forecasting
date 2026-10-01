# BDS-06 Local MVP Release Notes

## Release Record

- **Release record:** `BDS06-MVP-2026-10-01` (documentation identifier; no Git tag was available to verify)
- **API version reported by service:** `1.0.0`
- **Verification date:** 2026-10-01
- **Runtime:** Docker Desktop 4.93.0; Docker Engine 29.8.1; Docker Compose v5.5.1; Linux/amd64 under WSL 2; `desktop-linux` context; 4 CPUs and approximately 3.8 GiB memory.
- **Scope:** Local capstone MVP deployment, not production hosting.

## Capabilities Included

- FastAPI health, readiness, metrics, forecast, clustering, simulation, and heuristic-versus-MILP comparison routes.
- Streamlit read-only Overview and Forecast Explorer pages.
- Synthetic processed occupancy, room, timetable, and event artifacts.
- XGBoost one-hour room-level point forecast.
- Aggregate utilization analytics, deterministic room clustering and scenario artifacts, PuLP/CBC allocation.
- API-key permission separation, input validation, request IDs, safe dashboard errors, and Compose service networking.

The dashboard does not expose clustering, optimization, or simulation pages. These are API/offline analytical capabilities, not part of its two-page planner workflow.

## Verification

- Python regression evidence: 176 passed, 0 failed, 643 warnings; 45.87 seconds in the latest recorded run. Existing `coverage.xml` reports an 86.48% line rate; it was not regenerated in this documentation pass.
- Docker: `docker compose config --quiet` exited 0 (with a non-blocking obsolete top-level `version` warning).
- `docker compose up --build -d` built both images and started API/dashboard.
- API health/readiness and Streamlit health passed; dashboard-to-API calls used `http://api:8000`.
- Authenticated campus/building/room metrics and one-hour forecast passed; missing/invalid credentials were rejected, and the read key was denied optimization access.
- Down, cached rebuild, and restart passed; API returned healthy and both containers had zero restarts.
- Warmed Compose-DNS forecast latency: 20 sequential calls, nearest-rank p50 138.29 ms, p95 157.95 ms, max 544.25 ms. This small local sample meets the SRS 200 ms p95 target in-sample but is not a production performance certification.

## Known Limitations

- Synthetic data only; no live campus sensor or timetable-system integration is evidenced.
- Forecast API supports a one-hour point estimate. Calibrated prediction intervals and other horizons are not supported by the current artifact.
- XGBoost holdout sMAPE and WAPE are high; low/zero observations affect percentage metrics.
- One recorded clustering, scenario, and optimization experiment each; no repeated-run stability or sensitivity study.
- Current live greedy and MILP allocation objectives were both 187 on 50 assignments; no improvement claim is made.
- Formal peak detection, visual usability study, stakeholder validation, vulnerability scan, remote CI run, and external deployment were not verified.
- Workspace has no Git metadata; no tag, branch, pull request, code review, or individual hours can be attested here.
- Compose development defaults and debug mode are not production configuration; image sizes were about 3.71 GB each.

## Documentation Included

- Requirements-to-evidence matrix, redacted Task 3.2 runtime evidence, final report, system/model card, administrator guide, user guide, runbook/API examples, demo script, slide content, contribution template, and submission checklist.

## Reproducibility

From the repository root with Docker Desktop running:

```powershell
docker compose config --quiet
docker compose up --build -d
docker compose ps --all
```

See `docs/runbook.md` and `docs/administrator_guide.md` for health, logs, shutdown, and recovery.
