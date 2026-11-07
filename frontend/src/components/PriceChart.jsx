import { useEffect, useRef, useState } from 'react'
import { formatDate, formatMonthShort, formatShortDate, number, percent } from '../format'

const PLOT_HEIGHT = 220
const PAD = { top: 16, right: 64, bottom: 30, left: 52 } // bottom = the x-axis label band
const MIN_TICK_GAP = 48 // px between x-axis labels

// Round, evenly spaced y-axis values that cover min..max
function niceTicks(min, max, count = 5) {
  const span = max - min || Math.abs(max) || 1
  const raw = span / (count - 1)
  const magnitude = 10 ** Math.floor(Math.log10(raw))
  const step = [1, 2, 2.5, 5, 10].map((m) => m * magnitude).find((s) => s >= raw)
  const ticks = []
  for (let v = Math.floor(min / step) * step; v <= Math.ceil(max / step) * step + step / 2; v += step) {
    ticks.push(Number(v.toFixed(6)))
  }
  return ticks
}

// One price line, with a marker on each day the ticker was flagged in a report.
// prices: [{date, close, change_pct}], oldest first. flags: report rows for flagged days.
export default function PriceChart({ ticker, prices, flags, onOpenDay }) {
  const box = useRef(null)
  const [width, setWidth] = useState(640)
  const [active, setActive] = useState(null) // index of the day under the crosshair

  useEffect(() => {
    const observer = new ResizeObserver(([entry]) => setWidth(Math.max(280, entry.contentRect.width)))
    observer.observe(box.current)
    return () => observer.disconnect()
  }, [])

  const flagByDate = Object.fromEntries(flags.map((f) => [f.session_date, f]))
  const closes = prices.map((p) => p.close)
  const yTicks = niceTicks(Math.min(...closes), Math.max(...closes))
  const [yMin, yMax] = [yTicks[0], yTicks.at(-1)]
  const plotWidth = width - PAD.left - PAD.right
  const step = prices.length > 1 ? plotWidth / (prices.length - 1) : 0
  const x = (i) => PAD.left + (prices.length > 1 ? i * step : plotWidth / 2)
  const y = (v) => PAD.top + PLOT_HEIGHT - ((v - yMin) / (yMax - yMin || 1)) * PLOT_HEIGHT
  const line = prices.map((p, i) => `${i ? 'L' : 'M'}${x(i).toFixed(1)},${y(p.close).toFixed(1)}`).join('')

  // x-axis: month starts for longer ranges, every 5 trading days for one month; never crowded
  const xTicks = []
  prices.forEach((p, i) => {
    const isTick = prices.length > 30 ? i === 0 || p.date.slice(0, 7) !== prices[i - 1].date.slice(0, 7) : i % 5 === 0
    if (isTick && (!xTicks.length || x(i) - x(xTicks.at(-1)) >= MIN_TICK_GAP)) xTicks.push(i)
  })

  const indexAt = (clientX) => {
    const left = box.current.getBoundingClientRect().left
    return Math.max(0, Math.min(prices.length - 1, Math.round((clientX - left - PAD.left) / (step || 1))))
  }
  const openActive = () => {
    if (active != null && flagByDate[prices[active].date]) onOpenDay(prices[active].date)
  }
  const onKeyDown = (e) => {
    const moves = { ArrowLeft: -1, ArrowRight: 1, PageUp: -5, PageDown: 5 }
    if (e.key in moves) setActive((i) => Math.max(0, Math.min(prices.length - 1, (i ?? prices.length - 1) + moves[e.key])))
    else if (e.key === 'Home') setActive(0)
    else if (e.key === 'End') setActive(prices.length - 1)
    else if (e.key === 'Enter') openActive()
    else return
    e.preventDefault()
  }

  const last = prices.at(-1)
  const day = active != null ? prices[active] : null
  const flag = day && flagByDate[day.date]
  const tipOnLeft = day && x(active) > width / 2

  return (
    <div
      className="price-chart"
      ref={box}
      tabIndex={0}
      role="group"
      aria-label={`${ticker} daily closing price, ${formatDate(prices[0].date)} to ${formatDate(last.date)}. Use the arrow keys to move through days.`}
      onKeyDown={onKeyDown}
      onFocus={() => setActive((i) => i ?? prices.length - 1)}
      onBlur={() => setActive(null)}
    >
      <svg width={width} height={PAD.top + PLOT_HEIGHT + PAD.bottom} aria-hidden="true">
        {yTicks.map((v) => (
          <g key={v}>
            <line className="grid" x1={PAD.left} x2={width - PAD.right} y1={y(v)} y2={y(v)} />
            <text className="axis-label" x={PAD.left - 8} y={y(v) + 4} textAnchor="end">{number(v, v < 10 ? 2 : 0)}</text>
          </g>
        ))}
        {xTicks.map((i) => (
          <text key={i} className="axis-label" x={x(i)} y={PAD.top + PLOT_HEIGHT + 20} textAnchor="middle">
            {prices.length > 30 ? formatMonthShort(prices[i].date) : formatShortDate(prices[i].date)}
          </text>
        ))}

        <path className="price-line" d={line} />

        {day && <line className="crosshair" x1={x(active)} x2={x(active)} y1={PAD.top} y2={PAD.top + PLOT_HEIGHT} />}

        {prices.map((p, i) => {
          const f = flagByDate[p.date]
          if (!f) return null
          const [cx, cy] = [x(i), y(p.close)]
          const up = (f.return_1d_pct ?? 0) >= 0
          const shape = up ? `M${cx},${cy - 7}L${cx - 6},${cy + 5}L${cx + 6},${cy + 5}Z` : `M${cx},${cy + 7}L${cx - 6},${cy - 5}L${cx + 6},${cy - 5}Z`
          return <path key={p.date} className={`flag-marker ${up ? 'up' : 'down'}`} d={shape} />
        })}

        {/* A flagged day's marker doubles as its dot, so it's never hidden under one */}
        {!flagByDate[last.date] && <circle className="end-dot" cx={x(prices.length - 1)} cy={y(last.close)} r={4} />}
        <text className="end-label" x={x(prices.length - 1) + 10} y={y(last.close) + 4}>{number(last.close, 2)}</text>
        {day && !flag && <circle className="hover-dot" cx={x(active)} cy={y(day.close)} r={4} />}

        {/* Hit area: the whole plot, so the pointer only has to be near a day */}
        <rect
          className={`hit-area ${flag ? 'clickable' : ''}`}
          x={PAD.left - step / 2}
          y={PAD.top}
          width={plotWidth + step}
          height={PLOT_HEIGHT}
          onPointerMove={(e) => setActive(indexAt(e.clientX))}
          onPointerLeave={() => setActive(null)}
          onClick={openActive}
        />
      </svg>

      {day && (
        <div
          className="chart-tooltip"
          style={{ left: x(active) + (tipOnLeft ? -12 : 12), transform: tipOnLeft ? 'translateX(-100%)' : 'none' }}
          aria-live="polite"
        >
          <strong>{number(day.close, 2)}</strong>
          <span className="muted">{formatDate(day.date)}</span>
          {day.change_pct != null && <span>{percent(day.change_pct)} on the day</span>}
          {flag && (
            <span className="tip-flag">
              <span>{flag.return_1d_pct >= 0 ? '▲' : '▼'} Flagged in report</span>
              <span className="muted">
                z-score {number(flag.return_zscore, 1)}
                {flag.volume_vs_avg != null && ` · volume ${flag.volume_vs_avg}×`}
              </span>
              <span className="muted small">Click (or press Enter) to open it</span>
            </span>
          )}
        </div>
      )}
    </div>
  )
}
