import { useEffect, useState } from 'react'
import { getAlerts, startRun } from '../api'
import { formatDateTime, formatTime } from '../format'

const STEP_NAMES = {
  flag_events: () => 'Scanning the watchlist',
  get_news: (input) => `Reading news for ${input.ticker}`,
  compute_moves: (input) => `Checking ${input.ticker} in detail`,
  market_backdrop: () => 'Checking the market and sectors',
  upcoming_events: () => 'Checking the events calendar',
}

function describe(event) {
  switch (event.type) {
    case 'started':
      return `Writing the ${event.status} report for ${event.session_date}`
    case 'tool_call': {
      const name = event.tool.split('__').pop()
      return (STEP_NAMES[name] || (() => name))(event.input || {})
    }
    case 'saved':
      return `Saved (${event.outcome.replaceAll('_', ' ')}) · $${event.cost_usd.toFixed(3)}`
    default:
      return event.message || event.type
  }
}

// One line on Discord alerts: on or off for runs started here, and the latest one sent by any run
function AlertsStatus({ refreshKey }) {
  const [info, setInfo] = useState(null)

  useEffect(() => {
    const load = () =>
      getAlerts()
        .then(setInfo)
        .catch(() => setInfo(null))
    load()
    const timer = setInterval(load, 60_000) // scheduled runs send alerts a moment after saving
    return () => clearInterval(timer)
  }, [refreshKey])

  if (!info) return null
  const last = info.alerts.find((a) => a.status !== 'pending')
  return (
    <p className="muted small alerts-status">
      {info.enabled ? 'Discord alerts on' : 'Discord alerts off for runs started here'}
      {last?.status === 'sent' &&
        ` · last sent ${formatDateTime(last.sent_at)} (${last.kind === 'summary' ? 'daily summary' : last.ticker})`}
      {last?.status === 'failed' && (
        <span className="alert-failed" title={last.error}>
          {' '}
          · last alert failed: {last.error}
        </span>
      )}
    </p>
  )
}

export default function RunPanel({ run, onStarted, lastSaved }) {
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)
  const running = run?.state === 'running'

  const start = async () => {
    setSending(true)
    setError(null)
    try {
      onStarted(await startRun())
    } catch (e) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="panel">
      <h2>Request a fresh report</h2>
      <p className="muted small">
        Runs the agent now: an intraday update while the market is open, or the final report once it has closed.
      </p>
      <button className="primary" onClick={start} disabled={running || sending}>
        {running ? 'Writing report…' : 'Run update now'}
      </button>
      {error && <p className="error">{error}</p>}
      <AlertsStatus refreshKey={`${lastSaved?.updated_at}|${run?.finished_at}`} />

      {run && run.state !== 'idle' && (
        <div className="run-log" aria-live="polite">
          <p className="muted small">
            {run.state === 'running' && `In progress · started ${formatTime(run.started_at)}`}
            {run.state === 'finished' && `Finished ${formatTime(run.finished_at)}`}
            {run.state === 'failed' && `Failed ${formatTime(run.finished_at)}`}
          </p>
          <ol>
            {run.log.map((event, i) => (
              <li key={i}>{describe(event)}</li>
            ))}
          </ol>
          {run.state === 'failed' && <p className="error">{run.error}</p>}
        </div>
      )}
    </section>
  )
}
