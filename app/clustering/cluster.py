"""Deterministic room behavioral profiling and clustering."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler


PROFILE_COLUMNS = [
	"capacity",
	"mean_utilization",
	"peak_utilization",
	"occupancy_std",
	"off_peak_utilization",
]


@dataclass(frozen=True)
class ClusterResult:
	"""Cluster assignments, profile features, and validation metadata."""

	assignments: pd.DataFrame
	selected_clusters: int
	silhouette_score: float | None
	feature_names: tuple[str, ...]


def build_room_profiles(occupancy: pd.DataFrame) -> pd.DataFrame:
	"""Build interpretable room-level behavioral features from occupancy rows."""
	if occupancy.empty:
		raise ValueError("Cannot cluster an empty occupancy dataset")
	required = {"room_id", "capacity", "actual_headcount"}
	missing = required.difference(occupancy.columns)
	if missing:
		raise ValueError(f"Occupancy data missing clustering columns: {sorted(missing)}")

	frame = occupancy.copy()
	frame["capacity"] = pd.to_numeric(frame["capacity"], errors="coerce").clip(lower=0)
	frame["actual_headcount"] = pd.to_numeric(frame["actual_headcount"], errors="coerce").fillna(0).clip(lower=0)
	frame["utilization"] = np.divide(
		frame["actual_headcount"], frame["capacity"],
		out=np.zeros(len(frame), dtype=float), where=frame["capacity"].to_numpy() > 0,
	)
	if "hour" in frame.columns:
		hours = pd.to_numeric(frame["hour"], errors="coerce")
		frame["is_off_peak"] = ((hours < 9) | (hours >= 17)).to_numpy(dtype=bool)
	else:
		frame["is_off_peak"] = False

	profiles = frame.groupby("room_id", as_index=False).agg(
		capacity=("capacity", "max"),
		mean_utilization=("utilization", "mean"),
		peak_utilization=("utilization", "max"),
		occupancy_std=("actual_headcount", "std"),
	)
	off_peak = frame[frame["is_off_peak"]].groupby("room_id")["utilization"].mean()
	profiles["off_peak_utilization"] = profiles["room_id"].map(off_peak).fillna(0.0)
	profiles["occupancy_std"] = profiles["occupancy_std"].fillna(0.0)
	return profiles


class RoomClusterer:
	"""K-Means room archetype model with silhouette-based cluster selection."""

	def __init__(self, min_clusters: int = 2, max_clusters: int = 6, random_state: int = 42):
		if min_clusters < 1 or max_clusters < min_clusters:
			raise ValueError("cluster bounds are invalid")
		self.min_clusters = min_clusters
		self.max_clusters = max_clusters
		self.random_state = random_state
		self.scaler_: StandardScaler | None = None
		self.model_: KMeans | None = None
		self.profiles_: pd.DataFrame | None = None
		self.result_: ClusterResult | None = None

	def fit_predict(self, occupancy: pd.DataFrame) -> ClusterResult:
		profiles = build_room_profiles(occupancy)
		if len(profiles) < 2:
			assignments = profiles.assign(cluster_id=0, cluster_label="Single room", pca_x=0.0, pca_y=0.0)
			self.profiles_ = profiles
			self.result_ = ClusterResult(assignments, 1, None, tuple(PROFILE_COLUMNS))
			return self.result_

		features = profiles[PROFILE_COLUMNS].to_numpy(dtype=float)
		self.scaler_ = StandardScaler().fit(features)
		scaled = self.scaler_.transform(features)
		max_clusters = min(self.max_clusters, len(profiles))
		candidates = range(self.min_clusters, max_clusters + 1)
		if not list(candidates):
			raise ValueError("Not enough rooms for the configured cluster range")

		scores: dict[int, float] = {}
		for count in candidates:
			model = KMeans(n_clusters=count, random_state=self.random_state, n_init=10)
			labels = model.fit_predict(scaled)
			if count >= len(scaled):
				scores[count] = 0.0
			else:
				scores[count] = float(silhouette_score(scaled, labels))
		selected = max(scores, key=scores.get)
		self.model_ = KMeans(n_clusters=selected, random_state=self.random_state, n_init=10).fit(scaled)
		projection = PCA(n_components=2, random_state=self.random_state).fit_transform(scaled)
		assignments = profiles.assign(
			cluster_id=self.model_.labels_,
			pca_x=projection[:, 0],
			pca_y=projection[:, 1],
		)
		labels = assignments.groupby("cluster_id")["mean_utilization"].transform("mean")
		peak_labels = assignments.groupby("cluster_id")["peak_utilization"].transform("mean")
		assignments["cluster_label"] = np.select(
			[labels >= 0.85, labels >= 0.30, peak_labels >= 0.85],
			["High-demand rooms", "Balanced rooms", "Intermittent peak-use rooms"],
			default="Underutilized rooms",
		)
		self.profiles_ = profiles
		self.result_ = ClusterResult(assignments, selected, scores[selected], tuple(PROFILE_COLUMNS))
		return self.result_
