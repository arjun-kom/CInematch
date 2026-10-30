// Keeps track of who is logged in.
import { createContext, useContext, useEffect, useState } from 'react'
import { api, setUnauthorizedHandler, token } from './api.js'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [ready, setReady] = useState(false)

  useEffect(() => {
    setUnauthorizedHandler(() => { token.clear(); setUser(null) })
    if (!token.get()) { setReady(true); return }
    api.me().then(setUser).catch(() => token.clear()).finally(() => setReady(true))
  }, [])

  const signIn = ({ token: t, user: u }) => { token.set(t); setUser(u) }
  const signOut = async () => {
    try { await api.logout() } catch { /* already logged out */ }
    token.clear()
    setUser(null)
  }
  const refresh = () => api.me().then(setUser)

  return <AuthContext.Provider value={{ user, ready, signIn, signOut, refresh, setUser }}>{children}</AuthContext.Provider>
}

export const useAuth = () => useContext(AuthContext)
