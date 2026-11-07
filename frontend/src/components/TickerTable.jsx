import { useOpenChart } from '../chartContext'
import { number, percent } from '../format'

const ChartIcon = () => (
  <svg className="chart-icon" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
    <polyline points="1,10 4,6 7,8 11,2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

// Click a row (or Tab to its ticker and press Enter) to open that ticker's chart
export default function TickerTable({ tickers }) {
  const openChart = useOpenChart()
  if (!tickers?.length) return null
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
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => (
            <tr
              key={t.ticker}
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
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
