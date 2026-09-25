import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { FileText, Download, CheckCircle2 } from 'lucide-react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

function ReportsPage({ machines, initialMachineId }) {
  const [selectedMachine, setSelectedMachine] = useState(initialMachineId || '')
  const [machineData, setMachineData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (machines.length && !selectedMachine) {
      setSelectedMachine(machines[0].machineId)
    }
  }, [machines, selectedMachine])

  useEffect(() => {
    if (!selectedMachine) return
    let active = true
    setLoading(true)
    setError('')

    fetch(`${API_BASE_URL}/api/machines/${encodeURIComponent(selectedMachine)}`, { credentials: 'include' })
      .then((res) => {
        if (!res.ok) throw new Error('Failed to load machine summary for report.')
        return res.json()
      })
      .then((data) => {
        if (active) {
          setMachineData(data)
          setLoading(false)
        }
      })
      .catch((err) => {
        if (active) {
          setError(err.message)
          setLoading(false)
        }
      })

    return () => {
      active = false
    }
  }, [selectedMachine])

  return (
    <motion.div
      className="page-container reports-page"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header">
        <div>
          <div className="eyebrow-badge">
            <FileText size={14} />
            <span>Compliance & Audits</span>
          </div>
          <h1>Engineering PDF Reports</h1>
          <p className="hero-subtext">
            Export machine diagnostics, telemetry logs, and maintenance history.
          </p>
        </div>
      </div>

      <section className="reports-section">
        <div className="reports-control-panel panel">
          <label htmlFor="report-machine-select">
            <strong>Target Machine:</strong>
          </label>
          <div className="report-select-row">
            <select
              id="report-machine-select"
              value={selectedMachine}
              onChange={(e) => setSelectedMachine(e.target.value)}
            >
              {machines.map((m) => (
                <option key={m.machineId} value={m.machineId}>
                  {m.machineId} ({m.condition} · {m.failureRisk}% risk)
                </option>
              ))}
            </select>
            {selectedMachine && (
              <a
                className="primary-button report-download-btn"
                href={`${API_BASE_URL}/api/machines/${encodeURIComponent(selectedMachine)}/report`}
                download
              >
                <Download size={15} style={{ marginRight: '6px' }} />
                <span>Export PDF Report</span>
              </a>
            )}
          </div>
        </div>

        {loading && <p className="chart-empty">Loading audit summary…</p>}
        {error && <p className="api-error" role="alert">{error}</p>}

        {machineData && !loading && (
          <div className="report-preview-grid">
            <article className="report-preview-card">
              <h3>Machine Identification</h3>
              <p><strong>Machine ID:</strong> {machineData.machineId}</p>
              <p><strong>Variant Grade:</strong> {machineData.latestPrediction?.inputs?.type || 'M'}</p>
              <p><strong>Last Stream Log:</strong> {new Date(machineData.latestPrediction?.timestamp).toLocaleString()}</p>
            </article>

            <article className="report-preview-card">
              <h3>Condition &amp; Failure Risk</h3>
              <p>
                <strong>Condition:</strong>{' '}
                <span className={`history-condition ${machineData.latestPrediction?.condition?.toLowerCase()}`}>
                  {machineData.latestPrediction?.condition}
                </span>
              </p>
              <p><strong>Failure Risk Score:</strong> {machineData.latestPrediction?.failureRisk}%</p>
              <p><strong>Priority Action:</strong> {machineData.latestPrediction?.maintenancePriority}</p>
            </article>

            <article className="report-preview-card">
              <h3>Audit History Metrics</h3>
              <p><strong>Evaluations Logged:</strong> {machineData.predictions?.length || 0}</p>
              <p><strong>Maintenance Records:</strong> {machineData.maintenanceRecords?.length || 0}</p>
              <p><strong>Recommendation:</strong> {machineData.latestPrediction?.recommendation}</p>
            </article>
          </div>
        )}
      </section>
    </motion.div>
  )
}

export default ReportsPage
