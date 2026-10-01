"""
BDS-06: Reproducible Synthetic Campus-Data Generator
Academic Context: T.Y. B.Sc. Data Science - Semester V Capstone Project

Generates realistic, timetable-grounded campus datasets:
  1. data/raw/rooms.csv       - Master physical room directory & equipment
  2. data/raw/timetable.csv   - Scheduled academic course sessions
  3. data/raw/events.csv      - Academic calendar events (holidays, exams, fests)
  4. data/raw/occupancy.csv   - Calibrated hourly occupancy time series
"""

import argparse
import logging
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np
import pandas as pd

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)


def generate_rooms() -> pd.DataFrame:
    """Generate master directory of campus rooms with physical and pedagogical attributes."""
    buildings = [
        {"id": "B01", "name": "Alan Turing Science & Technology Block", "floors": 4, "type_dist": ["Lecture Hall", "Computer Lab", "Seminar Room"]},
        {"id": "B02", "name": "Ada Lovelace Computing Center", "floors": 3, "type_dist": ["Computer Lab", "Lecture Hall", "Tutorial Room"]},
        {"id": "B03", "name": "Srinivasa Ramanujan Mathematical Sciences", "floors": 3, "type_dist": ["Lecture Hall", "Seminar Room", "Tutorial Room"]},
        {"id": "B04", "name": "Aryabhata Central Lecture Complex", "floors": 2, "type_dist": ["Auditorium", "Lecture Hall"]},
    ]

    rooms: List[Dict] = []
    
    # Building B01: Science & Tech (10 rooms)
    rooms.extend([
        {"room_id": "B01-R101", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 120, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B01-R102", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 100, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B01-R201", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 2, "room_type": "Lecture Hall", "capacity": 80, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B01-R202", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 2, "room_type": "Seminar Room", "capacity": 45, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B01-L203", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 2, "room_type": "Computer Lab", "capacity": 50, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": True},
        {"room_id": "B01-R301", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 3, "room_type": "Lecture Hall", "capacity": 75, "has_projector": True, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B01-R302", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 3, "room_type": "Seminar Room", "capacity": 40, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": False},
        {"room_id": "B01-L303", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 3, "room_type": "Computer Lab", "capacity": 40, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": False},
        {"room_id": "B01-R401", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 4, "room_type": "Tutorial Room", "capacity": 30, "has_projector": False, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B01-R402", "building_id": "B01", "building_name": buildings[0]["name"], "floor": 4, "room_type": "Tutorial Room", "capacity": 30, "has_projector": False, "has_ac": False, "has_computers": False, "is_accessible": False},
    ])

    # Building B02: Computing Center (8 rooms)
    rooms.extend([
        {"room_id": "B02-L101", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 1, "room_type": "Computer Lab", "capacity": 60, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": True},
        {"room_id": "B02-L102", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 1, "room_type": "Computer Lab", "capacity": 60, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": True},
        {"room_id": "B02-R201", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 2, "room_type": "Lecture Hall", "capacity": 85, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B02-L202", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 2, "room_type": "Computer Lab", "capacity": 45, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": True},
        {"room_id": "B02-L203", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 2, "room_type": "Computer Lab", "capacity": 35, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": True},
        {"room_id": "B02-R301", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 3, "room_type": "Tutorial Room", "capacity": 30, "has_projector": False, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B02-R302", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 3, "room_type": "Tutorial Room", "capacity": 30, "has_projector": True, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B02-S303", "building_id": "B02", "building_name": buildings[1]["name"], "floor": 3, "room_type": "Seminar Room", "capacity": 35, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": False},
    ])

    # Building B03: Mathematical Sciences (8 rooms)
    rooms.extend([
        {"room_id": "B03-R101", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 110, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B03-R102", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 90, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B03-R201", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 2, "room_type": "Lecture Hall", "capacity": 70, "has_projector": True, "has_ac": False, "has_computers": False, "is_accessible": True},
        {"room_id": "B03-S202", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 2, "room_type": "Seminar Room", "capacity": 40, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B03-R301", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 3, "room_type": "Tutorial Room", "capacity": 25, "has_projector": False, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B03-R302", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 3, "room_type": "Tutorial Room", "capacity": 25, "has_projector": False, "has_ac": False, "has_computers": False, "is_accessible": False},
        {"room_id": "B03-L303", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 3, "room_type": "Computer Lab", "capacity": 30, "has_projector": True, "has_ac": True, "has_computers": True, "is_accessible": False},
        {"room_id": "B03-S304", "building_id": "B03", "building_name": buildings[2]["name"], "floor": 3, "room_type": "Seminar Room", "capacity": 35, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": False},
    ])

    # Building B04: Central Complex & Auditorium (6 rooms)
    rooms.extend([
        {"room_id": "B04-AUD01", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 1, "room_type": "Auditorium", "capacity": 280, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B04-R101", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 150, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B04-R102", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 1, "room_type": "Lecture Hall", "capacity": 130, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B04-R201", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 2, "room_type": "Lecture Hall", "capacity": 100, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B04-S202", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 2, "room_type": "Seminar Room", "capacity": 50, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
        {"room_id": "B04-S203", "building_id": "B04", "building_name": buildings[3]["name"], "floor": 2, "room_type": "Seminar Room", "capacity": 50, "has_projector": True, "has_ac": True, "has_computers": False, "is_accessible": True},
    ])

    return pd.DataFrame(rooms)


def generate_timetable(rooms_df: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    """Generate realistic academic timetable without conflicting room-slot collisions."""
    courses = [
        {"code": "DS101", "name": "Intro to Data Science", "enrolled": 95, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "DS201", "name": "Python & Data Structures", "enrolled": 55, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "DS202", "name": "Relational Databases & SQL", "enrolled": 48, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "DS301", "name": "Machine Learning", "enrolled": 70, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "DS302", "name": "Deep Learning Systems", "enrolled": 65, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "DS303", "name": "Spatiotemporal Analytics", "enrolled": 38, "type": "Seminar Room", "slots_per_week": 2, "duration": 1},
        {"code": "DS304", "name": "Big Data Engineering", "enrolled": 42, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "DS305", "name": "Computer Vision Lab", "enrolled": 32, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "CS101", "name": "Programming Fundamentals", "enrolled": 110, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "CS201", "name": "Algorithms & Complexity", "enrolled": 85, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "CS202", "name": "Operating Systems", "enrolled": 75, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "CS301", "name": "Distributed Systems", "enrolled": 55, "type": "Lecture Hall", "slots_per_week": 2, "duration": 1},
        {"code": "CS302", "name": "Cloud Computing & DevOps", "enrolled": 45, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "CS305", "name": "Web Technologies", "enrolled": 45, "type": "Computer Lab", "slots_per_week": 2, "duration": 2},
        {"code": "MAT101", "name": "Calculus & Linear Algebra", "enrolled": 115, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "MAT201", "name": "Probability & Statistics", "enrolled": 90, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "MAT202", "name": "Optimization for ML", "enrolled": 68, "type": "Lecture Hall", "slots_per_week": 3, "duration": 1},
        {"code": "MAT301", "name": "Time Series Forecasting", "enrolled": 42, "type": "Seminar Room", "slots_per_week": 2, "duration": 1},
        {"code": "ENG101", "name": "Technical Communication", "enrolled": 140, "type": "Lecture Hall", "slots_per_week": 2, "duration": 1},
        {"code": "ETH301", "name": "Data Ethics & AI Policy", "enrolled": 80, "type": "Lecture Hall", "slots_per_week": 2, "duration": 1},
        {"code": "GEN201", "name": "Research Methodology", "enrolled": 240, "type": "Auditorium", "slots_per_week": 1, "duration": 2},
    ]

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
    operating_hours = [8, 9, 10, 11, 12, 13, 14, 15, 16]

    timetable_records: List[Dict] = []
    # Track occupied slots: set of (room_id, day, hour)
    occupied_slots = set()

    timetable_counter = 1

    for c_idx, course in enumerate(courses):
        instructor_id = f"INST_{(c_idx % 12) + 1:02d}"
        req_type = course["type"]
        enrolled = course["enrolled"]
        duration = course["duration"]
        needed_slots = course["slots_per_week"]

        # Eligible rooms matching type and capacity
        eligible = rooms_df[
            (rooms_df["room_type"] == req_type) & 
            (rooms_df["capacity"] >= enrolled)
        ]
        if eligible.empty:
            # Fallback to any room with sufficient capacity
            eligible = rooms_df[rooms_df["capacity"] >= enrolled]

        candidate_room_ids = eligible["room_id"].tolist()

        scheduled_count = 0
        attempts = 0
        max_attempts = 300

        while scheduled_count < needed_slots and attempts < max_attempts:
            attempts += 1
            # Pick room
            room_id = rng.choice(candidate_room_ids)
            # Pick day (Saturday has only morning slots 9 to 12)
            day = rng.choice(days)
            if day == "Saturday":
                start_hour = rng.choice([9, 10, 11])
            else:
                start_hour = rng.choice(operating_hours)

            # Check if all consecutive duration hours are free
            is_free = True
            for h in range(start_hour, start_hour + duration):
                if h > 17:
                    is_free = False
                    break
                if (room_id, day, h) in occupied_slots:
                    is_free = False
                    break

            if is_free:
                for h in range(start_hour, start_hour + duration):
                    occupied_slots.add((room_id, day, h))

                timetable_records.append({
                    "timetable_id": f"TT-{timetable_counter:04d}",
                    "course_code": course["code"],
                    "course_name": course["name"],
                    "instructor_id": instructor_id,
                    "enrolled_count": enrolled,
                    "day_of_week": day,
                    "start_time": f"{start_hour:02d}:00:00",
                    "end_time": f"{start_hour + duration:02d}:00:00",
                    "duration_hours": duration,
                    "room_id": room_id,
                    "room_type_required": req_type,
                    "academic_term": "Semester V - Fall 2026"
                })
                timetable_counter += 1
                scheduled_count += 1

    return pd.DataFrame(timetable_records)


def generate_events(start_date: date, num_weeks: int) -> pd.DataFrame:
    """Generate academic calendar events (holidays, exams, symposiums, study breaks)."""
    end_date = start_date + timedelta(weeks=num_weeks)
    events: List[Dict] = []
    e_counter = 1

    # Explicit known calendar events
    predefined_events = [
        {"name": "Orientation Week", "start_offset_days": 0, "duration": 5, "type": "orientation", "impact": 0.8, "scope": "campus_wide"},
        {"name": "Independence Day Holiday", "start_offset_days": 12, "duration": 1, "type": "holiday", "impact": 0.0, "scope": "campus_wide"},
        {"name": "Ganesh Chaturthi Holiday", "start_offset_days": 24, "duration": 1, "type": "holiday", "impact": 0.0, "scope": "campus_wide"},
        {"name": "Teachers Day Fest & Symposium", "start_offset_days": 33, "duration": 1, "type": "symposium", "impact": 1.15, "scope": "auditorium_seminar"},
        {"name": "Mid-Semester Examinations", "start_offset_days": 49, "duration": 6, "type": "exam_period", "impact": 0.95, "scope": "exam_halls"},
        {"name": "Gandhi Jayanti Holiday", "start_offset_days": 60, "duration": 1, "type": "holiday", "impact": 0.0, "scope": "campus_wide"},
        {"name": "Diwali Semester Break", "start_offset_days": 77, "duration": 5, "type": "holiday", "impact": 0.0, "scope": "campus_wide"},
        {"name": "Pre-Exam Study Leave", "start_offset_days": 98, "duration": 5, "type": "study_break", "impact": 0.35, "scope": "library_labs"},
        {"name": "End-Semester Examinations", "start_offset_days": 105, "duration": 6, "type": "exam_period", "impact": 0.95, "scope": "exam_halls"},
    ]

    for pe in predefined_events:
        event_start = start_date + timedelta(days=pe["start_offset_days"])
        if event_start < end_date:
            for d in range(pe["duration"]):
                cur_d = event_start + timedelta(days=d)
                if cur_d <= end_date:
                    events.append({
                        "event_id": f"EVT-{e_counter:04d}",
                        "date": cur_d.isoformat(),
                        "event_name": pe["name"],
                        "event_type": pe["type"],
                        "impact_factor": pe["impact"],
                        "affected_scope": pe["scope"]
                    })
                    e_counter += 1

    return pd.DataFrame(events)


def generate_occupancy(
    rooms_df: pd.DataFrame,
    timetable_df: pd.DataFrame,
    events_df: pd.DataFrame,
    start_date: date,
    num_weeks: int,
    rng: np.random.Generator
) -> pd.DataFrame:
    """Generate calibrated, realistic 24-hour occupancy time series tied directly to the timetable."""
    room_map = rooms_df.set_index("room_id").to_dict(orient="index")
    total_days = num_weeks * 7

    # Build quick lookup: (room_id, day_of_week, hour) -> list of matching timetable records
    tt_lookup: Dict[Tuple[str, str, int], Dict] = {}
    for _, row in timetable_df.iterrows():
        r_id = row["room_id"]
        dow = row["day_of_week"]
        s_hour = int(row["start_time"].split(":")[0])
        e_hour = int(row["end_time"].split(":")[0])
        for h in range(s_hour, e_hour):
            tt_lookup[(r_id, dow, h)] = {
                "course_code": row["course_code"],
                "course_name": row["course_name"],
                "enrolled": int(row["enrolled_count"]),
                "room_type_required": row["room_type_required"]
            }

    # Build quick event lookup: date_str -> list of event dicts
    event_lookup: Dict[str, Dict] = {}
    for _, erow in events_df.iterrows():
        event_lookup[erow["date"]] = erow.to_dict()

    observations: List[Dict] = []
    obs_id = 1

    for day_offset in range(total_days):
        current_date = start_date + timedelta(days=day_offset)
        date_str = current_date.isoformat()
        dow = current_date.strftime("%A")
        week_num = (day_offset // 7) + 1
        is_weekend = (dow in ["Saturday", "Sunday"])
        event_info = event_lookup.get(date_str, None)
        event_type = event_info["event_type"] if event_info else "normal"

        for hour in range(24):
            for room_id, rdata in room_map.items():
                capacity = rdata["capacity"]
                room_type = rdata["room_type"]

                # 1. Determine scheduled status
                tt_entry = tt_lookup.get((room_id, dow, hour), None)
                is_scheduled = (tt_entry is not None)
                course_code = tt_entry["course_code"] if is_scheduled else None
                enrolled = tt_entry["enrolled"] if is_scheduled else 0

                anomaly_flag = "none"
                actual_headcount = 0

                # -----------------------------------------------------------------
                # CASE A: Full Campus Holiday / Break (Closed)
                # -----------------------------------------------------------------
                if event_type == "holiday":
                    # Deep night / empty campus. Rare security/patrol inspection (0-1 people)
                    if rng.random() < 0.02:
                        actual_headcount = 1
                    else:
                        actual_headcount = 0

                # -----------------------------------------------------------------
                # CASE B: Examination Period
                # -----------------------------------------------------------------
                elif event_type == "exam_period":
                    # Exams held in Lecture Halls & Auditoriums at 10-12 and 14-16
                    if room_type in ["Lecture Hall", "Auditorium"] and hour in [10, 11, 14, 15]:
                        # High attendance exam batch (88% - 98% of capacity)
                        exam_att = rng.uniform(0.88, 0.98)
                        actual_headcount = int(round(capacity * 0.75 * exam_att))
                    elif room_type == "Computer Lab" and 9 <= hour <= 17:
                        # Some students in labs for practicals or study
                        actual_headcount = int(round(capacity * rng.uniform(0.15, 0.35)))
                    else:
                        actual_headcount = int(rng.poisson(lam=0.5))

                # -----------------------------------------------------------------
                # CASE C: Pre-Exam Study Leave
                # -----------------------------------------------------------------
                elif event_type == "study_break":
                    # Regular classes suspended; self-study in labs & seminar rooms
                    if 9 <= hour <= 18:
                        if room_type in ["Computer Lab", "Seminar Room"]:
                            actual_headcount = int(round(capacity * rng.uniform(0.20, 0.45)))
                        else:
                            actual_headcount = int(rng.poisson(lam=1.0))
                    else:
                        actual_headcount = 0

                # -----------------------------------------------------------------
                # CASE D: Sunday (Campus basically idle)
                # -----------------------------------------------------------------
                elif dow == "Sunday":
                    if 10 <= hour <= 17 and rng.random() < 0.08:
                        # Rare student study group / robotics lab session
                        actual_headcount = int(rng.integers(3, min(15, capacity)))
                        anomaly_flag = "weekend_activity"
                    else:
                        actual_headcount = int(rng.poisson(lam=0.1))

                # -----------------------------------------------------------------
                # CASE E: Regular Weekday or Saturday
                # -----------------------------------------------------------------
                else:
                    if is_scheduled:
                        # Realistic Attendance Decay Curve:
                        # 1. Base Beta distribution (mean ~0.82)
                        base_rate = rng.beta(18, 4)

                        # 2. Time-of-day attendance multiplier
                        tod_mult = {
                            8: 0.82,   # Early morning rush
                            9: 0.94,
                            10: 1.05,  # Peak
                            11: 1.06,  # Peak
                            12: 1.02,
                            13: 0.88,  # Post-lunch dip
                            14: 0.96,
                            15: 0.98,
                            16: 0.88,
                            17: 0.78
                        }.get(hour, 0.90)

                        # 3. Day of week multiplier
                        dow_mult = {
                            "Monday": 1.02,
                            "Tuesday": 1.04,
                            "Wednesday": 1.02,
                            "Thursday": 0.98,
                            "Friday": 0.88,
                            "Saturday": 0.72
                        }.get(dow, 1.0)

                        # 4. Semester progression factor
                        if week_num <= 3:
                            sem_mult = 1.06  # Honeymoon attendance
                        elif 6 <= week_num <= 9:
                            sem_mult = 0.90  # Mid-term fatigue
                        else:
                            sem_mult = 0.98

                        expected = enrolled * base_rate * tod_mult * dow_mult * sem_mult
                        noise = rng.normal(0, max(1.5, enrolled * 0.04))
                        computed = int(round(expected + noise))

                        # --- Anomaly Injections for Scheduled Classes ---
                        rand_draw = rng.random()
                        if rand_draw < 0.015:
                            # Class canceled unexpectedly (sick professor / sudden meeting)
                            actual_headcount = int(rng.integers(0, 3))
                            anomaly_flag = "class_cancellation"
                        elif rand_draw < 0.025:
                            # Combined guest lecture / student overflow
                            actual_headcount = min(capacity, int(round(enrolled * 1.15)))
                            anomaly_flag = "overcrowding_surge"
                        elif rand_draw < 0.030:
                            # Sensor hardware glitch (transient dropout to 0 or bad reading)
                            actual_headcount = 0
                            anomaly_flag = "sensor_dropout_glitch"
                        else:
                            actual_headcount = computed

                    else:
                        # Room is NOT scheduled in timetable (Unscheduled / Idle)
                        if 0 <= hour <= 6 or hour >= 22:
                            # Night idle
                            actual_headcount = 0 if rng.random() > 0.02 else 1
                        elif 7 <= hour <= 8:
                            # Early arrivals / cleaning staff
                            actual_headcount = int(rng.poisson(lam=0.4))
                        elif 8 < hour < 18:
                            # Daytime unbooked room:
                            # 3% chance of informal study group or student club gathering
                            if rng.random() < 0.035:
                                actual_headcount = int(rng.integers(6, min(30, capacity)))
                                anomaly_flag = "unscheduled_group"
                            else:
                                # Normal low ambient occupancy (individual reading)
                                actual_headcount = int(rng.poisson(lam=0.8))
                        elif 18 <= hour < 22:
                            # Evening study / project work
                            if room_type in ["Computer Lab", "Seminar Room"] and rng.random() < 0.06:
                                actual_headcount = int(rng.integers(5, min(20, capacity)))
                                anomaly_flag = "evening_club_activity"
                            else:
                                actual_headcount = int(rng.poisson(lam=0.5))

                # Physical sanity bound clamping
                actual_headcount = max(0, min(capacity, actual_headcount))

                observations.append({
                    "observation_id": f"OBS-{obs_id:07d}",
                    "timestamp": f"{date_str}T{hour:02d}:00:00Z",
                    "date": date_str,
                    "hour": hour,
                    "day_of_week": dow,
                    "week_number": week_num,
                    "room_id": room_id,
                    "room_type": room_type,
                    "capacity": capacity,
                    "is_scheduled": is_scheduled,
                    "scheduled_course_code": course_code if is_scheduled else "",
                    "scheduled_enrollment": enrolled,
                    "actual_headcount": actual_headcount,
                    "is_holiday": (event_type == "holiday"),
                    "event_type": event_type,
                    "anomaly_flag": anomaly_flag
                })
                obs_id += 1

    return pd.DataFrame(observations)


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic campus occupancy dataset.")
    parser.add_argument("--seed", type=int, default=42, help="Fixed random seed for determinism (default: 42)")
    parser.add_argument("--start-date", type=str, default="2026-08-03", help="Semester start date YYYY-MM-DD")
    parser.add_argument("--weeks", type=int, default=16, help="Number of academic weeks (default: 16)")
    parser.add_argument("--output-dir", type=str, default="data/raw", help="Target output directory")
    args = parser.parse_args()

    out_path = Path(args.output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(args.seed)
    start_d = datetime.strptime(args.start_date, "%Y-%m-%d").date()

    logger.info(f"Initializing reproducible synthetic generator with seed={args.seed}")
    logger.info(f"Simulation timeline: {start_d} for {args.weeks} weeks ({args.weeks * 7} days)")

    # 1. Rooms
    rooms_df = generate_rooms()
    rooms_file = out_path / "rooms.csv"
    rooms_df.to_csv(rooms_file, index=False)
    logger.info(f"Saved {len(rooms_df)} rooms to {rooms_file}")

    # 2. Timetable
    timetable_df = generate_timetable(rooms_df, rng)
    timetable_file = out_path / "timetable.csv"
    timetable_df.to_csv(timetable_file, index=False)
    logger.info(f"Saved {len(timetable_df)} timetable slots to {timetable_file}")

    # 3. Events
    events_df = generate_events(start_d, args.weeks)
    events_file = out_path / "events.csv"
    events_df.to_csv(events_file, index=False)
    logger.info(f"Saved {len(events_df)} academic event days to {events_file}")

    # 4. Occupancy Time Series
    occupancy_df = generate_occupancy(rooms_df, timetable_df, events_df, start_d, args.weeks, rng)
    occupancy_file = out_path / "occupancy.csv"
    occupancy_df.to_csv(occupancy_file, index=False)
    logger.info(f"Saved {len(occupancy_df):,} hourly occupancy records to {occupancy_file}")

    logger.info("Dataset generation completed successfully.")


if __name__ == "__main__":
    main()
