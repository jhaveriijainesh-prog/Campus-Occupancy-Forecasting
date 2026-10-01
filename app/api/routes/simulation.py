"""What-if scenario simulation endpoint."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from app.core.config import get_settings
from app.core.security import require_read
from app.simulation.simulator import simulate_scenario


router = APIRouter()


class ScenarioRequest(BaseModel):
    """Validated scenario perturbation parameters."""

    occupancy_multiplier: float = Field(default=1.0, gt=0, le=5)
    enrollment_multiplier: float = Field(default=1.0, gt=0, le=5)
    closed_rooms: list[str] = Field(default_factory=list)
    capacity_adjustments: dict[str, float] = Field(default_factory=dict)


def _load_occupancy() -> pd.DataFrame:
    settings = get_settings()
    parquet_path = settings.processed_data_dir / "occupancy.parquet"
    csv_path = settings.processed_data_dir / "occupancy.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise HTTPException(status_code=503, detail="Processed occupancy data is unavailable")


@router.post("/run", summary="Run an occupancy what-if scenario")
async def run_scenario(request: ScenarioRequest, _: str = Depends(require_read)):
    """Run a reproducible scenario and return aggregate outcome differences."""
    try:
        result = simulate_scenario(
            _load_occupancy(),
            occupancy_multiplier=request.occupancy_multiplier,
            enrollment_multiplier=request.enrollment_multiplier,
            closed_rooms=request.closed_rooms,
            capacity_adjustments=request.capacity_adjustments,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "scenario_id": result.scenario_id,
        "parameters": result.parameters,
        "baseline_metrics": result.baseline_metrics,
        "scenario_metrics": result.scenario_metrics,
        "metric_deltas": result.metric_deltas,
    }
