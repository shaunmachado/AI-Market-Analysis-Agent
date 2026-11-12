import { useCallback, useEffect, useRef, useState } from 'react'
import { getCurrentRun, getLatestReport, getWatchlist } from './api'
import { ChartContext } from './chartContext'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
import CalendarTab from './components/CalendarTab'
import ComingUp from './components/ComingUp'
import FilingsTab from './components/FilingsTab'
import FollowThroughTab from './components/FollowThroughTab'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'
import StocksTab from './components/StocksTab'
import StoriesTab from './components/StoriesTab'
import TickerChart from './components/TickerChart'

export default function App() {
  const route = useRoute()
  const [latest, setLatest] = useState(null)
  const [latestError, setLatestError] = useState(null)
  const [run, setRun] = useState(null)
  const [lastSaved, setLastSaved] = useState(null) // tells the previous-days views to refresh
  const [chartTicker, setChartTicker] = useState(null)
  const [calendarScan, setCalendarScan] = useState(null) // "Update now" on the Calendar tab
  const [calendarVersion, setCalendarVersion] = useState(0) // tells the calendar to reload
  const [watchlist, setWatchlist] = useState(null) // tracked stocks; the main ones focus the Today tab
  const [followVersion, setFollowVersion] = useState(0) // tells the Follow-through tab to reload
  const [refreshJob, setRefreshJob] = useState(null) // "Refresh prices" on the Follow-through tab
  const [storiesVersion, setStoriesVersion] = useState(0) // tells the Story updates tab to reload
  const [storyJob, setStoryJob] = useState(null) // "Check for updates" on the Story updates tab
  const [filingsVersion, setFilingsVersion] = useState(0) // tells the Filings tab to reload
  const [filingsCheck, setFilingsCheck] = useState(null) // "Check now" on the Filings tab
  const [filingRead, setFilingRead] = useState(null) // "Read this filing"
  const chartOpener = useRef(null) // gets focus back when the chart closes

  const openChart = useCallback((ticker, opener) => {
    chartOpener.current = opener
    setChartTicker(ticker)
  }, [])
  const closeChart = useCallback(() => {
    setChartTicker(null)
    setTimeout(() => chartOpener.current?.focus(), 0)
  }, [])

  const loadLatest = useCallback(() => {
    getLatestReport()
      .then((report) => {
        setLatest(report)
        setLatestError(null)
      })
      .catch((error) => setLatestError(error.message))
  }, [])

  const loadWatchlist = useCallback(() => {
    getWatchlist()
      .then(setWatchlist)
      .catch(() => {}) // the Today tab then shows every ticker, as before
  }, [])

  useEffect(() => {
    loadLatest()
    loadWatchlist()
    getCurrentRun().then(setRun).catch(() => {})
  }, [loadLatest, loadWatchlist])

  useEffect(() => {
    window.scrollTo(0, 0) // start each tab at the top
  }, [route.tab])

  const connected = useLiveEvents((event) => {
    if (event.type === 'hello') {
      setRun(event.run) // (re)connected: catch up on anything missed
      setCalendarScan(event.calendar_scan)
      setCalendarVersion((v) => v + 1)
      loadLatest()
    } else if (event.type === 'calendar_scan') {
      setCalendarScan(event.scan)
    } else if (event.type === 'calendar_updated') {
      setCalendarVersion((v) => v + 1) // any calendar update: the daily scan, or "Update now"
      loadWatchlist() // next events
    } else if (event.type === 'watchlist_changed') {
      loadWatchlist() // from this page, another tab, or watchlist.txt edited by hand
    } else if (event.type === 'report_saved') {
      loadLatest()
      loadWatchlist() // latest figures
      setLastSaved(event)
    } else if (event.type === 'run_started' || event.type === 'run_finished') {
      setRun(event.run)
    } else if (event.type === 'run_event') {
      setRun((current) => current && { ...current, log: [...current.log, event.event] })
    } else if (event.type === 'followups_refresh') {
      setRefreshJob(event.job)
      if (event.job.state !== 'running') setFollowVersion((v) => v + 1)
    } else if (event.type === 'followups_updated') {
      setFollowVersion((v) => v + 1) // after a final report, "Refresh prices", or another program
    } else if (event.type === 'story_check') {
      setStoryJob(event.job)
      if (event.job.state !== 'running') {
        setStoriesVersion((v) => v + 1)
        setFollowVersion((v) => v + 1) // the moves table links to each move's latest story
      }
    } else if (event.type === 'story_checked') {
      setStoriesVersion((v) => v + 1)
      setFollowVersion((v) => v + 1)
    } else if (event.type === 'filings_check') {
      setFilingsCheck(event.job)
      if (event.job.state !== 'running') setFilingsVersion((v) => v + 1)
    } else if (event.type === 'filing_read') {
      setFilingRead(event.job)
      if (event.job.state !== 'running') setFilingsVersion((v) => v + 1)
    } else if (event.type === 'filings_updated') {
      setFilingsVersion((v) => v + 1) // a new filing or first take, from "Check now", a run, or another program
      setCalendarVersion((v) => v + 1) // the calendar shows what was reported
    }
  })

  // The live stream may have already moved the run on by the time the button's response arrives
  const onRunStarted = (started) =>
    setRun((current) => (current && current.started_at === started.started_at ? current : started))
  const onCalendarScanStarted = (started) =>
    setCalendarScan((current) => (current && current.started_at === started.started_at ? current : started))
  const onRefreshStarted = (started) =>
    setRefreshJob((current) => (current && current.started_at === started.started_at ? current : started))
  const onStoryCheckStarted = (started) =>
    setStoryJob((current) => (current && current.started_at === started.started_at ? current : started))
  const onFilingsCheckStarted = (started) =>
    setFilingsCheck((current) => (current && current.started_at === started.started_at ? current : started))
  const onFilingReadStarted = (started) =>
    setFilingRead((current) => (current && current.started_at === started.started_at ? current : started))

  const tabLink = (tab, href, label) => (
    <a href={href} className={`tab ${route.tab === tab ? 'active' : ''}`} aria-current={route.tab === tab ? 'page' : undefined}>
      {label}
    </a>
  )

  return (
    <ChartContext.Provider value={openChart}>
      <div className="app">
        <header className="topbar">
          <h1>Market Analyst</h1>
          <nav className="tabs" aria-label="Sections">
            {tabLink('today', routes.today, 'Today')}
            {tabLink('previous', routes.previous(), 'Previous days')}
            {tabLink('calendar', routes.calendar(), 'Calendar')}
            {tabLink('stocks', routes.stocks, 'Stocks')}
            {tabLink('followthrough', routes.followThrough, 'Follow-through')}
            {tabLink('stories', routes.stories(), 'Story updates')}
            {tabLink('filings', routes.filings(), 'Filings')}
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
                <ReportView report={latest} current focus={watchlist?.stocks.filter((s) => s.main).map((s) => s.ticker)} />
              ) : (
                <p className="muted">
                  {latestError === 'no reports yet'
                    ? 'No reports yet. Use "Run update now" to write the first one.'
                    : latestError || 'Loading…'}
                </p>
              )}
            </section>

            <aside className="side">
              <RunPanel run={run} onStarted={onRunStarted} lastSaved={lastSaved} />
              <ComingUp version={calendarVersion} />
              <AskPanel />
            </aside>
          </main>

          <PreviousDaysPreview latestDate={latest?.session_date} lastSaved={lastSaved} />
        </div>

        <div hidden={route.tab !== 'previous'}>
          <PreviousDaysTab
            latestDate={latest?.session_date}
            lastSaved={lastSaved}
            selectedDate={route.tab === 'previous' ? route.date : null}
          />
        </div>

        <div hidden={route.tab !== 'stocks'}>
          <StocksTab list={watchlist} onChange={setWatchlist} />
        </div>

        <div hidden={route.tab !== 'followthrough'}>
          <FollowThroughTab
            version={followVersion}
            refresh={refreshJob}
            onRefreshStarted={onRefreshStarted}
            latestDate={latest?.session_date}
          />
        </div>

        <div hidden={route.tab !== 'stories'}>
          <StoriesTab
            version={storiesVersion}
            job={storyJob}
            onCheckStarted={onStoryCheckStarted}
            picked={route.tab === 'stories' ? { date: route.date, ticker: route.ticker } : null}
          />
        </div>

        <div hidden={route.tab !== 'filings'}>
          <FilingsTab
            version={filingsVersion}
            checkJob={filingsCheck}
            readJob={filingRead}
            onCheckStarted={onFilingsCheckStarted}
            onReadStarted={onFilingReadStarted}
            picked={route.tab === 'filings' ? route.accession : null}
          />
        </div>

        <div hidden={route.tab !== 'calendar'}>
          <CalendarTab
            selectedDate={route.tab === 'calendar' ? route.date : null}
            version={calendarVersion}
            scan={calendarScan}
            onScanStarted={onCalendarScanStarted}
          />
        </div>

        {chartTicker && <TickerChart ticker={chartTicker} latestDate={latest?.session_date} onClose={closeChart} />}
      </div>
    </ChartContext.Provider>
  )
}
