"""JSON API for the frontend: reports, live updates, on-demand runs and questions.

Run:
    uvicorn api:app --port 8000

Endpoints:
    GET  /api/health
    GET  /api/reports?limit=30&before=YYYY-MM-DD&status=final|intraday
    GET  /api/reports/latest
    GET  /api/reports/{YYYY-MM-DD}
    GET  /api/tickers/{TICKER}/history?limit=30
    GET  /api/tickers/{TICKER}/prices?range=1mo|3mo|6mo|1y   daily prices for charts
    GET  /api/search?q=...&limit=12&ticker=&since=&until=     search passages in all reports
    GET  /api/search/status     what the search index contains
    GET  /api/alerts?limit=10   Discord alerts: whether they're on here, and the latest ones
    GET  /api/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD   upcoming events (and past ones) between two dates
    POST /api/calendar/scan     update the events calendar now
    GET  /api/calendar/scan     the calendar update in progress, or the last one
    GET  /api/watchlist         tracked stocks, main ones first, with latest figures and next event
    GET  /api/stocks/search?q=  find US stocks and ETFs by name or ticker (Yahoo Finance)
    POST /api/watchlist                   track a stock: {"ticker": "COST", "main": false}
    POST /api/watchlist/{TICKER}          star or unstar it: {"main": true}
    POST /api/watchlist/{TICKER}/remove   stop tracking it
    GET  /api/followups?horizon=1|5|20&ticker=   flagged moves and what the price did after them
    POST /api/followups/refresh  fill in follow-through prices now (Yahoo only, free)
    GET  /api/stories?ticker=    story updates (what later news said), and recent moves to check
    POST /api/stories/check      re-check one move's news now: {"session_date": "2026-10-13", "ticker": "MSFT"}
    GET  /api/filings?ticker=    company filings from the SEC, with first takes, and results expected but not filed
    POST /api/filings/check      look for new filings now (free; new results announcements are read)
    POST /api/filings/read       read one filing with Claude now: {"accession": "0000789019-26-000123"}
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules
(a run also logs the Discord alerts it sends). The events calendar is written the same
way, by events.py's scan (daily at the market open, or "Update now"). The Stocks tab edits
watchlist.txt, through watchlist.py's safe edits. Follow-through and story updates are written
by followups.py and stories.py (after each final report, or "Refresh prices" and "Check for updates").
Filings and first takes are written by filings.py (before each run, or "Check now" and "Read this filing").
The API does write the search index (search.db), which is rebuilt from reports.db.
If frontend/dist exists (after `npm run build`), the app is served at /.
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from contextlib import asynccontextmanager, closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import alerts
import ask
import edgar
import filings
import followups
import market_tools
import events as upcoming  # events.py ("events" here is the live-updates endpoint)
import prices
import reports_db
import run_brief
import search_index
import stories
import watchlist

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
ACCESSION = re.compile(r"\d{10}-\d{2}-\d{6}")                              # the SEC's number for a filing
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "60"))  # between on-demand runs
CALENDAR_SCAN_COOLDOWN_SECONDS = int(os.environ.get("CALENDAR_SCAN_COOLDOWN_SECONDS", "300"))
MAX_CALENDAR_DAYS = 100                                                   # longest date range one request returns
POLL_SECONDS = float(os.environ.get("REPORT_POLL_SECONDS", "2"))         # how often to check for new reports
AUTO_CLOSE = os.environ.get("AUTO_CLOSE_RUN", "1") != "0"                 # write the final report after the close
AUTO_CLOSE_TIME = os.environ.get("AUTO_CLOSE_TIME", "16:15")              # Eastern time, 15 minutes after the bell
AUTO_CLOSE_CHECK_SECONDS = float(os.environ.get("AUTO_CLOSE_CHECK_SECONDS", "30"))
AUTO_CLOSE_RETRY_SECONDS = 15 * 60
AUTO_CLOSE_MAX_ATTEMPTS = 3
FOLLOWUP_REFRESH_COOLDOWN_SECONDS = int(os.environ.get("FOLLOWUP_REFRESH_COOLDOWN_SECONDS", "60"))
STORY_CHECK_COOLDOWN_SECONDS = int(os.environ.get("STORY_CHECK_COOLDOWN_SECONDS", "30"))  # each check can cost a few cents
STORY_DAYS = 30                                                           # recent moves offered for a news check
FILINGS_CHECK_COOLDOWN_SECONDS = int(os.environ.get("FILINGS_CHECK_COOLDOWN_SECONDS", "60"))
FILING_READ_COOLDOWN_SECONDS = int(os.environ.get("FILING_READ_COOLDOWN_SECONDS", "30"))  # each read costs a few cents
MAX_ACTIVE_QUESTIONS = 2
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"


class BadRequest(ValueError):
    pass


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def _limit(request, default: int = 30, maximum: int = 365) -> int:
    raw = request.query_params.get("limit", str(default))
    if not (raw.isascii() and raw.isdigit()) or not 1 <= int(raw) <= maximum:  # isdigit() alone accepts "²"
        raise BadRequest(f"limit must be a whole number from 1 to {maximum}")
    return int(raw)


def _db():
    return closing(reports_db.connect(readonly=True))  # reading never writes


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Reports (read-only)
# ---------------------------------------------------------------------------

def health(request):
    with _db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    return JSONResponse({"status": "ok", "reports": count})


def list_reports(request):
    try:
        limit = _limit(request)
        before = request.query_params.get("before")
        status = request.query_params.get("status")
        if before and not DATE.fullmatch(before):
            raise BadRequest("before must be a date like 2026-11-06")
        if status and status not in ("intraday", "final"):
            raise BadRequest("status must be 'intraday' or 'final'")
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        return JSONResponse({"reports": reports_db.list_reports(conn, limit, before, status)})


def latest_report(request):
    with _db() as conn:
        report = reports_db.latest_report(conn)
    return JSONResponse(report) if report else _error(404, "no reports yet")


def get_report(request):
    day = request.path_params["session_date"]
    if not DATE.fullmatch(day):
        return _error(400, "use a date like 2026-11-06, or 'latest'")
    with _db() as conn:
        report = reports_db.get_report(conn, day)
    return JSONResponse(report) if report else _error(404, f"no report for {day}")


def ticker_history(request):
    ticker = request.path_params["ticker"]
    if not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    try:
        limit = _limit(request)
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        history = reports_db.ticker_history(conn, ticker, limit)
    return JSONResponse({"ticker": ticker.upper(), "history": history})


def ticker_prices(request):
    """Daily closing prices for a chart. Runs in a worker thread, so a slow download
    doesn't hold up anything else."""
    ticker = request.path_params["ticker"]
    period = request.query_params.get("range", "3mo")
    if not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    if period not in prices.RANGES:
        return _error(400, f"range must be one of: {', '.join(prices.RANGES)}")
    try:
        rows = prices.get_prices(ticker.upper(), period)
    except Exception as e:  # network problem, rate limit, unknown ticker...
        return _error(502, f"couldn't load prices for {ticker.upper()} ({e})")
    if not rows:
        return _error(404, f"no price data for {ticker.upper()}")
    return JSONResponse({"ticker": ticker.upper(), "range": period, "prices": rows})


# ---------------------------------------------------------------------------
# Search (the retrieval part of RAG). The index lives in search.db, never in reports.db.
# ---------------------------------------------------------------------------

log = logging.getLogger(__name__)

_index_lock = threading.Lock()  # one background embedding job at a time
_background = set()  # keeps background tasks alive until they finish


def _update_index_quietly() -> None:
    """Index and embed new reports. Problems are logged, never fatal."""
    with _index_lock:
        try:
            search_index.sync()
        except Exception as e:
            log.warning("Search index update failed (it will retry on the next report): %s", e)


def update_index_in_background() -> None:
    task = asyncio.create_task(asyncio.to_thread(_update_index_quietly))
    _background.add(task)
    task.add_done_callback(_background.discard)


def alerts_status(request):
    """Whether runs started from this server send Discord alerts, and the latest alerts
    sent by any run (scheduled runs included)."""
    try:
        limit = _limit(request, default=10, maximum=100)
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        latest = alerts.recent(conn, limit)
    return JSONResponse({"enabled": alerts.enabled(), "alerts": latest})


def calendar(request):
    """Events between start and end. Without dates: this month's calendar (6 weeks from its first day)."""
    today = upcoming.today_et()
    start, end = request.query_params.get("start"), request.query_params.get("end")
    try:
        for name, value in (("start", start), ("end", end)):
            if value and not DATE.fullmatch(value):
                raise BadRequest(f"{name} must be a date like 2026-11-06")
        first = date.fromisoformat(start) if start else today.replace(day=1)
        last = date.fromisoformat(end) if end else first + timedelta(days=41)
        if last < first:
            raise BadRequest("end must be on or after start")
        if (last - first).days > MAX_CALENDAR_DAYS:
            raise BadRequest(f"ask for at most {MAX_CALENDAR_DAYS} days at a time")
    except BadRequest as e:
        return _error(400, str(e))
    except ValueError:
        return _error(400, "that isn't a real date")
    with _db() as conn:
        found = upcoming.events_between(conn, first.isoformat(), last.isoformat())
        scanned = upcoming.last_scan(conn)
        reported = filings.for_calendar(conn, found, first.isoformat(), last.isoformat())  # results actually filed
    return JSONResponse({"today": today.isoformat(), "start": first.isoformat(), "end": last.isoformat(),
                         "events": found, "reported": reported, "last_scan": scanned, "scan": calendar_scans.snapshot()})


def search_reports(request):
    q = request.query_params.get("q", "").strip()
    ticker = request.query_params.get("ticker")
    since, until = request.query_params.get("since"), request.query_params.get("until")
    try:
        limit = _limit(request, default=12, maximum=50)
        if not q:
            raise BadRequest("q is required")
        if len(q) > ask.MAX_QUESTION_CHARS:
            raise BadRequest(f"keep searches under {ask.MAX_QUESTION_CHARS} characters")
        if ticker and not TICKER.fullmatch(ticker):
            raise BadRequest("invalid ticker")
        for name, value in (("since", since), ("until", until)):
            if value and not DATE.fullmatch(value):
                raise BadRequest(f"{name} must be a date like 2026-11-06")
    except BadRequest as e:
        return _error(400, str(e))
    search_index.sync(embed_now=False)  # the newest reports are searchable by keyword straight away
    return JSONResponse(search_index.search(q, limit, ticker, since, until))


def search_status(request):
    return JSONResponse(search_index.status())


# ---------------------------------------------------------------------------
# Tracked stocks (the Stocks tab, and the main ones on the Today tab)
# ---------------------------------------------------------------------------

_names_requested: set[str] = set()  # company names being looked up, so each is only asked for once


def _watchlist_view() -> dict:
    """Every tracked stock, main ones first, with its latest figures and next calendar event."""
    tracked = watchlist.entries()
    tickers = [e["ticker"] for e in tracked]
    with _db() as conn:
        latest = reports_db.latest_report(conn)
        rows = {t["ticker"]: {**t, "session_date": latest["session_date"], "status": latest["status"]}
                for t in (latest or {}).get("tickers", [])}
        for t in tickers:
            if t not in rows:  # not in the latest report (e.g. just added): its most recent figures, if any
                history = reports_db.ticker_history(conn, t, limit=1)
                if history:
                    rows[t] = history[0]
        next_event = {}
        for e in upcoming.upcoming(conn, upcoming.today_et(), upcoming.HORIZON_DAYS, tickers):
            next_event.setdefault(e["ticker"], {"event_date": e["event_date"], "kind": e["kind"], "title": e["title"],
                                                "line": upcoming.event_line(e, company=False)})
        try:
            calendar_names = dict(conn.execute("SELECT ticker, company FROM events GROUP BY ticker"))
        except Exception:  # no calendar yet
            calendar_names = {}
    stocks = []
    for e in sorted(tracked, key=lambda e: not e["main"]):  # main first, each group in list order
        row = rows.get(e["ticker"])
        stocks.append({
            "ticker": e["ticker"], "main": e["main"], "benchmark": e["benchmark"],
            "name": upcoming._names.get(e["ticker"]) or calendar_names.get(e["ticker"]),
            "latest": None if row is None else {k: row.get(k) for k in (
                "session_date", "status", "category", "price", "return_1d_pct", "return_zscore", "move_read")},
            "next_event": next_event.get(e["ticker"]),
        })
    return {"stocks": stocks, "tracked_count": len(stocks), "main_count": sum(s["main"] for s in stocks),
            "max_tracked": watchlist.MAX_TRACKED, "max_main": watchlist.MAX_MAIN}


def _in_background(coroutine) -> None:
    task = asyncio.create_task(coroutine)
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _fill_names(tickers: list[str]) -> None:
    """Look up company names Yahoo hasn't given us yet, then tell open pages to refresh."""
    def look_up():
        for t in tickers:
            try:
                upcoming._names[t] = upcoming.company_name(t)
            except Exception:
                pass
    await asyncio.to_thread(look_up)
    hub.publish({"type": "watchlist_changed"})


async def _calendar_for_new_stock(ticker: str) -> None:
    """A new stock's earnings and dividend dates (Yahoo only, no cost), so its next event shows straight away."""
    try:
        await asyncio.to_thread(upcoming.add_calendar_dates, ticker)
        hub.publish({"type": "calendar_updated", "scan": None})
    except Exception as e:
        log.warning("Couldn't add %s's calendar dates (the next daily scan will): %s", ticker, e)


async def watchlist_view(request):
    try:
        view = await asyncio.to_thread(_watchlist_view)
    except FileNotFoundError:
        return _error(404, "watchlist.txt is missing: create it with one ticker per line")
    missing = [s["ticker"] for s in view["stocks"] if not s["name"] and s["ticker"] not in _names_requested]
    if missing:
        _names_requested.update(missing)
        _in_background(_fill_names(missing))
    return JSONResponse(view)


def search_stocks(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return _error(400, "q is required")
    if len(q) > 60:
        return _error(400, "keep searches under 60 characters")
    try:
        return JSONResponse({"query": q, "results": watchlist.search(q)})
    except watchlist.WatchlistError as e:
        return _error(502, str(e))


async def _watchlist_change(request, action):
    """Shared by add, star and remove: checks, the change itself, then live updates."""
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, "send JSON")
    if not isinstance(body, dict):
        return _error(400, "send a JSON object")
    try:
        result = await asyncio.to_thread(action, body)
    except watchlist.WatchlistError as e:
        return _error(e.status, str(e))
    hub.publish({"type": "watchlist_changed"})
    return result


async def add_stock(request):
    async def respond(info):
        _in_background(_calendar_for_new_stock(info["ticker"]))
        return JSONResponse({"stock": info, "watchlist": await asyncio.to_thread(_watchlist_view)}, status_code=201)

    def action(body):
        ticker = body.get("ticker")
        if not isinstance(ticker, str):
            raise watchlist.WatchlistError('send {"ticker": "COST"}')
        return watchlist.add(ticker, main=bool(body.get("main")))

    result = await _watchlist_change(request, action)
    return await respond(result) if isinstance(result, dict) else result


async def star_stock(request):
    def action(body):
        if not isinstance(body.get("main"), bool):
            raise watchlist.WatchlistError('send {"main": true} or {"main": false}')
        watchlist.set_main(request.path_params["ticker"], body["main"])
        return _watchlist_view()

    result = await _watchlist_change(request, action)
    return JSONResponse(result) if isinstance(result, dict) else result


async def remove_stock(request):
    def action(body):
        watchlist.remove(request.path_params["ticker"])
        return _watchlist_view()

    result = await _watchlist_change(request, action)
    return JSONResponse(result) if isinstance(result, dict) else result


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------

class EventHub:
    """Sends each event to every open browser connection."""

    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    def publish(self, event: dict) -> None:
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # a stalled browser shouldn't block everyone else
                pass


hub = EventHub()


def _latest_calendar_scan() -> dict | None:
    """The most recent events scan, from any program (the daily schedule included)."""
    with _db() as conn:
        scanned = upcoming.last_scan(conn)
    return {k: scanned[k] for k in ("id", "status", "finished_at")} if scanned else None


def _latest_followups() -> tuple:
    """The latest follow-through update and story check, from any program (scheduled runs included)."""
    with _db() as conn:
        try:
            update = conn.execute("SELECT MAX(id) FROM followup_updates").fetchone()[0]
        except Exception:  # not set up yet
            update = None
        try:
            checked = conn.execute("SELECT MAX(id) FROM story_checks WHERE finished_at IS NOT NULL").fetchone()[0]
        except Exception:
            checked = None
    return update, checked


def _latest_filings() -> tuple:
    """Changes whenever any program lists a new filing, finishes a read, or confirms figures."""
    with _db() as conn:
        try:
            return (conn.execute("SELECT MAX(id) FROM filing_checks").fetchone()[0],
                    conn.execute("SELECT MAX(id) FROM filing_reads WHERE finished_at IS NOT NULL").fetchone()[0],
                    conn.execute("SELECT COUNT(*) FROM filings").fetchone()[0])
        except Exception:  # not set up yet
            return (None, None, None)


def _latest_change() -> dict | None:
    """The most recently saved report: changes whenever any run saves (scheduled or on demand)."""
    with _db() as conn:
        row = conn.execute("""SELECT session_date, status, revision, updated_at FROM reports
                              ORDER BY updated_at DESC, session_date DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


async def watch_reports() -> None:
    """Checks the database every few seconds and announces new or updated reports."""
    def watchlist_stamp():
        try:
            return market_tools.WATCHLIST_FILE.stat().st_mtime_ns
        except OSError:
            return None

    def check():  # all in one trip to a worker thread
        return _latest_change(), _latest_calendar_scan(), watchlist_stamp(), _latest_followups(), _latest_filings()

    last, last_scan, last_stamp, last_followed, last_filed = await asyncio.to_thread(check)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current, scan, stamp, followed, filed = await asyncio.to_thread(check)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if filed != last_filed:  # a new filing, a first take, or figures confirmed (by any program)
            last_filed = filed
            hub.publish({"type": "filings_updated"})
        if followed != last_followed:  # follow-through updated, or a story checked
            if followed[0] != last_followed[0]:
                hub.publish({"type": "followups_updated"})
            if followed[1] != last_followed[1]:
                hub.publish({"type": "story_checked"})
            last_followed = followed
        if current and current != last:
            last = current
            hub.publish({"type": "report_saved", **current})
            update_index_in_background()  # covers scheduled runs, which are separate programs
        if stamp != last_stamp:  # watchlist.txt changed, by the app or by hand
            last_stamp = stamp
            hub.publish({"type": "watchlist_changed"})
        if scan and scan != last_scan:
            last_scan = scan
            if scan["finished_at"]:  # a calendar update finished (scheduled or "Update now")
                hub.publish({"type": "calendar_updated", "scan": scan})


async def events(request):
    """Server-Sent Events stream. The browser's EventSource reconnects on its own."""
    queue = hub.subscribe()
    hello = {"type": "hello", "run": runs.snapshot(), "latest": await asyncio.to_thread(_latest_change),
             "calendar_scan": calendar_scans.snapshot()}

    async def stream():
        try:
            yield f"retry: 3000\ndata: {json.dumps(hello)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # stops idle connections being dropped
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
# Requests from the frontend: run now, ask a question
# ---------------------------------------------------------------------------

def _post_guard(request):
    """Stops other websites from triggering runs or questions through your browser."""
    origin = request.headers.get("origin")
    if origin and origin not in FRONTEND_ORIGINS and origin != f"{request.url.scheme}://{request.url.netloc}":
        return _error(403, "requests from this website aren't allowed")
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        return _error(415, "send JSON (Content-Type: application/json)")
    return None


class AlreadyRunning(Exception):
    pass


class TooSoon(Exception):
    pass


class RunManager:
    """One on-demand run at a time, with a cooldown between runs to cap cost."""

    def __init__(self):
        self.task = None
        self.last_started = None
        self.state = {"state": "idle", "started_at": None, "finished_at": None,
                      "log": [], "result": None, "error": None}

    def snapshot(self) -> dict:
        return {**self.state, "log": list(self.state["log"])}

    def start(self, scheduled: bool = False) -> dict:
        if self.task and not self.task.done():
            raise AlreadyRunning("A report is already being written. Its progress is shown below.")
        if self.last_started is not None and not scheduled:  # the after-close run ignores the button's cooldown
            wait = RUN_COOLDOWN_SECONDS - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(f"Please wait {seconds} second{'s' if seconds != 1 else ''} "
                              "before requesting another report.")
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None,
                      "log": [], "result": None, "error": None}
        hub.publish({"type": "run_started", "run": self.snapshot()})
        self.task = asyncio.create_task(self._run())
        return self.snapshot()

    def _emit(self, event: dict) -> None:
        self.state["log"].append(event)
        hub.publish({"type": "run_event", "event": event})

    async def _run(self) -> None:
        try:
            self.state["result"] = await run_brief.run_once(self._emit)
            self.state["state"] = "finished"
        except Exception as e:
            self.state.update(state="failed", error=str(e) or type(e).__name__)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": "run_finished", "run": self.snapshot()})


runs = RunManager()


class CalendarScanManager:
    """One "Update now" calendar scan at a time, with a cooldown to cap Claude's cost."""

    def __init__(self):
        self.task = None
        self.last_started = None
        self.state = {"state": "idle", "started_at": None, "finished_at": None, "message": None,
                      "result": None, "error": None}

    def snapshot(self) -> dict:
        return dict(self.state)

    def start(self) -> dict:
        if self.task and not self.task.done():
            raise AlreadyRunning("The calendar is already being updated.")
        if self.last_started is not None:
            wait = CALENDAR_SCAN_COOLDOWN_SECONDS - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(f"The calendar was just updated. Try again in {seconds} second{'s' if seconds != 1 else ''}.")
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None,
                      "message": "Starting…", "result": None, "error": None}
        hub.publish({"type": "calendar_scan", "scan": self.snapshot()})
        self.task = asyncio.create_task(self._run())
        return self.snapshot()

    def _progress(self, event: dict) -> None:
        if event["type"] == "progress":
            self.state["message"] = event["message"]
            hub.publish({"type": "calendar_scan", "scan": self.snapshot()})

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        emit = lambda event: loop.call_soon_threadsafe(self._progress, event)  # noqa: E731  (scan runs in a thread)
        try:
            result = await asyncio.to_thread(upcoming.scan, "manual", emit)
            result.pop("dropped_reasons", None)
            self.state.update(state="finished", result=result, message=None)
        except Exception as e:  # including ScanBusy: the daily scan is running right now
            self.state.update(state="failed", error=str(e) or type(e).__name__, message=None)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": "calendar_scan", "scan": self.snapshot()})


calendar_scans = CalendarScanManager()


async def start_run(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        run = runs.start()
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"run": run}, status_code=202)


def current_run(request):
    return JSONResponse({"run": runs.snapshot()})


async def start_calendar_scan(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        scan = calendar_scans.start()
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"scan": scan}, status_code=202)


def current_calendar_scan(request):
    return JSONResponse({"scan": calendar_scans.snapshot()})


# ---------------------------------------------------------------------------
# Follow-through (the price after flagged moves) and story updates (the news since)
# ---------------------------------------------------------------------------

class BackgroundJob:
    """One job of a kind at a time, run in a worker thread, with a cooldown: refreshing
    follow-through prices, and checking a story's news. Progress goes out as live updates."""

    def __init__(self, event_type: str, cooldown, busy: str, too_soon: str):
        self.event_type, self.cooldown, self.busy, self.too_soon = event_type, cooldown, busy, too_soon
        self.task, self.last_started = None, None
        self.state = {"state": "idle", "started_at": None, "finished_at": None, "message": None,
                      "target": None, "result": None, "error": None}

    def snapshot(self) -> dict:
        return dict(self.state)

    def start(self, work, target=None) -> dict:
        """work(emit) runs in a thread; what it returns becomes the job's result."""
        if self.task and not self.task.done():
            raise AlreadyRunning(self.busy)
        if self.last_started is not None:
            wait = self.cooldown() - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(self.too_soon.format(f"{seconds} second{'s' if seconds != 1 else ''}"))
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None, "message": "Starting…",
                      "target": target, "result": None, "error": None}
        hub.publish({"type": self.event_type, "job": self.snapshot()})
        self.task = asyncio.create_task(self._run(work))
        return self.snapshot()

    def _progress(self, event: dict) -> None:
        if event.get("type") == "progress":
            self.state["message"] = event["message"]
            hub.publish({"type": self.event_type, "job": self.snapshot()})

    async def _run(self, work) -> None:
        loop = asyncio.get_running_loop()
        emit = lambda event: loop.call_soon_threadsafe(self._progress, event)  # noqa: E731  (work runs in a thread)
        try:
            self.state.update(state="finished", result=await asyncio.to_thread(work, emit), message=None)
        except Exception as e:
            self.state.update(state="failed", error=str(e) or type(e).__name__, message=None)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": self.event_type, "job": self.snapshot()})


followup_refreshes = BackgroundJob("followups_refresh", lambda: FOLLOWUP_REFRESH_COOLDOWN_SECONDS,
                                   "Prices are already being refreshed.",
                                   "Prices were just refreshed. Try again in {}.")
story_checks = BackgroundJob("story_check", lambda: STORY_CHECK_COOLDOWN_SECONDS,
                             "A story is already being checked. Its progress is shown on the Story updates tab.",
                             "A story was just checked. Try again in {}.")


def _followups_view(horizon: int, ticker: str | None) -> dict:
    with _db() as conn:
        every = followups.moves(conn)
        updated = followups.last_update(conn)
    return {"horizon": horizon, "horizons": list(followups.HORIZONS),
            "moves": [m for m in every if not ticker or m["ticker"] == ticker.upper()],
            "tickers": sorted({m["ticker"] for m in every}), "patterns": followups.patterns(every, horizon),
            "updated": updated, "refresh": followup_refreshes.snapshot()}


async def followups_view(request):
    raw = request.query_params.get("horizon", str(followups.SURPRISE_HORIZON))
    ticker = request.query_params.get("ticker") or None
    if not (raw.isascii() and raw.isdigit()) or int(raw) not in followups.HORIZONS:
        return _error(400, f"horizon must be one of: {', '.join(map(str, followups.HORIZONS))}")
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_followups_view, int(raw), ticker))


async def refresh_followups(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        job = followup_refreshes.start(lambda emit: followups.update("manual", emit))
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"refresh": job}, status_code=202)


def _stories_view(ticker: str | None) -> dict:
    since = (upcoming.today_et() - timedelta(days=STORY_DAYS)).isoformat()
    with _db() as conn:
        found = stories.latest(conn, ticker)
        todo = stories.unchecked(conn, since)
    return {"checks": found, "unchecked": [m for m in todo if not ticker or m["ticker"] == ticker.upper()],
            "days": STORY_DAYS, "check": story_checks.snapshot(), "max_cost_usd": stories.CHECK_BUDGET_USD}


async def stories_view(request):
    ticker = request.query_params.get("ticker") or None
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_stories_view, ticker))


async def check_story(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"session_date": "2026-10-13", "ticker": "MSFT"}')
    day = body.get("session_date") if isinstance(body, dict) else None
    ticker = body.get("ticker") if isinstance(body, dict) else None
    if not isinstance(day, str) or not DATE.fullmatch(day) or not isinstance(ticker, str) or not TICKER.fullmatch(ticker):
        return _error(400, 'send JSON like {"session_date": "2026-10-13", "ticker": "MSFT"}')
    ticker = ticker.upper()
    with _db() as conn:  # a quick check first, so a wrong move is refused straight away
        try:
            known = conn.execute("SELECT 1 FROM followups WHERE session_date = ? AND ticker = ?", (day, ticker)).fetchone()
        except Exception:
            known = None
    if not known:
        return _error(404, f"{ticker} wasn't flagged in the final report of {day}.")
    try:
        job = story_checks.start(lambda emit: stories.check(day, ticker, "manual", emit),
                                 target={"session_date": day, "ticker": ticker})
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"check": job}, status_code=202)


# ---------------------------------------------------------------------------
# Company filings (the Filings tab)
# ---------------------------------------------------------------------------

filing_checks = BackgroundJob("filings_check", lambda: FILINGS_CHECK_COOLDOWN_SECONDS,
                              "Filings are already being checked.", "Filings were just checked. Try again in {}.")
filing_reads = BackgroundJob("filing_read", lambda: FILING_READ_COOLDOWN_SECONDS,
                             "A filing is already being read. Its progress is shown on the Filings tab.",
                             "A filing was just read. Try again in {}.")


def _filings_view(ticker: str | None) -> dict:
    with _db() as conn:
        every = filings.list_filings(conn)
        return {"filings": [f for f in every if not ticker or f["ticker"] == ticker.upper()],
                "tickers": sorted({f["ticker"] for f in every}),
                "expected": filings.expected(conn, upcoming.today_et()), "not_covered": filings.not_covered(conn),
                "checked": filings.last_check(conn), "check": filing_checks.snapshot(), "read": filing_reads.snapshot(),
                "max_cost_usd": filings.READ_BUDGET_USD, "automatic_days": filings.AUTOMATIC_WITHIN_DAYS,
                "contact_set": edgar.contact_set()}


async def filings_view(request):
    ticker = request.query_params.get("ticker") or None
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_filings_view, ticker))


async def check_filings(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        job = filing_checks.start(lambda emit: filings.check("manual", emit))
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"check": job}, status_code=202)


async def read_filing(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"accession": "0000789019-26-000123"}')
    accession = body.get("accession") if isinstance(body, dict) else None
    if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
        return _error(400, 'send JSON like {"accession": "0000789019-26-000123"}')
    with _db() as conn:  # a quick check first, so a wrong number is refused straight away
        known = filings.get_filing(conn, accession)
    if not known:
        return _error(404, f"No filing {accession} is listed. Check for new filings first.")
    try:
        job = filing_reads.start(lambda emit: filings.read(accession, "manual", emit),
                                 target={"accession": accession, "ticker": known["ticker"]})
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"read": job}, status_code=202)


active_questions = 0


async def ask_question(request):
    """Streams the answer as newline-delimited JSON: delta events, then done (or error)."""
    global active_questions
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"question": "..."}')
    question = body.get("question") if isinstance(body, dict) else None
    if not isinstance(question, str) or not question.strip():
        return _error(400, "question is required")
    if len(question) > ask.MAX_QUESTION_CHARS:
        return _error(400, f"keep questions under {ask.MAX_QUESTION_CHARS} characters")
    if active_questions >= MAX_ACTIVE_QUESTIONS:
        return _error(429, "Another question is being answered. Try again in a moment.")

    queue: asyncio.Queue = asyncio.Queue()

    async def work():
        try:
            await ask.answer(question, queue.put_nowait)
        except Exception as e:
            queue.put_nowait({"type": "error", "error": str(e) or type(e).__name__})

    async def stream():
        global active_questions
        active_questions += 1
        task = asyncio.create_task(work())
        try:
            while True:
                event = await queue.get()
                yield json.dumps(event) + "\n"
                if event["type"] in ("done", "error"):
                    break
        finally:
            active_questions -= 1
            task.cancel()

    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
# Automatic run after the close
# ---------------------------------------------------------------------------

def close_run_due(now: datetime, state: dict) -> bool:
    """True when today's after-close run should be attempted now. state is the loop's memory for today."""
    hour, minute = map(int, AUTO_CLOSE_TIME.split(":"))
    if now.weekday() >= 5 or state["done"] or state["attempts"] >= AUTO_CLOSE_MAX_ATTEMPTS:
        return False  # weekends have no session; run_once skips holidays for free
    if (now.hour, now.minute) < (hour, minute):
        return False
    return state["next_try"] is None or now >= state["next_try"]


async def run_close_job() -> None:
    """The default after-close job: the same run as the "Run update now" button.
    Once the market is closed it writes the day's final report, or skips for free if it's already saved."""
    while runs.task and not runs.task.done():  # let a run that's already going finish first
        await asyncio.wait([runs.task])
    runs.start(scheduled=True)
    await asyncio.wait([runs.task])
    if runs.state["state"] == "failed":
        raise RuntimeError(runs.state["error"])


close_job = run_close_job  # the test environment swaps this for a simulated one


async def run_at_close() -> None:
    """Once a weekday after AUTO_CLOSE_TIME (Eastern), saves the final report. Retries a failed run twice."""
    state = {"day": None, "attempts": 0, "done": False, "next_try": None}
    while True:
        await asyncio.sleep(AUTO_CLOSE_CHECK_SECONDS)
        now = run_brief.now_et()
        if state["day"] != now.date():
            state = {"day": now.date(), "attempts": 0, "done": False, "next_try": None}
        if not close_run_due(now, state):
            continue
        state["attempts"] += 1
        try:
            await close_job()
            state["done"] = True
        except Exception:
            state["next_try"] = now + timedelta(seconds=AUTO_CLOSE_RETRY_SECONDS)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app):
    tasks = [asyncio.create_task(watch_reports())]
    update_index_in_background()  # catch up on anything saved while the API was off
    if AUTO_CLOSE:
        tasks.append(asyncio.create_task(run_at_close()))
    yield
    for task in tasks:
        task.cancel()


def create_app(frontend_dist: Path = FRONTEND_DIST) -> Starlette:
    routes = [
        Route("/api/health", health),
        Route("/api/reports", list_reports),
        Route("/api/reports/latest", latest_report),  # must come before the {session_date} route
        Route("/api/reports/{session_date}", get_report),
        Route("/api/tickers/{ticker}/history", ticker_history),
        Route("/api/tickers/{ticker}/prices", ticker_prices),
        Route("/api/alerts", alerts_status),
        Route("/api/calendar", calendar),
        Route("/api/calendar/scan", start_calendar_scan, methods=["POST"]),
        Route("/api/calendar/scan", current_calendar_scan, methods=["GET"]),
        Route("/api/search", search_reports),
        Route("/api/search/status", search_status),
        Route("/api/watchlist", watchlist_view, methods=["GET"]),
        Route("/api/watchlist", add_stock, methods=["POST"]),
        Route("/api/watchlist/{ticker}", star_stock, methods=["POST"]),
        Route("/api/watchlist/{ticker}/remove", remove_stock, methods=["POST"]),
        Route("/api/stocks/search", search_stocks),
        Route("/api/followups", followups_view, methods=["GET"]),
        Route("/api/followups/refresh", refresh_followups, methods=["POST"]),
        Route("/api/stories", stories_view, methods=["GET"]),
        Route("/api/stories/check", check_story, methods=["POST"]),
        Route("/api/filings", filings_view, methods=["GET"]),
        Route("/api/filings/check", check_filings, methods=["POST"]),
        Route("/api/filings/read", read_filing, methods=["POST"]),
        Route("/api/events", events),
        Route("/api/runs", start_run, methods=["POST"]),
        Route("/api/runs/current", current_run),
        Route("/api/ask", ask_question, methods=["POST"]),
    ]
    if frontend_dist.is_dir():  # serve the built frontend (npm run build) at /
        routes.append(Mount("/", app=StaticFiles(directory=frontend_dist, html=True), name="frontend"))
    return Starlette(
        routes=routes,
        middleware=[Middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS,
                               allow_methods=["GET", "POST"], allow_headers=["Content-Type"])],
        lifespan=lifespan,
    )


app = create_app()
