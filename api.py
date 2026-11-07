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
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes is a run, through run_brief.py's normal storage rules.
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
from datetime import datetime, timedelta, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import alerts
import ask
import prices
import reports_db
import run_brief
import search_index

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "60"))  # between on-demand runs
POLL_SECONDS = float(os.environ.get("REPORT_POLL_SECONDS", "2"))          # how often to check for new reports
AUTO_CLOSE = os.environ.get("AUTO_CLOSE_RUN", "1") != "0"                 # write the final report after the close
AUTO_CLOSE_TIME = os.environ.get("AUTO_CLOSE_TIME", "16:15")              # Eastern time, 15 minutes after the bell
AUTO_CLOSE_CHECK_SECONDS = float(os.environ.get("AUTO_CLOSE_CHECK_SECONDS", "30"))
AUTO_CLOSE_RETRY_SECONDS = 15 * 60
AUTO_CLOSE_MAX_ATTEMPTS = 3
MAX_ACTIVE_QUESTIONS = 2
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"


class BadRequest(ValueError):
    pass


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def _limit(request, default: int = 30, maximum: int = 365) -> int:
    raw = request.query_params.get("limit", str(default))
    if not raw.isdigit() or not 1 <= int(raw) <= maximum:
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


def _latest_change() -> dict | None:
    """The most recently saved report: changes whenever any run saves (scheduled or on demand)."""
    with _db() as conn:
        row = conn.execute("""SELECT session_date, status, revision, updated_at FROM reports
                              ORDER BY updated_at DESC, session_date DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


async def watch_reports() -> None:
    """Checks the database every few seconds and announces new or updated reports."""
    last = await asyncio.to_thread(_latest_change)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current = await asyncio.to_thread(_latest_change)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if current and current != last:
            last = current
            hub.publish({"type": "report_saved", **current})
            update_index_in_background()  # covers scheduled runs, which are separate programs


async def events(request):
    """Server-Sent Events stream. The browser's EventSource reconnects on its own."""
    queue = hub.subscribe()
    hello = {"type": "hello", "run": runs.snapshot(), "latest": await asyncio.to_thread(_latest_change)}

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
        Route("/api/search", search_reports),
        Route("/api/search/status", search_status),
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
