# BDS-06 Final Demo Script

**Purpose:** 5–8 minute live demonstration of the verified BDS-06 campus occupancy prototype.
**Scope:** Local Docker stack, FastAPI backend, Streamlit dashboard, synthetic dataset, read-only Overview + Forecast Explorer, one-room/one-hour forecast, and honest limitations.
**Recording status:** Script only. No fabricated video or fake screen recording is claimed.

---

## 00:00–00:30 | Title / Introduction
**SCREEN:** Dashboard home / browser tab open to the app
**ACTION:** Open http://localhost:8501 and keep the app at full width. Start with the Overview page already loaded.
**SAY:**
"Good morning. I am presenting BDS-06, Campus Occupancy Forecasting with Spatiotemporal Analytics and Capacity Optimization. This project addresses a practical campus planning problem: schedules and nominal capacity do not always reflect the actual usage of rooms. We built a local decision-support prototype that helps planners inspect occupancy, review utilization, and estimate short-term room demand using a synthetic campus dataset."

---

## 00:30–01:10 | Problem and Solution
**SCREEN:** Overview page with readiness / KPI area visible
**ACTION:** Point to the main dashboard and the operational overview banner.
**SAY:**
"The core challenge is that room availability and room usage are not the same thing. A timetable may suggest a room is occupied, but the actual demand pattern can be different. Our solution combines cleaned synthetic data, utilization metrics, and a short-term forecast into a read-only dashboard and API. The aim is not production deployment; it is a controlled local prototype that demonstrates the workflow and the evidence behind it."

---

## 01:10–02:00 | System Overview
**SCREEN:** Overview page and top status panel
**ACTION:** Briefly show the API, Occupancy data, and Forecast model states, then point to the readiness summary.
**SAY:**
"The system runs as a local Docker stack with a FastAPI backend and a Streamlit dashboard. The backend provides health checks, metrics, forecast endpoints, and access control. The dashboard sits in front of that service and keeps the interaction read-only. In this demo, the key workflow is to inspect readiness, review utilization, and then request a short forecast for a selected room."

---

## 02:00–03:00 | Dashboard / Overview
**SCREEN:** Overview page with utilization cards and filters
**ACTION:** Show the scope selector and explain the dashboard metrics. Use campus scope or a known building if visible.
**SAY:**
"This is the Overview page. It shows the current operational health and the aggregate utilization picture. We focus on three main indicators: SUR, RFU, and WSH. These help a planner interpret how much of a space is being used, how intensively rooms are being used, and whether there is wasted seat-hour capacity. I am not claiming this is real campus telemetry; this is a reproducible synthetic dataset used for local validation and demonstration."

---

## 03:00–04:15 | Forecast Explorer
**SCREEN:** Forecast Explorer page
**ACTION:** Navigate to Forecast Explorer, select B01-R101, choose the supported one-hour horizon, and click Generate forecast.
**SAY:**
"Now I move to the Forecast Explorer. I am choosing room B01-R101, which is one of the verified live room examples in this project. I am using the supported forecast horizon of one hour, which matches the current served model contract. After I submit the request, the system returns the next one-hour occupancy estimate for that room."

---

## 04:15–04:55 | Forecast Result
**SCREEN:** Valid forecast result and result details
**ACTION:** Pause briefly on the forecast result and explain the value.
**SAY:**
"The forecast result for B01-R101 is a point estimate of 0.6201575398445129 for the next hour. This is a short-term planning estimate, not a multi-hour forecast and not a probabilistic uncertainty model. The important thing here is that the system demonstrates a valid one-room, one-hour forecasting flow within the verified MVP scope."

---

## 04:55–05:35 | Engineering and Security
**SCREEN:** Health/readiness endpoint or UI status panel
**ACTION:** Briefly show the health or readiness status, then explain access control.
**SAY:**
"From an engineering point of view, the API checks health and readiness before the dashboard accepts the operational state as ready. The project also includes authentication and authorization checks. Access to protected routes is gated with an API key, and invalid or unauthorized requests are handled in a controlled way rather than exposing internal details. The system also includes leakage-safe validation and temporal checks to prevent data leakage between training and evaluation."

---

## 05:35–06:10 | Testing and Reproducibility
**SCREEN:** Docker runtime and test results evidence
**ACTION:** Show Docker status or the successful local runtime evidence, then the test summary if needed.
**SAY:**
"The project is reproducible locally. The Docker stack runs successfully, and the verified test suite reported 178 passed tests with 1 warning in 53.36 seconds. This is strong evidence that the prototype is working, but it remains a local synthetic proof-of-concept rather than a public or production deployment."

---

## 06:10–06:45 | Analytics and Optimization
**SCREEN:** Explain analytically without showing a live optimizer dashboard page
**ACTION:** Mention clustering and optimization as analytical capabilities and explain the bounded evidence.
**SAY:**
"The repository also contains analytical clustering and optimization modules. Clustering groups rooms by behavior, and optimization compares a greedy baseline with a CBC MILP formulation on the same synthetic timetable. These are valuable analytical capabilities in the project, but they are not separate live dashboard pages in the current startup MVP, and the evidence remains bounded to the synthetic scenario."

---

## 06:45–07:00 | Limitations and Closing
**SCREEN:** Final conclusion / close on app and summary
**ACTION:** Return to the Overview or final closing shot.
**SAY:**
"The strongest contribution of this project is the end-to-end evidence for a local campus occupancy prototype: valid runtime, secure API access, a working dashboard, a tested one-hour forecast, and a reproducible local setup. The main limitations are also clear: the dataset is synthetic, the forecast is one-hour and point-estimate only, and there is no live campus deployment or real-world accreditation. This is a strong academic capstone prototype, and it demonstrates the engineering and data-science workflow responsibly and honestly."

---

## Final line
**SAY:**
"Thank you."

---

## Demo guidance for the presenter
- Keep the speech natural and measured.
- Do not read the report verbatim.
- Pause after the forecast result so the audience can read the number.
- Stay within the verified scope at all times.
- If a technical question exceeds the demo scope, state that it is out of the current local MVP and would require a future real-data study.
- Do not claim public hosting, live campus deployment, or one-week forecasting.
