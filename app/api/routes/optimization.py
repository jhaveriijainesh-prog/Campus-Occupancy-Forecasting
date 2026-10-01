"""Capacity optimization and baseline comparison endpoints."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.core.config import get_settings
from app.core.security import require_optimize
from app.optimization.heuristics import greedy_allocate
from app.optimization.solver import optimize_allocation


router = APIRouter()


def _load_processed(name: str) -> pd.DataFrame:
	settings = get_settings()
	parquet_path = settings.processed_data_dir / f"{name}.parquet"
	csv_path = settings.processed_data_dir / f"{name}.csv"
	if parquet_path.exists():
		return pd.read_parquet(parquet_path)
	if csv_path.exists():
		return pd.read_csv(csv_path)
	raise HTTPException(status_code=503, detail=f"Processed {name} data is unavailable")


@router.post("/compare", summary="Compare heuristic and MILP room allocation")
async def compare_allocations(_: str = Depends(require_optimize)):
	"""Run both allocation strategies on the processed timetable and room master."""
	try:
		timetable = _load_processed("timetable")
		rooms = _load_processed("rooms")
		heuristic = greedy_allocate(timetable, rooms)
		milp = optimize_allocation(timetable, rooms)
	except ValueError as exc:
		raise HTTPException(status_code=422, detail=str(exc)) from exc
	return {
		"baseline": {
			"method": "capacity_first_greedy",
			"feasible": heuristic.feasible,
			"objective_unused_capacity": heuristic.objective_value,
			"solver_status": heuristic.solver_status,
			"infeasibility_reason": heuristic.infeasibility_reason,
			"assignments": heuristic.assignments.to_dict(orient="records"),
		},
		"milp": {
			"method": "pulp_cbc_constraint_aware",
			"feasible": milp.feasible,
			"objective_unused_capacity": milp.objective_value,
			"runtime_seconds": milp.runtime_seconds,
			"solver_status": milp.solver_status,
			"infeasibility_reason": milp.infeasibility_reason,
			"assignments": milp.assignments.to_dict(orient="records"),
		},
	}
