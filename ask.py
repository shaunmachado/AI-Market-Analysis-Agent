"""Answer questions about saved reports with Claude.

No RAG yet: it picks the relevant reports straight from the database (the 10
most recent, plus the figures and flagged-day reports for any ticker named in
the question) and asks Claude to answer from those alone, citing report dates.
"""

import re
from contextlib import closing

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import reports_db
from run_brief import AGENT_ENV  # same auth as the report runs: the project's API key, if set

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05).
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included
FLAGGED_REPORTS_PER_TICKER = 10  # extra reports for each ticker named in the question
MAX_CONTEXT_CHARS = 60_000       # keeps each question's cost predictable

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],                      # answers only from the text it's given
    max_turns=1,
    max_budget_usd=0.25,           # hard stop on cost per question
    include_partial_messages=True,  # stream the answer as it's written
    env=AGENT_ENV,
)


def mentioned_tickers(conn, question: str) -> list[str]:
    """Tickers from the reports that the question names (any letter case)."""
    known = {row[0] for row in conn.execute("SELECT DISTINCT ticker FROM report_tickers")}
    words = {w.upper() for w in re.findall(r"[A-Za-z][A-Za-z.\-]{0,9}", question)}
    return sorted(words & known)


def build_context(conn, question: str) -> tuple[str, list[str]]:
    """The material Claude answers from, and the report dates it includes."""
    days = [r["session_date"] for r in reports_db.list_reports(conn, limit=RECENT_REPORTS)]
    tickers = mentioned_tickers(conn, question)
    for ticker in tickers:
        days += [row[0] for row in conn.execute(
            """SELECT session_date FROM report_tickers WHERE ticker = ? AND category = 'flagged'
               ORDER BY session_date DESC LIMIT ?""", (ticker, FLAGGED_REPORTS_PER_TICKER))]

    parts, size = [], 0
    for ticker in tickers:
        lines = [f"## Figures for {ticker} (newest first)",
                 "date | status | category | return % | z-score | volume vs normal"]
        lines += [f"{h['session_date']} | {h['status']} | {h['category']} | {h['return_1d_pct']} | "
                  f"{h['return_zscore']} | {h['volume_vs_avg']}"
                  for h in reports_db.ticker_history(conn, ticker, limit=60)]
        parts.append("\n".join(lines))
        size += len(parts[-1])

    used = []
    for day in sorted(set(days), reverse=True):
        report = reports_db.get_report(conn, day)
        block = f"## Report {day} ({report['status']}, as of {report['as_of']})\n\n{report['body_md']}"
        if size + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        used.append(day)
        size += len(block)
    return "\n\n---\n\n".join(parts), used


async def answer(question: str, emit) -> dict:
    """Answer one question. emit(event) receives {"type": "delta", "text": ...} as the
    answer is written, then {"type": "done", ...}. Returns the done event."""
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"questions must be 1 to {MAX_QUESTION_CHARS} characters")
    with closing(reports_db.connect(readonly=True)) as conn:
        context, used = build_context(conn, question)
    if not used:
        event = {"type": "done", "answer": "There are no saved reports yet, so there's nothing to answer from.",
                 "reports_used": [], "cost_usd": 0}
        emit(event)
        return event

    prompt = f"Saved reports:\n\n{context}\n\n---\n\nQuestion: {question}"
    streamed, result = "", None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
                streamed += event["delta"]["text"]
                emit({"type": "delta", "text": event["delta"]["text"]})
        elif isinstance(message, ResultMessage):
            result = message

    if result is None or result.is_error:
        raise RuntimeError(f"Claude couldn't answer: {result.subtype if result else 'no result'}")
    event = {"type": "done", "answer": result.result or streamed, "reports_used": used,
             "cost_usd": round(result.total_cost_usd or 0, 4)}
    emit(event)
    return event
