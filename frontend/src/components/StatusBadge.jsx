// current: true for the latest report, which can still be updated during the day.
// An older day that's still "intraday" was never finalized (no run happened while
// the market was closed before the next session), so it won't change any more.
export default function StatusBadge({ status, current = false }) {
  if (status === 'final') return <span className="badge final">Final</span>
  return current ? (
    <span className="badge live">Intraday · updating</span>
  ) : (
    <span className="badge live" title="No final report was saved for this day">Intraday (not finalized)</span>
  )
}
