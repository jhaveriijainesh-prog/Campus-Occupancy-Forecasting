"""Utilization metrics and API contract tests."""

from pathlib import Path

import pandas as pd
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.analytics.metrics import calculate_utilization_metrics, filter_occupancy
from app.api.main import app
from app.api.routes import forecast as forecast_route, health as health_route
from app.core.config import DEFAULT_API_READ_KEY


API_KEY = "bds06-super-secret-development-key-change-in-prod"


def test_utilization_metrics_match_hand_calculated_fixture():
    frame = pd.DataFrame(
        [
            {
                "room_id": "B01-R101",
                "capacity": 100,
                "actual_headcount": 50,
                "is_scheduled": True,
                "scheduled_enrollment": 80,
            },
            {
                "room_id": "B01-R101",
                "capacity": 100,
                "actual_headcount": 0,
                "is_scheduled": False,
                "scheduled_enrollment": 0,
            },
        ]
    )

    result = calculate_utilization_metrics(frame)

    assert result["seat_utilization_rate"] == 0.25
    assert result["room_frequency_of_use"] == 0.5
    assert result["wasted_seat_hours"] == 30.0
    assert result["peak_occupancy"] == 50.0


def test_filter_requires_identifier_for_non_campus_scope():
    frame = pd.DataFrame(
        [{
            "room_id": "B01-R101",
            "capacity": 100,
            "actual_headcount": 10,
            "is_scheduled": True,
            "scheduled_enrollment": 20,
        }]
    )

    try:
        filter_occupancy(frame, scope="room")
    except ValueError as exc:
        assert "room_id is required" in str(exc)
    else:
        raise AssertionError("room scope must require room_id")


def test_metrics_endpoint_requires_api_key():
    response = TestClient(app).get("/api/v1/metrics/utilization")

    assert response.status_code == 401


def test_metrics_and_forecast_endpoints_use_checked_in_artifacts():
    client = TestClient(app)
    headers = {"X-API-Key": API_KEY}

    metrics_response = client.get("/api/v1/metrics/utilization", headers=headers)
    forecast_response = client.get("/api/v1/forecast/predict/B01-R101", headers=headers)

    assert metrics_response.status_code == 200, metrics_response.text
    assert forecast_response.status_code == 200, forecast_response.text
    assert "seat_utilization_rate" in metrics_response.json()["metrics"]
    assert forecast_response.json()["room_id"] == "B01-R101"


def test_metrics_endpoint_supports_campus_building_and_room_scopes():
    client = TestClient(app)
    headers = {"X-API-Key": API_KEY}

    responses = []
    for params in (
        {"scope": "campus"},
        {"scope": "building", "building_id": "B01"},
        {"scope": "room", "room_id": "B01-R101"},
    ):
        response = client.get("/api/v1/metrics/utilization", headers=headers, params=params)
        assert response.status_code == 200, response.text
        assert set(response.json()["metrics"]) >= {"seat_utilization_rate", "room_frequency_of_use", "wasted_seat_hours"}
        responses.append(response.json())

    assert responses[0]["metrics"]["observations"] >= responses[1]["metrics"]["observations"]
    assert responses[1]["metrics"]["observations"] >= responses[2]["metrics"]["observations"]


def test_metrics_endpoint_rejects_unknown_identifiers_and_invalid_windows():
    client = TestClient(app)
    headers = {"X-API-Key": API_KEY}

    unknown = client.get("/api/v1/metrics/utilization", headers=headers, params={"scope": "room", "room_id": "UNKNOWN"})
    backwards = client.get(
        "/api/v1/metrics/utilization",
        headers=headers,
        params={"start_time": "2026-08-04T12:00:00Z", "end_time": "2026-08-03T12:00:00Z"},
    )

    assert unknown.status_code == 404
    assert backwards.status_code == 422

    invalid_day = client.get(
        "/api/v1/metrics/utilization",
        headers=headers,
        params={"day_of_week": "Funday"},
    )
    assert invalid_day.status_code == 422

    invalid_time_of_day = client.get(
        "/api/v1/metrics/utilization",
        headers=headers,
        params={"time_of_day": "overnight"},
    )
    assert invalid_time_of_day.status_code == 422

    contradictory_scope = client.get(
        "/api/v1/metrics/utilization",
        headers=headers,
        params={"scope": "campus", "building_id": "B01"},
    )
    assert contradictory_scope.status_code == 422


def test_metrics_response_exposes_aggregate_data_only():
    response = TestClient(app).get("/api/v1/metrics/utilization", headers={"X-API-Key": API_KEY})

    assert response.status_code == 200
    payload = response.json()
    assert "observation_id" not in payload
    assert "actual_headcount" not in payload
    assert payload["source_timestamp"].startswith("2026-")


def test_filtered_metrics_use_filtered_source_timestamp():
    response = TestClient(app).get(
        "/api/v1/metrics/utilization",
        headers={"X-API-Key": API_KEY},
        params={"end_time": "2026-08-03T00:00:00Z"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["source_timestamp"] == "2026-08-02T23:30:00Z"


def test_empty_filtered_metrics_do_not_claim_an_out_of_window_timestamp():
    response = TestClient(app).get(
        "/api/v1/metrics/utilization",
        headers={"X-API-Key": API_KEY},
        params={"start_time": "2030-01-01T00:00:00Z"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["metrics"]["observations"] == 0
    assert response.json()["source_timestamp"] is None


def test_forecast_rejects_invalid_confidence_levels():
    client = TestClient(app)
    headers = {"X-API-Key": API_KEY}

    response = client.get(
        "/api/v1/forecast/predict/B01-R101",
        headers=headers,
        params={"confidence_levels": "0.9,0.5,0.1"},
    )

    assert response.status_code == 422


def test_forecast_labels_point_estimate_interval_honestly():
    client = TestClient(app)
    response = client.get(
        "/api/v1/forecast/predict/B01-R101",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["interval_method"] == "point_estimate_only"
    assert len(set(payload["prediction_interval"].values())) == 1
    assert payload["capacity"] == 120
    assert payload["horizon_semantics"] == "one_step_ahead_hourly"
    assert payload["prediction_interval"]["p10"] <= payload["prediction_interval"]["p50"] <= payload["prediction_interval"]["p90"]
    assert 0.0 <= payload["predicted_headcount"] <= 120.0


def test_forecast_accepts_requested_target_time():
    target_time = "2026-10-07T12:00:00Z"
    response = TestClient(app).get(
        "/api/v1/forecast/predict/B01-R101",
        headers={"X-API-Key": API_KEY},
        params={"start_time": target_time},
    )

    assert response.status_code == 200, response.text
    assert response.json()["timestamp"] == "2026-10-07T12:00:00+00:00"


def test_read_only_key_can_run_what_if_scenarios():
    response = TestClient(app).post(
        "/api/v1/simulation/run",
        headers={"X-API-Key": DEFAULT_API_READ_KEY},
        json={
            "occupancy_multiplier": 1.2,
            "enrollment_multiplier": 1.1,
            "closed_rooms": ["B01-R101"],
        },
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["parameters"]["closed_rooms"] == ["B01-R101"]
    assert payload["baseline_metrics"] != payload["scenario_metrics"]
    assert "seat_utilization_rate" in payload["metric_deltas"]


def test_forecast_rejects_unsupported_artifact_horizon():
    response = TestClient(app).get(
        "/api/v1/forecast/predict/B01-R101",
        headers={"X-API-Key": API_KEY},
        params={"horizon_hours": 6},
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "less_than_equal"


def test_forecast_uses_only_causal_history_before_requested_timestamp(monkeypatch):
    timestamps = pd.date_range("2026-08-03T00:00:00Z", periods=6, freq="h")
    occupancy = pd.DataFrame({
        "room_id": ["B01-R101"] * 6,
        "timestamp": timestamps,
        "capacity": [100] * 6,
        "actual_headcount": [10, 20, 30, 40, 50, 60],
        "is_scheduled": [True] * 6,
        "scheduled_course_code": ["DS101"] * 6,
        "scheduled_enrollment": [80] * 6,
        "is_holiday": [False] * 6,
        "event_type": ["normal"] * 6,
        "is_imputed": [False] * 6,
        "was_clamped": [False] * 6,
        "room_type": ["Lecture Hall"] * 6,
        "week_number": [1] * 6,
    })
    rooms = pd.DataFrame({"room_id": ["B01-R101"], "building_id": ["B01"]})
    timetable = pd.DataFrame({
        "room_id": ["B01-R101"],
        "day_of_week": ["Monday"],
        "start_time": ["09:00:00"],
        "end_time": ["10:00:00"],
        "course_code": ["DS101"],
        "enrolled_count": [80],
        "timetable_id": ["TT-1"],
    })

    class CapturingForecaster:
        def predict(self, features):
            self.features = features.copy()
            return [25.0] * len(features)

    forecaster = CapturingForecaster()
    monkeypatch.setattr(forecast_route, "get_forecaster", lambda: forecaster)
    monkeypatch.setattr(forecast_route, "get_feature_engineer", lambda: forecast_route.FeatureEngineer(forecast_horizon=1))
    monkeypatch.setattr(
        forecast_route,
        "_read_processed_frame",
        lambda name: {
            "occupancy": occupancy,
            "rooms": rooms,
            "events": pd.DataFrame(),
            "timetable": timetable,
        }[name],
    )

    request_time = "2026-08-03T09:30:00+05:30"
    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={
            "room_ids": ["B01-R101"],
            "horizon_hours": 1,
            "start_time": request_time,
        },
    )

    assert response.status_code == 200, response.text
    assert response.json()["forecasts"][0]["timestamp"] == request_time
    assert forecaster.features["timestamp"].iloc[0] == pd.Timestamp(request_time)
    latest = forecaster.features.iloc[0]
    assert pd.isna(latest["actual_headcount"])
    assert latest["lag_1h"] == 40
    assert latest["rolling_mean_4h"] == 25.0
    assert latest["scheduled_enrollment"] == 80
    assert latest["is_scheduled"] == 1

    utc_req = "2026-08-03T04:00:00Z"
    same_instant_ist = "2026-08-03T09:30:00+05:30"
    utc_response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={
            "room_ids": ["B01-R101"],
            "horizon_hours": 1,
            "start_time": utc_req,
        },
    )
    ist_response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={
            "room_ids": ["B01-R101"],
            "horizon_hours": 1,
            "start_time": same_instant_ist,
        },
    )
    assert utc_response.status_code == 200
    assert ist_response.status_code == 200
    assert utc_response.json()["forecasts"][0]["timestamp"] == "2026-08-03T04:00:00+00:00"
    assert ist_response.json()["forecasts"][0]["timestamp"] == "2026-08-03T09:30:00+05:30"
    assert utc_response.json()["forecasts"][0]["predicted_headcount"] == ist_response.json()["forecasts"][0]["predicted_headcount"]


def test_forecast_without_history_before_target_returns_not_found(monkeypatch):
    occupancy = pd.DataFrame({
        "room_id": ["B01-R101"],
        "timestamp": ["2026-08-03T04:00:00Z"],
        "capacity": [100],
        "actual_headcount": [50],
        "is_scheduled": [True],
        "scheduled_enrollment": [80],
    })
    monkeypatch.setattr(forecast_route, "get_forecaster", lambda: object())
    monkeypatch.setattr(forecast_route, "_read_processed_frame", lambda name: {
        "occupancy": occupancy,
        "rooms": pd.DataFrame({"room_id": ["B01-R101"]}),
        "events": pd.DataFrame(),
        "timetable": pd.DataFrame({
            "room_id": [],
            "day_of_week": [],
            "start_time": [],
            "end_time": [],
        }),
    }[name])

    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={
            "room_ids": ["B01-R101"],
            "horizon_hours": 1,
            "start_time": "2026-08-03T04:00:00+05:30",
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"] == {"rooms_without_causal_history": ["B01-R101"]}


def test_forecast_feature_builder_receives_bounded_as_of_history(monkeypatch):
    timestamps = pd.date_range("2026-08-03T00:00:00Z", periods=240, freq="h")
    occupancy = pd.DataFrame({
        "observation_id": [f"OBS-{index}" for index in range(len(timestamps))],
        "room_id": ["B01-R101"] * len(timestamps),
        "timestamp": timestamps,
        "capacity": [100] * len(timestamps),
        "actual_headcount": list(range(len(timestamps))),
        "is_scheduled": [False] * len(timestamps),
        "scheduled_course_code": [None] * len(timestamps),
        "scheduled_enrollment": [0] * len(timestamps),
        "is_holiday": [False] * len(timestamps),
        "event_type": ["normal"] * len(timestamps),
        "is_imputed": [False] * len(timestamps),
        "was_clamped": [False] * len(timestamps),
        "room_type": ["Lecture Hall"] * len(timestamps),
        "week_number": [1] * len(timestamps),
    })
    rooms = pd.DataFrame({"room_id": ["B01-R101"], "building_id": ["B01"]})
    timetable = pd.DataFrame({
        "room_id": ["B01-R101"],
        "day_of_week": ["Tuesday"],
        "start_time": ["09:00:00"],
        "end_time": ["10:00:00"],
        "course_code": ["DS101"],
        "enrolled_count": [80],
        "timetable_id": ["TT-1"],
    })

    class CapturingForecaster:
        def predict(self, features):
            self.features = features.copy()
            return [17.0]

    class CapturingFeatureEngineer(forecast_route.FeatureEngineer):
        def create_features(self, occupancy_df, rooms_df=None, events_df=None):
            self.input_row_count = len(occupancy_df)
            self.input = occupancy_df.copy()
            return super().create_features(occupancy_df, rooms_df, events_df)

    forecaster = CapturingForecaster()
    feature_engineer = CapturingFeatureEngineer(forecast_horizon=1)
    monkeypatch.setattr(forecast_route, "get_forecaster", lambda: forecaster)
    monkeypatch.setattr(forecast_route, "get_feature_engineer", lambda: feature_engineer)
    monkeypatch.setattr(forecast_route, "_read_processed_frame", lambda name: {
        "occupancy": occupancy,
        "rooms": rooms,
        "events": pd.DataFrame(),
        "timetable": timetable,
    }[name])

    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={
            "room_ids": ["B01-R101"],
            "horizon_hours": 1,
            "start_time": "2026-08-11T09:00:00+05:30",
        },
    )

    assert response.status_code == 200, response.text
    assert feature_engineer.input_row_count == 169
    assert feature_engineer.input["timestamp"].max() == pd.Timestamp("2026-08-11T03:30:00Z")
    assert feature_engineer.input.iloc[-1]["actual_headcount"] != 201
    target_features = forecaster.features.iloc[0]
    assert target_features["timestamp"] == pd.Timestamp("2026-08-11T03:30:00Z")
    assert pd.isna(target_features["actual_headcount"])
    assert target_features["lag_1h"] == 194
    assert target_features["lag_168h"] == 27


@pytest.mark.parametrize(("missing_file", "missing_check"), [
    ("events.csv", "events_data"),
    ("timetable.csv", "timetable_data"),
])
def test_readiness_requires_forecast_input_artifacts(monkeypatch, tmp_path, missing_file, missing_check):
    raw_data_dir = tmp_path / "raw"
    processed_data_dir = tmp_path / "processed"
    models_dir = tmp_path / "models"
    configs_dir = tmp_path / "configs"
    experiments_dir = tmp_path / "experiments"
    for directory in (raw_data_dir, processed_data_dir, models_dir, configs_dir, experiments_dir / "xgboost"):
        directory.mkdir(parents=True)
    for artifact in ("rooms.csv", "occupancy.csv", "timetable.csv", "events.csv"):
        if artifact == missing_file:
            continue
        (processed_data_dir / artifact).touch()
    (experiments_dir / "xgboost" / "model.json").touch()
    (experiments_dir / "xgboost" / "feature_metadata.json").touch()
    settings = type("Settings", (), {
        "raw_data_dir": raw_data_dir,
        "processed_data_dir": processed_data_dir,
        "models_dir": models_dir,
        "configs_dir": configs_dir,
        "experiments_dir": experiments_dir,
    })()
    monkeypatch.setattr(health_route, "get_settings", lambda: settings)

    response = TestClient(app).get("/api/v1/health/ready")

    assert response.status_code == 503
    assert response.json()["detail"]["missing_dependencies"] == [missing_check]
    assert response.json()["detail"]["checks"][missing_check] == "missing"


def test_forecast_unknown_room_returns_not_found():
    response = TestClient(app).get(
        "/api/v1/forecast/predict/UNKNOWN",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 404


def test_forecast_batch_returns_all_requested_known_rooms():
    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={"room_ids": ["B01-R101", "B01-R102"], "horizon_hours": 1},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_rooms"] == 2
    assert {forecast["room_id"] for forecast in payload["forecasts"]} == {"B01-R101", "B01-R102"}


def test_forecast_batch_rejects_unknown_room_instead_of_dropping_it():
    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={"room_ids": ["B01-R101", "UNKNOWN"], "horizon_hours": 1},
    )

    assert response.status_code == 404
    assert response.json()["detail"]["unknown_room_ids"] == ["UNKNOWN"]


def test_model_info_reports_supported_horizon_without_filesystem_details():
    response = TestClient(app).get(
        "/api/v1/forecast/model/info",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["supported_horizon_hours"] == 1
    assert "experiments" not in response.text


def test_forecast_openapi_declares_error_contracts():
    data = TestClient(app).get("/openapi.json").json()

    assert set(data["paths"]["/api/v1/forecast/predict"]["post"]["responses"]) >= {"200", "404", "422", "503"}
    assert set(data["paths"]["/api/v1/forecast/predict/{room_id}"]["get"]["responses"]) >= {"200", "404", "422", "503"}


def test_health_openapi_declares_typed_responses_and_readiness_failure():
    data = TestClient(app).get("/openapi.json").json()
    paths = data["paths"]

    assert paths["/api/v1/health"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("HealthResponse")
    assert paths["/api/v1/health/live"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("LivenessResponse")
    assert paths["/api/v1/health/ready"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("ReadinessResponse")
    readiness_unavailable = paths["/api/v1/health/ready"]["get"]["responses"]["503"]["content"]["application/json"]["schema"]["$ref"]
    assert readiness_unavailable.endswith("ReadinessUnavailableResponse")
    assert paths["/api/v1/health/detailed"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("DetailedHealthResponse")
    assert paths["/api/v1/version"]["get"]["responses"]["200"]["content"]["application/json"]["schema"]["$ref"].endswith("VersionResponse")


def test_forecast_malformed_processed_data_returns_service_unavailable(monkeypatch):
    def malformed_frame(name):
        if name == "occupancy":
            return pd.DataFrame({"room_id": ["B01-R101"]})
        return pd.DataFrame({"room_id": ["B01-R101"]})

    monkeypatch.setattr(forecast_route, "_read_processed_frame", malformed_frame)
    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={"room_ids": ["B01-R101"], "horizon_hours": 1},
    )

    assert response.status_code == 503
    assert "required columns" in response.json()["detail"]


def test_forecast_missing_processed_data_returns_service_unavailable(monkeypatch):
    def missing_frame(name):
        if name == "occupancy":
            raise FileNotFoundError("occupancy.parquet")
        return pd.DataFrame({"room_id": ["B01-R101"]})

    monkeypatch.setattr(forecast_route, "_read_processed_frame", missing_frame)
    response = TestClient(app).post(
        "/api/v1/forecast/predict",
        headers={"X-API-Key": API_KEY},
        json={"room_ids": ["B01-R101"], "horizon_hours": 1},
    )

    assert response.status_code == 503


def test_corrupt_model_artifact_returns_service_unavailable(monkeypatch, tmp_path):
    model_dir = tmp_path / "xgboost"
    model_dir.mkdir()
    (model_dir / "model.json").write_text("not-a-model", encoding="utf-8")
    (model_dir / "feature_metadata.json").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(forecast_route, "get_settings", lambda: type("Settings", (), {"experiments_dir": tmp_path})())
    monkeypatch.setattr(forecast_route, "_forecaster", None)

    with pytest.raises(HTTPException) as error:
        forecast_route.get_forecaster()

    assert error.value.status_code == 503


def test_model_info_malformed_metadata_returns_service_unavailable(monkeypatch):
    client = TestClient(app)
    warm = client.get("/api/v1/forecast/model/info", headers={"X-API-Key": API_KEY})
    assert warm.status_code == 200, warm.text

    original_open = open

    class MalformedMetadata:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc_value, traceback):
            return False

        def read(self, *args):
            return "{ malformed"

    def fake_open(path, *args, **kwargs):
        if str(path).endswith("feature_metadata.json"):
            return MalformedMetadata()
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr("builtins.open", fake_open)
    response = client.get("/api/v1/forecast/model/info", headers={"X-API-Key": API_KEY})

    assert response.status_code == 503
    assert "metadata" in response.json()["detail"]


def test_model_info_structural_metadata_failure_returns_service_unavailable(monkeypatch):
    client = TestClient(app)
    warm = client.get("/api/v1/forecast/model/info", headers={"X-API-Key": API_KEY})
    assert warm.status_code == 200, warm.text

    original_load = forecast_route.json.load
    monkeypatch.setattr(forecast_route.json, "load", lambda file: [])
    response = client.get("/api/v1/forecast/model/info", headers={"X-API-Key": API_KEY})
    monkeypatch.setattr(forecast_route.json, "load", original_load)

    assert response.status_code == 503
    assert "JSON object" in response.json()["detail"]


def test_model_info_missing_metadata_returns_service_unavailable(monkeypatch):
    client = TestClient(app)
    monkeypatch.setattr(forecast_route, "get_settings", lambda: type("Settings", (), {"experiments_dir": Path("missing-artifacts")})())

    response = client.get("/api/v1/forecast/model/info", headers={"X-API-Key": API_KEY})

    assert response.status_code == 503
    assert "metadata" in response.json()["detail"]


def test_clustering_endpoint_returns_room_archetypes():
    response = TestClient(app).get(
        "/api/v1/clustering/rooms",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["rooms"]
    assert "cluster_label" in payload["rooms"][0]


def test_simulation_endpoint_returns_metric_deltas():
    response = TestClient(app).post(
        "/api/v1/simulation/run",
        headers={"X-API-Key": API_KEY},
        json={"occupancy_multiplier": 1.1, "closed_rooms": ["B01-R101"]},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["scenario_id"]
    assert "wasted_seat_hours" in payload["metric_deltas"]


def test_optimization_endpoint_returns_baseline_and_milp_results():
    response = TestClient(app).post(
        "/api/v1/optimize/compare",
        headers={"X-API-Key": API_KEY},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["baseline"]["method"] == "capacity_first_greedy"
    assert payload["milp"]["method"] == "pulp_cbc_constraint_aware"
    assert payload["milp"]["assignments"]


def test_ingestion_endpoint_validates_and_accepts_source_file():
    filename = "api-test-occupancy.csv"
    content = (
        "observation_id,timestamp,date,hour,day_of_week,room_id,capacity,is_scheduled,actual_headcount\n"
        "OBS-API,2026-08-03T09:00:00Z,2026-08-03,9,Monday,B01-R101,100,True,20\n"
    ).encode()
    response = TestClient(app).post(
        "/api/v1/data/ingest",
        headers={"X-API-Key": API_KEY},
        data={"dataset_name": "occupancy"},
        files={"file": (filename, content, "text/csv")},
    )
    Path("data/raw", filename).unlink(missing_ok=True)

    assert response.status_code == 200, response.text
    assert response.json()["status"] == "accepted"


def test_ingestion_endpoint_rejects_path_traversal_and_oversized_files():
    client = TestClient(app)
    headers = {"X-API-Key": API_KEY}
    traversal = client.post(
        "/api/v1/data/ingest",
        headers=headers,
        data={"dataset_name": "occupancy"},
        files={"file": ("../unsafe.csv", b"x", "text/csv")},
    )
    oversized = client.post(
        "/api/v1/data/ingest",
        headers=headers,
        data={"dataset_name": "occupancy"},
        files={"file": ("large.csv", b"x" * (10 * 1024 * 1024 + 1), "text/csv")},
    )

    assert traversal.status_code == 422
    assert oversized.status_code == 413
