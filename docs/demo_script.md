# BDS-06 Demo Script (7 Minutes)

**Recording status:** Script only. No recording or UI screenshot is claimed by this artifact.  
**Preflight:** Start the verified Compose stack, open `http://localhost:8501` and `http://localhost:8000/docs`, confirm `/api/v1/health/ready` is 200, and prepare local credentials privately. Do not display a key. Use only synthetic data.

| Time | Screen/action | Suggested narration | Evidence / expected result |
| --- | --- | --- | --- |
| 0:00-0:40 | Title slide | “BDS-06 helps planners inspect aggregate space use and estimate near-term room occupancy. The demo data is synthetic, so today I will show technical behavior, not claim real campus impact.” | State project name, intended users, synthetic-data boundary. |
| 0:40-1:15 | Architecture slide | “The project is a modular Python monolith with a FastAPI boundary and a Streamlit client. The dashboard talks to the API, not directly to model files.” | Show actual `api` and `dashboard` services and `http://api:8000` Compose DNS. |
| 1:15-1:45 | PowerShell terminal, `docker compose ps` | “This is the exact local Compose deployment. The API healthcheck is healthy and the dashboard is running.” | Two services; API healthy; ports 8000 and 8501. |
| 1:45-2:15 | Dashboard Overview | “Readiness appears before interpreting KPIs. The three headline measures are seat utilization, room frequency of use, and wasted seat-hours.” | API/data/model availability and SUR/RFU/WSH. Say values are from seeded synthetic records. |
| 2:15-2:55 | Overview scope form | Select Building, enter `B01`, apply; then select Room and enter `B01-R101`. | Real API-backed building and room aggregates. Note IDs are entered manually. |
| 2:55-4:00 | Forecast Explorer | Enter `B01-R101`; select Generate forecast. | One-hour XGBoost point prediction, forecast target timestamp and model version. State that no calibrated interval or capacity reference is shown in this response. |
| 4:00-4:45 | Swagger UI, `POST /api/v1/simulation/run` | Use the authorized read credential privately and submit occupancy multiplier 1.15, enrollment multiplier 1.10, closed room `B01-R101`. | Show scenario ID and aggregate deltas. Explain that the recorded scenario lowered WSH but also increased peak occupancy; it is a tradeoff, not an optimization claim. |
| 4:45-5:30 | Swagger UI, `POST /api/v1/optimize/compare` (optional) | Use an authorized local optimization credential privately. “The greedy capacity-first allocator and CBC MILP both find feasible solutions here. In this dataset run their unused-capacity objectives are equal, so I do not claim MILP superiority.” | Current live run: both objective 187, MILP Optimal, 50 assignments, runtime about 1.73 s. Keep key out of view. |
| 5:30-6:15 | API docs and security response | Demonstrate a protected metrics request without a key (401), then authorized read metrics; if showing optimization, explain read-only credential receives 403. | Least privilege and safe HTTP behavior. Never reveal key values. |
| 6:15-7:00 | Final slide | “The strongest evidence is the chronological forecast comparison and real local container workflow. Remaining work is validation with campus stakeholders, measured peak-detection/usability studies, and the student’s actual contribution record and final recording.” | Mention limits and next human actions. |

## Demo Safety Notes

- Do not claim live sensor integration, real campus deployment, multi-horizon inference, calibrated intervals, geographic heatmaps, or an optimization improvement not supported by results.
- The live dashboard does not include clustering, scenario, or optimization pages. Show those only through the documented API or checked-in experiment artifacts.
- No screen capture or video recording exists until a human records one and verifies the exported file.
