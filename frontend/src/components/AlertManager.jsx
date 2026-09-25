import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { AlertTriangle, ShieldCheck, CheckCircle2, Bell, Clock } from 'lucide-react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

function formatTime(timestamp) {
  if (!timestamp) return 'N/A'
  return new Date(timestamp).toLocaleString()
}

function AlertManager({ refreshKey, onAlertResolved }) {
  const [alerts, setAlerts] = useState([])
  const [state, setState] = useState({ loading: true, error: '' })

  const loadAlerts = async () => {
    setState({ loading: true, error: '' })
    try {
      const response = await fetch(`${API_BASE_URL}/api/alerts`, { credentials: 'include' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to load alerts.')
      setAlerts(data.alerts || [])
      setState({ loading: false, error: '' })
    } catch (error) {
      setState({ loading: false, error: error.message || 'Unable to load alerts.' })
    }
  }

  useEffect(() => {
    loadAlerts()
  }, [refreshKey])

  const resolveAlert = async (alertId) => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/alerts/${alertId}`, {
        method: 'PATCH',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: 'Resolved' }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to resolve alert.')
      await loadAlerts()
      if (onAlertResolved) onAlertResolved()
    } catch (error) {
      setState({ loading: false, error: error.message || 'Unable to resolve alert.' })
    }
  }

  const active = alerts.filter((alert) => alert.status === 'Active')
  const resolved = alerts.filter((alert) => alert.status === 'Resolved')
  const criticalCount = active.filter((alert) => alert.condition === 'Critical').length

  const renderAlert = (alert) => {
    const isCritical = alert.condition === 'Critical'
    const isWarning = alert.condition === 'Warning'

    return (
      <motion.article
        key={alert.id}
        className={`alert-row severity-${alert.condition.toLowerCase()}`}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, scale: 0.95 }}
        transition={{ duration: 0.2 }}
      >
        <div className="alert-meta-col">
          <span className={`alert-severity condition-${alert.condition.toLowerCase()}`}>
            {alert.condition}
          </span>
          <strong>{alert.machineId || 'Unidentified Machine'}</strong>
          <small className="alert-timestamp">
            <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
            {formatTime(alert.timestamp)}
          </small>
        </div>

        <div className="alert-body-col">
          <p className="alert-message">{alert.message}</p>
          <div className="alert-metric-tag">
            <span>Model Failure Risk:</span>
            <strong>{alert.failureRisk}%</strong>
          </div>
        </div>

        <div className="alert-action-col">
          {alert.status === 'Active' ? (
            <button
              className="secondary-button resolve-btn"
              type="button"
              onClick={() => resolveAlert(alert.id)}
            >
              Resolve Alert
            </button>
          ) : (
            <small className="resolved-label">
              <CheckCircle2 size={13} style={{ display: 'inline', marginRight: '4px' }} />
              Resolved {formatTime(alert.resolvedAt)}
            </small>
          )}
        </div>
      </motion.article>
    )
  }

  return (
    <motion.section
      className="alerts-section"
      aria-labelledby="alerts-title"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header">
        <div>
          <div className="eyebrow-badge">
            <Bell size={14} />
            <span>Telemetry Diagnostics</span>
          </div>
          <h1 id="alerts-title">Safety Alert Center</h1>
          <p className="hero-subtext">
            {active.length} active alerts {criticalCount > 0 ? `· ${criticalCount} critical` : '· 0 critical'}
          </p>
        </div>
      </div>

      {state.loading && <p className="chart-empty">Loading alerts data…</p>}
      {state.error && <p className="api-error" role="alert">{state.error}</p>}

      {!state.loading && !state.error && (
        <div className="alerts-dual-column">
          <div className="alert-column">
            <h3>Active Alerts ({active.length})</h3>
            <AnimatePresence>
              {active.length ? (
                active.map(renderAlert)
              ) : (
                <div className="chart-empty">
                  <ShieldCheck size={24} style={{ display: 'block', margin: '0 auto 8px', color: '#10b981' }} />
                  <span>No active safety alerts. Fleet operating within nominal boundaries.</span>
                </div>
              )}
            </AnimatePresence>
          </div>

          <div className="alert-column">
            <h3>Resolved Event History ({resolved.length})</h3>
            {resolved.length ? (
              resolved.map(renderAlert)
            ) : (
              <p className="chart-empty">No resolved alerts recorded.</p>
            )}
          </div>
        </div>
      )}
    </motion.section>
  )
}

export default AlertManager
