import { useOpenChart } from '../chartContext'
import { number, percent, points } from '../format'
import { routes } from '../useRoute'

const ChartIcon = () => (
  <svg className="chart-icon" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
    <polyline points="1,10 4,6 7,8 11,2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

function Row({ t, openChart }) {
  return (
    <tr
      className={`${t.category} clickable`}
      onClick={(e) => openChart(t.ticker, e.currentTarget.querySelector('button'))}
    >
      <td className="ticker">
        <button type="button" className="ticker-button" aria-label={`Show ${t.ticker} chart`} title="Show chart">
          {t.ticker} <ChartIcon />
        </button>
      </td>
      <td>{t.category === 'error' ? <span title={t.error}>data issue</span> : t.category}</td>
      <td className="num">{number(t.price, 2)}</td>
      <td className={`num ${t.return_1d_pct > 0 ? 'up' : t.return_1d_pct < 0 ? 'down' : ''}`}>
        {percent(t.return_1d_pct)}
      </td>
      <td className="num">{number(t.return_zscore, 1)}</td>
      <td className="num">{t.volume_vs_avg == null ? '—' : `${t.volume_vs_avg}×`}</td>
      <td className="num vs-sector" title={t.context_summary || undefined}>
        {t.vs_benchmark_pct == null ? (
          '—'
        ) : (
          <>
            {points(t.vs_benchmark_pct)} <span className="muted">vs {t.benchmark}</span>
            {t.move_read && <span className="move-read">{t.move_read}</span>}
          </>
        )}
      </td>
    </tr>
  )
}

// Click a row (or Tab to its ticker and press Enter) to open that ticker's chart.
// focus (the Today tab): show only these tickers (your main stocks), in this order, plus any
// other ticker flagged in this report, so the dashboard never hides an unusual move.
export default function TickerTable({ tickers, focus }) {
  const openChart = useOpenChart()
  if (!tickers?.length) return null
  let shown = tickers
  let alsoFlagged = []
  if (focus?.length) {
    const byTicker = Object.fromEntries(tickers.map((t) => [t.ticker, t]))
    shown = focus.map((ticker) => byTicker[ticker]).filter(Boolean)
    alsoFlagged = tickers.filter((t) => t.category === 'flagged' && !focus.includes(t.ticker))
  }
  const hidden = tickers.length - shown.length - alsoFlagged.length
  return (
    <div className="table-wrap">
      <table className="tickers">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Status</th>
            <th className="num">Price</th>
            <th className="num">Change</th>
            <th className="num">z-score</th>
            <th className="num">Volume</th>
            <th className="num">Vs. sector</th>
          </tr>
        </thead>
        <tbody>
          {shown.map((t) => (
            <Row key={t.ticker} t={t} openChart={openChart} />
          ))}
          {alsoFlagged.length > 0 && (
            <tr className="group-row">
              <th colSpan={7} scope="rowgroup">Also flagged (not a main stock)</th>
            </tr>
          )}
          {alsoFlagged.map((t) => (
            <Row key={t.ticker} t={t} openChart={openChart} />
          ))}
        </tbody>
      </table>
      {focus?.length > 0 && hidden > 0 && (
        <p className="muted small table-note">
          Showing your main stocks. {hidden} more in this report: <a href={routes.stocks}>see all tracked stocks</a>.
        </p>
      )}
    </div>
  )
}
