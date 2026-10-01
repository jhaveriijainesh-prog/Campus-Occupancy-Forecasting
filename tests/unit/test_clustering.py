"""Room clustering behavior tests."""

import pandas as pd
import pytest

from app.clustering.cluster import RoomClusterer, build_room_profiles


def _occupancy() -> pd.DataFrame:
    return pd.DataFrame([
        {"room_id": "R1", "capacity": 100, "actual_headcount": 10, "hour": 8},
        {"room_id": "R1", "capacity": 100, "actual_headcount": 20, "hour": 12},
        {"room_id": "R2", "capacity": 100, "actual_headcount": 90, "hour": 12},
        {"room_id": "R2", "capacity": 100, "actual_headcount": 95, "hour": 14},
        {"room_id": "R3", "capacity": 50, "actual_headcount": 25, "hour": 12},
        {"room_id": "R3", "capacity": 50, "actual_headcount": 20, "hour": 14},
    ])


def test_profiles_capture_room_behavior():
    profiles = build_room_profiles(_occupancy())

    assert set(profiles["room_id"]) == {"R1", "R2", "R3"}
    assert profiles.loc[profiles["room_id"] == "R2", "peak_utilization"].iloc[0] == 0.95
    assert "off_peak_utilization" in profiles.columns


def test_clusterer_is_deterministic_and_interpretable():
    first = RoomClusterer(min_clusters=2, max_clusters=2).fit_predict(_occupancy())
    second = RoomClusterer(min_clusters=2, max_clusters=2).fit_predict(_occupancy())

    assert first.selected_clusters == 2
    assert first.silhouette_score is not None
    assert first.assignments["cluster_id"].tolist() == second.assignments["cluster_id"].tolist()
    assert first.assignments["cluster_label"].notna().all()
    assert {"pca_x", "pca_y"}.issubset(first.assignments.columns)


def test_single_room_is_supported():
    result = RoomClusterer().fit_predict(_occupancy().iloc[[0]])

    assert result.selected_clusters == 1
    assert result.assignments.iloc[0]["cluster_label"] == "Single room"
    assert result.silhouette_score is None


def test_cluster_labels_distinguish_intermittent_peak_use_from_low_use():
    occupancy = pd.DataFrame([
        {"room_id": room_id, "capacity": 100, "actual_headcount": count, "hour": 12}
        for room_id, counts in {
            "PEAK": [0, 0, 0, 90],
            "LOW": [0, 0, 0, 10],
        }.items()
        for count in counts
    ])

    result = RoomClusterer(min_clusters=2, max_clusters=2).fit_predict(occupancy)
    labels = result.assignments.set_index("room_id")["cluster_label"]

    assert labels["PEAK"] == "Intermittent peak-use rooms"
    assert labels["LOW"] == "Underutilized rooms"


def test_empty_or_invalid_profiles_fail_explicitly():
    with pytest.raises(ValueError, match="empty"):
        RoomClusterer().fit_predict(pd.DataFrame())
    with pytest.raises(ValueError, match="clustering columns"):
        build_room_profiles(pd.DataFrame([{ "room_id": "R1" }]))
