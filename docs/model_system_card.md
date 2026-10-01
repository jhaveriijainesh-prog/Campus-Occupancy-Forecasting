# BDS-06 Model and System Card

## Model Card: XGBoost Occupancy Forecaster

### Model Details

- **Model:** `xgboost.XGBRegressor`
- **Purpose:** Predict room-level hourly occupancy from causal temporal, timetable, calendar, and room metadata features.
- **Artifact:** `experiments/xgboost/model.json`
- **Configuration:** `experiments/xgboost/config.json`
- **Seed:** `42`
- **Forecast horizon evidenced:** 1 hour
- **Feature count:** 48

### Training and Evaluation Data

The model was trained on the repository's synthetic processed occupancy data. The chronological split is train through `2026-10-11`, validation through `2026-10-25`, and holdout test from `2026-10-26` through `2026-11-22`. There are 53,760, 10,752, and 21,504 rows respectively. The feature engineering and leakage tests enforce antecedent lags and shifted rolling features.

### Performance

On the holdout test set: MAE `1.2775`, RMSE `4.3961`, R2 `0.8572`, WAPE `50.52%`, and sMAPE `155.5725%`. Relative to the historical seasonal baseline, MAE improves by `50.82%` and RMSE by `56.83%`. These are descriptive test-set results without confidence intervals or significance tests.

### Intended Use

Use for aggregate room-level occupancy forecasting and academic comparison against transparent heuristic baselines. The result can support exploratory capacity planning when accompanied by the documented limitations.

### Out-of-Scope Uses

Do not use this model for individual attendance tracking, identity inference, disciplinary decisions, safety-critical crowd control, automatic HVAC actuation, or claims about real-world campus performance beyond the synthetic dataset.

### Limitations and Bias Considerations

- The data generator encodes its own attendance, calendar, and anomaly assumptions; real sensor drift and institutional behavior may differ.
- WAPE and sMAPE are high because the dataset contains many low or zero occupancy observations; MAE and RMSE should be read with the slice tables.
- Sunday and night slices show small negative relative improvements, so the model does not dominate every regime.
- Prediction intervals are not evidenced as calibrated quantiles. The checked-in model artifact is a point regressor.
- No fairness evaluation by person-level protected attributes is appropriate because no person-level data is collected. Aggregate room and schedule effects still require operational review.

## System Card

### System Purpose and Architecture

BDS-06 is a modular Python application containing data validation and cleaning, feature engineering, forecasting, room clustering, scenario simulation, PuLP/CBC allocation, FastAPI routes, and a Streamlit dashboard. The architecture is described in [02_architecture.md](02_architecture.md).

### Verified Analytical Components

- Cleaning and temporal leakage tests: verified by focused test runs.
- Room clustering: 32-room run, 6 clusters, silhouette `0.4378954459`.
- Scenario simulation: deterministic SHA-256 scenario ID and persisted metric deltas.
- Allocation: saved 50-session CBC run, `Optimal`, objective `187.0`, runtime `1.199315s`. A live comparison returned the same objective (`187`) from greedy and CBC; the live CBC call took about `1.73s`. This instance does not show MILP superiority.

### Data Governance

The checked-in data is aggregate and synthetic. Ingestion rejects configured PII column names. The validation report records 86,016 occupancy rows, 32 rooms, and 50 timetable rows with zero reported errors or warnings after cleaning.

### Operational Status

The local analytical runner and Docker Compose stack were verified. On 2026-10-01, Docker Desktop 4.93.0 / Engine 29.8.1 / Compose 5.5.1 built and ran the `api` and `dashboard` services; readiness, host dashboard access, Compose-DNS API calls, metrics, one-hour forecast, least-privilege behavior, and a down/rebuild/start cycle passed. The verified runtime is local and uses development configuration; this is not production hosting. The API's model is loaded from `experiments/xgboost/model.json` with `feature_metadata.json`.

The dashboard has two pages: Overview and Forecast Explorer. Clustering, simulation, and optimization can be invoked through API/offline evidence but are not dashboard pages. No UI screenshot or recorded demo video is included in this handoff.

### Supported Interfaces and Dependencies

- API: FastAPI on port 8000. API docs are available at `/docs` when debug/docs are enabled.
- Dashboard: Streamlit on port 8501; internal Compose API URL is `http://api:8000`.
- Processed data: `data/processed/` (occupancy, rooms, timetable, events).
- Forecast artifacts: `experiments/xgboost/`.
- Data provenance: checked-in data is synthetic, generated with seed 42; no real sensor provenance is claimed.
- Credential model: separate `API_READ_KEY` for dashboard read/forecast access; higher privilege is required for optimization. Development fallback keys are not production secrets.

### Monitoring and Change Control

Before using a new dataset or model, rerun focused tests, regenerate forecast and analytical artifacts, compare against existing JSON metrics, and update the evidence matrix. Future work includes repeated-run determinism checks, calibrated intervals, multi-horizon evaluation, broader load tests, and real-user validation. Docker/API/dashboard runtime smoke evidence is already available for the local Task 3.2 environment.