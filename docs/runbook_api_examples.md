# BDS-06 API Examples

These examples match the current API routes. Use `/docs` as the live OpenAPI contract. Do not paste actual API keys into reports, source files, or screenshots.

## Readiness and Metrics

Public readiness:

```http
GET /api/v1/health/ready
```

Authenticated campus metrics:

```http
GET /api/v1/metrics/utilization?scope=campus
X-API-Key: <read key>
```

Building and room scope use query parameters:

```http
GET /api/v1/metrics/utilization?scope=building&building_id=B01
GET /api/v1/metrics/utilization?scope=room&room_id=B01-R101
```

## One-Hour Forecast

```http
GET /api/v1/forecast/predict/B01-R101?horizon_hours=1
X-API-Key: <read key>
```

The current checked-in artifact supports one-hour point output. `horizon_hours=2` is rejected with HTTP 422. Unknown room IDs return HTTP 404. Model metadata is available at `GET /api/v1/forecast/model/info` with the forecast/read permission.

## Scenario Request

```http
POST /api/v1/simulation/run
Content-Type: application/json
X-API-Key: <read key>

{
  "occupancy_multiplier": 1.15,
  "enrollment_multiplier": 1.10,
  "closed_rooms": ["B01-R101"],
  "capacity_adjustments": {}
}
```

The route returns a deterministic scenario ID and aggregate baseline/scenario metric deltas. The result is a what-if perturbation, not an optimal plan.

## Allocation Comparison

```http
POST /api/v1/optimize/compare
X-API-Key: <key with optimize permission>
```

This compares `capacity_first_greedy` with `pulp_cbc_constraint_aware`. The dashboard read key is intentionally insufficient and receives 403. On the verified sample both objectives were 187, so no superiority claim is supported.
