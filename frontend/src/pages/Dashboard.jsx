import { Link } from 'react-router-dom'
import { api, useApi } from '../api.js'
import { ErrorBox, Loading, MovieCard, Row } from '../components/ui.jsx'

export default function Dashboard() {
  const { data, error, loading, reload } = useApi(() => api.dashboard())
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const d = data
  const hero = d.picked_for_you[0]
  const maxLiked = Math.max(1, ...d.taste.map((t) => t.liked))

  return (
    <div className="stack">
      {hero && (
        <Link to={`/movie/${hero.id}`} className="hero">
          <div className="hero-text">
            <span className="eyebrow">Top pick for you</span>
            <h1>{hero.title}</h1>
            <p className="muted">{hero.year} · {hero.genres.join(', ')} · IMDb {hero.imdb_rating}</p>
            <ul className="reasons">{hero.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
          </div>
          {hero.poster && <img src={hero.poster} alt="" className="hero-img" />}
        </Link>
      )}

      <div className="stat-row">
        <div className="stat"><b>{d.stats.in_list}</b><span>in my list</span></div>
        <div className="stat"><b>{d.stats.rated}</b><span>movies rated</span></div>
        <div className="stat"><b>{d.user.favourite_genres.length}</b><span>favourite genres</span></div>
        <div className="stat wide"><span>Favourite genres</span><b className="small-b">{d.user.favourite_genres.join(', ')}</b></div>
      </div>

      <section className="row">
        <div className="row-head"><h2>My list</h2><Link to="/profile">Manage</Link></div>
        {d.my_list.length === 0 ? <p className="muted">Your list is empty. Add movies from Browse.</p> : (
          <div className="row-scroll">{d.my_list.map((m) => <MovieCard key={m.id} movie={m} />)}</div>
        )}
      </section>

      <Row title="Picked for you" subtitle="matched to your genres, favourite directors and actors" movies={d.picked_for_you.slice(1)} />
      {d.because_you_liked && (
        <Row title={`Because you liked ${d.because_you_liked.seed.title}`} subtitle="what other people with the same taste liked" movies={d.because_you_liked.items} />
      )}
      <Row title="Trending this week" subtitle="most rated by all users in the last 7 days" movies={d.trending} />
      {d.top_in_genre && <Row title={`Best of ${d.top_in_genre.genre}`} subtitle="highest IMDb ratings you have not seen" movies={d.top_in_genre.items} />}

      <section className="panel">
        <h2>Your taste</h2>
        <p className="muted small">From your own ratings (4 or 5 stars counts as liked).</p>
        {d.taste.length === 0 ? <p className="muted">Rate a few movies to see this.</p> : d.taste.slice(0, 8).map((t) => (
          <div key={t.genre} className="bar-row">
            <span>{t.genre}</span>
            <span className="bar"><span style={{ width: `${(t.liked / maxLiked) * 100}%` }} /></span>
            <span className="muted small">{t.liked} liked · avg {t.avg_stars}★</span>
          </div>
        ))}
      </section>
    </div>
  )
}
