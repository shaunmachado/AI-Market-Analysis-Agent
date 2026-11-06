import { useEffect, useRef, useState } from 'react'
import { getReport, listReports } from '../api'
import { formatDate, formatMonth } from '../format'
import { routes } from '../useRoute'
import ReportView from './ReportView'
import StatusBadge from './StatusBadge'

const PAGE_SIZE = 30

// Every report before the latest one, grouped by month, with the chosen day beside it.
export default function PreviousDaysTab({ latestDate, lastSaved, selectedDate }) {
  const [days, setDays] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const loaded = useRef(PAGE_SIZE) // how many days the list shows, kept when it refreshes
  const reportRef = useRef(null)

  const shownDate = selectedDate || days[0]?.session_date // the newest day, unless one is chosen
  const refreshShown = lastSaved?.session_date === shownDate ? lastSaved : null

  // The list: refreshed when the latest day changes or any report is saved
  useEffect(() => {
    if (!latestDate) return
    const limit = Math.min(loaded.current, 365)
    listReports({ before: latestDate, limit })
      .then((reports) => {
        setDays(reports)
        setHasMore(reports.length === limit)
      })
      .catch((e) => setError(e.message))
  }, [latestDate, lastSaved])

  // The open day: reloaded when you pick another day, or when that day is saved again
  useEffect(() => {
    if (!shownDate) return
    getReport(shownDate)
      .then((r) => {
        setReport(r)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [shownDate, refreshShown])

  // On a phone the report sits under the list, so bring it into view when a day is picked.
  // (setTimeout lets App's scroll-to-top on tab change happen first.)
  useEffect(() => {
    if (!selectedDate || window.innerWidth >= 760) return
    const timer = setTimeout(() => reportRef.current?.scrollIntoView({ behavior: 'smooth' }), 0)
    return () => clearTimeout(timer)
  }, [selectedDate])

  const loadOlder = () =>
    listReports({ before: days[days.length - 1].session_date, limit: PAGE_SIZE })
      .then((reports) => {
        loaded.current += reports.length
        setDays((current) => [...current, ...reports])
        setHasMore(reports.length === PAGE_SIZE)
      })
      .catch((e) => setError(e.message))

  const months = []
  for (const day of days) {
    const label = formatMonth(day.session_date)
    if (months.at(-1)?.label !== label) months.push({ label, days: [] })
    months.at(-1).days.push(day)
  }

  return (
    <section className="panel" aria-label="All previous days">
      <div className="section-head">
        <h2>All previous days</h2>
        <span className="muted small">
          {days.length}
          {hasMore ? '+' : ''} day{days.length === 1 ? '' : 's'}
        </span>
      </div>
      {error && <p className="error">{error}</p>}

      {days.length === 0 && !selectedDate ? (
        <p className="muted">No earlier reports yet.</p>
      ) : (
        <div className="previous-grid">
          <nav className="day-list" aria-label="Days">
            {months.map((month) => (
              <div key={month.label}>
                <h3 className="month">{month.label}</h3>
                <ul>
                  {month.days.map((d) => (
                    <li key={d.session_date}>
                      <a
                        className={`day ${d.session_date === shownDate ? 'active' : ''}`}
                        href={routes.previous(d.session_date)}
                        aria-current={d.session_date === shownDate ? 'true' : undefined}
                      >
                        <span className="day-date">{formatDate(d.session_date)}</span>
                        <span className="day-meta">
                          <StatusBadge status={d.status} /> {d.flagged_count} flagged
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {hasMore && (
              <button className="link" onClick={loadOlder}>Load older days</button>
            )}
          </nav>
          <div className="day-report" ref={reportRef}>
            {report ? <ReportView report={report} /> : <p className="muted">Loading…</p>}
          </div>
        </div>
      )}
    </section>
  )
}
