# BDS-06: Advanced XGBoost Model Evaluation & Benchmark Dossier

**Execution Date:** 2026-10-08T01:16:41.264145+00:00
**Architecture:** Extreme Gradient Boosting (`XGBRegressor`)  
**Random Seed:** `42` (Bit-level reproducible)  
**Partitioning:** Chronological (Train: 53,760 rows, Val: 10,752 rows, Test: 21,504 rows)  
**Best Tree Iteration:** `179`

---

## 1. Experimental Comparison with Baseline

| Model Candidate | Test MAE | Test RMSE | Test R² | Test WAPE | Relative MAE Imp. |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HistoricalSeasonalProfile (Champion Baseline)** | 3.2442 | 11.2925 | 0.3695 | 84.8% | Baseline |
| **Advanced XGBoost Forecaster** | **1.6831** | **5.2748** | **0.8624** | **44.0%** | **+48.12%** |


### Empirical Comparison Verdict:
> [!IMPORTANT]
> **Validated Superiority:** The advanced XGBoost model demonstrably outperforms the champion baseline on the holdout test partition:
> - **MAE Reduction:** 1.6831 vs. 3.2442 (**48.12% error reduction**).
> - **RMSE Reduction:** 5.2748 vs. 11.2925 (**53.29% reduction**).
> - **Variance Explained ($R^2$):** **0.8624** vs. 0.3695 (gain of **+0.4929** points).


---

## 2. XGBoost Performance Across Chronological Splits

| Partition | MAE | RMSE | R² | WAPE | sMAPE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Train (W1–10)** | 0.9576 | 2.7232 | 0.9629 | 25.4% | 150.9% |
| **Validation (W11–12)** | 0.7904 | 2.4826 | 0.9353 | 40.2% | 166.2% |
| **Holdout Test (W13–16)** | 1.6831 | 5.2748 | 0.8624 | 44.0% | 152.5% |

---

## 3. Top-10 Explanatory Features (Gain Attribution)

| Rank | Feature Name | Relative Gain |
| :---: | :--- | :---: |
| 1 | `scheduled_enrollment` | 24.98% |
| 2 | `is_scheduled` | 19.33% |
| 3 | `enrollment_vs_rolling_mean_24h` | 18.15% |
| 4 | `is_exam_period` | 6.92% |
| 5 | `has_event` | 4.24% |
| 6 | `is_holiday` | 3.32% |
| 7 | `room_id` | 2.99% |
| 8 | `campus_event_impact_factor` | 2.87% |
| 9 | `lag_24h_utilization` | 2.59% |
| 10 | `capacity` | 2.32% |

---

## 4. Architectural Leakage Prevention Verification
1. **Zero Future Target Contamination:** All lag features ($y_{t-k}$) and rolling statistics are calculated strictly on observations preceding timestamp $(t - H)$.
2. **Preprocessing Isolation:** Categorical index encodings and feature statistics were derived exclusively from the training partition.
3. **Chronological Splitting:** The holdout test set occupies Weeks 13–16, strictly subsequent to train and validation.
