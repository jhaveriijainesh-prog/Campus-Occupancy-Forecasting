import type {
  ClusterResponse,
  DetailedHealthResponse,
  ForecastSchedule,
  ForecastResponse,
  HealthResponse,
  ModelInfoResponse,
  OptimizationResult,
  ReadinessResponse,
  ScenarioRequest,
  ScenarioResponse,
  UtilizationResponse,
} from '../types'

export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)

  const response = await fetch(path, {
    ...init,
    headers,
  })

  if (!response.ok) {
    const rawPayload = await response.text()
    let message = rawPayload || `Request failed with status ${response.status}.`
    try {
      const json = JSON.parse(rawPayload) as { detail?: unknown }
      const detail = json.detail ?? json
      message = typeof detail === 'string' ? detail : JSON.stringify(detail)
    } catch {
      // Keep the original response body when the API did not return JSON.
    }
    throw new ApiError(response.status, message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return (await response.json()) as T
}

async function readiness(): Promise<ReadinessResponse> {
  try {
    return await request<ReadinessResponse>('/api/v1/health/ready', {
      method: 'GET',
    })
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 503) throw error

    try {
      const payload = JSON.parse(error.message) as Partial<ReadinessResponse>
      if (payload.status !== 'not_ready' || !payload.checks) throw error
      return {
        status: 'not_ready',
        checks: payload.checks,
        missing_dependencies: payload.missing_dependencies ?? [],
      }
    } catch {
      throw error
    }
  }
}

export const api = {
  health: () => request<HealthResponse>('/api/v1/health', { method: 'GET' }),
  readiness,
  detailedHealth: () =>
    request<DetailedHealthResponse>('/api/v1/health/detailed', {
      method: 'GET',
    }),

  utilization: (params: Record<string, string | undefined>) => {
    const query = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value) query.set(key, value)
    })
    return request<UtilizationResponse>(
      `/api/v1/metrics/utilization?${query.toString()}`,
      { method: 'GET' },
    )
  },

  modelInfo: () =>
    request<ModelInfoResponse>('/api/v1/forecast/model/info', {
      method: 'GET',
    }),

  forecast: (roomId: string, startTime: string, horizon = 1) => {
    const params = new URLSearchParams({
      horizon_hours: String(horizon),
      start_time: startTime,
    })
    return request<ForecastResponse>(
      `/api/v1/forecast/predict/${encodeURIComponent(roomId)}?${params}`,
      { method: 'GET' },
    )
  },

  forecastSchedules: () =>
    request<ForecastSchedule[]>('/api/v1/forecast/schedules', {
      method: 'GET',
    }),

  clusters: () =>
    request<ClusterResponse>('/api/v1/clustering/rooms', { method: 'GET' }),

  simulate: (scenario: ScenarioRequest) =>
    request<ScenarioResponse>('/api/v1/simulation/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(scenario),
    }),

  optimization: () =>
    request<OptimizationResult>('/api/v1/optimize/compare', { method: 'POST' }),
}
