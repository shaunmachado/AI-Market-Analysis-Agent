import { useEffect, useRef, useState } from 'react'
import { addStock, removeStock, searchStocks, setMainStock } from '../api'
import { useOpenChart } from '../chartContext'
import { number, percent } from '../format'
import { routes } from '../useRoute'

const SEARCH_DELAY_MS = 350 // wait for a pause in typing before searching

function Star({ on }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"
        fill={on ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Find US stocks and ETFs by name or ticker, and add them
function FindStocks({ list, onChange }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null) // {text, error}
  const latest = useRef('')

  useEffect(() => {
    const q = query.trim()
    latest.current = q
    setMessage(null)
    if (!q) {
      setResults(null)
      return
    }
    const timer = setTimeout(() => {
      setBusy(true)
      searchStocks(q)
        .then((found) => latest.current === q && setResults(found))
        .catch((e) => latest.current === q && setMessage({ text: e.message, error: true }))
        .finally(() => setBusy(false))
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [query])

  const add = async (stock, main) => {
    setMessage(null)
    try {
      const body = await addStock(stock.ticker, main)
      onChange(body.watchlist)
      setResults((current) => current?.map((r) => (r.ticker === stock.ticker ? { ...r, tracked: true } : r)))
      setMessage({ text: `Added ${stock.ticker}${main ? ' as a main stock' : ''}. Its first figures come with the next report.` })
    } catch (e) {
      setMessage({ text: e.message, error: true })
    }
  }

  const full = list && list.tracked_count >= list.max_tracked
  const mainFull = list && list.main_count >= list.max_main

  return (
    <section className="panel stocks-find" aria-label="Find stocks">
      <div className="section-head">
        <h2>Find stocks</h2>
        {list && (
          <span className="muted small">
            {list.tracked_count} of {list.max_tracked} tracked · {list.main_count} of {list.max_main} main
          </span>
        )}
      </div>
      <form role="search" onSubmit={(e) => e.preventDefault()}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Company name or ticker, e.g. Costco or COST"
          aria-label="Find a stock"
          maxLength={60}
        />
      </form>
      <p className="muted small">US-listed stocks and ETFs, from Yahoo Finance.</p>
      {message && <p className={message.error ? 'error' : 'notice'} role="status">{message.text}</p>}
      {busy && <p className="muted small">Searching…</p>}
      {results && !busy && results.length === 0 && <p className="muted small">No US stocks or ETFs match that.</p>}
      {results?.length > 0 && (
        <ul className="search-hits" aria-label="Matches">
          {results.map((r) => (
            <li key={r.ticker}>
              <div className="hit-name">
                <strong>{r.ticker}</strong> {r.name}
                <span className="muted small">
                  {' '}
                  · {r.type}
                  {r.exchange && ` · ${r.exchange}`}
                </span>
              </div>
              {r.tracked ? (
                <span className="muted small">Tracking</span>
              ) : (
                <div className="hit-actions">
                  <button type="button" className="chip" onClick={() => add(r, false)} disabled={full}>
                    Track
                  </button>
                  <button type="button" className="chip" onClick={() => add(r, true)} disabled={full || mainFull}>
                    Track as main
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {full && <p className="muted small">You're tracking the most stocks allowed. Remove one to add another.</p>}
    </section>
  )
}

function StockRow({ stock, list, onChange, setMessage }) {
  const openChart = useOpenChart()
  const [confirming, setConfirming] = useState(false)
  const latest = stock.latest
  const run = async (action) => {
    setMessage(null)
    try {
      onChange(await action())
    } catch (e) {
      setMessage({ text: e.message, error: true })
    }
  }
  const starBlocked = !stock.main && list.main_count >= list.max_main

  return (
    <tr className={latest?.category === 'flagged' ? 'flagged' : undefined}>
      <td>
        <button
          type="button"
          className={`star ${stock.main ? 'on' : ''}`}
          aria-pressed={stock.main}
          aria-label={`Main stock: ${stock.ticker}`}
          title={stock.main ? 'Main: on the dashboard. Click to unstar.' : starBlocked ? `Up to ${list.max_main} main stocks` : 'Make it a main stock'}
          disabled={starBlocked}
          onClick={() => run(() => setMainStock(stock.ticker, !stock.main))}
        >
          <Star on={stock.main} />
        </button>
      </td>
      <td className="ticker">
        <button
          type="button"
          className="ticker-button"
          onClick={(e) => openChart(stock.ticker, e.currentTarget)}
          aria-label={`Show ${stock.ticker} chart`}
          title="Show chart"
        >
          {stock.ticker}
        </button>
      </td>
      <td className="stock-name">{stock.name || '…'}</td>
      <td className="num">{latest ? number(latest.price, 2) : '—'}</td>
      <td className={`num ${latest?.return_1d_pct > 0 ? 'up' : latest?.return_1d_pct < 0 ? 'down' : ''}`}>
        {latest ? percent(latest.return_1d_pct) : '—'}
      </td>
      <td>
        {latest ? (
          <span title={`From the ${latest.status} report of ${latest.session_date}`}>
            {latest.category === 'error' ? 'data issue' : latest.category}
          </span>
        ) : (
          <span className="muted">first report next run</span>
        )}
      </td>
      <td className="next-event">
        {stock.next_event ? (
          <a href={routes.calendar(stock.next_event.event_date)}>{stock.next_event.line}</a>
        ) : (
          <span className="muted">—</span>
        )}
      </td>
      <td className="row-actions">
        {confirming ? (
          <>
            <button type="button" className="link danger" onClick={() => run(() => removeStock(stock.ticker))}>
              Remove {stock.ticker}
            </button>
            <button type="button" className="link" onClick={() => setConfirming(false)}>
              Keep
            </button>
          </>
        ) : (
          <button type="button" className="link" onClick={() => setConfirming(true)} aria-label={`Remove ${stock.ticker}`}>
            Remove
          </button>
        )}
      </td>
    </tr>
  )
}

// Every tracked stock: star the main ones (shown on the Today tab), open charts, remove stocks
function TrackedStocks({ list, onChange }) {
  const [message, setMessage] = useState(null)
  if (!list) return null
  const main = list.stocks.filter((s) => s.main)
  const others = list.stocks.filter((s) => !s.main)
  const group = (label, stocks) => (
    <>
      <tr className="group-row">
        <th colSpan={8} scope="rowgroup">
          {label}
        </th>
      </tr>
      {stocks.map((s) => (
        <StockRow key={s.ticker} stock={s} list={list} onChange={onChange} setMessage={setMessage} />
      ))}
    </>
  )

  return (
    <section className="panel" aria-label="Tracked stocks">
      <div className="section-head">
        <h2>Tracked stocks</h2>
        <span className="muted small">Every tracked stock is in each report, alert and calendar update</span>
      </div>
      {message && <p className={message.error ? 'error' : 'notice'} role="status">{message.text}</p>}
      {list.stocks.length === 0 ? (
        <p className="muted">You're not tracking any stocks yet. Find one above.</p>
      ) : (
        <div className="table-wrap">
          <table className="tickers stocks">
            <thead>
              <tr>
                <th>
                  <span className="sr-only">Main</span>
                </th>
                <th>Ticker</th>
                <th>Company</th>
                <th className="num">Price</th>
                <th className="num">Change</th>
                <th>Status</th>
                <th>Next event</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {group(`Main: on the Today tab (${main.length} of ${list.max_main})`, main)}
              {others.length > 0 && group(`Also tracked (${others.length})`, others)}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default function StocksTab({ list, onChange }) {
  return (
    <>
      <FindStocks list={list} onChange={onChange} />
      <TrackedStocks list={list} onChange={onChange} />
    </>
  )
}
