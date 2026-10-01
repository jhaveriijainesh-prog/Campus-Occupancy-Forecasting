"""
BDS-06: Complete Forecasting Comparison & Error Slicing Script
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Performs granular error analysis between:
  1. Champion Baseline (HistoricalSeasonalProfile)
  2. Advanced XGBoost Forecaster

Computes:
  - Global metrics: MAE, RMSE, R2, WAPE, sMAPE
  - Error distribution: Mean bias, std, skewness, 90th & 99th percentiles
  - Peak-period errors (10-12, 14-16) vs off-peak
  - Low-occupancy (0-5) vs High-occupancy (40+) errors
  - Weekday vs. Weekend errors
  - Room-level and Room-type errors

Generates high-resolution visualization figures and saves them under:
  docs/assets/
  experiments/comparison/
"""

import json
import sys
from pathlib import Path
from typing import Dict, Any

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

from app.forecasting.baseline import compute_metrics


def run_comparison_analysis(
    baseline_path: str = "experiments/baseline/test_predictions.parquet",
    xgboost_path: str = "experiments/xgboost/test_predictions.parquet",
    rooms_path: str = "data/processed/rooms.parquet",
    events_path: str = "data/processed/events.parquet",
    output_dir: str = "experiments/comparison",
    assets_dir: str = "docs/assets"
) -> Dict[str, Any]:
    """Execute complete error analysis, generate plots, and export results."""
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    asset_path = Path(assets_dir)
    asset_path.mkdir(parents=True, exist_ok=True)

    # 1. Load data
    base_df = pd.read_parquet(baseline_path)
    xgb_df = pd.read_parquet(xgboost_path)
    rooms_df = pd.read_parquet(rooms_path)
    events_df = pd.read_parquet(events_path)

    # Merge on observation_id
    df = base_df.merge(
        xgb_df[["observation_id", "predicted_headcount"]],
        on="observation_id"
    )
    df = df.merge(
        rooms_df[["room_id", "room_type", "building_id", "floor"]],
        on="room_id",
        how="left"
    )

    # Compute errors & residuals
    y_true = df["actual_headcount"].values
    y_base = df["pred_HistoricalSeasonalProfile"].values
    y_xgb = df["predicted_headcount"].values

    df["err_base"] = y_true - y_base
    df["abs_err_base"] = np.abs(df["err_base"])
    df["err_xgb"] = y_true - y_xgb
    df["abs_err_xgb"] = np.abs(df["err_xgb"])

    # -------------------------------------------------------------
    # 2. Overall Metrics & Error Distributions
    # -------------------------------------------------------------
    m_base = compute_metrics(y_true, y_base)
    m_xgb = compute_metrics(y_true, y_xgb)

    dist_stats = {
        "baseline": {
            "mean_bias": round(float(np.mean(df["err_base"])), 4),
            "median_err": round(float(np.median(df["err_base"])), 4),
            "std_err": round(float(np.std(df["err_base"])), 4),
            "skewness": round(float(stats.skew(df["err_base"])), 4),
            "p90_abs_err": round(float(np.percentile(df["abs_err_base"], 90)), 4),
            "p99_abs_err": round(float(np.percentile(df["abs_err_base"], 99)), 4),
        },
        "xgboost": {
            "mean_bias": round(float(np.mean(df["err_xgb"])), 4),
            "median_err": round(float(np.median(df["err_xgb"])), 4),
            "std_err": round(float(np.std(df["err_xgb"])), 4),
            "skewness": round(float(stats.skew(df["err_xgb"])), 4),
            "p90_abs_err": round(float(np.percentile(df["abs_err_xgb"], 90)), 4),
            "p99_abs_err": round(float(np.percentile(df["abs_err_xgb"], 99)), 4),
        }
    }

    # -------------------------------------------------------------
    # 3. Peak Period Slicing
    # -------------------------------------------------------------
    def assign_period(h: int) -> str:
        if h in [10, 11, 14, 15]:
            return "Day Peak (10-12, 14-16)"
        elif 8 <= h <= 17:
            return "Day Regular (08-10, 12-14, 16-18)"
        elif 18 <= h <= 21:
            return "Evening (18-22)"
        else:
            return "Night (22-08)"

    df["time_period"] = df["hour"].apply(assign_period)
    peak_stats = {}
    for p, grp in df.groupby("time_period"):
        b_m = compute_metrics(grp["actual_headcount"], grp["pred_HistoricalSeasonalProfile"])
        x_m = compute_metrics(grp["actual_headcount"], grp["predicted_headcount"])
        peak_stats[p] = {
            "sample_count": len(grp),
            "baseline_MAE": b_m["MAE"],
            "baseline_RMSE": b_m["RMSE"],
            "xgboost_MAE": x_m["MAE"],
            "xgboost_RMSE": x_m["RMSE"],
            "mae_delta": round(b_m["MAE"] - x_m["MAE"], 4),
            "mae_improvement_pct": round(((b_m["MAE"] - x_m["MAE"]) / b_m["MAE"]) * 100, 2)
        }

    # -------------------------------------------------------------
    # 4. Low-Occupancy vs High-Occupancy Slicing
    # -------------------------------------------------------------
    def assign_occ_bracket(headcount: int) -> str:
        if headcount <= 5:
            return "Low / Idle (0-5 occupants)"
        elif headcount <= 35:
            return "Moderate (6-35 occupants)"
        else:
            return "High (36+ occupants)"

    df["occ_bracket"] = df["actual_headcount"].apply(assign_occ_bracket)
    occ_stats = {}
    for b, grp in df.groupby("occ_bracket"):
        b_m = compute_metrics(grp["actual_headcount"], grp["pred_HistoricalSeasonalProfile"])
        x_m = compute_metrics(grp["actual_headcount"], grp["predicted_headcount"])
        occ_stats[b] = {
            "sample_count": len(grp),
            "baseline_MAE": b_m["MAE"],
            "xgboost_MAE": x_m["MAE"],
            "mae_improvement_pct": round(((b_m["MAE"] - x_m["MAE"]) / max(0.001, b_m["MAE"])) * 100, 2)
        }

    # -------------------------------------------------------------
    # 5. Weekday vs Weekend Slicing
    # -------------------------------------------------------------
    def assign_day_type(dow: str) -> str:
        if dow in ["Saturday"]:
            return "Saturday (Half-Day)"
        elif dow in ["Sunday"]:
            return "Sunday (Weekend Idle)"
        else:
            return "Weekday (Mon-Fri)"

    df["day_type"] = df["day_of_week"].apply(assign_day_type)
    day_stats = {}
    for d, grp in df.groupby("day_type"):
        b_m = compute_metrics(grp["actual_headcount"], grp["pred_HistoricalSeasonalProfile"])
        x_m = compute_metrics(grp["actual_headcount"], grp["predicted_headcount"])
        day_stats[d] = {
            "sample_count": len(grp),
            "baseline_MAE": b_m["MAE"],
            "baseline_RMSE": b_m["RMSE"],
            "xgboost_MAE": x_m["MAE"],
            "xgboost_RMSE": x_m["RMSE"],
            "mae_improvement_pct": round(((b_m["MAE"] - x_m["MAE"]) / b_m["MAE"]) * 100, 2)
        }

    # -------------------------------------------------------------
    # 6. Room-Level & Room-Type Slicing
    # -------------------------------------------------------------
    room_type_stats = {}
    for rt, grp in df.groupby("room_type"):
        b_m = compute_metrics(grp["actual_headcount"], grp["pred_HistoricalSeasonalProfile"])
        x_m = compute_metrics(grp["actual_headcount"], grp["predicted_headcount"])
        room_type_stats[rt] = {
            "sample_count": len(grp),
            "baseline_MAE": b_m["MAE"],
            "baseline_RMSE": b_m["RMSE"],
            "xgboost_MAE": x_m["MAE"],
            "xgboost_RMSE": x_m["RMSE"],
            "mae_improvement_pct": round(((b_m["MAE"] - x_m["MAE"]) / b_m["MAE"]) * 100, 2)
        }

    # Individual room stats
    room_individual_stats = []
    for r_id, grp in df.groupby("room_id"):
        b_m = compute_metrics(grp["actual_headcount"], grp["pred_HistoricalSeasonalProfile"])
        x_m = compute_metrics(grp["actual_headcount"], grp["predicted_headcount"])
        cap = int(grp["capacity"].iloc[0])
        rt = grp["room_type"].iloc[0]
        room_individual_stats.append({
            "room_id": r_id,
            "room_type": rt,
            "capacity": cap,
            "baseline_MAE": b_m["MAE"],
            "xgboost_MAE": x_m["MAE"],
            "mae_improvement_pct": round(((b_m["MAE"] - x_m["MAE"]) / max(0.001, b_m["MAE"])) * 100, 2)
        })

    room_individual_df = pd.DataFrame(room_individual_stats)
    top_improved_rooms = room_individual_df.sort_values(by="mae_improvement_pct", ascending=False).head(5).to_dict(orient="records")
    hardest_rooms = room_individual_df.sort_values(by="xgboost_MAE", ascending=False).head(5).to_dict(orient="records")

    # -------------------------------------------------------------
    # 7. Generate Visualizations
    # -------------------------------------------------------------
    sns.set_theme(style="whitegrid")

    # Figure 1: Residual Distribution Comparison
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.kdeplot(df["err_base"], label=f"Baseline (std={dist_stats['baseline']['std_err']:.2f})", color="crimson", lw=2, ax=ax)
    sns.kdeplot(df["err_xgb"], label=f"XGBoost (std={dist_stats['xgboost']['std_err']:.2f})", color="royalblue", lw=2, ax=ax)
    ax.axvline(0, color="black", linestyle="--", alpha=0.7)
    ax.set_title("Residual Error Distribution (Actual - Predicted) on Test Set", fontsize=14, fontweight="bold")
    ax.set_xlabel("Residual (Occupants)", fontsize=12)
    ax.set_ylabel("Density", fontsize=12)
    ax.set_xlim(-40, 40)
    ax.legend(fontsize=11)
    fig.tight_layout()
    fig1_path = asset_path / "residual_distribution.png"
    fig.savefig(fig1_path, dpi=200)
    fig.savefig(out_dir / "residual_distribution.png", dpi=200)
    plt.close(fig)

    # Figure 2: MAE by Hour of Day
    hourly_df = df.groupby("hour")[["abs_err_base", "abs_err_xgb"]].mean().reset_index()
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.plot(hourly_df["hour"], hourly_df["abs_err_base"], marker="o", color="crimson", lw=2.5, label="Historical Seasonal Baseline")
    ax.plot(hourly_df["hour"], hourly_df["abs_err_xgb"], marker="s", color="royalblue", lw=2.5, label="Advanced XGBoost Forecaster")
    ax.axvspan(10, 12, color="orange", alpha=0.2, label="Morning Peak (10-12)")
    ax.axvspan(14, 16, color="orange", alpha=0.1, label="Afternoon Peak (14-16)")
    ax.set_title("Mean Absolute Error (MAE) Across 24 Operating Hours", fontsize=14, fontweight="bold")
    ax.set_xlabel("Hour of Day (00:00 to 23:00)", fontsize=12)
    ax.set_ylabel("Mean Absolute Error (Seats)", fontsize=12)
    ax.set_xticks(range(24))
    ax.legend(fontsize=10, loc="upper right")
    fig.tight_layout()
    fig2_path = asset_path / "mae_by_hour.png"
    fig.savefig(fig2_path, dpi=200)
    fig.savefig(out_dir / "mae_by_hour.png", dpi=200)
    plt.close(fig)

    # Figure 3: MAE by Room Type Bar Chart
    rt_plot_df = pd.DataFrame([
        {"room_type": rt, "Baseline MAE": d["baseline_MAE"], "XGBoost MAE": d["xgboost_MAE"]}
        for rt, d in room_type_stats.items()
    ]).melt(id_vars="room_type", var_name="Model", value_name="MAE")

    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=rt_plot_df, x="room_type", y="MAE", hue="Model", palette=["crimson", "royalblue"], ax=ax)
    ax.set_title("Forecasting Error by Room Type Facility", fontsize=14, fontweight="bold")
    ax.set_xlabel("Room Facility Type", fontsize=12)
    ax.set_ylabel("Mean Absolute Error (Seats)", fontsize=12)
    for p in ax.patches:
        height = p.get_height()
        if height > 0:
            ax.annotate(f"{height:.2f}",
                        (p.get_x() + p.get_width() / 2., height),
                        ha="center", va="bottom", fontsize=10, xytext=(0, 3),
                        textcoords="offset points")
    fig.tight_layout()
    fig3_path = asset_path / "mae_by_room_type.png"
    fig.savefig(fig3_path, dpi=200)
    fig.savefig(out_dir / "mae_by_room_type.png", dpi=200)
    plt.close(fig)

    # Figure 4: Actual vs Predicted Time-Series Horizon Sample (Auditorium & Lecture Hall)
    sample_room = "B04-R101"
    sample_df = df[(df["room_id"] == sample_room) & (df["date"].between("2026-10-26", "2026-11-01"))].sort_values("timestamp")

    fig, ax = plt.subplots(figsize=(13, 5))
    ax.plot(sample_df["timestamp"], sample_df["actual_headcount"], color="black", lw=2, label="Actual Observed Headcount")
    ax.plot(sample_df["timestamp"], sample_df["pred_HistoricalSeasonalProfile"], color="crimson", linestyle="--", lw=1.5, label="Baseline Forecast")
    ax.plot(sample_df["timestamp"], sample_df["predicted_headcount"], color="royalblue", lw=2, label="XGBoost Forecast")
    ax.set_title(f"Test Set Dynamic Forecast: Room {sample_room} (Capacity 150) - Week 13 Sample", fontsize=13, fontweight="bold")
    ax.set_ylabel("Occupancy Headcount", fontsize=12)
    ax.legend(fontsize=11)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig4_path = asset_path / "forecast_time_series_sample.png"
    fig.savefig(fig4_path, dpi=200)
    fig.savefig(out_dir / "forecast_time_series_sample.png", dpi=200)
    plt.close(fig)

    # -------------------------------------------------------------
    # 8. Compile Master Summary JSON
    # -------------------------------------------------------------
    comparison_results = {
        "overall_metrics": {
            "baseline": m_base,
            "xgboost": m_xgb,
            "relative_mae_improvement_pct": round(((m_base["MAE"] - m_xgb["MAE"]) / m_base["MAE"]) * 100, 2),
            "relative_rmse_improvement_pct": round(((m_base["RMSE"] - m_xgb["RMSE"]) / m_base["RMSE"]) * 100, 2),
            "r2_gain": round(m_xgb["R2"] - m_base["R2"], 4)
        },
        "error_distribution": dist_stats,
        "peak_period_slices": peak_stats,
        "occupancy_bracket_slices": occ_stats,
        "day_type_slices": day_stats,
        "room_type_slices": room_type_stats,
        "hardest_rooms": hardest_rooms,
        "most_improved_rooms": top_improved_rooms,
        "visualizations": [
            str(fig1_path),
            str(fig2_path),
            str(fig3_path),
            str(fig4_path)
        ]
    }

    with open(out_dir / "comparison_metrics.json", "w", encoding="utf-8") as f:
        json.dump(comparison_results, f, indent=2)

    return comparison_results


if __name__ == "__main__":
    results = run_comparison_analysis()
    print("Forecasting comparison analysis completed successfully.")
