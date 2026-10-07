# BDS-06 Final Presentation Outline

## Slide 1 — BDS-06: Campus Occupancy Forecasting
- Purpose: Introduce the project and establish the verified local prototype scope.
- Key talking points:
  - BDS-06 title and academic setting.
  - Local prototype boundary: FastAPI + Streamlit + Docker.
  - Verified scope is a read-only startup MVP.
- Evidence/screenshots used: none required; title slide only.
- Presenter note: Frame the project as a verified local university capstone prototype with explicit boundaries and no unsupported deployment claims.

## Slide 2 — Problem Statement
- Purpose: Explain why nominal timetable data is insufficient for capacity planning.
- Key talking points:
  - Schedules alone do not reveal actual room usage.
  - Need better visibility into occupancy, wasted capacity, and short-term demand.
  - The project studies this problem on synthetic data as a controlled prototype.
- Evidence/screenshots used: none required.
- Presenter note: Keep the argument grounded in the capstone framing; do not imply real institutional deployment.

## Slide 3 — Objectives
- Purpose: Summarize what the project was designed to achieve.
- Key talking points:
  - Reproducible occupancy analytics workflow.
  - One-hour forecasting for a selected room.
  - Utilization metrics and room-level analysis.
  - Clustering, optimization, and secure local dashboard functionality.
- Evidence/screenshots used: runtime and code structure; no unsupported live demo beyond verified artifacts.
- Presenter note: Emphasize the prototype scope and that the project remains intentionally local.

## Slide 4 — Proposed Solution
- Purpose: Show the architecture of the solution as a compact pipeline.
- Key talking points:
  - Synthetic data intake.
  - Cleaning and validation.
  - Feature engineering.
  - Forecasting and analytics.
  - API and dashboard delivery.
- Evidence/screenshots used: verified source architecture and repo modules, plus the project data flow narrative.
- Presenter note: Present this as a modular analytic pipeline rather than a broad operational platform.

## Slide 5 — System Architecture
- Purpose: Show the verified local implementation structure.
- Key talking points:
  - FastAPI backend and Streamlit frontend.
  - Data/model dependencies.
  - Local Docker runtime architecture.
- Evidence/screenshots used: 10_architecture.png
- Presenter note: Refer to the actual architecture diagram and explain the verified local topology.

## Slide 6 — Data Flow and Methodology
- Purpose: Explain how synthetic data becomes forecasts and dashboard outputs.
- Key talking points:
  - Generate synthetic rooms, timetables, events, and occupancy.
  - Validate and clean data.
  - Build features and run inference.
  - Serve API and dashboard.
- Evidence/screenshots used: 11_data_flow.png
- Presenter note: Keep focus on the verified process and avoid over-claiming real-world data provenance.

## Slide 7 — Forecasting Approach
- Purpose: Clarify the supported forecasting model and its real evidence boundary.
- Key talking points:
  - XGBoost regressor on synthetic data.
  - One-room, one-hour forecast only.
  - Point estimate semantics.
  - Chronological and causal leakage controls.
- Evidence/screenshots used: model metadata and verified forecast output; no probabilistic calibration visuals.
- Presenter note: State clearly that the forecast is point estimate only and not a multi-hour or interval model.

## Slide 8 — Analytics and Optimization
- Purpose: Distinguish the analytical capabilities from live dashboard pages.
- Key talking points:
  - SUR, RFU, and WSH calculations.
  - Room clustering as an analytical capability.
  - Heuristic-versus-MILP allocation comparison.
  - Synthetic scenario comparison with bounded results.
- Evidence/screenshots used: project metrics and solver outputs; no dashboard screenshot for optimization.
- Presenter note: Make clear that clustering and optimization are analytical modules, not standalone live UI pages.

## Slide 9 — Dashboard
- Purpose: Show the actual product interface used by the verified startup MVP.
- Key talking points:
  - Overview page with readiness and KPI status.
  - Forecast Explorer request flow.
  - Read-only operational design.
- Evidence/screenshots used: 01_overview_full.png, 02_overview_kpis.png, 03_forecast_explorer.png
- Presenter note: Position the dashboard as the visible face of the MVP and emphasize the two-page read-only scope.

## Slide 10 — Live Forecast Demonstration
- Purpose: Show the verified live forecast result in the local environment.
- Key talking points:
  - Room B01-R101.
  - One-hour horizon.
  - Point estimate outcome.
  - Verified dashboard/API result.
- Evidence/screenshots used: 04_valid_forecast.png, 05_forecast_result_details.png
- Presenter note: Keep the slide clean and focus on the actual forecast result without overloading with technical detail.

## Slide 11 — Security and Robustness
- Purpose: Demonstrate the local operational controls and safe error handling.
- Key talking points:
  - API-key protection.
  - Health and readiness validation.
  - 401 and 403 access control responses.
  - Controlled error states without exposing internals.
- Evidence/screenshots used: 07_api_health.png
- Presenter note: Emphasize the local demo boundary and the secure but non-production auth model.

## Slide 12 — Testing and Reproducibility
- Purpose: Show that the project is reproducible and runtime-verified.
- Key talking points:
  - Docker local startup.
  - API and dashboard verification.
  - 178 passed, 1 warning in 53.36s.
- Evidence/screenshots used: 08_docker_runtime.png, 09_test_results.png
- Presenter note: This is strong evidence for local reproducibility, not for public deployment or production certification.

## Slide 13 — Results
- Purpose: Capture what the project successfully demonstrates.
- Key talking points:
  - Local runtime is operational.
  - Forecast works in the verified scope.
  - Dashboard functions with real API-backed data.
  - Security boundaries and leakage tests are in place.
- Evidence/screenshots used: actual runtime screenshots and test output.
- Presenter note: Separate verified outcomes from future or unsupported claims.

## Slide 14 — Limitations and Future Work
- Purpose: Maintain academic honesty and evidence boundaries.
- Key talking points:
  - Synthetic data only.
  - One-hour point forecast scope.
  - No live campus integration.
  - No public deployment claim.
  - Future work requires real institutional validation and broader forecasting/optimization scope.
- Evidence/screenshots used: project report and evidence matrix; no fabricated visuals.
- Presenter note: Keep limitations explicit and visible to maintain credibility.

## Slide 15 — Conclusion
- Purpose: End with the project’s real contribution and value.
- Key talking points:
  - Verified local prototype.
  - Software engineering contribution.
  - Data science contribution.
  - Decision-support value within a controlled scope.
  - Thank You / Questions & Discussion.
- Evidence/screenshots used: accumulated runtime and report evidence.
- Presenter note: Close with confidence in the verified prototype and clarity around its bounded scope.

## Evidence usage summary
- Real screenshot files used in the deck:
  - 01_overview_full.png
  - 02_overview_kpis.png
  - 03_forecast_explorer.png
  - 04_valid_forecast.png
  - 05_forecast_result_details.png
  - 07_api_health.png
  - 08_docker_runtime.png
  - 09_test_results.png
  - 10_architecture.png
  - 11_data_flow.png
- Disallowed/unsupported screenshots intentionally excluded:
  - 06_error_state.png
  - 12_optimization_evidence.png

## Presenter notes status
- Presenter notes are recorded in this outline as concise speaking cues for a 7–10 minute presentation.
- The deck itself contains only the slide content; the notes are kept in the outline to remain concise and readable.
