"""
Unit Tests for Campus Data Validation Pipeline (app/data/validation.py).
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project
"""

import pandas as pd
import pytest

from app.data.validation import CampusDataValidator


@pytest.fixture
def validator():
    return CampusDataValidator()


@pytest.fixture
def sample_rooms_df():
    return pd.DataFrame([
        {
            "room_id": "B01-R101",
            "building_id": "B01",
            "building_name": "Alan Turing Block",
            "floor": 1,
            "room_type": "Lecture Hall",
            "capacity": 100,
            "has_projector": True,
            "has_ac": True,
            "has_computers": False,
            "is_accessible": True,
        },
        {
            "room_id": "B01-L102",
            "building_id": "B01",
            "building_name": "Alan Turing Block",
            "floor": 1,
            "room_type": "Computer Lab",
            "capacity": 40,
            "has_projector": True,
            "has_ac": True,
            "has_computers": True,
            "is_accessible": True,
        }
    ])


@pytest.fixture
def sample_timetable_df():
    return pd.DataFrame([
        {
            "timetable_id": "TT-001",
            "course_code": "DS101",
            "course_name": "Intro to Data Science",
            "instructor_id": "INST_01",
            "enrolled_count": 80,
            "day_of_week": "Monday",
            "start_time": "09:00:00",
            "end_time": "10:00:00",
            "room_id": "B01-R101",
            "room_type_required": "Lecture Hall",
        }
    ])


@pytest.fixture
def sample_occupancy_df():
    return pd.DataFrame([
        {
            "observation_id": "OBS-001",
            "timestamp": "2026-08-03T09:00:00Z",
            "date": "2026-08-03",
            "hour": 9,
            "day_of_week": "Monday",
            "room_id": "B01-R101",
            "capacity": 100,
            "is_scheduled": True,
            "actual_headcount": 75,
        }
    ])


# -------------------------------------------------------------------------
# Test Cases for Room Validation
# -------------------------------------------------------------------------

def test_validate_rooms_success(validator, sample_rooms_df):
    report = validator.validate_rooms(sample_rooms_df)
    assert report.is_valid is True
    assert report.total_records == 2
    assert report.valid_records == 2
    assert len(report.errors) == 0


def test_validate_rooms_missing_required_column(validator, sample_rooms_df):
    dirty = sample_rooms_df.drop(columns=["capacity"])
    report = validator.validate_rooms(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "MISSING_COLUMN" for e in report.errors)


def test_validate_rooms_duplicate_room_id(validator, sample_rooms_df):
    dirty = pd.concat([sample_rooms_df, sample_rooms_df.iloc[[0]]], ignore_index=True)
    report = validator.validate_rooms(dirty)
    assert report.is_valid is False
    assert report.duplicate_records == 1
    assert any(e.error_type == "DUPLICATE_ROOM_ID" for e in report.errors)


def test_validate_rooms_invalid_capacity(validator, sample_rooms_df):
    dirty = sample_rooms_df.copy()
    dirty.loc[0, "capacity"] = -50  # Negative capacity
    report = validator.validate_rooms(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "INVALID_CAPACITY" for e in report.errors)


def test_validate_rooms_invalid_type(validator, sample_rooms_df):
    dirty = sample_rooms_df.copy()
    dirty.loc[0, "room_type"] = "Swimming Pool"  # Unknown room type
    report = validator.validate_rooms(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "INVALID_ROOM_TYPE" for e in report.errors)


# -------------------------------------------------------------------------
# Test Cases for Timetable Validation
# -------------------------------------------------------------------------

def test_validate_timetable_success(validator, sample_timetable_df, sample_rooms_df):
    report = validator.validate_timetable(sample_timetable_df, set(sample_rooms_df["room_id"]), sample_rooms_df)
    assert report.is_valid is True
    assert report.valid_records == 1


def test_validate_timetable_invalid_room_reference(validator, sample_timetable_df):
    # Only room "B99-UNKNOWN" in schedule, valid rooms has only B01
    dirty = sample_timetable_df.copy()
    dirty.loc[0, "room_id"] = "B99-UNKNOWN"
    report = validator.validate_timetable(dirty, valid_room_ids={"B01-R101"})
    assert report.is_valid is False
    assert any(e.error_type == "INVALID_ROOM_REFERENCE" for e in report.errors)


def test_validate_timetable_enrollment_exceeds_capacity(validator, sample_timetable_df, sample_rooms_df):
    dirty = sample_timetable_df.copy()
    dirty.loc[0, "enrolled_count"] = 500  # Room capacity is 100
    report = validator.validate_timetable(dirty, set(sample_rooms_df["room_id"]), sample_rooms_df)
    assert report.is_valid is False
    assert any(e.error_type == "ENROLLMENT_EXCEEDS_CAPACITY" for e in report.errors)


def test_validate_timetable_collision_detection(validator, sample_timetable_df, sample_rooms_df):
    # Two courses scheduled in same room at same time
    colliding = sample_timetable_df.copy()
    colliding.loc[0, "timetable_id"] = "TT-002"
    dirty = pd.concat([sample_timetable_df, colliding], ignore_index=True)
    report = validator.validate_timetable(dirty, set(sample_rooms_df["room_id"]), sample_rooms_df)
    assert report.is_valid is False
    assert any(e.error_type == "SCHEDULE_COLLISION" for e in report.errors)


# -------------------------------------------------------------------------
# Test Cases for Occupancy Validation
# -------------------------------------------------------------------------

def test_validate_occupancy_success(validator, sample_occupancy_df, sample_rooms_df):
    report = validator.validate_occupancy(sample_occupancy_df, set(sample_rooms_df["room_id"]), sample_rooms_df)
    assert report.is_valid is True
    assert report.valid_records == 1


def test_validate_occupancy_negative_values(validator, sample_occupancy_df):
    dirty = sample_occupancy_df.copy()
    dirty.loc[0, "actual_headcount"] = -10
    report = validator.validate_occupancy(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "NEGATIVE_OCCUPANCY" for e in report.errors)


def test_validate_occupancy_severe_capacity_overflow(validator, sample_occupancy_df):
    dirty = sample_occupancy_df.copy()
    dirty.loc[0, "actual_headcount"] = 350  # Capacity is 100 -> >25% overflow
    report = validator.validate_occupancy(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "EXTREME_CAPACITY_OVERFLOW" for e in report.errors)


def test_validate_occupancy_duplicate_timestamp(validator, sample_occupancy_df):
    dup = sample_occupancy_df.copy()
    dup.loc[0, "observation_id"] = "OBS-002"  # Different ID, same (room_id, timestamp)
    dirty = pd.concat([sample_occupancy_df, dup], ignore_index=True)
    report = validator.validate_occupancy(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "DUPLICATE_ROOM_TIMESTAMP" for e in report.errors)


def test_validate_occupancy_inconsistent_timestamp_hour(validator, sample_occupancy_df):
    dirty = sample_occupancy_df.copy()
    # Timestamp is 09:00:00, but hour column says 15
    dirty.loc[0, "hour"] = 15
    report = validator.validate_occupancy(dirty)
    assert report.is_valid is False
    assert any(e.error_type == "INCONSISTENT_TIMESTAMP_HOUR" for e in report.errors)


def test_validate_occupancy_invalid_room_id(validator, sample_occupancy_df):
    dirty = sample_occupancy_df.copy()
    dirty.loc[0, "room_id"] = "NON-EXISTENT-ROOM"
    report = validator.validate_occupancy(dirty, valid_room_ids={"B01-R101"})
    assert report.is_valid is False
    assert any(e.error_type == "INVALID_ROOM_REFERENCE" for e in report.errors)
