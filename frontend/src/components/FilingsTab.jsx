import { useEffect, useRef, useState } from 'react'
import { checkFilings, getFilings, readFiling } from '../api'
import { useOpenChart } from '../chartContext'
import { formatDateTime, formatShortDate, safeUrl } from '../format'
import { routes } from '../useRoute'

const KINDS = [
  ['all', 'All'],
  ['results', 'Results'],
  ['announcement', 'Announcements'],
  ['report', 'Reports'],
]
const inKind = (filing, kind) =>
  kind === 'all' ||
  (kind === 'report'
    ? ['quarterly', 'annual'].includes(filing.kind)
    : kind === 'announcement'
      ? ['announcement', 'late', 'foreign'].includes(filing.kind)
      : filing.kind === kind)

// $77.67B, $420.5M, $3.72: the same wording as the Discord messages
function money(value, unit) {
  if (value == null) return '—'
  const sign = value < 0 ? '-' : ''
  const size = Math.abs(value)
  if (unit !== 'USD') return `${sign}$${size.toFixed(2)}`
  // $999.96M rounds to a billion: show "$1.00B", not "$1000.0M"
  if (size >= 1e9 || (size / 1e6).toFixed(1) === '1000.0') return `${sign}$${(size / 1e9).toFixed(2)}B`
  if (size >= 1e6 || size.toFixed(0) === '1000000') return `${sign}$${(size / 1e6).toFixed(1)}M`
  return `${sign}$${Math.round(size).toLocaleString()}`
}

const change = (pct) => (pct == null ? '—' : `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`)
const direction = (pct) => (pct == null || pct === 0 ? '' : pct > 0 ? 'up' : 'down')

const CHECKS = {
  confirmed: ['ok', '✓ Confirmed', 'The quarterly report gives the same figure.'],
  pending: ['wait', 'Not checked yet', 'It will be compared with the quarterly report when that is filed.'],
  not_checked: ['wait', 'Can’t be checked', 'The report doesn’t give this figure for the quarter on its own.'],
}

function Earlier({ period, unit }) {
  if (!period) return <span className="muted">—</span>
  return (
    <span title={`Quarter to ${period.end}${period.derived ? ': worked out as the year minus the first nine months' : ''}`}>
      {period.derived && '≈ '}
      {money(period.value, unit)}
    </span>
  )
}

// Reported figures next to the periods before. Every comparison is worked out in code from the SEC's data.
function Figures({ figures, caption }) {
  if (!figures || figures.rows.length === 0) return null
  const year = figures.basis === 'year'
  const announced = figures.source === 'announcement'
  return (
    <div className="filing-figures">
      <div className="table-wrap">
        <table className="tickers figures">
          <caption>
            {caption} · {year ? 'year' : 'quarter'} to {figures.period_end ? formatShortDate(figures.period_end) : 'an unknown date'}
          </caption>
          <thead>
            <tr>
              <th scope="col">Figure</th>
              <th scope="col" className="num">{announced ? 'Reported' : 'In the report'}</th>
              {!year && <th scope="col" className="num">Quarter before</th>}
              {!year && <th scope="col" className="num">Change</th>}
              <th scope="col" className="num">A year earlier</th>
              <th scope="col" className="num">Change</th>
              {announced && <th scope="col">Checked against the report</th>}
            </tr>
          </thead>
          <tbody>
            {figures.rows.map((r) => {
              const [tone, label, tip] =
                r.check === 'differs'
                  ? ['bad', `✗ The report says ${money(r.report_value, r.unit)}`, 'The quarterly report gives a different figure.']
                  : CHECKS[r.check] || []
              return (
                <tr key={r.metric}>
                  <th scope="row" title={r.quote ? `From the filing: “${r.quote}”` : undefined}>{r.label}</th>
                  <td className="num">{money(r.value, r.unit)}</td>
                  {!year && <td className="num"><Earlier period={r.prior} unit={r.unit} /></td>}
                  {!year && <td className={`num ${direction(r.change_prior_pct)}`}>{change(r.change_prior_pct)}</td>}
                  <td className="num"><Earlier period={r.year_ago} unit={r.unit} /></td>
                  <td className={`num ${direction(r.change_year_pct)}`}>{change(r.change_year_pct)}</td>
                  {announced && <td className={`figure-check ${tone}`} title={tip}>{label}</td>}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {figures.margins.length > 0 && (
        <p className="muted small">
          {figures.margins
            .map((m) => `${m.label} ${m.value.toFixed(1)}%${m.year_ago != null ? ` (${m.year_ago.toFixed(1)}% a year earlier)` : ''}`)
            .join(' · ')}
        </p>
      )}
    </div>
  )
}

function Entries({ title, entries, badge }) {
  if (!entries || entries.length === 0) return null
  return (
    <div className="take-part">
      <h4>{title}</h4>
      <ul>
        {entries.map((e, i) => (
          <li key={i}>
            {badge && <span className={`guidance ${e.direction}`}>{badge(e)}</span>} {e.text}
            <details>
              <summary>From the filing</summary>
              <blockquote>{e.quote}</blockquote>
            </details>
          </li>
        ))}
      </ul>
    </div>
  )
}

const DIRECTIONS = { raised: 'Raised', lowered: 'Lowered', maintained: 'Kept', new: 'New', withdrawn: 'Withdrawn' }

function ReadButton({ filing, job, onStarted, label }) {
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = job?.state === 'running'
  const mine = job?.target?.accession === filing.accession
  const start = async () => {
    setStarting(true)
    setError(null)
    try {
      onStarted(await readFiling(filing.accession))
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }
  return (
    <div className="check-action">
      <button
        className={label === 'Read this filing' ? 'primary' : 'chip'}
        onClick={start}
        disabled={running || starting}
        aria-label={`${label}: ${filing.ticker}, ${filing.title}, filed ${filing.filing_date}`}
      >
        {running && mine ? 'Reading…' : label}
      </button>
      {running && mine && (
        <span className="muted small" aria-live="polite">
          {job.message}
        </span>
      )}
      {mine && job?.state === 'failed' && <span className="error">The read didn't finish: {job.error}</span>}
      {error && <span className="error">{error}</span>}
    </div>
  )
}

function Filing({ filing, picked, job, onReadStarted, cardRef }) {
  const openChart = useOpenChart()
  const take = filing.read
  const read = take?.status === 'ok'
  return (
    <article
      className={`filing ${picked ? 'picked' : ''} ${read ? 'read' : ''}`}
      ref={cardRef}
      aria-label={`${filing.ticker}: ${filing.title}, filed ${filing.filing_date}`}
    >
      <header>
        <div className="story-head">
          <button type="button" className="ticker-button" onClick={(e) => openChart(filing.ticker, e.currentTarget)} aria-label={`Show ${filing.ticker} chart`}>
            {filing.ticker}
          </button>
          <a className="filing-title" href={routes.filings(filing.accession)}>
            {filing.title}
          </a>
        </div>
        <div className="filing-tags">
          {filing.serious && <span className="verdict serious">Worth a look</span>}
          <span className="verdict">{filing.kind_label}</span>
        </div>
      </header>
      <p className="muted small">
        Filed {formatDateTime(filing.filed_at)} · form {filing.form}
        {filing.report_date && ['quarterly', 'annual'].includes(filing.kind) && ` · period to ${formatShortDate(filing.report_date)}`} ·{' '}
        <a href={safeUrl(filing.url)} target="_blank" rel="noopener noreferrer">
          the filing on sec.gov
        </a>
      </p>

      {filing.figures?.rows.length > 0 && (
        <details className="report-figures">
          <summary>Figures from the report ({filing.figures.rows.length}), from the SEC’s own data</summary>
          <Figures figures={filing.figures} caption="As filed" />
        </details>
      )}

      {read && (
        <>
          <p className="take-headline">{take.headline}</p>
          <Figures figures={take.figures} caption="Figures as announced" />
          <Entries title="Key points" entries={take.points} />
          <Entries title="Guidance" entries={take.guidance} badge={(g) => DIRECTIONS[g.direction] || 'New'} />
          <Entries title="What changed since the last announcement" entries={take.changes} />
          {take.notes.map((note, i) => (
            <p key={i} className="muted small take-note">
              Note: {note}
            </p>
          ))}
          <p className="muted small">
            First take by Claude, {formatDateTime(take.finished_at)} · {take.trigger === 'automatic' ? 'automatically' : 'on request'}
            {take.cost_usd > 0 && ` · $${take.cost_usd.toFixed(3)}`} · read from{' '}
            <a href={safeUrl(take.document_url)} target="_blank" rel="noopener noreferrer">
              {take.document}
            </a>
          </p>
        </>
      )}
      {take?.status === 'failed' && <p className="error">The last read failed: {take.error}</p>}
      {take?.status === 'running' ? (
        <p className="muted small">Being read…</p>
      ) : (
        <ReadButton filing={filing} job={job} onStarted={onReadStarted} label={read ? 'Read again' : 'Read this filing'} />
      )}
    </article>
  )
}

// What tracked companies have filed with the SEC, with Claude's first take on each one that's been read.
export default function FilingsTab({ version, checkJob, readJob, onCheckStarted, onReadStarted, picked }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const [ticker, setTicker] = useState('')
  const [kind, setKind] = useState('all')
  const [onlyRead, setOnlyRead] = useState(false)
  const pickedRef = useRef(null)

  useEffect(() => {
    let current = true
    getFilings()
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

  const loaded = Boolean(data)
  useEffect(() => {
    if (!picked || !loaded) return
    const timer = setTimeout(() => pickedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [picked, loaded])

  const check = async () => {
    setStarting(true)
    setError(null)
    try {
      onCheckStarted(await checkFilings())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const job = checkJob || data?.check
  const reading = readJob || data?.read
  const running = job?.state === 'running'
  const last = data?.checked
  const status = running
    ? job.message || 'Checking…'
    : last
      ? `Checked ${formatDateTime(last.finished_at)}`
      : loaded
        ? 'Not checked yet'
        : ''
  const all = data?.filings || []
  // A filing picked by its link is always shown, whatever the filters say
  const shown = all.filter(
    (f) =>
      f.accession === picked ||
      ((!ticker || f.ticker === ticker) && inKind(f, kind) && (!onlyRead || f.read?.status === 'ok')),
  )
  const maxCost = data ? `$${data.max_cost_usd.toFixed(2)}` : '$0.50'

  return (
    <>
      <section className="panel filings" aria-label="Company filings">
        <div className="section-head">
          <h2>Company filings</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={check} disabled={running || starting}>
              {running ? 'Checking…' : 'Check now'}
            </button>
          </div>
        </div>
        <p className="muted small">
          What your tracked companies file with the SEC: results, other announcements, and quarterly and annual reports. Looking
          for filings is free. A new results announcement is read by Claude automatically; any other filing has a “Read this
          filing” button (a few cents, at most {maxCost}). Every point is checked against the filing’s own words, and every
          comparison is worked out in code from the SEC’s figures.
        </p>
        {error && <p className="error">{error}</p>}
        {job?.state === 'failed' && <p className="error">The check didn't finish: {job.error}</p>}
        {!running && last?.status === 'partial' && <p className="muted small">Checked, with problems: {last.message}</p>}
        {data && !data.contact_set && !last && (
          <p className="notice-box">
            To look for filings, set <code>SEC_CONTACT</code> to your name and email where the API runs, then restart it. The SEC
            asks automated tools to say who they are.
          </p>
        )}

        {data?.expected.length > 0 && (
          <ul className="expected" aria-label="Results expected">
            {data.expected.map((e) => (
              <li key={`${e.ticker}-${e.event_date}`}>
                <strong>{e.company}</strong> ({e.ticker}) was due to report on{' '}
                <a href={routes.calendar(e.event_date)}>{formatShortDate(e.event_date)}</a>
                {!e.confirmed && ' (date not confirmed)'}: nothing filed yet.
              </li>
            ))}
          </ul>
        )}

        <div className="moves-filters filings-filters">
          <label>
            Stock
            <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
              <option value="">All</option>
              {(data?.tickers || []).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <div className="horizon-picker" role="group" aria-label="Kind of filing">
            {KINDS.map(([key, label]) => (
              <button key={key} type="button" className="chip" aria-pressed={kind === key} onClick={() => setKind(key)}>
                {label}
              </button>
            ))}
          </div>
          <label>
            <input type="checkbox" checked={onlyRead} onChange={(e) => setOnlyRead(e.target.checked)} /> Only with a first take
          </label>
        </div>

        {shown.length === 0 ? (
          <p className="muted">
            {!loaded ? 'Loading…' : all.length === 0 ? 'No filings listed yet. Press “Check now” to look for them.' : 'No filings match.'}
          </p>
        ) : (
          <div className="filing-list">
            {shown.slice(0, 80).map((f) => (
              <Filing
                key={`${f.ticker}-${f.accession}`}
                filing={f}
                picked={f.accession === picked}
                job={reading}
                onReadStarted={onReadStarted}
                cardRef={f.accession === picked ? pickedRef : undefined}
              />
            ))}
          </div>
        )}
        {shown.length > 80 && <p className="muted small">Showing the latest 80 of {shown.length}. Pick a stock to see its older filings.</p>}
        {data?.not_covered.length > 0 && (
          <p className="muted small">
            No company filings for {data.not_covered.join(', ')}: funds and some companies listed elsewhere don’t file these forms.
          </p>
        )}
      </section>
    </>
  )
}
