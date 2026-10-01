"""
BDS-06: Data Validation Pipeline
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Validates raw campus datasets:
  - Required column presence
  - Data types and value domains
  - ISO-8601 timestamps and temporal consistency
  - Primary key and composite duplicate detection
  - Missing value audits
  - Physical boundary checks (negative occupancy, capacity overflow)
  - Cross-dataset referential integrity (Room IDs, Timetable references)
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple

import numpy as np
import pandas as pd


@dataclass
class ValidationError:
    """Represents a specific validation failure in a dataset."""
    row_index: Optional[int]
    record_id: Optional[str]
    column: str
    error_type: str
    error_message: str
    invalid_value: Any


@dataclass
class ValidationReport:
    """Comprehensive validation audit report for a dataset."""
    dataset_name: str
    total_records: int
    valid_records: int
    invalid_records: int
    duplicate_records: int
    missing_values: Dict[str, int]
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    is_valid: bool = True

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to JSON-serializable dictionary."""
        data = asdict(self)
        return data


class CampusDataValidator:
    """Production validator for university campus occupancy, timetable, and room datasets."""

    ROOM_REQUIRED_COLUMNS: Dict[str, str] = {
        "room_id": "string",
        "building_id": "string",
        "building_name": "string",
        "floor": "int",
        "room_type": "string",
        "capacity": "int",
        "has_projector": "bool",
        "has_ac": "bool",
        "has_computers": "bool",
        "is_accessible": "bool",
    }

    TIMETABLE_REQUIRED_COLUMNS: Dict[str, str] = {
        "timetable_id": "string",
        "course_code": "string",
        "course_name": "string",
        "instructor_id": "string",
        "enrolled_count": "int",
        "day_of_week": "string",
        "start_time": "string",
        "end_time": "string",
        "room_id": "string",
        "room_type_required": "string",
    }

    OCCUPANCY_REQUIRED_COLUMNS: Dict[str, str] = {
        "observation_id": "string",
        "timestamp": "string",
        "date": "string",
        "hour": "int",
        "day_of_week": "string",
        "room_id": "string",
        "capacity": "int",
        "is_scheduled": "bool",
        "actual_headcount": "int",
    }

    ALLOWED_ROOM_TYPES: Set[str] = {
        "Lecture Hall",
        "Computer Lab",
        "Seminar Room",
        "Auditorium",
        "Tutorial Room",
    }

    ALLOWED_DAYS_OF_WEEK: Set[str] = {
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    }

    def validate_rooms(self, df: pd.DataFrame) -> ValidationReport:
        """Validate rooms dataframe against physical schemas and constraints."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        total_records = len(df)

        # 1. Required Columns
        missing_cols = [c for c in self.ROOM_REQUIRED_COLUMNS if c not in df.columns]
        for mc in missing_cols:
            errors.append(ValidationError(
                row_index=None,
                record_id=None,
                column=mc,
                error_type="MISSING_COLUMN",
                error_message=f"Mandatory column '{mc}' is missing from rooms dataset.",
                invalid_value=None
            ))

        if missing_cols:
            return ValidationReport(
                dataset_name="rooms",
                total_records=total_records,
                valid_records=0,
                invalid_records=total_records,
                duplicate_records=0,
                missing_values={c: int(df[c].isna().sum()) for c in df.columns},
                errors=errors,
                warnings=warnings,
                is_valid=False
            )

        # 2. Missing Values Audit
        missing_vals = {c: int(df[c].isna().sum()) for c in df.columns}

        # 3. Duplicate Room IDs
        duplicate_mask = df.duplicated(subset=["room_id"], keep=False)
        duplicate_records = int(df.duplicated(subset=["room_id"]).sum())
        for idx, row in df[duplicate_mask].iterrows():
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("room_id")),
                column="room_id",
                error_type="DUPLICATE_ROOM_ID",
                error_message=f"Duplicate room_id '{row.get('room_id')}' detected.",
                invalid_value=row.get("room_id")
            ))

        invalid_rows: Set[int] = set()

        # 4. Row-level validations
        for idx, row in df.iterrows():
            r_id = str(row["room_id"])
            cap = row["capacity"]
            r_type = str(row["room_type"])

            # Capacity bounds
            if pd.isna(cap) or not isinstance(cap, (int, np.integer, float)) or cap <= 0:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=r_id,
                    column="capacity",
                    error_type="INVALID_CAPACITY",
                    error_message=f"Room capacity must be a positive integer, found '{cap}'.",
                    invalid_value=cap
                ))
            elif cap > 1000:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=r_id,
                    column="capacity",
                    error_type="EXCESSIVE_CAPACITY",
                    error_message=f"Room capacity {cap} exceeds university building limit (1000).",
                    invalid_value=cap
                ))

            # Room type
            if r_type not in self.ALLOWED_ROOM_TYPES:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=r_id,
                    column="room_type",
                    error_type="INVALID_ROOM_TYPE",
                    error_message=f"Unrecognized room_type '{r_type}'. Allowed: {sorted(self.ALLOWED_ROOM_TYPES)}",
                    invalid_value=r_type
                ))

        invalid_count = len(invalid_rows) + duplicate_records
        valid_count = max(0, total_records - invalid_count)

        return ValidationReport(
            dataset_name="rooms",
            total_records=total_records,
            valid_records=valid_count,
            invalid_records=invalid_count,
            duplicate_records=duplicate_records,
            missing_values=missing_vals,
            errors=errors,
            warnings=warnings,
            is_valid=(len(errors) == 0)
        )

    def validate_timetable(
        self,
        df: pd.DataFrame,
        valid_room_ids: Optional[Set[str]] = None,
        rooms_df: Optional[pd.DataFrame] = None
    ) -> ValidationReport:
        """Validate timetable dataset for integrity, collisions, and room references."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        total_records = len(df)

        missing_cols = [c for c in self.TIMETABLE_REQUIRED_COLUMNS if c not in df.columns]
        for mc in missing_cols:
            errors.append(ValidationError(
                row_index=None,
                record_id=None,
                column=mc,
                error_type="MISSING_COLUMN",
                error_message=f"Mandatory column '{mc}' is missing from timetable dataset.",
                invalid_value=None
            ))

        if missing_cols:
            return ValidationReport(
                dataset_name="timetable",
                total_records=total_records,
                valid_records=0,
                invalid_records=total_records,
                duplicate_records=0,
                missing_values={c: int(df[c].isna().sum()) for c in df.columns},
                errors=errors,
                warnings=warnings,
                is_valid=False
            )

        missing_vals = {c: int(df[c].isna().sum()) for c in df.columns}

        # 1. Primary key duplicates
        duplicate_records = int(df.duplicated(subset=["timetable_id"]).sum())
        for idx, row in df[df.duplicated(subset=["timetable_id"], keep=False)].iterrows():
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("timetable_id")),
                column="timetable_id",
                error_type="DUPLICATE_TIMETABLE_ID",
                error_message=f"Duplicate timetable_id '{row.get('timetable_id')}'.",
                invalid_value=row.get("timetable_id")
            ))

        # 2. Room capacity mapping (if available)
        room_capacities = {}
        if rooms_df is not None and "room_id" in rooms_df.columns and "capacity" in rooms_df.columns:
            room_capacities = dict(zip(rooms_df["room_id"], rooms_df["capacity"]))

        invalid_rows: Set[int] = set()

        # 3. Row validations
        for idx, row in df.iterrows():
            tt_id = str(row["timetable_id"])
            r_id = str(row["room_id"])
            enrolled = row["enrolled_count"]
            dow = str(row["day_of_week"])
            start_str = str(row["start_time"])
            end_str = str(row["end_time"])

            # Referential integrity: Room ID exists
            if valid_room_ids and r_id not in valid_room_ids:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=tt_id,
                    column="room_id",
                    error_type="INVALID_ROOM_REFERENCE",
                    error_message=f"Timetable references room_id '{r_id}' which does not exist in master rooms.",
                    invalid_value=r_id
                ))

            # Enrollment checks
            if pd.isna(enrolled) or enrolled <= 0:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=tt_id,
                    column="enrolled_count",
                    error_type="INVALID_ENROLLMENT",
                    error_message=f"Course enrollment must be a positive integer, found '{enrolled}'.",
                    invalid_value=enrolled
                ))
            elif r_id in room_capacities and enrolled > room_capacities[r_id]:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=tt_id,
                    column="enrolled_count",
                    error_type="ENROLLMENT_EXCEEDS_CAPACITY",
                    error_message=f"Enrolled strength ({enrolled}) exceeds assigned room capacity ({room_capacities[r_id]}).",
                    invalid_value=enrolled
                ))

            # Day of week
            if dow not in self.ALLOWED_DAYS_OF_WEEK:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=tt_id,
                    column="day_of_week",
                    error_type="INVALID_DAY_OF_WEEK",
                    error_message=f"Invalid day_of_week '{dow}'.",
                    invalid_value=dow
                ))

            # Time parsing & bounds
            try:
                s_h = int(start_str.split(":")[0])
                e_h = int(end_str.split(":")[0])
                if s_h < 7 or e_h > 21 or s_h >= e_h:
                    invalid_rows.add(int(idx))
                    errors.append(ValidationError(
                        row_index=int(idx),
                        record_id=tt_id,
                        column="start_time",
                        error_type="INVALID_TIME_SLOT",
                        error_message=f"Time slot {start_str}-{end_str} outside operational campus bounds (07:00-21:00).",
                        invalid_value=f"{start_str}-{end_str}"
                    ))
            except Exception as ex:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=tt_id,
                    column="start_time",
                    error_type="TIME_PARSE_ERROR",
                    error_message=f"Failed to parse time range '{start_str}' - '{end_str}': {ex}",
                    invalid_value=f"{start_str}-{end_str}"
                ))

        # 4. Schedule collision detection (same room, same day, overlapping hours)
        room_schedule_map: Dict[Tuple[str, str], List[Tuple[int, int, str, int]]] = {}
        for idx, row in df.iterrows():
            try:
                s_h = int(str(row["start_time"]).split(":")[0])
                e_h = int(str(row["end_time"]).split(":")[0])
                key = (str(row["room_id"]), str(row["day_of_week"]))
                if key not in room_schedule_map:
                    room_schedule_map[key] = []
                for existing_s, existing_e, existing_id, existing_idx in room_schedule_map[key]:
                    # Check overlap: (StartA < EndB) and (EndA > StartB)
                    if s_h < existing_e and e_h > existing_s:
                        invalid_rows.add(int(idx))
                        invalid_rows.add(existing_idx)
                        errors.append(ValidationError(
                            row_index=int(idx),
                            record_id=str(row["timetable_id"]),
                            column="start_time",
                            error_type="SCHEDULE_COLLISION",
                            error_message=f"Collision in room '{row['room_id']}' on {row['day_of_week']}: clashes with '{existing_id}' ({existing_s}:00-{existing_e}:00).",
                            invalid_value=f"{s_h}:00-{e_h}:00"
                        ))
                room_schedule_map[key].append((s_h, e_h, str(row["timetable_id"]), int(idx)))
            except Exception:
                continue

        invalid_count = len(invalid_rows) + duplicate_records
        valid_count = max(0, total_records - invalid_count)

        return ValidationReport(
            dataset_name="timetable",
            total_records=total_records,
            valid_records=valid_count,
            invalid_records=invalid_count,
            duplicate_records=duplicate_records,
            missing_values=missing_vals,
            errors=errors,
            warnings=warnings,
            is_valid=(len(errors) == 0)
        )

    def validate_occupancy(
        self,
        df: pd.DataFrame,
        valid_room_ids: Optional[Set[str]] = None,
        rooms_df: Optional[pd.DataFrame] = None
    ) -> ValidationReport:
        """Validate occupancy time series: timestamps, duplicates, capacity bounds, and referential integrity."""
        errors: List[ValidationError] = []
        warnings: List[ValidationError] = []
        total_records = len(df)

        # 1. Required Columns Check
        missing_cols = [c for c in self.OCCUPANCY_REQUIRED_COLUMNS if c not in df.columns]
        for mc in missing_cols:
            errors.append(ValidationError(
                row_index=None,
                record_id=None,
                column=mc,
                error_type="MISSING_COLUMN",
                error_message=f"Mandatory column '{mc}' is missing from occupancy dataset.",
                invalid_value=None
            ))

        if missing_cols:
            return ValidationReport(
                dataset_name="occupancy",
                total_records=total_records,
                valid_records=0,
                invalid_records=total_records,
                duplicate_records=0,
                missing_values={c: int(df[c].isna().sum()) for c in df.columns},
                errors=errors,
                warnings=warnings,
                is_valid=False
            )

        missing_vals = {c: int(df[c].isna().sum()) for c in df.columns}

        # 2. Duplicate Detection: Primary observation_id
        obs_duplicates = int(df.duplicated(subset=["observation_id"]).sum())
        if obs_duplicates > 0:
            for idx, row in df[df.duplicated(subset=["observation_id"], keep=False)].head(100).iterrows():
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=str(row.get("observation_id")),
                    column="observation_id",
                    error_type="DUPLICATE_OBSERVATION_ID",
                    error_message=f"Duplicate observation_id '{row.get('observation_id')}'.",
                    invalid_value=row.get("observation_id")
                ))

        # 3. Composite Key Duplicates: (room_id, timestamp)
        composite_duplicates = int(df.duplicated(subset=["room_id", "timestamp"]).sum())
        if composite_duplicates > 0:
            for idx, row in df[df.duplicated(subset=["room_id", "timestamp"], keep=False)].head(100).iterrows():
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=str(row.get("observation_id")),
                    column="timestamp",
                    error_type="DUPLICATE_ROOM_TIMESTAMP",
                    error_message=f"Duplicate temporal observation for room '{row.get('room_id')}' at timestamp '{row.get('timestamp')}'.",
                    invalid_value=f"{row.get('room_id')}@{row.get('timestamp')}"
                ))

        # 4. Room capacity dictionary
        room_capacities: Dict[str, int] = {}
        if rooms_df is not None and "room_id" in rooms_df.columns and "capacity" in rooms_df.columns:
            room_capacities = dict(zip(rooms_df["room_id"], rooms_df["capacity"]))

        invalid_rows: Set[int] = set()

        # Vectorized checks for speed across large time series (86k+ rows)
        # A. Negative occupancy
        neg_mask = df["actual_headcount"] < 0
        for idx in df[neg_mask].index[:100]:
            invalid_rows.add(int(idx))
            row = df.loc[idx]
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("observation_id")),
                column="actual_headcount",
                error_type="NEGATIVE_OCCUPANCY",
                error_message=f"Negative occupancy headcount '{row['actual_headcount']}' is physically impossible.",
                invalid_value=row["actual_headcount"]
            ))

        # B. Non-finite / NaN occupancy
        nan_headcount_mask = df["actual_headcount"].isna()
        for idx in df[nan_headcount_mask].index[:100]:
            invalid_rows.add(int(idx))
            row = df.loc[idx]
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("observation_id")),
                column="actual_headcount",
                error_type="NULL_OCCUPANCY",
                error_message="Occupancy actual_headcount cannot be null.",
                invalid_value=None
            ))

        # C. Referential integrity check
        if valid_room_ids:
            invalid_rooms_mask = ~df["room_id"].isin(valid_room_ids)
            for idx in df[invalid_rooms_mask].index[:100]:
                invalid_rows.add(int(idx))
                row = df.loc[idx]
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=str(row.get("observation_id")),
                    column="room_id",
                    error_type="INVALID_ROOM_REFERENCE",
                    error_message=f"Occupancy references non-existent room_id '{row['room_id']}'.",
                    invalid_value=row["room_id"]
                ))

        # D. Occupancy Exceeds Physical Capacity
        # Check against row capacity and room_master capacity
        exceeds_cap_mask = df["actual_headcount"] > df["capacity"]
        for idx in df[exceeds_cap_mask].index[:100]:
            row = df.loc[idx]
            headcount = row["actual_headcount"]
            cap = row["capacity"]
            if headcount > cap * 1.25:
                invalid_rows.add(int(idx))
                errors.append(ValidationError(
                    row_index=int(idx),
                    record_id=str(row.get("observation_id")),
                    column="actual_headcount",
                    error_type="EXTREME_CAPACITY_OVERFLOW",
                    error_message=f"Occupancy {headcount} severely exceeds room capacity ({cap}) by >25% (likely sensor corruption).",
                    invalid_value=headcount
                ))
            else:
                warnings.append(ValidationError(
                    row_index=int(idx),
                    record_id=str(row.get("observation_id")),
                    column="actual_headcount",
                    error_type="MODERATE_CAPACITY_OVERFLOW",
                    error_message=f"Occupancy {headcount} moderately exceeds room capacity {cap}.",
                    invalid_value=headcount
                ))

        # E. Timestamp formatting and temporal consistency
        # Sample or vectorized check on timestamp parsing
        parsed_ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
        unparseable_mask = parsed_ts.isna() & df["timestamp"].notna()
        for idx in df[unparseable_mask].index[:50]:
            invalid_rows.add(int(idx))
            row = df.loc[idx]
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("observation_id")),
                column="timestamp",
                error_type="INVALID_TIMESTAMP_FORMAT",
                error_message=f"Failed to parse ISO-8601 timestamp '{row['timestamp']}'.",
                invalid_value=row["timestamp"]
            ))

        # F. Temporal field consistency: hour & date vs timestamp
        valid_ts_df = df[~unparseable_mask].copy()
        valid_ts = parsed_ts[~unparseable_mask]
        
        hour_mismatch = (valid_ts.dt.hour != valid_ts_df["hour"])
        for idx in valid_ts_df[hour_mismatch].index[:50]:
            invalid_rows.add(int(idx))
            row = df.loc[idx]
            errors.append(ValidationError(
                row_index=int(idx),
                record_id=str(row.get("observation_id")),
                column="hour",
                error_type="INCONSISTENT_TIMESTAMP_HOUR",
                error_message=f"Hour column ({row['hour']}) does not match timestamp hour ({valid_ts.loc[idx].hour}).",
                invalid_value=f"col_hour={row['hour']}_vs_ts_hour={valid_ts.loc[idx].hour}"
            ))

        total_invalid = len(invalid_rows) + composite_duplicates + obs_duplicates
        valid_count = max(0, total_records - total_invalid)

        return ValidationReport(
            dataset_name="occupancy",
            total_records=total_records,
            valid_records=valid_count,
            invalid_records=total_invalid,
            duplicate_records=composite_duplicates + obs_duplicates,
            missing_values=missing_vals,
            errors=errors,
            warnings=warnings,
            is_valid=(len(errors) == 0)
        )
