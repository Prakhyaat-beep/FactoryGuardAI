import { motion } from 'framer-motion'
import {
  LayoutDashboard,
  Cpu,
  Zap,
  AlertTriangle,
  Wrench,
  BrainCircuit,
  FileText,
} from 'lucide-react'

function Navigation({ activePage, onNavigate, activeAlertCount = 0 }) {
  const items = [
    { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'machines', label: 'Machines', icon: Cpu },
    { id: 'predictions', label: 'Predictions', icon: Zap },
    { id: 'alerts', label: 'Alerts', icon: AlertTriangle, badge: activeAlertCount },
    { id: 'maintenance', label: 'Maintenance', icon: Wrench },
    { id: 'ml', label: 'Machine Learning', icon: BrainCircuit },
    { id: 'reports', label: 'Reports', icon: FileText },
  ]

  return (
    <nav className="main-nav" aria-label="Primary navigation">
      <ul className="nav-list">
        {items.map((item) => {
          const isActive =
            activePage === item.id || (item.id === 'machines' && activePage.startsWith('machine-'))
          const IconComponent = item.icon
          return (
            <li key={item.id}>
              <button
                type="button"
                className={`nav-item ${isActive ? 'active' : ''}`}
                onClick={() => onNavigate(item.id)}
                aria-current={isActive ? 'page' : undefined}
              >
                <IconComponent className="nav-icon-svg" size={16} aria-hidden="true" />
                <span className="nav-label">{item.label}</span>
                {Boolean(item.badge) && item.badge > 0 && (
                  <motion.span
                    className="nav-badge"
                    initial={{ scale: 0.8 }}
                    animate={{ scale: 1 }}
                    transition={{ type: 'spring', stiffness: 400, damping: 25 }}
                    aria-label={`${item.badge} active alerts`}
                  >
                    {item.badge}
                  </motion.span>
                )}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}

export default Navigation
