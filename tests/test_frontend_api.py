"""Offline tests for the frontend's backend: live updates, run-now, and questions.

Run from the project folder:
    pytest -v tests/test_frontend_api.py
"""

import asyncio
import json
import sys
import time
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    AssistantMessage, ResultMessage, StreamEvent, ToolResultBlock, ToolUseBlock, UserMessage,
)
from starlette.testclient import TestClient  # noqa: E402

OPEN = {"status": "in_progress", "as_of": "2026-11-06 12:30 ET"}
JSON = {"Content-Type": "application/json"}


def scan(session=OPEN, flagged=("NVDA",), quiet=("AAPL",)):
    return {"session": session,
            "flagged": [{"ticker": t, "last_price": 150.0, "return_1d_pct": 6.5, "return_zscore": 4.2,
                         "volume_vs_avg": 2.8} for t in flagged],
            "quiet": [{"ticker": t, "return_1d_pct": 0.3} for t in quiet], "errors": []}


def save(day="2026-11-06", status="intraday", as_of="2026-11-06 12:30 ET", body="brief", flagged=("NVDA",)):
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=day, status=status, title=f"Report {day}",
                                      body_md=f"# Report {day}\n\n{body}", as_of=as_of, scan=scan(flagged=flagged))


def result(text="done", is_error=False, cost=0.01):
    return ResultMessage(subtype="error_during_execution" if is_error else "success", duration_ms=1,
                         duration_api_ms=1, is_error=is_error, num_turns=1, session_id="s",
                         total_cost_usd=cost, result=text)


def wait_until(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    """A temporary database, and fresh live-update and run state, for every test."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "runs", api.RunManager())
    monkeypatch.setattr(api, "AUTO_CLOSE", False)  # tests must never start a real after-close run
    reports_db.connect().close()


def fake_run_once(delay=0.0, fail=None):
    """Stands in for run_brief.run_once: reports progress, then saves a report."""
    async def run_once(emit):
        emit({"type": "started", "session_date": "2026-11-06", "status": "intraday"})
        emit({"type": "tool_call", "tool": "mcp__market__flag_events", "input": {}})
        await asyncio.sleep(delay)
        if fail:
            raise RuntimeError(fail)
        outcome = save()
        event = {"type": "saved", "outcome": outcome, "session_date": "2026-11-06", "status": "intraday",
                 "turns": 3, "cost_usd": 0.04}
        emit(event)
        return event
    return run_once


# ---------------------------------------------------------------------------
# run_brief.run_once progress events
# ---------------------------------------------------------------------------

def test_run_once_reports_progress_events(monkeypatch):
    messages = [
        AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})], model="m"),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": json.dumps(scan())}])]),
        AssistantMessage(content=[ToolUseBlock(id="t2", name="mcp__market__get_news", input={"ticker": "NVDA"})],
                         model="m"),
        result("# Intraday update: 2026-11-06 12:30 ET\n\ntext"),
    ]

    async def fake_query(*, prompt, options):
        for m in messages:
            yield m

    monkeypatch.setattr(run_brief, "market_session", lambda: OPEN)
    monkeypatch.setattr(run_brief, "query", fake_query)
    events = []

    final = asyncio.run(run_brief.run_once(events.append))

    assert [e["type"] for e in events] == ["started", "tool_call", "tool_call", "saved"]
    assert events[1]["tool"] == "mcp__market__flag_events"
    assert final == events[-1] and final["outcome"] == "created"


# ---------------------------------------------------------------------------
# Run now
# ---------------------------------------------------------------------------

def test_run_now_writes_a_report_and_shows_progress(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once())
    with TestClient(api.app) as client:
        response = client.post("/api/runs", json={})
        assert response.status_code == 202
        assert response.json()["run"]["state"] == "running"

        run = wait_until(lambda: (r := client.get("/api/runs/current").json()["run"])["state"] != "running" and r)

    assert run["state"] == "finished"
    assert [e["type"] for e in run["log"]] == ["started", "tool_call", "saved"]
    assert run["result"]["outcome"] == "created"
    assert run["started_at"] and run["finished_at"]


def test_run_now_allows_one_run_at_a_time_then_a_cooldown(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once(delay=0.5))
    with TestClient(api.app) as client:
        assert client.post("/api/runs", json={}).status_code == 202
        busy = client.post("/api/runs", json={})
        assert busy.status_code == 409 and "already being written" in busy.json()["error"]

        wait_until(lambda: client.get("/api/runs/current").json()["run"]["state"] == "finished")
        too_soon = client.post("/api/runs", json={})
        assert too_soon.status_code == 429 and "Please wait" in too_soon.json()["error"]

        monkeypatch.setattr(api, "RUN_COOLDOWN_SECONDS", 0)
        assert client.post("/api/runs", json={}).status_code == 202


def test_run_now_failure_is_reported(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once(fail="Run failed: error_max_budget_usd"))
    with TestClient(api.app) as client:
        client.post("/api/runs", json={})
        run = wait_until(lambda: (r := client.get("/api/runs/current").json()["run"])["state"] != "running" and r)

    assert run["state"] == "failed"
    assert run["error"] == "Run failed: error_max_budget_usd"


@pytest.mark.parametrize("path", ["/api/runs", "/api/ask"])
def test_other_websites_cannot_trigger_runs_or_questions(path):
    client = TestClient(api.app)
    evil = client.post(path, json={"question": "hi"}, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    form = client.post(path, content="question=hi", headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert form.status_code == 415  # plain form posts (which skip browser safety checks) are refused


def test_frontend_origin_can_post():
    client = TestClient(api.app)
    response = client.post("/api/ask", json={"question": "anything new?"}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Automatic run after the close
# ---------------------------------------------------------------------------

ET = ZoneInfo("America/New_York")
NEW_DAY = {"day": None, "attempts": 0, "done": False, "next_try": None}


@pytest.mark.parametrize("when, due", [
    (datetime(2026, 11, 6, 15, 59, tzinfo=ET), False),   # Friday, before 16:15
    (datetime(2026, 11, 6, 16, 15, tzinfo=ET), True),    # Friday, 16:15
    (datetime(2026, 11, 6, 23, 0, tzinfo=ET), True),     # Friday night: still due if it hasn't happened
    (datetime(2026, 11, 7, 17, 0, tzinfo=ET), False),    # Saturday
])
def test_close_run_is_due_on_weekdays_after_the_close(when, due):
    assert api.close_run_due(when, dict(NEW_DAY)) is due


def test_close_run_waits_between_retries_and_stops_after_success_or_three_tries():
    now = datetime(2026, 11, 6, 17, 0, tzinfo=ET)
    assert not api.close_run_due(now, {**NEW_DAY, "done": True})
    assert not api.close_run_due(now, {**NEW_DAY, "next_try": now + timedelta(minutes=5)})
    assert api.close_run_due(now, {**NEW_DAY, "attempts": 1, "next_try": now - timedelta(minutes=1)})
    assert not api.close_run_due(now, {**NEW_DAY, "attempts": api.AUTO_CLOSE_MAX_ATTEMPTS})


def test_after_close_job_runs_once_per_day_and_retries_failures(monkeypatch):
    clock = [datetime(2026, 11, 6, 16, 20, tzinfo=ET)]
    calls = []

    async def job():
        calls.append(clock[0])
        if len(calls) == 1:
            raise RuntimeError("Yahoo was down")

    monkeypatch.setattr(api, "AUTO_CLOSE_CHECK_SECONDS", 0.01)
    monkeypatch.setattr(api, "close_job", job)
    monkeypatch.setattr(api.run_brief, "now_et", lambda: clock[0])

    async def scenario():
        loop = asyncio.create_task(api.run_at_close())
        await asyncio.sleep(0.1)
        assert len(calls) == 1                       # failed, so waiting 15 minutes
        clock[0] += timedelta(minutes=16)
        await asyncio.sleep(0.1)
        assert len(calls) == 2                       # retried and succeeded
        await asyncio.sleep(0.1)
        assert len(calls) == 2                       # and doesn't run again today
        clock[0] += timedelta(days=3)                # Monday: a new day
        await asyncio.sleep(0.1)
        loop.cancel()

    asyncio.run(scenario())

    assert len(calls) == 3


def test_default_close_job_uses_the_run_now_machinery_without_the_cooldown(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once())
    api.runs.last_started = time.monotonic()  # a button press a moment ago would normally block a new run

    asyncio.run(api.run_close_job())

    assert api.runs.state["state"] == "finished" and api.runs.state["result"]["outcome"] == "created"


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------

def test_events_stream_sends_hello_then_live_events():
    async def scenario():
        response = await api.events(None)
        stream = response.body_iterator
        hello = await anext(stream)
        api.hub.publish({"type": "run_event", "event": {"type": "tool_call", "tool": "x", "input": {}}})
        live = await anext(stream)
        await stream.aclose()
        return hello, live

    hello, live = asyncio.run(scenario())

    assert hello.startswith("retry: 3000\ndata: ")
    assert json.loads(hello.split("data: ", 1)[1])["type"] == "hello"
    assert json.loads(live.removeprefix("data: "))["event"]["tool"] == "x"
    assert api.hub.subscribers == set()  # a closed browser tab is cleaned up


def test_watcher_announces_reports_saved_by_any_run(monkeypatch):
    """Covers scheduled runs too: they're separate programs, so the API spots their saves in the database."""
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.1)
        save(as_of="2026-11-06 11:00 ET")
        first = await asyncio.wait_for(queue.get(), 2)
        save(as_of="2026-11-06 12:30 ET")
        second = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return first, second

    first, second = asyncio.run(scenario())

    assert first == {"type": "report_saved", "session_date": "2026-11-06", "status": "intraday",
                     "revision": 1, "updated_at": first["updated_at"]}
    assert second["revision"] == 2


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

def fake_claude(monkeypatch, *messages):
    """Replace Claude in ask.py. Returns the list of prompts it was sent."""
    prompts = []

    async def fake_query(*, prompt, options):
        prompts.append(prompt)
        for m in messages:
            yield m

    monkeypatch.setattr(ask, "query", fake_query)
    return prompts


def delta(text):
    return StreamEvent(uuid="u", session_id="s",
                       event={"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}})


def ask_lines(question):
    response = TestClient(api.app).post("/api/ask", json={"question": question})
    assert response.status_code == 200
    return [json.loads(line) for line in response.text.splitlines()]


def test_ask_streams_the_answer(monkeypatch):
    save(day="2026-11-05", status="final", as_of="2026-11-05", body="NVDA jumped on earnings.")
    prompts = fake_claude(monkeypatch, delta("NVDA was flagged "), delta("on earnings (2026-11-05)."),
                          result("NVDA was flagged on earnings (2026-11-05).", cost=0.012))

    lines = ask_lines("why was nvda flagged?")

    assert [line["type"] for line in lines] == ["delta", "delta", "done"]
    assert "".join(line["text"] for line in lines[:2]) == lines[-1]["answer"]
    assert lines[-1]["reports_used"] == ["2026-11-05"]
    assert lines[-1]["cost_usd"] == 0.012
    assert "## Figures for NVDA" in prompts[0]  # ticker spotted, whatever the letter case
    assert "NVDA jumped on earnings." in prompts[0]


def test_ask_includes_older_reports_for_the_ticker_asked_about():
    save(day="2026-10-01", status="final", as_of="2026-10-01", flagged=("TSLA",))  # old, outside the recent 10
    for day in range(10, 22):
        save(day=f"2026-10-{day}", status="final", as_of=f"2026-10-{day}", flagged=("NVDA",))

    with closing(reports_db.connect()) as conn:
        _, used_general = ask.build_context(conn, "what happened this week?")
        _, used_tsla = ask.build_context(conn, "What about TSLA?")

    assert len(used_general) == 10 and "2026-10-01" not in used_general
    assert "2026-10-01" in used_tsla


def test_ask_context_stays_within_its_size_limit(monkeypatch):
    for day in range(10, 20):
        save(day=f"2026-10-{day}", status="final", as_of=f"2026-10-{day}", body="x" * 5000)
    monkeypatch.setattr(ask, "MAX_CONTEXT_CHARS", 12_000)

    with closing(reports_db.connect()) as conn:
        context, used = ask.build_context(conn, "summary?")

    assert len(context) <= 12_000
    assert used == ["2026-10-19", "2026-10-18"]  # newest first, until the limit


def test_ask_with_no_reports_does_not_call_claude(monkeypatch):
    prompts = fake_claude(monkeypatch, result("should not happen"))

    lines = ask_lines("anything?")

    assert lines[-1]["type"] == "done" and "no saved reports" in lines[-1]["answer"]
    assert prompts == []


def test_ask_failure_is_streamed_as_an_error(monkeypatch):
    save()
    fake_claude(monkeypatch, result(is_error=True))

    lines = ask_lines("anything?")

    assert lines == [{"type": "error", "error": "Claude couldn't answer: error_during_execution"}]


@pytest.mark.parametrize("body", [{"question": ""}, {"question": "x" * 501}, {"wrong": "key"}, ["not", "an", "object"]])
def test_ask_rejects_bad_questions(body):
    assert TestClient(api.app).post("/api/ask", json=body).status_code == 400


def test_ask_rejects_broken_json():
    assert TestClient(api.app).post("/api/ask", content="{not json", headers=JSON).status_code == 400


# ---------------------------------------------------------------------------
# Serving the built frontend
# ---------------------------------------------------------------------------

def test_built_frontend_is_served_alongside_the_api(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id='root'></div>")

    client = TestClient(api.create_app(frontend_dist=dist))

    assert "id='root'" in client.get("/").text
    assert client.get("/api/health").json()["status"] == "ok"
