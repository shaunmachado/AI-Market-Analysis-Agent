"""Offline tests for the upcoming events calendar. Yahoo Finance and Claude are faked.

Run from the project folder:
    pytest -v tests/test_events.py

Live check of Yahoo's calendar data (needs internet):
    LIVE_TESTS=1 pytest -v -s -k live_calendar
"""

import asyncio
import json
import os
import re
import sys
import time
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TODAY = date(2026, 11, 6)
NAMES = {"AAPL": "Apple Inc.", "NVDA": "NVIDIA Corporation", "JPM": "JPMorgan Chase & Co."}
CALENDARS = {}  # ticker -> what yfinance's .calendar returns (or an exception to raise)
NEWS = {}       # ticker -> raw yfinance news items
JSON_HEADERS = {"Content-Type": "application/json"}


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        return {"longName": NAMES.get(self.ticker)}

    @property
    def calendar(self):
        value = CALENDARS.get(self.ticker, {})
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def news(self):
        return NEWS.get(self.ticker, [])


def article(ticker, slug, title, summary, published="2026-11-04T13:00:00Z"):
    return {"content": {"title": title, "summary": summary, "pubDate": published,
                        "provider": {"displayName": "Example Wire"},
                        "canonicalUrl": {"url": f"https://news.example.com/{ticker.lower()}-{slug}"}}}


class FakeClaude:
    """Stands in for Claude: replies with whatever the test sets, and keeps the prompts it was sent."""

    def __init__(self):
        self.prompts, self.reply = [], lambda prompt: {"events": []}

    def __call__(self, prompt):
        self.prompts.append(prompt)
        reply = self.reply(prompt)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply), 0.03


def number(prompt, slug):
    """The [N] a test article got in the prompt (found by its title, since addresses aren't sent to Claude)."""
    title = next(a["content"]["title"] for items in NEWS.values() for a in items
                 if a["content"]["canonicalUrl"]["url"].endswith(slug))
    match = re.search(rf"^\[(\d+)\] .*\n    {re.escape(title)}$", prompt, re.M)
    assert match, f"article {slug} not in the prompt"
    return int(match.group(1))


@pytest.fixture
def cal(tmp_path, monkeypatch):
    """A temporary database and watchlist, a fixed 'today', and fake Yahoo and Claude."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    watchlist = tmp_path / "watchlist.txt"
    watchlist.write_text("AAPL\nNVDA\nJPM\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    monkeypatch.setattr(events, "today_et", lambda: TODAY)
    monkeypatch.setattr(events.yf, "Ticker", FakeTicker)
    events._names.clear()
    CALENDARS.clear()
    NEWS.clear()
    claude = FakeClaude()
    monkeypatch.setattr(events, "ask_claude", claude)
    return claude


def stored(day_from="2000-01-01", day_to="2100-01-01"):
    with closing(reports_db.connect(readonly=True)) as conn:
        return events.events_between(conn, day_from, day_to)


def standard_news():
    NEWS["AAPL"] = [article("AAPL", "event", "Apple sets November 18 launch event",
                            "Apple will hold a product launch event on November 18, it said on Wednesday."),
                    article("AAPL", "earnings-preview", "What to expect from Apple's results",
                            "Analysts look for iPhone sales to rise when Apple reports.")]
    NEWS["NVDA"] = [article("NVDA", "court", "Court hearing in Nvidia patent case set for next Thursday",
                            "A federal judge set a hearing for next Thursday.", published="2026-11-05T15:00:00Z")]


def standard_reply(prompt):
    return {"events": [
        {"ticker": "AAPL", "date": "2026-11-18", "title": "Product launch event",
         "details": "Apple will hold a product launch event.", "sources": [number(prompt, "aapl-event")]},
        {"ticker": "NVDA", "date": "2026-11-12", "title": "Court hearing in patent case",
         "details": "A federal judge set a hearing.", "sources": [number(prompt, "nvda-court")]},
        {"ticker": "TSLA", "date": "2026-11-20", "title": "Not on the watchlist", "sources": [1]},
        {"ticker": "AAPL", "date": "2026-11-21", "title": "Made up", "sources": []},
        {"ticker": "AAPL", "date": "2026-12-01", "title": "Cites an article that doesn't exist", "sources": [99]},
        {"ticker": "NVDA", "date": "2026-10-01", "title": "Already happened", "sources": [1]},
        {"ticker": "NVDA", "date": "2027-06-01", "title": "Too far ahead", "sources": [1]},
        {"ticker": "JPM", "date": "soon", "title": "No real date", "sources": [1]},
    ]}


# ---------------------------------------------------------------------------
# Company names and Yahoo's calendar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, short", [
    ("Apple Inc.", "Apple"), ("NVIDIA Corporation", "NVIDIA"), ("JPMorgan Chase & Co.", "JPMorgan Chase"),
    ("Amazon.com, Inc.", "Amazon.com"), ("Meta Platforms, Inc.", "Meta Platforms"),
    ("Berkshire Hathaway Inc.", "Berkshire Hathaway"), ("Microsoft", "Microsoft"),
])
def test_short_company_names(name, short):
    assert events.short_name(name) == short


def test_earnings_and_dividend_dates_from_yahoo():
    cal = {"Earnings Date": [date(2026, 11, 19)], "Earnings Average": 2.35, "Earnings Low": 2.21,
           "Earnings High": 2.4, "Ex-Dividend Date": date(2026, 11, 10), "Dividend Date": date(2026, 11, 13)}

    found = events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60))

    earnings, dividend = found
    assert (earnings["kind"], earnings["event_date"], earnings["title"]) == ("earnings", "2026-11-19", "Earnings report")
    assert earnings["details"] == "Analysts' average estimate is $2.35 a share (range $2.21 to $2.40)."
    assert earnings["date_note"] is None
    assert earnings["sources"][0]["url"] == "https://finance.yahoo.com/quote/AAPL/"
    assert (dividend["kind"], dividend["event_date"], dividend["title"]) == ("dividend", "2026-11-10", "Ex-dividend date")
    assert dividend["details"].endswith("It's paid on Nov 13.")


def test_an_unconfirmed_earnings_window_is_marked_as_an_estimate():
    cal = {"Earnings Date": [date(2026, 11, 23), date(2026, 11, 18)]}

    (earnings,) = events.calendar_events("NVDA", "NVIDIA", cal, TODAY, TODAY + timedelta(days=60))

    assert earnings["event_date"] == "2026-11-18"  # the start of the window
    assert earnings["title"] == "Earnings report (date not confirmed)"
    assert earnings["date_note"] == "Estimated: Yahoo Finance shows a window of Nov 18 to Nov 23."


def test_past_and_far_off_dates_are_left_out():
    cal = {"Earnings Date": [date(2026, 10, 30)], "Ex-Dividend Date": date(2027, 3, 1)}
    assert events.calendar_events("JPM", "JPMorgan Chase", cal, TODAY, TODAY + timedelta(days=60)) == []


@pytest.mark.parametrize("cal", [
    pd.DataFrame({0: [pd.Timestamp("2026-11-19")], 1: [pd.Timestamp("2026-11-20")]}, index=["Earnings Date"]),
    {"Earnings Date": [datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)]},
    {"Earnings Date": ["2026-11-19"]},
    {"Earnings Date": int(datetime(2026, 11, 19, 12, tzinfo=timezone.utc).timestamp())},
], ids=["older-table-format", "datetime", "text", "epoch-seconds"])
def test_other_calendar_formats_are_understood(cal):
    found = events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60))
    assert found[0]["event_date"] == "2026-11-19"


@pytest.mark.parametrize("cal", [None, {}, {"Earnings Date": []}, {"Earnings Date": "not a date"}, "junk", 42])
def test_missing_or_odd_calendar_data_gives_no_events(cal):
    assert events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60)) == []


# ---------------------------------------------------------------------------
# Scanning: calendar dates plus dated events from the news
# ---------------------------------------------------------------------------

def test_a_scan_saves_calendar_dates_and_checked_news_events(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    CALENDARS["JPM"] = {"Ex-Dividend Date": date(2026, 11, 10)}
    standard_news()
    cal.reply = standard_reply

    result = events.scan()

    assert result["status"] == "ok" and result["articles"] == 3 and result["cost_usd"] == 0.03
    assert result["events_found"] == 2 and result["dropped"] == 6
    reasons = " | ".join(result["dropped_reasons"])
    for why in ("not a watchlist ticker", "no valid article cited", "outside 2026-11-06 to 2027-01-05", "no valid date"):
        assert why in reasons
    saved = {(e["event_date"], e["company"], e["kind"]): e for e in stored()}
    assert set(saved) == {("2026-11-10", "JPMorgan Chase", "dividend"), ("2026-11-12", "NVIDIA", "news"),
                          ("2026-11-18", "Apple", "news"), ("2026-11-19", "Apple", "earnings")}
    launch = saved[("2026-11-18", "Apple", "news")]
    assert launch["title"] == "Product launch event"
    assert launch["sources"] == [{"title": "Apple sets November 18 launch event", "publisher": "Example Wire",
                                  "url": "https://news.example.com/aapl-event", "published": "2026-11-04T13:00:00Z"}]

    prompt = cal.prompts[0]
    assert "TODAY: 2026-11-06 (Friday)" in prompt and "HORIZON_END: 2027-01-05" in prompt
    assert re.search(r"- id \d+: AAPL earnings on 2026-11-19: Earnings report", prompt)  # Claude sees the calendar
    assert "[3] NVDA | Example Wire | published 2026-11-05T15:00:00Z" in prompt


def test_scanning_again_doesnt_duplicate_events(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = standard_reply

    events.scan()
    first = stored()
    events.scan()
    second = stored()

    assert len(second) == len(first) == 3
    assert [e["id"] for e in second] == [e["id"] for e in first]  # the same rows, updated in place


def test_a_moved_news_event_keeps_its_place_on_the_calendar(cal):
    NEWS["AAPL"] = [article("AAPL", "investor-day", "Apple investor day on Nov 20", "...")]
    cal.reply = lambda p: {"events": [{"ticker": "AAPL", "date": "2026-11-20", "title": "Investor day",
                                       "sources": [number(p, "investor-day")]}]}
    events.scan()
    (first,) = stored()

    NEWS["AAPL"] = [article("AAPL", "investor-day-moved", "Apple moves investor day to Nov 24", "...")]
    cal.reply = lambda p: {"events": [{"ticker": "AAPL", "date": "2026-11-24", "title": "Investor day (moved)",
                                       "sources": [number(p, "investor-day-moved")], "same_as": first["id"]}]}
    events.scan()
    (moved,) = stored()

    assert moved["id"] == first["id"] and moved["event_date"] == "2026-11-24"
    assert [s["url"] for s in moved["sources"]] == ["https://news.example.com/aapl-investor-day",
                                                   "https://news.example.com/aapl-investor-day-moved"]


def test_news_about_an_earnings_date_is_attached_without_changing_the_date(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()

    def reply(prompt):
        earnings_id = int(re.search(r"- id (\d+): AAPL earnings", prompt).group(1))
        return {"events": [{"ticker": "AAPL", "date": "2026-12-25", "title": "Results", "same_as": earnings_id,
                            "details": "Analysts look for iPhone sales to rise.",
                            "sources": [number(prompt, "earnings-preview")]}]}

    cal.reply = reply
    events.scan()
    (earnings,) = [e for e in stored() if e["kind"] == "earnings"]

    assert earnings["event_date"] == "2026-11-19" and earnings["title"] == "Earnings report"  # Yahoo's date stands
    assert earnings["news_note"] == "Analysts look for iPhone sales to rise."
    assert [s["publisher"] for s in earnings["sources"]] == ["Yahoo Finance", "Example Wire"]
    assert not [e for e in stored() if e["kind"] == "news"]


def test_yahoo_moving_an_earnings_date_replaces_the_old_one_but_never_touches_the_past(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    events.scan()
    with closing(events.connect()) as conn:  # an event that already happened
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, first_seen, last_seen)
                        VALUES ('2026-10-30', 'AAPL', 'Apple', 'earnings', 'Earnings report', 'x', 'x')""")
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 24)]}

    events.scan()

    assert [(e["event_date"], e["kind"]) for e in stored()] == [("2026-10-30", "earnings"), ("2026-11-24", "earnings")]


def test_news_events_stay_after_their_article_drops_out_of_the_feed(cal):
    standard_news()
    cal.reply = standard_reply
    events.scan()
    NEWS.clear()

    result = events.scan()

    assert len(cal.prompts) == 1  # no headlines, so Claude wasn't asked (and cost nothing)
    assert result["cost_usd"] == 0
    assert {e["title"] for e in stored()} == {"Product launch event", "Court hearing in patent case"}


def test_if_claude_fails_the_calendar_dates_are_still_saved(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = lambda prompt: RuntimeError("Claude couldn't read the news: error_max_budget_usd")

    result = events.scan()

    assert result["status"] == "partial"
    assert "news scan: Claude couldn't read the news" in result["message"]
    assert [e["kind"] for e in stored()] == ["earnings"]


def test_one_companys_calendar_failing_keeps_its_saved_dates(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    events.scan()
    CALENDARS["AAPL"] = ConnectionError("Yahoo rate limit")

    result = events.scan()

    assert result["status"] == "partial" and "AAPL calendar: Yahoo rate limit" in result["message"]
    assert [e["event_date"] for e in stored()] == ["2026-11-19"]


@pytest.mark.parametrize("reply", [
    '{"events": []}',
    'Here you go:\n```json\n{"events": []}\n```',
    'Sure. {"events": []} Hope that helps.',
])
def test_claudes_reply_is_read_even_with_extra_text(reply):
    assert events.parse_reply(reply) == []


@pytest.mark.parametrize("reply", ["no json here", '{"items": []}', '{"events": "none"}', "{broken"])
def test_an_unreadable_reply_is_an_error(reply):
    with pytest.raises(ValueError):
        events.parse_reply(reply)


def test_only_one_scan_runs_at_a_time(cal):
    with closing(events.connect()) as conn:
        conn.execute("INSERT INTO event_scans (started_at, trigger, status) VALUES (?, 'scheduled', 'running')",
                     (events._utc_now(),))
    with pytest.raises(events.ScanBusy):
        events.scan()

    # A scan that stopped half-way (the computer slept, say) doesn't block scans for ever
    stuck = (datetime.now(timezone.utc) - events.STUCK_AFTER - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(events.connect()) as conn:
        conn.execute("UPDATE event_scans SET started_at = ?", (stuck,))
    assert events.scan()["status"] == "ok"
    with closing(events.connect()) as conn:
        assert [r[0] for r in conn.execute("SELECT status FROM event_scans ORDER BY id")] == ["failed", "ok"]


def test_the_daily_schedule_skips_days_the_market_is_closed(cal, monkeypatch, capsys):
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "complete", "as_of": "2026-11-06"})
    monkeypatch.setattr(sys, "argv", ["events.py", "scan", "--only-if-open"])

    events.main()

    assert "skipped" in capsys.readouterr().out
    with closing(events.connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM event_scans").fetchone()[0] == 0


def test_command_line_scan_list_show_and_remove(cal, monkeypatch, capsys):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = standard_reply
    for argv in (["scan"], ["list"], ["show", "2026-11-18"]):
        monkeypatch.setattr(sys, "argv", ["events.py", *argv])
        events.main()
    out = capsys.readouterr().out

    assert "ok: 2 news events from 3 headlines, $0.030" in out
    assert "left out: TSLA 'Not on the watchlist': not a watchlist ticker" in out
    assert "2026-11-19  Apple              earnings  Earnings report" in out
    assert "- Example Wire: Apple sets November 18 launch event https://news.example.com/aapl-event" in out

    launch = next(e for e in stored() if e["title"] == "Product launch event")
    monkeypatch.setattr(sys, "argv", ["events.py", "remove", str(launch["id"])])
    events.main()
    assert "Removed." in capsys.readouterr().out
    assert "Product launch event" not in {e["title"] for e in stored()}


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(cal, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "calendar_scans", api.CalendarScanManager())
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for_scan(client):
    for _ in range(100):
        scan = client.get("/api/calendar/scan").json()["scan"]
        if scan["state"] in ("finished", "failed"):
            return scan
        time.sleep(0.05)
    raise AssertionError("the scan didn't finish")


def test_api_calendar_works_before_the_first_scan(client):
    body = client.get("/api/calendar").json()

    assert body["today"] == "2026-11-06" and body["start"] == "2026-11-01" and body["end"] == "2026-12-12"
    assert body["events"] == [] and body["last_scan"] is None and body["scan"]["state"] == "idle"


def test_update_now_scans_and_the_calendar_shows_the_results(client):
    CALENDARS["JPM"] = {"Ex-Dividend Date": date(2026, 11, 10)}
    standard_news()
    events.ask_claude.reply = standard_reply

    started = client.post("/api/calendar/scan", json={})
    scan = wait_for_scan(client)
    body = client.get("/api/calendar?start=2026-11-09&end=2026-11-15").json()

    assert started.status_code == 202 and started.json()["scan"]["state"] == "running"
    assert scan["state"] == "finished" and scan["result"]["events_found"] == 2 and scan["result"]["trigger"] == "manual"
    assert [(e["event_date"], e["company"]) for e in body["events"]] == [("2026-11-10", "JPMorgan Chase"),
                                                                          ("2026-11-12", "NVIDIA")]
    assert body["last_scan"]["status"] == "ok"


def test_update_now_has_a_cooldown_and_runs_one_at_a_time(client, monkeypatch):
    client.post("/api/calendar/scan", json={})
    wait_for_scan(client)
    assert client.post("/api/calendar/scan", json={}).status_code == 429  # cooldown

    monkeypatch.setattr(api, "CALENDAR_SCAN_COOLDOWN_SECONDS", 0)
    slow = events.scan
    monkeypatch.setattr(events, "scan", lambda *args: (time.sleep(0.5), slow(*args))[1])
    assert client.post("/api/calendar/scan", json={}).status_code == 202
    assert client.post("/api/calendar/scan", json={}).status_code == 409  # one at a time
    wait_for_scan(client)


def test_other_websites_cannot_start_a_scan(client):
    assert client.post("/api/calendar/scan", json={}, headers={"Origin": "https://evil.example"}).status_code == 403


@pytest.mark.parametrize("query", [
    "start=11-06-2026", "start=2026-11-10&end=2026-11-01", "start=2026-01-01&end=2026-12-31", "start=2026-02-30",
])
def test_api_calendar_rejects_bad_dates(client, query):
    response = client.get(f"/api/calendar?{query}")
    assert response.status_code == 400 and response.json()["error"]


def test_live_updates_announce_a_scan_from_the_daily_schedule(cal, monkeypatch):
    """The scheduled scan is a separate program, so the API spots it in the database and tells the browser."""
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)  # let the watcher take its first look
        await asyncio.to_thread(events.scan, "scheduled")
        event = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return event

    event = asyncio.run(scenario())

    assert event["type"] == "calendar_updated" and event["scan"]["status"] == "ok"


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_calendar_data(monkeypatch):
    import yfinance

    monkeypatch.setattr(events.yf, "Ticker", yfinance.Ticker)  # real Yahoo Finance
    events._names.clear()
    today = date.today()
    name = events.company_name("AAPL")
    raw = events.fetch_calendar("AAPL")
    found = events.calendar_events("AAPL", name, raw, today, today + timedelta(days=events.HORIZON_DAYS))
    news = events.fetch_news("AAPL")

    assert name == "Apple"
    assert isinstance(events._calendar_dict(raw), dict) and events._calendar_dict(raw), raw
    assert news and news[0]["title"] and news[0]["url"]
    print("\nYahoo's calendar for AAPL:", raw)
    print("Events from it:", [(e["event_date"], e["title"], e["date_note"]) for e in found])
