# BDS-06 Planner User Guide

**For:** Facilities/space planners and academic coordinators using the local demonstration.  
**Data:** The checked-in occupancy dataset is synthetic; the dashboard is read-only.

## Open the Dashboard

Open `http://localhost:8501`. Read the status first:

- **API:** whether the FastAPI service responds.
- **Occupancy data:** whether required room/occupancy artifacts are available.
- **Forecast model:** whether the current XGBoost model and metadata are available.
- **Overall readiness:** whether the API reports all required dependencies ready.

If readiness is degraded or unavailable, do not interpret missing results as zero occupancy. Ask the technical operator to check the readiness endpoint and logs.

## Overview

Choose one scope:

- **Campus:** aggregate across all rooms.
- **Building:** enter a building ID, such as `B01`, then apply filters.
- **Room:** enter a room ID, such as `B01-R101`, then apply filters.

Optional date range, day-of-week, and time-of-day filters are available when supported by the API. The building and room fields are entered as identifiers; they are not automatically discovered in a dropdown.

The KPI row reports:

- **SUR (Seat Utilization Rate):** observed people divided by available seats, aggregated across the selected observations.
- **RFU (Room Frequency of Use):** occupied room-hours divided by the API's estimated operating room-hours for the selected scope. The denominator uses distinct dates, rooms, and configured operating hours (or the selected time-of-day window); it is not derived from per-room timetable availability. For explicit start/end timestamp filters, the denominator remains an operating-hours estimate per included date rather than an exact count of slots in the requested interval.
- **WSH (Wasted Seat-Hours):** nonnegative scheduled enrollment minus observed occupancy, multiplied by the observation slot duration.

A horizontal density bar summarizes aggregate SUR. It is not a geographic campus heatmap and does not locate individual rooms spatially. Values shown in the local demo reflect synthetic data, not live campus sensors.

## Forecast Explorer

1. Select **Forecast Explorer** in the sidebar.
2. Confirm forecast readiness and model status.
3. Enter a known room ID (for example, `B01-R101`).
4. Select **Generate forecast**.
5. Review predicted headcount, the fixed **1 hour** horizon, forecast target timestamp, and model version.

The current XGBoost artifact returns one point estimate. It does not provide calibrated uncertainty bounds. The dashboard does not show a capacity reference because that field is not part of the forecast response. The API constrains its prediction to known room capacity where the underlying row provides it; this does not make the prediction a calibrated capacity or safety guarantee.

## Errors and Limits

- **Room not found / insufficient history:** Check the room ID or try another known room. The API also returns 404 when a room lacks enough causal history for inference; the dashboard intentionally shows a safe, shared message.
- **Invalid request / unsupported horizon:** The supported forecast horizon is one hour; correct the input and retry.
- **Unauthorized:** Your read credential is missing or invalid; ask the technical operator.
- **Unavailable/degraded:** A required API, data, or model dependency needs operator attention.
- **Too many requests:** Wait before retrying.

The two MVP dashboard pages are Overview and Forecast Explorer. Clustering, simulation, and optimization are not presented as dashboard workflows; they are available through separate API/offline evidence paths. The system is not for individual attendance tracking, automated HVAC control, safety-critical crowd management, or real-world decision-making without local validation.
