// Every call to the FastAPI backend lives here.
import { useCallback, useEffect, useState } from 'react'

const TOKEN_KEY = 'movie_app_token'

export const token = {
  get: () => { try { return localStorage.getItem(TOKEN_KEY) } catch { return null } },
  set: (t) => { try { localStorage.setItem(TOKEN_KEY, t) } catch { /* ignore */ } },
  clear: () => { try { localStorage.removeItem(TOKEN_KEY) } catch { /* ignore */ } },
}

export class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}

let onUnauthorized = () => {}
export const setUnauthorizedHandler = (fn) => { onUnauthorized = fn }

export function buildQuery(params = {}) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(params)) {
    if (v === undefined || v === null || v === '') continue
    if (Array.isArray(v)) v.forEach((x) => q.append(k, x))
    else q.append(k, v)
  }
  const s = q.toString()
  return s ? `?${s}` : ''
}

async function request(path, { method = 'GET', body, params } = {}) {
  const headers = {}
  if (body) headers['Content-Type'] = 'application/json'
  const t = token.get()
  if (t) headers.Authorization = `Bearer ${t}`
  let res
  try {
    res = await fetch(`/api${path}${buildQuery(params)}`, { method, headers, body: body ? JSON.stringify(body) : undefined })
  } catch {
    throw new ApiError('Cannot reach the server. Is the backend running?', 0)
  }
  let data = null
  try { data = await res.json() } catch { /* empty */ }
  if (res.status === 401 && t) onUnauthorized()
  if (!res.ok) throw new ApiError(data?.detail || `Request failed (HTTP ${res.status})`, res.status)
  return data
}

export const api = {
  meta: () => request('/meta'),
  register: (body) => request('/auth/register', { method: 'POST', body }),
  login: (body) => request('/auth/login', { method: 'POST', body }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),
  genres: () => request('/genres'),
  movies: (params) => request('/movies', { params }),
  movie: (id) => request(`/movies/${encodeURIComponent(id)}`),
  onboarding: (body) => request('/me/onboarding', { method: 'POST', body }),
  preferences: (genres) => request('/me/preferences', { method: 'PUT', body: { favourite_genres: genres } }),
  dashboard: () => request('/me/dashboard'),
  myList: () => request('/me/list'),
  addToList: (id) => request('/me/list', { method: 'POST', body: { movie_id: id } }),
  removeFromList: (id) => request(`/me/list/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  myRatings: () => request('/me/ratings'),
  rate: (id, stars) => request(`/me/ratings/${encodeURIComponent(id)}`, { method: 'PUT', body: { stars } }),
  unrate: (id) => request(`/me/ratings/${encodeURIComponent(id)}`, { method: 'DELETE' }),
  insights: () => request('/insights'),
  pipelines: () => request('/insights/pipelines'),
}

export function useApi(fn, deps = []) {
  const [state, setState] = useState({ data: null, error: null, loading: true })
  const load = useCallback(() => {
    setState((s) => ({ ...s, loading: true, error: null }))
    return fn()
      .then((data) => setState({ data, error: null, loading: false }))
      .catch((error) => setState({ data: null, error, loading: false }))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)
  useEffect(() => { load() }, [load])
  return { ...state, reload: load }
}
