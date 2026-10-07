# BDS-06 React Dashboard

The React dashboard is an interactive, read-only analytics interface to the FastAPI service. Users can request a room forecast for a selected time, query room-level metrics, and run what-if scenarios. Occupancy and timetable values are synthetic demonstration data, not live campus telemetry.

## Run Locally

From the repository root, start FastAPI:

```powershell
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies same-origin `/api` requests to `http://127.0.0.1:8000` and adds the configured read-only key server-side. It reads `API_READ_KEY` or `FASTAPI_API_KEY` locally, falling back to the Python settings. Never put credentials in `VITE_*` variables.

## Deploy to Render

The root `render.yaml` blueprint defines a single Docker web service for React and FastAPI. The image builds the frontend, generates deterministic synthetic data and a forecast model, then serves the SPA and API through Nginx and Uvicorn. Nginx injects the Render-managed read-only key into same-origin API requests; credentials are not bundled in browser assets. Render generates separate API keys.

To deploy, create a Blueprint in Render from this repository and use `render.yaml`. The free web-service plan may spin down while idle, so the first request afterward can take longer. This is a public demo deployment, not an institutional production service.

## Routes

- `/` - guided demo welcome page with shortcuts into the workspace; no account or simulated login is required
- `/dashboard` - API-driven campus utilization overview and service readiness
- `/forecast` - select a room and time, then review a one-hour point estimate
- `/rooms` - choose a room and review its metrics and similar-room group
- `/optimization` - select plain-language occupancy and enrollment changes, optionally exclude rooms, and compare results
- `/health` - API health, readiness, version, and dependency checks

The welcome screen is an entry point rather than an authentication boundary. All occupancy and timetable values shown are synthetic demonstration data, not live campus telemetry.

## Checks

```powershell
npm run format:check
npm run lint
npm run build
```

The Vite build may report a JavaScript bundle-size advisory; it is not suppressed.

## Scope

- Forecasting remains one room, one hour, and point-estimate only; the target time is user-selected.
- Missing API values remain unavailable rather than being substituted with zero.
- What-if runs are temporary comparisons against the same baseline; they do not mutate campus data. The MILP allocation comparison remains a separate privileged backend capability.
- The existing Compose stack remains FastAPI and Streamlit for local use; Render uses `Dockerfile.render`.

See [the deployment and frontend guide](../docs/react_frontend.md), [API mapping](../docs/react_dashboard_mapping.md), and [screenshot index](../docs/react_dashboard_screenshots.md).
