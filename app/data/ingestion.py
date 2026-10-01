"""Format-aware ingestion for the BDS-06 source datasets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from app.data.validation import CampusDataValidator


class IngestionError(ValueError):
	"""Raised when a source file cannot be safely admitted to the pipeline."""


@dataclass(frozen=True)
class IngestionResult:
	"""Dataframe plus provenance captured at the ingestion boundary."""

	dataset_name: str
	source_file: str
	ingested_at: str
	rows: int
	columns: tuple[str, ...]
	dataframe: pd.DataFrame


DATASET_COLUMNS: dict[str, set[str]] = {
	"rooms": set(CampusDataValidator.ROOM_REQUIRED_COLUMNS),
	"timetable": set(CampusDataValidator.TIMETABLE_REQUIRED_COLUMNS),
	"occupancy": set(CampusDataValidator.OCCUPANCY_REQUIRED_COLUMNS),
	"events": {"event_id", "date", "event_name", "event_type", "impact_factor", "affected_scope"},
}

PII_COLUMNS = {
	"email", "phone", "student_name", "student_id", "roll_number", "mac_address", "ip_address"
}


def _read_source(path: Path) -> pd.DataFrame:
	if path.suffix.lower() == ".csv":
		return pd.read_csv(path)
	if path.suffix.lower() == ".json":
		return pd.read_json(path)
	if path.suffix.lower() in {".xlsx", ".xls"}:
		return pd.read_excel(path)
	raise IngestionError(f"Unsupported source format: {path.suffix}")


def _normalize_types(dataset_name: str, frame: pd.DataFrame) -> pd.DataFrame:
	frame = frame.copy()
	string_columns = frame.select_dtypes(include=["object", "string"]).columns
	for column in string_columns:
		frame[column] = frame[column].map(lambda value: value.strip() if isinstance(value, str) else value)

	for column in {"room_id", "building_id", "course_code", "timetable_id", "observation_id", "event_id"}:
		if column in frame.columns:
			frame[column] = frame[column].astype("string").str.strip()
			if column == "room_id":
				frame[column] = frame[column].str.upper()

	if dataset_name == "occupancy" and "timestamp" in frame.columns:
		timestamps = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
		if timestamps.isna().any():
			bad_rows = timestamps[timestamps.isna()].index.tolist()
			raise IngestionError(f"occupancy contains invalid timestamps at rows {bad_rows[:10]}")
		frame["timestamp"] = timestamps
		frame["date"] = timestamps.dt.date.astype("string")
		frame["hour"] = timestamps.dt.hour.astype("int64")
		frame["day_of_week"] = timestamps.dt.day_name()

	if dataset_name == "events" and "date" in frame.columns:
		dates = pd.to_datetime(frame["date"], errors="coerce")
		if dates.isna().any():
			raise IngestionError("events contains invalid dates")
		frame["date"] = dates.dt.date.astype("string")
	return frame


def ingest_dataset(path: str | Path, dataset_name: str) -> IngestionResult:
	"""Read, normalize, and perform boundary checks for one source dataset."""
	if dataset_name not in DATASET_COLUMNS:
		raise IngestionError(f"Unsupported dataset name: {dataset_name}")
	source = Path(path)
	if not source.is_file():
		raise IngestionError(f"Source file does not exist: {source}")

	frame = _read_source(source)
	normalized_columns = {str(column).strip().lower() for column in frame.columns}
	pii_columns = normalized_columns.intersection(PII_COLUMNS)
	if pii_columns:
		raise IngestionError(f"PII columns are not accepted: {sorted(pii_columns)}")
	missing = DATASET_COLUMNS[dataset_name].difference(normalized_columns)
	if missing:
		raise IngestionError(f"{dataset_name} is missing required columns: {sorted(missing)}")

	frame.columns = [str(column).strip() for column in frame.columns]
	frame = _normalize_types(dataset_name, frame)
	return IngestionResult(
		dataset_name=dataset_name,
		source_file=str(source),
		ingested_at=datetime.now(timezone.utc).isoformat(),
		rows=len(frame),
		columns=tuple(str(column) for column in frame.columns),
		dataframe=frame,
	)
