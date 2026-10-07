# React + TypeScript + Vite

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

````js
export default defineConfig([
  # BDS-06 React Dashboard

  The existing React/Vite dashboard is a local, read-only interface to BDS-06 FastAPI. Occupancy inputs are synthetic demonstration data, not live campus telemetry.

  ## Run Locally

  Start FastAPI from the repository root:

  ```powershell
  python -m uvicorn app.api.main:app --host 127.0.0.1 --port 8000
````

In a second terminal:

```powershell
cd frontend
npm ci
npm run dev
```

Open `http://127.0.0.1:5173`. Vite proxies `/api` to `http://127.0.0.1:8000`. The proxy reads `API_READ_KEY` or `FASTAPI_API_KEY` from local environment configuration; if neither is set, it obtains the configured read key from the repository's Python settings. The key is added server-side and is not included in browser assets. Never use a `VITE_*` variable for credentials.

## Deploy to Render

The root `render.yaml` blueprint defines a single Docker web service for the React app and FastAPI. Render generates separate API keys; Nginx injects only the read-only key into same-origin API requests, so no credential is bundled into the frontend. The image builds its reproducible synthetic dataset and forecast model from the checked-in generator and training code.

To create the service, open the repository in Render's Blueprint flow and deploy the `render.yaml` blueprint. The free web-service plan may spin down when idle, so its first request after inactivity can take longer. All displayed occupancy is synthetic demonstration data, not live campus telemetry.

## Routes

- `/` - API-driven campus utilization overview and readiness
- `/forecast` - one room, one hour, point estimate
- `/rooms` - room metrics and API-returned cluster metadata
- `/optimization` - comparison only when the caller has `optimize`; the read-only credential receives `403`
- `/health` - health, readiness, service version, and dependency checks

## Checks

```powershell
npm run format:check
npm run lint
npm run build
```

ESLint includes TypeScript, React Hooks, and React Refresh rules. Vite may report the advisory that the JavaScript bundle exceeds 500 kB; the threshold is not suppressed.

## Boundaries

- Forecast requests remain one room, one hour, and point-estimate only.
- Missing values are unavailable, not substituted with zero; utilization chart values share percentage units.
- No privileged optimization credential or fabricated optimization output is present.
- Streamlit remains the existing fallback at port `8501`.
- Compose still contains FastAPI and Streamlit only; the Render deployment uses the separate `Dockerfile.render` image.

See [the React frontend guide](../docs/react_frontend.md), [API mapping](../docs/react_dashboard_mapping.md), and [screenshot index](../docs/react_dashboard_screenshots.md), including desktop page captures and the 390px responsive Overview.
},
