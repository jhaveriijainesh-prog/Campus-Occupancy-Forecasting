# BDS-06: Baseline Forecasting Experiment Report

**Execution Timestamp:** 2026-10-08T01:16:31.956806 UTC
**Dataset:** `data/processed/occupancy.parquet`  
**Split Boundary:** Train (W1–10, 53,760 rows) | Val (W11–12, 10,752 rows) | Test (W13–16, 21,504 rows)

---

## 1. Comparative Performance Matrix

| Baseline Model | Train MAE | Train RMSE | Train R² | Val MAE | Val RMSE | Val R² | Test MAE | Test RMSE | Test R² | Test WAPE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HistoricalSeasonalProfile** | 1.9405 | 7.0035 | 0.7543 | 2.6255 | 9.4104 | 0.0706 | 3.2442 | 11.2925 | 0.3695 | 84.8% |
| **SeasonalLastWeek** | 2.8429 | 10.9107 | 0.4038 | 2.5819 | 6.7454 | 0.5225 | 4.8355 | 12.278 | 0.2546 | 126.4% |
| **StaticTimetable** | 2.319 | 9.5985 | 0.5386 | 3.0671 | 13.4252 | -0.8915 | 3.9289 | 14.7939 | -0.0822 | 102.7% |

---

## 2. Key Findings & Empirical Benchmark
- **Champion Baseline:** `HistoricalSeasonalProfile` achieves the strongest baseline performance with **Test MAE = 3.2442**, **RMSE = 11.2925**, and **R² = 0.3695**.
- **Static Timetable Flaw:** `StaticTimetable` exhibits high error (Test MAE = 3.9289) because it fails to model actual student attendance dropouts, idle evening intervals, and exam-week timetable suspensions.
- **Weekly Naive Vulnerability:** `SeasonalLastWeek` suffers when calendar disruptions (such as holidays or study breaks) contaminate the reference lag $y_{t-168}$.
