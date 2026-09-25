import { motion } from 'framer-motion'
import { Wrench } from 'lucide-react'
import MaintenanceManager from '../components/MaintenanceManager.jsx'

function MaintenancePage({ machines, initialMachineId }) {
  return (
    <motion.div
      className="page-container maintenance-page"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <div className="page-header">
        <div>
          <div className="eyebrow-badge">
            <Wrench size={14} />
            <span>Preventive Operations</span>
          </div>
          <h1>Maintenance Management &amp; Logs</h1>
          <p className="hero-subtext">
            Track inspections, log maintenance actions, and download engineering reports.
          </p>
        </div>
      </div>
      <MaintenanceManager
        machines={machines}
        initialMachineId={initialMachineId}
      />
    </motion.div>
  )
}

export default MaintenancePage
