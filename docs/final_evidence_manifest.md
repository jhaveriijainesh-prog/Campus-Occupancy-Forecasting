# Final Evidence Manifest

## System

- Project: Campus Occupancy Forecasting
- Architecture: FastAPI API + Streamlit dashboard + local synthetic-data pipeline + Docker Compose stack
- Local launch command: `docker compose up --build -d`
- API endpoint: http://localhost:8000
- Dashboard endpoint: http://localhost:8501

## Core functionality

- Overview evidence: Dashboard Overview page shows service readiness, occupancy data availability, and overall readiness status.
- Forecast Explorer evidence: Dashboard Forecast Explorer page accepts a room ID and produces a one-hour forecast for a valid room.
- Forecast contract: `GET /api/v1/forecast/model/info` returns model metadata; `GET /api/v1/forecast/predict/{room_id}?horizon_hours=1` returns a point-estimate-only forecast.
- Optimization/clustering evidence: analytical modules and saved artifacts exist; local API and offline experiment evidence remain scoped to analytical capability, not a dedicated dashboard UI.

## ML validity

- Chronological split: implemented in the generated data pipeline and validated by regression tests.
- Causal lag: enforced and tested in the leakage regression suite.
- Leakage tests: `tests/regression/test_leakage.py` exercises temporal and causal checks.
- Room isolation: room-wise forecast and validation logic preserve room boundaries.
- Model limitation: current served model is a one-hour XGBoost point forecast only; no multi-horizon or calibrated interval claim is supported.

## Engineering

- Tests: `pytest` suite passes for the current verified repo state.
- API security: missing keys return 401; privileged optimizer access returns 403 for read-only keys.
- Health/readiness: `/api/v1/health` and `/api/v1/health/ready` return 200.
- Rate limiting: configured in the backend and documented as local development enforcement.
- Docker: local Docker Desktop + Compose runtime starts the stack successfully when the daemon is available.
- Reproducibility: `docker compose down` followed by `docker compose up --build -d` is the supported local repro path.
- Operational logs: API and dashboard logs show startup, health checks, and the live requests used for verification.

## Evaluation

- Forecast error: XGBoost MAE/RMSE and baseline comparison are documented in the evaluation dossier.
- Utilization evidence: campus/building/room utilization endpoints return valid real runtime responses.
- Baseline comparison: greedy vs. CBC comparison is recorded as a deterministic synthetic scenario, not evidence of superiority beyond that scenario.
- Scenario limitation: the persistent SUR discrepancy between saved and live scenario runs remains unresolved and must be reported honestly.
- Performance measurements: local runtime checks show healthy API responses and acceptable local timings for this small synthetic demo environment.

## Demo evidence

- Original capstone screenshot status: the Streamlit/demo screenshots listed in `docs/final_screenshot_manifest.md` remain human-owned.
- Post-capstone React evidence: real browser captures are stored in `docs/evidence/screenshots/react/` and indexed in `docs/react_dashboard_screenshots.md`; they supplement and do not replace the official capstone screenshot checklist.
- Final report and presentation drafts: `Final_BDS06_Project_Report.docx` and `BDS06_Final_Project_Presentation.pptx` are included with their source content/generation scripts; they still require the student's final review.
- Verified capstone substitute evidence: live HTTP responses and dashboard smoke checks captured in `docs/task3_2_runtime_evidence.md` and `docs/final_report.md`.
- Demo timestamp: 2026-10-01 / 2026-10-02 local runtime verification pass.
- Viva question references: `docs/viva_qna.md` and `docs/demo_script.md`.
- Capture requirement: see `docs/final_screenshot_manifest.md` for the required screenshot set and the exact items still awaiting human capture.

## Human-owned final items

- Demo video
- Contribution/hours evidence
- Institutional pages / final export
- Final sign-off record

## Evidence trail

- `README.md`
- `docs/final_report.md`
- `docs/evaluation_dossier.md`
- `docs/bds06_evidence_matrix.md`
- `docs/demo_script.md`
- `docs/demo_operator_checklist.md`
- `docs/demo_evidence_plan.md`
- `docs/viva_qna.md`
- `docs/submission_checklist.md`
- `tests/regression/test_leakage.py`
- `tests/unit/test_dashboard_overview.py`
- `tests/unit/test_dashboard_forecast.py`
