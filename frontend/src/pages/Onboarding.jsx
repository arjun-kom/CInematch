import { useEffect, useState } from 'react'
import { api, useApi } from '../api.js'
import { useAuth } from '../auth.jsx'
import { ErrorBox, GenreChips, Loading, MovieCard } from '../components/ui.jsx'

const MIN_GENRES = 2
const MIN_MOVIES = 3

export default function Onboarding({ meta }) {
  const { user, setUser, signOut } = useAuth()
  const [step, setStep] = useState(1)
  const [genres, setGenres] = useState([])
  const [picked, setPicked] = useState({})
  const [query, setQuery] = useState('')
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)
  const allGenres = useApi(() => api.genres())

  const toggleGenre = (g) => setGenres(genres.includes(g) ? genres.filter((x) => x !== g) : [...genres, g])
  const togglePick = (m) => {
    const next = { ...picked }
    if (next[m.id]) delete next[m.id]
    else next[m.id] = m
    setPicked(next)
  }

  const finish = async () => {
    setBusy(true)
    setError(null)
    try {
      setUser(await api.onboarding({ genres, movie_ids: Object.keys(picked) }))
    } catch (e) {
      setError(e)
      setBusy(false)
    }
  }

  return (
    <div className="onboard">
      <header className="onboard-head">
        <div className="brand"><span className="logo">▶</span> {meta.app_name}</div>
        <div className="steps"><span className={step === 1 ? 'on' : ''}>1. Genres</span><span className={step === 2 ? 'on' : ''}>2. Movies</span></div>
        <button className="btn btn-small btn-ghost" onClick={signOut}>Log out</button>
      </header>

      {step === 1 && (
        <section className="onboard-body">
          <h1>Hi {user.display_name}, what do you like to watch?</h1>
          <p className="muted">Pick at least {MIN_GENRES} genres. The number shows how many movies we have in each.</p>
          {allGenres.loading && <Loading />}
          <ErrorBox error={allGenres.error} onRetry={allGenres.reload} />
          {allGenres.data && <GenreChips genres={allGenres.data} selected={genres} onToggle={toggleGenre} />}
          <div className="onboard-foot">
            <span className="muted">{genres.length} selected</span>
            <button className="btn btn-primary" disabled={genres.length < MIN_GENRES} onClick={() => setStep(2)}>Next</button>
          </div>
        </section>
      )}

      {step === 2 && (
        <section className="onboard-body">
          <h1>Pick movies you are interested in</h1>
          <p className="muted">Choose at least {MIN_MOVIES}. They go into your list and teach the recommendations what you like.</p>
          <div className="row-gap">
            <input className="search" placeholder="Search a title, actor or director" value={query} onChange={(e) => setQuery(e.target.value)} />
          </div>
          <Candidates genres={genres} query={query} picked={picked} onPick={togglePick} />
          <ErrorBox error={error} />
          <div className="onboard-foot sticky">
            <button className="btn btn-ghost" onClick={() => setStep(1)}>Back</button>
            <span className="muted">{Object.keys(picked).length} selected</span>
            <button className="btn btn-primary" disabled={busy || Object.keys(picked).length < MIN_MOVIES} onClick={finish}>
              {busy ? 'Saving...' : 'Show my recommendations'}
            </button>
          </div>
        </section>
      )}
    </div>
  )
}

function Candidates({ genres, query, picked, onPick }) {
  const [q, setQ] = useState(query)
  useEffect(() => { const t = setTimeout(() => setQ(query), 300); return () => clearTimeout(t) }, [query])
  const { data, error, loading, reload } = useApi(
    () => api.movies({ genre: q ? [] : genres, q, sort: q ? 'relevance' : 'popular', page_size: 36 }),
    [q, genres.join(',')],
  )
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  return (
    <div className="grid">
      {data.items.map((m) => <MovieCard key={m.id} movie={m} selected={!!picked[m.id]} onSelect={onPick} />)}
      {data.items.length === 0 && <p className="muted">No movies found.</p>}
    </div>
  )
}
