import { useState } from 'react'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:5000'

function AuthPanel({ onAuthenticated }) {
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', password: '' })
  const [state, setState] = useState({ loading: false, error: '', message: '' })

  const submit = async (event) => {
    event.preventDefault()
    setState({ loading: true, error: '', message: '' })
    try {
      const endpoint = mode === 'login' ? 'login' : 'register'
      const response = await fetch(`${API_BASE_URL}/api/auth/${endpoint}`, {
        method: 'POST', credentials: 'include', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(form),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) throw new Error(data.error || 'Authentication request failed.')
      if (mode === 'register') {
        setState({ loading: false, error: '', message: `Account created as ${data.user.role}. Please log in.` })
        setMode('login')
        return
      }
      onAuthenticated(data.user)
    } catch (error) { setState({ loading: false, error: error.message, message: '' }) }
  }

  return <main className="auth-shell"><section className="auth-card"><div className="brand"><span className="brand-mark">FG</span><span>FactoryGuard AI</span></div><p className="section-kicker">Secure access</p><h1>{mode === 'login' ? 'Sign in to FactoryGuard' : 'Create an account'}</h1><p>{mode === 'login' ? 'Access saved machine analyses, maintenance records, and alerts.' : 'The first project account is an Admin; later accounts are Maintenance users.'}</p><form onSubmit={submit}><label>Username<input required minLength="3" maxLength="50" pattern="[A-Za-z0-9_.-]+" name="username" value={form.username} onChange={(event) => setForm({ ...form, username: event.target.value })} /></label><label>Password<input required minLength="8" maxLength="128" type="password" name="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} /></label>{state.error && <p className="api-error" role="alert">{state.error}</p>}{state.message && <p className="maintenance-success">{state.message}</p>}<button className="primary-button" disabled={state.loading}>{state.loading ? 'Please wait...' : mode === 'login' ? 'Login' : 'Register'}</button></form><button className="auth-switch" type="button" onClick={() => { setMode(mode === 'login' ? 'register' : 'login'); setState({ loading: false, error: '', message: '' }) }}>{mode === 'login' ? 'Need an account? Register' : 'Already have an account? Login'}</button></section></main>
}

export default AuthPanel
