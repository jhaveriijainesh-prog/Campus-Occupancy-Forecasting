"""Tests for forecast artifact cache invalidation."""

from types import SimpleNamespace

from app.api.routes import forecast as forecast_route


def test_processed_frame_cache_reuses_and_refreshes_changed_artifact(tmp_path, monkeypatch):
	artifact = tmp_path / "rooms.csv"
	artifact.write_text("room_id\nR1\n", encoding="utf-8")
	monkeypatch.setattr(
		forecast_route,
		"get_settings",
		lambda: SimpleNamespace(processed_data_dir=tmp_path),
	)
	read_calls = 0
	original_read_csv = forecast_route.pd.read_csv

	def counted_read_csv(*args, **kwargs):
		nonlocal read_calls
		read_calls += 1
		return original_read_csv(*args, **kwargs)

	monkeypatch.setattr(forecast_route.pd, "read_csv", counted_read_csv)
	forecast_route._load_processed_frame.cache_clear()

	first = forecast_route._read_processed_frame("rooms")
	second = forecast_route._read_processed_frame("rooms")
	assert first.equals(second)
	assert read_calls == 1

	artifact.write_text("room_id\nR1\nR2\n", encoding="utf-8")
	third = forecast_route._read_processed_frame("rooms")
	assert len(third) == 2
	assert read_calls == 2
	forecast_route._load_processed_frame.cache_clear()