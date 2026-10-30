import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, useApi } from '../api.js'
import { useAuth } from '../auth.jsx'
import { ErrorBox, GenreChips, Loading, MovieCard, Stars } from '../components/ui.jsx'

export default function Profile() {
  const { user, setUser } = useAuth()
  const list = useApi(() => api.myList())
  const ratings = useApi(() => api.myRatings())
  const allGenres = useApi(() => api.genres())
  const [genres, setGenres] = useState(user.favourite_genres)
  const [msg, setMsg] = useState(null)
  const [error, setError] = useState(null)
  useEffect(() => setGenres(user.favourite_genres), [user])

  const saveGenres = async () => {
    setError(null)
    try { setUser(await api.preferences(genres)); setMsg('Saved. Your recommendations are updated.') } catch (e) { setError(e) }
  }
  const remove = async (id) => { await api.removeFromList(id); list.reload() }
  const rate = async (id, s) => { await api.rate(id, s); ratings.reload() }

  return (
    <div className="stack">
      <h1>My list &amp; ratings</h1>

      <section className="panel">
        <h2>Favourite genres</h2>
        {allGenres.data && <GenreChips genres={allGenres.data} selected={genres}
          onToggle={(g) => { setMsg(null); setGenres(genres.includes(g) ? genres.filter((x) => x !== g) : [...genres, g]) }} />}
        <div className="row-gap">
          <button className="btn btn-primary" disabled={!genres.length} onClick={saveGenres}>Save genres</button>
          {msg && <span className="ok">{msg}</span>}
        </div>
        <ErrorBox error={error} />
      </section>

      <section>
        <h2>My list ({list.data?.length ?? 0})</h2>
        {list.loading && !list.data && <Loading />}
        <ErrorBox error={list.error} onRetry={list.reload} />
        {list.data && list.data.length === 0 && <p className="muted">Empty. <Link to="/browse">Find movies</Link></p>}
        <div className="grid">
          {list.data?.map((m) => (
            <div key={m.id} className="with-action">
              <MovieCard movie={m} />
              <button className="btn btn-small btn-ghost" onClick={() => remove(m.id)}>Remove</button>
            </div>
          ))}
        </div>
      </section>

      <section>
        <h2>My ratings ({ratings.data?.length ?? 0})</h2>
        <ErrorBox error={ratings.error} onRetry={ratings.reload} />
        {ratings.data && ratings.data.length === 0 && <p className="muted">You have not rated anything yet. Open a movie to rate it.</p>}
        <table className="table">
          <tbody>
            {ratings.data?.map((r) => (
              <tr key={r.movie.id}>
                <td><Link to={`/movie/${r.movie.id}`}>{r.movie.title}</Link> <span className="muted">({r.movie.year})</span></td>
                <td className="muted small">{r.movie.genres.join(', ')}</td>
                <td><Stars value={r.stars} size={18} onChange={(s) => rate(r.movie.id, s)} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </div>
  )
}
