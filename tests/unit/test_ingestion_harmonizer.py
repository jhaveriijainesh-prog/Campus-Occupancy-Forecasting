"""Ingestion and timetable/event harmonization tests."""

from pathlib import Path

import pandas as pd
import pytest

from app.data.harmonizer import harmonize_sources
from app.data.ingestion import IngestionError, ingest_dataset


def _occupancy_file(path: Path) -> Path:
    frame = pd.DataFrame([
        {
            "observation_id": "OBS-1",
            "timestamp": "2026-08-03T09:15:00Z",
            "date": "2026-08-03",
            "hour": 9,
            "day_of_week": "Monday",
            "room_id": "b01-r101",
            "capacity": 100,
            "is_scheduled": False,
            "actual_headcount": 20,
        }
    ])
    frame.to_csv(path, index=False)
    return path


def test_ingestion_normalizes_room_ids_and_captures_provenance(tmp_path):
    result = ingest_dataset(_occupancy_file(tmp_path / "occupancy.csv"), "occupancy")

    assert result.rows == 1
    assert result.dataframe.loc[0, "room_id"] == "B01-R101"
    assert result.source_file.endswith("occupancy.csv")
    assert result.ingested_at


def test_ingestion_rejects_pii_columns(tmp_path):
    source = tmp_path / "rooms.csv"
    pd.DataFrame([{"room_id": "R1", "student_name": "private"}]).to_csv(source, index=False)

    with pytest.raises(IngestionError, match="PII"):
        ingest_dataset(source, "rooms")


def test_ingestion_rejects_missing_columns(tmp_path):
    source = tmp_path / "occupancy.csv"
    pd.DataFrame([{"room_id": "R1"}]).to_csv(source, index=False)

    with pytest.raises(IngestionError, match="missing required columns"):
        ingest_dataset(source, "occupancy")


def test_harmonizer_derives_schedule_and_event_context(tmp_path):
    occupancy = ingest_dataset(_occupancy_file(tmp_path / "occupancy.csv"), "occupancy").dataframe
    timetable = pd.DataFrame([
        {
            "timetable_id": "TT-1",
            "course_code": "DS101",
            "day_of_week": "Monday",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "room_id": "B01-R101",
            "enrolled_count": 80,
        }
    ])
    events = pd.DataFrame([{"date": "2026-08-03", "event_type": "exam", "impact_factor": 1.2}])

    result = harmonize_sources(occupancy, timetable, events)

    assert bool(result.loc[0, "is_scheduled"])
    assert result.loc[0, "scheduled_course_code"] == "DS101"
    assert result.loc[0, "scheduled_enrollment"] == 80
    assert result.loc[0, "campus_event_type"] == "exam"


def test_harmonizer_retains_unmatched_observations(tmp_path):
    occupancy = ingest_dataset(_occupancy_file(tmp_path / "occupancy.csv"), "occupancy").dataframe
    timetable = pd.DataFrame([
        {
            "room_id": "B01-R101",
            "day_of_week": "Monday",
            "start_time": "10:00:00",
            "end_time": "11:00:00",
            "course_code": "DS102",
            "enrolled_count": 40,
        }
    ])

    result = harmonize_sources(occupancy, timetable)

    assert len(result) == 1
    assert not bool(result.loc[0, "is_scheduled"])
    assert result.loc[0, "scheduled_enrollment"] == 0
