import { useEffect, useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const POLL_INTERVAL_MS = 5000
const STALE_AFTER_MS = 15000

function formatValue(value, unit) { return `${Number(value).toFixed(1)} ${unit}` }

function LiveCncTelemetry() {
  const [machineId, setMachineId] = useState('CNC-LATHE-01')
  const [appliedMachineId, setAppliedMachineId] = useState('CNC-LATHE-01')
  const [state, setState] = useState({ loading: true, error: '', detail: null })

  useEffect(() => {
    let active = true
    const load = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/machines/${encodeURIComponent(appliedMachineId)}`, { credentials: 'include' })
        const data = await response.json().catch(() => ({}))
        if (response.status === 404) {
          if (active) setState({ loading: false, error: '', detail: null })
          return
        }
        if (!response.ok) throw new Error(data.error || 'Unable to load live telemetry.')
        if (active) setState({ loading: false, error: '', detail: data })
      } catch (error) {
        if (active) setState({ loading: false, error: error.message || 'Live telemetry is unavailable.', detail: null })
      }
    }
    load()
    const interval = window.setInterval(load, POLL_INTERVAL_MS)
    return () => { active = false; window.clearInterval(interval) }
  }, [appliedMachineId])

  const applyMachine = (event) => {
    event.preventDefault()
    const nextMachineId = machineId.trim()
    if (nextMachineId) { setState({ loading: true, error: '', detail: null }); setAppliedMachineId(nextMachineId) }
  }

  const latest = state.detail?.latestPrediction
  const age = latest ? Date.now() - new Date(latest.timestamp).getTime() : Infinity
  const isOnline = latest && age <= STALE_AFTER_MS

  return <section className="live-telemetry-section" aria-labelledby="live-telemetry-title">
    <div className="research-heading"><div><p className="section-kicker">Software simulated monitoring</p><h2 id="live-telemetry-title">Live CNC lathe telemetry</h2></div><span className={`telemetry-status ${isOnline ? 'online' : 'offline'}`}>{isOnline ? 'Online' : 'Offline'}</span></div>
    <p className="research-intro">Polling the latest saved simulator reading every 5 seconds. This view represents software-simulated telemetry, not a physical CNC connection.</p>
    <form className="telemetry-machine-form" onSubmit={applyMachine}><label htmlFor="live-machine-id">Machine</label><input id="live-machine-id" maxLength="100" value={machineId} onChange={(event) => setMachineId(event.target.value)} /><button className="secondary-button">View machine</button></form>
    {state.loading && <p className="chart-empty">Loading latest telemetry...</p>}
    {state.error && <p className="api-error" role="alert">{state.error}</p>}
    {!state.loading && !state.error && !latest && <p className="chart-empty">No saved reading for {appliedMachineId}. Start the CNC simulator to populate this view.</p>}
    {latest && <div className="telemetry-grid"><article><span>Air temperature</span><strong>{formatValue(latest.inputs.airTemperature, 'K')}</strong></article><article><span>Process temperature</span><strong>{formatValue(latest.inputs.processTemperature, 'K')}</strong></article><article><span>Rotational speed</span><strong>{formatValue(latest.inputs.rotationalSpeed, 'RPM')}</strong></article><article><span>Torque</span><strong>{formatValue(latest.inputs.torque, 'Nm')}</strong></article><article><span>Tool wear</span><strong>{formatValue(latest.inputs.toolWear, 'min')}</strong></article><article><span>Latest prediction</span><strong className={`telemetry-condition ${latest.condition.toLowerCase()}`}>{latest.condition} · {latest.failureRisk}%</strong><small>{new Date(latest.timestamp).toLocaleString()}</small></article></div>}
  </section>
}

export default LiveCncTelemetry
