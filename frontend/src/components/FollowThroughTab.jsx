import { useEffect, useState } from 'react'
import { getFollowups, refreshFollowups } from '../api'
import { useOpenChart } from '../chartContext'
import { formatDateTime, formatShortDate, percent } from '../format'
import { routes } from '../useRoute'

const HORIZONS = { 1: 'Next day', 5: 'A week later', 20: 'A month later' }
const OUTCOMES = [
  ['held', 'Held', 'gave back less than a quarter of the move'],
  ['faded', 'Faded', 'gave back a quarter or more'],
  ['reversed', 'Reversed', 'gave back all of it, or more'],
]

// The middle (median) price change since the move, in words: "typically 1.06% further" or "typically 2.10% back"
function typical(pct) {
  if (pct === 0) return 'typically flat since'
  return `typically ${Math.abs(pct).toFixed(2)}% ${pct > 0 ? 'further' : 'back'}`
}

// One row of the patterns: a 100% bar split into held, faded and reversed, with the counts in words
function PatternRow({ group }) {
  const { judged } = group
  return (
    <div className="pattern-row">
      <div className="pattern-label">{group.label}</div>
      {judged ? (
        <div className="outcome-bar" role="img" aria-label={`${group.label}: ${group.held} held, ${group.faded} faded, ${group.reversed} reversed`}>
          {OUTCOMES.filter(([key]) => group[key]).map(([key, label]) => (
            <span
              key={key}
              className={`seg ${key}`}
              style={{ flexGrow: group[key] }}
              data-tip={`${label}: ${group[key]} of ${judged} (${Math.round((group[key] / judged) * 100)}%)`}
            />
          ))}
        </div>
      ) : (
        <div className="outcome-bar empty" />
      )}
      <div className="pattern-text muted small">
        {judged ? (
          <>
            {group.held} held · {group.faded} faded · {group.reversed} reversed
            {group.median_follow_pct != null && <> · {typical(group.median_follow_pct)}</>}
            {!group.enough && <span className="too-few"> · too few to tell</span>}
          </>
        ) : (
          'No moves to judge yet'
        )}
      </div>
    </div>
  )
}

function Patterns({ title, groups }) {
  if (!groups?.length) return null
  return (
    <div className="patterns">
      <h3>{title}</h3>
      {groups.map((g) => (
        <PatternRow key={g.label} group={g} />
      ))}
    </div>
  )
}

function Outcome({ move, horizon }) {
  const result = move.outcomes[String(horizon)]
  if (!result) return <span className="muted">not yet</span>
  return (
    <span className="outcome">
      <span className={`swatch ${result}`} aria-hidden="true" />
      {result}
      {move.surprise && (
        <span className="surprise" title={move.surprise_kind}>
          {' '}
          · surprise
        </span>
      )}
    </span>
  )
}

function MoveRow({ move, horizon, latestDate }) {
  const openChart = useOpenChart()
  const day = move.session_date
  const after = (n) => {
    const value = move[`after_${n}d`]
    return (
      <td className={`num ${value > 0 ? 'up' : value < 0 ? 'down' : ''}`}>{value == null ? <span className="muted">…</span> : percent(value)}</td>
    )
  }
  return (
    <tr className={move.surprise ? 'surprise-row' : undefined}>
      <td>
        <a href={day === latestDate ? routes.today : routes.previous(day)}>{formatShortDate(day)}</a>
      </td>
      <td className="ticker">
        <button type="button" className="ticker-button" onClick={(e) => openChart(move.ticker, e.currentTarget)} aria-label={`Show ${move.ticker} chart`}>
          {move.ticker}
        </button>
      </td>
      <td className={`num ${move.move_pct > 0 ? 'up' : 'down'}`}>{percent(move.move_pct)}</td>
      <td>{move.kind}</td>
      <td title={move.why || undefined}>{move.reason_label}</td>
      {after(1)}
      {after(5)}
      {after(20)}
      <td>
        <Outcome move={move} horizon={horizon} />
      </td>
      <td>
        <a href={routes.stories(day, move.ticker)} className="story-link">
          {move.story ? move.story.status === 'no_news' ? 'No newer news' : `Story: ${move.story.verdict.replace('_', ' ')}` : 'Check news'}
        </a>
      </td>
    </tr>
  )
}

// What the price did after each flagged move: patterns first, then every move
export default function FollowThroughTab({ version, refresh, onRefreshStarted, latestDate }) {
  const [horizon, setHorizon] = useState(5)
  const [ticker, setTicker] = useState('')
  const [onlySurprises, setOnlySurprises] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = refresh?.state === 'running'

  useEffect(() => {
    let current = true
    getFollowups(horizon, ticker)
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [horizon, ticker, version])

  const refreshNow = async () => {
    setStarting(true)
    setError(null)
    try {
      onRefreshStarted(await refreshFollowups())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const updated = data?.updated
  const status = running
    ? refresh.message || 'Refreshing…'
    : updated
      ? `Prices updated ${formatDateTime(updated.finished_at)}`
      : 'Not worked out yet'
  const shown = (data?.moves || []).filter((m) => !onlySurprises || m.surprise)
  const p = data?.patterns

  return (
    <>
      <section className="panel followthrough" aria-label="How flagged moves played out">
        <div className="section-head">
          <h2>How flagged moves played out</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={refreshNow} disabled={running || starting}>
              {running ? 'Refreshing…' : 'Refresh prices'}
            </button>
          </div>
        </div>
        <p className="muted small">
          The price 1, 5 and 20 trading days after each move flagged in a final report, from Yahoo Finance. Prices only:
          for what the news said since, see <a href={routes.stories()}>Story updates</a>.
        </p>
        {error && <p className="error">{error}</p>}
        {refresh?.state === 'failed' && <p className="error">The refresh didn't finish: {refresh.error}</p>}
        {!running && updated?.status === 'partial' && <p className="muted small">Some prices couldn't be read: {updated.message}</p>}

        <div className="horizon-picker" role="group" aria-label="How long after the move">
          {Object.entries(HORIZONS).map(([n, label]) => (
            <button key={n} type="button" className="chip" aria-pressed={horizon === Number(n)} onClick={() => setHorizon(Number(n))}>
              {label}
            </button>
          ))}
        </div>

        {p && p.all.moves === 0 ? (
          <p className="muted">No flagged moves in final reports yet. They're followed up after each final report.</p>
        ) : (
          p && (
            <>
              <ul className="outcome-legend" aria-label="Key">
                {OUTCOMES.map(([key, label, meaning]) => (
                  <li key={key}>
                    <span className={`swatch ${key}`} aria-hidden="true" />
                    <strong>{label}</strong> <span className="muted">{meaning}</span>
                  </li>
                ))}
              </ul>
              <div className="patterns-all">
                <PatternRow group={p.all} />
              </div>
              <div className="patterns-grid">
                <Patterns title="By kind of move" groups={p.by_kind} />
                <Patterns title="By reason" groups={p.by_reason} />
                <Patterns title="By direction" groups={p.by_direction} />
              </div>
              <p className="muted small">
                History, not a forecast. Groups with fewer than 5 judged moves are marked "too few to tell".
              </p>
            </>
          )
        )}
      </section>

      <section className="panel" aria-label="Flagged moves">
        <div className="section-head">
          <h2>Flagged moves</h2>
          <div className="moves-filters">
            <label className="small">
              Stock{' '}
              <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
                <option value="">All</option>
                {(data?.tickers || []).map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="small">
              <input type="checkbox" checked={onlySurprises} onChange={(e) => setOnlySurprises(e.target.checked)} /> Only surprises
            </label>
          </div>
        </div>
        {shown.length === 0 ? (
          <p className="muted">{data ? 'No flagged moves to show.' : 'Loading…'}</p>
        ) : (
          <div className="table-wrap">
            <table className="tickers moves">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Ticker</th>
                  <th className="num">Move</th>
                  <th>Kind</th>
                  <th>Reason</th>
                  <th className="num">Next day</th>
                  <th className="num">1 week</th>
                  <th className="num">1 month</th>
                  <th>{HORIZONS[horizon]}</th>
                  <th>
                    <span className="sr-only">News</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((m) => (
                  <MoveRow key={`${m.session_date}-${m.ticker}`} move={m} horizon={horizon} latestDate={latestDate} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
