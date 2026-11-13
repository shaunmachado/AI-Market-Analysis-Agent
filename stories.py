"""Story updates: what the news has said since a flagged move.

A check reads the newest headlines about the company, keeps the ones published after the move,
and asks Claude what they add to the original story: the brief's "Likely why" line and its
sources. If there are no newer headlines, there's no Claude call and no cost.

- Automatic: moves that turn out to be surprises (see followups.py) are checked once, after the
  final report that settles their first week. Only moves from the last 30 days are checked
  automatically, so reports from before you added this don't run up costs on old news.
- On demand: any flagged move, from the Story updates tab ("Check for updates") or the terminal.

From the terminal:
    python stories.py check MSFT 2026-10-13     check one move now (a few cents)
    python stories.py list                      the latest updates
"""

import argparse
import asyncio
import dataclasses
import json
from contextlib import closing
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import events
import followups
import market_tools
import reports_db
from events import transaction

NEWS_PER_CHECK = 10              # newest headlines read per check
CHECK_BUDGET_USD = 0.10          # hard stop on Claude's cost per check
MAX_AUTOMATIC = 5                # most automatic (surprise) checks after one final report
AUTOMATIC_WITHIN_DAYS = 30       # automatic checks only for moves this recent; older ones are checked by hand
VERDICTS = {"developed": "Developed", "confirmed": "Confirmed", "contradicted": "Contradicted",
            "no_update": "No update"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS story_checks (
    id           INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,          -- the flagged move's day
    ticker       TEXT NOT NULL,
    trigger      TEXT NOT NULL CHECK (trigger IN ('surprise', 'manual')),
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'no_news', 'failed')),
    verdict      TEXT,                   -- developed, confirmed, contradicted or no_update
    update_text  TEXT,                   -- one or two sentences on what's happened since
    sources      TEXT,                   -- JSON list of the articles it's based on
    articles     INTEGER NOT NULL DEFAULT 0,  -- newer headlines found
    cost_usd     REAL NOT NULL DEFAULT 0,
    error        TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_story_checks_move ON story_checks (session_date, ticker);
"""

SYSTEM_PROMPT = """You check what has happened since a stock's unusual move. You get the original story
(the move, the explanation written at the time, and its source headlines), what the price has done since,
and newer headlines about the company.

Reply with JSON only, in this shape:
{"verdict": "developed", "update": "One or two plain sentences.", "sources": [1, 3]}

- verdict: "developed" (new information about the same story), "confirmed" (later news supports the
  original explanation), "contradicted" (later news undercuts it), or "no_update" (nothing about this story).
- update: what has happened since, from the newer headlines only. Mention dates. If nothing is about this
  story, say so in one sentence.
- sources: the numbers of the newer headlines you used (none for no_update).
- Use only the headlines given. Never explain the price move yourself, predict anything, or give advice."""

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],
    max_turns=1,
    max_budget_usd=CHECK_BUDGET_USD,
)


class StoryError(ValueError):
    """A check that can't be done, with a message to show as it is. status is the HTTP status."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    """The reports database, with the follow-up and story tables added if they're missing."""
    conn = followups.connect()
    conn.executescript(SCHEMA)
    return conn


def fetch_news(ticker: str) -> list[dict]:
    """The company's newest headlines. Tests and the test environment replace this."""
    return market_tools.get_news(ticker, NEWS_PER_CHECK)


async def _ask_claude_async(prompt: str) -> tuple[str, float]:
    from run_brief import AGENT_ENV  # same auth as the report runs: the project's API key, if set (imported here:
                                     # run_brief imports this module)
    result = None
    async for message in query(prompt=prompt, options=dataclasses.replace(options, env=AGENT_ENV)):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't check the story: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(prompt))


# ---------------------------------------------------------------------------
# One check
# ---------------------------------------------------------------------------

def build_prompt(move: dict, original: list[dict], later: list[dict]) -> str:
    when = {1: "next day", 5: "after a week", 20: "after a month"}
    since = [f"{when[n]}: {move[f'after_{n}d']:+.2f}%" for n in followups.HORIZONS if move[f"after_{n}d"] is not None]
    lines = [f"STOCK: {move['ticker']}",
             f"MOVE: {move['move_pct']:+.2f}% on {move['session_date']} ({move['kind']})",
             f"EXPLANATION AT THE TIME: {move['why'] or 'none given'}",
             f"PRICE SINCE: {', '.join(since) or 'not known yet'}", "", "Headlines at the time:"]
    lines += [f"- {a.get('title')} ({a.get('publisher') or 'unknown'})" for a in original] or ["- none"]
    lines += ["", "Newer headlines:"]
    for n, a in enumerate(later, 1):
        lines += [f"[{n}] {a.get('publisher') or 'unknown publisher'} | published {a.get('published') or 'unknown'}",
                  f"    {a.get('title') or ''}", f"    {(a.get('summary') or '').strip()}"]
    return "\n".join(lines)


def parse_reply(text: str, later: list[dict]) -> tuple[str, str, list[dict]]:
    """(verdict, update, sources) from Claude's reply, checked."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    verdict = str(data.get("verdict") or "").strip().lower()
    update = " ".join(str(data.get("update") or "").split())
    if verdict not in VERDICTS:
        raise ValueError(f"Claude's reply had an unknown verdict ({verdict or 'none'})")
    if not update:
        raise ValueError("Claude's reply had no update")
    refs = data.get("sources") if isinstance(data.get("sources"), list) else []
    picked = sorted({r for r in refs if type(r) is int and 1 <= r <= len(later)})  # not bool: True isn't headline 1
    if verdict != "no_update" and not picked:
        raise ValueError("Claude's reply cited none of the newer headlines")
    keep = ("title", "publisher", "url", "published")
    return verdict, update[:600], [{k: later[r - 1].get(k) for k in keep} for r in picked]


def _the_move(conn, session_date: str, ticker: str) -> dict:
    row = conn.execute("SELECT * FROM followups WHERE session_date = ? AND ticker = ?", (session_date, ticker)).fetchone()
    if row is None:
        raise StoryError(f"{ticker} wasn't flagged in the final report of {session_date}.", 404)
    return followups._move(row)


def check(session_date: str, ticker: str, trigger: str = "manual", emit=None) -> dict:
    """Check one flagged move's story now. Returns the saved check."""
    emit = emit or (lambda event: None)
    ticker = ticker.strip().upper()
    with closing(connect()) as conn:
        move = _the_move(conn, session_date, ticker)
        with transaction(conn):
            check_id = conn.execute(
                "INSERT INTO story_checks (session_date, ticker, trigger, status, started_at) VALUES (?, ?, ?, 'running', ?)",
                (session_date, ticker, trigger, _utc_now())).lastrowid
        original = [dict(r) for r in conn.execute(
            "SELECT title, publisher FROM report_sources WHERE session_date = ? AND ticker = ?", (session_date, ticker))]
    company = events.company_name(ticker)
    fields = {"status": "failed", "verdict": None, "update_text": None, "sources": "[]", "articles": 0,
              "cost_usd": 0.0, "error": None}
    try:
        emit({"type": "progress", "message": f"Reading {company}'s newest headlines"})
        later = [a for a in fetch_news(ticker)
                 if (d := events._to_date(a.get("published"))) is not None and d.isoformat() > session_date]
        fields["articles"] = len(later)
        if not later:  # nothing newer: no Claude call, no cost
            fields.update(status="no_news", verdict="no_update",
                          update_text=f"No newer headlines about {company} since {session_date}.")
        else:
            emit({"type": "progress", "message": f"Reading {len(later)} newer headline{'s' if len(later) != 1 else ''} with Claude"})
            reply, cost = ask_claude(build_prompt(move, original, later))
            fields["cost_usd"] = round(cost, 4)
            verdict, update, sources = parse_reply(reply, later)
            fields.update(status="ok", verdict=verdict, update_text=update, sources=json.dumps(sources))
    except Exception as e:  # saved as a failed check, so the reason is visible
        fields["error"] = str(e)[:500] or type(e).__name__
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute(f"""UPDATE story_checks SET {', '.join(f'{k} = ?' for k in fields)}, finished_at = ?
                             WHERE id = ?""", (*fields.values(), _utc_now(), check_id))
        return get_check(conn, check_id)


def check_surprises(emit=None, limit: int = MAX_AUTOMATIC, within_days: int | None = None) -> list[dict]:
    """The automatic checks: each recent surprise move that hasn't had one yet (at most `limit` at a time).
    Recent means within `within_days` (AUTOMATIC_WITHIN_DAYS) of the latest close, so older surprises, such as
    those in reports from before follow-through was added, don't spend money on today's headlines."""
    emit = emit or (lambda event: None)
    within = AUTOMATIC_WITHIN_DAYS if within_days is None else within_days
    since = (followups.last_complete_session() - timedelta(days=within)).isoformat()
    with closing(connect()) as conn:
        due = conn.execute(
            """SELECT f.session_date, f.ticker FROM followups f
               WHERE f.surprise = 1 AND f.session_date >= ? AND NOT EXISTS (
                   SELECT 1 FROM story_checks c WHERE c.session_date = f.session_date AND c.ticker = f.ticker
                   AND c.trigger = 'surprise')
               ORDER BY f.session_date DESC, f.ticker LIMIT ?""", (since, limit)).fetchall()
    done = []
    for row in due:
        emit({"type": "progress", "message": f"Checking the news on {row['ticker']}'s move of {row['session_date']} (a surprise)"})
        done.append(check(row["session_date"], row["ticker"], "surprise", emit))
    return done


def after_final_report(emit=None, within_days: int | None = None) -> dict:
    """Run after each final report: fill in follow-ups (free), then check any new surprises.
    Problems here are reported, never raised, so they can't spoil the run that called this."""
    emit = emit or (lambda event: None)
    result = {"followups": None, "checks": [], "problems": []}
    try:
        result["followups"] = followups.update("after a final report")
        f = result["followups"]
        emit({"type": "followups", "message": f"Follow-through: {f['added']} new move{'s' if f['added'] != 1 else ''}, {f['updated']} updated"
              + (f", {f['new_surprises']} new surprise{'s' if f['new_surprises'] != 1 else ''}" if f["new_surprises"] else "")})
    except Exception as e:
        result["problems"].append(f"follow-through: {e}")
    try:
        result["checks"] = check_surprises(emit, within_days=within_days)
        cost = sum(c["cost_usd"] for c in result["checks"])
        if result["checks"]:
            emit({"type": "stories", "message": f"Story updates: checked {len(result['checks'])} surprise"
                  f"{'s' if len(result['checks']) != 1 else ''} · ${cost:.3f}"})
    except Exception as e:
        result["problems"].append(f"story updates: {e}")
    for problem in result["problems"]:
        emit({"type": "warning", "message": f"Saved, but {problem}. It will catch up after the next final report."})
    return result


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _check_row(row) -> dict:
    c = dict(row)
    c["sources"] = json.loads(c["sources"] or "[]")
    c["verdict_label"] = VERDICTS.get(c["verdict"]) if c["status"] != "no_news" else "No newer news"
    return c


def get_check(conn, check_id: int) -> dict:
    return _check_row(conn.execute("SELECT * FROM story_checks WHERE id = ?", (check_id,)).fetchone())


def latest(conn, ticker: str | None = None, limit: int = 100) -> list[dict]:
    """Finished checks, newest first, each with its move."""
    try:
        rows = conn.execute(
            f"""SELECT c.* FROM story_checks c WHERE c.status != 'running'{' AND c.ticker = ?' if ticker else ''}
                ORDER BY c.finished_at DESC, c.session_date DESC, c.id DESC LIMIT ?""",
            ([ticker.upper()] if ticker else []) + [limit]).fetchall()
        found = {(r["session_date"], r["ticker"]): r for r in conn.execute("SELECT * FROM followups")}
    except Exception:  # not set up yet
        return []
    checks = []
    for r in rows:
        c = _check_row(r)
        move = found.get((c["session_date"], c["ticker"]))
        c["move"] = followups._move(move) if move else None
        checks.append(c)
    return checks


def unchecked(conn, since: str, limit: int = 40) -> list[dict]:
    """Recent flagged moves with no finished check yet: the ones the tab offers to check."""
    recent = "SELECT f.* FROM followups f WHERE f.session_date >= ?"
    checked = """ AND NOT EXISTS (SELECT 1 FROM story_checks c WHERE c.session_date = f.session_date
                  AND c.ticker = f.ticker AND c.status IN ('ok', 'no_news'))"""
    order = " ORDER BY f.session_date DESC, f.ticker LIMIT ?"
    rows = []
    for sql in (recent + checked + order, recent + order):  # the second before any story has been checked
        try:
            rows = conn.execute(sql, (since, limit)).fetchall()
            break
        except Exception:  # no story_checks table yet (or no followups table: nothing to offer)
            continue
    return [followups._move(r) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Story updates: what the news has said since a flagged move.")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("check", help="check one flagged move's story now (a few cents)")
    one.add_argument("ticker")
    one.add_argument("date")
    commands.add_parser("list", help="the latest story updates")
    args = parser.parse_args()
    if args.command == "check":
        try:
            c = check(args.date, args.ticker, emit=lambda e: print(e["message"]))
        except StoryError as e:
            raise SystemExit(str(e))
        if c["status"] == "failed":
            raise SystemExit(f"failed: {c['error']}")
        print(f"{c['verdict_label']}: {c['update_text']}  (${c['cost_usd']:.3f})")
        for s in c["sources"]:
            print(f"  - {s['publisher']}: {s['title']} {s['url'] or ''}")
    else:
        with closing(reports_db.connect(readonly=True)) as conn:
            for c in latest(conn, limit=30):
                print(f"{c['finished_at']}  {c['ticker']:<6} move of {c['session_date']}  "
                      f"{c['verdict_label'] or c['status']:<14} {c['update_text'] or c['error'] or ''}")


if __name__ == "__main__":
    main()
