import { useEffect, useState } from 'react'
import { getCalendar } from '../api'
import { formatWeekdayDate } from '../format'
import { routes } from '../useRoute'

const DAYS = 7  // how far ahead to look
const MAX_SHOWN = 6

const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

// The next week from the events calendar, on the Today tab. Each event links to its day on the Calendar tab.
export default function ComingUp({ version }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    const start = new Date()
    const end = new Date()
    end.setDate(end.getDate() + DAYS + 1) // a day extra, in case the server's "today" is ahead of this computer's
    getCalendar(isoDay(start), isoDay(end))
      .then(setData)
      .catch(() => setData(null))
  }, [version])

  if (!data) return null
  const last = new Date(`${data.today}T12:00:00`)
  last.setDate(last.getDate() + DAYS)
  const soon = data.events.filter((e) => e.event_date >= data.today && e.event_date <= isoDay(last))

  return (
    <section className="panel coming-up" aria-label="Coming up">
      <div className="section-head">
        <h2>Coming up</h2>
        <a className="link small" href={routes.calendar()}>
          Calendar
        </a>
      </div>
      {soon.length === 0 ? (
        <p className="muted small">
          {data.last_scan ? 'Nothing on the calendar for the next week.' : 'The events calendar hasn’t been updated yet.'}
        </p>
      ) : (
        <ul>
          {soon.slice(0, MAX_SHOWN).map((e) => (
            <li key={e.id}>
              <a href={routes.calendar(e.event_date)}>
                <span className="cu-date">{e.event_date === data.today ? 'Today' : formatWeekdayDate(e.event_date)}</span>
                <span className="cu-what">
                  <strong>{e.company}</strong> <span className="muted">{e.title}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
      {soon.length > MAX_SHOWN && (
        <a className="link small" href={routes.calendar(soon[MAX_SHOWN].event_date)}>
          +{soon.length - MAX_SHOWN} more on the calendar
        </a>
      )}
    </section>
  )
}
