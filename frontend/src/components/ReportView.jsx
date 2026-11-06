import { formatTime, safeUrl } from '../format'
import Markdown from './Markdown'
import StatusBadge from './StatusBadge'
import TickerTable from './TickerTable'

// current: true for the latest report (see StatusBadge)
export default function ReportView({ report, current = false }) {
  return (
    <article className="report">
      <div className="report-head">
        <StatusBadge status={report.status} current={current} />
        <span className="muted small">
          As of {report.as_of} · saved {formatTime(report.updated_at)}
          {report.status === 'intraday' && current && ` · update ${report.revision}`}
        </span>
      </div>

      <TickerTable tickers={report.tickers} />
      <Markdown text={report.body_md} />

      {report.sources?.length > 0 && (
        <details className="sources">
          <summary>Sources ({report.sources.length})</summary>
          <ul>
            {report.sources.map((s, i) => (
              <li key={i}>
                <a href={safeUrl(s.url)} target="_blank" rel="noopener noreferrer">{s.title || s.url}</a>
                <span className="muted"> · {s.publisher} · {s.ticker}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  )
}
