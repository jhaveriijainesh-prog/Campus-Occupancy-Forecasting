# BDS-06 Demo Script (5–8 Minutes)

**Recording status:** Script only. No recording or UI screenshot is claimed by this artifact.  
**Preflight:** Use the verified local Docker workflow only if Docker Desktop is running. Open the dashboard and API locally, confirm health/readiness, and keep all credentials private. Use synthetic data only.

| Time | Section | Narration | Evidence and boundary |
| --- | --- | --- | --- |
| 0:00–0:40 | Problem + stakeholder | “This project addresses a common campus-planning problem: nominal schedules and room capacity do not necessarily match actual usage. The goal is to inspect utilization, estimate short-term room occupancy, and evaluate whether simple capacity-aware analysis adds value.” | This is a synthetic capstone prototype. No real institution or live sensor feed is being claimed. |
| 0:40–1:15 | What the system does | “The system ingests synthetic room, timetable, event, and occupancy data; validates and cleans it; computes utilization metrics; and runs a one-hour forecast for a selected room.” | The supported scope is the verified MVP: Overview and Forecast Explorer. |
| 1:15–2:00 | Architecture and data flow | “The application is a modular Python monolith with a FastAPI backend and a Streamlit dashboard. The dashboard calls the API for health, readiness, KPI data, and forecast results; it does not directly read model files.” | The flow is local Compose-based and documented in the architecture and runbook. |
| 2:00–3:00 | Overview | “I start with the Overview page. It shows readiness, API/data/model availability, and the aggregate campus metrics: SUR, RFU, and WSH.” | Use the synthetic KPI values and explain that these are aggregate operational indicators, not real-campus measurements. |
| 3:00–4:20 | Forecast Explorer | “I select a known room such as B01-R101 and request a forecast. The system returns a one-hour point estimate for predicted headcount and the model version.” | This is a one-hour point forecast; it does not claim calibrated uncertainty intervals or multi-hour forecasting. |
| 4:20–5:20 | Optimization / clustering analytical capability | “The project also includes clustering and optimization evidence. Clustering groups rooms by behavior, and the allocation code compares a greedy baseline against a CBC MILP on the same synthetic timetable. The current evidence is analytical and documented, not a separate dashboard page.” | Say clearly that optimization and clustering are not part of the two-page MVP UI. |
| 5:20–6:20 | Engineering quality | “The API exposes health, readiness, metrics, and forecast endpoints; the dashboard uses a least-privilege read key; the project includes security checks and leakage tests; and the JavaScript-free local demo uses Docker Compose.” | Emphasize the verified local runtime and the fact that this is not public hosting. |
| 6:20–7:20 | Evaluation | “The supported evidence is a chronological holdout comparison between a baseline and the XGBoost model. The result is measured on synthetic data and is reported with its limitations. The scenario SUR discrepancy is left transparent, not hidden.” | State that causal leakage tests and the runtime checks are real evidence, while broader claims remain unverified. |
| 7:20–8:00 | Conclusion and future work | “This project demonstrates a credible, reproducible capstone prototype for campus occupancy analytics. The strongest contribution is the combination of data validation, leakage controls, forecasting, and analytical optimization evidence. The next step would be real-data validation and broader stakeholder testing.” | Close on the honest scope: local, synthetic, one-hour, evidence-backed, and academically defensible. |

## Demo safety notes
- Do not claim real campus integration, production hosting, or public deployment.
- Do not claim multi-horizon or probabilistic forecasting.
- Do not present optimization as a universal improvement claim; the evidence is bounded to the checked-in synthetic case.
- Do not show keys or raw secrets.
- Do not say a dashboard page exists if it is not in the current two-page MVP.
- Do not claim a final video or screenshot unless it is recorded and checked by a human.
