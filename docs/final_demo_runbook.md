# Final Demo Runbook

## BEFORE DEMO
1. Open Docker Desktop or ensure the Docker daemon is running.
2. Verify the daemon with: `docker version` and `docker info`.
3. Navigate to the project root.
4. Check the local environment file and confirm the development keys are in place.
5. Start the app: `docker compose up --build -d`.
6. Check health: `curl http://localhost:8000/api/v1/health` and `curl http://localhost:8000/api/v1/health/ready`.
7. Open the dashboard in the browser: http://localhost:8501.

## DEMO
1. State the problem clearly: campus space planning without reliable occupancy visibility.
2. Open the Overview page and explain readiness, status cards, and utilization scope filters.
3. Explain the KPIs and interpretation: SUR, RFU, WSH, and the overall readiness state.
4. Switch to Forecast Explorer.
5. Enter a valid room such as `B01-R101`.
6. Generate a forecast and explain that the supported horizon is 1 hour.
7. Explain the one-hour semantics and the fact that the model is point-estimate-only.
8. Explain that clustering and optimization are analytical capabilities backed by project artifacts and synthetic scenarios.
9. Explain leakage controls and security boundary: read keys are separate, and privileged routes are intentionally gated.
10. Summarize evaluation evidence and limitations honestly.
11. Conclude with the capstone boundary: local synthetic demo, local Docker stack, not public deployment.

## BACKUP
- Use the API health endpoints as backup if the UI is temporarily inconsistent.
- Keep the local test evidence ready for a quick re-check.
- Maintain screenshot evidence from the live dashboard and live API responses.
- Keep the compose restart commands available: `docker compose down` and `docker compose up --build -d`.

## FAILURE RULE
If a runtime issue occurs:
- report it honestly
- do not fabricate data or screenshots
- do not claim functionality that was not actually demonstrated
- restore the stack and continue with the evidence that is working

## RECOVERY
- If the Docker daemon has stopped, restart it using the supported local mechanism.
- If the app is unhealthy, restart the stack with `docker compose down` followed by `docker compose up --build -d`.
- Confirm health and readiness before resuming the demo.
