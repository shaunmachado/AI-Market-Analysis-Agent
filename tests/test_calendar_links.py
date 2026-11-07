"""Offline tests for the events calendar's links to briefs, Discord alerts and Ask.

Run from the project folder:
    pytest -v tests/test_calendar_links.py
"""

import asyncio
import json
import sys
from contextlib import closing
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import ask  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
from mcp import Client  # noqa: E402

ET = ZoneInfo("America/New_York")
TODAY = date(2026, 11, 6)  # a Friday


def add(day, ticker, company, kind, title, date_note=None):
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, date_note, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, 'x', 'x')""", (day, ticker, company, kind, title, date_note))


def calendar_updated():
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO event_scans (started_at, finished_at, trigger, status)
                        VALUES ('2026-11-06T14:35:00Z', '2026-11-06T14:35:09Z', 'scheduled', 'ok')""")


@pytest.fixture
def cal(tmp_path, monkeypatch):
    """A temporary database and watchlist, and the clock set to Friday 6 November 2026, 10am."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    watchlist = tmp_path / "watchlist.txt"
    watchlist.write_text("AAPL\nMSFT\nNVDA\nJPM\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    monkeypatch.setattr(market_tools, "now_et", lambda: datetime.combine(TODAY, time(10, 0), ET))
    monkeypatch.setattr(events, "today_et", lambda: TODAY)


@pytest.fixture
def filled(cal):
    calendar_updated()
    add("2026-11-05", "AMZN", "Amazon.com", "earnings", "Earnings report")         # yesterday
    add("2026-11-06", "AAPL", "Apple", "dividend", "Ex-dividend date")             # today
    add("2026-11-09", "MSFT", "Microsoft", "news", "Court hearing in patent case")
    add("2026-11-16", "NVDA", "NVIDIA", "earnings", "Earnings report (date not confirmed)",
        "Estimated: Yahoo Finance shows a window of Nov 16 to Nov 20.")
    add("2026-11-19", "JPM", "JPMorgan Chase", "news", "Investor day")
    add("2026-11-25", "MSFT", "Microsoft", "news", "Shareholder vote")             # 19 days away
    add("2026-11-10", "TSLA", "Tesla", "news", "Not on the watchlist")


# ---------------------------------------------------------------------------
# The brief: the upcoming_events tool
# ---------------------------------------------------------------------------

def test_upcoming_events_lists_the_next_two_weeks_for_the_watchlist(filled):
    result = market_tools.upcoming_events()

    assert result["from"] == "2026-11-06" and result["to"] == "2026-11-20"
    assert [(e["date"], e["ticker"], e["days_away"]) for e in result["events"]] == [
        ("2026-11-06", "AAPL", 0), ("2026-11-09", "MSFT", 3), ("2026-11-16", "NVDA", 10), ("2026-11-19", "JPM", 13)]
    assert result["this_week"] == ["Fri Nov 6: Apple (AAPL): Ex-dividend date",
                                   "Mon Nov 9: Microsoft (MSFT): Court hearing in patent case"]
    nvda = result["events"][2]
    assert nvda["confirmed"] is False and nvda["line"] == "Mon Nov 16: NVIDIA (NVDA): Earnings report (date not confirmed)"
    assert result["calendar_updated"] == "2026-11-06T14:35:09Z" and "note" not in result


def test_upcoming_events_for_one_ticker_and_a_longer_range(filled):
    msft = market_tools.upcoming_events(" msft ", days=30)
    assert [e["date"] for e in msft["events"]] == ["2026-11-09", "2026-11-25"]
    assert market_tools.upcoming_events(days=500)["to"] == "2027-01-05"  # capped at 60 days
    assert market_tools.upcoming_events(days=0)["to"] == "2026-11-07"    # at least 1


def test_upcoming_events_before_the_calendar_exists(cal):
    result = market_tools.upcoming_events()
    assert result["events"] == [] and result["this_week"] == [] and result["calendar_updated"] is None
    assert "hasn't been filled in yet" in result["note"]


def test_upcoming_events_through_mcp(filled):
    async def call():
        async with Client(market_tools.mcp) as client:
            return await client.call_tool("upcoming_events", {"ticker": "JPM"})

    result = asyncio.run(call())

    assert not result.is_error
    assert [e["title"] for e in json.loads(result.content[0].text)["events"]] == ["Investor day"]


def test_the_brief_has_a_coming_up_section():
    prompt = (Path(market_tools.__file__).parent / "analyst_prompt.md").read_text()
    assert "## Coming up" in prompt and "upcoming_events.this_week" in prompt
    assert "Don't say the event caused the move unless the news says so." in prompt


def test_search_leaves_out_the_coming_up_section():
    """Otherwise a search for "earnings" would find the days before each earnings date."""
    import search_index
    body = ("# Watchlist brief: 2026-11-06\n\n## Market backdrop\n\nThe S&P 500 rose.\n\n## Quiet\n\nAAPL (+0.2%)\n\n"
            "## Coming up\n\n- Mon Nov 16: NVIDIA (NVDA): Earnings report\n")
    passages = search_index.chunk_report({"title": "Watchlist brief: 2026-11-06", "status": "final", "body_md": body})

    assert len(passages) == 1 and "The S&P 500 rose." in passages[0]["text"]
    assert "Earnings report" not in passages[0]["text"] and "Coming up" not in passages[0]["text"]


# ---------------------------------------------------------------------------
# Discord alerts
# ---------------------------------------------------------------------------

def save_report(status, flagged=("NVDA",)):
    as_of = "2026-11-06" if status == "final" else "2026-11-06 12:30 ET"
    scan = {"session": {"status": "complete" if status == "final" else "in_progress", "as_of": as_of},
            "flagged": [{"ticker": t, "last_price": 100.0, "return_1d_pct": -4.0, "return_zscore": -3.0,
                         "volume_vs_avg": 2.0} for t in flagged],
            "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.2}], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date="2026-11-06", status=status, title="Watchlist brief: 2026-11-06",
                               body_md="# Watchlist brief", as_of=as_of, scan=scan)


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/secret")
    messages = []
    monkeypatch.setattr(alerts, "send", lambda payload: messages.append(payload) or "1")
    return messages


def test_daily_summary_lists_the_coming_week(filled, sent):
    save_report("final")
    alerts.notify("2026-11-06")
    text = sent[0]["embeds"][0]["description"]

    # Only the 7 days after the report's day, and only watchlist companies (not Tesla on Nov 10)
    assert text.endswith("**Coming up:**\n• Mon Nov 9: Microsoft (MSFT): Court hearing in patent case")


def test_daily_summary_caps_the_list(cal, sent):
    calendar_updated()
    for day in range(7, 14):  # 7 events in the coming week
        add(f"2026-11-{day:02d}", "MSFT", "Microsoft", "news", f"Event {day}")
    save_report("final")
    alerts.notify("2026-11-06")
    text = sent[0]["embeds"][0]["description"]

    assert text.count("• ") == alerts.MAX_COMING_UP and "…and 1 more on the calendar" in text


def test_a_flag_card_mentions_the_tickers_next_event(filled, sent):
    save_report("intraday", flagged=("NVDA", "MSFT"))
    alerts.notify("2026-11-06")
    cards = {e["title"].split()[0]: e["description"] for e in sent[0]["embeds"]}

    assert "**Coming up:** Mon Nov 16: Earnings report (date not confirmed)" in cards["NVDA"]
    assert "**Coming up:** Mon Nov 9: Court hearing in patent case" in cards["MSFT"]  # its soonest, not Nov 25


def test_alerts_work_without_a_calendar(cal, sent):
    save_report("intraday")
    alerts.notify("2026-11-06")
    assert "Coming up" not in sent[0]["embeds"][0]["description"]


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

def test_ask_sees_the_calendar(filled):
    with closing(reports_db.connect(readonly=True)) as conn:
        context = ask.calendar_section(conn, ["AMZN"])

    assert context.startswith("## Events calendar (today is Fri 2026-11-06)")
    assert "- 2026-11-16 Mon Nov 16: NVIDIA (NVDA): Earnings report (date not confirmed)" in context
    assert "- 2026-11-25 Wed Nov 25: Microsoft (MSFT): Shareholder vote" in context  # 30 days ahead
    assert "In the last 30 days, for AMZN:\n- 2026-11-05 Thu Nov 5: Amazon.com (AMZN): Earnings report" in context


def test_ask_includes_the_calendar_in_its_context(filled):
    save_report("final")
    with closing(reports_db.connect(readonly=True)) as conn:
        context, _ = ask.build_context(conn, "What's coming up next week?")
    assert "## Events calendar" in context and "Court hearing in patent case" in context
    assert "(calendar)" in ask.SYSTEM_PROMPT


def test_ask_without_a_calendar_has_no_calendar_section(cal):
    with closing(reports_db.connect(readonly=True)) as conn:
        assert ask.calendar_section(conn, ["NVDA"]) == ""
