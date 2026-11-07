// Display helpers

export const formatDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

export const formatMonth = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

export const formatShortDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export const formatMonthShort = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short' })

export const formatTime = (utc) =>
  utc ? new Date(utc).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ''

export const number = (value, digits) => (value == null ? '—' : value.toFixed(digits))

export const percent = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`)

// Only allow normal web links from news sources
export const safeUrl = (url) => (/^https?:\/\//i.test(url || '') ? url : undefined)
