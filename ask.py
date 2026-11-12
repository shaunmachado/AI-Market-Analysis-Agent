"""Answer questions about saved reports with Claude, using retrieval (RAG).

For each question it gathers, within a size limit:
1. Figures across days for any watchlist ticker named in the question.
2. The events calendar: everything in the next 30 days, plus the last 30 days for named tickers.
3. What happened after flagged moves (followups.py and stories.py): for named tickers, each
   move's follow-through and story updates; otherwise, how moves of each kind played out.
4. Company filings (filings.py): for named tickers, their latest filings and first takes;
   otherwise, what was filed in the last week.
5. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
6. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import events
import filings
import followups
import reports_db
import search_index
from run_brief import AGENT_ENV  # same auth as the report runs: the project's API key, if set
import stories

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports, passages and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05). Passages carry the date of the report they came from.
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- Dated events come from the events calendar: cite them as (calendar), and say so when a date isn't confirmed.
- Follow-through figures say what a stock's price did after a flagged move: cite them as (follow-through).
  Story updates say what later news added: cite them as (story update, then the date it was checked).
  Both are history, never a forecast.
- Company filings are what a company itself filed with the SEC: cite them as (filing, then the date it was filed).
  A first take's figures were checked against the filing: use them exactly as given. "Confirmed" means the
  quarterly report later gave the same figure. If a filing has no first take, say only that it was filed.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
CALENDAR_DAYS = 30               # events calendar: this far ahead (all tickers) and back (named tickers)
FOLLOWUP_MOVES = 10              # flagged moves' follow-through per named ticker
STORY_UPDATES = 3                # latest story updates per named ticker
FILING_TAKES = 2                 # latest first takes on filings, in full, per named ticker
FILINGS_LISTED = 8               # latest filings listed per named ticker
FILINGS_DAYS = 7                 # with no ticker named: filings from this many days back
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


def find_passages(question: str) -> list[dict]:
    """The retrieval step. If the index isn't available, Ask still works from recent reports."""
    try:
        search_index.sync(embed_now=False)  # make sure the newest reports are searchable
        return search_index.search(question, limit=PASSAGES)["results"]
    except Exception:
        return []


def calendar_section(conn, tickers: list[str]) -> str:
    """Upcoming events for the watchlist, and recent ones for the tickers asked about."""
    today = events.today_et()
    soon = events.upcoming(conn, today, CALENDAR_DAYS, events.watchlist_tickers())
    recent = events.upcoming(conn, today - timedelta(days=CALENDAR_DAYS), CALENDAR_DAYS - 1, tickers) if tickers else []
    if not soon and not recent:
        return ""
    lines = [f"## Events calendar (today is {today:%a} {today.isoformat()})", "", "Coming up:"]
    lines += [f"- {e['event_date']} {events.event_line(e)}" for e in soon] or ["- nothing in the next 30 days"]
    if recent:
        lines += ["", f"In the last {CALENDAR_DAYS} days, for {', '.join(tickers)}:"]
        lines += [f"- {e['event_date']} {events.event_line(e)}" for e in recent]
    return "\n".join(lines)


def followup_section(conn, tickers: list[str]) -> str:
    """What happened after flagged moves: each named ticker's moves and story updates, or, with no
    ticker named, how moves of each kind played out a week later."""
    horizon = followups.SURPRISE_HORIZON
    if not tickers:
        found = followups.moves(conn)
        if not found:
            return ""
        result = followups.patterns(found, horizon)
        lines = ["## How flagged moves played out a week later (all stocks; cite as (follow-through))", ""]
        lines += [f"- {followups.describe_group(g, horizon)}" for g in
                  [result["all"], *result["by_kind"], *result["by_reason"], *result["by_direction"]]]
        return "\n".join(lines)
    parts = []
    for ticker in tickers:
        found = followups.moves(conn, ticker)[:FOLLOWUP_MOVES]
        if found:
            lines = [f"## Follow-through for {ticker}: the price after each flagged move (cite as (follow-through))",
                     "day of the move | move % | kind | reason | 1 day later % | 1 week later % | 1 month later % | after a week"]
            for m in found:
                after = " | ".join("" if m[f"after_{n}d"] is None else f"{m[f'after_{n}d']:+.2f}" for n in followups.HORIZONS)
                lines.append(f"{m['session_date']} | {m['move_pct']:+.2f} | {m['kind']} | {m['reason_label']} | {after} | "
                             f"{m['outcomes'][str(horizon)] or 'not known yet'}")
            parts.append("\n".join(lines))
        checks = [c for c in stories.latest(conn, ticker, STORY_UPDATES) if c["status"] in ("ok", "no_news")]
        if checks:
            lines = [f"## Story updates for {ticker} (cite as (story update, date checked))"]
            for c in checks:
                cited = "; ".join(f"{s['publisher']}: {s['title']}" for s in c["sources"])
                lines.append(f"- Move of {c['session_date']}, checked {c['finished_at'][:10]}: {c['verdict_label']}. "
                             f"{c['update_text']}" + (f" Sources: {cited}" if cited else ""))
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


def _take_lines(f: dict) -> list[str]:
    """One filing's first take as lines of text."""
    take = f["read"]
    lines = [f"### {f['ticker']}: {f['title']}, filed {f['filing_date']} (cite as (filing, {f['filing_date']}))",
             take["headline"]]
    figures = take["figures"] or {}
    for r in figures.get("rows", []):
        parts = [f"{r['label']}: {filings.money(r['value'], r['unit'])}"]
        if r["change_prior_pct"] is not None:
            parts.append(f"{r['change_prior_pct']:+.1f}% vs the quarter before")
        if r["change_year_pct"] is not None:
            parts.append(f"{r['change_year_pct']:+.1f}% vs a year earlier")
        if r["check"] == "confirmed":
            parts.append("confirmed by the quarterly report")
        elif r["check"] == "differs":
            parts.append(f"but the quarterly report says {filings.money(r['report_value'], r['unit'])}")
        lines.append("- " + ", ".join(parts))
    lines += [f"- {m['label']}: {m['value']}%" for m in figures.get("margins", [])]
    lines += [f"- {p['text']}" for p in take["points"]]
    lines += [f"- Guidance ({filings.DIRECTIONS[g['direction']].lower()}): {g['text']}" for g in take["guidance"]]
    lines += [f"- Changed since the last announcement: {c['text']}" for c in take["changes"]]
    return lines


def filings_section(conn, tickers: list[str]) -> str:
    """What companies filed with the SEC: each named ticker's latest filings and first takes, or,
    with no ticker named, everything filed in the last week."""
    def has_take(f):
        return f["read"] is not None and f["read"]["status"] == "ok"

    if not tickers:
        found = filings.list_filings(conn, since=filings._days_ago(FILINGS_DAYS), limit=40)
        if not found:
            return ""
        lines = [f"## Company filings in the last {FILINGS_DAYS} days (cite as (filing, date filed))", ""]
        lines += [f"- {f['filing_date']} {f['ticker']}: {f['title']}" + (f". {f['read']['headline']}" if has_take(f) else "")
                  for f in found]
        return "\n".join(lines)
    parts = []
    for ticker in tickers:
        found = filings.list_filings(conn, ticker, limit=60)
        if not found:
            continue
        lines = [f"## Company filings for {ticker} (cite as (filing, date filed))", ""]
        lines += [f"- {f['filing_date']}: {f['title']}" + ("" if has_take(f) else " (not read)") for f in found[:FILINGS_LISTED]]
        for f in [f for f in found if has_take(f)][:FILING_TAKES]:
            lines += ["", *_take_lines(f)]
        parts.append("\n".join(lines))
    return "\n\n".join(parts)


def build_context(conn, question: str) -> tuple[str, list[str]]:
    """The material Claude answers from, and the report dates it draws on."""
    days = [r["session_date"] for r in reports_db.list_reports(conn, limit=RECENT_REPORTS)]
    tickers = mentioned_tickers(conn, question)
    for ticker in tickers:
        days += [row[0] for row in conn.execute(
            """SELECT session_date FROM report_tickers WHERE ticker = ? AND category = 'flagged'
               ORDER BY session_date DESC LIMIT ?""", (ticker, FLAGGED_REPORTS_PER_TICKER))]
    days = sorted(set(days), reverse=True)

    parts, used, size = [], set(), 0

    def add(text: str, day: str | None = None) -> bool:
        nonlocal size
        if size + len(text) > MAX_CONTEXT_CHARS:
            return False
        parts.append(text)
        size += len(text)
        if day:
            used.add(day)
        return True

    for ticker in tickers:
        lines = [f"## Figures for {ticker} (newest first)",
                 "date | status | category | return % | z-score | volume vs normal | vs sector (points) | kind of move"]
        for h in reports_db.ticker_history(conn, ticker, limit=60):
            vs_sector = "" if h["vs_benchmark_pct"] is None else f"{h['vs_benchmark_pct']} vs {h['benchmark']}"
            lines.append(f"{h['session_date']} | {h['status']} | {h['category']} | {h['return_1d_pct']} | "
                         f"{h['return_zscore']} | {h['volume_vs_avg']} | {vs_sector} | {h['move_read'] or ''}")
        add("\n".join(lines))

    calendar = calendar_section(conn, tickers)
    if calendar:
        add(calendar)
    followed = followup_section(conn, tickers)
    if followed:
        add(followed)
    filed = filings_section(conn, tickers)
    if filed:
        add(filed)

    # Retrieved passages from reports that aren't already included in full
    for p in find_passages(question):
        if p["session_date"] not in days:
            add(f"## Passage from the report of {p['session_date']} ({p['status']}): {p['heading']}\n\n{p['text']}",
                p["session_date"])

    for day in days:
        report = reports_db.get_report(conn, day)
        if not add(f"## Report {day} ({report['status']}, as of {report['as_of']})\n\n{report['body_md']}", day):
            break
    return "\n\n---\n\n".join(parts), sorted(used, reverse=True)


def gather(question: str) -> tuple[str, list[str]]:
    with closing(reports_db.connect(readonly=True)) as conn:
        return build_context(conn, question)


async def answer(question: str, emit) -> dict:
    """Answer one question. emit(event) receives {"type": "delta", "text": ...} as the
    answer is written, then {"type": "done", ...}. Returns the done event."""
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"questions must be 1 to {MAX_QUESTION_CHARS} characters")
    context, used = await asyncio.to_thread(gather, question)  # searching can take a moment
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
