import { useState } from 'react'
import { Link } from 'react-router-dom'
import { colourFor, initials } from '../format.js'

export function Poster({ movie, className = '' }) {
  const [broken, setBroken] = useState(false)
  if (movie.poster && !broken) {
    return <img className={`poster ${className}`} src={movie.poster} alt={movie.title} loading="lazy" onError={() => setBroken(true)} />
  }
  return (
    <div className={`poster poster-fallback ${className}`} style={{ background: colourFor(movie.title) }}>
      <span>{initials(movie.title)}</span>
      <small>{movie.title}</small>
    </div>
  )
}

export function MovieCard({ movie, reason, selected, onSelect }) {
  const body = (
    <>
      <div className="card-poster">
        <Poster movie={movie} />
        <span className="imdb">★ {movie.imdb_rating}</span>
        {selected !== undefined && <span className={`tick ${selected ? 'on' : ''}`}>{selected ? '✓' : '+'}</span>}
      </div>
      <div className="card-title">{movie.title}</div>
      <div className="card-sub">{movie.year} · {(movie.genres || []).slice(0, 2).join(', ')}</div>
      {reason && <div className="card-reason">{reason}</div>}
    </>
  )
  if (onSelect) {
    return <button type="button" className={`movie-card ${selected ? 'selected' : ''}`} onClick={() => onSelect(movie)}>{body}</button>
  }
  return <Link to={`/movie/${movie.id}`} className="movie-card">{body}</Link>
}

export function Row({ title, subtitle, movies, reasonKey = true, empty }) {
  return (
    <section className="row">
      <div className="row-head">
        <h2>{title}</h2>
        {subtitle && <span className="muted">{subtitle}</span>}
      </div>
      {movies.length === 0 ? (
        <p className="muted">{empty || 'Nothing here yet.'}</p>
      ) : (
        <div className="row-scroll">
          {movies.map((m) => <MovieCard key={m.id} movie={m} reason={reasonKey ? m.reasons?.[0] : null} />)}
        </div>
      )}
    </section>
  )
}

export function Stars({ value, onChange, size = 26 }) {
  const [hover, setHover] = useState(0)
  return (
    <div className="stars" onMouseLeave={() => setHover(0)}>
      {[1, 2, 3, 4, 5].map((s) => (
        <button key={s} type="button" aria-label={`${s} stars`} style={{ fontSize: size }}
          className={(hover || value || 0) >= s ? 'star on' : 'star'}
          onMouseEnter={() => setHover(s)} onClick={() => onChange(s)}>★</button>
      ))}
    </div>
  )
}

export function GenreChips({ genres, selected, onToggle }) {
  return (
    <div className="chips">
      {genres.map((g) => (
        <button key={g.genre} type="button" className={`chip ${selected.includes(g.genre) ? 'on' : ''}`} onClick={() => onToggle(g.genre)}>
          {g.genre} <span className="chip-count">{g.movies}</span>
        </button>
      ))}
    </div>
  )
}

export function ErrorBox({ error, onRetry }) {
  if (!error) return null
  return (
    <div className="error-box" role="alert">
      {error.message || String(error)}
      {onRetry && <button className="btn btn-small" onClick={onRetry}>Try again</button>}
    </div>
  )
}

export const Loading = () => <div className="muted pad">Loading...</div>
