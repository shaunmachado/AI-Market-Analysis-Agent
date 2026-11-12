"""Regression tests: one group per bug found while testing (see test-case-reporting.md).

Each test failed before its fix and passes after it, so the bug can't come back unnoticed.
The bug ID (BUG-01, BUG-02...) matches the bug log in the report, so you can run one group:
    pytest -v tests/test_regressions.py -k bug03

OPEN-01 is a known issue that hasn't been fixed yet. Its test is marked xfail (expected to fail).
Once the issue is fixed it passes, pytest reports that as a failure (strict), and you remove the mark.
"""

import ast
import os
import subprocess
import sys
import threading
from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import events  # noqa: E402
import filings  # noqa: E402
import market_tools  # noqa: E402
import prices  # noqa: E402
import reports_db  # noqa: E402
import search_index  # noqa: E402
import watchlist  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import test_market_tools as fakes  # noqa: E402  (its fake Yahoo Finance: prices shaped like the real thing)

PROJECT = Path(__file__).resolve().parent.parent


@pytest.fixture(autouse=True)
def temp_files(tmp_path, monkeypatch):
    """A temporary database and watchlist for every test, so nothing real is touched."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", tmp_path / "watchlist.txt")
    prices._cache.clear()
    return tmp_path


# ---------------------------------------------------------------------------
# BUG-01: watchlist.txt was read in Windows' default encoding (cp1252) but written as UTF-8.
# One edit in the app turned a comment's em dash into bytes cp1252 can't read, and from then on
# every read of the watchlist crashed (the agent, alerts, calendar and Stocks tab).
# ---------------------------------------------------------------------------

def test_bug01_app_edits_keep_non_ascii_comments_intact(temp_files):
    wl = temp_files / "watchlist.txt"
    lines = ["# my stocks: “main” ones are starred", "*AAPL", "*NVDA  SMH  # semis — chips, café", "MSFT", "JPM"]
    wl.write_bytes(("\n".join(lines) + "\n").encode("utf-8"))

    watchlist.set_main("MSFT", True)   # three edits, as the Stocks tab makes them
    watchlist.set_main("MSFT", False)
    watchlist.remove("JPM")

    assert wl.read_bytes().decode("utf-8").splitlines() == lines[:4]  # every comment exactly as it was
    assert market_tools.load_watchlist() == ["AAPL", "NVDA", "MSFT"]
    assert market_tools.load_benchmarks() == {"NVDA": "SMH"}


@pytest.mark.parametrize("raw, tickers", [
    pytest.param("AAPL  # “my” pick\nMSFT\n".encode("utf-8"), ["AAPL", "MSFT"], id="smart-quotes"),
    pytest.param(b"\xef\xbb\xbfAAPL\nMSFT\n", ["AAPL", "MSFT"], id="utf8-byte-order-mark"),
    pytest.param("AAPL  # café\r\nMSFT\r\n".encode("cp1252"), ["AAPL", "MSFT"], id="older-windows-encoding"),
])
def test_bug01_hand_edited_watchlists_are_read_in_any_common_encoding(temp_files, raw, tickers):
    (temp_files / "watchlist.txt").write_bytes(raw)
    assert market_tools.load_watchlist() == tickers
    assert [e["ticker"] for e in watchlist.entries()] == tickers
    assert events.watchlist_tickers() == tickers


def _text_io_without_encoding(path: Path) -> list[str]:
    """Calls in a file that read or write text without naming an encoding."""
    found = []
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if not isinstance(node, ast.Call) or any(k.arg == "encoding" for k in node.keywords):
            continue
        func = node.func
        name = func.attr if isinstance(func, ast.Attribute) else func.id if isinstance(func, ast.Name) else ""
        if name in ("read_text", "write_text"):
            found.append(f"{path.name}:{node.lineno} {name}()")
        elif name in ("open", "fdopen"):
            mode = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "mode"), None)
            if not (isinstance(mode, ast.Constant) and "b" in str(mode.value)):
                found.append(f"{path.name}:{node.lineno} {name}()")
    return found


def test_bug01_the_app_always_names_an_encoding_for_text_files():
    """Guards the whole class of bug: without an encoding, Python uses the computer's default,
    which differs between Windows and Mac/Linux."""
    offenders = [hit for path in sorted(PROJECT.glob("*.py")) for hit in _text_io_without_encoding(path)]
    assert offenders == []


# ---------------------------------------------------------------------------
# BUG-02: opening a brand-new database from two threads at once failed with
# "database is locked" (or "no such table"). It made test_api_shows_alert_status flaky
# (about 1 run in 15), and could break the API's first start: its startup search-index
# update and the first page load both create reports.db and search.db.
# ---------------------------------------------------------------------------

def _open_together(folder: Path, name: str, open_one, rounds: int = 15, threads: int = 8) -> list[str]:
    """Open a brand-new database file from several threads at the same moment, `rounds` times over.
    open_one(path, i) opens it as thread i would. Returns the problems seen."""
    problems = []
    for n in range(rounds):
        path = folder / f"{n}-{name}"
        barrier = threading.Barrier(threads)

        def worker(i):
            barrier.wait()  # every thread starts together
            try:
                open_one(path, i)
            except Exception as e:
                problems.append(f"{type(e).__name__}: {e}")

        workers = [threading.Thread(target=worker, args=(i,)) for i in range(threads)]
        for w in workers:
            w.start()
        for w in workers:
            w.join()
    return problems


def test_bug02_a_new_reports_database_can_be_opened_by_many_threads_at_once(temp_files):
    def open_one(path, i):
        conn = reports_db.connect(path, readonly=i % 2 == 1)  # half like the API, half like a run
        try:
            assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 0
        finally:
            conn.close()

    assert _open_together(temp_files, "reports.db", open_one) == []


def test_bug02_a_new_search_index_can_be_opened_by_many_threads_at_once(temp_files):
    assert _open_together(temp_files, "search.db", lambda path, i: search_index.connect(path).close()) == []


# ---------------------------------------------------------------------------
# BUG-03: a row with no closing price in Yahoo's data (NaN) was used as if it were real.
# Market closed: the stock showed last_close NaN, and the previous day's return labelled as
# the latest session's. Market open: one empty 5-minute bar made every figure NaN.
# A row with no price now counts the same as a missing row.
# ---------------------------------------------------------------------------

CLOSED = {"status": "complete", "as_of": "2026-11-06"}


@pytest.fixture
def fake_yahoo(monkeypatch):
    for store in (fakes.FAKE_DAILY, fakes.FAKE_INTRADAY, fakes.FAKE_NEWS, fakes.FAKE_INFO):
        store.clear()
    monkeypatch.setattr(market_tools.yf, "Ticker", fakes.FakeTicker)
    market_tools._sectors.clear()


def _daily(close_override: dict[int, float] | None = None, drop: tuple = ()) -> pd.DataFrame:
    index = pd.bdate_range(end=fakes.FRIDAY, periods=fakes.DAYS, tz=fakes.ET)
    close = 100 * np.cumprod(1 + fakes.calm_returns(7))
    for position, value in (close_override or {}).items():
        close[position] = value
    frame = pd.DataFrame({"Close": close, "Volume": fakes.normal_volume()}, index=index)
    return frame.drop(frame.index[list(drop)])


@pytest.mark.parametrize("position", [pytest.param(-1, id="latest-row"), pytest.param(-10, id="older-row")])
def test_bug03_a_daily_row_without_a_price_counts_as_missing(fake_yahoo, position):
    fakes.FAKE_DAILY["GAP"] = _daily({position: np.nan})
    fakes.FAKE_DAILY["SKIP"] = _daily(drop=(position,))

    with_gap = market_tools._moves("GAP", CLOSED)
    without_row = market_tools._moves("SKIP", CLOSED)

    assert {**with_gap, "ticker": "SKIP"} == without_row
    assert all(not (isinstance(v, float) and np.isnan(v)) for v in with_gap.values())


def test_bug03_an_empty_5_minute_bar_is_skipped_while_the_market_is_open(fake_yahoo, monkeypatch):
    fakes.fake_open_market("NVDA", today_move=0.012)
    bars = fakes.FAKE_INTRADAY["NVDA"]
    expected_bars = bars.iloc[:-1].copy()
    bars.iloc[-1, bars.columns.get_loc("Close")] = np.nan  # Yahoo's newest bar has no price yet
    session = {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"}

    gap = market_tools._moves("NVDA", session)
    fakes.FAKE_INTRADAY["NVDA"] = expected_bars
    expected = market_tools._moves("NVDA", session)

    assert gap == expected
    assert gap["as_of"] == "2026-11-06 11:25 ET"  # the latest bar that has a price
    assert not np.isnan(gap["return_1d_pct"]) and not np.isnan(gap["return_zscore"])


# ---------------------------------------------------------------------------
# BUG-04: limit=² (or another character Python calls a digit but can't turn into a number)
# crashed four API endpoints with a 500 error instead of a clear 400.
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path", [
    "/api/reports?limit=%C2%B2", "/api/alerts?limit=%C2%B2", "/api/search?q=nvda&limit=%C2%B2",
    "/api/tickers/NVDA/history?limit=%C2%B9", "/api/followups?horizon=%C2%B9",
    "/api/reports?limit=%D9%A3",  # Arabic-Indic 3: a digit, but not one people type in a URL
])
def test_bug04_unusual_digits_in_numbers_are_a_clear_400(path):
    response = TestClient(api.app, raise_server_exceptions=False).get(path)
    assert response.status_code == 400
    assert "error" in response.json()


# ---------------------------------------------------------------------------
# BUG-05: in Claude's calendar reply, a JSON true was read as the number 1, so
# "sources": [true] cited the first article and "same_as": true attached news to event 1.
# (stories.py already guarded against this; events.py didn't.)
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 6)
ARTICLES = [{"ticker": "AAPL", "title": "first", "url": "https://example.com/1"},
            {"ticker": "AAPL", "title": "second", "url": "https://example.com/2"}]
KNOWN = {1: {"id": 1, "ticker": "AAPL", "kind": "earnings", "event_date": "2026-11-20", "title": "Earnings report"}}


def _validate(raw):
    return events.validate([raw], ARTICLES, {"AAPL": "Apple"}, KNOWN, TODAY, TODAY + timedelta(days=60))


def test_bug05_true_is_not_a_citation():
    accepted, dropped = _validate({"ticker": "AAPL", "title": "Launch event", "date": "2026-11-15", "sources": [True]})
    assert accepted == [] and dropped == ["AAPL 'Launch event': no valid article cited"]


def test_bug05_true_is_not_an_event_id():
    accepted, _ = _validate({"ticker": "AAPL", "title": "Launch event", "date": "2026-11-15", "sources": [2], "same_as": True})
    assert accepted[0]["same_as"] is None
    assert accepted[0]["event_date"] == "2026-11-15"  # its own date, not event 1's


# ---------------------------------------------------------------------------
# BUG-06: a zero close in Yahoo's prices (bad data) failed the whole chart with a 502.
# ---------------------------------------------------------------------------

def test_bug06_a_zero_price_doesnt_break_the_chart(monkeypatch):
    monkeypatch.setattr(prices, "fetch_prices", lambda ticker, period: [
        {"date": "2026-11-04", "close": 0.0, "volume": 10},
        {"date": "2026-11-05", "close": 1.5, "volume": 10},
        {"date": "2026-11-06", "close": 3.0, "volume": 10}])
    response = TestClient(api.app).get("/api/tickers/PENNY/prices")
    assert response.status_code == 200
    assert [p["change_pct"] for p in response.json()["prices"]] == [None, None, 100.0]


# ---------------------------------------------------------------------------
# BUG-07: with a ticker on the list twice (added by hand), "Remove" in the app removed one
# line and said it was done, but the stock was still tracked.
# ---------------------------------------------------------------------------

def test_bug07_removing_a_stock_listed_twice_removes_it(temp_files):
    wl = temp_files / "watchlist.txt"
    wl.write_text("*AAPL\nMSFT  # mine\n*AAPL  # added again by hand\n", encoding="utf-8")
    watchlist.remove("AAPL")
    assert market_tools.load_watchlist() == ["MSFT"]
    assert wl.read_text(encoding="utf-8") == "MSFT  # mine\n"


# ---------------------------------------------------------------------------
# BUG-08: the end-of-day Discord summary crashed if a flagged stock had no return figure
# (stored empty). The flag alert already handled it; the summary didn't, and the failed
# summary was retried, and failed, on every later run.
# ---------------------------------------------------------------------------

def test_bug08_summary_handles_a_flagged_stock_without_figures():
    report = {"session_date": "2026-11-06", "title": "Watchlist brief", "body_md": "# Watchlist brief",
              "status": "final", "as_of": "2026-11-06",
              "tickers": [{"ticker": "NVDA", "category": "flagged", "return_1d_pct": 6.5, "return_zscore": 4.2,
                           "move_read": "stock-specific"},
                          {"ticker": "AAPL", "category": "flagged", "return_1d_pct": None, "return_zscore": None,
                           "move_read": None}]}
    description = alerts.summary_payload(report)["embeds"][0]["description"]
    assert "**NVDA** +6.50% (z-score 4.2) · stock-specific" in description  # unchanged for normal figures
    assert "**AAPL**" in description


# ---------------------------------------------------------------------------
# BUG-09 (a bug in a test): the live data check in test_market_tools.py could never reach Yahoo.
# Its fixture swaps the fake in on the yfinance module itself, so "undoing" it with
# yfinance.Ticker put the fake straight back, and the check failed with KeyError: 'AAPL'.
# It's skipped unless LIVE_TESTS=1, so nobody saw it. This check runs offline, every time.
# ---------------------------------------------------------------------------

def test_bug09_the_live_check_keeps_the_real_yahoo_finance(fake_yahoo):
    assert market_tools.yf.Ticker is fakes.FakeTicker   # what every other test sees...
    assert fakes.REAL_TICKER is not fakes.FakeTicker    # ...while the live check still has the real one
    assert fakes.REAL_TICKER.__module__.startswith("yfinance")


# ---------------------------------------------------------------------------
# BUG-10: on Windows, an edit on the Stocks tab failed ("Access is denied", a 500) if anything had
# watchlist.txt open at that instant: a run or the API reading it, or a virus scanner. Windows
# can't replace a file that's open. Found when the live demo's build edited the list during runs.
# ---------------------------------------------------------------------------

def test_bug10_an_edit_waits_for_the_file_to_be_free(temp_files, monkeypatch):
    (temp_files / "watchlist.txt").write_text("AAPL\nMSFT\n", encoding="utf-8")
    real_replace, refused = os.replace, []

    def busy_twice(src, dst):  # what Windows does while another handle has the file open
        if len(refused) < 2:
            refused.append(dst)
            raise PermissionError(13, "Access is denied")
        real_replace(src, dst)

    monkeypatch.setattr(watchlist, "REPLACE_WAIT_SECONDS", 0)
    monkeypatch.setattr(watchlist.os, "replace", busy_twice)
    watchlist.remove("MSFT")

    assert len(refused) == 2 and market_tools.load_watchlist() == ["AAPL"]


@pytest.mark.skipif(os.name != "nt", reason="only Windows refuses to replace an open file")
def test_bug10_a_reader_holding_the_file_on_windows(temp_files):
    wl = temp_files / "watchlist.txt"
    wl.write_text("AAPL\nMSFT\n", encoding="utf-8")
    reader = open(wl, "rb")  # held open the way Python opens files, as a run reading the list does
    threading.Timer(0.3, reader.close).start()

    watchlist.remove("MSFT")  # refused while it's open, done as soon as it's closed

    assert reader.closed and market_tools.load_watchlist() == ["AAPL"]


def test_bug10_a_file_that_stays_locked_still_fails_cleanly(temp_files, monkeypatch):
    (temp_files / "watchlist.txt").write_text("AAPL\nMSFT\n", encoding="utf-8")

    def always_busy(src, dst):
        raise PermissionError(13, "Access is denied")

    monkeypatch.setattr(watchlist, "REPLACE_WAIT_SECONDS", 0)
    monkeypatch.setattr(watchlist.os, "replace", always_busy)
    with pytest.raises(PermissionError):
        watchlist.remove("MSFT")

    assert not list(temp_files.glob(".watchlist-*.tmp"))  # no temporary file left behind
    assert market_tools.load_watchlist() == ["AAPL", "MSFT"]


# ---------------------------------------------------------------------------
# BUG-11: `python filings.py show` (and check, read) crashed with UnicodeEncodeError when its
# output went to a file or a pipe on Windows, such as the scheduled check's filings.log. That
# output is cp1252 there, which has no "✓" or "✗". A console was fine, which is why it hid.
# ---------------------------------------------------------------------------

TICKS = "print('Revenue $46.19B  \\u2713 confirmed by the report  \\u2717 the report says $1.00B')"


@pytest.mark.parametrize("set_up, works", [pytest.param(False, False, id="as-it-was"),
                                           pytest.param(True, True, id="fixed")])
def test_bug11_filings_output_to_a_log_file_can_print_ticks(set_up, works):
    code = "import filings\n" + ("filings._utf8_output()\n" if set_up else "") + TICKS
    env = {**os.environ, "PYTHONIOENCODING": "cp1252"}  # what Windows uses for output to a file or a pipe
    done = subprocess.run([sys.executable, "-c", code], cwd=PROJECT, env=env, capture_output=True, timeout=120)
    assert (done.returncode == 0) is works, done.stderr.decode(errors="replace")[-500:]
    if works:
        assert "✓ confirmed by the report  ✗ the report says" in done.stdout.decode("utf-8")


def test_bug11_every_filings_command_sets_up_its_output(monkeypatch, capsys):
    called = []
    monkeypatch.setattr(filings, "_utf8_output", lambda: called.append(True))
    monkeypatch.setattr(sys, "argv", ["filings.py", "list"])
    filings.main()
    assert called


# ---------------------------------------------------------------------------
# OPEN-01 (not fixed yet): the check that stops other websites from triggering runs trusts the
# Host header. A page using DNS rebinding sends a matching Origin and Host, passes the check,
# and can start paid runs and questions. Recommended fix: only accept the API's own origin
# when its host is localhost/127.0.0.1 or listed in FRONTEND_ORIGINS (or an ALLOWED_HOSTS setting).
# ---------------------------------------------------------------------------

@pytest.mark.xfail(strict=True, reason="OPEN-01: same-origin check trusts the Host header (DNS rebinding)")
def test_open01_a_rebound_host_cannot_post():
    response = TestClient(api.app).post(
        "/api/ask", content=b"{}",
        headers={"Origin": "http://attacker.example:8000", "Host": "attacker.example:8000",
                 "Content-Type": "application/json"})
    assert response.status_code == 403
