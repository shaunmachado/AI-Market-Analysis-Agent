import { useEffect, useRef, useState } from 'react'
import { getPrices, getTickerHistory } from '../api'
import { formatDate, number, percent } from '../format'
import { routes } from '../useRoute'
import PriceChart from './PriceChart'

const RANGES = [['1mo', '1M', '1-month'], ['3mo', '3M', '3-month'], ['6mo', '6M', '6-month'], ['1y', '1Y', '1-year']]

// A dialog with one ticker's price chart, the days it was flagged in your reports,
// and the same figures as tables.
export default function TickerChart({ ticker, latestDate, onClose }) {
  const [range, setRange] = useState('3mo')
  const [prices, setPrices] = useState(null)
  const [flags, setFlags] = useState([])
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(true)
  const dialog = useRef(null)
  const closeButton = useRef(null)

  // Focus the close button, keep Tab inside the dialog, close on Escape, and stop the page scrolling behind
  useEffect(() => {
    closeButton.current?.focus()
    const onKeyDown = (e) => {
      if (e.key === 'Escape') onClose()
      if (e.key !== 'Tab') return
      const focusable = dialog.current.querySelectorAll('button, [href], summary, [tabindex="0"]')
      const [first, last] = [focusable[0], focusable[focusable.length - 1]]
      if (e.shiftKey && document.activeElement === first) {
        last.focus()
        e.preventDefault()
      } else if (!e.shiftKey && document.activeElement === last) {
        first.focus()
        e.preventDefault()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKeyDown)
      document.body.style.overflow = overflow
    }
  }, [onClose])

  useEffect(() => {
    let current = true // ignore a slow answer for a range that's no longer selected
    setLoading(true)
    getPrices(ticker, range)
      .then((rows) => {
        if (current) {
          setPrices(rows)
          setError(null)
        }
      })
      .catch((e) => {
        if (current) setError(e.message)
      })
      .finally(() => {
        if (current) setLoading(false)
      })
    return () => {
      current = false
    }
  }, [ticker, range])

  useEffect(() => {
    getTickerHistory(ticker)
      .then((history) => setFlags(history.filter((d) => d.category === 'flagged')))
      .catch(() => setFlags([]))
  }, [ticker])

  const openDay = (day) => {
    window.location.hash = day === latestDate ? routes.today : routes.previous(day)
    onClose()
  }

  const first = prices?.[0]
  const last = prices?.at(-1)
  const shown = prices ? flags.filter((f) => f.session_date >= first.date && f.session_date <= last.date) : []
  const change = prices?.length > 1 ? (last.close / first.close - 1) * 100 : null
  const rangeName = RANGES.find(([value]) => value === range)[2]

  return (
    <div className="modal-backdrop" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal="true" aria-labelledby="chart-title" ref={dialog}>
        <div className="modal-head">
          <div>
            <h2 id="chart-title">{ticker}</h2>
            <span className="muted small">Daily closing price</span>
          </div>
          <button ref={closeButton} className="close" onClick={onClose} aria-label="Close chart">×</button>
        </div>

        <div className="range-row" role="group" aria-label="Time range">
          {RANGES.map(([value, label, name]) => (
            <button
              key={value}
              className={`range ${range === value ? 'active' : ''}`}
              aria-pressed={range === value}
              aria-label={name}
              onClick={() => setRange(value)}
            >
              {label}
            </button>
          ))}
        </div>

        {prices && (
          <div className="chart-stats">
            <div><span className="muted small">Latest</span><strong>{number(last.close, 2)}</strong></div>
            <div>
              <span className="muted small">{rangeName} change</span>
              <strong className={change > 0 ? 'up' : change < 0 ? 'down' : ''}>{percent(change)}</strong>
            </div>
            <div><span className="muted small">Flagged in reports</span><strong>{shown.length} day{shown.length === 1 ? '' : 's'}</strong></div>
          </div>
        )}

        {error && <p className="error">{error}</p>}
        {!prices && !error && <p className="muted">Loading…</p>}
        {prices && (
          <div className={loading ? 'refreshing' : ''}>
            <PriceChart ticker={ticker} prices={prices} flags={shown} onOpenDay={openDay} />
          </div>
        )}

        {prices && (
          <>
            <h3 className="table-title">Days flagged in your reports</h3>
            {shown.length === 0 ? (
              <p className="muted small">None in this range.</p>
            ) : (
              <div className="table-wrap">
                <table className="tickers">
                  <thead>
                    <tr><th>Date</th><th className="num">Change</th><th className="num">z-score</th><th className="num">Volume</th><th /></tr>
                  </thead>
                  <tbody>
                    {[...shown].reverse().map((f) => (
                      <tr key={f.session_date}>
                        <td>{f.return_1d_pct >= 0 ? '▲' : '▼'} {formatDate(f.session_date)}</td>
                        <td className={`num ${f.return_1d_pct > 0 ? 'up' : f.return_1d_pct < 0 ? 'down' : ''}`}>{percent(f.return_1d_pct)}</td>
                        <td className="num">{number(f.return_zscore, 1)}</td>
                        <td className="num">{f.volume_vs_avg == null ? '—' : `${f.volume_vs_avg}×`}</td>
                        <td><a className="link" href={f.session_date === latestDate ? routes.today : routes.previous(f.session_date)} onClick={onClose}>Open report</a></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <details className="sources">
              <summary>Daily prices as a table ({prices.length} days)</summary>
              <div className="table-wrap">
                <table className="tickers">
                  <thead><tr><th>Date</th><th className="num">Close</th><th className="num">Change</th></tr></thead>
                  <tbody>
                    {[...prices].reverse().map((p) => (
                      <tr key={p.date}>
                        <td>{formatDate(p.date)}</td>
                        <td className="num">{number(p.close, 2)}</td>
                        <td className="num">{percent(p.change_pct)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
            <p className="muted small">
              Daily closes from your market data source; while the market is open, the last point is the latest price.
              Markers ▲▼ show days {ticker} was flagged in your reports.
            </p>
          </>
        )}
      </div>
    </div>
  )
}
