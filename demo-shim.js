/* Live demo: answers the app's /api requests inside the browser, from the sample data in
   demo-data/ (made by demo.py from the test environment). It's loaded before the app, so the
   app's own code runs unchanged: it calls fetch('/api/...') and opens EventSource('/api/events')
   as usual, and gets the same answers your Python API would give for the sample.

   Nothing here contacts a server or an AI. What a visitor changes (stocks, runs played) lives
   in this tab only, and a reload starts the demo again.

   It also:
   - sets the page's clock to the sample's trading day, so "today" matches the sample
   - adds a short banner saying the data is simulated */
;(function () {
  'use strict'

  const config = window.DEMO_CONFIG || {}
  const realFetch = window.fetch.bind(window)
  const RealDate = window.Date
  const RealEventSource = window.EventSource
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

  // ---------------------------------------------------------------------------
  // The clock: the sample's day, moving on to each recorded run's time when it's played
  // ---------------------------------------------------------------------------

  let offset = 0
  const now = () => RealDate.now() + offset
  const nowISO = () => new RealDate(now()).toISOString().replace(/\.\d{3}Z$/, 'Z')
  const setClock = (ms) => {
    offset = ms - RealDate.now()
  }

  class DemoDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) super(RealDate.now() + offset)
      else super(...args)
    }

    static now() {
      return RealDate.now() + offset
    }
  }
  window.Date = DemoDate
  if (config.start) setClock(RealDate.parse(config.start))

  // ---------------------------------------------------------------------------
  // The sample data. Each file has versions: 0 is the start, and N is from the Nth recorded run.
  // ---------------------------------------------------------------------------

  const dataRoot = new URL(`${config.data || 'demo-data'}/`, document.baseURI)
  const files = new Map()
  let manifest = null
  const state = {
    step: 0, // recorded runs played so far
    run: null,
    scan: { state: 'idle', started_at: null, finished_at: null, message: null, result: null, error: null },
    lastScan: null, // set once "Update now" has been played
    stocks: [], // [{ticker, main, benchmark}] in list order
    addedAt: {}, // ticker -> runs played when it was added
    eventsReady: {}, // ticker -> its calendar dates have been "looked up"
    lastRunStart: -Infinity,
    lastScanStart: -Infinity,
    refresh: { state: 'idle', started_at: null, finished_at: null, message: null, target: null, result: null, error: null },
    lastRefresh: null, // the follow-through update made by "Refresh prices", once played
    lastRefreshStart: -Infinity,
    storyJob: { state: 'idle', started_at: null, finished_at: null, message: null, target: null, result: null, error: null },
    newChecks: [], // story checks a visitor has played, newest first
    lastStoryStart: -Infinity,
    filingsCheck: { state: 'idle', started_at: null, finished_at: null, message: null, target: null, result: null, error: null },
    lastFilingsCheck: null, // the check made by "Check now" on the Filings tab, once played
    lastFilingsCheckStart: -Infinity,
    filingRead: { state: 'idle', started_at: null, finished_at: null, message: null, target: null, result: null, error: null },
    newReads: {}, // filing number -> the first take a visitor has had read
    lastFilingReadStart: -Infinity,
  }
  let universe = {}

  function loadFile(path) {
    if (!files.has(path)) {
      files.set(
        path,
        realFetch(new URL(path, dataRoot)).then((response) => {
          if (!response.ok) throw new Error(`demo data missing: ${path}`)
          return response.json()
        }),
      )
    }
    return files.get(path)
  }

  function versionOf(name) {
    let found = null
    for (const v of manifest.versions[name] || []) if (v <= state.step) found = v
    return found
  }

  // A copy of the file as it is after the runs played so far, or null if there's no such file
  async function data(name) {
    const v = versionOf(name)
    if (v === null) return null
    return JSON.parse(JSON.stringify(await loadFile(`${v}/${name}`)))
  }

  const ready = loadFile('manifest.json').then(async (m) => {
    manifest = m
    universe = Object.fromEntries(m.universe.map((u) => [u.ticker, u]))
    const list = await data('watchlist.json')
    state.stocks = list.stocks.map((s) => ({ ticker: s.ticker, main: s.main, benchmark: s.benchmark }))
    state.run = (await data('runs/current.json')).run
  })

  // ---------------------------------------------------------------------------
  // Live updates: a stand-in for the EventSource the app opens on /api/events
  // ---------------------------------------------------------------------------

  const openStreams = new Set()

  function emit(event) {
    for (const stream of openStreams) setTimeout(() => stream._deliver(event), 0)
  }

  class DemoEventSource {
    constructor(url, options) {
      const target = new URL(url, window.location.href)
      if (!target.pathname.startsWith('/api/') && RealEventSource) return new RealEventSource(url, options)
      this.url = target.href
      this.withCredentials = false
      this.readyState = 0
      this.onopen = this.onmessage = this.onerror = null
      this._listeners = {}
      openStreams.add(this)
      ready.then(() => {
        if (this.readyState === 2) return
        this.readyState = 1
        this._fire('open', new Event('open'))
        this._deliver({ type: 'hello', run: state.run, latest: null, calendar_scan: state.scan })
      })
    }

    _deliver(event) {
      if (this.readyState === 1) this._fire('message', new MessageEvent('message', { data: JSON.stringify(event) }))
    }

    _fire(type, event) {
      if (typeof this[`on${type}`] === 'function') this[`on${type}`](event)
      for (const listener of this._listeners[type] || []) listener.call(this, event)
    }

    addEventListener(type, listener) {
      ;(this._listeners[type] = this._listeners[type] || []).push(listener)
    }

    removeEventListener(type, listener) {
      this._listeners[type] = (this._listeners[type] || []).filter((l) => l !== listener)
    }

    close() {
      this.readyState = 2
      openStreams.delete(this)
    }
  }
  DemoEventSource.CONNECTING = 0
  DemoEventSource.OPEN = 1
  DemoEventSource.CLOSED = 2
  window.EventSource = DemoEventSource

  // ---------------------------------------------------------------------------
  // Helpers shared by the endpoints
  // ---------------------------------------------------------------------------

  class ApiError extends Error {
    constructor(status, message) {
      super(message)
      this.status = status
    }
  }

  const DATE = /^\d{4}-\d{2}-\d{2}$/
  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

  function limitOf(params, fallback, maximum) {
    const raw = params.get('limit') ?? String(fallback)
    const n = /^\d+$/.test(raw) ? Number(raw) : NaN
    if (!(n >= 1 && n <= maximum)) throw new ApiError(400, `limit must be a whole number from 1 to ${maximum}`)
    return n
  }

  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
  const signed = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`

  function addDays(day, n) {
    const d = new RealDate(`${day}T00:00:00Z`)
    d.setUTCDate(d.getUTCDate() + n)
    return d.toISOString().slice(0, 10)
  }

  function realDate(day) {
    return DATE.test(day) && new RealDate(`${day}T00:00:00Z`).toISOString().slice(0, 10) === day
  }

  const byEvent = (a, b) =>
    a.event_date.localeCompare(b.event_date) ||
    a.company.localeCompare(b.company) ||
    a.kind.localeCompare(b.kind) ||
    a.title.localeCompare(b.title)

  // Stocks added on the Stocks tab that weren't in the sample (they have recorded figures per run)
  const addedFromUniverse = () => state.stocks.filter((s) => universe[s.ticker] && !universe[s.ticker].in_sample)

  function figuresFor(ticker) {
    const runs = state.step - (state.addedAt[ticker] ?? 0)
    return runs > 0 ? universe[ticker].steps?.[state.step - 1] || null : null
  }

  async function calendarEvents() {
    const calendar = await data('calendar.json')
    const extra = addedFromUniverse().flatMap((s) => (state.eventsReady[s.ticker] ? universe[s.ticker].events || [] : []))
    return { calendar, events: [...calendar.events, ...extra].sort(byEvent) }
  }

  // ---------------------------------------------------------------------------
  // Reports, charts, alerts
  // ---------------------------------------------------------------------------

  const CATEGORY_ORDER = { flagged: 0, quiet: 1, error: 2 }

  // Today's report also lists stocks added since, once a run has been played (as a real run would)
  function withAddedStocks(report) {
    if (!report || report.session_date !== manifest.today) return report
    for (const s of addedFromUniverse()) {
      const row = figuresFor(s.ticker)?.row
      if (row && !report.tickers.some((t) => t.ticker === s.ticker)) report.tickers.push(row)
    }
    report.tickers.sort(
      (a, b) => (CATEGORY_ORDER[a.category] ?? 3) - (CATEGORY_ORDER[b.category] ?? 3) || a.ticker.localeCompare(b.ticker),
    )
    return report
  }

  async function getReport(day) {
    if (day !== 'latest' && !DATE.test(day)) throw new ApiError(400, "use a date like 2026-11-06, or 'latest'")
    const report = await data(day === 'latest' ? 'reports/latest.json' : `reports/${day}.json`)
    if (!report) throw new ApiError(404, day === 'latest' ? 'no reports yet' : `no report for ${day}`)
    return withAddedStocks(report)
  }

  async function listReports(params) {
    const limit = limitOf(params, 30, 365)
    const before = params.get('before')
    const status = params.get('status')
    if (before && !DATE.test(before)) throw new ApiError(400, 'before must be a date like 2026-11-06')
    if (status && status !== 'intraday' && status !== 'final') throw new ApiError(400, "status must be 'intraday' or 'final'")
    const { reports } = await data('reports.json')
    return {
      reports: reports
        .filter((r) => (!before || r.session_date < before) && (!status || r.status === status))
        .slice(0, limit),
    }
  }

  async function tickerHistory(ticker, params) {
    const limit = limitOf(params, 30, 365)
    const found = await data(`tickers/${ticker.toUpperCase()}/history.json`)
    return { ticker: ticker.toUpperCase(), history: found ? found.history.slice(0, limit) : [] }
  }

  async function tickerPrices(ticker, params) {
    const range = params.get('range') || '3mo'
    if (!['1mo', '3mo', '6mo', '1y'].includes(range)) throw new ApiError(400, 'range must be one of: 1mo, 3mo, 6mo, 1y')
    const found = await data(`tickers/${ticker.toUpperCase()}/prices-${range}.json`)
    if (!found || !found.prices.length) throw new ApiError(404, `no price data for ${ticker.toUpperCase()}`)
    return found
  }

  async function alerts(params) {
    const limit = limitOf(params, 10, 100)
    const found = await data('alerts.json')
    return { enabled: found.enabled, alerts: found.alerts.slice(0, limit) }
  }

  // ---------------------------------------------------------------------------
  // "Run update now": replays the recorded runs, one per press
  // ---------------------------------------------------------------------------

  function startRun() {
    if (state.run && state.run.state === 'running')
      throw new ApiError(409, 'A report is already being written. Its progress is shown below.')
    const wait = manifest.cooldown_seconds * 1000 - (now() - state.lastRunStart)
    if (wait > 0) {
      const seconds = Math.floor(wait / 1000) + 1
      throw new ApiError(429, `Please wait ${plural(seconds, 'second')} before requesting another report.`)
    }
    const step = state.step + 1
    const recorded = manifest.runs[step - 1]
    if (!recorded) return lastRunSkipped()
    setClock(Math.max(now(), RealDate.parse(recorded.started_at))) // the run happens at its sample time
    state.lastRunStart = now()
    const first = recorded.events[0].event
    state.run = JSON.parse(JSON.stringify(first.run))
    emit(first)
    for (const { at, event } of recorded.events.slice(1)) {
      setTimeout(() => {
        if (event.type === 'run_event') state.run.log.push(event.event)
        else if (event.type === 'run_finished') state.run = JSON.parse(JSON.stringify(event.run))
        else if (event.type === 'report_saved') state.step = step // the new report's files from now on
        emit(event)
        if (event.type === 'report_saved') emit({ type: 'filings_updated' }) // a run looks for new filings too
      }, at * 1000)
    }
    return { run: JSON.parse(JSON.stringify(state.run)) }
  }

  function lastRunSkipped() {
    state.lastRunStart = now()
    state.run = { state: 'running', started_at: nowISO(), finished_at: null, log: [], result: null, error: null }
    emit({ type: 'run_started', run: JSON.parse(JSON.stringify(state.run)) })
    const skipped = {
      type: 'skipped',
      session_date: manifest.today,
      message: 'That was the last recorded update in this demo. Reload the page to start it again.',
    }
    setTimeout(() => {
      state.run.log.push(skipped)
      emit({ type: 'run_event', event: skipped })
      state.run = { ...state.run, state: 'finished', finished_at: nowISO(), result: skipped }
      emit({ type: 'run_finished', run: JSON.parse(JSON.stringify(state.run)) })
    }, 600)
    return { run: JSON.parse(JSON.stringify(state.run)) }
  }

  // ---------------------------------------------------------------------------
  // The events calendar, and its "Update now" (replays the recorded update, at the current time)
  // ---------------------------------------------------------------------------

  async function calendar(params) {
    const { calendar: cal, events } = await calendarEvents()
    const start = params.get('start')
    const end = params.get('end')
    for (const [name, value] of [['start', start], ['end', end]]) {
      if (value && !DATE.test(value)) throw new ApiError(400, `${name} must be a date like 2026-11-06`)
      if (value && !realDate(value)) throw new ApiError(400, "that isn't a real date")
    }
    const first = start || `${cal.today.slice(0, 8)}01`
    const last = end || addDays(first, 41)
    if (last < first) throw new ApiError(400, 'end must be on or after start')
    const span = (RealDate.parse(`${last}T00:00:00Z`) - RealDate.parse(`${first}T00:00:00Z`)) / 86400000
    if (span > cal.max_days) throw new ApiError(400, `ask for at most ${cal.max_days} days at a time`)
    return {
      today: cal.today,
      start: first,
      end: last,
      events: events
        .filter((e) => e.event_date >= first && e.event_date <= last)
        .map(({ _line, _line_company, ...e }) => e), // eslint-disable-line no-unused-vars
      reported: reportedBetween(cal.reported || [], events, first, last),
      last_scan: state.lastScan || cal.last_scan,
      scan: state.scan,
    }
  }

  // Results filed, as api.py's calendar gives them: with the earnings event each answers if that event is
  // in the dates asked for, and otherwise only on the day they were filed
  function reportedBetween(reported, events, first, last) {
    const inRange = new Set(events.filter((e) => e.event_date >= first && e.event_date <= last).map((e) => e.id))
    return reported
      .map((r) => (inRange.has(r.event_id) ? r : { ...r, event_id: null }))
      .filter((r) => r.event_id !== null || (r.filing_date >= first && r.filing_date <= last))
  }

  // Moves every "..._at" time in a recorded event so the recording starts now
  function shiftTimes(value, by) {
    if (Array.isArray(value)) return value.map((v) => shiftTimes(v, by))
    if (!value || typeof value !== 'object') return value
    const out = {}
    for (const [key, v] of Object.entries(value)) {
      out[key] =
        key.endsWith('_at') && typeof v === 'string'
          ? new RealDate(RealDate.parse(v) + by).toISOString().replace(/\.\d{3}Z$/, 'Z')
          : shiftTimes(v, by)
    }
    return out
  }

  function startCalendarScan() {
    if (state.scan.state === 'running') throw new ApiError(409, 'The calendar is already being updated.')
    const wait = manifest.cooldown_seconds * 1000 - (now() - state.lastScanStart)
    if (wait > 0) {
      const seconds = Math.floor(wait / 1000) + 1
      throw new ApiError(429, `The calendar was just updated. Try again in ${plural(seconds, 'second')}.`)
    }
    state.lastScanStart = now()
    const recorded = manifest.calendar_scan
    const by = now() - RealDate.parse(recorded[0].event.scan.started_at)
    const events = recorded.map(({ at, event }) => ({ at, event: shiftTimes(event, by) }))
    state.scan = events[0].event.scan
    emit(events[0].event)
    for (const { at, event } of events.slice(1)) {
      setTimeout(() => {
        if (event.type === 'calendar_scan') {
          state.scan = event.scan
          if (event.scan.result) state.lastScan = event.scan.result // the calendar's "Updated" time
        }
        emit(event)
      }, at * 1000)
    }
    return { scan: state.scan }
  }

  // ---------------------------------------------------------------------------
  // Tracked stocks: the same rules and messages as watchlist.py
  // ---------------------------------------------------------------------------

  const shortName = (name) => name.replace(/^The\s+/i, '').replace(/[\s,]+(Inc\.?|Corporation|Company|Co\.?|Incorporated)$/i, '')

  async function watchlistView() {
    const sample = Object.fromEntries((await data('watchlist.json')).stocks.map((s) => [s.ticker, s]))
    const stocks = state.stocks.map((entry) => {
      if (sample[entry.ticker]) return { ...sample[entry.ticker], main: entry.main, benchmark: entry.benchmark }
      const u = universe[entry.ticker]
      return {
        ticker: entry.ticker,
        main: entry.main,
        benchmark: entry.benchmark,
        name: u.short_name || shortName(u.name),
        latest: figuresFor(entry.ticker)?.latest || null,
        next_event: state.eventsReady[entry.ticker] ? u.next_event || null : null,
      }
    })
    const ordered = [...stocks.filter((s) => s.main), ...stocks.filter((s) => !s.main)]
    return {
      stocks: ordered,
      tracked_count: ordered.length,
      main_count: ordered.filter((s) => s.main).length,
      max_tracked: manifest.limits.max_tracked,
      max_main: manifest.limits.max_main,
    }
  }

  const tickerPattern = () => new RegExp(`^(?:${manifest.limits.ticker_pattern})$`)
  const mainCount = () => state.stocks.filter((s) => s.main).length

  function canAdd(ticker, main) {
    const { max_tracked: maxTracked, max_main: maxMain } = manifest.limits
    if (state.stocks.some((s) => s.ticker === ticker)) throw new ApiError(409, `You're already tracking ${ticker}.`)
    if (state.stocks.length >= maxTracked)
      throw new ApiError(
        409,
        `You're tracking ${maxTracked} stocks, the most allowed. Remove one first, or raise MAX_TRACKED (see the guide).`,
      )
    if (main && mainCount() >= maxMain)
      throw new ApiError(409, `You already have ${maxMain} main stocks. Add it as tracked, or unstar one first.`)
  }

  async function addStock(body) {
    if (!body || typeof body !== 'object' || typeof body.ticker !== 'string')
      throw new ApiError(400, 'send {"ticker": "COST"}')
    const ticker = body.ticker.trim().toUpperCase()
    const main = Boolean(body.main)
    if (!tickerPattern().test(ticker))
      throw new ApiError(400, "That isn't a US ticker (letters, numbers and - only, like AAPL or BRK-B).")
    canAdd(ticker, main)
    const u = universe[ticker]
    if (!u) throw new ApiError(400, `Yahoo Finance doesn't know ${ticker}. Check the spelling, or search by company name.`)
    const type = manifest.limits.allowed_types[u.quote_type]
    if (!type)
      throw new ApiError(
        400,
        `${ticker} is a ${u.quote_type.toLowerCase().replaceAll('_', ' ')}. Only stocks and ETFs can be tracked.`,
      )
    await sleep(250) // as long as a quick check with Yahoo takes
    canAdd(ticker, main)
    state.stocks.push({ ticker, main, benchmark: null })
    state.addedAt[ticker] = state.step
    emit({ type: 'watchlist_changed' })
    setTimeout(() => {
      state.eventsReady[ticker] = true // its earnings and dividend dates, "from Yahoo"
      emit({ type: 'calendar_updated', scan: null })
    }, 700)
    return { stock: { ticker, name: u.name, type, main }, watchlist: await watchlistView() }
  }

  async function setMain(ticker, body) {
    if (!body || typeof body.main !== 'boolean') throw new ApiError(400, 'send {"main": true} or {"main": false}')
    const entry = state.stocks.find((s) => s.ticker === ticker)
    if (!entry) throw new ApiError(404, `${ticker} isn't on your list.`)
    if (body.main && !entry.main && mainCount() >= manifest.limits.max_main)
      throw new ApiError(409, `You already have ${manifest.limits.max_main} main stocks. Unstar one first.`)
    entry.main = body.main
    emit({ type: 'watchlist_changed' })
    return watchlistView()
  }

  async function removeStock(ticker) {
    if (!state.stocks.some((s) => s.ticker === ticker)) throw new ApiError(404, `${ticker} isn't on your list.`)
    state.stocks = state.stocks.filter((s) => s.ticker !== ticker)
    delete state.addedAt[ticker]
    delete state.eventsReady[ticker]
    emit({ type: 'watchlist_changed' })
    return watchlistView()
  }

  // Yahoo Finance's search, over the stocks the sample knows: ticker matches first, then names
  function searchStocks(params) {
    const raw = (params.get('q') || '').trim()
    if (!raw) throw new ApiError(400, 'q is required')
    if (raw.length > 60) throw new ApiError(400, 'keep searches under 60 characters')
    const query = raw.split(/\s+/).join(' ').slice(0, 60)
    const q = query.toLowerCase()
    const ranked = []
    manifest.universe.forEach((u, order) => {
      const sym = u.ticker.toLowerCase()
      const low = u.name.toLowerCase()
      const nameMatch = low.replaceAll(',', ' ').split(/\s+/).some((w) => w.startsWith(q)) || low.includes(q)
      const rank = sym === q ? 0 : sym.startsWith(q) ? 1 : nameMatch ? 2 : null
      if (rank !== null) ranked.push({ rank, order, u })
    })
    ranked.sort((a, b) => a.rank - b.rank || a.order - b.order)
    const tracked = new Set(state.stocks.map((s) => s.ticker))
    const pattern = tickerPattern()
    const results = ranked
      .slice(0, 15)
      .map((r) => r.u)
      .filter((u) => manifest.limits.allowed_types[u.quote_type] && pattern.test(u.ticker))
      .slice(0, 8)
      .map((u) => ({
        ticker: u.ticker,
        name: u.name,
        type: manifest.limits.allowed_types[u.quote_type],
        exchange: u.exchange,
        tracked: tracked.has(u.ticker),
      }))
    return { query, results }
  }

  // ---------------------------------------------------------------------------
  // Follow-through (the price after flagged moves) and Story updates (the news since)
  // ---------------------------------------------------------------------------

  const moveKey = (date, ticker) => `${date}/${ticker}`
  const latestNewCheck = (date, ticker) =>
    state.newChecks.find((c) => c.session_date === date && c.ticker === ticker && (c.status === 'ok' || c.status === 'no_news'))

  async function followupsView(params) {
    const horizon = params.get('horizon') || '5'
    const ticker = (params.get('ticker') || '').toUpperCase()
    if (!['1', '5', '20'].includes(horizon)) throw new ApiError(400, 'horizon must be one of: 1, 5, 20')
    const view = await data(`followups/${horizon}.json`)
    for (const m of view.moves) {
      const c = latestNewCheck(m.session_date, m.ticker)
      if (c) m.story = { verdict: c.verdict, update: c.update_text, checked_at: c.finished_at, status: c.status }
    }
    if (ticker) view.moves = view.moves.filter((m) => m.ticker === ticker)
    view.refresh = state.refresh
    if (state.lastRefresh) view.updated = state.lastRefresh
    return view
  }

  // Plays a recorded job (a price refresh or a story check) as if it were running now
  function playJob(recorded, setJob, onFinished) {
    const by = now() - RealDate.parse(recorded[0].event.job.started_at)
    const events = recorded.map(({ at, event }) => ({ at, event: shiftTimes(event, by) }))
    setJob(events[0].event.job)
    emit(events[0].event)
    for (const { at, event } of events.slice(1)) {
      setTimeout(() => {
        setJob(event.job)
        emit(event)
        if (event.job.state !== 'running') onFinished(event.job)
      }, at * 1000)
    }
    return events[0].event.job
  }

  function tooSoon(lastStart, message) {
    const wait = manifest.cooldown_seconds * 1000 - (now() - lastStart)
    if (wait > 0) throw new ApiError(429, message.replace('{}', plural(Math.floor(wait / 1000) + 1, 'second')))
  }

  function refreshFollowups() {
    if (state.refresh.state === 'running') throw new ApiError(409, 'Prices are already being refreshed.')
    tooSoon(state.lastRefreshStart, 'Prices were just refreshed. Try again in {}.')
    state.lastRefreshStart = now()
    const job = playJob(manifest.followups_refresh, (j) => (state.refresh = j), (j) => {
      if (j.result) state.lastRefresh = { ...j.result, surprises: undefined }
      emit({ type: 'followups_updated' })
    })
    return { refresh: job }
  }

  async function storiesView(params) {
    const ticker = (params.get('ticker') || '').toUpperCase()
    const view = await data('stories.json')
    const done = new Set(state.newChecks.filter((c) => c.status === 'ok' || c.status === 'no_news').map((c) => moveKey(c.session_date, c.ticker)))
    view.checks = [...state.newChecks, ...view.checks].filter((c) => !ticker || c.ticker === ticker)
    view.unchecked = view.unchecked.filter((m) => !done.has(moveKey(m.session_date, m.ticker)) && (!ticker || m.ticker === ticker))
    view.check = state.storyJob
    return view
  }

  function checkStory(body) {
    const day = body && body.session_date
    const ticker = body && typeof body.ticker === 'string' ? body.ticker.toUpperCase() : null
    if (typeof day !== 'string' || !DATE.test(day) || !ticker || !/^[A-Z0-9.\-^=]{1,15}$/.test(ticker))
      throw new ApiError(400, 'send JSON like {"session_date": "2026-10-13", "ticker": "MSFT"}')
    const recorded = manifest.story_checks[moveKey(day, ticker)]
    if (!recorded) throw new ApiError(404, `${ticker} wasn't flagged in the final report of ${day}.`)
    if (state.storyJob.state === 'running')
      throw new ApiError(409, 'A story is already being checked. Its progress is shown on the Story updates tab.')
    tooSoon(state.lastStoryStart, 'A story was just checked. Try again in {}.')
    state.lastStoryStart = now()
    const job = playJob(recorded, (j) => (state.storyJob = j), (j) => {
      if (j.result) state.newChecks.unshift(j.result)
      emit({ type: 'story_checked' })
    })
    return { check: job }
  }

  // ---------------------------------------------------------------------------
  // Company filings: api.py's /api/filings, "Check now" and "Read this filing"
  // ---------------------------------------------------------------------------

  async function filingsView(params) {
    const ticker = (params.get('ticker') || '').toUpperCase()
    if (ticker && !/^[A-Z0-9.\-^=]{1,15}$/.test(ticker)) throw new ApiError(400, 'invalid ticker')
    const view = await data('filings.json')
    for (const f of view.filings) if (state.newReads[f.accession]) f.read = state.newReads[f.accession]
    if (ticker) view.filings = view.filings.filter((f) => f.ticker === ticker)
    view.check = state.filingsCheck
    view.read = state.filingRead
    if (state.lastFilingsCheck) view.checked = state.lastFilingsCheck
    return view
  }

  function checkFilings() {
    if (state.filingsCheck.state === 'running') throw new ApiError(409, 'Filings are already being checked.')
    tooSoon(state.lastFilingsCheckStart, 'Filings were just checked. Try again in {}.')
    state.lastFilingsCheckStart = now()
    const job = playJob(manifest.filings_check, (j) => (state.filingsCheck = j), (j) => {
      if (j.result) state.lastFilingsCheck = { ...j.result, new: undefined, read: undefined, alerts: undefined }
      emit({ type: 'filings_updated' })
    })
    return { check: job }
  }

  async function readFiling(body) {
    const accession = body && body.accession
    if (typeof accession !== 'string' || !/^\d{10}-\d{2}-\d{6}$/.test(accession))
      throw new ApiError(400, 'send JSON like {"accession": "0000789019-26-000123"}')
    const listed = (await data('filings.json')).filings.some((f) => f.accession === accession)
    const recorded = manifest.filing_reads[accession]
    if (!listed || !recorded) throw new ApiError(404, `No filing ${accession} is listed. Check for new filings first.`)
    if (state.filingRead.state === 'running')
      throw new ApiError(409, 'A filing is already being read. Its progress is shown on the Filings tab.')
    tooSoon(state.lastFilingReadStart, 'A filing was just read. Try again in {}.')
    state.lastFilingReadStart = now()
    const job = playJob(recorded, (j) => (state.filingRead = j), (j) => {
      if (j.result) state.newReads[accession] = j.result
      emit({ type: 'filings_updated' })
    })
    return { read: job }
  }

  const WHEN = { 1: 'the next day', 5: 'a week later', 20: 'a month later' }
  function describeGroup(g, horizon) {
    if (!g.judged) return `${g.label}: no moves to judge yet`
    return (
      `${g.label}: ${g.held} of ${g.judged} held ${WHEN[horizon]}, ${g.faded} faded, ${g.reversed} reversed` +
      (g.enough ? '' : ' (too few to tell)')
    )
  }

  // ---------------------------------------------------------------------------
  // Search: keywords (a simple BM25) plus the test environment's topic stand-in for meaning
  // ---------------------------------------------------------------------------

  const WORD = /[A-Za-z0-9][A-Za-z0-9.\-']*/g
  const SUFFIXES = ['ations', 'ation', 'ings', 'ing', 'edly', 'ed', 'ly', 'es', 's']

  function stem(word) {
    let w = word.toLowerCase()
    if (w.length <= 3 || /^\d+$/.test(w)) return w
    if (w.endsWith('ies') && w.length > 4) return `${w.slice(0, -3)}y`
    for (const suffix of SUFFIXES) {
      if (w.endsWith(suffix) && w.length - suffix.length >= 3) {
        w = w.slice(0, -suffix.length)
        if ((suffix === 'ed' || suffix === 'ing') && /([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1) // flagged -> flag
        break
      }
    }
    if (w.endsWith('e') && w.length > 4) w = w.slice(0, -1)
    return w
  }

  const tokens = (text) => (text.toLowerCase().match(/[a-z0-9]+/g) || []).map(stem)
  const indexes = new Map()

  async function searchIndex() {
    const v = versionOf('search/passages.json')
    if (!indexes.has(v)) {
      const { passages } = await data('search/passages.json')
      const topics = Object.values(manifest.search.topics)
      const docs = passages.map((p) => {
        const full = `${p.heading} ${p.text}`
        const terms = {}
        const list = tokens(full)
        for (const t of list) terms[t] = (terms[t] || 0) + 1
        return { p, terms, length: list.length, vector: topicVector(p.text, topics, 0.1) }
      })
      const df = {}
      for (const d of docs) for (const t of Object.keys(d.terms)) df[t] = (df[t] || 0) + 1
      const avg = docs.reduce((sum, d) => sum + d.length, 0) / Math.max(1, docs.length)
      indexes.set(v, { docs, df, avg, topics })
    }
    return indexes.get(v)
  }

  function topicVector(text, topics, bias) {
    const low = text.toLowerCase()
    const v = [...topics.map((phrases) => 3 * phrases.filter((p) => low.includes(p)).length), bias]
    const norm = Math.hypot(...v)
    return norm ? v.map((x) => x / norm) : v
  }

  async function search(query, limit = 10, { ticker, since, until } = {}) {
    const s = manifest.search
    const words = (query.match(WORD) || []).slice(0, s.max_query_words)
    const result = { query, mode: 'hybrid', note: null, terms: words, results: [] }
    if (!words.length) return { ...result, mode: 'keyword' }
    const { docs, df, avg, topics } = await searchIndex()
    const n = docs.length
    const allowed = docs.filter(
      ({ p }) =>
        (!ticker || p.ticker === ticker.toUpperCase()) &&
        (!since || p.session_date >= since) &&
        (!until || p.session_date <= until),
    )
    const groups = words.map((w) => tokens(w)).filter((g) => g.length)
    const keyword = allowed
      .map((d) => {
        let score = 0
        for (const group of groups) {
          if (!group.every((t) => d.terms[t])) continue
          for (const t of group) {
            const idf = Math.max(1e-6, Math.log((n - df[t] + 0.5) / (df[t] + 0.5)))
            const tf = d.terms[t]
            score += (idf * tf * 2.2) / (tf + 1.2 * (0.25 + (0.75 * d.length) / avg))
          }
        }
        return { d, score }
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score || a.d.p.id - b.d.p.id)
      .slice(0, limit * 3)
      .map((x) => x.d)
    const q = topicVector(query, topics, 0)
    const scored = allowed.map((d) => ({ d, score: d.vector.reduce((sum, x, i) => sum + x * q[i], 0) }))
    const best = Math.max(0, ...scored.map((x) => x.score))
    const floor = Math.max(s.min_similarity, best * s.meaning_cutoff)
    const meaning = scored
      .filter((x) => x.score >= floor)
      .sort((a, b) => b.score - a.score || a.d.p.id - b.d.p.id)
      .slice(0, limit * 3)
      .map((x) => x.d)
    const fused = new Map()
    for (const [ranking, label] of [[keyword, 'keywords'], [meaning, 'meaning']]) {
      ranking.forEach((d, rank) => {
        const entry = fused.get(d) || { score: 0, matched_by: [] }
        entry.score += 1 / (s.rrf_k + rank + 1)
        entry.matched_by.push(label)
        fused.set(d, entry)
      })
    }
    result.results = [...fused.entries()]
      .sort((a, b) => b[1].score - a[1].score)
      .slice(0, limit)
      .map(([d, entry]) => ({
        session_date: d.p.session_date,
        status: d.p.status,
        ticker: d.p.ticker,
        heading: d.p.heading,
        text: d.p.text.split('\n').slice(1).join('\n'), // without the title line
        score: Math.round(entry.score * 1e5) / 1e5,
        matched_by: entry.matched_by,
      }))
    return result
  }

  async function searchEndpoint(params) {
    const q = (params.get('q') || '').trim()
    const limit = limitOf(params, 12, 50)
    if (!q) throw new ApiError(400, 'q is required')
    if (q.length > manifest.ask.max_question_chars)
      throw new ApiError(400, `keep searches under ${manifest.ask.max_question_chars} characters`)
    for (const name of ['since', 'until'])
      if (params.get(name) && !DATE.test(params.get(name))) throw new ApiError(400, `${name} must be a date like 2026-11-06`)
    return search(q, limit, { ticker: params.get('ticker'), since: params.get('since'), until: params.get('until') })
  }

  // ---------------------------------------------------------------------------
  // Ask: an answer built straight from the sample data (as the test environment's offline answers are)
  // ---------------------------------------------------------------------------

  async function flaggedDays(ticker) {
    const found = await data(`tickers/${ticker}/history.json`)
    return found ? found.history.filter((h) => h.category === 'flagged') : []
  }

  async function upcoming(start, days, tickers) {
    const { events } = await calendarEvents()
    const last = addDays(start, days)
    return events.filter((e) => e.event_date >= start && e.event_date <= last && (!tickers || tickers.includes(e.ticker)))
  }

  async function answer(question) {
    const a = manifest.ask
    const { tickers: known } = await data('known_tickers.json')
    const words = new Set((question.match(/[A-Za-z][A-Za-z.\-]{0,9}/g) || []).map((w) => w.toUpperCase()))
    const tickers = known.filter((t) => words.has(t)).sort()
    const today = manifest.today
    const lines = ['*Demo answer, built from the sample data without Claude.*', '']
    const days = new Set((await data('reports.json')).reports.slice(0, a.recent_reports).map((r) => r.session_date))
    for (const t of tickers) {
      const rows = await flaggedDays(t)
      rows.slice(0, a.flagged_reports_per_ticker).forEach((r) => days.add(r.session_date))
      if (rows.length) {
        const recent = rows.slice(0, 5).map((r) => `${r.session_date} (${signed(r.return_1d_pct)}%)`).join(', ')
        lines.push(`- **${t}** was flagged on ${plural(rows.length, 'day')}. Most recent: ${recent}.`)
      } else {
        lines.push(`- **${t}** hasn't been flagged in the saved reports.`)
      }
      const ahead = await upcoming(today, a.calendar_days, [t])
      if (ahead.length) lines.push(`  Next on the calendar: ${ahead[0]._line} (calendar).`)
      const judged = (await followupsView(new URLSearchParams({ horizon: '5', ticker: t }))).moves.filter((m) => m.outcomes['5'])
      if (judged.length) {
        const m = judged[0]
        lines.push(
          `  After its last judged move (${m.session_date}, ${signed(m.move_pct)}%): ${m.outcomes['5']} a week later (${signed(m.after_5d)}%) (follow-through).`,
        )
      }
      const checked = (await storiesView(new URLSearchParams({ ticker: t }))).checks.filter(
        (c) => c.status === 'ok' || c.status === 'no_news',
      )
      if (checked.length) {
        const c = checked[0]
        lines.push(
          `  Latest story update, on its move of ${c.session_date}: ${c.verdict_label}. ${c.update_text} (story update, ${c.finished_at.slice(0, 10)}).`,
        )
      }
      const taken = (await filingsView(new URLSearchParams({ ticker: t }))).filings.filter((f) => f.read && f.read.status === 'ok')
      if (taken.length) {
        const f = taken[0]
        lines.push(`  Latest first take, on its ${f.title.toLowerCase()}: ${f.read.headline} (filing, ${f.filing_date}).`)
      }
    }
    if (!tickers.length) {
      const counts = await Promise.all(known.map(async (t) => [t, (await flaggedDays(t)).length]))
      const top = counts
        .filter(([, n]) => n > 0)
        .sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
        .slice(0, 3)
      lines.push(
        `Most-flagged tickers in the saved reports: ${top.map(([t, n]) => `**${t}** (${n} days)`).join(', ') || 'none yet'}.`,
      )
      const ahead = await upcoming(today, 7)
      if (ahead.length) lines.push('', 'Next on the calendar (calendar):', ...ahead.slice(0, 3).map((e) => `- ${e._line_company}`))
      const followed = await followupsView(new URLSearchParams({ horizon: '5' }))
      if (followed.moves.length)
        lines.push('', `How flagged moves played out (follow-through): ${describeGroup(followed.patterns.all, 5)}.`)
    }
    const passages = (await search(question, a.passages)).results
    passages.forEach((p) => days.add(p.session_date))
    if (passages.length) {
      lines.push('', 'Most relevant passages:')
      for (const p of passages.slice(0, 3)) lines.push(`- ${p.session_date}: ${p.heading} (matched by ${p.matched_by.join(' and ')})`)
    }
    return { text: lines.join('\n'), used: [...days].sort().reverse() }
  }

  function askEndpoint(body) {
    const question = body && typeof body.question === 'string' ? body.question : null
    if (!question || !question.trim()) throw new ApiError(400, 'question is required')
    if (question.length > manifest.ask.max_question_chars)
      throw new ApiError(400, `keep questions under ${manifest.ask.max_question_chars} characters`)
    const encoder = new TextEncoder()
    const line = (event) => encoder.encode(`${JSON.stringify(event)}\n`)
    const stream = new ReadableStream({
      async start(controller) {
        try {
          const { text, used } = await answer(question.trim())
          for (const word of text.split(' ')) {
            await sleep(25)
            controller.enqueue(line({ type: 'delta', text: `${word} ` }))
          }
          controller.enqueue(line({ type: 'done', answer: text, reports_used: used, cost_usd: 0 }))
        } catch (e) {
          controller.enqueue(line({ type: 'error', error: String(e.message || e) }))
        }
        controller.close()
      },
    })
    return new Response(stream, { status: 200, headers: { 'Content-Type': 'application/x-ndjson' } })
  }

  // ---------------------------------------------------------------------------
  // Routing: the same paths as api.py
  // ---------------------------------------------------------------------------

  function bodyOf(init) {
    try {
      return init && typeof init.body === 'string' ? JSON.parse(init.body) : null
    } catch {
      return null
    }
  }

  async function route(url, init) {
    await ready
    const method = ((init && init.method) || 'GET').toUpperCase()
    const path = url.pathname.replace(/\/+$/, '')
    const params = url.searchParams
    const body = bodyOf(init)
    let m
    if (method === 'GET') {
      if (path === '/api/health') return { status: 'ok', reports: (await data('reports.json')).reports.length }
      if (path === '/api/reports') return listReports(params)
      if ((m = path.match(/^\/api\/reports\/([^/]+)$/))) return getReport(decodeURIComponent(m[1]))
      if ((m = path.match(/^\/api\/tickers\/([^/]+)\/history$/))) return tickerHistory(decodeURIComponent(m[1]), params)
      if ((m = path.match(/^\/api\/tickers\/([^/]+)\/prices$/))) return tickerPrices(decodeURIComponent(m[1]), params)
      if (path === '/api/runs/current') return { run: state.run }
      if (path === '/api/search') return searchEndpoint(params)
      if (path === '/api/alerts') return alerts(params)
      if (path === '/api/watchlist') return watchlistView()
      if (path === '/api/stocks/search') return searchStocks(params)
      if (path === '/api/calendar') return calendar(params)
      if (path === '/api/followups') return followupsView(params)
      if (path === '/api/stories') return storiesView(params)
      if (path === '/api/filings') return filingsView(params)
    } else if (method === 'POST') {
      if (path === '/api/runs') return [202, startRun()]
      if (path === '/api/ask') return askEndpoint(body)
      if (path === '/api/calendar/scan') return [202, startCalendarScan()]
      if (path === '/api/followups/refresh') return [202, refreshFollowups()]
      if (path === '/api/stories/check') return [202, checkStory(body)]
      if (path === '/api/filings/check') return [202, checkFilings()]
      if (path === '/api/filings/read') return [202, await readFiling(body)]
      if (path === '/api/watchlist') return [201, await addStock(body)]
      if ((m = path.match(/^\/api\/watchlist\/([^/]+)\/remove$/))) return removeStock(decodeURIComponent(m[1]).toUpperCase())
      if ((m = path.match(/^\/api\/watchlist\/([^/]+)$/))) return setMain(decodeURIComponent(m[1]).toUpperCase(), body)
    }
    throw new ApiError(404, 'not found')
  }

  window.fetch = async function demoFetch(input, init) {
    const raw = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input)
    const url = new URL(raw, window.location.href)
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return realFetch(input, init)
    try {
      const result = await route(url, init)
      if (result instanceof Response) return result
      return Array.isArray(result) ? json(result[1], result[0]) : json(result)
    } catch (e) {
      if (e instanceof ApiError) return json({ error: e.message }, e.status)
      return json({ error: `demo: ${e.message || e}` }, 500)
    }
  }

  // ---------------------------------------------------------------------------
  // The banner
  // ---------------------------------------------------------------------------

  function addBanner() {
    const style = document.createElement('style')
    style.textContent = `
      .demo-banner { padding: 8px 16px; text-align: center; font-size: 0.875rem; line-height: 1.45;
        background: var(--live-bg, #fef3c7); color: var(--text, #1c2430); border-bottom: 1px solid var(--border, #e2e6eb); }
      .demo-banner a { color: var(--accent, #2456d6); font-weight: 600; white-space: nowrap; }`
    document.head.appendChild(style)
    const bar = document.createElement('div')
    bar.className = 'demo-banner'
    bar.setAttribute('role', 'note')
    const strong = document.createElement('strong')
    strong.textContent = 'Live demo with sample data.'
    bar.append(
      strong,
      ' Prices, news, company filings, runs and answers are simulated, and no AI is called. Changes stay in this tab until you reload.',
    )
    if (/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(config.repo_url || '')) {
      const link = document.createElement('a')
      link.href = config.repo_url
      link.textContent = 'See the code on GitHub'
      bar.append(' ', link)
    }
    document.body.prepend(bar)
  }

  if (document.body) addBanner()
  else document.addEventListener('DOMContentLoaded', addBanner)
})()
