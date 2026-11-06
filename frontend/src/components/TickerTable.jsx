import { number, percent } from '../format'

export default function TickerTable({ tickers }) {
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
            <tr key={t.ticker} className={t.category}>
              <td className="ticker">{t.ticker}</td>
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
