"""Discord alerts for the market analyst agent.

After each run saves a report, run_brief.py calls notify(), which compares the saved
report with the alerts already sent and posts whatever is new:
- While the market is open: one message for tickers flagged for the first time today.
  A ticker alerts once per day, unless its move later grows a lot (or reverses).
- After the final report: one end-of-day summary per day.
Every alert is logged in the reports database. One that fails is retried by the next run.

Set it up:
    export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
    python alerts.py test

Other commands:
    python alerts.py preview [DATE]       what would be sent now, without sending (works without a webhook)
    python alerts.py log                  recent alerts
    python alerts.py summary DATE         send a day's summary (add --force to send it again)

The webhook address works like a password: anyone who has it can post in your channel.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv

import reports_db

load_dotenv()  # picks up DISCORD_WEBHOOK_URL from .env

WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
APP_URL = os.environ.get("ALERTS_APP_URL", "").rstrip("/")  # e.g. http://localhost:8000: adds links to the app
SEND_FLAG_ALERTS = True      # newly flagged tickers while the market is open
SEND_DAILY_SUMMARY = True    # one summary after each final report
ESCALATE_Z = 1.5             # alert a ticker again the same day if its |z-score| grows by this much
PENDING_SECONDS = 120        # an alert being sent by another run counts as sent for this long
USERNAME = "Market Analyst"
COLORS = {"up": 0x12805C, "down": 0xC0392B, "neutral": 0x5F6B7A}
WEBHOOK_PREFIXES = tuple(f"https://{host}/api/webhooks/" for host in
                         ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"))
# Discord's limits for one message
MAX_EMBEDS, MAX_TITLE, MAX_DESCRIPTION, MAX_CONTENT, MAX_TOTAL = 10, 256, 4096, 2000, 6000

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY,
    session_date  TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('flag', 'summary')),
    ticker        TEXT,                -- flag alerts only
    return_1d_pct REAL,
    return_zscore REAL,
    as_of         TEXT,                -- the report's as_of when the alert was decided
    status        TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
    error         TEXT,
    created_at    TEXT NOT NULL,       -- UTC timestamps
    sent_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_day ON alerts (session_date, kind, ticker);
"""


class SendError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def webhook_url() -> str | None:
    """The webhook from the environment, or None. Raises ValueError if it isn't a Discord webhook."""
    url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not url:
        return None
    if not url.startswith(WEBHOOK_PREFIXES):
        raise ValueError(f"{WEBHOOK_ENV} must be a Discord webhook URL (https://discord.com/api/webhooks/...)")
    return url


def enabled() -> bool:
    try:
        return webhook_url() is not None
    except ValueError:
        return False


def connect():
    """The reports database, with the alerts log table added if it's missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def post(payload: dict) -> str:
    """Send one message to the Discord webhook. Returns Discord's message id.

    Waits once and retries if Discord asks us to slow down. Error messages never
    include the webhook address.
    """
    url = webhook_url()
    if not url:
        raise SendError(f"{WEBHOOK_ENV} isn't set")
    body = json.dumps({"username": USERNAME, "allowed_mentions": {"parse": []}, **payload}).encode()
    request = urllib.request.Request(
        url + "?wait=true", data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "market-agent-alerts/1.0"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return str(json.loads(response.read() or b"{}").get("id", ""))
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code == 429 and attempt == 1:  # rate limited: Discord says how long to wait, in seconds
                try:
                    wait = float(json.loads(detail).get("retry_after", 1))
                except ValueError:
                    wait = 1.0
                if wait <= 5:
                    time.sleep(wait)
                    continue
            if e.code == 404:
                raise SendError("Discord says this webhook doesn't exist (deleted?). Create a new one.") from None
            raise SendError(f"Discord refused the message ({e.code}): {detail}") from None
        except urllib.error.URLError as e:
            raise SendError(f"couldn't reach Discord ({e.reason})") from None
    raise SendError("Discord is rate limiting this webhook; try again shortly")


send = post  # tests and the test environment swap this for a fake


# ---------------------------------------------------------------------------
# Building messages from a saved report
# ---------------------------------------------------------------------------

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")


def _shorten(text: str, limit: int) -> str:
    """Fit text in a limit. If it has to be cut, links are turned into plain text first,
    so a link is never cut in half."""
    text = text.strip()
    if len(text) <= limit:
        return text
    text = MARKDOWN_LINK.sub(r"\1", text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _section(body_md: str, heading: str) -> str:
    """The text under a markdown heading (## or ###), up to the next heading of any level."""
    match = re.search(rf"^#{{2,3}}\s+{heading}\b[^\n]*\n(.*?)(?=^#{{1,3}}\s|\Z)", body_md, re.M | re.S)
    return match.group(1).strip() if match else ""


def likely_why(body_md: str, ticker: str) -> str:
    """The agent's "Likely why" line for a ticker, from the brief."""
    match = re.search(r"^-\s*\*\*Likely why:\*\*\s*(.+)$", _section(body_md, re.escape(ticker)), re.M)
    return match.group(1).strip() if match else ""


def market_backdrop(body_md: str) -> str:
    return " ".join(_section(body_md, "Market backdrop").split())


def _app_link(path: str) -> dict:
    return {"url": f"{APP_URL}/{path}"} if APP_URL.startswith(("http://", "https://")) else {}


def flag_embed(t: dict, report: dict, previous: dict | None = None) -> dict:
    intraday = report["status"] == "intraday"
    so_far = " so far today" if intraday else ""
    pct = t["return_1d_pct"] or 0
    title = f"{t['ticker']} {pct:+.2f}%{so_far}"
    if previous:
        title = f"Bigger move: {title}" if (previous["return_zscore"] or 0) * (t["return_zscore"] or 0) > 0 \
            else f"Reversal: {title}"
    lines = [f"z-score {t['return_zscore']} · volume {t['volume_vs_avg']}x normal"
             + (" for this time of day" if intraday else "")]
    if previous:
        lines.append(f"Was {previous['return_1d_pct']:+.2f}% at {str(previous['as_of'])[11:]}")
    if t.get("context_summary"):
        lines.append(f"**Vs. sector and market:** {_shorten(t['context_summary'], 600)}")
    why = likely_why(report["body_md"], t["ticker"])
    if why:
        lines.append(f"**Likely why:** {_shorten(why, 600)}")
    return {
        "title": _shorten(title, MAX_TITLE),
        "description": _shorten("\n".join(lines), MAX_DESCRIPTION),
        "color": COLORS["up" if pct > 0 else "down" if pct < 0 else "neutral"],
        "footer": {"text": f"As of {report['as_of']} · research, not investment advice"},
        **_app_link("#/"),
    }


def flags_payload(report: dict, items: list[tuple[dict, dict | None]]) -> dict:
    new = sum(1 for _, previous in items if previous is None)
    bigger = len(items) - new
    parts = [f"{new} new flag{'s' if new != 1 else ''}"] if new else []
    if bigger:
        parts.append(f"{bigger} bigger move{'s' if bigger != 1 else ''}")
    content = f"**{' and '.join(parts).capitalize()}** in the intraday update as of {report['as_of'][11:]}"
    if len(items) > MAX_EMBEDS:
        content += f" (showing {MAX_EMBEDS}; the rest are in the app)"
    return {"content": content, "embeds": _fit([flag_embed(t, report, prev) for t, prev in items[:MAX_EMBEDS]])}


def summary_payload(report: dict) -> dict:
    tickers = report["tickers"]
    flagged = [t for t in tickers if t["category"] == "flagged"]
    lines = []
    backdrop = market_backdrop(report["body_md"])
    if backdrop:
        lines += [f"**Market:** {_shorten(backdrop, 400)}", ""]
    for t in flagged:
        read = f" · {t['move_read']}" if t.get("move_read") else ""
        why = likely_why(report["body_md"], t["ticker"])
        lines.append(f"**{t['ticker']}** {t['return_1d_pct']:+.2f}% (z-score {t['return_zscore']}){read}"
                     + (f"\n{_shorten(why, 300)}" if why else ""))
    if not flagged:
        lines.append("Nothing unusual today.")
    quiet = [f"{t['ticker']} {t['return_1d_pct']:+.2f}%" for t in tickers
             if t["category"] == "quiet" and t["return_1d_pct"] is not None]
    if quiet:
        lines += ["", f"**Quiet:** {', '.join(quiet)}"]
    errors = [t["ticker"] for t in tickers if t["category"] == "error"]
    if errors:
        lines.append(f"**Data issues:** {', '.join(errors)}")
    embed = {
        "title": _shorten(report["title"], MAX_TITLE),
        "description": _shorten("\n".join(lines), MAX_DESCRIPTION),
        "color": COLORS["neutral"],
        "footer": {"text": "End-of-day summary · research, not investment advice"},
        **_app_link(f"#/previous/{report['session_date']}"),
    }
    n = len(flagged)
    return {"content": f"**Daily summary:** {n} flagged move{'s' if n != 1 else ''}", "embeds": _fit([embed])}


def _fit(embeds: list[dict]) -> list[dict]:
    """Keep the whole message within Discord's 6,000-character limit by trimming descriptions."""
    def size():
        return sum(len(e.get("title", "")) + len(e.get("description", "")) + len(e.get("footer", {}).get("text", ""))
                   for e in embeds)
    while size() > MAX_TOTAL:
        longest = max(embeds, key=lambda e: len(e.get("description", "")))
        longest["description"] = _shorten(longest["description"], max(100, len(longest["description"]) - (size() - MAX_TOTAL) - 10))
    return embeds


# ---------------------------------------------------------------------------
# Deciding what to send
# ---------------------------------------------------------------------------

def _already(conn, session_date: str, kind: str, ticker: str | None = None) -> dict | None:
    """The latest alert of this kind that was sent (or is being sent right now by another run)."""
    recent = _stamp(_utc_now() - timedelta(seconds=PENDING_SECONDS))
    row = conn.execute(
        """SELECT * FROM alerts WHERE session_date = ? AND kind = ? AND ticker IS ?
           AND (status = 'sent' OR (status = 'pending' AND created_at >= ?))
           ORDER BY id DESC LIMIT 1""", (session_date, kind, ticker, recent)).fetchone()
    return dict(row) if row else None


def _grew(t: dict, previous: dict) -> bool:
    """Has the move grown a lot (or reversed) since its last alert?"""
    now, then = t["return_zscore"], previous["return_zscore"]
    if now is None or then is None:
        return False
    if now * then < 0:  # reversed direction
        return abs(now) >= 2
    return abs(now) >= abs(then) + ESCALATE_Z


def plan(conn, session_date: str) -> dict:
    """What notify() would send now for a day's report: {"report", "flags", "summary"}."""
    report = reports_db.get_report(conn, session_date)
    result = {"report": report, "flags": [], "summary": False}
    if report is None:
        return result
    if report["status"] == "intraday" and SEND_FLAG_ALERTS:
        for t in report["tickers"]:
            if t["category"] != "flagged":
                continue
            previous = _already(conn, session_date, "flag", t["ticker"])
            if previous is None or _grew(t, previous):
                result["flags"].append((t, previous))
    if report["status"] == "final" and SEND_DAILY_SUMMARY:
        result["summary"] = _already(conn, session_date, "summary") is None
    return result


def _record(conn, session_date: str, kind: str, report: dict, t: dict | None = None) -> int:
    cursor = conn.execute(
        """INSERT INTO alerts (session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (session_date, kind, t and t["ticker"], t and t["return_1d_pct"], t and t["return_zscore"],
         report["as_of"], _stamp(_utc_now())))
    return cursor.lastrowid


def _finish(conn, ids: list[int], error: str | None) -> None:
    conn.executemany("UPDATE alerts SET status = ?, error = ?, sent_at = ? WHERE id = ?",
                     [("failed" if error else "sent", error, None if error else _stamp(_utc_now()), i) for i in ids])


def notify(session_date: str, force_summary: bool = False) -> dict:
    """Send whatever alerts this day's saved report calls for. Safe to call after every run:
    anything already sent is skipped, and anything that failed before is tried again.

    Returns {"enabled", "sent": [...], "failed": [...]}, each entry a short description.
    """
    outcome = {"enabled": enabled(), "sent": [], "failed": []}
    if not outcome["enabled"]:
        return outcome
    with closing(connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")  # decide and claim in one step, so two runs can't both send
        try:
            todo = plan(conn, session_date)
            report = todo["report"]
            if report and force_summary and report["status"] == "final":
                todo["summary"] = True
            messages = []
            if todo["flags"]:
                ids = [_record(conn, session_date, "flag", report, t) for t, _ in todo["flags"]]
                label = "flag alert: " + ", ".join(t["ticker"] for t, _ in todo["flags"])
                messages.append((label, ids, flags_payload(report, todo["flags"])))
            if todo["summary"]:
                messages.append((f"daily summary for {session_date}", [_record(conn, session_date, "summary", report)],
                                 summary_payload(report)))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        for label, ids, payload in messages:
            try:
                send(payload)
                _finish(conn, ids, None)
                outcome["sent"].append(label)
            except Exception as e:  # recorded as failed: the next run tries again
                _finish(conn, ids, str(e) or type(e).__name__)
                outcome["failed"].append(f"{label} ({e})")
    return outcome


def recent(conn, limit: int = 20) -> list[dict]:
    """The latest alerts, newest first. Works on a read-only connection, even before the first alert."""
    try:
        return [dict(row) for row in conn.execute(
            """SELECT session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status, error,
                      created_at, sent_at FROM alerts ORDER BY id DESC LIMIT ?""", (limit,))]
    except Exception:  # no alerts table yet
        return []


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Discord alerts for the market analyst.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("test", help="send a test message")
    preview = commands.add_parser("preview", help="show what would be sent now, without sending")
    preview.add_argument("date", nargs="?", default="latest", help="YYYY-MM-DD or 'latest'")
    commands.add_parser("log", help="recent alerts")
    summary = commands.add_parser("summary", help="send a day's end-of-day summary")
    summary.add_argument("date")
    summary.add_argument("--force", action="store_true", help="send it even if it was sent already")
    args = parser.parse_args()

    if args.command == "test":
        try:
            send({"embeds": [{"title": "Alerts are set up", "color": COLORS["neutral"],
                              "description": "Flag alerts and daily summaries from your market analyst will appear here."}]})
        except (SendError, ValueError) as e:
            sys.exit(f"Couldn't send: {e}")
        print("Sent. Check your Discord channel.")
    elif args.command == "preview":
        with closing(connect()) as conn:
            day = args.date
            if day == "latest":
                row = conn.execute("SELECT session_date FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()
                if not row:
                    sys.exit("No reports yet.")
                day = row[0]
            todo = plan(conn, day)
        if todo["report"] is None:
            sys.exit(f"No report for {day}.")
        payloads = []
        if todo["flags"]:
            payloads.append(flags_payload(todo["report"], todo["flags"]))
        if todo["summary"]:
            payloads.append(summary_payload(todo["report"]))
        print(json.dumps(payloads, indent=2) if payloads else f"Nothing new to send for {day}.")
    elif args.command == "log":
        with closing(connect()) as conn:
            for a in recent(conn, 50):
                what = a["ticker"] or "summary"
                print(f"{a['created_at']}  {a['session_date']}  {a['kind']:<7}  {what:<8} {a['status']:<7} {a['error'] or ''}")
    elif args.command == "summary":
        if not enabled():
            sys.exit(f"Set {WEBHOOK_ENV} first (see the alerts guide).")
        outcome = notify(args.date, force_summary=args.force)
        print(outcome["sent"] or outcome["failed"] or "Nothing sent: the summary was already sent (use --force), "
                                                       "or that day has no final report.")


if __name__ == "__main__":
    main()
