# Project Title
## Campus Occupancy Forecasting
### Spatiotemporal Analytics + Capacity Optimization

### One-line summary
A modular Python capstone prototype that combines synthetic campus occupancy data, causal feature engineering, one-hour forecasting, utilization analytics, and analytical optimization evidence for a local demonstration environment.

### Technical contribution
- Built a reproducible data pipeline for validation, cleaning, and processed occupancy artifacts.
- Implemented a causal feature engineering layer with temporal leakage safeguards.
- Developed a one-hour XGBoost room forecast and a supporting API contract.
- Added utilization metrics for SUR, RFU, and WSH in a read-only dashboard workflow.
- Recorded analytical clustering and optimization evidence using synthetic scheduling scenarios.

### Achievement bullets
- Verified dashboard and leakage evidence with automated tests.
- Implemented a local Docker Compose workflow for the capstone demo environment.
- Preserved a clear boundary between the supported MVP and unsupported production claims.
- Produced evidence-backed documentation for requirements, architecture, evaluation, and security.

### Tech stack
Python, FastAPI, Streamlit, Docker Compose, Pandas, NumPy, XGBoost, PuLP, pytest.

### Architecture
Modular monolith with a FastAPI service layer, Streamlit dashboard, synthetic data/validation pipeline, analytics modules, and reproducible local deployment.

### Evaluation
Evidence includes chronological forecast evaluation, leakage regression tests, optimization comparison on a synthetic timetable, and local health/readiness validation. The project remains honest about limitations, including synthetic data and the one-hour scope.

### Reproducibility
The supported demo path is the local Docker Compose workflow. This is a local, reproducible capstone environment rather than a public deployment claim.

### Demo
The live demo highlights the Overview and Forecast Explorer pages, explains the supported one-hour forecast semantics, and distinguishes analytical optimization/clustering evidence from the current dashboard scope.

### Important limitations
- Synthetic data only
- One-hour point forecast only
- Local-only Docker demonstration
- No public deployment claim
- No real-campus operational validation
