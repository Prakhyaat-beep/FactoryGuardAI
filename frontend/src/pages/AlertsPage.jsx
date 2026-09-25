import { AlertTriangle } from 'lucide-react'
import AlertManager from '../components/AlertManager.jsx'

function AlertsPage({ refreshKey, onAlertResolved }) {
  return (
    <div className="page-container alerts-page">
      <AlertManager
        refreshKey={refreshKey}
        onAlertResolved={onAlertResolved}
      />
    </div>
  )
}

export default AlertsPage
