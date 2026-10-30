import { useState } from 'react'
import { api } from '../api.js'
import { useAuth } from '../auth.jsx'
import { ErrorBox } from '../components/ui.jsx'

export default function Login({ meta }) {
  const { signIn } = useAuth()
  const [mode, setMode] = useState('login')
  const [form, setForm] = useState({ username: '', password: '', display_name: '' })
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const res = mode === 'login'
        ? await api.login({ username: form.username, password: form.password })
        : await api.register({ username: form.username, password: form.password, display_name: form.display_name || undefined })
      signIn(res)
    } catch (err) {
      setError(err)
    } finally {
      setBusy(false)
    }
  }
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value })

  return (
    <div className="auth-page">
      <div className="auth-box">
        <div className="brand big"><span className="logo">▶</span> {meta.app_name}</div>
        <p className="muted">{meta.tagline}</p>
        <div className="tabs">
          <button className={mode === 'login' ? 'on' : ''} onClick={() => setMode('login')}>Log in</button>
          <button className={mode === 'register' ? 'on' : ''} onClick={() => setMode('register')}>Create account</button>
        </div>
        <form onSubmit={submit} className="form">
          <label>Username<input value={form.username} onChange={set('username')} autoComplete="username" required /></label>
          {mode === 'register' && <label>Your name (optional)<input value={form.display_name} onChange={set('display_name')} /></label>}
          <label>Password<input type="password" value={form.password} onChange={set('password')} autoComplete={mode === 'login' ? 'current-password' : 'new-password'} required /></label>
          {mode === 'register' && <p className="muted small">Username: letters, numbers, _ or . (3 to 30). Password: at least 6 characters.</p>}
          <ErrorBox error={error} />
          <button className="btn btn-primary" disabled={busy}>{busy ? 'Please wait...' : mode === 'login' ? 'Log in' : 'Create account'}</button>
        </form>
        <p className="muted small">Demo account: <b>demo</b> / <b>demo1234</b></p>
      </div>
    </div>
  )
}
