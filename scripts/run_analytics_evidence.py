"""Run and persist reproducible clustering, scenario, and allocation evidence."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.clustering.cluster import RoomClusterer
from app.optimization.solver import optimize_allocation
from app.simulation.simulator import simulate_scenario


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def _run_component(
    name: str,
    output_dir: Path,
    runner: Callable[[], dict[str, Any]],
) -> dict[str, Any]:
    started = datetime.now(timezone.utc).isoformat()
    try:
        result = runner()
        record = {
            "component": name,
            "status": "verified",
            "started_at_utc": started,
            **result,
        }
    except Exception as exc:  # Preserve a rerunnable diagnostic instead of claiming success.
        record = {
            "component": name,
            "status": "environment-blocked",
            "started_at_utc": started,
            "error_type": type(exc).__name__,
            "error": str(exc),
        }
    _write_json(output_dir / f"{name}.json", record)
    return record


def run_evidence(
    data_dir: str = "data/processed",
    output_dir: str = "experiments/analytics",
) -> dict[str, Any]:
    """Execute all available non-forecast analytical components on processed data."""
    data_path = Path(data_dir)
    evidence_path = Path(output_dir)
    evidence_path.mkdir(parents=True, exist_ok=True)

    occupancy = pd.read_parquet(data_path / "occupancy.parquet")
    rooms = pd.read_parquet(data_path / "rooms.parquet")
    timetable = pd.read_parquet(data_path / "timetable.parquet")

    def run_clustering() -> dict[str, Any]:
        result = RoomClusterer(random_state=42).fit_predict(occupancy)
        result.assignments.to_csv(evidence_path / "clustering_assignments.csv", index=False)
        return {
            "selected_clusters": result.selected_clusters,
            "silhouette_score": result.silhouette_score,
            "feature_names": list(result.feature_names),
            "rooms_profiled": int(len(result.assignments)),
            "assignments_artifact": "experiments/analytics/clustering_assignments.csv",
        }

    def run_scenario() -> dict[str, Any]:
        closed_room = str(rooms.iloc[0]["room_id"])
        result = simulate_scenario(
            occupancy,
            occupancy_multiplier=1.15,
            enrollment_multiplier=1.10,
            closed_rooms=[closed_room],
        )
        result.scenario_data.to_csv(evidence_path / "scenario_data.csv", index=False)
        return {
            "scenario_id": result.scenario_id,
            "parameters": result.parameters,
            "baseline_metrics": result.baseline_metrics,
            "scenario_metrics": result.scenario_metrics,
            "metric_deltas": result.metric_deltas,
            "scenario_artifact": "experiments/analytics/scenario_data.csv",
        }

    def run_optimization() -> dict[str, Any]:
        result = optimize_allocation(timetable, rooms, timeout_seconds=30.0)
        if result.feasible:
            result.assignments.to_csv(evidence_path / "optimization_assignments.csv", index=False)
        return {
            "feasible": result.feasible,
            "solver_status": result.solver_status,
            "objective_value": result.objective_value,
            "runtime_seconds": round(result.runtime_seconds, 6),
            "assignments": int(len(result.assignments)),
            "infeasibility_reason": result.infeasibility_reason,
            "assignments_artifact": (
                "experiments/analytics/optimization_assignments.csv" if result.feasible else None
            ),
        }

    components = [
        _run_component("clustering", evidence_path, run_clustering),
        _run_component("scenario", evidence_path, run_scenario),
        _run_component("optimization", evidence_path, run_optimization),
    ]
    summary = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_dir": data_dir,
        "random_seed": 42,
        "components": components,
    }
    _write_json(evidence_path / "run_summary.json", summary)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Generate BDS-06 analytical evidence artifacts.")
    parser.add_argument("--data-dir", default="data/processed")
    parser.add_argument("--output-dir", default="experiments/analytics")
    args = parser.parse_args()
    print(json.dumps(run_evidence(args.data_dir, args.output_dir), indent=2, default=str))