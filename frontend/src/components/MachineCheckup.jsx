import { useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import {
  ChevronLeft,
  Activity,
  Thermometer,
  RotateCw,
  Zap,
  Clock,
  Wrench,
  AlertTriangle,
  FileText,
  ShieldAlert,
  Cpu,
  Sliders,
} from 'lucide-react'
import CncLathe3DCanvas from './CncLathe3DCanvas.jsx'
import ExplainableAiPanel from './ExplainableAiPanel.jsx'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const POLL_INTERVAL_MS = 3000
const STALE_AFTER_MS = 15000

function formatTime(timestamp) {
  if (!timestamp) return 'Never'
  return new Date(timestamp).toLocaleTimeString()
}

function MachineCheckup({ machineId, onBack, onNavigateMaintenance }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [scenario, setScenario] = useState('normal')
  const [isUpdatingScenario, setIsUpdatingScenario] = useState(false)
  const [resolvingAlertId, setResolvingAlertId] = useState(null)
  const isMountedRef = useRef(true)

  const fetchLive = async () => {
    try {
      const response = await fetch(
        `${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}/simulation/live`,
        { credentials: 'include' }
      )
      const resData = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(resData.error || 'Failed to fetch live telemetry.')
      if (isMountedRef.current) {
        setData(resData)
        if (resData.scenario) setScenario(resData.scenario)
        setLoading(false)
        setError('')
      }
    } catch (err) {
      if (isMountedRef.current) {
        setError(err.message || 'Live telemetry connection lost.')
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    isMountedRef.current = true
    setLoading(true)
    setError('')

    // 1. Automatically start/resume simulation for this machine
    fetch(`${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}/simulation/start`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario: 'normal', type: 'M' }),
    })
      .then((res) => res.json())
      .then((initialData) => {
        if (isMountedRef.current) {
          setData(initialData)
          if (initialData.scenario) setScenario(initialData.scenario)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (isMountedRef.current) {
          setError(err.message)
          setLoading(false)
        }
      })

    // 2. Poll every 3 seconds for continuous updates
    const timer = setInterval(() => {
      if (isMountedRef.current) {
        fetchLive()
      }
    }, POLL_INTERVAL_MS)

    return () => {
      isMountedRef.current = false
      clearInterval(timer)
      // Pause simulation when unmounting to save resources
      fetch(`${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}/simulation/stop`, {
        method: 'POST',
        credentials: 'include',
      }).catch(() => {})
    }
  }, [machineId])

  const handleScenarioChange = async (newScenario) => {
    setScenario(newScenario)
    setIsUpdatingScenario(true)
    try {
      const res = await fetch(
        `${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}/simulation/scenario`,
        {
          method: 'POST',
          credentials: 'include',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ scenario: newScenario }),
        }
      )
      const updated = await res.json().catch(() => ({}))
      if (res.ok && isMountedRef.current) {
        setData(updated)
      }
    } catch (err) {
      console.error('Failed to change scenario:', err)
    } finally {
      if (isMountedRef.current) setIsUpdatingScenario(false)
    }
  }

  const resolveAlert = async (alertId) => {
    setResolvingAlertId(alertId)
    try {
      const res = await fetch(`${API_BASE_URL}/api/alerts/${alertId}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'Resolved' }),
      })
      if (res.ok) {
        await fetchLive()
      }
    } catch (err) {
      console.error('Failed to resolve alert:', err)
    } finally {
      setResolvingAlertId(null)
    }
  }

  const telemetry = data?.telemetry
  const prediction = data?.prediction
  const explanation = data?.explanation
  const recentTrend = data?.recentTrend || []
  const activeAlerts = data?.activeAlerts || []

  const lastUpdated = data?.lastUpdated
  const isStale = lastUpdated ? Date.now() - new Date(lastUpdated).getTime() > STALE_AFTER_MS : false
  const isOnline = data?.status === 'ONLINE' && !isStale

  // Trend sparkline coordinates
  const trendWidth = 540
  const trendHeight = 160
  const trendPadding = 24

  let riskPoints = ''
  let wearPoints = ''
  if (recentTrend.length >= 2) {
    riskPoints = recentTrend
      .map((item, idx) => {
        const x = trendPadding + (idx * (trendWidth - trendPadding * 2)) / (recentTrend.length - 1)
        const y = trendHeight - trendPadding - (Number(item.failureRisk || 0) * (trendHeight - trendPadding * 2)) / 100
        return `${x},${y}`
      })
      .join(' ')

    const maxWear = Math.max(...recentTrend.map((t) => Number(t.toolWear || 0)), 250)
    wearPoints = recentTrend
      .map((item, idx) => {
        const x = trendPadding + (idx * (trendWidth - trendPadding * 2)) / (recentTrend.length - 1)
        const y = trendHeight - trendPadding - (Number(item.toolWear || 0) * (trendHeight - trendPadding * 2)) / maxWear
        return `${x},${y}`
      })
      .join(' ')
  }

  return (
    <motion.div
      className="machine-checkup-view"
      aria-label={`Live checkup for ${machineId}`}
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Top Header Bar */}
      <header className="checkup-header">
        <div className="checkup-title-block">
          <button type="button" className="secondary-button back-fleet-btn" onClick={onBack}>
            <ChevronLeft size={16} />
            <span>Fleet</span>
          </button>
          <div>
            <div className="machine-id-badge-row">
              <h1 className="checkup-machine-id">{machineId}</h1>
              <span className={`status-pill ${isOnline ? 'online' : 'standby'}`}>
                <span className="pulsing-dot" />
                {isOnline ? 'ONLINE' : 'STANDBY'}
              </span>
            </div>
            <p className="checkup-meta">
              CNC Lathe Diagnostic Console · Variant {data?.type || 'M'} · Last reading: <strong>{formatTime(lastUpdated)}</strong>
            </p>
          </div>
        </div>

        {/* Operating Scenario Switcher */}
        <div className="scenario-control-box">
          <label htmlFor="scenario-select">
            <Sliders size={14} style={{ display: 'inline', marginRight: '6px' }} />
            <strong>Simulation Profile:</strong>
          </label>
          <select
            id="scenario-select"
            value={scenario}
            onChange={(e) => handleScenarioChange(e.target.value)}
            disabled={isUpdatingScenario}
          >
            <option value="normal">Normal Operation (Nominal turning)</option>
            <option value="degradation">Tool Degradation (Accelerated wear)</option>
            <option value="high_torque">High Torque (Heavy cutting load)</option>
            <option value="overheating">Thermal Overheating (Heat dissipation stress)</option>
            <option value="failure">Failure Mode (Stress combination)</option>
          </select>
          <small className="scenario-hint">
            Physics drift simulation · Scikit-learn model evaluates live output
          </small>
        </div>
      </header>

      {loading && !data && <p className="chart-empty">Connecting live telemetry stream…</p>}
      {error && <p className="api-error" role="alert">{error}</p>}

      {data && (
        <div className="checkup-content-grid">
          {/* Top Banner: 3D Twin & Diagnostic Cards */}
          <div className="checkup-top-stage">
            <div className="lathe-3d-wrapper">
              <CncLathe3DCanvas
                isSimulating={isOnline}
                condition={prediction?.condition || 'Normal'}
                rotationalSpeed={telemetry?.rotationalSpeed || 1500}
                toolWear={telemetry?.toolWear || 0}
              />
            </div>

            {/* Health & Risk Metrics */}
            <section className="checkup-summary-banner">
              <div className="condition-indicator-card">
                <span className="card-kicker">Machine Health</span>
                <strong className={`condition-big-text condition-${prediction?.condition?.toLowerCase()}`}>
                  {prediction?.condition || 'Normal'}
                </strong>
                <small>{prediction?.recommendation}</small>
              </div>

              <div className="risk-indicator-card">
                <span className="card-kicker">Model Failure Risk</span>
                <strong className="risk-big-text">{prediction?.failureRisk ?? 0}%</strong>
                <small>{prediction?.riskLabel || 'Decision support score'}</small>
              </div>

              <div className="priority-indicator-card">
                <span className="card-kicker">Maintenance Action</span>
                <strong className={`priority-text priority-${prediction?.maintenancePriority?.toLowerCase()}`}>
                  {prediction?.maintenancePriority || 'Routine'}
                </strong>
                <small>{prediction?.maintenanceDisclaimer}</small>
              </div>
            </section>
          </div>

          {/* Live Telemetry Sensors Grid */}
          <section className="dashboard-panel live-telemetry-panel" aria-labelledby="telemetry-panel-title">
            <div className="panel-header-row">
              <h2 id="telemetry-panel-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} />
                <span>Live Telemetry Sensors</span>
              </h2>
              <span className="model-tag">Physics Stream</span>
            </div>

            <div className="telemetry-metrics-grid">
              <article className="telemetry-card">
                <div className="sensor-card-title">
                  <Thermometer size={14} />
                  <span className="sensor-name">Air Temperature</span>
                </div>
                <strong className="sensor-value">{telemetry?.airTemperature ?? '--'} K</strong>
                <span className="sensor-range">Nominal: ~300.1 K</span>
              </article>

              <article className="telemetry-card">
                <div className="sensor-card-title">
                  <Thermometer size={14} />
                  <span className="sensor-name">Process Temperature</span>
                </div>
                <strong className="sensor-value">{telemetry?.processTemperature ?? '--'} K</strong>
                <span className="sensor-range">Nominal: ~310.1 K</span>
              </article>

              <article className="telemetry-card">
                <div className="sensor-card-title">
                  <RotateCw size={14} />
                  <span className="sensor-name">Spindle Speed</span>
                </div>
                <strong className="sensor-value">{telemetry?.rotationalSpeed ?? '--'} RPM</strong>
                <span className="sensor-range">Nominal: ~1,503 RPM</span>
              </article>

              <article className="telemetry-card">
                <div className="sensor-card-title">
                  <Zap size={14} />
                  <span className="sensor-name">Cutting Torque</span>
                </div>
                <strong className="sensor-value">{telemetry?.torque ?? '--'} Nm</strong>
                <span className="sensor-range">Nominal: ~40.1 Nm</span>
              </article>

              <article className="telemetry-card wear-card">
                <div className="sensor-card-title">
                  <Wrench size={14} />
                  <span className="sensor-name">Tool Wear</span>
                </div>
                <strong className="sensor-value">{telemetry?.toolWear ?? '--'} min</strong>
                <span className="sensor-range">Limit: 220 min</span>
              </article>
            </div>
          </section>

          {/* Remaining Useful Tool Life (RUTL) Panel */}
          {data?.rutl && (
            <section className="dashboard-panel rutl-panel" aria-labelledby="rutl-title">
              <div className="panel-header-row">
                <div>
                  <h2 id="rutl-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Clock size={18} />
                    <span>Remaining Useful Tool Life (RUTL)</span>
                  </h2>
                  <p className="panel-subtitle">
                    Degradation-based wear calculation · EOL Limit: {data.rutl.end_of_life_threshold} min
                  </p>
                </div>
                <span className={`rutl-condition-pill condition-${data.rutl.tool_condition.toLowerCase().replace(/[^a-z0-9]/g, '-')}`}>
                  {data.rutl.tool_condition}
                </span>
              </div>

              <div className="rutl-kpi-grid">
                <div className="rutl-kpi-card highlight-life">
                  <span className="rutl-kpi-label">Remaining Tool Life</span>
                  <strong className="rutl-kpi-value">{data.rutl.remaining_tool_life} min</strong>
                  <span className="rutl-kpi-sub">{data.rutl.remaining_tool_life_percent}% tool capacity</span>
                </div>

                <div className="rutl-kpi-card">
                  <span className="rutl-kpi-label">Est. Operating Time</span>
                  <strong className="rutl-kpi-value">~{data.rutl.estimated_remaining_minutes} min</strong>
                  <span className="rutl-kpi-sub">until 220 min limit</span>
                </div>

                <div className="rutl-kpi-card">
                  <span className="rutl-kpi-label">Current Tool Wear</span>
                  <strong className="rutl-kpi-value">{data.rutl.current_tool_wear} min</strong>
                  <span className="rutl-kpi-sub">Limit: 220 min</span>
                </div>

                <div className="rutl-kpi-card">
                  <span className="rutl-kpi-label">Estimated Wear Rate</span>
                  <strong className="rutl-kpi-value">{data.rutl.wear_rate} min/cycle</strong>
                  <span className="rutl-kpi-sub">{data.rutl.confidence}</span>
                </div>
              </div>

              {/* Tool Life Capacity Bar */}
              <div className="rutl-bar-container">
                <div className="rutl-bar-header">
                  <span>Tool Flank Wear Accumulation</span>
                  <span>{data.rutl.current_tool_wear} / {data.rutl.end_of_life_threshold} min ({Math.round(100 - data.rutl.remaining_tool_life_percent)}% consumed)</span>
                </div>
                <div className="rutl-progress-track">
                  <div
                    className={`rutl-progress-fill ${data.rutl.remaining_tool_life_percent <= 15 ? 'critical' : data.rutl.remaining_tool_life_percent <= 40 ? 'warning' : 'nominal'}`}
                    style={{ width: `${Math.min(100, Math.max(0, 100 - data.rutl.remaining_tool_life_percent))}%` }}
                  />
                  <div className="rutl-marker marker-warn" style={{ left: '63.6%' }} title="Warning wear zone (140 min)" />
                  <div className="rutl-marker marker-crit" style={{ left: '88.6%' }} title="Critical wear zone (195 min)" />
                </div>
                <div className="rutl-bar-ticks">
                  <span>0 min (New)</span>
                  <span>140 min (Warning)</span>
                  <span>195 min (Critical)</span>
                  <span>220 min (EOL Limit)</span>
                </div>
              </div>

              <div className="rutl-recommendation-box">
                <div>
                  <strong>Recommendation:</strong> {data.rutl.recommendation}
                </div>
              </div>
            </section>
          )}

          {/* Telemetry & Risk Trend */}
          <section className="dashboard-panel trend-panel" aria-labelledby="trend-title">
            <div className="panel-header-row">
              <h2 id="trend-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Activity size={18} />
                <span>Telemetry &amp; Risk Trend</span>
              </h2>
              <span className="panel-count">{recentTrend.length} readings</span>
            </div>
            {recentTrend.length < 2 ? (
              <p className="chart-empty">Accumulating stream data…</p>
            ) : (
              <div>
                <svg
                  className="risk-chart checkup-trend-chart"
                  viewBox={`0 0 ${trendWidth} ${trendHeight}`}
                  role="img"
                  aria-label="Real-time telemetry and failure risk trend"
                >
                  <line x1={trendPadding} y1={trendPadding} x2={trendPadding} y2={trendHeight - trendPadding} />
                  <line x1={trendPadding} y1={trendHeight - trendPadding} x2={trendWidth - trendPadding} y2={trendHeight - trendPadding} />
                  <text x="2" y={trendPadding + 4}>100%</text>
                  <text x="8" y={trendHeight - trendPadding}>0%</text>
                  <polyline points={riskPoints} className="trend-line-risk" />
                  <polyline points={wearPoints} className="trend-line-wear" />
                </svg>
                <div className="trend-legend">
                  <span><i className="legend-dot risk-dot" /> Failure Risk (%)</span>
                  <span><i className="legend-dot wear-dot" /> Tool Wear (min)</span>
                </div>
              </div>
            )}
          </section>

          {/* Prediction Drivers / XAI Panel */}
          <ExplainableAiPanel explanation={explanation} />

          {/* Active Safety Alerts */}
          <section className="dashboard-panel alerts-panel" aria-labelledby="alerts-machine-title">
            <div className="panel-header-row">
              <h2 id="alerts-machine-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <ShieldAlert size={18} />
                <span>Active Safety Alerts</span>
              </h2>
              <span className="panel-count">{activeAlerts.length} Active</span>
            </div>
            {activeAlerts.length === 0 ? (
              <p className="chart-empty">No active alerts for {machineId}. Standard operational range.</p>
            ) : (
              <div className="alert-list">
                {activeAlerts.map((alert) => (
                  <article key={alert.id} className="alert-row">
                    <div>
                      <span className={`alert-severity condition-${alert.condition.toLowerCase()}`}>
                        {alert.condition}
                      </span>
                      <strong>{machineId}</strong>
                      <small>{formatTime(alert.timestamp)} · {alert.failureRisk}% risk</small>
                    </div>
                    <p>{alert.message}</p>
                    <button
                      type="button"
                      className="secondary-button"
                      disabled={resolvingAlertId === alert.id}
                      onClick={() => resolveAlert(alert.id)}
                    >
                      {resolvingAlertId === alert.id ? 'Resolving…' : 'Resolve Alert'}
                    </button>
                  </article>
                ))}
              </div>
            )}
          </section>

          {/* Maintenance Actions & Reports */}
          <section className="dashboard-panel maintenance-guidance-panel" aria-labelledby="guidance-title">
            <div className="panel-header-row">
              <h2 id="guidance-title" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Wrench size={18} />
                <span>Maintenance Guidance &amp; Reports</span>
              </h2>
              <span className="model-tag">{prediction?.maintenancePriority || 'Routine'}</span>
            </div>
            <p className="panel-copy">{prediction?.recommendation}</p>
            <div className="maintenance-action-buttons">
              <button
                type="button"
                className="secondary-button"
                onClick={() => onNavigateMaintenance && onNavigateMaintenance(machineId)}
              >
                Log Maintenance Action
              </button>
              <a
                className="primary-button report-link"
                href={`${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}/report`}
                download
              >
                <FileText size={15} style={{ marginRight: '6px' }} />
                <span>Download PDF Report</span>
              </a>
            </div>
          </section>
        </div>
      )}
    </motion.div>
  )
}

export default MachineCheckup
