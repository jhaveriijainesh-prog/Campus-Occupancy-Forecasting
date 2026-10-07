# Final Screenshot Evidence Manifest

This manifest records the actual image evidence that exists in the repository after the verified local runtime capture pass on 2026-10-02.

## Captured figures

| Figure | File | Purpose | Report Location | Evidence type | Source / workflow |
| --- | --- | --- | --- | --- | --- |
| Figure 3.1 | `01_overview_full.png` | Shows the live dashboard with the application title, navigation, and overall readiness state | Chapter 3 / dashboard overview | Runtime evidence | Direct browser capture of `http://localhost:8501` |
| Figure 3.2 | `02_overview_kpis.png` | Clarifies the Overview KPI/operational summary area | Chapter 3 / dashboard overview | Runtime evidence | Direct browser capture of the Overview content |
| Figure 3.3 | `03_forecast_explorer.png` | Shows the Forecast Explorer page prior to forecast generation | Chapter 3 / Forecast Explorer | Runtime evidence | Direct browser capture of the UI |
| Figure 3.4 | `04_valid_forecast.png` | Shows a valid room forecast result for one room and one-hour horizon | Chapter 3 / forecast evidence | Runtime evidence | Real user interaction with a valid room (`B01-R101`) |
| Figure 3.5 | `05_forecast_result_details.png` | Captures the forecast result details for interpretation of the point estimate | Chapter 3 / forecast evidence | Runtime evidence | Direct browser capture of the valid forecast output |
| Figure 4.1 | `07_api_health.png` | Shows the live FastAPI API documentation/health surface in the running service | Chapter 4 / API runtime evidence | Runtime evidence | Direct browser capture of `http://localhost:8000/docs` |
| Figure 4.2 | `08_docker_runtime.png` | Shows the actual Docker Compose runtime state from the verified stack | Chapter 4 / deployment evidence | Runtime evidence | Captured from `docker compose ps --all` output |
| Figure 4.3 | `09_test_results.png` | Shows the verified final pytest result summary | Chapter 4 / quality evidence | Evaluation evidence | Rendered from the actual `pytest -q` output |
| Figure 5.1 | `10_architecture.png` | Shows the actual system architecture diagram for the project | Chapter 5 / architecture | Design evidence | Rendered from the project architecture diagram text |
| Figure 5.2 | `11_data_flow.png` | Shows the actual data-flow pipeline for synthetic data to dashboard/API output | Chapter 5 / data flow | Design evidence | Rendered from the project data-flow diagram text |

## Not captured

These items were not produced because the repository and verified runtime do not support a real UI artifact for them without inventing content or overstating the scope.

| Item | Reason |
| --- | --- |
| `06_error_state.png` | No stable invalid-room UI screen was consistently available during the verified app run. The project has real API-level error proof instead. |
| `12_optimization_evidence.png` | No live optimization dashboard page exists in the supported UI; the optimization evidence remains analytical/API-based, not a dedicated dashboard screenshot. |

## Integrity note

Only files that actually exist in `docs/evidence/screenshots/` are listed above. The dashboard and API screenshots are genuine browser captures from the running local BDS-06 application. The architecture and data-flow figures are rendered directly from the project’s documented Mermaid diagrams and therefore reflect the current source design without modifying the codebase.
