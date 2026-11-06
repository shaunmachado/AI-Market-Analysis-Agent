import { useCallback, useEffect, useState } from 'react'
import { getCurrentRun, getLatestReport } from './api'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'

export default function App() {
  const route = useRoute()
  const [latest, setLatest] = useState(null)
  const [latestError, setLatestError] = useState(null)
  const [run, setRun] = useState(null)
  const [lastSaved, setLastSaved] = useState(null) // tells the previous-days views to refresh

  const loadLatest = useCallback(() => {
    getLatestReport()
      .then((report) => {
        setLatest(report)
        setLatestError(null)
      })
      .catch((error) => setLatestError(error.message))
  }, [])

  useEffect(() => {
    loadLatest()
    getCurrentRun().then(setRun).catch(() => {})
  }, [loadLatest])

  useEffect(() => {
    window.scrollTo(0, 0) // start each tab at the top
  }, [route.tab])

  const connected = useLiveEvents((event) => {
    if (event.type === 'hello') {
      setRun(event.run) // (re)connected: catch up on anything missed
      loadLatest()
    } else if (event.type === 'report_saved') {
      loadLatest()
      setLastSaved(event)
    } else if (event.type === 'run_started' || event.type === 'run_finished') {
      setRun(event.run)
    } else if (event.type === 'run_event') {
      setRun((current) => current && { ...current, log: [...current.log, event.event] })
    }
  })

  // The live stream may have already moved the run on by the time the button's response arrives
  const onRunStarted = (started) =>
    setRun((current) => (current && current.started_at === started.started_at ? current : started))

  const tabLink = (tab, href, label) => (
    <a href={href} className={`tab ${route.tab === tab ? 'active' : ''}`} aria-current={route.tab === tab ? 'page' : undefined}>
      {label}
    </a>
  )

  return (
    <div className="app">
      <header className="topbar">
        <h1>Market Analyst</h1>
        <nav className="tabs" aria-label="Sections">
          {tabLink('today', routes.today, 'Today')}
          {tabLink('previous', routes.previous(), 'Previous days')}
        </nav>
        <span className={`connection ${connected ? 'on' : 'off'}`}>
          {connected ? 'Live' : 'Reconnecting…'}
        </span>
      </header>

      {/* Both tabs stay mounted, so switching keeps a streamed answer or run progress on screen */}
      <div hidden={route.tab !== 'today'}>
        <main className="layout">
          <section className="panel latest" aria-label="Latest report">
            <h2>Latest report</h2>
            {latest ? (
              <ReportView report={latest} current />
            ) : (
              <p className="muted">
                {latestError === 'no reports yet'
                  ? 'No reports yet. Use "Run update now" to write the first one.'
                  : latestError || 'Loading…'}
              </p>
            )}
          </section>

          <aside className="side">
            <RunPanel run={run} onStarted={onRunStarted} />
            <AskPanel />
          </aside>
        </main>

        <PreviousDaysPreview latestDate={latest?.session_date} lastSaved={lastSaved} />
      </div>

      <div hidden={route.tab !== 'previous'}>
        <PreviousDaysTab latestDate={latest?.session_date} lastSaved={lastSaved} selectedDate={route.date} />
      </div>
    </div>
  )
}
