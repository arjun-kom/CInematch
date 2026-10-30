import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api, useApi } from '../api.js'
import { ErrorBox, Loading } from '../components/ui.jsx'

const axis = { stroke: '#9ca3af', fontSize: 12 }

export default function Insights() {
  const { data, error, loading, reload } = useApi(() => api.insights())
  const [pipes, setPipes] = useState(null)
  if (loading && !data) return <Loading />
  if (error) return <ErrorBox error={error} onRetry={reload} />
  const d = data
  const days = d.ratings_per_day.map((r) => ({ ...r, day: r._id.slice(5, 10) }))
  const LABELS = { 0: 'under 5', 5: '5 to 6', 6: '6 to 7', 7: '7 to 8', 8: '8 to 9', 9: '9 and up' }
  const buckets = d.rating_buckets.map((b) => ({ range: LABELS[b._id] || 'other', movies: b.movies }))

  return (
    <div className="stack">
      <div className="row-head">
        <h1>Insights</h1>
        <button className="btn btn-small" onClick={() => api.pipelines().then(setPipes)}>Show the MongoDB pipelines</button>
      </div>
      <p className="muted">Every chart below is one MongoDB aggregation pipeline running on the data.</p>
      <div className="stat-row">
        {Object.entries(d.counts).map(([k, v]) => <div key={k} className="stat"><b>{v.toLocaleString()}</b><span>{k}</span></div>)}
      </div>

      <div className="two-col">
        <Chart title="Movies per genre ($unwind + $group)" height={460}>
          <BarChart data={d.genres} layout="vertical" margin={{ left: 30 }}>
            <CartesianGrid stroke="#2a2f3a" /><XAxis type="number" {...axis} /><YAxis type="category" dataKey="_id" {...axis} width={80} interval={0} />
            <Tooltip contentStyle={{ background: '#111827', border: 'none' }} /><Bar dataKey="movies" fill="#e11d48" />
          </BarChart>
        </Chart>
        <Chart title="IMDb rating spread ($bucket)">
          <BarChart data={buckets}><CartesianGrid stroke="#2a2f3a" /><XAxis dataKey="range" {...axis} /><YAxis {...axis} />
            <Tooltip contentStyle={{ background: '#111827', border: 'none' }} /><Bar dataKey="movies" fill="#f59e0b" /></BarChart>
        </Chart>
        <Chart title="Movies per decade ($floor + $group)">
          <BarChart data={d.decades}><CartesianGrid stroke="#2a2f3a" /><XAxis dataKey="_id" {...axis} /><YAxis {...axis} />
            <Tooltip contentStyle={{ background: '#111827', border: 'none' }} /><Bar dataKey="movies" fill="#38bdf8" /></BarChart>
        </Chart>
        <Chart title="User ratings per day, last 14 days ($dateTrunc)">
          <LineChart data={days}><CartesianGrid stroke="#2a2f3a" /><XAxis dataKey="day" {...axis} /><YAxis {...axis} />
            <Tooltip contentStyle={{ background: '#111827', border: 'none' }} /><Line dataKey="ratings" stroke="#22c55e" strokeWidth={2} /></LineChart>
        </Chart>
      </div>

      <div className="two-col">
        <section className="panel">
          <h2>Best directors (3+ movies, by average IMDb)</h2>
          <table className="table"><tbody>
            {d.top_directors.map((r) => (
              <tr key={r._id}><td>{r._id}</td><td>{r.avg_rating}</td><td className="muted small">{r.titles.join(', ')}</td></tr>
            ))}
          </tbody></table>
        </section>
        <section className="panel">
          <h2>Most loved by users (5+ ratings)</h2>
          <table className="table"><tbody>
            {d.most_loved.map((r) => (
              <tr key={r._id}><td>{r.movie.title} <span className="muted">({r.movie.year})</span></td><td>{r.avg_stars}★</td><td className="muted small">{r.ratings} ratings</td></tr>
            ))}
          </tbody></table>
        </section>
      </div>

      {pipes && (
        <section className="panel">
          <h2>Pipelines</h2>
          {Object.entries(pipes).map(([name, p]) => (
            <details key={name}><summary>{name} <span className="muted">on {p.collection}</span></summary>
              <pre className="json">{JSON.stringify(p.pipeline, null, 2)}</pre></details>
          ))}
        </section>
      )}
    </div>
  )
}

function Chart({ title, children, height = 300 }) {
  return (
    <section className="panel">
      <h2>{title}</h2>
      <ResponsiveContainer width="100%" height={height}>{children}</ResponsiveContainer>
    </section>
  )
}
