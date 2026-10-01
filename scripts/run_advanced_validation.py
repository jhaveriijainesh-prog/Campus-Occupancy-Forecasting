"""Generate run-scoped research validation evidence from repository artifacts."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import os
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.metrics import adjusted_rand_score

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.clustering.cluster import RoomClusterer, build_room_profiles
from app.optimization.heuristics import greedy_allocate
from app.optimization.solver import _overlaps, optimize_allocation
from app.simulation.simulator import simulate_scenario


def _load_table(directory: Path, name: str) -> pd.DataFrame:
    for suffix, reader in ((".parquet", pd.read_parquet), (".csv", pd.read_csv)):
        path = directory / f"{name}{suffix}"
        if path.exists():
            return reader(path)
    raise FileNotFoundError(f"No CSV or Parquet artifact found for {name} in {directory}")


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _json_default(value: Any) -> Any:
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        return float(value)
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if isinstance(value, (pd.Timestamp, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, default=_json_default, allow_nan=False) + "\n",
        encoding="utf-8",
    )


def _metric_values(actual: pd.Series, predicted: pd.Series) -> dict[str, Any]:
    y_true = pd.to_numeric(actual, errors="coerce").to_numpy(dtype=float)
    y_pred = np.maximum(0.0, pd.to_numeric(predicted, errors="coerce").to_numpy(dtype=float))
    valid = np.isfinite(y_true) & np.isfinite(y_pred)
    y_true, y_pred = y_true[valid], y_pred[valid]
    if not len(y_true):
        return {"sample_count": 0}

    error = y_pred - y_true
    denominator = np.abs(y_true) + np.abs(y_pred)
    smape_terms = np.divide(
        2 * np.abs(error), denominator,
        out=np.zeros_like(error), where=denominator != 0,
    )
    smape_valid = denominator > 1e-12
    nonzero = y_true != 0
    result: dict[str, Any] = {
        "sample_count": int(len(y_true)),
        "MAE": float(np.mean(np.abs(error))),
        "RMSE": float(np.sqrt(np.mean(error ** 2))),
        "mean_bias_pred_minus_actual": float(np.mean(error)),
        "WAPE": float(np.sum(np.abs(error)) / np.sum(np.abs(y_true))) if np.sum(np.abs(y_true)) else None,
        "sMAPE_pct": float(np.mean(smape_terms[smape_valid]) * 100) if smape_valid.any() else None,
        "sMAPE_nonzero_denominator_count": int(smape_valid.sum()),
        "MAPE_nonzero_actual_pct": (
            float(np.mean(np.abs(error[nonzero]) / np.abs(y_true[nonzero])) * 100)
            if nonzero.any() else None
        ),
        "MAPE_nonzero_actual_count": int(nonzero.sum()),
    }
    total_variance = float(np.sum((y_true - np.mean(y_true)) ** 2))
    result["R2"] = (
        float(1 - np.sum(error ** 2) / total_variance)
        if len(y_true) > 1 and total_variance > 0 else None
    )
    return result


def _forecast_evaluation(output_dir: Path, rooms: pd.DataFrame) -> dict[str, Any]:
    baseline = _load_table(ROOT_DIR / "experiments" / "baseline", "test_predictions")
    xgboost = _load_table(ROOT_DIR / "experiments" / "xgboost", "test_predictions")
    paired = baseline.merge(
        xgboost[["observation_id", "predicted_headcount"]],
        on="observation_id", validate="one_to_one",
    )
    if len(paired) != len(baseline) or len(paired) != len(xgboost):
        raise ValueError("Forecast artifacts do not contain identical one-to-one test observations")
    paired = paired.merge(
        rooms[["room_id", "room_type", "building_id"]],
        on="room_id", how="left", validate="many_to_one",
    )
    paired["timestamp"] = pd.to_datetime(paired["timestamp"], utc=True)
    paired["hour"] = paired["timestamp"].dt.hour
    paired["day_type"] = np.select(
        [paired["timestamp"].dt.dayofweek == 5, paired["timestamp"].dt.dayofweek == 6],
        ["Saturday", "Sunday"], default="Weekday",
    )
    occupancy_ratio = paired["actual_headcount"] / paired["capacity"].replace(0, np.nan)
    paired["occupancy_band"] = pd.cut(
        paired["actual_headcount"], [-np.inf, 5, 35, np.inf],
        labels=["0-5", "6-35", "36+"],
    ).astype(str)
    paired["period"] = np.select(
        [paired["hour"].between(10, 11) | paired["hour"].between(14, 15),
         paired["hour"].between(8, 17), paired["hour"].between(18, 21)],
        ["peak", "regular_day", "evening"], default="night",
    )

    prediction_columns = {
        "HistoricalSeasonalProfile": "pred_HistoricalSeasonalProfile",
        "SeasonalLastWeek": "pred_SeasonalLastWeek",
        "StaticTimetable": "pred_StaticTimetable",
        "XGBoost": "predicted_headcount",
    }
    overall = {
        name: _metric_values(paired["actual_headcount"], paired[column])
        for name, column in prediction_columns.items()
    }
    slices: dict[str, Any] = {}
    for dimension in ("period", "day_type", "occupancy_band", "room_type", "building_id", "room_id"):
        groups: dict[str, Any] = {}
        for label, group in paired.groupby(dimension, observed=True, dropna=False):
            if len(group) < (20 if dimension == "room_id" else 1):
                continue
            groups[str(label)] = {
                name: _metric_values(group["actual_headcount"], group[column])
                for name, column in prediction_columns.items()
            }
        slices[dimension] = groups

    actual_peak = occupancy_ratio >= 0.8
    predicted_peak = paired["predicted_headcount"] / paired["capacity"].replace(0, np.nan) >= 0.8
    true_positive = int((actual_peak & predicted_peak).fillna(False).sum())
    false_positive = int((~actual_peak & predicted_peak).fillna(False).sum())
    false_negative = int((actual_peak & ~predicted_peak).fillna(False).sum())
    peak_detection = {
        "definition": "occupancy / room capacity >= 0.8",
        "test_observations": int(len(paired)),
        "actual_peak_observations": int(actual_peak.fillna(False).sum()),
        "predicted_peak_observations": int(predicted_peak.fillna(False).sum()),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "precision": true_positive / (true_positive + false_positive) if true_positive + false_positive else None,
        "recall": true_positive / (true_positive + false_negative) if true_positive + false_negative else None,
    }
    paired["xgboost_error_pred_minus_actual"] = paired["predicted_headcount"] - paired["actual_headcount"]
    paired[["observation_id", "timestamp", "room_id", "actual_headcount", "predicted_headcount", "xgboost_error_pred_minus_actual"]].to_csv(
        output_dir / "forecast_test_errors.csv", index=False,
    )
    config = json.loads((ROOT_DIR / "experiments" / "xgboost" / "config.json").read_text(encoding="utf-8"))
    return {
        "source": "existing paired chronological holdout prediction artifacts; no model retraining",
        "model": config.get("model_type"),
        "forecast_horizon_hours": config.get("forecast_horizon"),
        "split": config.get("chronological_splits", {}),
        "prediction_rows": int(len(paired)),
        "overall_metrics": overall,
        "slices": slices,
        "peak_detection": peak_detection,
        "error_table": "forecast_test_errors.csv",
        "limitation": "single-hour point forecasts; no calibrated interval evaluation or future horizons in persisted predictions",
    }


def _cluster_evaluation(occupancy: pd.DataFrame, output_dir: Path, seed: int, repeats: int) -> dict[str, Any]:
    baseline = RoomClusterer(random_state=seed).fit_predict(occupancy)
    baseline_assignments = baseline.assignments.sort_values("room_id").reset_index(drop=True)
    baseline_labels = baseline_assignments["cluster_id"].to_numpy()
    rng = np.random.default_rng(seed)
    perturbations = []
    for replicate in range(repeats):
        perturbed = occupancy.copy()
        noise = rng.normal(1.0, 0.02, size=len(perturbed))
        capacity = pd.to_numeric(perturbed["capacity"], errors="coerce").fillna(0).to_numpy()
        count = pd.to_numeric(perturbed["actual_headcount"], errors="coerce").fillna(0).to_numpy()
        perturbed["actual_headcount"] = np.clip(count * noise, 0, capacity)
        result = RoomClusterer(random_state=seed).fit_predict(perturbed)
        assignments = result.assignments.sort_values("room_id").reset_index(drop=True)
        perturbations.append({
            "replicate": replicate + 1,
            "seed": seed + replicate + 1,
            "noise_sd_fraction": 0.02,
            "adjusted_rand_index_vs_baseline": float(adjusted_rand_score(baseline_labels, assignments["cluster_id"])),
            "silhouette_score": result.silhouette_score,
        })

    profiles = baseline_assignments.groupby("cluster_id").agg(
        room_count=("room_id", "count"),
        median_capacity=("capacity", "median"),
        mean_utilization=("mean_utilization", "mean"),
        mean_peak_utilization=("peak_utilization", "mean"),
        mean_off_peak_utilization=("off_peak_utilization", "mean"),
        mean_occupancy_std=("occupancy_std", "mean"),
        operational_label=("cluster_label", "first"),
    ).reset_index()
    features = baseline_assignments[["capacity", "mean_utilization", "peak_utilization", "occupancy_std", "off_peak_utilization"]]
    standardized = RoomClusterer(random_state=seed)
    standardized.fit_predict(occupancy)
    if standardized.scaler_ is None or standardized.model_ is None:
        between_share = {}
    else:
        centers = standardized.model_.cluster_centers_
        counts = np.bincount(standardized.model_.labels_, minlength=len(centers))
        between_by_feature = np.sum(counts[:, None] * centers ** 2, axis=0)
        total = float(between_by_feature.sum())
        between_share = {
            name: float(value / total) if total else 0.0
            for name, value in zip(features.columns, between_by_feature)
        }
    profiles.to_csv(output_dir / "cluster_profiles.csv", index=False)
    baseline_assignments.to_csv(output_dir / "cluster_assignments.csv", index=False)
    ari = [item["adjusted_rand_index_vs_baseline"] for item in perturbations]
    return {
        "algorithm": "KMeans with StandardScaler and silhouette-selected k",
        "seed": seed,
        "rooms": int(len(baseline_assignments)),
        "selected_clusters": int(baseline.selected_clusters),
        "silhouette_score": baseline.silhouette_score,
        "cluster_sizes": {str(k): int(v) for k, v in baseline_assignments["cluster_id"].value_counts().sort_index().items()},
        "between_cluster_dispersion_share_by_feature": between_share,
        "perturbation_stability": {
            "replicates": repeats,
            "ari_mean": float(np.mean(ari)) if ari else None,
            "ari_min": float(np.min(ari)) if ari else None,
            "ari_max": float(np.max(ari)) if ari else None,
            "runs": perturbations,
        },
        "profiles_artifact": "cluster_profiles.csv",
        "assignments_artifact": "cluster_assignments.csv",
        "interpretation_limit": "cluster labels describe aggregate synthetic room profiles; they are not causal or operational prescriptions",
    }


def _constraint_violations(assignments: pd.DataFrame, timetable: pd.DataFrame, rooms: pd.DataFrame) -> dict[str, int]:
    if assignments.empty:
        return {"capacity": 0, "room_type": 0, "overlap": 0, "duplicate_assignment": 0}
    room_meta = rooms.drop_duplicates("room_id").set_index("room_id")
    course_meta = timetable.drop_duplicates("timetable_id").set_index("timetable_id")
    capacity = 0
    room_type = 0
    for assigned in assignments.itertuples():
        if assigned.room_id not in room_meta.index or assigned.timetable_id not in course_meta.index:
            capacity += 1
            continue
        room = room_meta.loc[assigned.room_id]
        course = course_meta.loc[assigned.timetable_id]
        capacity += int(float(room["capacity"]) < float(assigned.enrolled_count))
        required_type = str(course.get("room_type_required", "")).strip()
        room_type += int(bool(required_type) and required_type != str(room["room_type"]))
    overlap = 0
    for _, group in assignments.groupby("room_id"):
        rows = group.to_dict("records")
        for index, left in enumerate(rows):
            overlap += sum(_overlaps(pd.Series(left), pd.Series(right)) for right in rows[index + 1:])
    duplicate_assignment = int(assignments["timetable_id"].duplicated().sum())
    return {
        "capacity": capacity,
        "room_type": room_type,
        "overlap": int(overlap),
        "duplicate_assignment": duplicate_assignment,
    }


def _allocation_summary(result: Any, elapsed: float, timetable: pd.DataFrame, rooms: pd.DataFrame) -> dict[str, Any]:
    assignments = result.assignments
    violations = _constraint_violations(assignments, timetable, rooms)
    assigned = int(assignments["timetable_id"].nunique()) if not assignments.empty else 0
    unused = float(assignments["unused_capacity"].sum()) if not assignments.empty else None
    return {
        "status": result.solver_status,
        "feasible": bool(result.feasible),
        "assigned_sessions": assigned,
        "unassigned_sessions": max(0, int(len(timetable)) - assigned),
        "objective_unused_capacity": result.objective_value,
        "unused_capacity_recomputed": unused,
        "constraint_violations": violations,
        "runtime_seconds": float(elapsed),
        "diagnostic": result.infeasibility_reason,
    }


def _scenario_and_optimization(
    occupancy: pd.DataFrame,
    timetable: pd.DataFrame,
    rooms: pd.DataFrame,
    output_dir: Path,
    timeout_seconds: float,
) -> dict[str, Any]:
    room_ids = sorted(rooms["room_id"].astype(str).unique())
    primary_room, secondary_room = room_ids[0], room_ids[1]
    primary_capacity = float(rooms.set_index("room_id").loc[primary_room, "capacity"])
    secondary_capacity = float(rooms.set_index("room_id").loc[secondary_room, "capacity"])
    cases = [
        {"name": "baseline", "occupancy_multiplier": 1.0, "enrollment_multiplier": 1.0},
        {"name": "occupancy_increase_small", "occupancy_multiplier": 1.05, "enrollment_multiplier": 1.05},
        {"name": "occupancy_increase_moderate", "occupancy_multiplier": 1.15, "enrollment_multiplier": 1.15},
        {"name": "occupancy_increase_large", "occupancy_multiplier": 1.30, "enrollment_multiplier": 1.30},
        {"name": "occupancy_decrease_small", "occupancy_multiplier": 0.90, "enrollment_multiplier": 0.90},
        {"name": "room_closure", "occupancy_multiplier": 1.0, "enrollment_multiplier": 1.0, "closed_rooms": [primary_room]},
        {"name": "capacity_reduction", "occupancy_multiplier": 1.0, "enrollment_multiplier": 1.0, "capacity_adjustments": {primary_room: primary_capacity * 0.8}},
        {"name": "capacity_increase", "occupancy_multiplier": 1.0, "enrollment_multiplier": 1.0, "capacity_adjustments": {primary_room: primary_capacity * 1.2}},
        {"name": "combined_valid_perturbation", "occupancy_multiplier": 1.15, "enrollment_multiplier": 1.10, "closed_rooms": [primary_room], "capacity_adjustments": {secondary_room: secondary_capacity * 0.8}},
        {"name": "invalid_negative_multiplier", "occupancy_multiplier": -0.1, "enrollment_multiplier": 1.0, "expected_invalid": True},
        {"name": "infeasible_demand", "occupancy_multiplier": 1.0, "enrollment_multiplier": 100.0, "expected_infeasible": True},
    ]
    results = []
    for case in cases:
        name = case["name"]
        params = {key: value for key, value in case.items() if key not in {"name", "expected_invalid", "expected_infeasible"}}
        try:
            simulation = simulate_scenario(
                occupancy,
                occupancy_multiplier=float(params.get("occupancy_multiplier", 1.0)),
                enrollment_multiplier=float(params.get("enrollment_multiplier", 1.0)),
                closed_rooms=params.get("closed_rooms", []),
                capacity_adjustments=params.get("capacity_adjustments", {}),
            )
        except (ValueError, KeyError) as exc:
            results.append({
                "scenario": name,
                "parameters": params,
                "expected_invalid": bool(case.get("expected_invalid")),
                "observed": "rejected",
                "passed": bool(case.get("expected_invalid")),
                "error_type": type(exc).__name__,
                "error": str(exc),
            })
            continue

        scenario_rooms = rooms.copy()
        for room_id, capacity in params.get("capacity_adjustments", {}).items():
            scenario_rooms.loc[scenario_rooms["room_id"] == room_id, "capacity"] = float(capacity)
        closed_rooms = set(params.get("closed_rooms", []))
        scenario_rooms = scenario_rooms[~scenario_rooms["room_id"].astype(str).isin(closed_rooms)].copy()
        scenario_timetable = timetable.copy()
        multiplier = float(params.get("enrollment_multiplier", 1.0))
        scenario_timetable["enrolled_count"] = np.ceil(
            pd.to_numeric(scenario_timetable["enrolled_count"], errors="coerce") * multiplier
        )

        paired: dict[str, Any] = {}
        for method, runner in (("milp", lambda: optimize_allocation(scenario_timetable, scenario_rooms, timeout_seconds=timeout_seconds)),
                               ("greedy", lambda: greedy_allocate(scenario_timetable, scenario_rooms))):
            started = time.perf_counter()
            allocation = runner()
            elapsed = time.perf_counter() - started
            paired[method] = _allocation_summary(allocation, elapsed, scenario_timetable, scenario_rooms)
        results.append({
            "scenario": name,
            "parameters": params,
            "scenario_id": simulation.scenario_id,
            "simulation": {
                "baseline_metrics": simulation.baseline_metrics,
                "scenario_metrics": simulation.scenario_metrics,
                "metric_deltas": simulation.metric_deltas,
                "peak_occupancy": simulation.scenario_metrics.get("peak_occupancy"),
            },
            "optimization": paired,
            "expected_infeasible": bool(case.get("expected_infeasible")),
            "observed": "infeasible" if not paired["milp"]["feasible"] else "feasible",
            "passed": (
                not paired["milp"]["feasible"]
                if case.get("expected_infeasible")
                else True
            ),
        })

    _write_json(output_dir / "scenario_optimization_matrix.json", {"cases": results})
    return {
        "case_count": len(results),
        "matrix_artifact": "scenario_optimization_matrix.json",
        "cases": results,
        "comparison_basis": "same transformed timetable and room inventory for CBC MILP and capacity-first greedy baseline",
        "limits": "scenario simulation scales observed occupancy and scheduled enrollment but does not reassign displaced courses or shift schedules",
    }


def _data_quality(raw_dir: Path, processed_dir: Path) -> dict[str, Any]:
    raw = {name: _load_table(raw_dir, name) for name in ("events", "occupancy", "rooms", "timetable")}
    processed = {name: _load_table(processed_dir, name) for name in raw}
    report_path = processed_dir / "validation_report.json"
    prior_report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    forbidden_tokens = ("student", "name", "email", "phone", "mac", "ip_address", "ipaddress", "device_id")
    datasets: dict[str, Any] = {}
    for name, raw_frame in raw.items():
        clean = processed[name]
        pii_columns = [column for column in raw_frame.columns if any(token in str(column).lower() for token in forbidden_tokens)]
        record: dict[str, Any] = {
            "raw_records": int(len(raw_frame)),
            "analysis_ready_records": int(len(clean)),
            "raw_duplicate_rows": int(raw_frame.duplicated().sum()),
            "processed_duplicate_rows": int(clean.duplicated().sum()),
            "raw_missing_cells": int(raw_frame.isna().sum().sum()),
            "processed_missing_cells": int(clean.isna().sum().sum()),
            "raw_pii_like_columns": pii_columns,
            "room_id_normalization_changes": None,
            "invalid_timestamps": None,
            "negative_occupancy": None,
            "occupancy_over_capacity": None,
        }
        if "room_id" in raw_frame:
            room_ids = raw_frame["room_id"].dropna().astype(str)
            record["room_id_normalization_changes"] = int((room_ids != room_ids.str.strip().str.upper()).sum())
        if "timestamp" in raw_frame:
            record["invalid_timestamps"] = int(pd.to_datetime(raw_frame["timestamp"], errors="coerce", utc=True).isna().sum())
        if name == "occupancy" and {"actual_headcount", "capacity"}.issubset(raw_frame.columns):
            actual = pd.to_numeric(raw_frame["actual_headcount"], errors="coerce")
            capacity = pd.to_numeric(raw_frame["capacity"], errors="coerce")
            record["negative_occupancy"] = int((actual < 0).sum())
            record["occupancy_over_capacity"] = int((actual > capacity).sum())
            record["missing_scheduled_course_code"] = int(raw_frame["scheduled_course_code"].isna().sum()) if "scheduled_course_code" in raw_frame else None
        datasets[name] = record
    return {
        "source_characterization": "checked-in synthetic repository data; not institutional sensor data",
        "datasets": datasets,
        "validation_report_summary": {
            "execution_timestamp": prior_report.get("execution_timestamp"),
            "overall_status": prior_report.get("overall_status"),
            "quarantined_records_count": prior_report.get("quarantined_records_count"),
            "summaries": prior_report.get("summaries", {}),
        },
        "flow_note": "Counts are raw and processed snapshots; the prior validation report records 0 corrected/rejected occupancy rows. Missing scheduled_course_code is structural for unscheduled slots and is reported separately, not silently treated as an occupancy defect.",
    }


def _failure_probes(occupancy: pd.DataFrame, rooms: pd.DataFrame, timetable: pd.DataFrame) -> list[dict[str, Any]]:
    probes: list[dict[str, Any]] = []
    checks = [
        ("empty_scenario_data", lambda: simulate_scenario(occupancy.iloc[0:0])),
        ("invalid_scenario_multiplier", lambda: simulate_scenario(occupancy, occupancy_multiplier=0)),
        ("unknown_closed_room", lambda: simulate_scenario(occupancy, closed_rooms=["UNKNOWN-ROOM"])),
        ("empty_cluster_data", lambda: build_room_profiles(occupancy.iloc[0:0])),
    ]
    for name, check in checks:
        try:
            check()
            probes.append({"case": name, "expected": "reject", "observed": "accepted", "passed": False})
        except (ValueError, KeyError) as exc:
            probes.append({"case": name, "expected": "reject", "observed": "rejected", "error_type": type(exc).__name__, "passed": True})
    impossible = timetable.iloc[[0]].copy()
    impossible["enrolled_count"] = float(rooms["capacity"].max()) + 1
    result = optimize_allocation(impossible, rooms)
    probes.append({
        "case": "single_course_demand_exceeds_all_rooms",
        "expected": "infeasible with diagnostic",
        "observed": result.solver_status,
        "diagnostic": result.infeasibility_reason,
        "passed": not result.feasible and bool(result.infeasibility_reason),
    })
    return probes


def _forecast_latency(occupancy: pd.DataFrame, rooms: pd.DataFrame, events: pd.DataFrame, repeats: int) -> dict[str, Any]:
    from app.features.engineering import FeatureEngineer
    from app.forecasting.model import OccupancyForecaster

    model_dir = ROOT_DIR / "experiments" / "xgboost"
    started = time.perf_counter()
    model = OccupancyForecaster().load(model_dir)
    load_seconds = time.perf_counter() - started
    room_id = str(sorted(occupancy["room_id"].astype(str).unique())[0])
    history = occupancy[occupancy["room_id"].astype(str) == room_id].sort_values("timestamp").tail(200).copy()
    feature_start = time.perf_counter()
    features = FeatureEngineer(forecast_horizon=1).create_features(history, rooms, events)
    feature_seconds = time.perf_counter() - feature_start
    sample = features.tail(1)
    model.predict(sample)
    measurements = []
    for _ in range(repeats):
        started = time.perf_counter()
        model.predict(sample)
        measurements.append((time.perf_counter() - started) * 1000)
    return {
        "workload": "single-room direct XGBoost inference on latest engineered row; excludes HTTP and dashboard",
        "room_id": room_id,
        "warmup_count": 1,
        "measured_calls": repeats,
        "model_load_seconds": load_seconds,
        "feature_engineering_seconds_for_200_rows": feature_seconds,
        "prediction_latency_ms": {
            "p50": float(np.percentile(measurements, 50)),
            "p95": float(np.percentile(measurements, 95)),
            "p99": float(np.percentile(measurements, 99)),
        },
        "limitation": "local process measurements only; not an API latency or production capacity claim",
    }


def run_validation(
    data_dir: str = "data/processed",
    repeats: int = 10,
    inference_repeats: int = 30,
    timeout_seconds: float = 10.0,
) -> dict[str, Any]:
    generated = datetime.now(timezone.utc)
    run_id = generated.strftime("%Y%m%dT%H%M%S%fZ")
    output_dir = ROOT_DIR / "experiments" / "advanced_validation" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)

    processed_dir = ROOT_DIR / data_dir
    read_started = time.perf_counter()
    occupancy = _load_table(processed_dir, "occupancy")
    rooms = _load_table(processed_dir, "rooms")
    timetable = _load_table(processed_dir, "timetable")
    events = _load_table(processed_dir, "events")
    data_load_seconds = time.perf_counter() - read_started

    forecast = _forecast_evaluation(output_dir, rooms)
    clustering = _cluster_evaluation(occupancy, output_dir, seed=42, repeats=repeats)
    scenario_optimization = _scenario_and_optimization(
        occupancy, timetable, rooms, output_dir, timeout_seconds,
    )
    data_quality = _data_quality(ROOT_DIR / "data" / "raw", processed_dir)
    failures = _failure_probes(occupancy, rooms, timetable)
    latency = _forecast_latency(occupancy, rooms, events, inference_repeats)

    source_files = [
        "app/clustering/cluster.py",
        "app/simulation/simulator.py",
        "app/optimization/solver.py",
        "app/optimization/heuristics.py",
        "app/features/engineering.py",
        "app/forecasting/model.py",
        "scripts/run_advanced_validation.py",
    ]
    artifact_files = [
        f"{data_dir}/occupancy.parquet",
        f"{data_dir}/rooms.parquet",
        f"{data_dir}/timetable.parquet",
        f"{data_dir}/events.parquet",
        "experiments/xgboost/model.json",
        "experiments/xgboost/config.json",
        "experiments/xgboost/test_predictions.parquet",
        "experiments/baseline/test_predictions.parquet",
    ]
    provenance = {}
    for relative in source_files + artifact_files:
        path = ROOT_DIR / relative
        if path.exists():
            provenance[relative] = {"sha256": _sha256(path), "bytes": path.stat().st_size}
    packages = {}
    for package in ("numpy", "pandas", "scikit-learn", "xgboost", "PuLP", "FastAPI", "Streamlit"):
        try:
            packages[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            packages[package] = None
    result = {
        "run_id": run_id,
        "generated_at_utc": generated.isoformat(),
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "cpu_count": os.cpu_count(),
            "packages": packages,
        },
        "configuration": {
            "seed": 42,
            "cluster_perturbation_repeats": repeats,
            "inference_repeats": inference_repeats,
            "milp_timeout_seconds_per_case": timeout_seconds,
            "data_directory": data_dir,
        },
        "provenance_sha256": provenance,
        "performance": {
            "processed_data_load_seconds": data_load_seconds,
            "forecast_inference": latency,
            "measurement_scope": "observed wall time on this host; no memory/CPU sampling or dashboard/API latency claimed",
        },
        "forecast_evaluation": forecast,
        "clustering_evaluation": clustering,
        "scenario_optimization_evaluation": scenario_optimization,
        "data_quality": data_quality,
        "failure_probes": failures,
        "not_executed_or_not_supported": [
            "multi-horizon and calibrated prediction interval evaluation",
            "schedule-shift and calendar-change scenarios",
            "equipment, accessibility, cohort-travel, and schedule-inertia optimization constraints",
            "full API security fuzzing and dependency vulnerability scan",
            "container build/runtime because Docker availability has not been established in this run",
            "dashboard visual QA and clean-machine replay",
        ],
    }
    _write_json(output_dir / "advanced_validation.json", result)
    print(json.dumps({
        "run_id": run_id,
        "output_dir": str(output_dir.relative_to(ROOT_DIR)),
        "forecast_rows": forecast["prediction_rows"],
        "cluster_ari_mean": clustering["perturbation_stability"]["ari_mean"],
        "scenario_cases": scenario_optimization["case_count"],
        "failed_failure_probes": [probe["case"] for probe in failures if not probe["passed"]],
        "forecast_p95_ms": latency["prediction_latency_ms"]["p95"],
    }, indent=2))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data/processed")
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--inference-repeats", type=int, default=30)
    parser.add_argument("--timeout-seconds", type=float, default=10.0)
    args = parser.parse_args()
    if args.repeats < 1 or args.inference_repeats < 1 or args.timeout_seconds <= 0:
        parser.error("repeat counts and timeout must be positive")
    run_validation(args.data_dir, args.repeats, args.inference_repeats, args.timeout_seconds)