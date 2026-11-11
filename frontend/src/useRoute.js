import { useEffect, useState } from 'react'

// A tiny router using the part of the address after #:
//   #/                      Today
//   #/previous              Previous days (newest day shown)
//   #/previous/2026-11-05   Previous days, with that day open
//   #/calendar              Upcoming events calendar
//   #/calendar/2026-11-12   The calendar, with that day's events open
//   #/stocks                Every tracked stock, and finding new ones
//   #/follow-through        What the price did after each flagged move
//   #/stories               Story updates: what the news has said since
//   #/stories/2026-10-13/MSFT   ...with that move picked, ready to check
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date, ticker] = hash.replace(/^#/, '').split('/')
  if (tab === 'stocks') return { tab: 'stocks', date: null }
  if (tab === 'follow-through') return { tab: 'followthrough', date: null }
  if (tab === 'stories') {
    const picked = /^\d{4}-\d{2}-\d{2}$/.test(date || '') && /^[A-Za-z0-9.\-^=]{1,15}$/.test(ticker || '')
    return { tab: 'stories', date: picked ? date : null, ticker: picked ? decodeURIComponent(ticker).toUpperCase() : null }
  }
  if (tab !== 'previous' && tab !== 'calendar') return { tab: 'today', date: null }
  return { tab, date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
  calendar: (date) => (date ? `#/calendar/${date}` : '#/calendar'),
  stocks: '#/stocks',
  followThrough: '#/follow-through',
  stories: (date, ticker) => (date && ticker ? `#/stories/${date}/${encodeURIComponent(ticker)}` : '#/stories'),
}

export function useRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
