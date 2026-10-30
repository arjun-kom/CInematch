import { useEffect, useState } from 'react'
import { Navigate, NavLink, Route, Routes, useNavigate } from 'react-router-dom'
import { api } from './api.js'
import { useAuth } from './auth.jsx'
import Login from './pages/Login.jsx'
import Onboarding from './pages/Onboarding.jsx'
import Dashboard from './pages/Dashboard.jsx'
import Browse from './pages/Browse.jsx'
import MovieDetail from './pages/MovieDetail.jsx'
import Profile from './pages/Profile.jsx'
import Insights from './pages/Insights.jsx'
import { Loading } from './components/ui.jsx'

export default function App() {
  const { user, ready, signOut } = useAuth()
  const [meta, setMeta] = useState({ app_name: 'CineMatch', tagline: '' })
  const navigate = useNavigate()

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); document.title = m.app_name }).catch(() => {})
  }, [])

  if (!ready) return <Loading />
  if (!user) return <Login meta={meta} />
  if (!user.onboarded) return <Onboarding meta={meta} />

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand" onClick={() => navigate('/')}>
          <span className="logo">▶</span> {meta.app_name}
        </div>
        <nav>
          <NavLink to="/" end>Home</NavLink>
          <NavLink to="/browse">Browse</NavLink>
          <NavLink to="/profile">My list &amp; ratings</NavLink>
          <NavLink to="/insights">Insights</NavLink>
        </nav>
        <div className="user">
          <span>{user.display_name}</span>
          <button className="btn btn-small btn-ghost" onClick={signOut}>Log out</button>
        </div>
      </header>
      <main className="main">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/browse" element={<Browse />} />
          <Route path="/movie/:id" element={<MovieDetail />} />
          <Route path="/profile" element={<Profile />} />
          <Route path="/insights" element={<Insights />} />
          <Route path="*" element={<Navigate to="/" />} />
        </Routes>
      </main>
      <footer className="footer muted">{meta.tagline} · Movie data: IMDb dataset copies and Wikipedia</footer>
    </div>
  )
}
