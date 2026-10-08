export type HealthResponse = {
  status: string
  timestamp: string
  service: string
}

export type ReadinessCheckState = 'healthy' | 'degraded' | 'missing'

export type ReadinessResponse = {
  status: 'ready' | 'not_ready'
  timestamp?: string
  checks: Record<string, ReadinessCheckState>
  missing_dependencies?: string[]
}

export type DetailedHealthResponse = {
  status: 'healthy' | 'degraded'
  timestamp: string
  service: string
  version: string
  checks: Record<string, ReadinessCheckState>
  environment: string
}

export type UtilizationMetrics = {
  seat_utilization_rate: number
  room_frequency_of_use: number
  wasted_seat_hours: number
  peak_occupancy: number
  observations: number
}

export type UtilizationResponse = {
  scope: string
  room_id?: string | null
  building_id?: string | null
  metrics: UtilizationMetrics
  time_window: { start?: string | null; end?: string | null }
  source_timestamp?: string | null
}

export type ScenarioRequest = {
  occupancy_multiplier: number
  enrollment_multiplier: number
  closed_rooms: string[]
}

export type ScenarioResponse = {
  scenario_id: string
  parameters: ScenarioRequest & { capacity_adjustments: Record<string, number> }
  baseline_metrics: UtilizationMetrics
  scenario_metrics: UtilizationMetrics
  metric_deltas: Partial<UtilizationMetrics>
}

export type ForecastResponse = {
  room_id: string
  timestamp: string
  horizon_hours: number
  predicted_headcount: number
  capacity?: number | null
  is_scheduled: boolean
  scheduled_enrollment: number
  scheduled_course_code?: string | null
  prediction_interval: Record<string, number>
  confidence_levels: number[]
  interval_method: string
  horizon_semantics: string
  model_version: string
}

export type ForecastSchedule = {
  room_id: string
  day_of_week: string
  start_time: string
  end_time: string
  enrolled_count: number
  course_code?: string | null
  course_name?: string | null
}

export type ModelInfoResponse = {
  model_type: string
  version: string
  trained_at: string
  best_iteration: number | null
  feature_count: number
  top_features: Record<string, number>
  hyperparameters: Record<string, number | string>
  supported_horizon_hours: number
}

export type ClusterRoomRow = {
  room_id: string
  cluster_id: number
  cluster_label?: string
  silhouette_score?: number
  [key: string]: unknown
}

export type ClusterResponse = {
  selected_clusters: number[]
  silhouette_score?: number
  feature_names: string[]
  rooms: ClusterRoomRow[]
}

export type OptimizationResult = {
  baseline: {
    method: string
    feasible: boolean
    objective_unused_capacity: number | null
    solver_status?: string
    infeasibility_reason?: string | null
  }
  milp: {
    method: string
    feasible: boolean
    objective_unused_capacity: number | null
    runtime_seconds?: number | null
    solver_status?: string
    infeasibility_reason?: string | null
  }
}
