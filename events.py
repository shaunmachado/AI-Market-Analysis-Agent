"""Upcoming events calendar: earnings, ex-dividend dates, and dated events found in the news.

Once a day when the market opens (and whenever you press "Update now" in the app), scan():
1. reads each watchlist company's calendar from Yahoo Finance: earnings and ex-dividend dates,
2. reads each company's recent news headlines,
3. asks Claude to pick out upcoming events the news gives a specific date for (product
   launches, court rulings, regulatory decisions, shareholder votes...), citing the article,
4. checks every one of Claude's events in code (a watchlist ticker, a real article from
   step 2, a date in range), and saves them in the reports database for the Calendar tab.

Without an Anthropic key, or if Claude fails, the calendar dates from step 1 are still saved.

    python events.py scan                  scan now
    python events.py scan --only-if-open   scan only if the market is open (for the daily schedule)
    python events.py list                  upcoming events
    python events.py show 2026-11-12       one day's events, with their news links
    python events.py remove 42             delete one event (by the id that list and show print)
"""

import argparse
import asyncio
import dataclasses
import json
import math
import re
import sys
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import market_tools
import reports_db

HORIZON_DAYS = 60        # how far ahead to look
NEWS_PER_TICKER = 10     # headlines read per company
MAX_EVENTS = 60          # most events accepted from one scan
MAX_TITLE, MAX_DETAILS = 80, 400
SCAN_BUDGET_USD = 0.25   # hard stop on Claude's cost per request
BATCH_TICKERS = 10       # companies per Claude request: a long watchlist becomes several small requests
STUCK_AFTER = timedelta(minutes=10)  # a "running" scan older than this is treated as crashed
KINDS = ("earnings", "dividend", "news")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    event_date  TEXT NOT NULL,                -- YYYY-MM-DD
    ticker      TEXT NOT NULL,
    company     TEXT NOT NULL,                -- short display name, e.g. "Apple"
    kind        TEXT NOT NULL CHECK (kind IN ('earnings', 'dividend', 'news')),
    title       TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '',
    date_note   TEXT,                         -- e.g. an estimated earnings window
    news_note   TEXT,                         -- what recent news says about a calendar event
    sources     TEXT NOT NULL DEFAULT '[]',   -- JSON list of {title, publisher, url, published}
    first_seen  TEXT NOT NULL,                -- UTC timestamps
    last_seen   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events (event_date, ticker);

CREATE TABLE IF NOT EXISTS event_scans (
    id           INTEGER PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    trigger      TEXT NOT NULL,               -- scheduled, manual (the app) or command line
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    tickers      INTEGER,
    articles     INTEGER,
    events_found INTEGER,
    dropped      INTEGER,
    cost_usd     REAL NOT NULL DEFAULT 0,
    message      TEXT
);
"""

SYSTEM_PROMPT = """You read recent news about a list of companies and pick out upcoming events that could move their share prices: product launches, court rulings, regulatory decisions, shareholder votes, investor days, conference presentations, deal deadlines and similar.

Rules:
- Only include an event if an article gives a specific future date for it, or one you can work out exactly from the article's published date ("next Tuesday"). If no specific day is given, leave it out.
- Only dates from TODAY to HORIZON_END (both given below).
- Every event must cite the numbered articles it comes from. Use nothing but these articles.
- Don't list earnings reports or dividend dates as new events: those come from a separate calendar. If an article adds something about one of them, attach it with same_as instead.
- title: short and plain, under 60 characters, e.g. "iPhone launch event" or "Court hearing on App Store case".
- details: one or two factual sentences from the articles. No predictions and no investment advice.
- If an event is already on the calendar (listed below), set same_as to its id. For a news event, also give its date (corrected, if the news says it moved).

Respond with only JSON, in this shape:
{"events": [{"ticker": "AAPL", "date": "2026-11-12", "title": "...", "details": "...", "sources": [3, 7], "same_as": null}]}
If there are none, respond {"events": []}."""

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],                 # it only reads the text it's given
    max_turns=1,
    max_budget_usd=SCAN_BUDGET_USD,
)


class ScanBusy(Exception):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_et() -> date:
    return market_tools.now_et().date()


def connect():
    """The reports database, with the events tables added if they're missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def _day(d: date) -> str:
    return f"{d:%b} {d.day}"  # "Nov 5" (written out, because %-d doesn't work on Windows)


# ---------------------------------------------------------------------------
# Company data from Yahoo Finance
# ---------------------------------------------------------------------------

_names: dict[str, str] = {}
SUFFIX = re.compile(r"[\s,]+(inc\.?|incorporated|corporation|corp\.?|company|co\.?|ltd\.?|limited|plc|"
                    r"n\.v\.|s\.a\.|ag|se|holdings?|group|&)$", re.I)


def short_name(name: str) -> str:
    """'JPMorgan Chase & Co.' -> 'JPMorgan Chase', 'NVIDIA Corporation' -> 'NVIDIA',
    'The Coca-Cola Company' -> 'Coca-Cola'."""
    name = " ".join((name or "").split())
    if name[:4].lower() == "the " and len(name) > 4:
        name = name[4:]
    while True:
        shorter = SUFFIX.sub("", name).strip(" ,")
        if shorter == name or not shorter:
            return name
        name = shorter


def company_name(ticker: str) -> str:
    """A short display name for the calendar, or the ticker if Yahoo doesn't have one."""
    if ticker not in _names:
        try:
            info = yf.Ticker(ticker).info or {}
            _names[ticker] = short_name(info.get("longName") or info.get("shortName") or "") or ticker
        except Exception:
            return ticker
    return _names[ticker]


def fetch_calendar(ticker: str):
    return yf.Ticker(ticker).calendar


def fetch_news(ticker: str) -> list[dict]:
    return market_tools.get_news(ticker, NEWS_PER_TICKER)


def _to_date(value) -> date | None:
    """A date from whatever Yahoo returns: date, datetime, pandas Timestamp, epoch seconds or text."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date") and callable(value.date):  # pandas Timestamp
        try:
            return value.date()
        except Exception:
            return None
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, timezone.utc).date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _calendar_dict(cal) -> dict:
    """yfinance returns a dict; some older versions returned a small table instead."""
    if isinstance(cal, dict):
        return cal
    if hasattr(cal, "to_dict"):  # pandas DataFrame
        if "Earnings Date" in getattr(cal, "index", []):  # one row per field
            return {k: [v for v in row if v is not None and str(v) != "nan"] for k, row in cal.iterrows()}
        return {k: [v for v in values.values() if v is not None and str(v) != "nan"]
                for k, values in cal.to_dict().items()}
    return {}


def _dates(value) -> list[date]:
    values = value if isinstance(value, (list, tuple)) else [value]
    return sorted({d for d in (_to_date(v) for v in values) if d})


def _first(value):
    return value[0] if isinstance(value, (list, tuple)) and value else value


def _money(value) -> str | None:
    value = _first(value)
    return f"${value:,.2f}" if isinstance(value, (int, float)) and not math.isnan(value) else None


def calendar_events(ticker: str, company: str, cal, today: date, horizon_end: date) -> list[dict]:
    """Earnings and ex-dividend dates from a company's Yahoo Finance calendar."""
    cal = _calendar_dict(cal)
    quote_page = {"title": f"{company} on Yahoo Finance", "publisher": "Yahoo Finance",
                  "url": f"https://finance.yahoo.com/quote/{ticker}/", "published": None}
    found = []

    earnings = [d for d in _dates(cal.get("Earnings Date")) if d >= today]
    if earnings and earnings[0] <= horizon_end:
        estimate = len(earnings) > 1  # Yahoo gives a window when the exact day isn't confirmed
        details = []
        average, low, high = (_money(cal.get(k)) for k in ("Earnings Average", "Earnings Low", "Earnings High"))
        if average:
            details.append(f"Analysts' average estimate is {average} a share"
                           + (f" (range {low} to {high})." if low and high else "."))
        found.append({
            "ticker": ticker, "company": company, "kind": "earnings", "event_date": earnings[0].isoformat(),
            "title": "Earnings report (date not confirmed)" if estimate else "Earnings report",
            "details": " ".join(details),
            "date_note": (f"Estimated: Yahoo Finance shows a window of {_day(earnings[0])} to {_day(earnings[-1])}."
                          if estimate else None),
            "sources": [quote_page]})

    ex_dividend = _to_date(_first(cal.get("Ex-Dividend Date")))
    if ex_dividend and today <= ex_dividend <= horizon_end:
        paid = _to_date(_first(cal.get("Dividend Date")))
        details = "Shares bought on or after this date don't receive the next dividend."
        if paid and paid >= ex_dividend:
            details += f" It's paid on {_day(paid)}."
        found.append({"ticker": ticker, "company": company, "kind": "dividend", "event_date": ex_dividend.isoformat(),
                      "title": "Ex-dividend date", "details": details, "date_note": None, "sources": [quote_page]})
    return found


# ---------------------------------------------------------------------------
# Claude: reading the news for dated events
# ---------------------------------------------------------------------------

def build_prompt(articles: list[dict], known: list[dict], today: date, horizon_end: date) -> str:
    lines = [f"TODAY: {today.isoformat()} ({today:%A})", f"HORIZON_END: {horizon_end.isoformat()}", "",
             "Already on the calendar:"]
    lines += [f"- id {e['id']}: {e['ticker']} {e['kind']} on {e['event_date']}: {e['title']}" for e in known] or ["- (nothing yet)"]
    lines += ["", "Articles:"]
    for n, a in enumerate(articles, 1):
        lines += [f"[{n}] {a['ticker']} | {a.get('publisher') or 'unknown publisher'} | published {a.get('published') or 'unknown'}",
                  f"    {a.get('title') or ''}", f"    {(a.get('summary') or '').strip()}"]
    return "\n".join(lines)


async def _ask_claude_async(prompt: str) -> tuple[str, float]:
    from run_brief import AGENT_ENV  # same auth as the report runs: the project's API key, if set (imported here:
                                     # run_brief imports this module)
    result = None
    async for message in query(prompt=prompt, options=dataclasses.replace(options, env=AGENT_ENV)):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't read the news: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(prompt))


def parse_reply(text: str) -> list:
    """The events list from Claude's reply, even if it's wrapped in a code fence or a sentence."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, list):
        raise ValueError('Claude\'s reply had no "events" list')
    return events


def validate(raw_events: list, articles: list[dict], companies: dict[str, str], known: dict[int, dict],
             today: date, horizon_end: date) -> tuple[list[dict], list[str]]:
    """Keep only events that pass every check. Returns (accepted, reasons for the rest)."""
    accepted, dropped, seen = [], [], set()
    for raw in raw_events[: MAX_EVENTS * 2]:
        if not isinstance(raw, dict):
            dropped.append("not an object")
            continue
        ticker = str(raw.get("ticker") or "").strip().upper()
        title = " ".join(str(raw.get("title") or "").split())
        label = f"{ticker or '?'} {title[:40]!r}"
        if ticker not in companies:
            dropped.append(f"{label}: not a watchlist ticker")
            continue
        refs = raw.get("sources")
        refs = [r for r in refs if type(r) is int and 1 <= r <= len(articles)] if isinstance(refs, list) else []  # not bool: True isn't article 1
        if not refs:
            dropped.append(f"{label}: no valid article cited")
            continue
        same_as = raw.get("same_as")
        target = known.get(same_as) if type(same_as) is int else None
        if target and target["ticker"] != ticker:
            target = None
        if target and target["kind"] != "news":  # extra news for an earnings or dividend date: date stays as is
            event_date = date.fromisoformat(target["event_date"])
        else:
            try:
                event_date = date.fromisoformat(str(raw.get("date"))[:10])
            except ValueError:
                dropped.append(f"{label}: no valid date")
                continue
        if not today <= event_date <= horizon_end:
            dropped.append(f"{label}: date {event_date} is outside {today} to {horizon_end}")
            continue
        if not title and not target:
            dropped.append(f"{label}: no title")
            continue
        key = (ticker, event_date, (target or {}).get("id") or title.lower())
        if key in seen:
            continue
        seen.add(key)
        sources = [{k: articles[r - 1].get(k) for k in ("title", "publisher", "url", "published")}
                   for r in dict.fromkeys(refs)]
        accepted.append({
            "ticker": ticker, "company": companies[ticker], "kind": "news", "event_date": event_date.isoformat(),
            "title": title[:MAX_TITLE].rstrip() if title else target["title"],
            "details": " ".join(str(raw.get("details") or "").split())[:MAX_DETAILS],
            "sources": [s for s in sources if str(s.get("url") or "").startswith(("http://", "https://"))] or sources,
            "same_as": target["id"] if target else None,
        })
        if len(accepted) >= MAX_EVENTS:
            break
    return accepted, dropped


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def _merge_sources(old_json: str, new: list[dict]) -> str:
    merged = {s.get("url") or s.get("title"): s for s in json.loads(old_json or "[]")}
    for s in new:
        merged[s.get("url") or s.get("title")] = s
    return json.dumps(list(merged.values()))


def save_calendar(conn, ticker: str, found: list[dict], today: date) -> None:
    """Yahoo's calendar is the authority for earnings and dividend dates: upcoming ones it no
    longer lists (moved or cancelled) are removed. Past events are never changed."""
    now = _utc_now()
    keep = []
    for e in found:
        row = conn.execute("SELECT id, sources FROM events WHERE ticker = ? AND kind = ? AND event_date = ?",
                           (ticker, e["kind"], e["event_date"])).fetchone()
        if row:
            conn.execute("""UPDATE events SET company = ?, title = ?, details = ?, date_note = ?, sources = ?,
                            last_seen = ? WHERE id = ?""",
                         (e["company"], e["title"], e["details"], e["date_note"],
                          _merge_sources(row["sources"], e["sources"]), now, row["id"]))
            keep.append(row["id"])
        else:
            keep.append(conn.execute(
                """INSERT INTO events (event_date, ticker, company, kind, title, details, date_note, sources,
                   first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (e["event_date"], ticker, e["company"], e["kind"], e["title"], e["details"], e["date_note"],
                 json.dumps(e["sources"]), now, now)).lastrowid)
    conn.execute(f"""DELETE FROM events WHERE ticker = ? AND kind IN ('earnings', 'dividend') AND event_date >= ?
                     AND id NOT IN ({','.join('?' * len(keep)) or 'NULL'})""", (ticker, today.isoformat(), *keep))


def save_news(conn, accepted: list[dict]) -> None:
    """News events build up over the days: an event stays on the calendar after the article
    about it drops out of the news feed. Matching events (same_as) are updated, not repeated."""
    now = _utc_now()
    for e in accepted:
        row = None
        if e["same_as"]:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (e["same_as"],)).fetchone()
        if row is None:
            row = conn.execute("""SELECT * FROM events WHERE ticker = ? AND kind = 'news' AND event_date = ?
                                  AND lower(title) = lower(?)""", (e["ticker"], e["event_date"], e["title"])).fetchone()
        if row is None:
            conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, details, sources,
                            first_seen, last_seen) VALUES (?, ?, ?, 'news', ?, ?, ?, ?, ?)""",
                         (e["event_date"], e["ticker"], e["company"], e["title"], e["details"],
                          json.dumps(e["sources"]), now, now))
        elif row["kind"] == "news":
            conn.execute("""UPDATE events SET event_date = ?, title = ?, details = ?, sources = ?, last_seen = ?
                            WHERE id = ?""",
                         (e["event_date"], e["title"], e["details"] or row["details"],
                          _merge_sources(row["sources"], e["sources"]), now, row["id"]))
        else:  # news about an earnings or dividend date
            conn.execute("UPDATE events SET news_note = ?, sources = ?, last_seen = ? WHERE id = ?",
                         (e["details"] or row["news_note"], _merge_sources(row["sources"], e["sources"]), now, row["id"]))


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------

def _start_scan(conn, trigger: str) -> int:
    with transaction(conn):  # check and claim in one step, so two scans can't start together
        running = conn.execute("SELECT started_at FROM event_scans WHERE status = 'running' "
                               "ORDER BY id DESC LIMIT 1").fetchone()
        if running and _utc_now() < (datetime.fromisoformat(running[0].replace("Z", "+00:00"))
                                     + STUCK_AFTER).strftime("%Y-%m-%dT%H:%M:%SZ"):
            raise ScanBusy("An events scan is already running. Try again in a minute.")
        conn.execute("UPDATE event_scans SET status = 'failed', message = 'stopped unexpectedly' "
                     "WHERE status = 'running'")
        scan_id = conn.execute("INSERT INTO event_scans (started_at, trigger, status) VALUES (?, ?, 'running')",
                               (_utc_now(), trigger)).lastrowid
    return scan_id


def scan(trigger: str = "command line", emit=None) -> dict:
    """Update the calendar. Returns the finished scan's summary. Raises ScanBusy if one is running."""
    emit = emit or (lambda event: None)
    today = today_et()
    horizon_end = today + timedelta(days=HORIZON_DAYS)
    tickers = market_tools.load_watchlist()
    with closing(connect()) as conn:
        scan_id = _start_scan(conn, trigger)
        problems, cost, articles, accepted, dropped = [], 0.0, [], [], []
        try:
            companies = {}
            for ticker in tickers:
                emit({"type": "progress", "message": f"Checking {ticker}'s calendar and news"})
                companies[ticker] = company_name(ticker)
                try:
                    found = calendar_events(ticker, companies[ticker], fetch_calendar(ticker), today, horizon_end)
                    with transaction(conn):  # one ticker at a time
                        save_calendar(conn, ticker, found, today)
                except Exception as e:  # keep that ticker's saved dates; carry on with the rest
                    problems.append(f"{ticker} calendar: {e}")
                try:
                    articles += [{**a, "ticker": ticker} for a in fetch_news(ticker)]
                except Exception as e:
                    problems.append(f"{ticker} news: {e}")

            known_rows = [dict(r) for r in conn.execute(
                "SELECT id, ticker, kind, event_date, title FROM events WHERE event_date >= ? ORDER BY event_date",
                (today.isoformat(),))] if articles else []
            batches = [tickers[i:i + BATCH_TICKERS] for i in range(0, len(tickers), BATCH_TICKERS)]
            for n, batch in enumerate(batches, 1):
                batch_articles = [a for a in articles if a["ticker"] in batch]
                if not batch_articles:  # no headlines, no request (and no cost)
                    continue
                group = f" (group {n} of {len(batches)})" if len(batches) > 1 else ""
                emit({"type": "progress", "message": f"Reading {len(batch_articles)} headlines for dated events{group}"})
                try:
                    reply, batch_cost = ask_claude(build_prompt(
                        batch_articles, [r for r in known_rows if r["ticker"] in batch], today, horizon_end))
                    cost += batch_cost
                    found, left_out = validate(parse_reply(reply), batch_articles, companies,
                                               {r["id"]: r for r in known_rows}, today, horizon_end)
                    with transaction(conn):
                        save_news(conn, found)
                    accepted += found
                    dropped += left_out
                except Exception as e:  # one group failing doesn't lose the others
                    problems.append(f"news scan{group}: {e}")
            status = "partial" if problems else "ok"
            message = "; ".join(problems)[:1000] or None
        except Exception as e:
            status, message = "failed", str(e)[:1000] or type(e).__name__
        conn.execute("""UPDATE event_scans SET finished_at = ?, status = ?, tickers = ?, articles = ?,
                        events_found = ?, dropped = ?, cost_usd = ?, message = ? WHERE id = ?""",
                     (_utc_now(), status, len(tickers), len(articles), len(accepted), len(dropped),
                      round(cost, 4), message, scan_id))
        summary = last_scan(conn)
    summary["dropped_reasons"] = dropped
    emit({"type": "finished", "scan": summary})
    return summary


def add_calendar_dates(ticker: str) -> int:
    """A newly tracked company's earnings and dividend dates, straight away (Yahoo only: no Claude,
    no cost). Its news events follow with the next daily scan. Returns how many dates were found."""
    today = today_et()
    found = calendar_events(ticker, company_name(ticker), fetch_calendar(ticker), today,
                            today + timedelta(days=HORIZON_DAYS))
    with closing(connect()) as conn, transaction(conn):
        save_calendar(conn, ticker, found, today)
    return len(found)


# ---------------------------------------------------------------------------
# Reading (the API and the command line)
# ---------------------------------------------------------------------------

def _row(r) -> dict:
    event = dict(r)
    event["sources"] = json.loads(event["sources"] or "[]")
    return event


def events_between(conn, start: str, end: str) -> list[dict]:
    """Events from start to end (YYYY-MM-DD, inclusive), by date then company.
    Works on a read-only connection, even before the first scan."""
    try:
        rows = conn.execute("""SELECT * FROM events WHERE event_date BETWEEN ? AND ?
                               ORDER BY event_date, company, kind, title""", (start, end))
        return [_row(r) for r in rows]
    except Exception:  # no events table yet
        return []


def last_scan(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM event_scans ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:
        return None
    return dict(row) if row else None


def watchlist_tickers() -> list[str] | None:
    """The watchlist, or None (meaning every ticker) if it can't be read."""
    try:
        return market_tools.load_watchlist()
    except OSError:
        return None


def upcoming(conn, start: date, days: int, tickers=None) -> list[dict]:
    """Events from start to `days` days later (both included), for some tickers or all of them.
    Used by the brief's upcoming_events tool, the Discord alerts and Ask."""
    found = events_between(conn, start.isoformat(), (start + timedelta(days=days)).isoformat())
    return [e for e in found if tickers is None or e["ticker"] in tickers]


def confirmed(event: dict) -> bool:
    """False for an earnings date Yahoo only gives as an estimated window."""
    return not (event.get("date_note") or "").startswith("Estimated")


def event_line(event: dict, company: bool = True) -> str:
    """One event as a short line: 'Mon Nov 9: Microsoft (MSFT): Court hearing in patent case'."""
    d = date.fromisoformat(event["event_date"])
    who = f"{event['company']} ({event['ticker']}): " if company else ""
    return f"{d:%a} {_day(d)}: {who}{event['title']}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upcoming events calendar.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("scan", help="update the calendar now")
    run.add_argument("--only-if-open", action="store_true", help="skip unless the market is open (for the schedule)")
    commands.add_parser("list", help="upcoming events")
    show = commands.add_parser("show", help="one day's events")
    show.add_argument("date")
    remove = commands.add_parser("remove", help="delete one event, e.g. one the news got wrong")
    remove.add_argument("id", type=int)
    args = parser.parse_args()

    if args.command == "scan":
        if args.only_if_open and market_tools.market_session()["status"] != "in_progress":
            print("The market isn't open, so the scheduled events scan was skipped.")
            return
        try:
            result = scan("scheduled" if args.only_if_open else "command line",
                          emit=lambda e: print(e.get("message", "")) if e["type"] == "progress" else None)
        except ScanBusy as e:
            sys.exit(str(e))
        print(f"{result['status']}: {result['events_found']} news events from {result['articles']} headlines, "
              f"${result['cost_usd']:.3f}" + (f" ({result['message']})" if result["message"] else ""))
        for reason in result["dropped_reasons"]:
            print(f"  left out: {reason}")
    elif args.command == "remove":
        with closing(connect()) as conn:
            gone = conn.execute("DELETE FROM events WHERE id = ?", (args.id,)).rowcount
        print("Removed." if gone else f"No event with id {args.id}.")
    else:
        with closing(reports_db.connect(readonly=True)) as conn:
            if args.command == "list":
                start = today_et().isoformat()
                rows = events_between(conn, start, (today_et() + timedelta(days=HORIZON_DAYS)).isoformat())
            else:
                rows = events_between(conn, args.date, args.date)
        for e in rows:
            print(f"{e['id']:>5}  {e['event_date']}  {e['company']:<18} {e['kind']:<9} {e['title']}")
            if args.command == "show":
                for line in (e["date_note"], e["details"], e["news_note"]):
                    if line:
                        print(f"    {line}")
                for s in e["sources"]:
                    print(f"    - {s.get('publisher') or ''}: {s.get('title') or ''} {s.get('url') or ''}")
        if not rows:
            print("Nothing on the calendar." + (" Run: python events.py scan" if args.command == "list" else ""))


if __name__ == "__main__":
    main()
