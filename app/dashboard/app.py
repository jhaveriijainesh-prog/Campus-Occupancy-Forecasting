"""Streamlit stakeholder dashboard for the BDS-06 read workflow."""

import os
import sys
from pathlib import Path

# Streamlit places this file's directory first, where app.py can shadow the app package.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) in sys.path:
	sys.path.remove(str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT))

import streamlit as st

from app.core.config import get_settings
from app.dashboard.api_client import APIClient
from app.dashboard.views.overview import show_overview
from app.dashboard.views.forecasting import show_forecast


def build_api_client() -> APIClient:
	"""Build the dashboard gateway from local or Compose environment configuration."""
	settings = get_settings()
	base_url = (
		os.getenv("FASTAPI_PUBLIC_URL")
		or os.getenv("FASTAPI_INTERNAL_URL")
		or settings.fastapi_public_url
	)
	return APIClient(
		base_url,
		os.getenv("FASTAPI_API_KEY") or settings.api_read_key,
		settings.dashboard_api_timeout_seconds,
	)


@st.cache_resource
def get_client() -> APIClient:
	return build_api_client()


def show_analysis(client: APIClient) -> None:
	st.subheader("Room archetypes")
	clusters = client.clusters()
	st.caption(f"Selected clusters: {clusters['selected_clusters']}")
	st.dataframe(clusters["rooms"], use_container_width=True)


def show_scenarios(client: APIClient) -> None:
	st.subheader("What-if scenario")
	multiplier = st.slider("Occupancy multiplier", 0.5, 2.0, 1.0, 0.05)
	room_id = st.text_input("Room to close", value="")
	if st.button("Run scenario"):
		result = client.scenario(occupancy_multiplier=multiplier, closed_rooms=[room_id] if room_id else [])
		st.json({"parameters": result["parameters"], "metric_deltas": result["metric_deltas"]})


def show_optimization(client: APIClient) -> None:
	st.subheader("Allocation comparison")
	if st.button("Run comparison"):
		result = client.optimization_comparison()
		st.json({
			"baseline": {key: result["baseline"][key] for key in ("method", "feasible", "objective_unused_capacity")},
			"milp": {key: result["milp"][key] for key in ("method", "feasible", "objective_unused_capacity", "runtime_seconds")},
		})


def main() -> None:
	st.set_page_config(page_title="Campus Operations", layout="wide")
	st.markdown(
		"""
		<div style="padding: 1.25rem 1.5rem; border-radius: 1rem; background: linear-gradient(135deg, #0b3d66 0%, #167D83 100%); color: white; margin-bottom: 1rem;">
			<h1 style="margin: 0; font-size: 2rem;">Campus Operations</h1>
			<p style="margin: 0.35rem 0 0; color: rgba(255,255,255,0.82);">Occupancy readiness, space utilization, and one-hour planning.</p>
		</div>
		""",
		unsafe_allow_html=True,
	)
	st.sidebar.title("Campus Operations")
	st.sidebar.caption("Live campus decision support")
	client = get_client()
	page = st.sidebar.radio("View", ["Overview", "Forecast Explorer"], key="dashboard_page")
	if page == "Overview":
		show_overview(client)
	else:
		show_forecast(client)


if __name__ == "__main__":
	main()
