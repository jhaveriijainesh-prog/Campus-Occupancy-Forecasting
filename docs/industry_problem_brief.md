# BDS-06 Industry Problem Brief

**Project:** Campus Occupancy Forecasting with Spatiotemporal Analytics and Capacity Optimization  
**Academic context:** T.Y. B.Sc. Data Science, Semester V  
**Evidence boundary:** The problem framing and personas below come from the project requirements. No campus stakeholder interviews, time-and-motion study, or live facility audit is present in the repository.

## Problem

Campus room assignments are commonly planned from scheduled enrollment and nominal room capacity. Those figures do not, by themselves, describe actual occupancy, unused seat-hours, or variation across time and room types. The capstone investigates whether aggregate occupancy history, schedules, and room metadata can support more evidence-based space planning.

The project uses synthetic data. It does not claim that a specific college currently experiences measured congestion, energy waste, or scheduling bottlenecks. Those statements require stakeholder and campus evidence before being presented as observed facts.

## Stakeholder Map

| Stakeholder | Need / decision | Product interaction | Evidence status |
| --- | --- | --- | --- |
| Facilities/space planner | Review aggregate utilization and near-term room occupancy | Overview KPIs, scope filters, Forecast Explorer | Intended persona; no interview evidence |
| Academic scheduler | Compare capacity-compatible room allocations | Optimization API/offline comparison evidence | Intended persona; no formal workflow acceptance |
| Technical operator | Start services, check dependencies, manage credentials | Runbook, health/readiness, logs, Compose | Local runtime verified; no production operator trial |
| Academic evaluator | Assess data science methods, leakage, tests, reproducibility, and limits | Dossier, test artifacts, system card, API/docs | Deliverables mapped; evaluator feedback not present |
| Students represented by aggregate counts | Privacy and non-surveillance protections | Aggregate synthetic room-level data only | No person-level data in intended dataset; institutional privacy review still required for real data |

## Current Workflow and Pain Points

The project requirements hypothesize that planners may rely on nominal enrollment, manual surveys, and anecdotal reports. This repository does not contain field observations verifying how a real institution currently allocates rooms. These points are hypotheses to validate with facilities staff, not research findings.

## User Stories

- As a facilities planner, I can see whether the API, occupancy data, and forecast model are ready before interpreting KPIs.
- As a facilities planner, I can inspect SUR, RFU, and WSH for campus, building, or room scope.
- As a planner, I can request a supported one-hour forecast for a room and see its timestamp/model metadata.
- As a technical operator, I can start the API and dashboard with Compose and diagnose missing artifacts using readiness and logs.
- As an evaluator, I can trace model claims to chronological test metrics, source artifacts, tests, and documented limitations.

## Scope and Exclusions

**Implemented/verified local workflow:** synthetic artifact preparation; validation/cleaning; aggregate utilization; one-hour XGBoost point forecast; API; two-page read-only dashboard; room clustering; aggregate what-if simulation; greedy/CBC capacity allocation; local Docker Compose runtime.

**Not established or excluded from the startup dashboard:** live sensor or timetable-system integration; real occupancy collection; calibrated forecast intervals; horizons beyond one hour; geographic heatmap; optimizer/simulation/clustering pages; production identity/secret management; automated HVAC actions; individual attendance or disciplinary decisions; external production hosting.

## Risks and Misuse Cases

| Risk / misuse | Mitigation/evidence | Remaining limitation |
| --- | --- | --- |
| Synthetic results presented as real campus facts | Label data synthetic; cite generator/provenance and report limitations | Real data study and stakeholder validation remain open |
| Forecast treated as calibrated uncertainty or future safety guarantee | API identifies point-estimate-only; one-hour horizon enforced | No uncertainty calibration or safety use |
| Individual student surveillance | Aggregate room-level synthetic counts; reject configured PII-like ingestion columns | Formal privacy review required before real institutional data |
| Read credential used for writes/optimization | Permission model; live read key denied optimizer access with 403 | Static development keys; no production IAM |
| Stale/missing artifacts interpreted as zero occupancy | Readiness state and named dependency failures | Operator still needs artifact recovery process |
| Optimization assumed universally better | Greedy and MILP comparison reported; live objective was equal at 187 | Only one synthetic allocation instance and no sensitivity study |
| Local development keys exposed on a network | Explicit development-only warnings | Compose uses debug/development settings; do not publicly expose |

## Success Measures and Evidence

- Forecast: holdout MAE 1.2775 and RMSE 4.3961 for XGBoost, compared with historical seasonal MAE 2.5975 and RMSE 10.1839. Results are synthetic, descriptive, and lack significance intervals.
- Utilization: deterministic formulas and live campus/building/room API responses; no independent real-campus ground truth.
- Clustering: 6 clusters for 32 rooms; silhouette 0.4378954459; no stability threshold was specified.
- Scenario: persisted/live runs report aggregate deltas; SUR differs across the two recorded execution contexts and requires reconciliation.
- Optimization: CBC found an optimal feasible allocation for 50 assignments; live greedy and CBC objectives both equaled 187; no claimed improvement.
- Performance: 20 warmed Compose-DNS forecast calls had sample p95 157.95 ms, maximum 544.25 ms; small local sample only.
- Reproducibility: Compose build/start/health/API/dashboard/rebuild-restart verified on 2026-10-01.

The only numeric forecast latency threshold found in the SRS is NFR-01 p95 <= 200 ms. The solver NFR-02 threshold is <=45 seconds on a 100-room workload; that workload was not tested. No formal threshold is defined for peak detection, scenario stability, or visualization quality.

## Prioritized Backlog and Current Task State

The authoritative task order is [startup-mvp-tasklist.md](../project-tasks/startup-mvp-tasklist.md). Tasks 0.1 through 3.2 are marked complete with the full Python suite at 176 passed / 0 failed / 643 warnings. Task 3.3 is the final documentation/handoff task. Human-owned validation, recorded demo, contribution hours, and institutional packaging are distinguished from repository work in the final checklist.
