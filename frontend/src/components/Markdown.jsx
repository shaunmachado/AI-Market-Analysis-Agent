import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Links inside reports open in a new tab
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

// Renders markdown from the agent. Reports quote news headlines from the web,
// so DOMPurify strips anything that could run code (and images, which reports
// never need) before it reaches the page.
export default function Markdown({ text }) {
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(text || ''), { FORBID_TAGS: ['img', 'style'], FORBID_ATTR: ['style'] }),
    [text],
  )
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
}
