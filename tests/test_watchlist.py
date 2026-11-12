"""Offline tests for tracked and main stocks: the watchlist file, finding stocks, the API,
and the calendar scan staying in small requests as the list grows. Yahoo Finance is faked.

Run from the project folder:
    pytest -v tests/test_watchlist.py

Live check of Yahoo's search (needs internet and a recent yfinance):
    LIVE_TESTS=1 pytest -v -s -k live_search
"""

import asyncio
import json
import os
import re
import sys
import threading
import time
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
import watchlist  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TODAY = date(2026, 11, 6)
KNOWN = {  # what the fake Yahoo Finance knows: ticker -> (type, name)
    "AAPL": ("EQUITY", "Apple Inc."), "MSFT": ("EQUITY", "Microsoft Corporation"),
    "NVDA": ("EQUITY", "NVIDIA Corporation"), "COST": ("EQUITY", "Costco Wholesale Corporation"),
    "SPY": ("ETF", "SPDR S&P 500 ETF Trust"), "BTC-USD": ("CRYPTOCURRENCY", "Bitcoin USD"),
    **{f"T{i:02d}": ("EQUITY", f"Test Company {i}") for i in range(40)},
}
SEARCHES = []  # every query that reached the fake Yahoo search


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        if self.ticker == "FLAKY":
            raise ConnectionError("Yahoo rate limit")
        kind, name = KNOWN.get(self.ticker, (None, None))
        return {"quoteType": kind, "longName": name} if kind else {}


def fake_search(query):
    SEARCHES.append(query)
    if query == "broken":
        raise ConnectionError("timed out")
    return [
        {"symbol": "COST", "quoteType": "EQUITY", "longname": "Costco Wholesale Corporation", "exchDisp": "NASDAQ"},
        {"symbol": "CTCO.L", "quoteType": "EQUITY", "shortname": "Costco UK", "exchDisp": "London"},  # not US
        {"symbol": "XCOSX", "quoteType": "MUTUALFUND", "shortname": "Cost Fund"},
        {"symbol": "COST-USD", "quoteType": "CRYPTOCURRENCY", "shortname": "CostCoin"},
        {"symbol": "^COST", "quoteType": "INDEX", "shortname": "Cost index"},
        {"symbol": "SPY", "typeDisp": "ETF", "shortname": "SPDR S&P 500"},  # older format: no quoteType
        {"symbol": "AAPL", "quoteType": "EQUITY", "shortname": "Apple Inc.", "exchDisp": "NASDAQ"},
    ]


@pytest.fixture
def wl(tmp_path, monkeypatch):
    """A temporary watchlist and database, a fixed 'today', and fake Yahoo Finance. Returns the file."""
    path = tmp_path / "watchlist.txt"
    path.write_text("# my stocks\n*AAPL\n*NVDA  SMH   # vs. semiconductors\n\nMSFT\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", path)
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(watchlist.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(watchlist, "search_yahoo", fake_search)
    monkeypatch.setattr(events, "today_et", lambda: TODAY)
    monkeypatch.setattr(events, "fetch_calendar", lambda t: {"Earnings Date": [date(2026, 11, 19)]} if t == "COST" else {})
    monkeypatch.setattr(events, "company_name", lambda t: events.short_name(KNOWN.get(t, ("", t))[1]))
    watchlist._search_cache.clear()
    events._names.clear()
    SEARCHES.clear()
    return path


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

def test_a_star_marks_a_main_stock(wl):
    found = watchlist.entries()

    assert [(e["ticker"], e["main"], e["benchmark"]) for e in found] == [
        ("AAPL", True, None), ("NVDA", True, "SMH"), ("MSFT", False, None)]
    assert market_tools.load_watchlist() == ["AAPL", "NVDA", "MSFT"]  # the agent still tracks all of them
    assert market_tools.load_benchmarks() == {"NVDA": "SMH"}
    assert watchlist.main_tickers() == ["AAPL", "NVDA"]


def test_without_stars_the_first_ten_are_main(wl):
    wl.write_text("\n".join(f"T{i:02d}" for i in range(12)) + "\n")
    assert watchlist.main_tickers() == [f"T{i:02d}" for i in range(10)]


def test_adding_keeps_every_other_line_as_it_was(wl):
    before = wl.read_text()

    info = watchlist.add("cost")

    assert info == {"ticker": "COST", "name": "Costco Wholesale Corporation", "type": "Stock", "main": False}
    assert wl.read_text() == before + "COST\n"


def test_the_first_edit_makes_the_implicit_main_stocks_explicit(wl):
    wl.write_text("AAPL\nMSFT  # mine\n")  # no stars: both are main
    watchlist.add("COST")  # added as tracked only, so it mustn't become main

    assert wl.read_text() == "*AAPL\n*MSFT  # mine\nCOST\n"
    assert watchlist.main_tickers() == ["AAPL", "MSFT"]


@pytest.mark.parametrize("ticker, message", [
    ("ZZZZ", "Yahoo Finance doesn't know ZZZZ"),
    ("BTC-USD", "BTC-USD is a cryptocurrency. Only stocks and ETFs can be tracked."),
    ("CTCO.L", "That isn't a US ticker"),
    ("FLAKY", "Couldn't check FLAKY with Yahoo Finance right now"),
    ("", "That isn't a US ticker"),
])
def test_adding_checks_the_ticker_first(wl, ticker, message):
    before = wl.read_text()
    with pytest.raises(watchlist.WatchlistError, match=re.escape(message)):
        watchlist.add(ticker)
    assert wl.read_text() == before


def test_limits_on_tracked_and_main_stocks(wl, monkeypatch):
    with pytest.raises(watchlist.WatchlistError, match="already tracking AAPL") as dup:
        watchlist.add("AAPL")
    assert dup.value.status == 409

    monkeypatch.setattr(watchlist, "MAX_TRACKED", 4)
    watchlist.add("COST")
    with pytest.raises(watchlist.WatchlistError, match="tracking 4 stocks, the most allowed"):
        watchlist.add("SPY")

    monkeypatch.setattr(watchlist, "MAX_MAIN", 2)
    with pytest.raises(watchlist.WatchlistError, match="already have 2 main stocks"):
        watchlist.set_main("MSFT", True)


def test_star_and_unstar_keep_the_rest_of_the_line(wl):
    watchlist.set_main("NVDA", False)
    assert "NVDA  SMH   # vs. semiconductors" in wl.read_text().splitlines()
    watchlist.set_main("MSFT", True)
    assert watchlist.main_tickers() == ["AAPL", "MSFT"]
    watchlist.set_main("NVDA", True)
    assert "*NVDA  SMH   # vs. semiconductors" in wl.read_text().splitlines()


def test_remove(wl):
    watchlist.remove("nvda")
    assert wl.read_text() == "# my stocks\n*AAPL\n\nMSFT\n"
    with pytest.raises(watchlist.WatchlistError, match="isn't on your list") as missing:
        watchlist.remove("NVDA")
    assert missing.value.status == 404


def test_edits_at_the_same_time_are_never_lost(wl):
    tickers = [f"T{i:02d}" for i in range(8)]
    threads = [threading.Thread(target=watchlist.add, args=(t,)) for t in tickers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert set(tickers) <= set(market_tools.load_watchlist())
    assert len(market_tools.load_watchlist()) == 11
    assert not list(wl.parent.glob(".watchlist-*"))  # no temporary files left behind


@pytest.mark.skipif(os.name == "nt", reason="file permissions work differently on Windows")
def test_editing_keeps_the_files_permissions(wl):
    wl.chmod(0o644)
    watchlist.add("COST")
    assert wl.stat().st_mode & 0o777 == 0o644


# ---------------------------------------------------------------------------
# Finding stocks
# ---------------------------------------------------------------------------

def test_search_finds_us_stocks_and_etfs_only(wl):
    results = watchlist.search("  cost  ")

    assert [(r["ticker"], r["type"], r["tracked"]) for r in results] == [
        ("COST", "Stock", False), ("SPY", "ETF", False), ("AAPL", "Stock", True)]
    assert results[0]["name"] == "Costco Wholesale Corporation" and results[0]["exchange"] == "NASDAQ"
    assert SEARCHES == ["cost"]


def test_search_is_cached_and_problems_are_clear(wl):
    watchlist.search("cost")
    watchlist.search("COST")
    assert SEARCHES == ["cost"]  # the second search (any capitals) came from the cache
    assert watchlist.search("   ") == []
    with pytest.raises(watchlist.WatchlistError, match="search isn't answering right now"):
        watchlist.search("broken")


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(wl, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    reports_db.connect().close()  # the database exists, as it does once the program has run
    with TestClient(api.app) as test_client:
        yield test_client


def save_report(tickers):
    scan = {"session": {"status": "complete", "as_of": "2026-11-06"},
            "flagged": [{"ticker": tickers[0], "last_close": 190.0, "return_1d_pct": 4.1, "return_zscore": 2.9,
                         "volume_vs_avg": 2.0}],
            "quiet": [{"ticker": t, "last_close": 50.0, "return_1d_pct": 0.2} for t in tickers[1:]], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date="2026-11-06", status="final", title="Brief", body_md="# Brief",
                               as_of="2026-11-06", scan=scan)


def wait_until(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_lists_main_stocks_first_with_their_latest_figures(client):
    save_report(["AAPL", "MSFT"])
    events._names["AAPL"] = "Apple"

    body = client.get("/api/watchlist").json()

    assert [(s["ticker"], s["main"]) for s in body["stocks"]] == [("AAPL", True), ("NVDA", True), ("MSFT", False)]
    assert body["main_count"] == 2 and body["tracked_count"] == 3
    assert body["max_main"] == 10 and body["max_tracked"] == 25
    aapl, nvda, msft = body["stocks"]
    assert aapl["name"] == "Apple" and aapl["latest"]["category"] == "flagged" and aapl["latest"]["return_1d_pct"] == 4.1
    assert nvda["latest"] is None and nvda["benchmark"] == "SMH"  # not in any report yet
    assert msft["latest"]["category"] == "quiet" and msft["latest"]["price"] == 50.0
    # Names Yahoo hasn't given yet are looked up in the background
    wait_until(lambda: client.get("/api/watchlist").json()["stocks"][1]["name"] == "NVIDIA")


@pytest.mark.parametrize("name, short", [
    ("The Coca-Cola Company", "Coca-Cola"), ("The Home Depot, Inc.", "Home Depot"), ("Costco Wholesale Corporation", "Costco Wholesale"),
])
def test_short_names_for_new_stocks(name, short):
    assert events.short_name(name) == short


def test_quiet_stocks_keep_their_price(wl, monkeypatch):
    """flag_events gives quiet stocks a price too, so the Stocks tab can show every stock's."""
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    figures = {"AAPL": 0.4, "NVDA": 0.1, "MSFT": -0.2}
    monkeypatch.setattr(market_tools, "_measure", lambda t, session: (
        {"ticker": t, "last_price": 100.0 + figures[t], "return_1d_pct": figures[t], "return_zscore": 0.3,
         "volume_vs_avg": 1.0}, None))

    result = market_tools.flag_events()

    assert result["flagged"] == [] and result["quiet"][0] == {"ticker": "AAPL", "last_price": 100.4, "return_1d_pct": 0.4}


def test_api_add_star_and_remove(client):
    queue = api.hub.subscribe()

    added = client.post("/api/watchlist", json={"ticker": "COST"})
    starred = client.post("/api/watchlist/COST", json={"main": True})
    removed = client.post("/api/watchlist/MSFT/remove", json={})

    assert added.status_code == 201 and added.json()["stock"]["name"] == "Costco Wholesale Corporation"
    assert [s["ticker"] for s in added.json()["watchlist"]["stocks"]] == ["AAPL", "NVDA", "MSFT", "COST"]
    assert [s["ticker"] for s in starred.json()["stocks"] if s["main"]] == ["AAPL", "NVDA", "COST"]
    assert [s["ticker"] for s in removed.json()["stocks"]] == ["AAPL", "NVDA", "COST"]
    assert queue.qsize() >= 3 and queue.get_nowait() == {"type": "watchlist_changed"}
    # The new stock's earnings date is added in the background (Yahoo only, no Claude)
    wait_until(lambda: client.get("/api/watchlist").json()["stocks"][2]["next_event"])
    assert client.get("/api/watchlist").json()["stocks"][2]["next_event"]["line"] == "Thu Nov 19: Earnings report"


@pytest.mark.parametrize("path, body, status, message", [
    ("/api/watchlist", {"ticker": "AAPL"}, 409, "already tracking"),
    ("/api/watchlist", {"ticker": "ZZZZ"}, 400, "doesn't know"),
    ("/api/watchlist", {"symbol": "COST"}, 400, '{"ticker": "COST"}'),
    ("/api/watchlist/TSLA", {"main": True}, 404, "isn't on your list"),
    ("/api/watchlist/MSFT", {"main": "yes"}, 400, '{"main": true}'),
    ("/api/watchlist/TSLA/remove", {}, 404, "isn't on your list"),
])
def test_api_explains_what_went_wrong(client, path, body, status, message):
    response = client.post(path, json=body)
    assert response.status_code == status and message in response.json()["error"]


def test_other_websites_cannot_change_the_list(client, wl):
    before = wl.read_text()
    for path, body in (("/api/watchlist", {"ticker": "COST"}), ("/api/watchlist/AAPL/remove", {})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert wl.read_text() == before


def test_api_search(client):
    found = client.get("/api/stocks/search?q=cost").json()
    assert [r["ticker"] for r in found["results"]] == ["COST", "SPY", "AAPL"]
    assert client.get("/api/stocks/search").status_code == 400
    assert client.get("/api/stocks/search?q=broken").status_code == 502


def test_editing_watchlist_txt_by_hand_updates_open_pages(wl, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())
    # Create the database first. Creating one can take 1.4 s on Windows (SQLite retries deleting its
    # WAL files while a virus scanner has them open), and the watcher must have looked before the edit.
    reports_db.connect().close()

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        wl.write_text(wl.read_text() + "COST\n")
        os.utime(wl, ns=(time.time_ns(), time.time_ns() + 10**9))  # make sure the change time moves on
        event = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return event

    assert asyncio.run(scenario()) == {"type": "watchlist_changed"}


# ---------------------------------------------------------------------------
# Growing the list: the agent gets room, and the calendar's Claude requests stay small
# ---------------------------------------------------------------------------

def test_bigger_watchlists_give_the_agent_more_turns(wl, monkeypatch):
    import run_brief
    assert run_brief.turn_limit() == 25  # 3 stocks: the usual limit
    wl.write_text("\n".join(f"T{i:02d}" for i in range(40)) + "\n")
    assert run_brief.turn_limit() == 50  # a news check for each stock, plus room for the other tools

    used = {}

    async def fake_query(*, prompt, options):  # stops the run once it has seen the options
        used["max_turns"], used["budget"] = options.max_turns, options.max_budget_usd
        raise RuntimeError("stop here")
        yield

    monkeypatch.setattr(run_brief, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    monkeypatch.setattr(run_brief, "query", fake_query)
    with pytest.raises(RuntimeError, match="stop here"):
        asyncio.run(run_brief.run_once())
    assert used == {"max_turns": 50, "budget": 1.00}  # the cost cap is unchanged
    assert run_brief.options.max_turns == 25           # the shared settings aren't changed


def test_calendar_scan_reads_a_long_watchlist_in_groups(wl, monkeypatch):
    wl.write_text("\n".join(f"T{i:02d}" for i in range(23)) + "\n")
    monkeypatch.setattr(events, "fetch_news", lambda t: [{"title": f"{t} news", "publisher": "Wire",
                                                          "published": "2026-11-05", "url": f"https://x.example/{t}",
                                                          "summary": "..."}])
    prompts = []

    def fake_claude(prompt):
        prompts.append(prompt)
        if len(prompts) == 2:
            raise RuntimeError("Claude couldn't read the news: error_max_budget_usd")
        return json.dumps({"events": []}), 0.02

    monkeypatch.setattr(events, "ask_claude", fake_claude)

    result = events.scan()

    assert len(prompts) == 3  # 10 + 10 + 3 companies
    assert [len(re.findall(r"^\[\d+\] ", p, re.M)) for p in prompts] == [10, 10, 3]
    assert "T10" not in prompts[0] and "T10 |" in prompts[1]  # each request sees only its own companies
    assert result["cost_usd"] == 0.04 and result["status"] == "partial"
    assert "news scan (group 2 of 3): Claude couldn't read the news" in result["message"]


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_search():
    import yfinance

    raw = watchlist.search_yahoo("costco")  # real Yahoo Finance (this test doesn't use the fakes)
    print(f"\nyfinance {yfinance.__version__}. Yahoo's matches for 'costco':",
          [(q.get("symbol"), q.get("quoteType"), q.get("exchDisp")) for q in raw])
    assert any(q.get("symbol") == "COST" for q in raw)
    info = watchlist.check_ticker("COST")
    print("Checked:", info)
    assert info["type"] == "Stock" and "Costco" in info["name"]
