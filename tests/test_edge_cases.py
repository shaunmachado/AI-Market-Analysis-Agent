"""Edge cases and boundaries: the inputs and data at the limits of what the app accepts.

The other test files check that each feature works. These check the edges around it: values
exactly at a limit and one past it, empty and odd input, bad data from Yahoo or Claude, and
requests a browser or another website could send. Every test here passed when it was written;
they're here so later versions keep it that way. See test-case-reporting.md.

Run from the project folder:
    pytest -v tests/test_edge_cases.py
"""

import asyncio
import json
import sys
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import ask  # noqa: E402
import edgar  # noqa: E402
import events  # noqa: E402
import filings  # noqa: E402
import followups  # noqa: E402
import market_tools  # noqa: E402
import prices  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
import search_index  # noqa: E402
import stories  # noqa: E402
import watchlist  # noqa: E402
from claude_agent_sdk import ToolResultBlock  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

import test_market_tools as fakes  # noqa: E402  (its fake Yahoo Finance: prices shaped like the real thing)

CLOSED = {"status": "complete", "as_of": "2026-11-06"}
DAY = "2026-11-06"


@pytest.fixture(autouse=True)
def temp_files(tmp_path, monkeypatch):
    """A temporary database and watchlist for every test, so nothing real is touched."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", tmp_path / "watchlist.txt")
    (tmp_path / "watchlist.txt").write_text("AAPL\nNVDA\n", encoding="utf-8")
    prices._cache.clear()
    watchlist._search_cache.clear()
    events._names.clear()
    return tmp_path


@pytest.fixture
def client():
    return TestClient(api.app)  # no `with`: the background jobs (index updates, after-close run) stay off


def save_report(conn, day=DAY, status="final", as_of=None, title="Watchlist brief", body="# Watchlist brief\n\nbody",
                flagged=(("NVDA", 6.5),), quiet=("AAPL",)):
    as_of = as_of or (day if status == "final" else f"{day} 12:30 ET")
    scan = {"flagged": [{"ticker": t, "last_close": 100.0, "return_1d_pct": r, "return_5d_pct": r,
                         "return_zscore": 4.0, "volume_vs_avg": 2.0, "compared_to": "test"} for t, r in flagged],
            "quiet": [{"ticker": t, "return_1d_pct": 0.1} for t in quiet], "errors": []}
    return reports_db.save_report(conn, session_date=day, status=status, title=title, body_md=body,
                                  as_of=as_of, scan=scan)


# ---------------------------------------------------------------------------
# Market math at its limits (market_tools.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def fake_yahoo(monkeypatch):
    for store in (fakes.FAKE_DAILY, fakes.FAKE_INTRADAY, fakes.FAKE_NEWS, fakes.FAKE_INFO):
        store.clear()
    monkeypatch.setattr(market_tools.yf, "Ticker", fakes.FakeTicker)
    monkeypatch.setattr(market_tools, "market_session", lambda: CLOSED)
    market_tools._sectors.clear()


def daily(close, volume=1_000_000.0) -> pd.DataFrame:
    close = np.asarray(close, dtype=float)
    index = pd.bdate_range(end=fakes.FRIDAY, periods=len(close), tz=fakes.ET)
    return pd.DataFrame({"Close": close, "Volume": np.broadcast_to(volume, close.shape).astype(float)}, index=index)


def test_flat_prices_give_a_zero_zscore_not_a_division_error(fake_yahoo):
    fakes.FAKE_DAILY["FLAT"] = daily(np.full(63, 50.0))
    m = market_tools._moves("FLAT", CLOSED)
    assert m["return_1d_pct"] == 0.0 and m["return_5d_pct"] == 0.0
    assert m["return_zscore"] == 0.0  # no spread in past moves: nothing counts as unusual


def test_no_volume_history_gives_no_volume_ratio(fake_yahoo):
    fakes.FAKE_DAILY["NOVOL"] = daily(100 * np.cumprod(1 + fakes.calm_returns(3)), volume=0.0)
    assert market_tools._moves("NOVOL", CLOSED)["volume_vs_avg"] is None  # not infinity, not an error


@pytest.mark.parametrize("rows, works", [(25, True), (24, False)])
def test_25_days_of_history_is_the_minimum(fake_yahoo, rows, works):
    fakes.FAKE_DAILY["NEW"] = daily(100 * np.cumprod(1 + fakes.calm_returns(5)[:rows]))
    m = market_tools._moves("NEW", CLOSED)
    assert ("error" not in m) is works
    if not works:
        assert m["error"] == "not enough price history"


def test_flag_thresholds_include_the_limit_itself(fake_yahoo):
    fakes.FAKE_DAILY["NVDA"] = daily(100 * np.cumprod(1 + np.r_[fakes.calm_returns(9)[:-1], 0.03]))
    z = abs(market_tools._moves("NVDA", CLOSED)["return_zscore"])
    market_tools.WATCHLIST_FILE.write_text("NVDA\n", encoding="utf-8")

    at_limit = market_tools.flag_events(z_threshold=z, volume_threshold=99)
    just_above = market_tools.flag_events(z_threshold=z + 0.01, volume_threshold=99)

    assert [m["ticker"] for m in at_limit["flagged"]] == ["NVDA"]
    assert just_above["flagged"] == [] and [m["ticker"] for m in just_above["quiet"]] == ["NVDA"]


def test_a_watchlist_with_no_tickers_scans_nothing(fake_yahoo):
    market_tools.WATCHLIST_FILE.write_text("# nothing yet\n\n   \n*\n", encoding="utf-8")
    result = market_tools.flag_events()
    assert result["flagged"] == [] and result["quiet"] == [] and result["errors"] == []


def test_compute_moves_tidies_the_ticker(fake_yahoo):
    fakes.FAKE_DAILY["NVDA"] = daily(100 * np.cumprod(1 + fakes.calm_returns(4)))
    assert market_tools.compute_moves("  nvda ")["ticker"] == "NVDA"


@pytest.mark.parametrize("asked, days", [(0, 1), (-5, 1), (14, 14), (60, 60), (1000, 60)])
def test_upcoming_events_keeps_the_range_between_1_and_60_days(monkeypatch, asked, days):
    monkeypatch.setattr(market_tools, "now_et", lambda: datetime(2026, 11, 6, 9, 0, tzinfo=fakes.ET))
    result = market_tools.upcoming_events(days=asked)
    assert result["from"] == DAY
    assert result["to"] == (date(2026, 11, 6) + timedelta(days=days)).isoformat()


# ---------------------------------------------------------------------------
# The watchlist file and its rules (watchlist.py)
# ---------------------------------------------------------------------------

class KnownTicker:
    """Fake Yahoo Finance: every ticker is a real stock."""

    def __init__(self, ticker):
        self.info = {"quoteType": "EQUITY", "longName": f"{ticker} Inc."}


@pytest.mark.parametrize("ticker, allowed", [
    ("ABCDEFGHIJ", True),     # 10 characters: the longest allowed
    ("ABCDEFGHIJK", False),   # 11
    ("BRK-B", True),
    ("-ABC", False),          # must start with a letter or number
    ("BRK.B", False),         # a dot means a listing outside the US on Yahoo
    ("AAPL\nMSFT", False),    # a line break can't sneak a second line into the file
    ("AAPL # x", False),
])
def test_ticker_format_limits(monkeypatch, ticker, allowed):
    monkeypatch.setattr(watchlist.yf, "Ticker", KnownTicker)
    if allowed:
        watchlist.add(ticker)
        assert ticker in market_tools.load_watchlist()
    else:
        with pytest.raises(watchlist.WatchlistError, match="isn't a US ticker"):
            watchlist.add(ticker)
        assert market_tools.load_watchlist() == ["AAPL", "NVDA"]


def test_adding_tidies_case_and_spaces(monkeypatch):
    monkeypatch.setattr(watchlist.yf, "Ticker", KnownTicker)
    assert watchlist.add("  cost ")["ticker"] == "COST"
    assert market_tools.load_watchlist() == ["AAPL", "NVDA", "COST"]


def test_adding_to_a_file_without_a_final_line_break_starts_a_new_line(monkeypatch, temp_files):
    monkeypatch.setattr(watchlist.yf, "Ticker", KnownTicker)
    (temp_files / "watchlist.txt").write_text("*AAPL\n*NVDA  # last line, no line break", encoding="utf-8")
    watchlist.add("COST")
    assert (temp_files / "watchlist.txt").read_text(encoding="utf-8").splitlines() == [
        "*AAPL", "*NVDA  # last line, no line break", "COST"]


def test_starring_twice_adds_one_star(temp_files):
    (temp_files / "watchlist.txt").write_text("*AAPL\nNVDA\n", encoding="utf-8")
    watchlist.set_main("NVDA", True)
    watchlist.set_main("NVDA", True)
    assert (temp_files / "watchlist.txt").read_text(encoding="utf-8") == "*AAPL\n*NVDA\n"


def test_lines_with_only_stars_comments_or_spaces_are_ignored(temp_files):
    (temp_files / "watchlist.txt").write_text("*\n  # AAPL\n\t\n * msft # mine\n", encoding="utf-8")
    assert [(e["ticker"], e["main"]) for e in watchlist.entries()] == [("MSFT", True)]


def test_editing_a_missing_stock_is_a_404_and_changes_nothing(temp_files):
    before = (temp_files / "watchlist.txt").read_bytes()
    for edit in (lambda: watchlist.remove("ZZZZ"), lambda: watchlist.set_main("ZZZZ", True), lambda: watchlist.remove("")):
        with pytest.raises(watchlist.WatchlistError) as error:
            edit()
        assert error.value.status == 404
    assert (temp_files / "watchlist.txt").read_bytes() == before


# ---------------------------------------------------------------------------
# Storage rules at their edges (reports_db.py)
# ---------------------------------------------------------------------------

@pytest.fixture
def conn():
    with closing(reports_db.connect()) as connection:
        yield connection


def test_an_intraday_update_with_the_same_time_replaces_the_earlier_one(conn):
    assert save_report(conn, status="intraday", as_of=f"{DAY} 12:30 ET", body="# first") == reports_db.CREATED
    assert save_report(conn, status="intraday", as_of=f"{DAY} 12:30 ET", body="# second") == reports_db.UPDATED
    assert reports_db.get_report(conn, DAY)["body_md"] == "# second"


def test_an_unknown_status_is_refused_and_nothing_is_saved(conn):
    with pytest.raises(ValueError):
        save_report(conn, status="draft")
    assert reports_db.list_reports(conn) == []


def test_text_that_looks_like_sql_is_stored_as_plain_text(conn):
    title = "Robert'); DROP TABLE reports;--"
    save_report(conn, title=title, body=f"# {title}\n\n%_ wildcards and \"quotes\" too")
    report = reports_db.get_report(conn, DAY)
    assert report["title"] == title and report["body_md"].endswith('%_ wildcards and "quotes" too')
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1


def test_emoji_and_a_very_long_report_are_kept_exactly(conn):
    body = "# Brief \U0001F4C8\n\n" + ("Café — “quoted” 日本 " * 40_000)  # about 700 KB
    save_report(conn, body=body)
    assert reports_db.get_report(conn, DAY)["body_md"] == body


def test_a_failed_save_leaves_nothing_half_written(conn):
    bad_scan = {"flagged": [{"ticker": None, "return_1d_pct": 1.0}]}  # a ticker is required
    with pytest.raises(Exception):
        reports_db.save_report(conn, session_date=DAY, status="final", title="t", body_md="b", as_of=DAY, scan=bad_scan)
    assert reports_db.get_report(conn, DAY) is None
    assert conn.execute("SELECT COUNT(*) FROM report_tickers").fetchone()[0] == 0
    assert save_report(conn) == reports_db.FINALIZED  # the connection still works afterwards


def test_ticker_history_ignores_letter_case(conn):
    save_report(conn)
    assert [h["session_date"] for h in reports_db.ticker_history(conn, "nvda")] == [DAY]


# ---------------------------------------------------------------------------
# API requests at the limits (api.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("path, status_code", [
    ("/api/reports?limit=365", 200), ("/api/reports?limit=366", 400),
    ("/api/reports?limit=-1", 400), ("/api/reports?limit=1.5", 400), ("/api/reports?limit=", 400),
    ("/api/alerts?limit=100", 200), ("/api/alerts?limit=101", 400),
    ("/api/search?q=nvda&limit=50", 200), ("/api/search?q=nvda&limit=51", 400),
    ("/api/tickers/ABCDEFGHIJKLMNO/history", 200),    # 15 characters
    ("/api/tickers/ABCDEFGHIJKLMNOP/history", 400),   # 16
    ("/api/followups?horizon=5", 200), ("/api/followups?horizon=2", 400),
    ("/api/stories?ticker=" + "A" * 16, 400),
])
def test_number_and_length_limits(client, path, status_code):
    assert client.get(path).status_code == status_code


@pytest.mark.parametrize("query, status_code", [
    ("start=2026-01-01&end=2026-04-11", 200),   # 100 days: the most allowed
    ("start=2026-01-01&end=2026-04-12", 400),   # 101 days
    ("start=2026-11-06&end=2026-11-06", 200),   # one day
    ("start=2028-02-29", 200),                  # a real leap day
    ("start=2027-02-29", 400),                  # not a real day
    ("start=2026-13-01", 400),
])
def test_calendar_date_range_limits(client, query, status_code):
    assert client.get(f"/api/calendar?{query}").status_code == status_code


@pytest.mark.parametrize("q, status_code", [("x" * 500, 200), ("x" * 501, 400), ("   ", 400), ("", 400)])
def test_search_text_length_limits(client, q, status_code):
    assert client.get("/api/search", params={"q": q}).status_code == status_code


@pytest.mark.parametrize("body, status_code", [
    ({"ticker": 123}, 400), ({"ticker": None}, 400), ({"ticker": "A" * 1000}, 400),
    ({"ticker": ""}, 400), ([], 400), ("COST", 400),
])
def test_adding_a_stock_with_bad_input_is_a_clear_400(client, temp_files, body, status_code):
    before = (temp_files / "watchlist.txt").read_bytes()
    response = client.post("/api/watchlist", json=body)
    assert response.status_code == status_code and response.json()["error"]
    assert (temp_files / "watchlist.txt").read_bytes() == before


@pytest.mark.parametrize("path", ["/api/watchlist", "/api/runs", "/api/ask", "/api/calendar/scan", "/api/followups/refresh"])
def test_pages_opened_from_a_file_or_sandbox_cannot_post(client, path):
    """Browsers send Origin: null from local files and sandboxed frames."""
    assert client.post(path, json={}, headers={"Origin": "null"}).status_code == 403


def test_broken_json_is_a_clear_400(client):
    for path in ("/api/watchlist", "/api/ask", "/api/stories/check"):
        response = client.post(path, content=b'{"ticker": ', headers={"Content-Type": "application/json"})
        assert response.status_code == 400, path


@pytest.mark.parametrize("path", ["/%2e%2e/secret.txt", "/..%2fsecret.txt", "/%2e%2e%2fsecret.txt", "/assets/..%2f..%2fsecret.txt"])
def test_the_built_frontend_never_serves_files_outside_its_folder(tmp_path, path):
    dist = tmp_path / "site" / "dist"
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<div id='root'></div>", encoding="utf-8")
    (tmp_path / "site" / "secret.txt").write_text("TOP SECRET", encoding="utf-8")
    app = TestClient(api.create_app(frontend_dist=dist))
    assert "id='root'" in app.get("/").text  # the folder itself is served...
    response = app.get(path)                 # ...but nothing above it
    assert "TOP SECRET" not in response.text
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Discord alerts (alerts.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("before, now, again", [
    (2.0, 3.5, True),     # grew by exactly 1.5: alert again
    (2.0, 3.49, False),
    (-2.0, -3.5, True),   # the same, for a fall
    (2.5, -2.0, True),    # reversed, and now unusual the other way
    (2.5, -1.99, False),  # reversed, but not unusual yet
    (2.0, None, False),
])
def test_when_a_ticker_alerts_again_the_same_day(before, now, again):
    assert alerts._grew({"return_zscore": now}, {"return_zscore": before}) is again


@pytest.mark.parametrize("url, ok", [
    ("  https://discord.com/api/webhooks/1/abc\n", True),     # spaces and a line break from copy-paste
    ("https://ptb.discord.com/api/webhooks/1/abc", True),
    ("http://discord.com/api/webhooks/1/abc", False),          # not encrypted
    ("https://discord.com.evil.example/api/webhooks/1/abc", False),
    ("https://evil.example/?https://discord.com/api/webhooks/1/abc", False),
    ("https://discord.com/api/channels/1", False),
])
def test_only_real_discord_webhooks_are_accepted(monkeypatch, url, ok):
    monkeypatch.setenv(alerts.WEBHOOK_ENV, url)
    if ok:
        assert alerts.webhook_url() == url.strip()
    else:
        with pytest.raises(ValueError):
            alerts.webhook_url()
        assert alerts.enabled() is False


def test_shortening_keeps_text_at_the_limit_and_never_cuts_a_link():
    assert alerts._shorten("x" * 50, 50) == "x" * 50
    long = "See [the full story here](https://example.com/" + "a" * 200 + ") for more. " + "y" * 100
    short = alerts._shorten(long, 120)
    assert len(short) <= 120 and "](" not in short and "https://" not in short
    assert short.startswith("See the full story here for more.") and short.endswith("…")


# ---------------------------------------------------------------------------
# Follow-through: judging a move at the exact boundaries (followups.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move, after, expected", [
    (10, -2.27, "held"),      # gave back 25%: still held
    (10, -2.32, "faded"),     # 26%
    (-10, 2.78, "held"),      # the same, for a fall
    (-10, 2.9, "faded"),
    (10, -9.09, "reversed"),  # exactly back where it started counts as all of it
    (10, -9.0, "faded"),
    (-10, 11.11, "reversed"),
    (0, 5.0, "held"),         # a volume-only flag with no price move doesn't divide by zero
])
def test_held_faded_reversed_boundaries(move, after, expected):
    assert followups.outcome(move, after) == expected


@pytest.mark.parametrize("move, after, surprise", [
    (10, 9.09, True),    # as much again within a week
    (10, 9.0, False),
    (10, -9.09, True),   # reversed
    (0, 50.0, False),
])
def test_surprise_boundaries(move, after, surprise):
    assert followups.is_surprise(move, after) is surprise


# ---------------------------------------------------------------------------
# Claude's replies, read defensively (events.py, stories.py)
# ---------------------------------------------------------------------------

TODAY = date(2026, 11, 6)
ARTICLES = [{"ticker": "AAPL", "title": f"story {n}", "url": f"https://example.com/{n}"} for n in (1, 2)]


def validate(raw_events, articles=ARTICLES):
    return events.validate(raw_events, articles, {"AAPL": "Apple"}, {}, TODAY, TODAY + timedelta(days=60))


def test_calendar_reply_items_that_arent_events_are_dropped_with_a_reason():
    accepted, dropped = validate(["launch", 3, None, {"ticker": "AAPL", "title": "Launch", "date": "2026-11-20", "sources": [1]}])
    assert [e["title"] for e in accepted] == ["Launch"]
    assert dropped == ["not an object"] * 3


@pytest.mark.parametrize("day, kept", [("2026-11-06", True), ("2027-01-05", True), ("2026-11-05", False),
                                       ("2027-01-06", False), ("next week", False), (None, False)])
def test_calendar_events_must_fall_between_today_and_the_horizon(day, kept):
    accepted, _ = validate([{"ticker": "AAPL", "title": "Launch", "date": day, "sources": [1]}])
    assert bool(accepted) is kept


def test_the_same_event_twice_is_kept_once_and_too_many_are_capped():
    same = {"ticker": "AAPL", "title": "Launch", "date": "2026-11-20", "sources": [1]}
    assert len(validate([same, {**same, "title": "  launch "}, same])[0]) == 1
    many = [{"ticker": "AAPL", "title": f"Event {n}", "date": "2026-11-20", "sources": [1]} for n in range(200)]
    assert len(validate(many)[0]) == events.MAX_EVENTS


def test_unsafe_links_are_dropped_from_calendar_sources():
    articles = [{"title": "a", "url": "javascript:alert(1)"}, {"title": "b", "url": "https://example.com/b"}]
    accepted, _ = validate([{"ticker": "AAPL", "title": "Launch", "date": "2026-11-20", "sources": [1, 2]}], articles)
    assert [s["url"] for s in accepted[0]["sources"]] == ["https://example.com/b"]


LATER = [{"title": f"later {n}", "publisher": "Wire", "url": f"https://example.com/{n}", "published": None} for n in (1, 2, 3)]


@pytest.mark.parametrize("reply, problem", [
    ('{"verdict": "maybe", "update": "x", "sources": [1]}', "unknown verdict"),
    ('{"verdict": "confirmed", "update": "   ", "sources": [1]}', "no update"),
    ('{"verdict": "confirmed", "update": "x", "sources": [0, 4, true, "1"]}', "cited none"),
    ("I couldn't find anything.", "no JSON"),
])
def test_story_replies_that_cant_be_trusted_are_refused(reply, problem):
    with pytest.raises(ValueError, match=problem):
        stories.parse_reply(reply, LATER)


def test_story_reply_is_tidied():
    reply = 'Sure! ```json\n{"verdict": "Developed", "update": "  ' + "word " * 200 + '", "sources": [3, 1, 3, 9]}\n```'
    verdict, update, sources = stories.parse_reply(reply, LATER)
    assert verdict == "developed"
    assert len(update) == 600 and "  " not in update
    assert [s["title"] for s in sources] == ["later 1", "later 3"]  # in order, once each, only real headlines


def test_no_update_needs_no_sources():
    assert stories.parse_reply('{"verdict": "no_update", "update": "Nothing new.", "sources": []}', LATER) == (
        "no_update", "Nothing new.", [])


# ---------------------------------------------------------------------------
# Search (search_index.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query", ["???", "— …", "日本株", "''", '"'])
def test_searches_with_no_usable_words_return_nothing_without_an_error(query):
    with closing(reports_db.connect()) as conn:
        save_report(conn)
    search_index.sync(embed_now=False)
    assert search_index.search(query)["results"] == []


def test_long_searches_use_the_first_20_words():
    words = [f"word{n}" for n in range(40)]
    assert search_index.search(" ".join(words))["terms"] == words[:20]


# ---------------------------------------------------------------------------
# Chart prices cache (prices.py)
# ---------------------------------------------------------------------------

def test_cached_prices_expire_and_empty_results_are_not_cached(monkeypatch):
    clock, calls = [1000.0], []
    monkeypatch.setattr(prices.time, "monotonic", lambda: clock[0])

    def fetch(ticker, period):
        calls.append(ticker)
        return [] if ticker == "NONE" else [{"date": DAY, "close": 10.0, "volume": 1}]

    monkeypatch.setattr(prices, "fetch_prices", fetch)
    prices.get_prices("NVDA", "1mo")
    clock[0] += prices.CACHE_SECONDS - 1
    prices.get_prices("NVDA", "1mo")       # still fresh
    clock[0] += 2
    prices.get_prices("NVDA", "1mo")       # expired: downloaded again
    prices.get_prices("NONE", "1mo")
    prices.get_prices("NONE", "1mo")       # nothing came back last time, so it asks again
    assert calls == ["NVDA", "NVDA", "NONE", "NONE"]


# ---------------------------------------------------------------------------
# Ask (ask.py)
# ---------------------------------------------------------------------------

def test_tickers_are_found_in_questions_however_they_are_written(conn):
    save_report(conn, flagged=(("NVDA", 6.5), ("BRK-B", -3.0)), quiet=("AAPL",))
    found = ask.mentioned_tickers(conn, "Why did nvda's price jump? And what about Brk-b, or MSFT?")
    assert found == ["BRK-B", "NVDA"]  # MSFT isn't in any report
    assert ask.mentioned_tickers(conn, "Anything unusual this week?") == []


@pytest.mark.parametrize("question", ["", "   \n\t ", "x" * 501])
def test_ask_refuses_empty_or_too_long_questions_before_any_cost(question):
    with pytest.raises(ValueError):
        asyncio.run(ask.answer(question, lambda event: None))


def test_a_question_of_exactly_500_characters_is_accepted():
    done = asyncio.run(ask.answer("x" * 500, lambda event: None))
    assert done["type"] == "done" and done["cost_usd"] == 0  # no reports yet, so Claude isn't asked


# ---------------------------------------------------------------------------
# Runs (run_brief.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("content, expected", [
    ('{"a": 1}', {"a": 1}),
    ([{"type": "text", "text": '{"a": 1}'}], {"a": 1}),
    ([{"type": "text", "text": '{"a": 1}'}, {"type": "text", "text": '{"b": 2}'}], [{"a": 1}, {"b": 2}]),
    ([{"type": "image", "data": "..."}, {"type": "text", "text": "[1, 2]"}], [1, 2]),
    ("not json", None),
    ([], []),
    (None, []),
])
def test_tool_results_are_read_whatever_their_shape(content, expected):
    assert run_brief.tool_payload(ToolResultBlock(tool_use_id="t1", content=content)) == expected


def test_runs_get_more_turns_for_longer_watchlists(temp_files):
    (temp_files / "watchlist.txt").write_text("\n".join(f"T{n:02d}" for n in range(40)), encoding="utf-8")
    assert run_brief.turn_limit() == 50
    (temp_files / "watchlist.txt").write_text("AAPL\n", encoding="utf-8")
    assert run_brief.turn_limit() == run_brief.BASE_TURNS
    (temp_files / "watchlist.txt").unlink()
    assert run_brief.turn_limit() == run_brief.BASE_TURNS  # a missing file doesn't stop the run here


@pytest.mark.parametrize("session, key", [
    ({"status": "in_progress", "as_of": "2026-11-06 09:35 ET"}, ("2026-11-06", "intraday")),
    ({"status": "complete", "as_of": "2026-11-06"}, ("2026-11-06", "final")),
])
def test_report_key(session, key):
    assert run_brief.report_key(session) == key


def test_news_items_round_trip_through_json_with_odd_characters():
    item = {"title": "Café — \U0001F4C8 <b>bold</b> & \"quotes\"", "url": "https://example.com/?a=1&b=2"}
    block = ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": json.dumps(item)}])
    assert run_brief.tool_payload(block) == item


# ---------------------------------------------------------------------------
# Company filings at their limits (edgar.py, filings.py)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("metric, announced, reported, same", [
    ("revenue", 1_005_990_000, 1e9, True),     # just inside 0.6%
    ("revenue", 1_006_010_000, 1e9, False),    # just outside
    ("revenue", 50_600_000, 50e6, True),       # small figures: $600,000 exactly
    ("revenue", 50_600_001, 50e6, False),      # one dollar more
    ("eps_diluted", 1.01, 1.00, True),         # a cent
    ("eps_diluted", 1.012, 1.00, False),       # more than a cent
])
def test_confirming_figures_at_the_rounding_limits(metric, announced, reported, same):
    assert filings.agrees(metric, announced, reported) is same


DOC = filings._plain("Revenue was up 20% this quarter, and the outlook was raised.")


@pytest.mark.parametrize("quote, found", [
    ("venue was up", True),                    # 12 characters: the shortest quote that counts
    ("enue was up", False),                    # 11: too short to prove anything
    ("Revenue ... quarter", True),             # pieces in order, 14 characters in all
    ("quarter ... Revenue", False),            # the same pieces, out of order
    ("Revenue was up 20% this quarter.", True),
    ("Revenue was up 21% this quarter.", False),
])
def test_quotes_at_the_length_limit(quote, found):
    assert filings.quoted(quote, DOC) is found


def _known(value):
    period = {"start": date(2026, 4, 1), "end": date(2026, 6, 30), "value": value, "derived": False}
    return {"revenue": {"quarters": {period["end"]: period}}}


@pytest.mark.parametrize("value, kept", [(20e9, True), (20.1e9, False), (0.05e9, True), (0.049e9, False)])
def test_the_wrong_unit_check_at_20_times_and_a_20th(value, kept):
    notes = []
    reported = [{"metric": "revenue", "value": value, "as_written": "x", "scale": "millions", "quote": "q"}]
    rows = filings.compare(reported, date(2026, 9, 30), _known(1e9), notes)["rows"]
    assert bool(rows) is kept and bool(notes) is not kept


@pytest.mark.parametrize("period_end, clear", [
    ("2026-10-28", True),    # the filing date itself
    ("2026-10-29", False),   # after the filing: impossible
    ("2026-04-11", True),    # 200 days before
    ("2026-04-10", False),   # 201
])
def test_a_quarter_end_at_the_edges_of_what_is_believable(period_end, clear):
    reply = json.dumps({"headline": "Results.", "period_end": period_end,
                        "points": [{"text": "Up.", "quote": "Revenue was up 20% this quarter"}]})
    checked = filings.check_reply(reply, "Revenue was up 20% this quarter, and the outlook was raised.", "results", date(2026, 10, 28))
    assert (checked["period_end"] is not None) is clear


def test_documents_are_cut_only_past_the_limit_and_at_a_line_break():
    exact = "a" * 50 + "\n" + "b" * 49  # 100 characters
    assert filings._cut(exact, 100) == (exact, False)
    assert filings._cut(exact + "c", 100) == ("a" * 50, True)
    assert filings._cut("x" * 101, 100) == ("x" * 100, True)  # one long line: cut at the limit


@pytest.mark.parametrize("written, value", [
    ("1,234.5", 1234.5), ("(0.12)", -0.12), ("12,3456", None), ("1.2.3", None), ("$", None), ("()", None), ("1,234,567", 1234567),
])
def test_numbers_at_the_edges_of_how_filings_write_them(written, value):
    assert edgar.parse_number(written) == value


@pytest.mark.parametrize("form, items, kind, title", [
    ("8-k", ["8.01"], "announcement", "Other events"),               # lower case
    (" NT  10-Q ", [], "late", "Says its quarterly report will be late"),
    ("8-K/A", ["2.02", "9.01"], "results", "Amended: Results announcement"),
    ("8-K", [], "announcement", "Announcement"),                     # no items at all
    ("8-K", ["9.99"], "announcement", "Item 9.99"),                  # an item the SEC adds later
    ("10-K405", [], None, None),                                     # a form that isn't followed
])
def test_naming_odd_forms_and_items(form, items, kind, title):
    about = filings.describe(form, items)
    assert (about["kind"], about["title"]) == (kind, title) if kind else about is None


@pytest.mark.parametrize("body, status_code", [
    ({"accession": "0000789019-26-000123"}, 404),     # the right shape, not listed
    ({"accession": "000789019-26-000123"}, 400),      # 9 digits first
    ({"accession": "00000789019-26-000123"}, 400),    # 11
    ({"accession": " 0000789019-26-000123"}, 400),    # a space
    ({"accession": "0000789019-26-00012a"}, 400),
    ({"accession": 789019_26_000123}, 400), ({}, 400), ([], 400), ("0000789019-26-000123", 400),
])
def test_reading_a_filing_with_bad_input_is_refused_before_anything_is_spent(client, monkeypatch, body, status_code):
    monkeypatch.setattr(filings, "read", lambda *a, **k: pytest.fail("nothing should be read"))
    response = client.post("/api/filings/read", json=body)
    assert response.status_code == status_code and response.json()["error"]


@pytest.mark.parametrize("path, status_code", [
    ("/api/filings?ticker=ABCDEFGHIJKLMNO", 200),   # 15 characters
    ("/api/filings?ticker=ABCDEFGHIJKLMNOP", 400),  # 16
    ("/api/filings?ticker=msft", 200), ("/api/filings?ticker=MS%20FT", 400),
])
def test_filings_view_ticker_limits(client, path, status_code):
    assert client.get(path).status_code == status_code


def test_filings_check_and_read_refuse_pages_from_files_or_sandboxes(client):
    for path in ("/api/filings/check", "/api/filings/read"):
        assert client.post(path, json={}, headers={"Origin": "null"}).status_code == 403, path
