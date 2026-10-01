"""Room behavioral clustering endpoint."""

import pandas as pd
from fastapi import APIRouter, Depends, HTTPException

from app.clustering.cluster import RoomClusterer
from app.core.config import get_settings
from app.core.security import require_read


router = APIRouter()


def _load_occupancy() -> pd.DataFrame:
    settings = get_settings()
    parquet_path = settings.processed_data_dir / "occupancy.parquet"
    csv_path = settings.processed_data_dir / "occupancy.csv"
    if parquet_path.exists():
        return pd.read_parquet(parquet_path)
    if csv_path.exists():
        return pd.read_csv(csv_path)
    raise HTTPException(status_code=503, detail="Processed occupancy data is unavailable")


@router.get("/rooms", summary="Cluster rooms by occupancy behavior")
async def cluster_rooms(_: str = Depends(require_read)):
    """Return reproducible room profiles, archetypes, and PCA coordinates."""
    try:
        result = RoomClusterer().fit_predict(_load_occupancy())
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {
        "selected_clusters": result.selected_clusters,
        "silhouette_score": result.silhouette_score,
        "feature_names": result.feature_names,
        "rooms": result.assignments.to_dict(orient="records"),
    }
