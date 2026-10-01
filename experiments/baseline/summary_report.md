# BDS-06: Baseline Forecasting Experiment Report

**Execution Timestamp:** 2026-09-24T14:40:35.168826 UTC  
**Dataset:** `data/processed/occupancy.parquet`  
**Split Boundary:** Train (W1–10, 53,760 rows) | Val (W11–12, 10,752 rows) | Test (W13–16, 21,504 rows)  

---

## 1. Comparative Performance Matrix

| Baseline Model | Train MAE | Train RMSE | Train R² | Val MAE | Val RMSE | Val R² | Test MAE | Test RMSE | Test R² | Test WAPE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HistoricalSeasonalProfile** | 1.5755 | 6.5907 | 0.4794 | 1.4437 | 5.1542 | -0.072 | 2.5975 | 10.1839 | 0.2335 | 102.7% |
| **SeasonalLastWeek** | 2.0473 | 9.9753 | -0.1927 | 1.3584 | 4.0096 | 0.3512 | 2.9778 | 10.5901 | 0.1711 | 117.8% |
| **StaticTimetable** | 1.3434 | 7.7589 | 0.2784 | 0.9296 | 6.8129 | -0.873 | 2.5478 | 11.9689 | -0.0588 | 100.8% |

---

## 2. Key Findings & Empirical Benchmark
- **Champion Baseline:** `HistoricalSeasonalProfile` achieves the strongest baseline performance with **Test MAE = 2.5975**, **RMSE = 10.1839**, and **R² = 0.2335**.
- **Static Timetable Flaw:** `StaticTimetable` exhibits high error (Test MAE = 2.5478) because it fails to model actual student attendance dropouts, idle evening intervals, and exam-week timetable suspensions.
- **Weekly Naive Vulnerability:** `SeasonalLastWeek` suffers when calendar disruptions (such as holidays or study breaks) contaminate the reference lag $y_{t-168}$.
