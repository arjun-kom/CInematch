import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, useApi } from '../api.js'
import { ErrorBox, Loading, Poster, Row, Stars } from '../components/ui.jsx'
import { money, runtime } from '../format.js'

export default function MovieDetail() {
  const { id } = useParams()
  const { data, error, loading, reload } = useApi(() => api.movie(id), [id])
  const [actionError, setActionError] = useState(null)

  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const { movie: m, community: c } = data

  const act = (fn) => async () => {
    setActionError(null)
    try { await fn(); reload() } catch (e) { setActionError(e) }
  }
  const maxDist = Math.max(1, ...Object.values(c.distribution))

  return (
    <div className="stack">
      <div className="detail">
        <Poster movie={m} className="detail-poster" />
        <div className="detail-info">
          <h1>{m.title} <span className="muted">({m.year})</span></h1>
          <p className="muted">
            {[runtime(m.runtime), m.certificate, m.genres.join(', ')].filter(Boolean).join(' · ')}
          </p>
          <div className="badges">
            <span className="badge imdb-badge">IMDb {m.imdb_rating}{m.imdb_votes ? ` · ${m.imdb_votes.toLocaleString()} votes` : ''}</span>
            {m.metascore && <span className="badge">Metascore {m.metascore}</span>}
            {money(m.revenue_musd) && <span className="badge">Box office {money(m.revenue_musd)}</span>}
          </div>
          <p>{m.description}</p>
          {m.director && <p><span className="muted">Director:</span> <Link to={`/browse?q=${encodeURIComponent(`"${m.director}"`)}`}>{m.director}</Link></p>}
          <p><span className="muted">Cast:</span> {m.cast.join(', ')}</p>
          <div className="actions">
            {data.in_my_list
              ? <button className="btn" onClick={act(() => api.removeFromList(m.id))}>✓ In my list (remove)</button>
              : <button className="btn btn-primary" onClick={act(() => api.addToList(m.id))}>+ Add to my list</button>}
            <div className="rate">
              <span className="muted small">Your rating</span>
              <Stars value={data.my_stars} onChange={(s) => act(() => api.rate(m.id, s))()} />
              {data.my_stars && <button className="link-btn small" onClick={act(() => api.unrate(m.id))}>clear</button>}
            </div>
          </div>
          <ErrorBox error={actionError} />
          {m.wiki && <p className="small"><a href={m.wiki} target="_blank" rel="noreferrer">Read more on Wikipedia ↗</a></p>}
        </div>
        <div className="panel community">
          <h3>Community ratings</h3>
          {c.ratings === 0 ? <p className="muted small">Nobody has rated this yet.</p> : (
            <>
              <div className="big-num">{c.avg_stars}★</div>
              <p className="muted small">{c.ratings} rating(s) from users</p>
              {[5, 4, 3, 2, 1].map((s) => (
                <div key={s} className="dist-row">
                  <span>{s}★</span>
                  <span className="bar"><span style={{ width: `${(c.distribution[s] / maxDist) * 100}%` }} /></span>
                  <span className="muted small">{c.distribution[s]}</span>
                </div>
              ))}
            </>
          )}
        </div>
      </div>

      <Row title="People who liked this also liked" subtitle="based on other users' ratings" movies={data.fans_also_liked}
        empty="Not enough ratings yet to compare with other users." />
      <Row title="More like this" subtitle="same genres, director or actors" movies={data.similar} />
    </div>
  )
}
