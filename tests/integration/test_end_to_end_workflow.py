"""Representative BDS-06 workflow integration test."""

from app.analytics.metrics import calculate_utilization_metrics
from app.clustering.cluster import RoomClusterer
from app.data.cleaning import CampusDataCleaner
from app.data.harmonizer import harmonize_sources
from app.data.ingestion import ingest_dataset
from app.features.engineering import FeatureEngineer
from app.optimization.heuristics import greedy_allocate
from app.optimization.solver import optimize_allocation
from app.simulation.simulator import simulate_scenario


def test_real_repository_data_flows_through_analytics_pipeline(tmp_path):
    rooms = ingest_dataset("data/raw/rooms.csv", "rooms").dataframe
    timetable = ingest_dataset("data/raw/timetable.csv", "timetable").dataframe
    events = ingest_dataset("data/raw/events.csv", "events").dataframe
    occupancy = ingest_dataset("data/raw/occupancy.csv", "occupancy").dataframe

    cleaner = CampusDataCleaner(tmp_path / "processed")
    cleaned_rooms, _ = cleaner.clean_rooms(rooms)
    cleaned_timetable, _ = cleaner.clean_timetable(timetable, cleaned_rooms)
    cleaned_occupancy, _ = cleaner.clean_occupancy(occupancy, cleaned_rooms)
    harmonized = harmonize_sources(cleaned_occupancy, cleaned_timetable, events)

    metrics = calculate_utilization_metrics(harmonized)
    features = FeatureEngineer(forecast_horizon=1).create_features(harmonized.head(5000))
    clusters = RoomClusterer().fit_predict(harmonized)
    scenario = simulate_scenario(harmonized, occupancy_multiplier=1.1)
    baseline = greedy_allocate(cleaned_timetable, cleaned_rooms)
    optimized = optimize_allocation(cleaned_timetable, cleaned_rooms)

    assert len(harmonized) == len(cleaned_occupancy)
    assert metrics["observations"] == len(harmonized)
    assert not features.empty
    assert not clusters.assignments.empty
    assert scenario.scenario_id
    assert baseline.feasible
    assert optimized.feasible
    assert len(optimized.assignments) == len(cleaned_timetable)
