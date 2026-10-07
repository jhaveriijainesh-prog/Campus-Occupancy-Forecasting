# BDS-06 Viva Q&A

This document is intentionally short and evidence-backed. Every answer below is tied to the checked-in code, tests, runtime evidence, and current scope boundary.

## 1. Why this problem?
Because campus space is expensive and difficult to plan from nominal schedules alone. The project demonstrates a low-risk, synthetic proof-of-concept for evaluating room utilization, short-term occupancy, and a simple optimization lens without relying on live campus telemetry.

## 2. Who are the stakeholders?
The intended stakeholder roles are facilities/space planners, academic schedulers, technical operators, and academic evaluators. These are documented in the project requirements and supported by the local demo workflow, but no formal campus interviews or live stakeholder study are recorded in this repository.

## 3. What data did you use?
The checked-in project uses synthetic room, timetable, event, and hourly occupancy data generated under a deterministic seed. Processed CSV/Parquet artifacts exist under `data/processed/` and are used by the API and forecast pipeline.

## 4. Why synthetic data?
Synthetic data allows a reproducible, privacy-safe capstone environment. It supports reproducible feature engineering, leakage tests, and API validation without claiming real institutional data provenance.

## 5. How was synthetic data generated?
The repository includes a data generator and validation pipeline in the `app/data` and `scripts/` modules. The generated dataset is seeded and documented as synthetic, not real campus occupancy data.

## 6. How did you prevent leakage?
Leakage controls are enforced through chronological splitting and causal feature engineering. The strongest evidence is in `tests/regression/test_leakage.py`, which checks temporal ordering, lag correctness, target perturbation invariance, and room isolation. These tests are explicitly designed to fail if future data contaminates the training features.

## 7. Why XGBoost?
XGBoost was chosen because it is a strong, fast, interpretable tree-based regressor for tabular spatiotemporal features and works well with the project's synthetic hourly room dataset. The current served model is a one-hour point predictor, not a multi-horizon or probabilistic system.

## 8. Why one-hour horizon?
The checked-in system is intentionally scoped to a one-hour prediction horizon. That is the current serving contract and is reflected in the dashboard and forecast API. It is a realistic short-term operational window for room planning, and it matches the verified MVP boundary.

## 9. Why point forecast instead of probabilistic forecast?
The current verified artifact is a point forecast model. The project does not claim calibrated p10/p50/p90 intervals or a quantile model. The evidence matrix and report explicitly treat those as unsupported or deferred capabilities.

## 10. How is utilization calculated?
Utilization is derived from the project formulas for Seat Utilization Rate (SUR), Room Frequency of Use (RFU), and Wasted Seat-Hours (WSH), implemented in the analytics modules. The dashboard reads these via the metrics API and renders them as aggregate campus/building/room values.

## 11. What is RFU?
RFU is the proportion of occupied room-hours relative to the relevant operating room-hours for the selected scope and time window. The denominator is an estimated operating-hours measure, not an unqualified count of live sensor readings.

## 12. What is WSH?
WSH is the total wasted seat-hours, computed from positive differences between scheduled enrollment and observed occupancy across the relevant operating slots. It is a capacity-efficiency metric used to reason about unused seats and underused rooms.

## 13. How does clustering help?
Room clustering helps identify rooms with similar behavioral patterns, such as similar utilization or peak behavior. It is relevant as an analytical capability and evidence artifact, but it is not a dashboard page in the current MVP. It supports exploratory classification rather than live operational control.

## 14. What exactly is optimized?
The project optimizes room allocation by reducing unused capacity while respecting hard scheduling constraints. The optimizer evaluates a greedy baseline against a CBC MILP allocation on a room assignment problem, with feasibility checks and no overlap in the same room.

## 15. What are the optimization constraints?
The implementation enforces capacity compatibility, room eligibility, one assignment per session, and non-overlap in a room. The code is designed to avoid infeasible room assignments while favoring the lowest unused-seat objective. It does not claim full general-purpose campus scheduling optimization beyond the checked-in synthetic instance.

## 16. What is the baseline?
The baseline is a capacity-first greedy allocator. The project compares it against the CBC MILP solver on the same synthetic timetable, then reports the resulting objective and feasibility information. The evidence shows equal objective values in the checked-in example and therefore does not claim universal MILP superiority.

## 17. How do you know the optimizer adds value?
The value is evidenced by the solver run and the recorded objective comparison: feasible solutions were produced and the CBC solver was able to evaluate the same scheduling problem with a bounded objective. The current evidence does not show a broad or universal performance gain across all campus scenarios.

## 18. What happens when data/model artifacts are missing?
The health and readiness APIs check dependency presence. If an artifact is missing, the system returns a degraded or unavailable state instead of silently continuing. The dashboard renders the issue clearly and avoids exposing operational internals.

## 19. How does authentication work?
The API uses static API keys with permission checks. The dashboard uses a least-privilege read key; higher-privilege access is required for optimization-capable routes. This is a local development boundary, not a production identity system.

## 20. How are secrets handled?
Secrets are expected to be provided through environment variables, not committed to the repository. The project includes development defaults, but the docs explicitly say these are not production secrets and should not be treated as a production-grade secret management pattern.

## 21. How does rate limiting work?
The application uses an in-memory rate limiter. The API may reject excessive requests with a retry message and the UI exposes safe retry timing. It is suitable for local demonstration, not for a public production service.

## 22. What happens if a room ID is invalid?
The dashboard and API validate room identifiers and return explicit safe error states for unknown or malformed values. The user sees a clear error without raw traceback or internal system details.

## 23. How is reproducibility achieved?
Reproducibility is achieved through deterministic generation, fixed config values, controlled splits, versioned artifacts, and the Docker Compose workflow. The project also includes automated leakage and API tests to verify critical invariants.

## 24. What are the main limitations?
The main limitations are the synthetic dataset, one-hour forecast scope, limited optimization evidence beyond one scenario, no production secret management, no real stakeholder trial, and no production hosting claim. These are discussed openly in the report and evidence matrix.

## 25. What would you build next?
The next credible step would be a larger real-data validation program with institutional permission, broader forecasting horizons, calibrated uncertainty, and a more complete operational optimization study. Any live deployment would require a separate production security and privacy review.

## 26. What did YOU personally implement?
This answer is intentionally left for the student to state in the final viva and contribution statement. The repository evidence supports what was implemented, but personal contribution and institutional requirements remain human-owned responsibilities.
