import { useEffect, useState } from 'react'
import Navigation from './components/Navigation.jsx'
import AuthPanel from './components/AuthPanel.jsx'
import DashboardPage from './pages/DashboardPage.jsx'
import MachinesPage from './pages/MachinesPage.jsx'
import PredictionsPage from './pages/PredictionsPage.jsx'
import AlertsPage from './pages/AlertsPage.jsx'
import MaintenancePage from './pages/MaintenancePage.jsx'
import MachineLearningPage from './pages/MachineLearningPage.jsx'
import ReportsPage from './pages/ReportsPage.jsx'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'
const INITIAL_FORM = {
  machineId: '',
  airTemperature: '',
  processTemperature: '',
  rotationalSpeed: '',
  torque: '',
  toolWear: '',
  type: 'M',
}

const NUMERIC_FIELDS = [
  { name: 'airTemperature', min: 250, max: 400 },
  { name: 'processTemperature', min: 250, max: 450 },
  { name: 'rotationalSpeed', min: 1, max: 20000 },
  { name: 'torque', min: 0, max: 1000 },
  { name: 'toolWear', min: 0, max: 10000 },
]

function validateForm(form) {
  const errors = {}
  NUMERIC_FIELDS.forEach(({ name, min, max }) => {
    const value = Number(form[name])
    if (form[name] === '' || !Number.isFinite(value)) errors[name] = 'Required numeric value.'
    else if (value < min || value > max) errors[name] = `Must be between ${min} and ${max}.`
  })
  if (!['L', 'M', 'H'].includes(form.type)) errors.type = 'Product type must be L, M, or H.'
  if (form.machineId.length > 100) errors.machineId = 'Machine ID must be 100 characters or fewer.'
  return errors
}

function parseHashRoute() {
  const hash = window.location.hash.replace(/^#\/?/, '')
  if (!hash) return { page: 'dashboard', machineId: null }
  const parts = hash.split('/')
  if (parts[0] === 'machines' && parts[1]) {
    return { page: 'machines', machineId: decodeURIComponent(parts[1]) }
  }
  return { page: parts[0] || 'dashboard', machineId: null }
}

function App() {
  const [activePage, setActivePage] = useState('dashboard')
  const [targetMachineId, setTargetMachineId] = useState(null)
  const [form, setForm] = useState(INITIAL_FORM)
  const [errors, setErrors] = useState({})
  const [prediction, setPrediction] = useState(null)
  const [apiError, setApiError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [connection, setConnection] = useState({ state: 'checking', message: 'Checking API connection...' })
  const [history, setHistory] = useState([])
  const [historyState, setHistoryState] = useState({ loading: true, error: '' })
  const [dashboard, setDashboard] = useState(null)
  const [dashboardState, setDashboardState] = useState({ loading: true, error: '' })
  const [experiment, setExperiment] = useState(null)
  const [experimentState, setExperimentState] = useState({ loading: true, error: '' })
  const [alertRefreshKey, setAlertRefreshKey] = useState(0)
  const [user, setUser] = useState(null)
  const [authLoading, setAuthLoading] = useState(true)

  // Sync state with URL hash
  useEffect(() => {
    const route = parseHashRoute()
    setActivePage(route.page)
    if (route.machineId) setTargetMachineId(route.machineId)

    const onHashChange = () => {
      const nextRoute = parseHashRoute()
      setActivePage(nextRoute.page)
      if (nextRoute.machineId) setTargetMachineId(nextRoute.machineId)
    }
    window.addEventListener('hashchange', onHashChange)
    return () => window.removeEventListener('hashchange', onHashChange)
  }, [])

  const navigateTo = (page, machineId = null) => {
    setActivePage(page)
    setTargetMachineId(machineId)
    if (page === 'machines' && machineId) {
      window.location.hash = `#/machines/${encodeURIComponent(machineId)}`
    } else {
      window.location.hash = `#/${page}`
    }
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const loadHistory = async () => {
    setHistoryState({ loading: true, error: '' })
    try {
      const response = await fetch(`${API_BASE_URL}/api/predictions`, { credentials: 'include' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to load prediction history.')
      setHistory(data.predictions || [])
      setHistoryState({ loading: false, error: '' })
    } catch (error) {
      setHistoryState({ loading: false, error: error.message || 'Unable to load prediction history.' })
    }
  }

  const loadDashboard = async () => {
    setDashboardState({ loading: true, error: '' })
    try {
      const [summaryResponse, trendsResponse] = await Promise.all([
        fetch(`${API_BASE_URL}/api/dashboard/summary`, { credentials: 'include' }),
        fetch(`${API_BASE_URL}/api/dashboard/trends`, { credentials: 'include' }),
      ])
      const summary = await summaryResponse.json().catch(() => ({}))
      const trendData = await trendsResponse.json().catch(() => ({}))
      if (!summaryResponse.ok || !trendsResponse.ok) throw new Error('Unable to load dashboard data.')
      setDashboard({ ...summary, trends: trendData.trends || [] })
      setDashboardState({ loading: false, error: '' })
    } catch (error) {
      setDashboardState({ loading: false, error: error.message || 'Unable to load dashboard data.' })
    }
  }

  const loadExperiment = async () => {
    setExperimentState({ loading: true, error: '' })
    try {
      const response = await fetch(`${API_BASE_URL}/api/models/performance`, { credentials: 'include' })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Unable to load model performance results.')
      setExperiment(data)
      setExperimentState({ loading: false, error: '' })
    } catch (error) {
      setExperimentState({ loading: false, error: error.message || 'Unable to load model performance results.' })
    }
  }

  useEffect(() => {
    const checkBackendConnection = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/api/health`)
        if (!response.ok) throw new Error('Health check failed')
        const data = await response.json()
        setConnection({ state: 'connected', message: data.message || 'Backend connected' })
      } catch {
        setConnection({ state: 'unavailable', message: 'Backend unavailable. Start Flask on port 5000.' })
      }
    }
    checkBackendConnection()
    fetch(`${API_BASE_URL}/api/auth/me`, { credentials: 'include' })
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setUser(data?.user || null))
      .catch(() => setUser(null))
      .finally(() => setAuthLoading(false))
  }, [])

  useEffect(() => {
    if (user) {
      loadHistory()
      loadDashboard()
      loadExperiment()
    }
  }, [user])

  const handleChange = ({ target: { name, value } }) => {
    setForm((current) => ({ ...current, [name]: value }))
    setErrors((current) => ({ ...current, [name]: undefined }))
    setApiError('')
  }

  const handleSubmit = async (event) => {
    event.preventDefault()
    const nextErrors = validateForm(form)
    setErrors(nextErrors)
    setPrediction(null)
    setApiError('')
    if (Object.keys(nextErrors).length) return
    const payload = {
      airTemperature: Number(form.airTemperature),
      processTemperature: Number(form.processTemperature),
      rotationalSpeed: Number(form.rotationalSpeed),
      torque: Number(form.torque),
      toolWear: Number(form.toolWear),
      type: form.type,
    }
    if (form.machineId.trim()) payload.machineId = form.machineId.trim()
    setIsLoading(true)
    try {
      const response = await fetch(`${API_BASE_URL}/api/predict`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Prediction request failed.')
      setPrediction(data)
      setConnection({ state: 'connected', message: 'Backend connected' })
      loadHistory()
      loadDashboard()
      setAlertRefreshKey((value) => value + 1)
    } catch (error) {
      setApiError(error.message || 'Unable to reach the prediction API.')
      setConnection({ state: 'unavailable', message: 'Prediction API is unavailable.' })
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    setForm(INITIAL_FORM)
    setErrors({})
    setPrediction(null)
    setApiError('')
  }

  const logout = async () => {
    await fetch(`${API_BASE_URL}/api/auth/logout`, { method: 'POST', credentials: 'include' })
    setUser(null)
    setPrediction(null)
    setHistory([])
    setDashboard(null)
  }

  if (authLoading) {
    return (
      <main className="auth-shell">
        <p>Checking secure session...</p>
      </main>
    )
  }

  if (!user) {
    return <AuthPanel onAuthenticated={setUser} />
  }

  const activeAlertCount = dashboard?.activeAlertCount || 0
  const machineList = dashboard?.machineStatuses || []

  return (
    <main className="app-shell">
      {/* Top Header Bar */}
      <header className="topbar">
        <div className="brand" onClick={() => navigateTo('dashboard')} style={{ cursor: 'pointer' }}>
          <span className="brand-mark">FG</span>
          <span>FactoryGuard AI</span>
          <span className="app-subtag">CNC Lathe Intelligence</span>
        </div>
        <div className="user-controls">
          <span>{user.username} ({user.role})</span>
          <button className="secondary-button" type="button" onClick={logout}>
            Logout
          </button>
        </div>
        <div className={`connection-status ${connection.state}`} role="status">
          <span className="status-indicator" />
          {connection.message}
        </div>
      </header>

      {/* Main Tabbed Navigation */}
      <Navigation
        activePage={activePage}
        onNavigate={(page) => navigateTo(page)}
        activeAlertCount={activeAlertCount}
      />

      {/* Page Routing */}
      {activePage === 'dashboard' && (
        <DashboardPage
          dashboard={dashboard}
          loading={dashboardState.loading}
          error={dashboardState.error}
          onNavigate={(page) => navigateTo(page)}
          onSelectMachine={(machineId) => navigateTo('machines', machineId)}
        />
      )}

      {activePage === 'machines' && (
        <MachinesPage
          initialMachineId={targetMachineId}
          onNavigateMaintenance={(mId) => navigateTo('maintenance', mId)}
        />
      )}

      {activePage === 'predictions' && (
        <PredictionsPage
          form={form}
          errors={errors}
          prediction={prediction}
          apiError={apiError}
          isLoading={isLoading}
          history={history}
          historyState={historyState}
          userMachines={machineList}
          onChange={handleChange}
          onSelectMachine={(selectedId) => {
            const match = machineList.find((m) => m.machineId === selectedId)
            const inputs = match?.inputs || match || {}
            setForm({
              machineId: selectedId,
              airTemperature: inputs.airTemperature ?? form.airTemperature ?? '300.0',
              processTemperature: inputs.processTemperature ?? form.processTemperature ?? '310.0',
              rotationalSpeed: inputs.rotationalSpeed ?? form.rotationalSpeed ?? '1500',
              torque: inputs.torque ?? form.torque ?? '40.0',
              toolWear: inputs.toolWear ?? form.toolWear ?? '120',
              type: inputs.type ?? form.type ?? 'M',
            })
            setErrors({})
          }}
          onSubmit={handleSubmit}
          onReset={handleReset}
          onOpenHistoryRecord={(record) => {
            setPrediction({ ...record, predictionId: record.id })
            window.scrollTo({ top: 0, behavior: 'smooth' })
          }}
        />
      )}

      {activePage === 'alerts' && (
        <AlertsPage
          refreshKey={alertRefreshKey}
          onAlertResolved={() => {
            loadDashboard()
            setAlertRefreshKey((k) => k + 1)
          }}
        />
      )}

      {activePage === 'maintenance' && (
        <MaintenancePage
          machines={machineList}
          initialMachineId={targetMachineId}
        />
      )}

      {activePage === 'ml' && (
        <MachineLearningPage
          experiment={experiment}
          loading={experimentState.loading}
          error={experimentState.error}
        />
      )}

      {activePage === 'reports' && (
        <ReportsPage
          machines={machineList}
          initialMachineId={targetMachineId}
        />
      )}
    </main>
  )
}

export default App
