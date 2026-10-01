"""Data ingestion endpoints."""

from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from app.core.config import get_settings
from app.core.security import require_write
from app.data.ingestion import IngestionError, ingest_dataset

router = APIRouter()
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


@router.post("/ingest", summary="Ingest campus data")
async def ingest_data(
	dataset_name: str = Form(...),
	file: UploadFile = File(...),
	_: str = Depends(require_write),
):
	"""Validate and persist one source file without accepting path input."""
	settings = get_settings()
	safe_name = Path(file.filename or "").name
	if not safe_name or safe_name != file.filename or Path(safe_name).suffix.lower() not in {".csv", ".json", ".xlsx", ".xls"}:
		raise HTTPException(status_code=422, detail="Only CSV, JSON, and Excel source files are accepted")
	settings.raw_data_dir.mkdir(parents=True, exist_ok=True)
	payload = await file.read(MAX_UPLOAD_BYTES + 1)
	if len(payload) > MAX_UPLOAD_BYTES:
		raise HTTPException(status_code=413, detail="Uploaded file exceeds the 10 MB limit")
	destination = settings.raw_data_dir / safe_name
	temporary_path = None
	with NamedTemporaryFile(
		mode="wb",
		suffix=Path(safe_name).suffix.lower(),
		prefix=".upload-",
		dir=settings.raw_data_dir,
		delete=False,
	) as temporary:
		temporary.write(payload)
		temporary_path = Path(temporary.name)
	try:
		result = ingest_dataset(temporary_path, dataset_name)
	except IngestionError as exc:
		temporary_path.unlink(missing_ok=True)
		raise HTTPException(status_code=422, detail=str(exc)) from exc
	temporary_path.replace(destination)
	return {
		"status": "accepted",
		"dataset_name": result.dataset_name,
		"source_file": result.source_file,
		"rows": result.rows,
		"columns": result.columns,
		"ingested_at": result.ingested_at,
	}
