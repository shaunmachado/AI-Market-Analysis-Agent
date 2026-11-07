"""Offline tests for sector and market context: storage, upgrading older databases,
the API, Ask and the agent's setup. (The calculations are tested in test_market_tools.py.)

Run from the project folder:
    pytest -v tests/test_sector_context.py
"""

import asyncio
import sqlite3
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from mcp import Client  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

CLOSED = {"status": "complete", "as_of": "2026-11-06"}
CONTEXT = {
    "benchmark": "XLK", "sector": "Technology", "benchmark_return_pct": -2.1, "market_return_pct": -1.2,
    "vs_benchmark_pct": -1.9, "vs_benchmark_zscore": -2.4, "benchmark_vs_market_zscore": -0.8,
    "market_zscore": -1.5, "read": "stock-specific",
    "summary": "NVDA fell 4.00%; its sector (Technology, XLK) fell 2.10% and the S&P 500 fell 1.20%. ...",
}


def scan(flagged_context=CONTEXT):
    return {
        "session": CLOSED,
        "flagged": [{"ticker": "NVDA", "last_close": 150.0, "return_1d_pct": -4.0, "return_5d_pct": -5.0,
                     "return_zscore": -3.1, "volume_vs_avg": 2.5, "compared_to": "test",
                     "context": flagged_context}],
        "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.3}],
        "errors": [],
    }


def save(conn, day="2026-11-06", status="final", flagged_context=CONTEXT):
    return reports_db.save_report(conn, session_date=day, status=status, title="Watchlist brief", body_md="brief",
                                  as_of=day if status == "final" else f"{day} 12:30 ET",
                                  scan=scan(flagged_context))


@pytest.fixture
def db(tmp_path, monkeypatch):
    path = tmp_path / "reports.db"
    monkeypatch.setattr(reports_db, "DB_PATH", path)
    return path


def test_context_is_saved_with_each_flagged_ticker(db):
    with closing(reports_db.connect()) as conn:
        save(conn)
        tickers = {t["ticker"]: t for t in reports_db.get_report(conn, "2026-11-06")["tickers"]}

    nvda, aapl = tickers["NVDA"], tickers["AAPL"]
    assert nvda["benchmark"] == "XLK"
    assert nvda["benchmark_return_pct"] == -2.1 and nvda["market_return_pct"] == -1.2
    assert nvda["vs_benchmark_pct"] == -1.9 and nvda["vs_benchmark_zscore"] == -2.4
    assert nvda["move_read"] == "stock-specific"
    assert nvda["context_summary"].startswith("NVDA fell 4.00%")
    assert aapl["benchmark"] is None and aapl["move_read"] is None  # quiet tickers aren't compared


def test_unavailable_context_is_stored_as_empty(db):
    with closing(reports_db.connect()) as conn:
        save(conn, flagged_context={"error": "no comparison data for XLK"})
        nvda = reports_db.get_report(conn, "2026-11-06")["tickers"][0]

    assert nvda["ticker"] == "NVDA" and nvda["return_1d_pct"] == -4.0
    assert nvda["benchmark"] is None and nvda["context_summary"] is None


OLD_SCHEMA = """
CREATE TABLE reports (session_date TEXT PRIMARY KEY, status TEXT NOT NULL, title TEXT NOT NULL,
    body_md TEXT NOT NULL, as_of TEXT NOT NULL, revision INTEGER NOT NULL DEFAULT 1,
    total_cost_usd REAL NOT NULL DEFAULT 0, created_at TEXT NOT NULL, updated_at TEXT NOT NULL, finalized_at TEXT);
CREATE TABLE report_tickers (session_date TEXT NOT NULL, ticker TEXT NOT NULL, category TEXT NOT NULL,
    price REAL, return_1d_pct REAL, return_5d_pct REAL, return_zscore REAL, volume_vs_avg REAL,
    compared_to TEXT, error TEXT, PRIMARY KEY (session_date, ticker));
CREATE TABLE report_sources (id INTEGER PRIMARY KEY, session_date TEXT NOT NULL, ticker TEXT NOT NULL,
    title TEXT, publisher TEXT, url TEXT, published TEXT);
CREATE TRIGGER final_reports_no_update BEFORE UPDATE ON reports
WHEN OLD.status = 'final' BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;
INSERT INTO reports VALUES ('2026-10-01', 'final', 'Old brief', 'old body', '2026-10-01', 1, 0.05,
    '2026-10-01T20:30:00Z', '2026-10-01T20:30:00Z', '2026-10-01T20:30:00Z');
INSERT INTO report_tickers VALUES ('2026-10-01', 'NVDA', 'flagged', 120.0, 5.0, 6.0, 3.3, 2.1, 'old', NULL);
"""


def test_database_from_an_earlier_version_still_reads_and_is_upgraded(db):
    old = sqlite3.connect(db)
    old.executescript(OLD_SCHEMA)
    old.close()

    # Read-only (the API) works before any upgrade: the new fields are just empty
    with closing(reports_db.connect(readonly=True)) as conn:
        before = reports_db.get_report(conn, "2026-10-01")["tickers"][0]
        assert before["return_1d_pct"] == 5.0 and before["benchmark"] is None

    # The next run's connection adds the columns, without touching the old final report
    with closing(reports_db.connect()) as conn:
        columns = {row[1] for row in conn.execute("PRAGMA table_info(report_tickers)")}
        assert set(reports_db.ADDED_TICKER_COLUMNS) <= columns
        assert save(conn) == reports_db.FINALIZED
        old_report = reports_db.get_report(conn, "2026-10-01")
        new_report = reports_db.get_report(conn, "2026-11-06")
        with pytest.raises(sqlite3.DatabaseError, match="permanent"):
            conn.execute("UPDATE reports SET title = 'changed' WHERE session_date = '2026-10-01'")

    assert old_report["body_md"] == "old body" and old_report["tickers"][0]["price"] == 120.0
    assert new_report["tickers"][0]["move_read"] == "stock-specific"
    reports_db.connect().close()  # upgrading again is harmless


def test_api_returns_context_in_reports_and_history(db):
    with closing(reports_db.connect()) as conn:
        save(conn)
    with TestClient(api.app) as client:
        latest = client.get("/api/reports/latest").json()
        history = client.get("/api/tickers/NVDA/history").json()["history"]

    assert latest["tickers"][0]["vs_benchmark_pct"] == -1.9
    assert latest["tickers"][0]["move_read"] == "stock-specific"
    assert history[0]["benchmark"] == "XLK" and history[0]["status"] == "final"


def test_ask_sees_the_kind_of_move(db):
    with closing(reports_db.connect()) as conn:
        save(conn)
    with closing(reports_db.connect(readonly=True)) as conn:
        context, _ = ask.build_context(conn, "Why did NVDA fall?")

    assert "| vs sector (points) | kind of move" in context
    assert "2026-11-06 | final | flagged | -4.0 | -3.1 | 2.5 | -1.9 vs XLK | stock-specific" in context


def test_agent_can_use_every_market_tool():
    """A tool added to market_tools.py must also be allowed in run_brief.py and named in the prompt."""
    async def names():
        async with Client(market_tools.mcp) as client:
            return {t.name for t in (await client.list_tools()).tools}

    tools = asyncio.run(names())
    prompt = (Path(run_brief.__file__).parent / "analyst_prompt.md").read_text()

    assert "market_backdrop" in tools
    assert {f"mcp__market__{t}" for t in tools} == set(run_brief.options.allowed_tools)
    for tool in tools:
        assert f"`{tool}`" in prompt
    assert "context.read" in prompt and "Vs. sector and market" in prompt
