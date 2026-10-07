import {
  ArrowRight,
  BarChart3,
  Building2,
  CalendarDays,
  CircleHelp,
  HeartPulse,
  LayoutDashboard,
  Map,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  Workflow,
} from 'lucide-react'
import { useCallback, useEffect, useState } from 'react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import {
  Link,
  Navigate,
  NavLink,
  Route,
  Routes,
  useLocation,
} from 'react-router-dom'
import { ApiError, api } from './api/client'
import type {
  ClusterResponse,
  DetailedHealthResponse,
  ForecastSchedule,
  ForecastResponse,
  HealthResponse,
  ModelInfoResponse,
  ReadinessResponse,
  ScenarioResponse,
  UtilizationResponse,
} from './types'

const CAMPUS_TIME_ZONE = 'Asia/Kolkata'
const DEMO_ROOM_ID = 'B01-R101'

function campusDateTimeParts(value: Date) {
  return new Intl.DateTimeFormat('en-CA', {
    timeZone: CAMPUS_TIME_ZONE,
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  })
    .formatToParts(value)
    .reduce<Record<string, string>>((parts, part) => {
      if (part.type !== 'literal') parts[part.type] = part.value
      return parts
    }, {})
}

function nextScheduledDemoTime(now = new Date()): string {
  const parts = campusDateTimeParts(now)
  const year = Number(parts.year)
  const month = Number(parts.month)
  const day = Number(parts.day)
  const campusDate = new Date(Date.UTC(year, month - 1, day))
  let daysUntilFriday = (5 - campusDate.getUTCDay() + 7) % 7
  if (
    daysUntilFriday === 0 &&
    (Number(parts.hour) > 9 ||
      (Number(parts.hour) === 9 && Number(parts.minute) > 0))
  ) {
    daysUntilFriday = 7
  }

  const targetDate = new Date(Date.UTC(year, month - 1, day + daysUntilFriday))
  const targetYear = targetDate.getUTCFullYear()
  const targetMonth = String(targetDate.getUTCMonth() + 1).padStart(2, '0')
  const targetDay = String(targetDate.getUTCDate()).padStart(2, '0')
  return `${targetYear}-${targetMonth}-${targetDay}T09:00`
}

function nextScheduledTime(
  schedules: ForecastSchedule[],
  roomId: string,
  now = new Date(),
): string | null {
  const parts = campusDateTimeParts(now)
  const weekdays: Record<string, number> = {
    Sunday: 0,
    Monday: 1,
    Tuesday: 2,
    Wednesday: 3,
    Thursday: 4,
    Friday: 5,
    Saturday: 6,
  }
  const currentDate = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
  )
  const currentWallClock = Date.UTC(
    Number(parts.year),
    Number(parts.month) - 1,
    Number(parts.day),
    Number(parts.hour),
    Number(parts.minute),
  )
  const options = schedules.flatMap((schedule) => {
    if (schedule.room_id !== roomId) return []
    const weekday = weekdays[schedule.day_of_week]
    const time = /^(\d{2}):(\d{2})/.exec(schedule.start_time)
    if (weekday === undefined || !time) return []

    let daysUntil = (weekday - new Date(currentDate).getUTCDay() + 7) % 7
    const [hour, minute] = time.slice(1).map(Number)
    let candidate = Date.UTC(
      Number(parts.year),
      Number(parts.month) - 1,
      Number(parts.day) + daysUntil,
      hour,
      minute,
    )
    if (candidate <= currentWallClock) {
      daysUntil += 7
      candidate = Date.UTC(
        Number(parts.year),
        Number(parts.month) - 1,
        Number(parts.day) + daysUntil,
        hour,
        minute,
      )
    }
    const targetDate = new Date(candidate)
    const targetTime = `${String(hour).padStart(2, '0')}:${String(minute).padStart(2, '0')}`
    return [
      {
        timestamp: candidate,
        value: `${targetDate.toISOString().slice(0, 10)}T${targetTime}`,
      },
    ]
  })
  return (
    options.sort((left, right) => left.timestamp - right.timestamp)[0]?.value ??
    null
  )
}

function campusDateTimeToIsoString(value: string): string {
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})$/.exec(value)
  if (!match) throw new Error('Choose a valid campus date and time.')

  const [, year, month, day, hour, minute] = match
  const wallClock = Date.UTC(
    Number(year),
    Number(month) - 1,
    Number(day),
    Number(hour),
    Number(minute),
  )
  const date = new Date(wallClock)
  if (
    date.getUTCFullYear() !== Number(year) ||
    date.getUTCMonth() !== Number(month) - 1 ||
    date.getUTCDate() !== Number(day) ||
    date.getUTCHours() !== Number(hour) ||
    date.getUTCMinutes() !== Number(minute)
  ) {
    throw new Error('Choose a valid campus date and time.')
  }

  const campusParts = campusDateTimeParts(date)
  const campusWallClock = Date.UTC(
    Number(campusParts.year),
    Number(campusParts.month) - 1,
    Number(campusParts.day),
    Number(campusParts.hour),
    Number(campusParts.minute),
  )
  return new Date(wallClock - (campusWallClock - wallClock)).toISOString()
}

function formatPercent(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return 'n/a'
  return `${(value * 100).toFixed(1)}%`
}

function formatNumber(value: number | undefined): string {
  if (value === undefined || Number.isNaN(value)) return 'n/a'
  return value.toLocaleString(undefined, { maximumFractionDigits: 1 })
}

function formatTimestamp(value?: string | null): string {
  if (!value) return 'Not available'
  const date = new Date(value)
  return Number.isNaN(date.getTime())
    ? value
    : date.toLocaleString(undefined, { timeZone: CAMPUS_TIME_ZONE })
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) return `HTTP ${error.status}: ${error.message}`
  return error instanceof Error
    ? error.message
    : 'The request could not be completed.'
}

function StatusBadge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    ready: 'Ready',
    healthy: 'Connected',
    degraded: 'Limited',
    unavailable: 'Offline',
    missing: 'Missing',
    not_ready: 'Needs attention',
    checking: 'Checking',
  }
  const palette = {
    ready: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40',
    healthy: 'bg-emerald-500/15 text-emerald-300 ring-1 ring-emerald-500/40',
    degraded: 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/40',
    unavailable: 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/40',
    missing: 'bg-rose-500/15 text-rose-200 ring-1 ring-rose-500/40',
    not_ready: 'bg-amber-500/15 text-amber-200 ring-1 ring-amber-500/40',
    default: 'bg-slate-500/15 text-slate-200 ring-1 ring-slate-500/40',
  }

  return (
    <span
      className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${palette[status as keyof typeof palette] ?? palette.default}`}
    >
      {labels[status] ?? status}
    </span>
  )
}

function Card({
  title,
  children,
  className = '',
}: {
  title: string
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={`rounded-2xl border border-slate-700/80 bg-slate-900/70 p-5 shadow-lg shadow-slate-950/20 ${className}`}
    >
      <div className="mb-4 text-sm font-medium uppercase tracking-[0.12em] text-slate-400">
        {title}
      </div>
      {children}
    </div>
  )
}

function StatCard({
  label,
  value,
  hint,
}: {
  label: string
  value: string
  hint?: string
}) {
  return (
    <div className="rounded-2xl border border-slate-700/80 bg-slate-950/60 p-4">
      <div className="text-xs uppercase tracking-[0.12em] text-slate-400">
        {label}
      </div>
      <div className="mt-3 text-2xl font-semibold text-white">{value}</div>
      {hint ? <div className="mt-2 text-xs text-slate-400">{hint}</div> : null}
    </div>
  )
}

function AppShell() {
  const location = useLocation()
  const [apiStatus, setApiStatus] = useState('checking')
  const pageTitle =
    (
      {
        '/dashboard': 'Campus overview',
        '/forecast': 'Room forecast',
        '/rooms': 'Explore rooms',
        '/optimization': 'Scenario planner',
        '/health': 'System status',
      } as Record<string, string>
    )[location.pathname] ?? 'Campus overview'

  useEffect(() => {
    let active = true
    const checkApi = () => {
      void api
        .health()
        .then((health) => {
          if (active) setApiStatus(health.status)
        })
        .catch(() => {
          if (active) setApiStatus('unavailable')
        })
    }
    checkApi()
    const interval = window.setInterval(checkApi, 30_000)

    return () => {
      active = false
      window.clearInterval(interval)
    }
  }, [])

  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/forecast', label: 'Forecast a room', icon: TrendingUp },
    { to: '/rooms', label: 'Explore rooms', icon: Building2 },
    { to: '/optimization', label: 'Try a scenario', icon: Workflow },
    { to: '/health', label: 'System status', icon: HeartPulse },
  ]

  return (
    <div className="dashboard-shell min-h-screen bg-slate-950 text-slate-100">
      <div className="flex min-h-screen">
        <aside className="hidden w-72 shrink-0 border-r border-slate-800 bg-slate-950/90 p-5 lg:flex lg:flex-col">
          <div className="mb-8 flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-300 shadow-lg shadow-cyan-950/30">
              <BarChart3 className="h-5 w-5" />
            </div>
            <div>
              <div className="text-xs uppercase tracking-[0.2em] text-cyan-300">
                BDS-06
              </div>
              <div className="text-base font-semibold leading-tight text-white">
                Campus insights
              </div>
            </div>
          </div>

          <nav className="space-y-2">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                className={({ isActive }) =>
                  `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition ${
                    isActive
                      ? 'bg-cyan-500/15 text-cyan-100 ring-1 ring-cyan-500/30'
                      : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
                  }`
                }
              >
                <Icon className="h-4 w-4" />
                {label}
              </NavLink>
            ))}
          </nav>

          <div className="mt-auto rounded-2xl border border-slate-800 bg-slate-900/80 p-4 text-sm text-slate-300">
            <div className="mb-1 flex items-center gap-2 text-xs uppercase tracking-[0.15em] text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5" />
              Demo environment
            </div>
            <div className="font-medium text-emerald-300">Demo workspace</div>
            <div className="mt-1 text-xs text-slate-400">
              Uses synthetic demonstration data
            </div>
          </div>
        </aside>

        <div className="flex min-w-0 flex-1 flex-col">
          <header className="border-b border-slate-800 bg-slate-950/80 px-4 py-4 backdrop-blur sm:px-6">
            <div className="flex items-center justify-between gap-4">
              <div>
                <div className="text-[10px] uppercase tracking-[0.18em] text-cyan-300">
                  BDS-06 · Campus insights
                </div>
                <div className="mt-1 text-xl font-semibold text-white">
                  {pageTitle}
                </div>
              </div>
              <div className="flex items-center gap-3">
                <StatusBadge status={apiStatus} />
                <div className="hidden text-xs text-slate-400 sm:block">
                  API connection
                </div>
                <Link
                  to="/"
                  className="hidden rounded-xl border border-slate-700 px-3 py-2 text-xs font-medium text-slate-300 transition hover:bg-slate-800/80 sm:inline-flex"
                >
                  Demo home
                </Link>
              </div>
            </div>
          </header>

          <nav className="mobile-nav lg:hidden" aria-label="Primary navigation">
            {navItems.map(({ to, label, icon: Icon }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/dashboard'}
                className={({ isActive }) =>
                  isActive ? 'mobile-nav-link active' : 'mobile-nav-link'
                }
              >
                <Icon aria-hidden="true" className="h-4 w-4" />
                <span>{label}</span>
              </NavLink>
            ))}
          </nav>

          <main className="mx-auto w-full max-w-[1500px] flex-1 p-4 sm:p-6">
            <Routes>
              <Route path="/dashboard" element={<OverviewPage />} />
              <Route path="/forecast" element={<ForecastPage />} />
              <Route path="/rooms" element={<RoomsPage />} />
              <Route path="/optimization" element={<OptimizationPage />} />
              <Route path="/health" element={<HealthPage />} />
              <Route path="*" element={<Navigate to="/dashboard" replace />} />
            </Routes>
          </main>
        </div>
      </div>
    </div>
  )
}

function PageIntro({
  title,
  description,
}: {
  title: string
  description: string
}) {
  return (
    <div className="mb-6">
      <h1 className="text-3xl font-semibold text-white">{title}</h1>
      <p className="mt-2 text-sm text-slate-300">{description}</p>
    </div>
  )
}

function WelcomePage() {
  return (
    <main className="welcome-screen">
      <div className="welcome-container">
        <header className="welcome-header">
          <Link
            to="/"
            className="welcome-brand"
            aria-label="Campus insights home"
          >
            <span className="welcome-brand-icon">
              <BarChart3 aria-hidden="true" />
            </span>
            <span>
              <span className="welcome-brand-kicker">BDS-06 CAPSTONE</span>
              <span className="welcome-brand-name">Campus insights</span>
            </span>
          </Link>
          <span className="demo-label">
            <span className="demo-dot" />
            Interactive demo
          </span>
        </header>

        <section className="welcome-hero">
          <div className="welcome-copy">
            <div className="welcome-eyebrow">
              <Sparkles aria-hidden="true" />A clearer view of campus space
            </div>
            <h1>
              Make every
              <br />
              campus space
              <br />
              <span>work smarter.</span>
            </h1>
            <p>
              See how rooms are used, explore upcoming occupancy, and compare
              simple planning scenarios — all in one place.
            </p>
            <Link to="/dashboard" className="welcome-primary-button">
              Open the demo workspace
              <ArrowRight aria-hidden="true" />
            </Link>
            <div className="welcome-note">
              <ShieldCheck aria-hidden="true" />
              No account needed · Synthetic demo data only
            </div>
          </div>

          <div className="welcome-preview" aria-label="Workspace preview">
            <div className="preview-topline">
              <div>
                <span className="preview-kicker">YOUR CAMPUS, AT A GLANCE</span>
                <h2>From questions to decisions</h2>
              </div>
              <span className="preview-mark">
                <Map aria-hidden="true" />
              </span>
            </div>
            <div className="preview-flow">
              <div className="preview-step">
                <span className="preview-step-number">01</span>
                <span className="preview-step-icon">
                  <LayoutDashboard aria-hidden="true" />
                </span>
                <span>
                  <strong>See the big picture</strong>
                  <small>Start with a campus snapshot</small>
                </span>
              </div>
              <div className="preview-connector" />
              <div className="preview-step">
                <span className="preview-step-number">02</span>
                <span className="preview-step-icon">
                  <CalendarDays aria-hidden="true" />
                </span>
                <span>
                  <strong>Explore what’s next</strong>
                  <small>Choose a room and forecast time</small>
                </span>
              </div>
              <div className="preview-connector" />
              <div className="preview-step">
                <span className="preview-step-number">03</span>
                <span className="preview-step-icon">
                  <Workflow aria-hidden="true" />
                </span>
                <span>
                  <strong>Compare a plan</strong>
                  <small>Change a few options, then review</small>
                </span>
              </div>
            </div>
            <div className="preview-footnote">
              <CircleHelp aria-hidden="true" />
              Every result is explained in plain language.
            </div>
          </div>
        </section>

        <section className="welcome-shortcuts">
          <div className="shortcuts-heading">
            <div>
              <span className="preview-kicker">PICK UP WHERE YOU NEED</span>
              <h2>What would you like to do?</h2>
            </div>
            <span className="shortcuts-hint">Choose one to get started</span>
          </div>
          <div className="shortcut-grid">
            <Link to="/dashboard" className="shortcut-card">
              <span className="shortcut-icon">
                <LayoutDashboard aria-hidden="true" />
              </span>
              <span>
                <strong>See the campus overview</strong>
                <small>Key space-use measures in one view</small>
              </span>
              <ArrowRight aria-hidden="true" className="shortcut-arrow" />
            </Link>
            <Link to="/forecast" className="shortcut-card">
              <span className="shortcut-icon">
                <TrendingUp aria-hidden="true" />
              </span>
              <span>
                <strong>Forecast a room</strong>
                <small>Get an occupancy estimate for a time</small>
              </span>
              <ArrowRight aria-hidden="true" className="shortcut-arrow" />
            </Link>
            <Link to="/optimization" className="shortcut-card">
              <span className="shortcut-icon">
                <Workflow aria-hidden="true" />
              </span>
              <span>
                <strong>Try a planning scenario</strong>
                <small>Compare a change with the baseline</small>
              </span>
              <ArrowRight aria-hidden="true" className="shortcut-arrow" />
            </Link>
          </div>
          <footer className="welcome-footer">
            <span>Campus Occupancy Forecasting · Capstone demonstration</span>
            <span>Synthetic data · Not live campus telemetry</span>
          </footer>
        </section>
      </div>
    </main>
  )
}

function OverviewPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [metrics, setMetrics] = useState<UtilizationResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [healthResponse, readinessResponse, utilization] =
          await Promise.all([
            api.health(),
            api.readiness(),
            api.utilization({ scope: 'campus' }),
          ])

        if (!active) return
        setHealth(healthResponse)
        setReadiness(readinessResponse)
        setMetrics(utilization)
        setError(null)
      } catch (err) {
        if (!active) return
        setError(errorMessage(err))
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [])

  if (loading) return <LoadingPanel label="Loading campus overview" />
  if (error) return <ErrorPanel message={error} />

  const utilizationData = [
    { name: 'Seat utilization', value: metrics?.metrics.seat_utilization_rate },
    { name: 'Room frequency', value: metrics?.metrics.room_frequency_of_use },
  ].filter(
    (item): item is { name: string; value: number } =>
      typeof item.value === 'number' && Number.isFinite(item.value),
  )

  return (
    <>
      <PageIntro
        title="Campus overview"
        description="A quick, clear look at how campus spaces are being used."
      />

      <div className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StatCard
          label="Seats in use"
          value={formatPercent(metrics?.metrics.seat_utilization_rate)}
          hint="of available seats"
        />
        <StatCard
          label="Room use"
          value={formatPercent(metrics?.metrics.room_frequency_of_use)}
          hint="how often rooms are used"
        />
        <StatCard
          label="Unused seat-hours"
          value={formatNumber(metrics?.metrics.wasted_seat_hours)}
          hint="available capacity not used"
        />
        <StatCard
          label="Busiest occupancy"
          value={formatNumber(metrics?.metrics.peak_occupancy)}
          hint="people"
        />
      </div>

      <div className="mb-6 grid gap-3 md:grid-cols-3">
        <Card title="Connection">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-2xl font-semibold text-white">
                {health?.status ?? 'unknown'}
              </div>
              <div className="mt-2 text-xs text-slate-400">
                {health ? formatTimestamp(health.timestamp) : 'No data'}
              </div>
            </div>
            <StatusBadge status={health?.status ?? 'default'} />
          </div>
        </Card>

        <Card title="Service readiness">
          <div className="flex items-center justify-between gap-3">
            <div>
              <div className="text-2xl font-semibold text-white">
                {readiness?.status ?? 'unknown'}
              </div>
              <div className="mt-2 text-xs text-slate-400">
                {readiness?.missing_dependencies?.length ?? 0} missing
                dependencies
              </div>
            </div>
            <StatusBadge status={readiness?.status ?? 'default'} />
          </div>
        </Card>

        <Card title="Data updated">
          <div className="text-2xl font-semibold text-white">
            {formatTimestamp(metrics?.source_timestamp)}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            {metrics?.scope ?? 'campus'} scope
          </div>
        </Card>
      </div>

      <div className="mt-6 grid gap-6 xl:grid-cols-[1.3fr_0.7fr]">
        <Card title="Campus space use">
          {utilizationData.length > 0 ? (
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={utilizationData}
                  margin={{ top: 8, right: 8, bottom: 8, left: 0 }}
                >
                  <CartesianGrid stroke="#dce4dc" strokeDasharray="3 3" />
                  <XAxis
                    dataKey="name"
                    stroke="#65756d"
                    tick={{ fontSize: 11 }}
                  />
                  <YAxis
                    domain={[0, 1]}
                    tickFormatter={(value) =>
                      `${Math.round(Number(value) * 100)}%`
                    }
                    stroke="#65756d"
                  />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: '#ffffff',
                      border: '1px solid #dce4dc',
                      borderRadius: 8,
                    }}
                    formatter={(value) => {
                      const raw = Array.isArray(value) ? value[0] : value
                      return [formatPercent(Number(raw)), 'Rate']
                    }}
                  />
                  <Bar dataKey="value" radius={[5, 5, 0, 0]} fill="#287568" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <EmptyPanel message="Utilization rates are unavailable for the selected source data." />
          )}
        </Card>

        <Card title="About this snapshot">
          <div className="space-y-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-slate-400">
                View
              </div>
              <div className="mt-1 text-lg font-medium text-white">
                {metrics?.scope ?? 'campus'}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-slate-400">
                Records analyzed
              </div>
              <div className="mt-1 text-lg font-medium text-white">
                {formatNumber(metrics?.metrics.observations)}
              </div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3">
              <div className="text-xs uppercase tracking-[0.12em] text-slate-400">
                Most recent data
              </div>
              <div className="mt-1 text-sm text-slate-200">
                {formatTimestamp(metrics?.source_timestamp)}
              </div>
            </div>
          </div>
        </Card>
      </div>
    </>
  )
}

function ForecastPage() {
  const [roomId, setRoomId] = useState(DEMO_ROOM_ID)
  const [roomOptions, setRoomOptions] = useState<string[]>([])
  const [schedules, setSchedules] = useState<ForecastSchedule[]>([])
  const [roomListError, setRoomListError] = useState<string | null>(null)
  const [scheduleNotice, setScheduleNotice] = useState<string | null>(null)
  const [forecastTime, setForecastTime] = useState(nextScheduledDemoTime)
  const [model, setModel] = useState<ModelInfoResponse | null>(null)
  const [forecast, setForecast] = useState<ForecastResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [statusLoading, setStatusLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const requestForecast = useCallback(
    async (selectedRoomId: string, selectedTime: string) => {
      if (!selectedRoomId.trim() || !selectedTime) return
      setLoading(true)
      setError(null)
      setForecast(null)
      try {
        const result = await api.forecast(
          selectedRoomId.trim(),
          campusDateTimeToIsoString(selectedTime),
          1,
        )
        setForecast(result)
      } catch (err) {
        setError(errorMessage(err))
      } finally {
        setLoading(false)
      }
    },
    [],
  )

  useEffect(() => {
    let active = true
    const load = async () => {
      const [modelResult, roomsResult, schedulesResult] =
        await Promise.allSettled([
          api.modelInfo(),
          api.clusters(),
          api.forecastSchedules(),
        ])
      if (!active) return

      if (modelResult.status === 'fulfilled') {
        setModel(modelResult.value)
      } else {
        setError(errorMessage(modelResult.reason))
      }

      let initialRoomId = DEMO_ROOM_ID
      if (roomsResult.status === 'fulfilled') {
        const roomIds = roomsResult.value.rooms.map((room) => room.room_id)
        setRoomOptions(roomIds)
        initialRoomId = roomIds.includes(DEMO_ROOM_ID)
          ? DEMO_ROOM_ID
          : (roomIds[0] ?? DEMO_ROOM_ID)
      } else {
        setRoomListError(errorMessage(roomsResult.reason))
      }

      const availableSchedules =
        schedulesResult.status === 'fulfilled' ? schedulesResult.value : []
      if (schedulesResult.status === 'fulfilled') {
        setSchedules(availableSchedules)
      } else {
        setScheduleNotice(
          'Class times could not be loaded. Choose a time manually to forecast.',
        )
      }

      const initialForecastTime =
        nextScheduledTime(availableSchedules, initialRoomId) ??
        nextScheduledDemoTime()
      setRoomId(initialRoomId)
      setForecastTime(initialForecastTime)
      await requestForecast(initialRoomId, initialForecastTime)
      if (!active) return

      setStatusLoading(false)
    }

    void load()
    return () => {
      active = false
    }
  }, [requestForecast])

  const handleForecast = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    await requestForecast(roomId, forecastTime)
  }

  const handleRoomChange = (selectedRoomId: string) => {
    setRoomId(selectedRoomId)
    setError(null)
    const selectedScheduleTime = nextScheduledTime(schedules, selectedRoomId)
    if (!selectedScheduleTime) {
      setForecast(null)
      setScheduleNotice(
        'No class time was found for this room. Choose a time to estimate occupancy; low values may be expected outside scheduled classes.',
      )
      return
    }
    setScheduleNotice(
      'Showing this room’s next scheduled class. You can choose another time above.',
    )
    setForecastTime(selectedScheduleTime)
    void requestForecast(selectedRoomId, selectedScheduleTime)
  }

  if (statusLoading) return <LoadingPanel label="Checking forecast readiness" />

  return (
    <>
      <PageIntro
        title="Forecast a room"
        description="Choose a room and the campus-local time you want to forecast."
      />

      <div className="grid gap-6 xl:grid-cols-[0.9fr_1.1fr]">
        <Card title="1. Choose what to forecast">
          <form className="space-y-4" onSubmit={handleForecast}>
            <label className="block text-sm text-slate-300">
              Room
              {roomOptions.length ? (
                <select
                  required
                  aria-label="Choose a room"
                  value={roomId}
                  disabled={loading}
                  onChange={(event) => handleRoomChange(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
                >
                  {roomOptions.map((room) => (
                    <option key={room} value={room}>
                      {room}
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  required
                  aria-label="Room ID"
                  value={roomId}
                  onChange={(event) => setRoomId(event.target.value)}
                  className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none ring-0 transition focus:border-cyan-400"
                  placeholder="For example, B01-R101"
                />
              )}
              {roomListError ? (
                <span className="mt-1 block text-xs text-slate-400">
                  Room suggestions could not load. Enter a room ID instead.
                </span>
              ) : null}
            </label>

            <label className="block text-sm text-slate-300">
              When should we estimate occupancy? (Asia/Kolkata)
              <input
                required
                type="datetime-local"
                value={forecastTime}
                disabled={loading}
                onChange={(event) => {
                  setForecastTime(event.target.value)
                  setForecast(null)
                  setError(null)
                  setScheduleNotice(
                    'Time changed. Select “Show me the estimate” to update the forecast.',
                  )
                }}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
              />
            </label>

            <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm text-slate-300">
              We’ll estimate occupancy at the selected time, using history
              available through the previous hour.{' '}
              <span className="font-semibold text-white">
                Campus time: Asia/Kolkata
              </span>
              <span className="mt-2 block text-xs text-slate-400">
                Changing rooms selects that room’s next scheduled class when
                available. Enrollment is the class size; the estimate predicts
                attendance.
              </span>
            </div>
            {scheduleNotice ? (
              <div className="text-xs text-slate-400" role="status">
                {scheduleNotice}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading || !roomId.trim() || !forecastTime}
              className="w-full rounded-xl bg-cyan-500 px-4 py-2.5 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {loading ? 'Creating estimate…' : 'Show me the estimate'}
            </button>

            {model ? (
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-xs text-slate-300">
                <div className="text-slate-400">Model</div>
                <div className="mt-1 font-medium text-white">
                  {model.model_type}
                </div>
                <div className="mt-1 text-slate-400">
                  Version: {model.version}
                </div>
              </div>
            ) : null}
          </form>
        </Card>

        <Card title="2. Review the estimate">
          {error ? (
            <ErrorPanel message={error} />
          ) : forecast ? (
            <div className="space-y-4">
              <div className="grid gap-3 sm:grid-cols-3">
                <StatCard
                  label="Predicted headcount"
                  value={formatNumber(forecast.predicted_headcount)}
                  hint="people"
                />
                <StatCard
                  label="Horizon"
                  value={`${forecast.horizon_hours}h`}
                  hint="one-hour estimate"
                />
                <StatCard
                  label="Model version"
                  value={forecast.model_version}
                  hint="point estimate"
                />
              </div>

              <div className="h-64">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart
                    data={[
                      {
                        timestamp: forecast.timestamp,
                        predicted: forecast.predicted_headcount,
                      },
                    ]}
                  >
                    <CartesianGrid stroke="#dce4dc" strokeDasharray="3 3" />
                    <XAxis
                      dataKey="timestamp"
                      stroke="#65756d"
                      tick={{ fontSize: 11, fill: '#65756d' }}
                      tickFormatter={formatTimestamp}
                    />
                    <YAxis stroke="#65756d" tick={{ fill: '#65756d' }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#ffffff',
                        border: '1px solid #dce4dc',
                        borderRadius: 8,
                      }}
                      formatter={(value) => {
                        const raw = Array.isArray(value) ? value[0] : value
                        return [Number(raw).toFixed(1), 'Forecast']
                      }}
                    />
                    <Line
                      type="monotone"
                      dataKey="predicted"
                      stroke="#287568"
                      strokeWidth={3}
                      dot={{ fill: '#287568', r: 6 }}
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>

              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-300">
                <div className="flex items-center justify-between">
                  <span>Room</span>
                  <span className="font-medium text-white">
                    {forecast.room_id}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span>Forecast target</span>
                  <span className="font-medium text-white">
                    {formatTimestamp(forecast.timestamp)}
                  </span>
                </div>
                <div className="mt-2 flex items-center justify-between">
                  <span>Prediction interval</span>
                  <span className="font-medium text-white">
                    {forecast.interval_method}
                  </span>
                </div>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm text-slate-300">
                {forecast.is_scheduled ? (
                  <>
                    <span className="font-medium text-white">
                      {forecast.scheduled_course_code
                        ? `${forecast.scheduled_course_code} class`
                        : 'Class'}{' '}
                      scheduled
                    </span>
                    {forecast.scheduled_enrollment > 0
                      ? ` · ${forecast.scheduled_enrollment} enrolled`
                      : ''}
                    . The estimate predicts attendance, which may be lower than
                    enrollment.
                  </>
                ) : (
                  <>
                    <span className="font-medium text-white">
                      No class is scheduled at this time.
                    </span>{' '}
                    A low estimate can be expected outside class hours. Choose
                    the room’s next scheduled class to see an in-class example.
                  </>
                )}
              </div>
            </div>
          ) : (
            <EmptyPanel message="Select a room and generate a forecast to see the live one-hour prediction." />
          )}
        </Card>
      </div>
    </>
  )
}

function RoomsPage() {
  const [roomId, setRoomId] = useState('B01-R101')
  const [metrics, setMetrics] = useState<UtilizationResponse | null>(null)
  const [clusters, setClusters] = useState<ClusterResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [queryLoading, setQueryLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [clusterError, setClusterError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        let initialRoomId = 'B01-R101'
        try {
          const clusterData = await api.clusters()
          if (!active) return
          setClusters(clusterData)
          initialRoomId =
            clusterData.rooms.find((room) => room.room_id === initialRoomId)
              ?.room_id ??
            clusterData.rooms[0]?.room_id ??
            initialRoomId
          setRoomId(initialRoomId)
        } catch (err) {
          if (!active) return
          setClusterError(errorMessage(err))
        }

        try {
          const roomMetrics = await api.utilization({
            scope: 'room',
            room_id: initialRoomId,
          })
          if (active) setMetrics(roomMetrics)
        } catch (err) {
          if (active) setError(errorMessage(err))
        }
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [])

  if (loading) return <LoadingPanel label="Loading room intelligence" />

  const handleRoomQuery = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (!roomId.trim()) return
    setQueryLoading(true)
    setError(null)
    try {
      const roomMetrics = await api.utilization({
        scope: 'room',
        room_id: roomId.trim(),
      })
      setMetrics(roomMetrics)
    } catch (err) {
      setMetrics(null)
      setError(errorMessage(err))
    } finally {
      setQueryLoading(false)
    }
  }

  const matchingRoom = clusters?.rooms.find(
    (room) => room.room_id === metrics?.room_id,
  )

  return (
    <>
      <PageIntro
        title="Explore a room"
        description="Choose a room to understand its use and how it compares with similar spaces."
      />

      <Card title="1. Choose a room" className="mb-6">
        <form
          className="flex flex-col gap-3 sm:flex-row sm:items-end"
          onSubmit={handleRoomQuery}
        >
          <label className="block flex-1 text-sm text-slate-300">
            Room
            {clusters?.rooms.length ? (
              <select
                required
                value={roomId}
                onChange={(event) => setRoomId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
              >
                {clusters.rooms.map((room) => (
                  <option key={room.room_id} value={room.room_id}>
                    {room.room_id}
                  </option>
                ))}
              </select>
            ) : (
              <input
                required
                value={roomId}
                onChange={(event) => setRoomId(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
                placeholder="For example, B01-R101"
              />
            )}
          </label>
          <button
            type="submit"
            disabled={queryLoading || !roomId.trim()}
            className="rounded-xl bg-cyan-500 px-5 py-2.5 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
          >
            {queryLoading ? 'Loading room…' : 'Show room details'}
          </button>
        </form>
        {clusterError ? (
          <p className="mt-3 text-xs text-amber-200">
            Room suggestions are unavailable: {clusterError}
          </p>
        ) : null}
      </Card>

      {error ? (
        <div className="mb-6">
          <ErrorPanel message={error} />
        </div>
      ) : null}
      {!metrics ? (
        <EmptyPanel message="Enter a known room ID and request its metrics." />
      ) : (
        <>
          <div className="grid gap-4 md:grid-cols-4">
            <StatCard
              label="Seats in use"
              value={formatPercent(metrics?.metrics.seat_utilization_rate)}
              hint="of available seats"
            />
            <StatCard
              label="Peak occupancy"
              value={formatNumber(metrics?.metrics.peak_occupancy)}
              hint="people"
            />
            <StatCard
              label="Room use"
              value={formatPercent(metrics?.metrics.room_frequency_of_use)}
              hint="how often this room is used"
            />
            <StatCard
              label="Unused seat-hours"
              value={formatNumber(metrics?.metrics.wasted_seat_hours)}
              hint="available capacity not used"
            />
          </div>

          <div className="mt-6 grid gap-6 xl:grid-cols-2">
            <Card title="Room details">
              <div className="space-y-3 text-sm text-slate-300">
                <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <span>Room ID</span>
                  <span className="font-medium text-white">
                    {metrics.room_id}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <span>View</span>
                  <span className="font-medium text-white">
                    {metrics?.scope ?? 'room'}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                  <span>Data updated</span>
                  <span className="font-medium text-white">
                    {formatTimestamp(metrics?.source_timestamp)}
                  </span>
                </div>
              </div>
            </Card>

            <Card title="Similar room group">
              {matchingRoom ? (
                <div className="space-y-3 text-sm text-slate-300">
                  <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <span>Assigned cluster</span>
                    <span className="font-medium text-white">
                      {matchingRoom.cluster_label ??
                        `Cluster ${matchingRoom.cluster_id}`}
                    </span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <span>Cluster ID</span>
                    <span className="font-medium text-white">
                      {matchingRoom.cluster_id}
                    </span>
                  </div>
                  <div className="flex items-center justify-between rounded-xl border border-slate-800 bg-slate-950/60 p-3">
                    <span>Feature profile</span>
                    <span className="font-medium text-white">
                      {clusters?.feature_names.length ?? 0} metrics
                    </span>
                  </div>
                </div>
              ) : (
                <EmptyPanel
                  message={
                    clusterError ??
                    'No cluster profile is available for this room.'
                  }
                />
              )}
            </Card>
          </div>
        </>
      )}
    </>
  )
}

function OptimizationPage() {
  const [clusters, setClusters] = useState<ClusterResponse | null>(null)
  const [occupancyMultiplier, setOccupancyMultiplier] = useState('1')
  const [enrollmentMultiplier, setEnrollmentMultiplier] = useState('1')
  const [closedRooms, setClosedRooms] = useState<string[]>([])
  const [result, setResult] = useState<ScenarioResponse | null>(null)
  const [loading, setLoading] = useState(false)
  const [roomsLoading, setRoomsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const loadRooms = async () => {
      try {
        const response = await api.clusters()
        if (!active) return
        setClusters(response)
      } catch (err) {
        if (!active) return
        setError(errorMessage(err))
      } finally {
        if (active) setRoomsLoading(false)
      }
    }

    void loadRooms()
    return () => {
      active = false
    }
  }, [])

  const handleScenario = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const occupancy = Number(occupancyMultiplier)
    const enrollment = Number(enrollmentMultiplier)
    if (!Number.isFinite(occupancy) || !Number.isFinite(enrollment)) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const response = await api.simulate({
        occupancy_multiplier: occupancy,
        enrollment_multiplier: enrollment,
        closed_rooms: closedRooms,
      })
      setResult(response)
    } catch (err) {
      setError(errorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const toggleClosedRoom = (roomId: string) => {
    setClosedRooms((current) =>
      current.includes(roomId)
        ? current.filter((id) => id !== roomId)
        : [...current, roomId],
    )
  }

  return (
    <>
      <PageIntro
        title="Try a planning scenario"
        description="Choose a few simple changes and compare the result with today’s baseline. Your source data will not be changed."
      />

      <div className="grid gap-6 xl:grid-cols-[0.85fr_1.15fr]">
        <Card title="1. Choose your changes">
          <form className="space-y-5" onSubmit={handleScenario}>
            <label className="block text-sm text-slate-300">
              Expected room attendance
              <span className="mt-1 block text-xs text-slate-400">
                How busy do you expect rooms to be?
              </span>
              <select
                value={occupancyMultiplier}
                onChange={(event) => setOccupancyMultiplier(event.target.value)}
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
              >
                <option value="0.8">A little quieter (20% lower)</option>
                <option value="1">About the same</option>
                <option value="1.2">A little busier (20% higher)</option>
                <option value="1.5">Much busier (50% higher)</option>
                <option value="2">Twice as busy</option>
              </select>
            </label>

            <label className="block text-sm text-slate-300">
              Student enrollment
              <span className="mt-1 block text-xs text-slate-400">
                How might student numbers change?
              </span>
              <select
                value={enrollmentMultiplier}
                onChange={(event) =>
                  setEnrollmentMultiplier(event.target.value)
                }
                className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-3 py-2.5 text-white outline-none transition focus:border-cyan-400"
              >
                <option value="0.8">A little lower (20% fewer)</option>
                <option value="1">About the same</option>
                <option value="1.2">A little higher (20% more)</option>
                <option value="1.5">Much higher (50% more)</option>
                <option value="2">Twice as many</option>
              </select>
            </label>

            <fieldset>
              <legend className="text-sm text-slate-300">
                Rooms that won’t be available (optional)
              </legend>
              <p className="mt-1 text-xs text-slate-400">
                Choose any rooms you want to leave out of this comparison.
              </p>
              <div className="mt-2 max-h-48 space-y-2 overflow-y-auto rounded-xl border border-slate-700 bg-slate-950/60 p-3">
                {roomsLoading ? (
                  <p className="text-sm text-slate-400">Loading room list…</p>
                ) : clusters?.rooms.length ? (
                  clusters.rooms.map((room) => (
                    <label
                      key={room.room_id}
                      className="flex items-center gap-2 text-sm text-slate-200"
                    >
                      <input
                        type="checkbox"
                        checked={closedRooms.includes(room.room_id)}
                        onChange={() => toggleClosedRoom(room.room_id)}
                        className="accent-cyan-400"
                      />
                      {room.room_id}
                    </label>
                  ))
                ) : (
                  <p className="text-sm text-amber-200">
                    {error ?? 'No rooms are available to select.'}
                  </p>
                )}
              </div>
            </fieldset>

            {error ? (
              <div
                role="alert"
                className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-3 text-sm text-rose-100"
              >
                {error}
              </div>
            ) : null}

            <button
              type="submit"
              disabled={loading || roomsLoading}
              className="w-full rounded-xl bg-cyan-500 px-4 py-2.5 font-medium text-slate-950 transition hover:bg-cyan-400 disabled:cursor-not-allowed disabled:bg-slate-700 disabled:text-slate-400"
            >
              {loading ? 'Comparing options…' : 'Compare this plan'}
            </button>
          </form>
        </Card>

        <Card title="2. Compare the results">
          {result ? (
            <div className="space-y-4">
              <p className="text-xs text-slate-400">
                Scenario {result.scenario_id} · compared with the same
                source-data baseline
              </p>
              <div className="overflow-x-auto">
                <table className="w-full min-w-[420px] text-left text-sm">
                  <thead className="text-xs uppercase tracking-wide text-slate-400">
                    <tr>
                      <th className="pb-3 pr-3">Measure</th>
                      <th className="pb-3 pr-3">Baseline</th>
                      <th className="pb-3 pr-3">Scenario</th>
                      <th className="pb-3">Change</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800 text-slate-200">
                    {(
                      [
                        [
                          'Seat utilization',
                          'seat_utilization_rate',
                          'percent',
                        ],
                        ['Room frequency', 'room_frequency_of_use', 'percent'],
                        ['Wasted seat-hours', 'wasted_seat_hours', 'number'],
                        ['Peak occupancy', 'peak_occupancy', 'number'],
                      ] as const
                    ).map(([label, key, format]) => {
                      const baseline = result.baseline_metrics[key]
                      const scenario = result.scenario_metrics[key]
                      const delta = result.metric_deltas[key] ?? 0
                      const display = (value: number) =>
                        format === 'percent'
                          ? formatPercent(value)
                          : formatNumber(value)
                      const change =
                        format === 'percent'
                          ? `${delta > 0 ? '+' : ''}${(delta * 100).toFixed(1)} pp`
                          : `${delta > 0 ? '+' : ''}${formatNumber(delta)}`
                      return (
                        <tr key={key}>
                          <th scope="row" className="py-3 pr-3 font-medium">
                            {label}
                          </th>
                          <td className="py-3 pr-3">{display(baseline)}</td>
                          <td className="py-3 pr-3 font-semibold text-white">
                            {display(scenario)}
                          </td>
                          <td className="py-3">{change}</td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
              <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3 text-sm text-slate-300">
                {result.scenario_metrics.observations.toLocaleString()}{' '}
                observations evaluated; {result.parameters.closed_rooms.length}{' '}
                room(s) closed.
              </div>
            </div>
          ) : (
            <EmptyPanel message="Adjust scenario assumptions and run the simulation to see measured changes against the baseline." />
          )}
        </Card>
      </div>
    </>
  )
}

function HealthPage() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [detailed, setDetailed] = useState<DetailedHealthResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const [currentHealth, currentReadiness, currentDetailed] =
          await Promise.all([
            api.health(),
            api.readiness(),
            api.detailedHealth(),
          ])

        if (!active) return
        setHealth(currentHealth)
        setReadiness(currentReadiness)
        setDetailed(currentDetailed)
      } catch (err) {
        if (!active) return
        setError(errorMessage(err))
      } finally {
        if (active) setLoading(false)
      }
    }

    void load()
    return () => {
      active = false
    }
  }, [])

  if (loading) return <LoadingPanel label="Loading health and readiness" />
  if (error) return <ErrorPanel message={error} />

  return (
    <>
      <PageIntro
        title="System Health"
        description="Real backend health and dependency state from the verified FastAPI observability endpoints."
      />

      <div className="grid gap-4 md:grid-cols-3">
        <Card title="API health">
          <div className="flex items-center justify-between">
            <div className="text-2xl font-semibold text-white">
              {health?.status ?? 'n/a'}
            </div>
            <StatusBadge status={health?.status ?? 'default'} />
          </div>
        </Card>

        <Card title="Readiness">
          <div className="flex items-center justify-between">
            <div className="text-2xl font-semibold text-white">
              {readiness?.status ?? 'n/a'}
            </div>
            <StatusBadge status={readiness?.status ?? 'default'} />
          </div>
        </Card>

        <Card title="Service version">
          <div className="text-2xl font-semibold text-white">
            {detailed?.version ?? 'n/a'}
          </div>
          <div className="mt-2 text-xs text-slate-400">
            Campus Occupancy API
          </div>
        </Card>
      </div>

      {readiness?.missing_dependencies?.length ? (
        <div className="my-6 rounded-xl border border-amber-500/30 bg-amber-500/10 p-4 text-sm text-amber-100">
          Not ready: {readiness.missing_dependencies.join(', ')}
        </div>
      ) : null}

      <div className="mt-6">
        <Card title="Dependency checks">
          {Object.keys(detailed?.checks ?? readiness?.checks ?? {}).length ? (
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
              {Object.entries(detailed?.checks ?? readiness?.checks ?? {}).map(
                ([key, value]) => (
                  <div
                    key={key}
                    className="rounded-xl border border-slate-800 bg-slate-950/60 p-3"
                  >
                    <div className="flex items-center justify-between gap-3">
                      <span className="text-sm text-slate-300">
                        {key.replaceAll('_', ' ')}
                      </span>
                      <StatusBadge status={value || 'default'} />
                    </div>
                  </div>
                ),
              )}
            </div>
          ) : (
            <EmptyPanel message="Dependency checks are not available from the health API." />
          )}
          <div className="mt-4 text-xs text-slate-400">
            Checked {formatTimestamp(health?.timestamp)}
          </div>
        </Card>
      </div>
    </>
  )
}

function LoadingPanel({ label }: { label: string }) {
  return (
    <div className="flex min-h-[40vh] items-center justify-center">
      <div className="rounded-2xl border border-slate-700 bg-slate-900 p-6 text-sm text-slate-300">
        {label}
      </div>
    </div>
  )
}

function ErrorPanel({ message }: { message: string }) {
  return (
    <Card title="Request error">
      <div className="rounded-xl border border-rose-500/30 bg-rose-500/10 p-4 text-sm text-rose-100">
        {message}
      </div>
    </Card>
  )
}

function EmptyPanel({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-dashed border-slate-700 bg-slate-950/40 p-8 text-center text-sm text-slate-300">
      {message}
    </div>
  )
}

export default function App() {
  const location = useLocation()
  return location.pathname === '/' ? <WelcomePage /> : <AppShell />
}
