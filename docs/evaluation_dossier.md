# BDS-06 Evaluation Dossier

**Evidence date:** 2026-09-27  
**Evidence policy:** This dossier reports checked-in repository artifacts and commands executed in the configured `.venv-2` environment. Missing runs are marked rather than inferred.

## Executive Summary

The reproducible forecast evidence supports the XGBoost model over the historical seasonal baseline on the chronological holdout test set. XGBoost test MAE is `1.2775` versus `2.5975` (`50.82%` relative reduction), RMSE is `4.3961` versus `10.1839`, and R2 is `0.8572` versus `0.2335`.

The repository also now contains executed evidence for clustering, scenario simulation, and room allocation under `experiments/analytics/`. The allocation run was optimal and feasible. The scenario result is a recorded what-if perturbation, not a claim that the chosen scenario is operationally optimal.

All intervals below are descriptive point estimates. No confidence intervals, hypothesis tests, or statistical power calculations are present in the repository, so inferential confidence is **not established**.

## Task 3.2 Runtime Addendum (2026-10-01)

The local Docker Compose stack was runtime-verified after this dossier's original evidence date:

| Check | Result | Scope |
| --- | --- | --- |
| Docker runtime | Docker Desktop 4.93.0, Engine 29.8.1, Compose v5.5.1; `desktop-linux`; Linux/amd64; WSL 2; 4 CPUs, about 3.8 GiB | Local Windows host only |
| Build and launch | Project images built; exact `docker compose up --build -d` succeeded; API healthy, dashboard running | Local Compose |
| Readiness and dashboard | API health/readiness and Streamlit health returned 200; dashboard-to-API client calls used `http://api:8000` | Local Compose |
| Authentication | Missing/invalid protected-read key returned 401; read key was denied optimizer access with 403 | Local Compose |
| Metrics and forecast | Campus/building/room metrics succeeded; B01-R101 one-hour point forecast succeeded and remained within known capacity | Synthetic checked-in data |
| Restart/rebuild | `down`, Compose build, and `up` succeeded; API healthy and both restart counts were zero | Local Compose |
| Warmed forecast latency | 20 sequential Compose-DNS APIClient calls: p50 138.29 ms, nearest-rank p95 157.95 ms, maximum 544.25 ms | Single local host; small sample, not production certification |

The p95 is below the SRS NFR-01 target of 200 ms for this small sample only. The maximum outlier and limited sample size prevent treating this as a general SLA. The SRS NFR-02 target is for a 100-room workload; the measured allocation had 50 sessions, so that target remains unverified.

The local live API optimizer comparison returned greedy objective 187 and CBC objective 187 for 50 assignments; CBC status was Optimal and runtime about 1.73 seconds. This is objective parity for one synthetic instance, not evidence that MILP is superior. A live scenario call returned WSH delta -1543.6, SUR delta +0.002174, RFU delta -0.008475, and peak delta +33. The persisted 2026-09-27 scenario artifact has SUR delta +0.002845 for the same parameter signature. This discrepancy is unresolved; do not merge the SUR values or claim a reconciled result.

## Data Foundation

| Check | Result | Evidence |
| --- | ---: | --- |
| Processed occupancy rows | 86,016 | `data/processed/validation_report.json` |
| Rooms | 32 | `data/processed/validation_report.json` |
| Timetable rows | 50 | `data/processed/validation_report.json` |
| Post-cleaning validation | 0 errors, 0 warnings | `data/processed/validation_report.md` |
| Temporal leakage checks | 25 focused tests passed, including leakage tests | `tests/regression/test_leakage.py`, executed 2026-09-27 |

The source data is synthetic and generated with seed `42`; it is not a claim of real sensor provenance.

## Forecast Evaluation

The baseline and XGBoost experiments use the same chronological partitions: train `2026-08-03` through `2026-10-11` (`53,760` rows), validation `2026-10-12` through `2026-10-25` (`10,752` rows), and test `2026-10-26` through `2026-11-22` (`21,504` rows). The XGBoost configuration records one-hour horizon, seed `42`, 48 features, and best iteration `224`.

### Baseline Results

| Model | Split | MAE | RMSE | R2 | WAPE | sMAPE |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| HistoricalSeasonalProfile | Train | 1.5755 | 6.5907 | 0.4794 | 99.07% | 157.1459% |
| HistoricalSeasonalProfile | Validation | 1.4437 | 5.1542 | -0.0720 | 205.30% | 175.7653% |
| HistoricalSeasonalProfile | Test | 2.5975 | 10.1839 | 0.2335 | 102.72% | 163.6674% |
| SeasonalLastWeek | Test | 2.9778 | 10.5901 | 0.1711 | 117.75% | 168.3447% |
| StaticTimetable | Test | 2.5478 | 11.9689 | -0.0588 | 100.75% | 195.7784% |

### XGBoost Results

| Split | MAE | RMSE | R2 | WAPE | sMAPE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Train | 0.7510 | 2.2662 | 0.9384 | 47.23% | 156.8909% |
| Validation | 0.6451 | 3.1662 | 0.5955 | 91.74% | 171.4428% |
| Test | 1.2775 | 4.3961 | 0.8572 | 50.52% | 155.5725% |

MAPE is not reported because `compute_metrics` implements MAE, RMSE, R2, WAPE, and sMAPE only. It must not be reconstructed from the available tables.

### Test Error Slices

The checked-in comparison artifact reports XGBoost MAE improvement over the champion baseline of `69.11%` during day peaks, `50.76%` on weekdays, `69.90%` for auditoriums, and `84.00%` for observations with 36 or more occupants. The model is slightly worse in the low-error night slice (`-4.66%`) and on Sunday (`-9.04%`), which is retained as a limitation rather than hidden.

## Clustering, Scenario, and Optimization Evidence

Generated by:

```powershell
f:/Campus-Occupancy-Forecasting/.venv-2/Scripts/python.exe scripts/run_analytics_evidence.py
```

| Component | Status | Result | Primary artifact |
| --- | --- | --- | --- |
| Room clustering | verified | 32 rooms, 6 selected K-Means clusters, silhouette `0.4378954459`, seed `42` | `experiments/analytics/clustering.json` |
| Scenario simulation | verified | Scenario `7d1ec4ea14b6`; occupancy `x1.15`, enrollment `x1.10`, room `B01-R101` closed; WSH delta `-1543.6` | `experiments/analytics/scenario.json` |
| Room allocation | verified | CBC status `Optimal`, 50 assignments, objective `187.0`, runtime `1.578141s` | `experiments/analytics/optimization.json` |

The scenario's peak occupancy increased by `33` and room frequency decreased by `0.008475`; this is a tradeoff, not a universal improvement claim. No alternative scenario sweep was run.

## Reproduction and Environment Checks

| Check | Status | Detail |
| --- | --- | --- |
| Leakage, validation, cleaning tests | verified | `25 passed` |
| Clustering, simulation, optimization tests | verified | `10 passed`, with 4 PuLP deprecation warnings |
| Forecast artifact provenance | verified | Existing JSON, CSV/Parquet predictions, config, and comparison artifacts are present |
| Full test suite | verified (previous run) | `176 passed`, `0 failed`, `643 warnings`; latest recorded duration 45.87 s in `.venv-2`. Existing `coverage.xml` reports an 86.48% line rate; it was not regenerated for this addendum. |
| Docker/Compose execution | verified locally | Runtime/build/start/readiness/dashboard/API/auth/metrics/forecast/rebuild-restart evidence recorded in the Task 3.2 completion report and 2026-10-01 runtime addendum above. |
| Dashboard smoke evidence | partial | Streamlit AppTest in the dashboard container verified Overview readiness/KPIs and Forecast Explorer success/unknown-room states without exceptions; no browser screenshot, accessibility audit, or narrow-viewport review is included |

## Limitations and Next Evidence

The forecast evidence covers a one-hour XGBoost point forecast, not the full multi-horizon or calibrated p10/p50/p90 contract described in the requirements. Clustering, simulation, and optimization are backed by a small number of deterministic runs, but not by sensitivity analyses or repeated-run variance reports. Docker is verified on the current Windows/WSL 2 host; external clean-machine portability and production hosting remain unverified.

## Artifact Manifest

- [Baseline metrics](../experiments/baseline/metrics.json)
- [XGBoost metrics](../experiments/xgboost/metrics.json)
- [Forecast comparison metrics](../experiments/comparison/comparison_metrics.json)
- [Analytics run summary](../experiments/analytics/run_summary.json)
- [Analytics evidence runner](../scripts/run_analytics_evidence.py)
- [Data validation report](../data/processed/validation_report.md)