# Startup MVP UX Architecture

**Product:** Campus Occupancy Forecasting  
**Scope:** Read-only startup MVP  
**Primary users:** Facilities/space planner; technical operator  
**UI runtime:** Streamlit dashboard at `:8501`  
**Backend boundary:** FastAPI JSON API at `:8000`  
**Status:** UX foundation for implementation

> **Implementation status note (2026-10-01):** This file is the intended UX contract, not proof every design target was implemented or usability-tested. The current dashboard has Overview and Forecast Explorer only; the forecast control accepts one room and the supported horizon is fixed at one hour. The aggregate density bar is not a geographic heatmap. Optimizer, simulation, and clustering are API/offline capabilities, not dashboard pages. No formal user study, accessibility audit, or narrow-viewport screenshot is evidenced.

## 1. MVP UX Boundary

The MVP supports one operational question:

> What is the current utilization state of campus spaces, and what occupancy should a planner expect for a selected room over a supported forecast horizon?

The dashboard has two user-facing workflows:

1. **Overview:** confirm service readiness, inspect campus/building/room utilization, and scan occupancy density.
2. **Forecast Explorer:** choose one or more rooms, request a bounded forecast, and inspect the predicted occupancy time series with interval context.

The dashboard is read-only. It does not ingest files, retrain models, edit timetables, run optimization, run what-if simulations, expose SHAP diagnostics, or expose raw telemetry. Those capabilities remain outside the startup MVP even though placeholder view modules exist for them.

## 2. Information Architecture

### Application shell

- **Header:** product name, current page title, API status indicator, and a compact refresh action.
- **Sidebar navigation:** exactly two MVP destinations:
  - `Overview`
  - `Forecast Explorer`
- **Sidebar context:** selected building/room filters belong to the active page; do not create global filters whose meaning changes between pages.
- **Footer/status area:** data timestamp, model version when a forecast is loaded, and a link to API documentation for technical operators.

The shell must not expose `Clustering`, `Optimizer`, or `Simulation` as usable MVP pages. If these modules remain in the repository, they are implementation placeholders and should not appear in navigation.

### Overview page

1. **Readiness strip**
   - API state: `Ready`, `Degraded`, `Unavailable`, or `Unauthorized`.
   - Data state and model state shown separately when the API provides dependency checks.
   - Last successful data timestamp when available.
2. **Scope controls**
   - Scope selector: `Campus`, `Building`, `Room`.
   - Building selector enabled for building and room scope.
   - Room selector enabled for room scope.
   - Time window and supported time-of-day/day-of-week filters only when supported by the metrics contract.
3. **KPI row**
   - `SUR` (Seat Utilization Rate).
   - `RFU` (Room Fill Utilization).
   - `WSH` (Wasted Seat-Hours).
   - Each KPI includes its selected scope, time window, unit/format, and source timestamp.
4. **Occupancy density visualization**
   - A compact campus/building density view based on returned aggregate data.
   - Use a clear legend and accessible text/table summary.
   - Never render raw sensor rows or unidentified points.
5. **Context and next action**
   - A short data/model freshness line.
   - A clear action to open `Forecast Explorer` with the selected room when a room is selected.

### Forecast Explorer page

1. **Request controls**
   - Room selector using known room IDs/names from the supported API response.
   - Bounded horizon control showing only supported values.
   - Optional forecast start time only if the API supports it; otherwise use the documented default.
   - Confidence/interval display is fixed to the supported contract; do not imply configurable calibrated uncertainty unless the API guarantees it.
   - Primary action: `Generate forecast`.
2. **Request context**
   - Selected rooms, horizon, request timestamp, and API/model status.
   - Keep the current selection visible while the request is loading or fails.
3. **Forecast result**
   - Time-series chart with predicted occupancy as the primary series.
   - Prediction interval as a visually distinct band when supplied.
   - Capacity reference when room capacity is available.
   - Actual or scheduled context only when returned by the API; label each series explicitly.
   - For multiple rooms, use selectable series or small multiples rather than an unreadable combined chart.
4. **Result metadata**
   - Model version.
   - Forecast generated timestamp.
   - Forecast horizon and room ID.
   - A plain-language note that states the supported horizon semantics.
5. **Result actions**
   - Retry the same request.
   - Return to or reuse the overview selection.
   - No write, export, optimization, or retraining action in the MVP.

## 3. Primary User Flow

### Planner flow: metrics to forecast

1. Open `http://localhost:8501`.
2. Read the readiness strip before interpreting any values.
3. If ready, choose a scope and optional building/room filter.
4. Review SUR, RFU, and WSH for the selected scope and time window.
5. Scan the density visualization and its text summary.
6. Select a room, then open `Forecast Explorer`.
7. Confirm the room and choose a supported forecast horizon.
8. Select `Generate forecast`.
9. While loading, retain the request context and show progress without blanking the page.
10. Review the predicted occupancy curve, interval band, capacity reference, timestamp, and model version.
11. Adjust the room or horizon and generate another read-only forecast, or return to `Overview`.

### Technical operator flow: diagnose availability

1. Open the dashboard and inspect the readiness strip.
2. If unavailable or degraded, read the named dependency/state message.
3. Use the API docs link and `/api/v1/health` endpoint for technical verification.
4. Retry after the API/data/model dependency is restored.

### Navigation and state rules

- Preserve filter selections when moving between the two pages where the values remain valid.
- Clear dependent selections when a parent scope changes, such as clearing room when changing from room scope to campus scope.
- Never show stale chart data as current after a new request fails; label the last successful result and the new request state separately.
- Do not require a page reload to retry a failed request.

## 4. State Model

Every API-backed region must have an explicit state. States should be rendered inline in the region they describe, with a concise recovery action.

### Initial / no selection

- Overview: show readiness and prompt for a scope; show no fabricated KPI values.
- Forecast Explorer: show room and horizon controls, then an instruction to choose a room and generate a forecast.
- Do not display empty charts with axes that imply data exists.

### Loading

- Keep navigation and current controls usable.
- Show a short progress indicator with the operation, for example `Loading utilization metrics` or `Generating forecast`.
- Keep the last successful result visible only if it is clearly labeled `Last successful result` and the current request is visibly pending.
- Avoid multiple simultaneous requests from repeated clicks; disable the relevant submit action while pending.

### Success

- Render values with units, scope, time window, timestamps, and labels.
- Show a small freshness/model metadata line near the result rather than hiding provenance in a tooltip.
- Use the response as the source of truth; the dashboard must not calculate replacement business metrics from raw files.

### Empty data

- Explain the condition in user language: `No occupancy data matches this scope and time window.`
- Suggest one bounded action: broaden the time window, choose another room/building, or return to campus scope.
- Preserve the selected filters so the user can understand what produced the empty result.
- Do not display zero as a substitute for missing data.

### Validation error (HTTP 422)

- Show the invalid field and the correction required, such as unsupported horizon, malformed timestamp, or missing room.
- Keep the form values available for correction.
- Do not show a traceback or raw request payload.

### Not found (HTTP 404)

- Forecast: `Room or forecast data not found.` Offer room reselection.
- Metrics: `No matching scope was found.` Offer a broader scope or corrected filter.
- Do not imply that the room exists with zero occupancy.

### Unauthorized / forbidden (HTTP 401/403)

- Show `Access is not authorized for this read operation.`
- Do not expose API keys, headers, or server-side details.
- Preserve the page shell but disable dependent data controls until authorization is restored.

### Rate limited (HTTP 429)

- Show `Too many requests. Please wait and retry.`
- Disable immediate repeated retries and provide one retry action after the client’s configured backoff.

### Dependency unavailable (HTTP 503)

- Name the user-relevant dependency state: processed data unavailable, forecast model unavailable, or API not ready.
- For Overview, allow health/readiness retry.
- For Forecast Explorer, explain that forecast generation cannot proceed until the model/data is available.
- Never expose filesystem paths or internal exception text.

### Unexpected error / timeout

- Show `The request could not be completed.` with a retry action and correlation/request ID only if the API intentionally supplies a safe support identifier.
- Keep the rest of the dashboard usable where possible.
- Record technical detail in structured backend logs, not in the UI.

## 5. Visual Acceptance Criteria

### Information hierarchy

- A planner can identify readiness, selected scope, and the primary KPI/result within five seconds of a successful page load.
- The page title and active navigation state clearly identify `Overview` or `Forecast Explorer`.
- Primary actions are visually distinct from navigation and secondary actions.
- Deferred features are absent from the MVP navigation.

### Metrics presentation

- SUR, RFU, and WSH are presented as labeled values with consistent formatting across campus, building, and room scopes.
- Every KPI has visible scope and time context; no unlabeled number is accepted.
- Missing and zero values are visually and textually distinguishable.
- Density colors include a legend and a non-color text/table alternative; color is never the sole carrier of meaning.

### Forecast presentation

- The chart has readable time labels, a y-axis label such as `Occupancy (people)`, a legend, and a capacity reference when available.
- Point prediction and interval bounds are visually distinct, and interval bounds are ordered lower to upper.
- Room ID, horizon, generated timestamp, and model version are visible adjacent to the chart.
- The UI does not claim real-time behavior, unsupported 7-14 day accuracy, calibrated uncertainty, or capabilities not returned by the API.
- Multi-room results remain readable at the supported room count; they must not collapse into an overlapping legend or illegible line mass.

### Responsive and operational usability

- The dashboard remains usable on a narrow viewport: sidebar controls remain reachable, KPI values do not overlap, and charts can be read without horizontal page failure.
- Loading, empty, error, and success states occupy the same logical region as their content so layout does not jump unpredictably.
- Interactive controls have visible labels, keyboard-focus indication, and sufficient contrast.
- Status colors are paired with text labels or icons with accessible names.
- No raw telemetry, PII, filesystem path, secret, or traceback is visible in any state.

### Read-only and architecture compliance

- All dashboard data requests pass through `app/dashboard/api_client.py`.
- View modules do not import processed data readers, model classes, or storage paths.
- The dashboard uses the FastAPI base URL configured for local or Docker Compose execution; it does not assume a hard-coded deployment host.
- The UI exposes only read routes for health/readiness, metrics, forecast, and model information.

## 6. Implementation Handoff

### Existing module mapping

- `app/dashboard/app.py`: shell, session state, and two-page navigation.
- `app/dashboard/api_client.py`: typed calls, timeout/auth configuration, response parsing, and normalized user-safe errors.
- `app/dashboard/views/overview.py`: readiness, scope controls, KPI row, density visualization, and empty/error states.
- `app/dashboard/views/forecasting.py`: forecast controls, request lifecycle, time-series result, metadata, and forecast errors.
- `app/dashboard/views/clustering.py`, `optimizer.py`, and `simulation.py`: remain deferred and should not be added to MVP navigation.

### API dependency map

- Readiness/health/version: API health routes.
- Utilization: `GET /api/v1/metrics/utilization`.
- Forecast: `POST /api/v1/forecast/predict` or the documented single-room route.
- Model metadata: `GET /api/v1/forecast/model/info` when the result requires it.

The UX contract follows the startup task list over the broader architectural diagram where they differ. It does not expand the API, add new data sources, or change the Streamlit + FastAPI deployment topology.

## 7. MVP Review Checklist

- [ ] The first screen communicates API readiness before showing analytical conclusions.
- [ ] A planner can complete the metrics-to-forecast flow using seeded processed data.
- [ ] Campus, building, and room scopes have explicit selection and context.
- [ ] SUR, RFU, and WSH are visible and distinguishable.
- [ ] Forecast room selection, supported horizon, loading state, result, and retry path are present.
- [ ] Empty, 401/403, 404, 422, 429, 503, timeout, and unexpected error states are designed.
- [ ] Prediction intervals, capacity, model version, and generated timestamp are labeled when supplied.
- [ ] No deferred feature appears as an operational MVP workflow.
- [ ] The dashboard remains read-only and API-mediated.
- [ ] Narrow viewport, keyboard focus, contrast, and non-color status cues pass visual review.
