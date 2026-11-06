"""Offline tests for the reports database, the API and how run_brief.py saves reports.

Run from the project folder:
    pytest -v tests/test_reports_db.py
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage,
)
from starlette.testclient import TestClient  # noqa: E402

OPEN = {"status": "in_progress", "as_of": "2026-11-06 12:30 ET"}
CLOSED = {"status": "complete", "as_of": "2026-11-06"}


def scan(session, flagged=("NVDA",), quiet=("AAPL",), errors=()):
    """A flag_events result shaped like the real one."""
    price_key = "last_price" if session["status"] == "in_progress" else "last_close"
    return {
        "session": session,
        "flagged": [{"ticker": t, price_key: 150.0, "return_1d_pct": 6.5, "return_5d_pct": 9.1,
                     "return_zscore": 4.2, "volume_vs_avg": 2.8, "compared_to": "test baseline"}
                    for t in flagged],
        "quiet": [{"ticker": t, "return_1d_pct": 0.3} for t in quiet],
        "errors": [{"ticker": t, "error": "not enough price history"} for t in errors],
    }


def save(conn, session_date="2026-11-06", status="intraday", as_of="2026-11-06 12:30 ET",
         body="# Intraday update\n\nbody", **kwargs):
    kwargs.setdefault("scan", scan(OPEN if status == "intraday" else CLOSED))
    return reports_db.save_report(conn, session_date=session_date, status=status, title=body.splitlines()[0][2:],
                                  body_md=body, as_of=as_of, **kwargs)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    connection = reports_db.connect()
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Storage rules
# ---------------------------------------------------------------------------

def test_database_and_tables_are_created_on_first_use(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"reports", "report_tickers", "report_sources"} <= tables
    reports_db.connect().close()  # opening again is safe


def test_intraday_report_is_updated_in_place_during_the_day(conn):
    assert save(conn, as_of="2026-11-06 10:30 ET", body="# Intraday update\n\nmorning",
                scan=scan(OPEN, flagged=("NVDA",))) == reports_db.CREATED
    first = reports_db.get_report(conn, "2026-11-06")

    assert save(conn, as_of="2026-11-06 12:30 ET", body="# Intraday update\n\nmidday",
                scan=scan(OPEN, flagged=("TSLA",)), cost_usd=0.05) == reports_db.UPDATED
    report = reports_db.get_report(conn, "2026-11-06")

    assert report["status"] == "intraday"
    assert report["body_md"].endswith("midday")
    assert report["revision"] == 2
    assert report["created_at"] == first["created_at"]
    assert [t["ticker"] for t in report["tickers"] if t["category"] == "flagged"] == ["TSLA"]  # replaced
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1  # still one report for the day


def test_older_intraday_update_never_overwrites_a_newer_one(conn):
    save(conn, as_of="2026-11-06 13:30 ET", body="# Intraday update\n\nnewer")
    assert save(conn, as_of="2026-11-06 12:30 ET", body="# Intraday update\n\nolder") == reports_db.SKIPPED_STALE
    assert reports_db.get_report(conn, "2026-11-06")["body_md"].endswith("newer")


def test_final_report_replaces_the_days_intraday_report(conn):
    save(conn, status="intraday", sources=[{"ticker": "NVDA", "title": "old news", "url": "https://a"}])

    outcome = save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief: 2026-11-06\n\nfinal",
                   scan=scan(CLOSED, flagged=("AMD",)),
                   sources=[{"ticker": "AMD", "title": "new news", "url": "https://b"}])
    report = reports_db.get_report(conn, "2026-11-06")

    assert outcome == reports_db.FINALIZED
    assert report["status"] == "final" and report["finalized_at"]
    assert report["body_md"].endswith("final")
    assert [t["ticker"] for t in report["tickers"] if t["category"] == "flagged"] == ["AMD"]
    assert [s["title"] for s in report["sources"]] == ["new news"]


def test_final_report_is_permanent(conn):
    save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief\n\noriginal")

    assert save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief\n\nrewrite") == reports_db.SKIPPED_FINAL
    assert save(conn, status="intraday", body="# Intraday update\n\nlate") == reports_db.SKIPPED_FINAL
    report = reports_db.get_report(conn, "2026-11-06")
    assert report["body_md"].endswith("original")
    assert report["revision"] == 1


@pytest.mark.parametrize("sql", [
    "UPDATE reports SET body_md = 'hacked'",
    "DELETE FROM reports",
    "UPDATE report_tickers SET price = 0",
    "DELETE FROM report_tickers",
    "INSERT INTO report_tickers (session_date, ticker, category) VALUES ('2026-11-06', 'ZZZ', 'quiet')",
    "DELETE FROM report_sources",
    "INSERT INTO report_sources (session_date, ticker) VALUES ('2026-11-06', 'ZZZ')",
])
def test_database_itself_blocks_changes_to_final_reports(conn, sql):
    save(conn, status="final", as_of="2026-11-06", sources=[{"ticker": "NVDA", "title": "news"}])
    with pytest.raises(sqlite3.IntegrityError, match="final reports are permanent"):
        conn.execute(sql)


def test_a_new_day_never_touches_past_reports(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", body="# Watchlist brief\n\nthursday")
    before = reports_db.get_report(conn, "2026-11-05")

    save(conn, session_date="2026-11-06", status="intraday", body="# Intraday update\n\nfriday")
    save(conn, session_date="2026-11-06", status="final", as_of="2026-11-06", body="# Watchlist brief\n\nfriday")

    assert reports_db.get_report(conn, "2026-11-05") == before


def test_list_reports_newest_first_with_filters(conn):
    for day in ("2026-11-03", "2026-11-04", "2026-11-05"):
        save(conn, session_date=day, status="final", as_of=day)
    save(conn, session_date="2026-11-06", status="intraday")

    assert [r["session_date"] for r in reports_db.list_reports(conn)] == [
        "2026-11-06", "2026-11-05", "2026-11-04", "2026-11-03"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, limit=2)] == ["2026-11-06", "2026-11-05"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, before="2026-11-05")] == ["2026-11-04", "2026-11-03"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, status="intraday")] == ["2026-11-06"]
    assert reports_db.list_reports(conn)[0]["flagged_count"] == 1


def test_ticker_history_across_days(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", scan=scan(CLOSED, flagged=("NVDA",)))
    save(conn, session_date="2026-11-06", status="intraday", scan=scan(OPEN, flagged=(), quiet=("NVDA",)))

    history = reports_db.ticker_history(conn, "nvda")

    assert [(h["session_date"], h["status"], h["category"]) for h in history] == [
        ("2026-11-06", "intraday", "quiet"), ("2026-11-05", "final", "flagged")]
    assert history[1]["price"] == 150.0  # last_close for a final report


# ---------------------------------------------------------------------------
# API for the frontend
# ---------------------------------------------------------------------------

@pytest.fixture
def client(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", body="# Watchlist brief: 2026-11-05\n\nx",
         sources=[{"ticker": "NVDA", "title": "Beats estimates", "publisher": "Reuters", "url": "https://a"}])
    save(conn, session_date="2026-11-06", status="intraday", body="# Intraday update: 2026-11-06 12:30 ET\n\ny")
    return TestClient(api.app)


def test_api_lists_reports(client):
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert [(r["session_date"], r["status"]) for r in response.json()["reports"]] == [
        ("2026-11-06", "intraday"), ("2026-11-05", "final")]
    assert client.get("/api/reports?status=final&limit=1").json()["reports"][0]["session_date"] == "2026-11-05"


def test_api_returns_a_full_report(client):
    report = client.get("/api/reports/2026-11-05").json()
    assert report["title"] == "Watchlist brief: 2026-11-05"
    assert report["status"] == "final"
    assert {t["ticker"]: t["category"] for t in report["tickers"]} == {"NVDA": "flagged", "AAPL": "quiet"}
    assert report["sources"][0]["publisher"] == "Reuters"


def test_api_latest_and_health(client):
    assert client.get("/api/reports/latest").json()["session_date"] == "2026-11-06"
    assert client.get("/api/health").json() == {"status": "ok", "reports": 2}


def test_api_ticker_history(client):
    data = client.get("/api/tickers/nvda/history").json()
    assert data["ticker"] == "NVDA"
    assert [h["session_date"] for h in data["history"]] == ["2026-11-06", "2026-11-05"]


@pytest.mark.parametrize("path, status_code", [
    ("/api/reports/2026-12-25", 404),
    ("/api/reports/yesterday", 400),
    ("/api/reports?limit=0", 400),
    ("/api/reports?limit=abc", 400),
    ("/api/reports?before=nov-5", 400),
    ("/api/reports?status=draft", 400),
    ("/api/tickers/not%20a%20ticker/history", 400),
])
def test_api_rejects_bad_requests_clearly(client, path, status_code):
    response = client.get(path)
    assert response.status_code == status_code
    assert "error" in response.json()


def test_api_is_read_only(client):
    assert client.post("/api/reports", json={}).status_code == 405
    assert client.delete("/api/reports/2026-11-05").status_code == 405
    readonly = reports_db.connect(readonly=True)  # the kind of connection the API uses
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        readonly.execute("DELETE FROM report_sources")
    readonly.close()


def test_api_allows_the_frontend_origin(client):
    response = client.get("/api/reports", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/api/reports", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_api_works_before_any_report_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "new.db")
    client = TestClient(api.app)
    assert client.get("/api/reports").json() == {"reports": []}
    assert client.get("/api/reports/latest").status_code == 404


# ---------------------------------------------------------------------------
# run_brief.py: saving what the agent produced
# ---------------------------------------------------------------------------

def agent_messages(flag_result, news=None, brief="# Intraday update: 2026-11-06 12:30 ET\n\nbrief text"):
    """The message stream the Agent SDK yields for a typical run."""
    messages = [AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})],
                                 model="test")]
    if flag_result is not None:
        messages.append(UserMessage(content=[ToolResultBlock(
            tool_use_id="t1", content=[{"type": "text", "text": json.dumps(flag_result)}])]))
    if news:
        messages.append(AssistantMessage(content=[ToolUseBlock(
            id="t2", name="mcp__market__get_news", input={"ticker": "nvda"})], model="test"))
        messages.append(UserMessage(content=[ToolResultBlock(  # MCP sends a list as one part per item
            tool_use_id="t2", content=[{"type": "text", "text": json.dumps(item)} for item in news])]))
    messages.append(ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                  num_turns=4, session_id="s", total_cost_usd=0.04, result=brief))
    return messages


@pytest.fixture
def fake_run(conn, monkeypatch):
    """Point run_brief at fake market status and a fake agent. Returns the list of prompts sent."""
    prompts = []

    def setup(session, messages):
        monkeypatch.setattr(run_brief, "market_session", lambda: session)

        async def fake_query(*, prompt, options):
            prompts.append(prompt)
            for m in messages:
                yield m

        monkeypatch.setattr(run_brief, "query", fake_query)
        return prompts
    return setup


def test_run_saves_report_with_figures_and_sources(conn, fake_run):
    news = [{"title": "Beats estimates", "publisher": "Reuters", "published": "2026-11-06T13:00:00Z",
             "url": "https://a", "summary": "..."},
            {"title": "Guidance raised", "publisher": "AP", "published": 1762000000, "url": "https://b", "summary": ""}]
    fake_run(OPEN, agent_messages(scan(OPEN), news))

    asyncio.run(run_brief.main())
    report = reports_db.get_report(conn, "2026-11-06")

    assert report["status"] == "intraday"
    assert report["title"] == "Intraday update: 2026-11-06 12:30 ET"
    assert report["as_of"] == "2026-11-06 12:30 ET"
    assert report["total_cost_usd"] == pytest.approx(0.04)
    assert {t["ticker"] for t in report["tickers"]} == {"NVDA", "AAPL"}
    assert [(s["ticker"], s["publisher"]) for s in report["sources"]] == [("NVDA", "Reuters"), ("NVDA", "AP")]


def test_run_skips_claude_when_final_report_already_exists(conn, fake_run):
    save(conn, status="final", as_of="2026-11-06")
    prompts = fake_run(CLOSED, agent_messages(scan(CLOSED)))

    asyncio.run(run_brief.main())

    assert prompts == []  # Claude was never called, so the run cost nothing


def test_run_rescans_if_the_agent_result_cannot_be_read(conn, fake_run, monkeypatch):
    fake_run(CLOSED, agent_messages(flag_result=None, brief="# Watchlist brief: 2026-11-06\n\nx"))
    monkeypatch.setattr(run_brief, "flag_events", lambda: scan(CLOSED, flagged=("AMD",)))

    asyncio.run(run_brief.main())

    report = reports_db.get_report(conn, "2026-11-06")
    assert report["status"] == "final"
    assert "AMD" in {t["ticker"] for t in report["tickers"]}


def test_run_saves_as_final_if_the_market_closed_mid_run(conn, fake_run):
    """Started at 3:59pm, but the figures the agent got were for the finished session."""
    fake_run(OPEN, agent_messages(scan(CLOSED), brief="# Watchlist brief: 2026-11-06\n\nx"))

    asyncio.run(run_brief.main())

    assert reports_db.get_report(conn, "2026-11-06")["status"] == "final"
