import { useState } from 'react'
import { searchReports } from '../api'
import { formatDate } from '../format'
import { routes } from '../useRoute'
import StatusBadge from './StatusBadge'

const EXAMPLES = ['analyst downgrade', 'earnings', 'regulatory', 'no clear catalyst']

// A short plain-text preview of a markdown passage
const plain = (md) =>
  md
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^- /gm, '')
    .trim()

// Marks the searched words by splitting the text, so no HTML is ever built from report text
function Highlight({ text, terms }) {
  const words = terms.filter((t) => t.length > 1).map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!words.length) return text
  return text.split(new RegExp(`\\b(${words.join('|')})`, 'gi')).map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part))
}

// Search every saved report: by keywords, and by meaning when the API has a Voyage key.
// Results are grouped by day; clicking a day opens its report.
export default function SearchPanel({ latestDate }) {
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = async (q) => {
    if (!q.trim()) return
    setBusy(true)
    setError(null)
    try {
      setData(await searchReports(q))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const clear = () => {
    setQuery('')
    setData(null)
    setError(null)
  }

  // An older day opens in the report viewer below; bring it into view
  const openDay = (day) => {
    if (day !== latestDate) {
      setTimeout(() => document.getElementById('day-report')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    }
  }

  const days = []
  for (const r of data?.results || []) {
    let day = days.find((d) => d.date === r.session_date)
    if (!day) days.push((day = { date: r.session_date, status: r.status, passages: [] }))
    day.passages.push(r)
  }

  return (
    <section className="panel search" aria-label="Search reports">
      <div className="section-head">
        <h2>Search reports</h2>
        {data && <span className="muted small">{data.mode === 'hybrid' ? 'By meaning and keywords' : 'By keywords'}</span>}
      </div>

      <form
        className="search-row"
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          run(query)
        }}
      >
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. analyst downgrade, earnings, regulatory"
          aria-label="Search all reports"
          maxLength={500}
        />
        <button className="primary" disabled={busy || !query.trim()}>{busy ? 'Searching…' : 'Search'}</button>
        {data && <button type="button" className="link" onClick={clear}>Clear</button>}
      </form>

      {!data && (
        <div className="examples">
          {EXAMPLES.map((q) => (
            <button
              key={q}
              type="button"
              className="chip"
              onClick={() => {
                setQuery(q)
                run(q)
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {data?.note && <p className="muted small">{data.note}</p>}
      {data?.mode === 'keyword' && !data.note && (
        <p className="muted small">Searching by keywords only: meaning-based search is off because the API has no Voyage API key.</p>
      )}

      {data && (
        <div className={busy ? 'refreshing' : ''} aria-live="polite">
          <p className="muted small">
            {data.results.length === 0
              ? 'No matching passages.'
              : `${data.results.length} passage${data.results.length === 1 ? '' : 's'} from ${days.length} day${days.length === 1 ? '' : 's'}, best match first`}
          </p>
          <ol className="search-results">
            {days.map((day) => (
              <li key={day.date}>
                <a
                  className="result-day"
                  href={day.date === latestDate ? routes.today : routes.previous(day.date)}
                  onClick={() => openDay(day.date)}
                >
                  <span className="day-date">{formatDate(day.date)}</span>
                  <StatusBadge status={day.status} current={day.date === latestDate} />
                </a>
                {day.passages.map((p, i) => (
                  <div key={i} className="passage">
                    <div className="passage-head">
                      <strong>{p.ticker || 'Overview'}</strong>
                      <span className="muted small">matched by {p.matched_by.join(' and ')}</span>
                    </div>
                    <p className="passage-text">
                      <Highlight text={plain(p.text)} terms={data.terms} />
                    </p>
                  </div>
                ))}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
