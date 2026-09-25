import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Wrench, FileText, Calendar, PlusCircle, CheckCircle2 } from 'lucide-react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const EMPTY_FORM = { machineId: '', maintenanceDate: '', maintenanceType: 'Inspection', issue: '', actionTaken: '', notes: '' }

function MaintenanceManager({ machines, initialMachineId }) {
  const [selectedMachine, setSelectedMachine] = useState(initialMachineId || '')
  const [detail, setDetail] = useState(null)
  const [state, setState] = useState({ loading: false, error: '', success: '' })
  const [form, setForm] = useState(EMPTY_FORM)

  const loadDetail = async (machineId) => {
    if (!machineId) { setDetail(null); return }
    setState({ loading: true, error: '', success: '' })
    try {
      const response = await fetch(`${API_BASE_URL}/api/machines/${encodeURIComponent(machineId)}`, { credentials: 'include' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to load machine details.')
      setDetail(data)
      setForm((current) => ({ ...current, machineId }))
      setState({ loading: false, error: '', success: '' })
    } catch (error) { setState({ loading: false, error: error.message, success: '' }) }
  }

  useEffect(() => {
    const target = initialMachineId || (machines.length ? machines[0].machineId : '')
    if (target && target !== selectedMachine) {
      setSelectedMachine(target)
      loadDetail(target)
    }
  }, [machines, initialMachineId])

  const changeMachine = (event) => { setSelectedMachine(event.target.value); loadDetail(event.target.value) }
  const handleChange = ({ target: { name, value } }) => setForm((current) => ({ ...current, [name]: value }))
  const submit = async (event) => {
    event.preventDefault()
    setState({ loading: true, error: '', success: '' })
    try {
      const response = await fetch(`${API_BASE_URL}/api/maintenance`, { method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form) })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to save maintenance record.')
      setForm((current) => ({ ...EMPTY_FORM, machineId: current.machineId, maintenanceType: 'Inspection' }))
      await loadDetail(selectedMachine)
      setState({ loading: false, error: '', success: 'Maintenance record saved.' })
    } catch (error) { setState({ loading: false, error: error.message, success: '' }) }
  }

  return (
    <section className="maintenance-section" aria-labelledby="maintenance-title">
      <div className="panel-header-row">
        <div>
          <h2 id="maintenance-title">Machine Maintenance Records</h2>
          <p className="panel-subtitle">Deterministically priority-guided maintenance actions</p>
        </div>
      </div>
      
      {machines.length === 0 ? (
        <p className="chart-empty">No machines found in database.</p>
      ) : (
        <>
          <label className="machine-select-label" htmlFor="maintenance-machine">Select Machine:</label>
          <select id="maintenance-machine" value={selectedMachine} onChange={changeMachine}>
            {machines.map((machine) => <option key={machine.machineId} value={machine.machineId}>{machine.machineId}</option>)}
          </select>
          {state.loading && <p className="chart-empty">Loading machine details…</p>}
          {state.error && <p className="api-error" role="alert">{state.error}</p>}
          {detail && (
            <div className="maintenance-grid">
              <article className="machine-detail-card">
                <h3>Current Status</h3>
                <div className={`history-condition ${detail.latestPrediction.condition.toLowerCase()}`}>{detail.latestPrediction.condition}</div>
                <strong>{detail.latestPrediction.failureRisk}% Risk Score</strong>
                <p><b>Priority:</b> {detail.latestPrediction.maintenancePriority}</p>
                <p>{detail.latestPrediction.recommendation}</p>
                <small>{detail.latestPrediction.maintenanceDisclaimer}</small>
                <h3>Engineering Report</h3>
                <p>{new Date(detail.latestPrediction.timestamp).toLocaleString()}</p>
                <a className="primary-button report-link" href={`${API_BASE_URL}/api/machines/${encodeURIComponent(selectedMachine)}/report`} download>
                  <FileText size={14} style={{ marginRight: '6px' }} />
                  <span>Download PDF Report</span>
                </a>
              </article>

              <article className="maintenance-history">
                <h3>Log History</h3>
                {detail.maintenanceRecords.length === 0 ? (
                  <p className="chart-empty">No maintenance records logged for this machine.</p>
                ) : (
                  detail.maintenanceRecords.map((record) => (
                    <div key={record.id} className="maintenance-history-item">
                      <strong>{record.maintenanceDate} · {record.maintenanceType}</strong>
                      <p>{record.issue}</p>
                      <small>{record.actionTaken || 'No action recorded'}{record.notes ? ` — ${record.notes}` : ''}</small>
                    </div>
                  ))
                )}
              </article>

              <form className="maintenance-form" onSubmit={submit}>
                <h3>
                  <PlusCircle size={16} style={{ display: 'inline', marginRight: '6px' }} />
                  <span>Add Maintenance Record</span>
                </h3>
                <label>Date<input required type="date" name="maintenanceDate" value={form.maintenanceDate} onChange={handleChange} /></label>
                <label>Type
                  <select name="maintenanceType" value={form.maintenanceType} onChange={handleChange}>
                    <option>Inspection</option>
                    <option>Preventive</option>
                    <option>Corrective</option>
                  </select>
                </label>
                <label>Issue<textarea required name="issue" maxLength="500" value={form.issue} onChange={handleChange} /></label>
                <label>Action Taken<textarea name="actionTaken" maxLength="500" value={form.actionTaken} onChange={handleChange} /></label>
                <label>Notes<textarea name="notes" maxLength="1000" value={form.notes} onChange={handleChange} /></label>
                {state.success && (
                  <p className="maintenance-success">
                    <CheckCircle2 size={14} style={{ display: 'inline', marginRight: '4px' }} />
                    {state.success}
                  </p>
                )}
                <button className="primary-button" disabled={state.loading}>Save Record</button>
              </form>
            </div>
          )}
        </>
      )}
    </section>
  )
}

export default MaintenanceManager
