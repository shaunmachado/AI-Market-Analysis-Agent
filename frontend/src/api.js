// Helpers for talking to the Python API. Paths start with /api: in development
// Vite forwards them to port 8000, and in production the API serves this app itself.

async function request(path, options) {
  const response = await fetch(path, options)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}

const postJSON = (path, data) =>
  fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })

export const getLatestReport = () => request('/api/reports/latest')

export const getReport = (date) => request(`/api/reports/${date}`)

export const listReports = ({ before, limit = 20 } = {}) =>
  request(`/api/reports?limit=${limit}${before ? `&before=${before}` : ''}`).then((body) => body.reports)

export const getCurrentRun = () => request('/api/runs/current').then((body) => body.run)

export const getPrices = (ticker, range) =>
  request(`/api/tickers/${encodeURIComponent(ticker)}/prices?range=${range}`).then((body) => body.prices)

export const searchReports = (q, limit = 12) =>
  request(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`)

export const getAlerts = (limit = 10) => request(`/api/alerts?limit=${limit}`)

export const getWatchlist = () => request('/api/watchlist')

export const searchStocks = (q) => request(`/api/stocks/search?q=${encodeURIComponent(q)}`).then((body) => body.results)

async function post(path, data) {
  const response = await postJSON(path, data)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}

// Each returns the updated list (adding also returns the new stock's details)
export const addStock = (ticker, main = false) => post('/api/watchlist', { ticker, main })
export const setMainStock = (ticker, main) => post(`/api/watchlist/${encodeURIComponent(ticker)}`, { main })
export const removeStock = (ticker) => post(`/api/watchlist/${encodeURIComponent(ticker)}/remove`, {})

export const getCalendar = (start, end) => request(`/api/calendar?start=${start}&end=${end}`)

// Follow-through: what the price did 1, 5 or 20 trading days after each flagged move
export const getFollowups = (horizon, ticker) =>
  request(`/api/followups?horizon=${horizon}${ticker ? `&ticker=${encodeURIComponent(ticker)}` : ''}`)
export const refreshFollowups = () => post('/api/followups/refresh', {}).then((body) => body.refresh)

// Story updates: what the news has said since a flagged move
export const getStories = (ticker) => request(`/api/stories${ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''}`)
export const checkStory = (sessionDate, ticker) =>
  post('/api/stories/check', { session_date: sessionDate, ticker }).then((body) => body.check)

// Company filings from the SEC, and Claude's first take on them
export const getFilings = (ticker) => request(`/api/filings${ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''}`)
export const checkFilings = () => post('/api/filings/check', {}).then((body) => body.check)
export const readFiling = (accession) => post('/api/filings/read', { accession }).then((body) => body.read)

export async function startCalendarScan() {
  const response = await postJSON('/api/calendar/scan', {})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body.scan
}

export const getTickerHistory = (ticker, limit = 365) =>
  request(`/api/tickers/${encodeURIComponent(ticker)}/history?limit=${limit}`).then((body) => body.history)

export async function startRun() {
  const response = await postJSON('/api/runs', {})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body.run
}

// Streams Claude's answer. onEvent receives {type: 'delta', text} as it's written,
// then {type: 'done', answer, reports_used, cost_usd} or {type: 'error', error}.
export async function askQuestion(question, onEvent) {
  const response = await postJSON('/api/ask', { question })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error || `Request failed (${response.status})`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep any half-received line for the next chunk
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line))
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer))
}
