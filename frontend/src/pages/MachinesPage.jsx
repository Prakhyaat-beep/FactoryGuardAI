import { useEffect, useState } from 'react'
import { motion } from 'framer-motion'
import { Cpu, Search, ArrowRight, Activity, Clock, Wrench } from 'lucide-react'
import MachineCheckup from '../components/MachineCheckup.jsx'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

function MachinesPage({ initialMachineId, onNavigateMaintenance }) {
  const [selectedMachineId, setSelectedMachineId] = useState(initialMachineId || null)
  const [machines, setMachines] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [customMachineInput, setCustomMachineInput] = useState('')

  const loadMachines = async () => {
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE_URL}/api/machines`, { credentials: 'include' })
      const data = await res.json().catch(() => ({}))
      if (!res.ok) throw new Error(data.error || 'Failed to load machines.')
      setMachines(data.machines || [])
      setLoading(false)
    } catch (err) {
      setError(err.message || 'Unable to load fleet machines.')
      setLoading(false)
    }
  }

  useEffect(() => {
    if (initialMachineId) {
      setSelectedMachineId(initialMachineId)
    } else {
      loadMachines()
    }
  }, [initialMachineId])

  const handleOpenCheckup = (machineId) => {
    setSelectedMachineId(machineId)
  }

  const handleBackToFleet = () => {
    setSelectedMachineId(null)
    loadMachines()
  }

  const handleCustomMachineSubmit = (e) => {
    e.preventDefault()
    const trimmed = customMachineInput.trim()
    if (trimmed) {
      setSelectedMachineId(trimmed)
      setCustomMachineInput('')
    }
  }

  if (selectedMachineId) {
    return (
      <div className="page-container machine-monitoring-page">
        <MachineCheckup
          machineId={selectedMachineId}
          onBack={handleBackToFleet}
          onNavigateMaintenance={onNavigateMaintenance}
        />
      </div>
    )
  }

  const totalCount = machines.length
  const attentionCount = machines.filter((m) => ['Warning', 'Critical'].includes(m.condition)).length

  return (
    <motion.div
      className="page-container machines-page"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header">
        <div>
          <div className="eyebrow-badge">
            <Cpu size={14} />
            <span>Fleet Control</span>
          </div>
          <h1>Machine Fleet</h1>
          <p className="hero-subtext">
            {totalCount} machines · {attentionCount > 0 ? `${attentionCount} need attention` : 'All nominal'}
          </p>
        </div>
      </div>

      {/* Direct Machine Checkup Search */}
      <section className="custom-machine-bar panel">
        <form onSubmit={handleCustomMachineSubmit} className="custom-machine-form">
          <label htmlFor="custom-machine-id">
            <Search size={14} style={{ display: 'inline', marginRight: '4px' }} />
            <strong>Target Machine Checkup:</strong>
          </label>
          <div className="custom-machine-input-row">
            <input
              id="custom-machine-id"
              type="text"
              placeholder="e.g. CNC-LATHE-02"
              maxLength="100"
              value={customMachineInput}
              onChange={(e) => setCustomMachineInput(e.target.value)}
            />
            <button type="submit" className="primary-button">
              Launch Diagnostic
            </button>
          </div>
        </form>
      </section>

      {loading && <p className="chart-empty">Loading machine fleet status…</p>}
      {error && <p className="api-error" role="alert">{error}</p>}

      {!loading && (
        <motion.section
          className="fleet-grid"
          aria-label="Machine fleet cards"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: { opacity: 1, transition: { staggerChildren: 0.05 } },
          }}
        >
          {machines.map((m) => {
            const cond = m.condition || 'Normal'
            const risk = m.failureRisk ?? 0
            const wear = m.inputs?.toolWear ?? (m.toolWear || 0)
            const remainingLife = m.remainingToolLife ?? Math.max(0, 220 - Number(wear))

            return (
              <motion.article
                key={m.machineId}
                className={`fleet-card card-condition-${cond.toLowerCase()}`}
                variants={{
                  hidden: { opacity: 0, y: 8 },
                  visible: { opacity: 1, y: 0 },
                }}
                whileHover={{ y: -3 }}
              >
                <div className="fleet-card-header">
                  <div>
                    <h2 className="fleet-machine-id">{m.machineId}</h2>
                    <span className="fleet-type-badge">Variant {m.inputs?.type || m.type || 'M'}</span>
                  </div>
                  <span className={`history-condition ${cond.toLowerCase()}`}>{cond}</span>
                </div>

                <div className="fleet-card-metrics">
                  <div className="metric-box">
                    <span>Failure Risk</span>
                    <strong className={`risk-text-${cond.toLowerCase()}`}>{risk}%</strong>
                  </div>
                  <div className="metric-box">
                    <span>Tool Wear</span>
                    <strong>{wear} min</strong>
                  </div>
                  <div className="metric-box">
                    <span>Est. RUTL</span>
                    <strong>~{remainingLife} min</strong>
                  </div>
                </div>

                <div className="fleet-card-footer">
                  <small className="fleet-timestamp">
                    <Clock size={12} style={{ display: 'inline', marginRight: '4px' }} />
                    {m.timestamp ? new Date(m.timestamp).toLocaleTimeString() : 'Standby'}
                  </small>
                  <button
                    type="button"
                    className="primary-button open-checkup-btn"
                    onClick={() => handleOpenCheckup(m.machineId)}
                  >
                    <span>Checkup</span>
                    <ArrowRight size={14} />
                  </button>
                </div>
              </motion.article>
            )
          })}
        </motion.section>
      )}
    </motion.div>
  )
}

export default MachinesPage
