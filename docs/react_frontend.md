# BDS-06 React Frontend

## Purpose

This is a post-capstone, local product enhancement to the existing BDS-06 project. It continues the existing React application; it does not replace the Streamlit dashboard or change the official capstone sequence. Occupancy and schedule data are synthetic demonstration data, not live campus telemetry.

## Architecture

- React 19, TypeScript, Vite, React Router, Tailwind CSS, Recharts, and Lucide icons.
- `frontend/src/App.tsx` owns the five route views and application shell.
- `frontend/src/api/client.ts` contains the API calls and HTTP error status handling.
- Local Vite proxies same-origin `/api` requests to FastAPI and attaches the read-only credential server-side. It is not compiled into browser assets.
- FastAPI remains the source for utilization, forecast, room-cluster, authorization, and health results. React does not fabricate those results.

## Local Startup

Start FastAPI from the repository root:

```powershell
python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
```

Start React in a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite proxy target is fixed to `http://127.0.0.1:8000` and cannot forward the read credential to a remote host. It reads `API_READ_KEY` or `FASTAPI_API_KEY` from local configuration, then uses repository Python settings when neither is set. Do not put credentials in `VITE_*` variables.

## Routes And Capabilities

| Route           | Live capability                                                                                                       |
| --------------- | --------------------------------------------------------------------------------------------------------------------- |
| `/`             | Campus utilization KPIs, percentage-only utilization chart, health/readiness, source timestamp, and observation count |
| `/forecast`     | One room, one hour, one API point estimate; defaults to `B01-R101`                                                    |
| `/rooms`        | Room-level API metrics and returned cluster ID, label, and feature names                                              |
| `/optimization` | Displays comparison output only if the caller is authorized; otherwise shows the real permission boundary             |
| `/health`       | API health, readiness, service version, and dependency checks                                                         |

The forecast response identifies its interval as `point_estimate_only`; the UI does not present fabricated uncertainty. Missing API values remain unavailable. The UI does not display environment values or credentials. Optimization comparison requires `optimize`; the read-only dashboard credential receives `403`, and no privileged credential is present in the frontend.

## Quality Checks

```powershell
npm run format:check
npm run lint
npm run build
```

ESLint covers TypeScript, React Hooks, and React Refresh. Vite may warn that the production JavaScript chunk exceeds 500 kB; the advisory is not suppressed.

## Render Deployment

The root `render.yaml` defines a single Docker web service for the React dashboard and FastAPI. `Dockerfile.render` builds the frontend, generates deterministic synthetic data and its forecast model, then starts Nginx and Uvicorn. Nginx serves the SPA and injects the Render-managed read-only API key into same-origin `/api/` requests; the key is not included in browser assets. Render generates separate production API keys and checks `/api/v1/health/ready` before routing traffic. The existing `docker-compose.yml` remains unchanged and continues to define FastAPI and Streamlit; React is not represented as a Compose service. Streamlit remains the existing fallback on port `8501`.

Deploy the `render.yaml` blueprint from the repository in Render. The configured free plan can spin down while idle, and the first request after inactivity may take longer. Occupancy remains synthetic demonstration data, not live campus telemetry. This is a public demo, not an institutional production service. The existing `docker-compose.yml` remains unchanged and continues to define FastAPI and Streamlit; React is not represented as a Compose service. Streamlit remains the existing fallback on port `8501`.

## Screenshots

See [the React screenshot index](react_dashboard_screenshots.md) for real desktop route captures, a 390px responsive Overview, and their demo/report usage.
