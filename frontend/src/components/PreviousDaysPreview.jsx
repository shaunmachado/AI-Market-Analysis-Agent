import { useEffect, useState } from 'react'
import { getReport, listReports } from '../api'
import { formatDate, percent } from '../format'
import { routes } from '../useRoute'
import StatusBadge from './StatusBadge'

const PREVIEW_DAYS = 3
const TICKERS_PER_CARD = 4

// The last few days before the latest report, as cards on the Today tab.
// Each card opens that day on the Previous days tab, which lists every day.
export default function PreviousDaysPreview({ latestDate, lastSaved }) {
  const [reports, setReports] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!latestDate) return
    listReports({ before: latestDate, limit: PREVIEW_DAYS })
      .then((days) => Promise.all(days.map((d) => getReport(d.session_date))))
      .then((full) => {
        setReports(full)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [latestDate, lastSaved])

  return (
    <section className="panel previous" aria-label="Recent days">
      <div className="section-head">
        <h2>Previous days</h2>
        <a className="link" href={routes.previous()}>See all previous days →</a>
      </div>
      {error && <p className="error">{error}</p>}
      {reports.length === 0 ? (
        <p className="muted">No earlier reports yet.</p>
      ) : (
        <div className="preview-cards">
          {reports.map((report) => {
            const flagged = report.tickers.filter((t) => t.category === 'flagged')
            return (
              <a key={report.session_date} className="preview-card" href={routes.previous(report.session_date)}>
                <span className="preview-top">
                  <span className="day-date">{formatDate(report.session_date)}</span>
                  <StatusBadge status={report.status} />
                </span>
                <span className="preview-flagged">
                  {flagged.length === 0 && <span className="muted small">Nothing flagged</span>}
                  {flagged.slice(0, TICKERS_PER_CARD).map((t) => (
                    <span key={t.ticker} className={`tick ${t.return_1d_pct > 0 ? 'up' : t.return_1d_pct < 0 ? 'down' : ''}`}>
                      {t.ticker} {percent(t.return_1d_pct)}
                    </span>
                  ))}
                  {flagged.length > TICKERS_PER_CARD && (
                    <span className="muted small">+{flagged.length - TICKERS_PER_CARD} more</span>
                  )}
                </span>
              </a>
            )
          })}
        </div>
      )}
    </section>
  )
}
