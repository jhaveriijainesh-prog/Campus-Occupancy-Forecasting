# BDS-06: Advanced XGBoost Model Evaluation & Benchmark Dossier

**Execution Date:** 2026-09-24T14:44:47.626610+00:00  
**Architecture:** Extreme Gradient Boosting (`XGBRegressor`)  
**Random Seed:** `42` (Bit-level reproducible)  
**Partitioning:** Chronological (Train: 53,760 rows, Val: 10,752 rows, Test: 21,504 rows)  
**Best Tree Iteration:** `224`  

---

## 1. Experimental Comparison with Baseline

| Model Candidate | Test MAE | Test RMSE | Test R² | Test WAPE | Relative MAE Imp. |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **HistoricalSeasonalProfile (Champion Baseline)** | 2.5975 | 10.1839 | 0.2335 | 102.7% | Baseline |
| **Advanced XGBoost Forecaster** | **1.2775** | **4.3961** | **0.8572** | **50.5%** | **+50.82%** |


### Empirical Comparison Verdict:
> [!IMPORTANT]
> **Validated Superiority:** The advanced XGBoost model demonstrably outperforms the champion baseline on the holdout test partition:
> - **MAE Reduction:** 1.2775 vs. 2.5975 (**50.82% error reduction**).
> - **RMSE Reduction:** 4.3961 vs. 10.1839 (**56.83% reduction**).
> - **Variance Explained ($R^2$):** **0.8572** vs. 0.2335 (gain of **+0.6237** points).


---

## 2. XGBoost Performance Across Chronological Splits

| Partition | MAE | RMSE | R² | WAPE | sMAPE |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Train (W1–10)** | 0.751 | 2.2662 | 0.9384 | 47.2% | 156.9% |
| **Validation (W11–12)** | 0.6451 | 3.1662 | 0.5955 | 91.7% | 171.4% |
| **Holdout Test (W13–16)** | 1.2775 | 4.3961 | 0.8572 | 50.5% | 155.6% |

---

## 3. Top-10 Explanatory Features (Gain Attribution)

| Rank | Feature Name | Relative Gain |
| :---: | :--- | :---: |
| 1 | `enrollment_vs_rolling_mean_24h` | 15.89% |
| 2 | `is_scheduled` | 14.83% |
| 3 | `scheduled_enrollment` | 12.47% |
| 4 | `is_exam_period` | 11.42% |
| 5 | `room_type` | 6.69% |
| 6 | `lag_24h` | 6.41% |
| 7 | `has_event` | 5.92% |
| 8 | `capacity` | 4.86% |
| 9 | `lag_24h_utilization` | 3.35% |
| 10 | `is_holiday` | 2.63% |

---

## 4. Architectural Leakage Prevention Verification
1. **Zero Future Target Contamination:** All lag features ($y_{t-k}$) and rolling statistics are calculated strictly on observations preceding timestamp $(t - H)$.
2. **Preprocessing Isolation:** Categorical index encodings and feature statistics were derived exclusively from the training partition.
3. **Chronological Splitting:** The holdout test set occupies Weeks 13–16, strictly subsequent to train and validation.
