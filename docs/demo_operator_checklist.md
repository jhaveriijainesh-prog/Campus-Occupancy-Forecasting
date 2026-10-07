# Demo Operator Checklist

This checklist is for the local demonstration only. It supports a truthful capstone presentation and does not claim public hosting or production deployment.

## BEFORE DEMO

- Docker Desktop is running and the local Docker daemon is available.
- The repository is opened at the project root.
- Environment variables are configured locally in `.env` if used for the demo.
- The Compose stack has been started successfully with the project’s verified local process.
- The API is healthy and the readiness endpoint responds successfully.
- The dashboard is reachable on the local host.
- A known room ID is confirmed for the live forecast step, such as `B01-R101`.
- The API read credential is available locally but not displayed on screen.
- No secret values are shown in terminal output, screenshots, or recordings.

## DURING DEMO

- Open the Overview page and confirm readiness state is clear.
- Explain the KPI values in plain language: SUR, RFU, WSH.
- Show that the metrics come from a synthetic dataset and are local operational indicators.
- Open Forecast Explorer and enter a real room ID.
- Explain the one-hour forecast semantics and the fact that it is a point estimate.
- State the forecast target timestamp and model version without implying a calibrated interval.
- Explain the optimization and clustering analytical capability without claiming dashboard pages for them.
- Show the API health/readiness or docs evidence where appropriate.
- Preserve the honest boundary: local demonstration, synthetic data, one-hour forecast, local-only Docker stack.

## BACKUP PLAN

### If the API is unavailable
- State that the API is not responding and postpone the forecast demonstration.
- Show the health/readiness section or local docs evidence rather than claiming a live forecast.
- Keep the explanation tied to the repo’s verified evidence and local demo boundary.

### If the forecast fails
- Show the safe error state and explain that the room or model dependency is unavailable.
- Do not claim the forecast is working if the endpoint is failing.
- Fall back to readiness and metrics evidence.

### If a screenshot or recording is required
- Capture only clean, non-secret evidence.
- Avoid showing keys, raw logs, or stack traces.
- Prefer the Overview, readiness, forecast result, and repository evidence sections.

### What must not be claimed
- No public deployment
- No real-campus sensor integration
- No production hosting
- No multi-horizon or probabilistic forecast claim
- No unsupported optimization superiority claim
- No hidden or unverified scenario outcome
- No secret or credential disclosure
