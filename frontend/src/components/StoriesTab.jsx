import { useEffect, useRef, useState } from 'react'
import { checkStory, getStories } from '../api'
import { formatDateTime, formatFullDate, formatShortDate, percent, safeUrl } from '../format'
import { routes } from '../useRoute'

const AFTER = [
  [1, 'next day'],
  [5, 'a week'],
  [20, 'a month'],
]

// "+1.20% next day, -3.40% a week (reversed)": the price since, in one line
function sinceLine(move) {
  const parts = AFTER.filter(([n]) => move[`after_${n}d`] != null).map(([n, label]) => `${percent(move[`after_${n}d`])} ${label}`)
  if (!parts.length) return 'Price since: not known yet'
  const lastKnown = [...AFTER].reverse().find(([n]) => move.outcomes[String(n)])
  return `Price since: ${parts.join(', ')}${lastKnown ? ` (${move.outcomes[String(lastKnown[0])]} after ${lastKnown[1]})` : ''}`
}

function MoveHeading({ move, sessionDate, ticker }) {
  return (
    <div className="story-head">
      <strong>{ticker}</strong>
      <span>
        move of {formatShortDate(sessionDate)}
        {move && (
          <>
            {' · '}
            <span className={move.move_pct > 0 ? 'up' : 'down'}>{percent(move.move_pct)}</span> · {move.reason_label}
          </>
        )}
      </span>
    </div>
  )
}

// `inPicked`: shown under the picked move, which already says what happened at the time and since
function Check({ check, inPicked = false }) {
  const move = check.move
  return (
    <article className="story" aria-label={`${check.ticker}, move of ${check.session_date}`}>
      <header>
        <MoveHeading move={move} sessionDate={check.session_date} ticker={check.ticker} />
        <span className={`verdict ${check.status === 'failed' ? 'failed' : check.verdict}`}>
          {check.status === 'failed' ? 'Check failed' : check.verdict_label}
        </span>
      </header>
      {move?.why && !inPicked && <p className="muted small">At the time: {move.why}</p>}
      <p className="story-update">{check.status === 'failed' ? check.error : check.update_text}</p>
      {check.sources.length > 0 && (
        <ul className="story-sources">
          {check.sources.map((s, i) => (
            <li key={i}>
              <a href={safeUrl(s.url)} target="_blank" rel="noreferrer">
                {s.title}
              </a>{' '}
              <span className="muted small">{s.publisher}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">
        {move && !inPicked && <>{sinceLine(move)} · </>}
        Checked {formatDateTime(check.finished_at)} ·{' '}
        {check.trigger === 'surprise' ? `automatically: a surprise (${move?.surprise_kind || 'unexpected move'})` : 'on request'}
        {check.cost_usd > 0 && ` · $${check.cost_usd.toFixed(3)}`}
      </p>
    </article>
  )
}

function CheckButton({ sessionDate, ticker, job, onStarted, label = 'Check for updates' }) {
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = job?.state === 'running'
  const mine = job?.target?.session_date === sessionDate && job?.target?.ticker === ticker
  const start = async () => {
    setStarting(true)
    setError(null)
    try {
      onStarted(await checkStory(sessionDate, ticker))
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }
  return (
    <div className="check-action">
      <button className="primary" onClick={start} disabled={running || starting} aria-label={`${label}: ${ticker}, ${sessionDate}`}>
        {running && mine ? 'Checking…' : label}
      </button>
      {running && mine && (
        <span className="muted small" aria-live="polite">
          {job.message}
        </span>
      )}
      {mine && job?.state === 'failed' && <span className="error">The check didn't finish: {job.error}</span>}
      {error && <span className="error">{error}</span>}
    </div>
  )
}

// What the news has said since each flagged move. Automatic for surprises; any other move on request.
export default function StoriesTab({ version, job, onCheckStarted, picked }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const pickedRef = useRef(null)

  useEffect(() => {
    let current = true
    getStories()
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [version])

  useEffect(() => {
    if (!picked?.date) return
    const timer = setTimeout(() => pickedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [picked?.date, picked?.ticker])

  const checks = data?.checks || []
  const isPicked = (date, ticker) => picked?.date === date && picked?.ticker === ticker
  const pickedChecks = picked?.date ? checks.filter((c) => isPicked(c.session_date, c.ticker)) : []
  const pickedMove = picked?.date
    ? (data?.unchecked || []).find((m) => isPicked(m.session_date, m.ticker)) || pickedChecks[0]?.move || null
    : null
  const maxCost = data ? `$${data.max_cost_usd.toFixed(2)}` : '$0.10'

  return (
    <>
      <section className="panel stories" aria-label="Story updates">
        <div className="section-head">
          <h2>Story updates</h2>
        </div>
        <p className="muted small">
          What the news has said since a flagged move. Moves that turn out to be surprises (reversed within a week, or kept
          going by as much again) are checked automatically after the next final report. Any other move can be checked here: each
          check costs a few cents (at most {maxCost}), and nothing if there are no newer headlines. For prices only, see{' '}
          <a href={routes.followThrough}>Follow-through</a>.
        </p>
        {error && <p className="error">{error}</p>}

        {picked?.date && data && (
          <div className="picked-move" ref={pickedRef} aria-label="Picked move">
            <h3>
              {picked.ticker}'s move of {formatFullDate(picked.date)}
            </h3>
            {pickedMove ? (
              <>
                {pickedMove.why && <p className="muted small">At the time: {pickedMove.why}</p>}
                <p className="muted small">{sinceLine(pickedMove)}</p>
              </>
            ) : null}
            {pickedChecks.length > 0 && <p className="small">Latest update below. You can check again for anything newer.</p>}
            <CheckButton
              sessionDate={picked.date}
              ticker={picked.ticker}
              job={job}
              onStarted={onCheckStarted}
              label={pickedChecks.length ? 'Check again' : 'Check for updates'}
            />
            {pickedChecks.slice(0, 1).map((c) => (
              <Check key={c.id} check={c} inPicked />
            ))}
          </div>
        )}

        <h3 className="stories-subhead">Latest updates</h3>
        {checks.length === 0 ? (
          <p className="muted">{data ? 'No story updates yet.' : 'Loading…'}</p>
        ) : (
          <div className="story-list">
            {checks.slice(0, 30).map((c) => (
              <Check key={c.id} check={c} />
            ))}
          </div>
        )}
      </section>

      <section className="panel" aria-label="Moves you can check">
        <div className="section-head">
          <h2>Moves you can check</h2>
          <span className="muted small">Flagged in the last {data?.days ?? 30} days, not checked yet</span>
        </div>
        {(data?.unchecked || []).length === 0 ? (
          <p className="muted">{data ? 'Every recent flagged move has been checked.' : 'Loading…'}</p>
        ) : (
          <ul className="check-list">
            {data.unchecked.map((m) => (
              <li key={`${m.session_date}-${m.ticker}`}>
                <div>
                  <MoveHeading move={m} sessionDate={m.session_date} ticker={m.ticker} />
                  {m.why && <p className="muted small">{m.why}</p>}
                </div>
                <CheckButton sessionDate={m.session_date} ticker={m.ticker} job={job} onStarted={onCheckStarted} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
  )
}
