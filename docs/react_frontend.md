# BDS-06 React Dashboard

## Purpose and Architecture

This is a read-only React dashboard for the BDS-06 FastAPI service. Occupancy and schedule data are synthetic demonstration data, not live campus telemetry.

- React 19, TypeScript, Vite, React Router, Tailwind CSS, Recharts, and Lucide icons.
- `frontend/src/App.tsx` owns the route views and application shell.
- `frontend/src/api/client.ts` makes same-origin API calls and handles HTTP errors.
- FastAPI remains the source for utilization, forecast, room-cluster, authorization, and health results.
- Local Vite and the Render Nginx proxy attach the read-only API credential server-side. Credentials are never compiled into browser assets.

## Run Locally

Start FastAPI from the repository root:

```powershell
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`. It reads `API_READ_KEY` or `FASTAPI_API_KEY` from local configuration, then uses repository Python settings when neither is set. Never put credentials in `VITE_*` variables.

## Deploy to Render

The root `render.yaml` defines one Docker web service for React and FastAPI. `Dockerfile.render` builds the frontend and creates the deterministic synthetic dataset and one-hour forecast model from the checked-in generator/training scripts. Nginx serves the SPA and injects the Render-managed read-only key into same-origin `/api/` requests; Render generates separate production API keys.

The public free-tier demo is available at [campus-occupancy-forecasting.onrender.com](https://campus-occupancy-forecasting.onrender.com/). The service may spin down while idle, so the first request afterward may take longer. Occupancy remains synthetic demonstration data; this is not an institutional production service.

## Routes and Capabilities

| Route | Capability |
| --- | --- |
| `/` | Guided welcome screen with demo entry and task shortcuts; no account or simulated authentication |
| `/dashboard` | Campus utilization KPIs, chart, API status, and readiness |
| `/forecast` | Select a room and target time; review a one-hour point forecast |
| `/rooms` | Choose a room and review its metrics and similar-room group |
| `/optimization` | Choose plain-language occupancy/enrollment options, optionally exclude rooms, and compare results |
| `/health` | API health, readiness, version, and dependency checks |

The welcome screen is a demo entry point, not an authentication boundary. Forecast output is point-estimate-only; the UI does not present fabricated uncertainty. Missing API values remain unavailable. What-if scenarios run under the read-only credential and compare against the immutable source-data baseline. The separate MILP allocation comparison still requires the `optimize` permission.

## Quality Checks

Run in `frontend/`:

```powershell
npm run format:check
npm run lint
npm run build
```

Vite may report a JavaScript bundle-size advisory; it is not suppressed.

## Docker and Streamlit

The existing `docker-compose.yml` remains the local FastAPI and Streamlit setup. React is built into the separate Render image; Streamlit remains available as the local fallback at port `8501`.

See [the API mapping](react_dashboard_mapping.md) and [the React screenshot index](react_dashboard_screenshots.md) for route contracts and real browser captures.
