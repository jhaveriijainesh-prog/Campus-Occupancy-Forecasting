from app.schemas.forecast import (
    BatchForecastResponse,
    ForecastRequest,
    ForecastResponse,
    ModelInfoResponse,
)


def test_forecast_request_schema_validates_expected_contract():
    request = ForecastRequest(
        room_ids=["B01-R101"],
        horizon_hours=1,
        confidence_levels=[0.1, 0.5, 0.9],
    )

    assert request.room_ids == ["B01-R101"]
    assert request.horizon_hours == 1
    assert request.confidence_levels == [0.1, 0.5, 0.9]


def test_forecast_response_schema_supports_batch_contract():
    response = BatchForecastResponse(
        forecasts=[
            ForecastResponse(
                room_id="B01-R101",
                timestamp="2026-08-03T09:00:00Z",
                horizon_hours=1,
                predicted_headcount=20.0,
                is_scheduled=False,
                scheduled_enrollment=0,
                prediction_interval={"p10": 18.0, "p50": 20.0, "p90": 22.0},
                confidence_levels=[0.1, 0.5, 0.9],
                model_version="xgboost-v1",
            )
        ],
        generated_at="2026-08-03T09:00:00Z",
        model_version="xgboost-v1",
        total_rooms=1,
    )

    assert response.total_rooms == 1
    assert response.forecasts[0].room_id == "B01-R101"


def test_model_info_schema_has_expected_metadata_shape():
    info = ModelInfoResponse(
        model_type="XGBRegressor",
        version="1.0.0",
        trained_at="2026-08-03T00:00:00Z",
        best_iteration=42,
        feature_count=7,
        top_features={"hour": 0.4},
        hyperparameters={"max_depth": 6},
    )

    assert info.model_type == "XGBRegressor"
    assert info.feature_count == 7
