import { useEffect, useRef, useState } from 'react'

// Keeps one live connection to /api/events open and calls onEvent for every update.
// If the server restarts, the browser reconnects by itself (and gets a fresh "hello").
export function useLiveEvents(onEvent) {
  const [connected, setConnected] = useState(false)
  const handler = useRef(onEvent)

  useEffect(() => {
    handler.current = onEvent
  })

  useEffect(() => {
    const source = new EventSource('/api/events')
    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)
    source.onmessage = (message) => handler.current(JSON.parse(message.data))
    return () => source.close()
  }, [])

  return connected
}
