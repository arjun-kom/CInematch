import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, useApi } from '../api.js'
import { ErrorBox, GenreChips, Loading, MovieCard } from '../components/ui.jsx'

export default function Browse() {
  const [params, setParams] = useSearchParams()
  const genres = params.getAll('genre')
  const [text, setText] = useState(params.get('q') || '')
  const filters = {
    q: params.get('q') || '',
    genre: genres,
    year_from: params.get('year_from') || '',
    year_to: params.get('year_to') || '',
    min_rating: params.get('min_rating') || '',
    sort: params.get('sort') || (params.get('q') ? 'relevance' : 'popular'),
    page: Number(params.get('page') || 1),
  }
  const allGenres = useApi(() => api.genres())
  const { data, error, loading, reload } = useApi(() => api.movies({ ...filters, page_size: 24 }), [params.toString()])

  const update = (changes) => {
    const next = new URLSearchParams(params)
    for (const [k, v] of Object.entries(changes)) {
      next.delete(k)
      if (Array.isArray(v)) v.forEach((x) => next.append(k, x))
      else if (v) next.set(k, v)
    }
    if (!('page' in changes)) next.delete('page')
    setParams(next)
  }
  useEffect(() => { setText(params.get('q') || '') }, [params])
  const pages = data ? Math.max(1, Math.ceil(data.total / data.page_size)) : 1

  return (
    <div className="stack">
      <h1>Browse movies</h1>
      <form className="filters" onSubmit={(e) => { e.preventDefault(); update({ q: text.trim(), sort: text.trim() ? 'relevance' : '' }) }}>
        <input className="search" placeholder="Search title, actor, director or plot words" value={text} onChange={(e) => setText(e.target.value)} />
        <button className="btn">Search</button>
        <input type="number" placeholder="From year" value={filters.year_from} onChange={(e) => update({ year_from: e.target.value })} />
        <input type="number" placeholder="To year" value={filters.year_to} onChange={(e) => update({ year_to: e.target.value })} />
        <select value={filters.min_rating} onChange={(e) => update({ min_rating: e.target.value })}>
          <option value="">Any IMDb rating</option>
          {[6, 7, 7.5, 8, 8.5].map((r) => <option key={r} value={r}>IMDb {r}+</option>)}
        </select>
        <select value={filters.sort} onChange={(e) => update({ sort: e.target.value })}>
          {filters.q && <option value="relevance">Best match</option>}
          <option value="popular">Most popular</option>
          <option value="rating">Highest rated</option>
          <option value="newest">Newest</option>
          <option value="oldest">Oldest</option>
        </select>
        <button type="button" className="btn btn-ghost" onClick={() => { setText(''); setParams({}) }}>Clear</button>
      </form>
      {allGenres.data && (
        <GenreChips genres={allGenres.data} selected={genres}
          onToggle={(g) => update({ genre: genres.includes(g) ? genres.filter((x) => x !== g) : [...genres, g] })} />
      )}
      <ErrorBox error={error} onRetry={reload} />
      {loading && !data && <Loading />}
      {data && (
        <>
          <p className="muted">{data.total} movies</p>
          <div className="grid">{data.items.map((m) => <MovieCard key={m.id} movie={m} />)}</div>
          {data.total === 0 && <p className="muted">No movies match. Try fewer filters.</p>}
          <div className="pager">
            <button className="btn btn-small" disabled={filters.page <= 1} onClick={() => update({ page: String(filters.page - 1) })}>Previous</button>
            <span className="muted">Page {filters.page} of {pages}</span>
            <button className="btn btn-small" disabled={filters.page >= pages} onClick={() => update({ page: String(filters.page + 1) })}>Next</button>
          </div>
        </>
      )}
    </div>
  )
}
