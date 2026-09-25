import { motion } from 'framer-motion'
import { Activity, AlertTriangle, ShieldCheck, Cpu, Sliders, ArrowUpRight } from 'lucide-react'
import SummaryCard from '../components/SummaryCard.jsx'
import ConditionChart from '../components/ConditionChart.jsx'
import RiskChart from '../components/RiskChart.jsx'
import PredictionTable from '../components/PredictionTable.jsx'
import MachineStatus from '../components/MachineStatus.jsx'

function DashboardPage({ dashboard, loading, error, onNavigate, onSelectMachine }) {
  if (loading) {
    return (
      <div className="page-container dashboard-page">
        <section className="dashboard-message">Loading telemetry and aggregates…</section>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-container dashboard-page">
        <section className="dashboard-message history-error" role="alert">{error}</section>
      </div>
    )
  }

  if (!dashboard) return null

  const totalMachines = dashboard.machineStatuses?.length || 0
  const warningCount = dashboard.conditionCounts?.Warning || 0
  const criticalCount = dashboard.conditionCounts?.Critical || 0
  const needAttention = warningCount + criticalCount

  const containerVariants = {
    hidden: { opacity: 0, y: 12 },
    visible: {
      opacity: 1,
      y: 0,
      transition: { duration: 0.35, staggerChildren: 0.08 },
    },
  }

  const itemVariants = {
    hidden: { opacity: 0, y: 10 },
    visible: { opacity: 1, y: 0, transition: { duration: 0.25 } },
  }

  return (
    <motion.div
      className="page-container dashboard-page"
      initial="hidden"
      animate="visible"
      variants={containerVariants}
    >
      <section className="hero dashboard-hero" aria-labelledby="page-title">
        <div>
          <div className="eyebrow-badge">
            <Cpu size={14} />
            <span>Operational Fleet Status</span>
          </div>
          <h1 id="page-title">Control Room Dashboard</h1>
          <p className="hero-subtext">
            {totalMachines} machines online · {needAttention > 0 ? `${needAttention} require inspection` : 'All systems normal'}
          </p>
        </div>
        <div className="hero-actions">
          <button
            className="primary-button"
            type="button"
            onClick={() => onNavigate('machines')}
          >
            <Cpu size={15} />
            <span>Machine Fleet</span>
          </button>
          <button
            className="secondary-button"
            type="button"
            onClick={() => onNavigate('predictions')}
          >
            <Sliders size={15} />
            <span>Run Prediction</span>
          </button>
        </div>
      </section>

      <section className="dashboard" aria-label="Factory monitoring dashboard">
        <motion.div className="summary-grid" variants={itemVariants}>
          <SummaryCard label="Predictions logged" value={dashboard.totalPredictions} icon={Activity} />
          <SummaryCard label="Normal" value={dashboard.conditionCounts.Normal} tone="normal" icon={ShieldCheck} />
          <SummaryCard label="Warning" value={dashboard.conditionCounts.Warning} tone="warning" icon={AlertTriangle} />
          <SummaryCard label="Critical" value={dashboard.conditionCounts.Critical} tone="critical" icon={AlertTriangle} />
          <SummaryCard label="Fleet avg risk" value={`${dashboard.averageFailureRisk}%`} icon={ArrowUpRight} />
          <SummaryCard label="Active alerts" value={dashboard.activeAlertCount} tone={dashboard.activeAlertCount > 0 ? 'critical' : 'normal'} icon={AlertTriangle} />
        </motion.div>

        <motion.div className="chart-grid" variants={itemVariants}>
          <ConditionChart counts={dashboard.conditionCounts} />
          <RiskChart trends={dashboard.trends} />
        </motion.div>

        <motion.div className="dashboard-two-column" variants={itemVariants}>
          <MachineStatus
            machines={dashboard.machineStatuses}
            onSelectMachine={onSelectMachine}
          />
          <PredictionTable predictions={dashboard.recentPredictions} />
        </motion.div>
      </section>
    </motion.div>
  )
}

export default DashboardPage
