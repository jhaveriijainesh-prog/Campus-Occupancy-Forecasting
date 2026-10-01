# BDS-06: Baseline Forecasting Models & Benchmark Specification

**Academic Context:** T.Y. B.Sc. Data Science – Semester V Capstone Project  
**Module Reference:** `app/forecasting/baseline.py`  
**Execution Script:** `scripts/run_baseline.py`  
**Artifacts Destination:** `experiments/baseline/`  
**Evaluation Protocol:** Strict Chronological Temporal Splits (No Random Shuffling)  

> **Implementation status note (2026-10-01):** This document records the historical baseline experiment and candidate rationale. The currently served model is an XGBoost one-hour point regressor; multi-horizon and quantile models described as candidates below are not served by the current artifact. See `docs/evaluation_dossier.md` for the current result and limits.

---

## 1. Executive Summary & Purpose of Baseline Models

In empirical machine learning and data science research, establishing a solid, transparent, and interpretable **benchmark baseline** is mandatory before evaluating complex algorithms (such as LightGBM, XGBoost, or Deep Temporal Networks).

Without baselines:
1. It is impossible to ascertain whether complex ML models are truly extracting non-linear spatiotemporal interactions or simply memorizing diurnal and calendar periodicity.
2. Complex pipelines risk introducing unnecessary inference latency and maintenance overhead without demonstrable accuracy gains over simple statistical heuristics.

For **BDS-06**, we formulated and empirically benchmarked three candidate baseline architectures across 86,016 hourly observations partitioned into chronological Train, Validation, and Test splits.

---

## 2. Baseline Model Candidates

### 2.1 Baseline 1: Historical Seasonal Stratified Profile (`HistoricalSeasonalProfileBaseline`) — **Champion Baseline**
- **Formulation:** Computes the historical sample mean headcount for every unique combination of room, day-of-week, hour, and scheduled status observed exclusively in the training partition:
  $$\hat{y}_{r, d, h, s} = \frac{1}{|S_{r,d,h,s}|} \sum_{i \in S_{r,d,h,s}} y_{r,i}$$
  Where $S_{r,d,h,s}$ represents the index set of training observations matching room $r$, day $d$, hour $h$, and schedule state $s$.
- **Hierarchical Fallback:** If a specific tuple is unseen in the training partition (e.g., an unusual combination), the model falls back gracefully to `(room_id, hour)` mean $\rightarrow$ `room_id` overall mean $\rightarrow$ global training mean.

### 2.2 Baseline 2: Weekly Seasonal Naive Lag (`SeasonalLastWeekBaseline`)
- **Formulation:** Assumes that the occupancy today at hour $h$ matches exactly what was observed in the identical room 7 days (168 hours) prior:
  $$\hat{y}_{r, t} = y_{r, \, t - 168}$$
- **Concept:** Standard benchmark in seasonal time series (e.g. "Next Monday at 10:00 will look like last Monday at 10:00").

### 2.3 Baseline 3: Static Timetable Enrollment (`StaticTimetableBaseline`)
- **Formulation:** Assumes that occupancy equals the registered course enrollment $N$ whenever a course is scheduled, and 0 during unscheduled periods:
  $$\hat{y}_{r, t} = \begin{cases} \text{Enrolled Students}_c & \text{if room } r \text{ is booked for course } c \text{ at slot } t \\ 0 & \text{otherwise} \end{cases}$$
- **Concept:** The default naive rule utilized by traditional campus timetable coordinators.

---

## 3. Why the Historical Seasonal Profile Was Selected as Primary

The **Historical Seasonal Stratified Profile** was crowned as the primary champion baseline because:

1. **Robustness to Calendar Irregularities:** Unlike `SeasonalLastWeek` (which predicts 0 on a normal class day if the preceding week was a holiday like Diwali), the stratified profile averages across all 10 normal training weeks, smoothing out isolated anomalies.
2. **Attendance Decay Grounding:** Unlike `StaticTimetable` (which naively expects 100% attendance of registered students), the historical profile empirically captures true student attendance rates (~80–85%) without manual heuristics.
3. **Interpretability & Lookup Structure:** The model is an in-memory lookup table. Its serving latency was not separately benchmarked in this experiment, so no sub-millisecond performance claim is made.

---

## 4. Underlying Assumptions

1. **[ASSUMPTION-BASE-01] Recurrent Weekly Seasonality:** Campus occupancy is assumed to be predominantly periodic on a 168-hour (7-day) cycle governed by the academic timetable.
2. **[ASSUMPTION-BASE-02] Stationarity Across Normal Weeks:** Attendance behavior during regular lecture weeks in the first half of the semester (Weeks 1–10) is assumed to provide a meaningful statistical prior for regular weeks in the second half.
3. **[ASSUMPTION-BASE-03] Spatial Independence:** Each room's profile is estimated independently without borrowing spatial strength from adjacent classrooms or shared building zones.

---

## 5. Inherent Limitations of Heuristic Baselines

While the Historical Seasonal Profile provides an effective anchor, it exhibits severe structural limitations that motivate advanced Machine Learning:

1. **Inability to Adapt to Academic Regime Shifts:**
   - During **Mid-Semester and End-Semester Examination Weeks**, normal timetable classes are canceled, and designated lecture halls transition into dense examination seatings. A static historical profile continues predicting regular class numbers, causing high residual error during exam blocks.
2. **Ignorance of Weather & Sudden Campus Events:**
   - Baselines cannot incorporate external dynamic signals (e.g., sudden symposiums, severe weather disruptions, or faculty illness announcements).
3. **Point Forecast Only (No Uncertainty Quantification):**
   - The heuristic produces a single deterministic point prediction $\hat{y}$ without confidence intervals (p10/p90 quantiles), making risk-aware HVAC or capacity planning impossible.
4. **No Spatial Feature Crosses:**
   - Cannot learn cross-building commute patterns or floor-level ventilation interactions.

---

## 6. Empirical Results & Chronological Benchmark Matrix

The baseline experiment was executed on the processed campus dataset (`86,016` records) using strict chronological partitioning:
- **Training Set:** Weeks 1–10 (`2026-08-03` to `2026-10-11`, **53,760 rows**)
- **Validation Set:** Weeks 11–12 (`2026-10-12` to `2026-10-25`, **10,752 rows**)
- **Test Set:** Weeks 13–16 (`2026-10-26` to `2026-11-22`, **21,504 rows**)

### Evaluation Results Table:

| Baseline Model | Train MAE | Train RMSE | Train R² | Val MAE | Val RMSE | Val R² | Test MAE | Test RMSE | Test R² | Test WAPE |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **HistoricalSeasonalProfile (Champion)** | **1.5755** | **6.5907** | **0.4794** | 1.4437 | 5.1542 | -0.0720 | **2.5975** | **10.1839** | **0.2335** | **102.7%** |
| **SeasonalLastWeek (Weekly Naive)** | 2.0473 | 9.9753 | -0.1927 | **1.3584** | **4.0096** | **0.3512** | 2.9778 | 10.5901 | 0.1711 | 117.8% |
| **StaticTimetable (Administrative)** | 1.3434 | 7.7589 | 0.2784 | 0.9296 | 6.8129 | -0.8730 | 2.5478 | 11.9689 | -0.0588 | 100.8% |

---

## 7. Analysis of Benchmark Findings

1. **Historical Seasonal Profile Dominance on Test Partition:**
   The `HistoricalSeasonalProfile` achieved the highest explained variance on the holdout test set with **$R^2 = 0.2335$** and an **$\text{RMSE} = 10.18$**, outperforming both the weekly naive lag ($R^2 = 0.1711$) and the static timetable ($R^2 = -0.0588$).
2. **Static Timetable Limitation on This Synthetic Test Set:**
   The negative $R^2$ ($-0.0588$) of `StaticTimetable` on this holdout indicates that this rule underperformed the test-set mean predictor for the generated dataset. It supports further study but does not prove the same result for a real campus.
3. **Subsequent XGBoost Evidence:**
   The checked-in XGBoost experiment later recorded test MAE `1.2775` and R2 `0.8572` on the same chronological split, versus this baseline's MAE `2.5975` and R2 `0.2335`. These are descriptive results on synthetic data without confidence intervals. The current API still supports only the one-hour point forecast; this result does not establish multi-horizon or calibrated-interval performance.

---

## 8. Reproducibility & Artifact Manifest

All artifacts from this experiment are preserved under `experiments/baseline/`:
- `experiments/baseline/config.json`: Declarative experiment parameters and split dates.
- `experiments/baseline/metrics.json`: Full floating-point metric results across all splits.
- `experiments/baseline/test_predictions.parquet`: Itemized row-level predictions for all test hours.
- `experiments/baseline/summary_report.md`: Executive summary table.

Reproduce the run at any time via:
```bash
python scripts/run_baseline.py --data-path data/processed/occupancy.parquet --output-dir experiments/baseline
```
