# Report Traceability Matrix

This document maps the claims in the final report to the actual evidence files and runtime checks available in the repository.

## Scope and limits

| Report claim | Supporting evidence | Status |
| --- | --- | --- |
| Local-only Docker demo and synthetic-data scope | `README.md`, `docs/final_report.md`, `docs/task3_2_runtime_evidence.md` | Verified |
| Synthetic data provenance and generation logic | `docs/data_generation.md` | Verified |
| Forecasting model and evaluation summary | `docs/evaluation_dossier.md`, `docs/model_system_card.md`, `docs/final_report.md` | Verified |
| API security and permission checks | `tests/unit/test_security.py`, `docs/security_review.md`, `docs/task3_2_runtime_evidence.md` | Verified |
| Dashboard behavior | `app/dashboard/app.py`, `tests/unit/test_dashboard_overview.py`, `tests/unit/test_dashboard_forecast.py`, `docs/evidence/screenshots/01_overview_full.png`, `docs/evidence/screenshots/03_forecast_explorer.png` | Verified |
| Runtime Docker startup and health | `docs/task3_2_runtime_evidence.md`, `docs/evidence/screenshots/08_docker_runtime.png`, `docs/evidence/screenshots/07_api_health.png` | Verified |
| One-hour forecast result | `docs/evidence/screenshots/04_valid_forecast.png`, `docs/evidence/screenshots/05_forecast_result_details.png`, `docs/final_report.md` | Verified |
| Architecture and data flow | `docs/evidence/screenshots/10_architecture.png`, `docs/evidence/screenshots/11_data_flow.png`, `docs/02_architecture.md` | Verified |
| Quality gate and test result | `docs/evidence/screenshots/09_test_results.png`, `pytest -q` output, `coverage.xml` | Verified |
| Human-only submission items | `docs/submission_checklist.md` | Human action required |

## Chapter-to-evidence map

### Abstract / problem framing
- `docs/final_report.md` – Abstract and problem description
- `docs/industry_problem_brief.md` – business framing
- `docs/01_requirements.md` – scope and functional requirements

### Data and provenance
- `docs/data_generation.md` – generation assumptions and dataset schema
- `docs/data_cleaning_and_validation.md` – cleaning and validation logic
- `data/raw/` and `data/processed/` – generated artifacts

### Forecasting and evaluation
- `docs/evaluation_dossier.md` – benchmark and model results
- `docs/model_system_card.md` – model scope and limitations
- `docs/baseline_forecasting.md` – baseline comparisons
- `scripts/evaluate_models.py` and related model artifacts under `experiments/`

### Architecture and runtime
- `docs/02_architecture.md` – system structure
- `docs/runbook.md`, `docs/runbook_api_examples.md` – execution flow and commands
- `docs/task3_2_runtime_evidence.md` – verified Docker and API behavior

### Security and operations
- `docs/security_review.md` – repo security posture and caveats
- `app/core/security.py` – local permission logic
- `tests/unit/test_security.py` – permission failure cases

### Dashboard experience
- `app/dashboard/app.py` and `app/dashboard/api_client.py`
- `tests/unit/test_dashboard_overview.py`
- `tests/unit/test_dashboard_forecast.py`

## Integrity note

This matrix only covers claims that can be validated from the repository and the latest local verification evidence. Claims that require human recording, artifact export, or institutional approval are marked as `Human action required` in `docs/submission_checklist.md` and are not treated as repository proof.
