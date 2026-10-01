"""
Unit Tests for Data Cleaning & Quarantine Pipeline (app/data/cleaning.py).
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project
"""

import pandas as pd
import pytest

from app.data.cleaning import CampusDataCleaner


@pytest.fixture
def cleaner(tmp_path):
    return CampusDataCleaner(processed_dir=str(tmp_path))


@pytest.fixture
def rooms_master():
    return pd.DataFrame([
        {
            "room_id": "B01-R101",
            "building_id": "B01",
            "building_name": "Alan Turing Block",
            "floor": 1,
            "room_type": "Lecture Hall",
            "capacity": 80,
            "has_projector": True,
            "has_ac": True,
            "has_computers": False,
            "is_accessible": True,
        }
    ])


def test_clean_occupancy_clamps_negative_values(cleaner, rooms_master):
    dirty = pd.DataFrame([
        {
            "observation_id": "OBS-001",
            "timestamp": "2026-08-03T09:00:00Z",
            "date": "2026-08-03",
            "hour": 9,
            "day_of_week": "Monday",
            "room_id": "B01-R101",
            "capacity": 80,
            "is_scheduled": True,
            "actual_headcount": -15,  # Impossible negative
        }
    ])

    cleaned, summary = cleaner.clean_occupancy(dirty, rooms_master)
    assert cleaned.loc[0, "actual_headcount"] == 0
    assert bool(cleaned.loc[0, "was_clamped"]) is True
    assert summary.negative_clamped == 1
    assert summary.records_corrected == 1


def test_clean_occupancy_clamps_capacity_overflow(cleaner, rooms_master):
    dirty = pd.DataFrame([
        {
            "observation_id": "OBS-001",
            "timestamp": "2026-08-03T09:00:00Z",
            "date": "2026-08-03",
            "hour": 9,
            "day_of_week": "Monday",
            "room_id": "B01-R101",
            "capacity": 80,
            "is_scheduled": True,
            "actual_headcount": 120,  # Exceeds capacity of 80
        }
    ])

    cleaned, summary = cleaner.clean_occupancy(dirty, rooms_master)
    assert cleaned.loc[0, "actual_headcount"] == 80  # Clamped to true capacity
    assert bool(cleaned.loc[0, "was_clamped"]) is True
    assert summary.capacity_clamped == 1


def test_clean_occupancy_reconciles_inconsistent_timestamps(cleaner, rooms_master):
    dirty = pd.DataFrame([
        {
            "observation_id": "OBS-001",
            "timestamp": "2026-08-03T14:00:00Z",  # True hour is 14
            "date": "2026-08-03",
            "hour": 9,                            # Inconsistent hour 9
            "day_of_week": "Sunday",              # Inconsistent DOW
            "room_id": "B01-R101",
            "capacity": 80,
            "is_scheduled": True,
            "actual_headcount": 50,
        }
    ])

    cleaned, summary = cleaner.clean_occupancy(dirty, rooms_master)
    assert cleaned.loc[0, "hour"] == 14
    assert cleaned.loc[0, "day_of_week"] == "Monday"
    assert summary.timestamps_reconciled == 1


def test_clean_occupancy_quarantines_invalid_rooms(cleaner, rooms_master):
    # Room does not exist in master rooms
    dirty = pd.DataFrame([
        {
            "observation_id": "OBS-999",
            "timestamp": "2026-08-03T10:00:00Z",
            "date": "2026-08-03",
            "hour": 10,
            "day_of_week": "Monday",
            "room_id": "B99-GHOST-ROOM",
            "capacity": 80,
            "is_scheduled": False,
            "actual_headcount": 10,
        }
    ])

    cleaned, summary = cleaner.clean_occupancy(dirty, rooms_master)
    # Record must NOT be silently deleted, it must be quarantined
    assert len(cleaned) == 0
    assert summary.records_rejected == 1
    assert len(cleaner.quarantined_records) == 1
    assert cleaner.quarantined_records[0]["record_id"] == "OBS-999"


def test_clean_occupancy_deduplication(cleaner, rooms_master):
    row = {
        "observation_id": "OBS-001",
        "timestamp": "2026-08-03T10:00:00Z",
        "date": "2026-08-03",
        "hour": 10,
        "day_of_week": "Monday",
        "room_id": "B01-R101",
        "capacity": 80,
        "is_scheduled": True,
        "actual_headcount": 45,
    }
    dup_row = dict(row, observation_id="OBS-002", actual_headcount=45)
    dirty = pd.DataFrame([row, dup_row])

    cleaned, summary = cleaner.clean_occupancy(dirty, rooms_master)
    assert len(cleaned) == 1
    assert summary.duplicates_removed == 1
