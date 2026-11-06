import { useEffect, useState } from 'react'

// A tiny router using the part of the address after #:
//   #/                      Today
//   #/previous              Previous days (newest day shown)
//   #/previous/2026-11-05   Previous days, with that day open
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date] = hash.replace(/^#/, '').split('/')
  if (tab !== 'previous') return { tab: 'today', date: null }
  return { tab: 'previous', date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
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
