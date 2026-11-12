import { useEffect, useMemo, useRef, useState } from 'react'
import { getCalendar, startCalendarScan } from '../api'
import { formatDateTime, formatFullDate, formatMonth, formatShortDate, safeUrl } from '../format'
import { routes } from '../useRoute'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const KINDS = { earnings: 'Earnings', dividend: 'Ex-dividend', news: 'In the news' }
const MAX_NAMES = 3 // company names shown in a day's box; the rest show as "+N more"

// Dates are handled as YYYY-MM-DD text, using UTC so time zones can't shift a day
const iso = (d) => d.toISOString().slice(0, 10)
const utc = (day) => new Date(`${day}T00:00:00Z`)
const localToday = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Every day shown for a month: whole weeks, Monday to Sunday
function monthGrid(month) {
  const first = utc(`${month}-01`)
  const start = new Date(first)
  start.setUTCDate(1 - ((first.getUTCDay() + 6) % 7))
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0))
  const end = new Date(last)
  end.setUTCDate(last.getUTCDate() + 6 - ((last.getUTCDay() + 6) % 7))
  const days = []
  for (const d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) days.push(iso(d))
  return { start: iso(start), end: iso(end), days }
}

function shiftMonth(month, by) {
  const d = utc(`${month}-01`)
  d.setUTCMonth(d.getUTCMonth() + by)
  return iso(d).slice(0, 7)
}

// News items carry their date as text, or (older yfinance) as seconds since 1970
function publishedOn(value) {
  if (typeof value === 'number') return iso(new Date(value * 1000))
  return /^\d{4}-\d{2}-\d{2}/.test(value || '') ? value.slice(0, 10) : null
}

// "Reported Oct 28: headline" under an earnings event, or on the day results were filed
function Reported({ filing, eventDate }) {
  return (
    <p className="cal-reported">
      <strong>Reported{filing.filing_date !== eventDate ? ` on ${formatShortDate(filing.filing_date)}` : ''}:</strong>{' '}
      {filing.headline || 'Results were filed with the SEC.'}{' '}
      <a href={routes.filings(filing.accession)}>{filing.headline ? 'First take' : 'See the filing'}</a>
    </p>
  )
}

function EventCard({ event, reported }) {
  return (
    <article className="cal-event">
      <div className="cal-event-head">
        <strong>{event.company}</strong>
        <span className="muted small">{event.ticker}</span>
        <span className={`kind kind-${event.kind}`}>{KINDS[event.kind]}</span>
      </div>
      <h3>{event.title}</h3>
      {event.date_note && <p className="muted small">{event.date_note}</p>}
      {reported && <Reported filing={reported} eventDate={event.event_date} />}
      {event.details && <p>{event.details}</p>}
      {event.news_note && (
        <p>
          <strong>In the news:</strong> {event.news_note}
        </p>
      )}
      {event.sources.length > 0 && (
        <ul className="cal-sources">
          {event.sources.map((s, i) => (
            <li key={i}>
              {safeUrl(s.url) ? (
                <a href={safeUrl(s.url)} target="_blank" rel="noopener noreferrer">
                  {s.title || s.url}
                </a>
              ) : (
                s.title
              )}
              {s.publisher && <span className="muted small"> · {s.publisher}</span>}
              {publishedOn(s.published) && (
                <span className="muted small"> · {formatShortDate(publishedOn(s.published))}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

// A month calendar of upcoming events: each day shows just the company names.
// Clicking a day opens its events below, with what the news says and links to the articles.
export default function CalendarTab({ selectedDate, version, scan, onScanStarted }) {
  const [month, setMonth] = useState(() => (selectedDate || localToday()).slice(0, 7))
  const [data, setData] = useState(null)
  const [dayEvents, setDayEvents] = useState(null)
  const [dayReported, setDayReported] = useState([])
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const dayRef = useRef(null)
  const grid = useMemo(() => monthGrid(month), [month])
  const running = scan?.state === 'running'
  const today = data?.today || localToday()

  // Opening a day (or following a link to one) shows its month
  useEffect(() => {
    if (selectedDate) setMonth(selectedDate.slice(0, 7))
  }, [selectedDate])

  // The month's events: reloaded when the month changes or the calendar is updated
  useEffect(() => {
    let current = true
    getCalendar(grid.start, grid.end)
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [grid.start, grid.end, version])

  // The open day's events (fetched on their own, since you can browse to another month)
  useEffect(() => {
    if (!selectedDate) return
    let current = true
    setDayEvents(null)
    getCalendar(selectedDate, selectedDate)
      .then((body) => {
        if (!current) return
        setDayEvents(body.events)
        setDayReported(body.reported || [])
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [selectedDate, version])

  // Bring the day's events into view when a day is picked (after App's scroll-to-top on tab change)
  useEffect(() => {
    if (!selectedDate) return
    const timer = setTimeout(() => dayRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [selectedDate])

  const update = async () => {
    setStarting(true)
    setError(null)
    try {
      onScanStarted(await startCalendarScan())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const byDay = {}
  for (const e of data?.events || []) (byDay[e.event_date] ||= []).push(e)
  // Results show on the day they were actually filed too, in case the calendar's date was out (or missing)
  for (const r of data?.reported || []) (byDay[r.filing_date] ||= []).push({ ticker: r.ticker, company: r.company })
  const reportedFor = new Map(dayReported.filter((r) => r.event_id != null).map((r) => [r.event_id, r]))
  const dayIds = new Set((dayEvents || []).map((e) => e.id))
  const filedToday = dayReported.filter((r) => r.filing_date === selectedDate && !dayIds.has(r.event_id))
  const last = data?.last_scan
  const status = running
    ? scan.message || 'Updating…'
    : last?.finished_at
      ? `Updated ${formatDateTime(last.finished_at)}`
      : 'Not updated yet'

  return (
    <>
      <section className="panel calendar" aria-label="Upcoming events calendar">
        <div className="section-head">
          <h2>Upcoming events</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={update} disabled={running || starting}>
              {running ? 'Updating…' : 'Update now'}
            </button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        {scan?.state === 'failed' && <p className="error">The update didn't finish: {scan.error}</p>}
        {!running && last?.status === 'partial' && (
          <p className="muted small">Updated, but some sources couldn't be read: {last.message}</p>
        )}

        <div className="cal-nav">
          <button type="button" className="chip" onClick={() => setMonth(shiftMonth(month, -1))} aria-label="Previous month">
            ‹
          </button>
          <h3 className="cal-month">{formatMonth(`${month}-01`)}</h3>
          <button type="button" className="chip" onClick={() => setMonth(shiftMonth(month, 1))} aria-label="Next month">
            ›
          </button>
          {month !== today.slice(0, 7) && (
            <button type="button" className="link" onClick={() => setMonth(today.slice(0, 7))}>
              This month
            </button>
          )}
        </div>

        <div className="cal-grid">
          {WEEKDAYS.map((d) => (
            <div key={d} className="cal-weekday" aria-hidden="true">
              {d}
            </div>
          ))}
          {grid.days.map((day, i) => {
            const companies = [...new Map((byDay[day] || []).map((e) => [e.ticker, e])).values()]
            const classes = [
              'cal-day',
              day.slice(0, 7) !== month && 'other-month',
              i % 7 >= 5 && 'weekend',
              day < today && 'past',
              day === today && 'today',
              day === selectedDate && 'selected',
            ].filter(Boolean)
            return (
              <a
                key={day}
                className={classes.join(' ')}
                href={routes.calendar(day)}
                aria-label={`${formatFullDate(day)}: ${companies.map((c) => c.company).join(', ') || 'no events'}`}
                aria-current={day === selectedDate ? 'date' : undefined}
              >
                <span className="cal-date">{Number(day.slice(8))}</span>
                {companies.slice(0, MAX_NAMES).map((c) => (
                  <span key={c.ticker} className="cal-name">
                    <span className="long">{c.company}</span>
                    <span className="short">{c.ticker}</span>
                  </span>
                ))}
                {companies.length > MAX_NAMES && (
                  <span className="cal-more">
                    <span className="long">+{companies.length - MAX_NAMES} more</span>
                    <span className="short">+{companies.length - MAX_NAMES}</span>
                  </span>
                )}
              </a>
            )
          })}
        </div>
        <p className="muted small cal-note">
          Earnings and ex-dividend dates come from Yahoo Finance. Other events are found in recent news, each with a
          link to its source. The calendar updates every trading day when the market opens. Once a company files its
          results with the SEC, its day says “Reported”, with a link to the filing.
        </p>
      </section>

      {selectedDate && (
        <section className="panel cal-day-detail" id="calendar-day" ref={dayRef} aria-label={`Events on ${formatFullDate(selectedDate)}`}>
          <div className="section-head">
            <h2>{formatFullDate(selectedDate)}</h2>
            <a className="link" href={routes.calendar()}>
              Close
            </a>
          </div>
          {dayEvents === null ? (
            <p className="muted">Loading…</p>
          ) : dayEvents.length === 0 && filedToday.length === 0 ? (
            <p className="muted">Nothing on the calendar for this day.</p>
          ) : (
            <>
              {dayEvents.map((e) => (
                <EventCard key={e.id} event={e} reported={reportedFor.get(e.id)} />
              ))}
              {filedToday.map((r) => (
                <article key={r.accession} className="cal-event">
                  <div className="cal-event-head">
                    <strong>{r.company}</strong>
                    <span className="muted small">{r.ticker}</span>
                    <span className="kind kind-earnings">Reported</span>
                  </div>
                  <h3>Results announced</h3>
                  <Reported filing={r} eventDate={selectedDate} />
                </article>
              ))}
            </>
          )}
        </section>
      )}
    </>
  )
}
