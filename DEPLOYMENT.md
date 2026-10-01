# Deployment Package

## 1. Purpose

This project is a local Docker-based campus forecasting application that preserves the verified Streamlit + FastAPI architecture. The goal of this deployment package is to keep local development usable while making future host deployment straightforward without baking secrets into tracked source.

## 2. Local runtime (verified)

- API: http://localhost:8000
- Dashboard: http://localhost:8501
- Local Docker workflow remains the default verification path.

## 3. Architecture

- Frontend: Streamlit dashboard
- Backend: FastAPI API
- Runtime boundary: direct server-side call from Streamlit to FastAPI
- Credentials: stored in environment variables or a platform secret store; never in browser-visible code
- Data/model dependencies: local files mounted via Docker volumes

## 4. Required environment variables

Create a local `.env` file from `.env.example` and provide real values for the current environment.

Required names:
- `APP_ENV`
- `DEBUG`
- `LOG_LEVEL`
- `API_HOST`
- `API_PORT`
- `API_SECRET_KEY`
- `API_READ_KEY`
- `FASTAPI_INTERNAL_URL`
- `FASTAPI_PUBLIC_URL`
- `FASTAPI_API_KEY`
- `DATA_DIR`
- `MODELS_DIR`
- `LOGS_DIR`
- `CONFIGS_DIR`
- `SOLVER_TIMEOUT_SECONDS`

Do not commit `.env`.

## 5. Local development

```bash
docker compose up --build -d
```

Then verify:

```bash
curl http://localhost:8000/api/v1/health
curl http://localhost:8000/api/v1/health/ready
curl http://localhost:8501/_stcore/health
```

## 6. Production deployment preparation

Production deployment requires:

1. a real Git repository and remote
2. authenticated hosting credentials
3. platform-managed environment secrets
4. deployment-specific environment values rather than development defaults

The application must not silently fall back to hardcoded credentials in production mode. The runtime now requires explicit environment values.

## 7. Security requirements

- never commit `.env`
- never put secrets in browser-visible code
- never send the admin credential to the frontend or browser
- keep `API_READ_KEY` separate from `API_SECRET_KEY`
- use platform secret management for externally hosted deployment
- keep local development secrets local only

## 8. Health and readiness

- API health: `/api/v1/health`
- API readiness: `/api/v1/health/ready`
- Dashboard health: `/_stcore/health`

## 9. Redeploy and rollback

Redeploy:

```bash
docker compose up --build -d
```

Rollback:

1. stop the current stack
2. restore the previous image or previous deployment artifact
3. rerun the same environment-supplied configuration

## 10. Remaining external actions required

This package is ready for real deployment once a human provides:

- authenticated Git remote/repository access
- hosting platform authorization
- deployment secrets in the platform secret store
- public HTTPS target configuration

No public URL is claimed here.
