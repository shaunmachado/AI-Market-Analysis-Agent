import { useState } from 'react'
import { askQuestion } from '../api'
import Markdown from './Markdown'

const EXAMPLES = ['What moved the most this week?', 'Why was NVDA flagged?', "What's coming up next week?"]

export default function AskPanel() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [details, setDetails] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!question.trim() || busy) return
    setBusy(true)
    setAnswer('')
    setDetails(null)
    setError(null)
    try {
      await askQuestion(question, (event) => {
        if (event.type === 'delta') setAnswer((text) => text + event.text)
        else if (event.type === 'done') {
          setAnswer(event.answer)
          setDetails(event)
        } else if (event.type === 'error') setError(event.error)
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Ask about your reports</h2>
      <form onSubmit={submit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && submit(e)}
          maxLength={500}
          rows={3}
          placeholder="e.g. Why was NVDA flagged this week?"
          aria-label="Your question"
        />
        <div className="row">
          <button className="primary" disabled={busy || !question.trim()}>
            {busy ? 'Answering…' : 'Ask'}
          </button>
          <span className="muted small">Answers come only from saved reports and the calendar.</span>
        </div>
      </form>
      <div className="examples">
        {EXAMPLES.map((q) => (
          <button key={q} type="button" className="chip" onClick={() => setQuestion(q)}>
            {q}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {answer && (
        <div className="answer" aria-live="polite">
          <Markdown text={answer} />
          {details && (
            <p className="muted small">
              Based on {details.reports_used.length} saved report{details.reports_used.length === 1 ? '' : 's'}
              {details.cost_usd > 0 && ` · $${details.cost_usd.toFixed(3)}`}
            </p>
          )}
        </div>
      )}
    </section>
  )
}
