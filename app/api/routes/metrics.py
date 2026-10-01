"""Utilization Metrics and Clustering Endpoints."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException, Query

from app.analytics.metrics import TIME_OF_DAY_WINDOWS, add_building_id, calculate_utilization_metrics, filter_occupancy
from app.core.config import get_settings
from app.core.security import require_read
from app.schemas.metrics import UtilizationResponse

router = APIRouter()

def _load_occupancy() -> pd.DataFrame:
	settings = get_settings()
	parquet_path = settings.processed_data_dir / "occupancy.parquet"
	csv_path = settings.processed_data_dir / "occupancy.csv"
	try:
		if parquet_path.exists():
			return pd.read_parquet(parquet_path)
		if csv_path.exists():
			return pd.read_csv(csv_path)
	except (OSError, ValueError, pd.errors.ParserError) as exc:
		raise HTTPException(status_code=503, detail=f"Unable to load occupancy data: {exc}") from exc
	raise HTTPException(status_code=503, detail="Processed occupancy data is unavailable")

@router.get("/utilization", response_model=UtilizationResponse, summary="Get occupancy utilization metrics")
async def utilization_metrics(
	scope: str = Query(default="campus"),
	room_id: str | None = Query(default=None),
	building_id: str | None = Query(default=None),
	start_time: str | None = Query(default=None),
	end_time: str | None = Query(default=None),
	day_of_week: str | None = Query(default=None),
	time_of_day: str | None = Query(default=None),
	_: str = Depends(require_read),
):
	"""Return aggregated SUR, RFU, WSH, peak occupancy, and source metadata."""
	occupancy = _load_occupancy()
	with_buildings = add_building_id(occupancy)
	if scope == "campus" and (room_id or building_id):
		raise HTTPException(status_code=422, detail="campus scope cannot include room_id or building_id")
	if scope == "building" and room_id:
		raise HTTPException(status_code=422, detail="building scope cannot include room_id")
	if scope == "room" and building_id:
		raise HTTPException(status_code=422, detail="room scope cannot include building_id")
	if room_id and room_id not in with_buildings["room_id"].astype(str).values:
		raise HTTPException(status_code=404, detail=f"Unknown room_id: {room_id}")
	if building_id and building_id not in with_buildings["building_id"].astype(str).values:
		raise HTTPException(status_code=404, detail=f"Unknown building_id: {building_id}")
	try:
		filtered = filter_occupancy(
			occupancy,
			scope=scope,
			room_id=room_id,
			building_id=building_id,
			start_time=start_time,
			end_time=end_time,
			day_of_week=day_of_week,
			time_of_day=time_of_day,
		)
	except ValueError as exc:
		raise HTTPException(status_code=422, detail=str(exc)) from exc

	if "timestamp" not in occupancy.columns:
		raise HTTPException(status_code=503, detail="Occupancy data has no source timestamp column")

	metrics = calculate_utilization_metrics(
		filtered,
		operating_hours_start=get_settings().operational_hours_start,
		operating_hours_end=get_settings().operational_hours_end,
		available_slot_hours=(
			pd.to_datetime(filtered["timestamp"], utc=True, errors="coerce").dt.date.nunique()
			* filtered["room_id"].nunique()
			* (
				TIME_OF_DAY_WINDOWS[time_of_day.casefold()][1] - TIME_OF_DAY_WINDOWS[time_of_day.casefold()][0]
				if time_of_day and time_of_day.casefold() in TIME_OF_DAY_WINDOWS
				else get_settings().operational_hours_end - get_settings().operational_hours_start
			)
			if not filtered.empty
			else 0
		),
	)
	source_timestamp = None
	if not filtered.empty:
		source_timestamps = pd.to_datetime(filtered["timestamp"], utc=True, errors="coerce")
		if source_timestamps.isna().all():
			raise HTTPException(status_code=503, detail="Occupancy data has no valid source timestamp")
		source_timestamp = source_timestamps.max().isoformat()

	return {
		"scope": scope,
		"room_id": room_id,
		"building_id": building_id,
		"metrics": metrics,
		"time_window": {"start": start_time, "end": end_time},
		"source_timestamp": source_timestamp,
	}
