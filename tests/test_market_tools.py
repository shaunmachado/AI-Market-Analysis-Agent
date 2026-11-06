"""Offline tests for market_tools.py. No internet or API key needed.

Run from the project folder:
    pip install pytest
    pytest -v

Live-data check (needs internet, hits Yahoo Finance):
    LIVE_TESTS=1 pytest -v -s -k live        (Windows PowerShell: $env:LIVE_TESTS=1; pytest -v -s -k live)
"""

import asyncio
import json
import os
import sys
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import market_tools  # noqa: E402
from mcp import Client  # noqa: E402

REAL_TICKER = market_tools.yf.Ticker  # saved before the fixture swaps in the fake

ET = ZoneInfo("America/New_York")
FRIDAY = date(2026, 11, 6)
DAYS = 63  # about 3 months of trading days

# ---------------------------------------------------------------------------
# Fake market data, shaped like yfinance's real output
# ---------------------------------------------------------------------------

FAKE_DAILY = {}     # ticker -> (daily returns, daily volumes), a DataFrame, "empty" or "raise"
FAKE_INTRADAY = {}  # ticker -> DataFrame of 5-minute bars
FAKE_NEWS = {}      # ticker -> list of raw yfinance news items


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period="3mo", interval="1d"):
        if interval != "1d":
            return FAKE_INTRADAY.get(self.ticker, pd.DataFrame(columns=["Close", "Volume"])).copy()
        spec = FAKE_DAILY[self.ticker]
        if isinstance(spec, pd.DataFrame):
            return spec.copy()
        if spec == "empty":
            return pd.DataFrame(columns=["Close", "Volume"])
        if spec == "raise":
            raise ConnectionError("Yahoo rate limit")
        returns, volumes = spec
        index = pd.bdate_range(end=FRIDAY, periods=DAYS, tz=ET)
        close = 100 * np.cumprod(1 + returns)
        return pd.DataFrame({"Close": close, "Volume": volumes}, index=index)

    @property
    def news(self):
        return FAKE_NEWS.get(self.ticker, [])


def calm_returns(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 0.01, DAYS)


def normal_volume():
    return np.full(DAYS, 1_000_000.0)


def bars(day: date, until: str = "15:55") -> pd.DataFrame:
    """Flat 5-minute bars for one session, 9:30 up to `until`."""
    times = pd.date_range(f"{day} 09:30", f"{day} {until}", freq="5min", tz=ET)
    return pd.DataFrame({"Close": 100.0, "Volume": 1.0}, index=times)


def set_clock(monkeypatch, day: date, hhmm: str):
    when = datetime.combine(day, time.fromisoformat(hhmm), ET)
    monkeypatch.setattr(market_tools, "now_et", lambda: when)


def set_spy(*sessions):
    """SPY's 5-minute bars, which decide whether the market is open. Pass (day, until) pairs."""
    FAKE_INTRADAY["SPY"] = pd.concat([bars(day, until) for day, until in sessions])


def open_market(monkeypatch, cutoff: str = "11:30"):
    """Friday, mid-session: the clock is 2 minutes after SPY's latest bar."""
    set_spy((FRIDAY - timedelta(days=1), "15:55"), (FRIDAY, cutoff))
    later = (datetime.combine(FRIDAY, time.fromisoformat(cutoff)) + timedelta(minutes=2)).strftime("%H:%M")
    set_clock(monkeypatch, FRIDAY, later)


def fake_open_market(ticker, today_move, volume_mult=1.0, cutoff="11:30", past_days=20, seed=0, half_days=()):
    """Fake both feeds for a ticker on Friday mid-session.

    5-minute bars: `past_days` full sessions (or 9:30-12:55 for `half_days`) plus today
    up to `cutoff`, where the price ends exactly `today_move` above Thursday's close.
    Every bar has the same volume (times `volume_mult` today).
    Daily bars: 45 older sessions flat at 100, then one row per fake session. The last
    row is today's partial session, as Yahoo shows it during trading hours.
    """
    rng = np.random.default_rng(seed)
    days = [d.date() for d in pd.bdate_range(end=FRIDAY, periods=past_days + 1)]
    price, frames, rows = 100.0, [], []
    for day in days:
        until = cutoff if day == FRIDAY else ("12:55" if day in half_days else "15:55")
        times = pd.date_range(f"{day} 09:30", f"{day} {until}", freq="5min", tz=ET)
        if day == FRIDAY:
            closes = np.linspace(price, price * (1 + today_move), len(times) + 1)[1:]
            volumes = np.full(len(times), 10_000.0 * volume_mult)
        else:
            closes = price * np.cumprod(1 + rng.normal(0, 0.001, len(times)))
            volumes = np.full(len(times), 10_000.0)
        frames.append(pd.DataFrame({"Close": closes, "Volume": volumes}, index=times))
        rows.append((day, closes[-1], volumes.sum()))
        price = closes[-1]
    FAKE_INTRADAY[ticker] = pd.concat(frames)

    older = [d.date() for d in pd.bdate_range(end=days[0] - timedelta(days=1), periods=45)]
    rows = [(d, 100.0, 780_000.0) for d in older] + rows
    index = pd.DatetimeIndex([pd.Timestamp(d) for d, _, _ in rows]).tz_localize(ET)
    FAKE_DAILY[ticker] = pd.DataFrame({"Close": [r[1] for r in rows], "Volume": [r[2] for r in rows]}, index=index)


@pytest.fixture(autouse=True)
def fake_market(monkeypatch, tmp_path):
    """Fake data, a test watchlist and a fake clock for every test.

    Default: Saturday morning, so the market is closed and Friday is the last session.
    """
    FAKE_DAILY.clear()
    FAKE_INTRADAY.clear()
    FAKE_NEWS.clear()
    monkeypatch.setattr(market_tools.yf, "Ticker", FakeTicker)
    watchlist = tmp_path / "watchlist.txt"
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    set_spy((FRIDAY, "15:55"))
    set_clock(monkeypatch, FRIDAY + timedelta(days=1), "10:00")
    return watchlist


# ---------------------------------------------------------------------------
# Market open or closed?
# ---------------------------------------------------------------------------

THANKSGIVING = date(2026, 11, 26)
DAY_AFTER_THANKSGIVING = date(2026, 11, 27)  # NYSE closes early, at 1pm


@pytest.mark.parametrize("clock_day, clock_time, spy_sessions, expected", [
    pytest.param(FRIDAY + timedelta(days=1), "10:00", [(FRIDAY, "15:55")],
                 {"status": "complete", "as_of": "2026-11-06"}, id="weekend"),
    pytest.param(FRIDAY, "11:32", [(FRIDAY, "11:30")],
                 {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"}, id="market-open"),
    pytest.param(FRIDAY, "08:00", [(FRIDAY - timedelta(days=1), "15:55")],
                 {"status": "complete", "as_of": "2026-11-05"}, id="pre-market"),
    pytest.param(FRIDAY, "16:10", [(FRIDAY, "15:55")],
                 {"status": "complete", "as_of": "2026-11-06"}, id="after-close"),
    pytest.param(THANKSGIVING, "11:00", [(THANKSGIVING - timedelta(days=1), "15:55")],
                 {"status": "complete", "as_of": "2026-11-25"}, id="holiday"),
    pytest.param(DAY_AFTER_THANKSGIVING, "14:00", [(DAY_AFTER_THANKSGIVING, "12:55")],
                 {"status": "complete", "as_of": "2026-11-27"}, id="after-early-close"),
    pytest.param(DAY_AFTER_THANKSGIVING, "11:02", [(DAY_AFTER_THANKSGIVING, "11:00")],
                 {"status": "in_progress", "as_of": "2026-11-27 11:00 ET"}, id="during-half-day"),
])
def test_market_session(monkeypatch, clock_day, clock_time, spy_sessions, expected):
    set_spy(*spy_sessions)
    set_clock(monkeypatch, clock_day, clock_time)
    assert market_tools.market_session() == expected


# ---------------------------------------------------------------------------
# Market closed: last completed session vs. 3 months of daily moves
# ---------------------------------------------------------------------------

def test_watchlist_skips_comments_blanks_and_uppercases(fake_market):
    fake_market.write_text("# my list\naapl\n\n  msft  \n#NVDA\n")
    assert market_tools.load_watchlist() == ["AAPL", "MSFT"]


def test_zscore_matches_independent_calculation():
    returns = calm_returns(1)
    returns[-1] = 0.04
    FAKE_DAILY["TEST"] = (returns, normal_volume())

    result = market_tools.compute_moves("TEST")

    # Recompute by hand: the session's return vs. the baseline of the days *before* it
    r = pd.Series(100 * np.cumprod(1 + returns)).pct_change().dropna()
    expected_z = (r.iloc[-1] - r.iloc[:-1].mean()) / r.iloc[:-1].std()
    assert result["session"] == "complete"
    assert result["return_zscore"] == pytest.approx(expected_z, abs=0.01)
    assert result["return_1d_pct"] == pytest.approx(4.0, abs=0.01)
    assert result["volume_vs_avg"] == pytest.approx(1.0)
    assert result["as_of"] == "2026-11-06"


def test_big_move_is_flagged_and_calm_ticker_is_quiet(fake_market):
    fake_market.write_text("NVDA\nAAPL\n")
    spike = calm_returns(2)
    spike[-1] = 0.07
    FAKE_DAILY["NVDA"] = (spike, normal_volume())
    FAKE_DAILY["AAPL"] = (calm_returns(3) * 0.1, normal_volume())

    result = market_tools.flag_events()

    assert result["session"]["status"] == "complete"
    assert [m["ticker"] for m in result["flagged"]] == ["NVDA"]
    assert [q["ticker"] for q in result["quiet"]] == ["AAPL"]
    assert result["errors"] == []


def test_volume_spike_alone_is_flagged(fake_market):
    fake_market.write_text("JPM\n")
    returns = calm_returns(4) * 0.1  # tiny price moves
    volumes = normal_volume()
    volumes[-1] = 3_000_000  # 3x average volume
    FAKE_DAILY["JPM"] = (returns, volumes)

    result = market_tools.flag_events()

    assert result["flagged"][0]["ticker"] == "JPM"
    assert result["flagged"][0]["volume_vs_avg"] == pytest.approx(3.0)


def test_thresholds_control_flagging(fake_market):
    fake_market.write_text("AAPL\n")
    FAKE_DAILY["AAPL"] = (calm_returns(5), normal_volume())

    assert len(market_tools.flag_events(z_threshold=0.0)["flagged"]) == 1   # everything flags
    assert len(market_tools.flag_events(z_threshold=99.0)["flagged"]) == 0  # nothing flags


def test_bad_tickers_are_reported_not_fatal(fake_market):
    fake_market.write_text("GOOD\nNODATA\nBROKEN\n")
    FAKE_DAILY["GOOD"] = (calm_returns(6), normal_volume())
    FAKE_DAILY["NODATA"] = "empty"
    FAKE_DAILY["BROKEN"] = "raise"

    result = market_tools.flag_events()

    errors = {e["ticker"]: e["error"] for e in result["errors"]}
    assert errors["NODATA"] == "not enough price history"
    assert "rate limit" in errors["BROKEN"]
    assert len(result["flagged"]) + len(result["quiet"]) == 1


def test_premarket_ignores_todays_unfinished_row(monkeypatch):
    """Before the open, a row for today must not be treated as a finished session."""
    fake_open_market("TEST", today_move=0.05)  # daily data includes a partial Friday row
    set_spy((FRIDAY - timedelta(days=1), "15:55"))
    set_clock(monkeypatch, FRIDAY, "08:00")

    result = market_tools.compute_moves("TEST")

    assert result["session"] == "complete"
    assert result["as_of"] == "2026-11-05"  # Thursday, the last finished session


# ---------------------------------------------------------------------------
# Market open: today so far vs. the same time of day in past sessions
# ---------------------------------------------------------------------------

def test_intraday_zscore_matches_independent_calculation(monkeypatch):
    open_market(monkeypatch, cutoff="11:30")
    fake_open_market("TEST", today_move=0.03)

    result = market_tools.compute_moves("TEST")

    # Recompute by hand: each past session's return from its previous close to 11:30
    intraday, daily = FAKE_INTRADAY["TEST"], FAKE_DAILY["TEST"]
    closes = {ts.date(): c for ts, c in zip(daily.index, daily["Close"])}
    sessions = sorted(closes)
    past = []
    for day in sorted(set(intraday.index.date) - {FRIDAY}):
        prev = closes[sessions[sessions.index(day) - 1]]
        at_cutoff = intraday[(intraday.index.date == day) & (intraday.index.time <= time(11, 30))]
        past.append(at_cutoff["Close"].iloc[-1] / prev - 1)
    expected_z = (0.03 - np.mean(past)) / np.std(past, ddof=1)

    assert result["session"] == "in_progress"
    assert result["as_of"] == "2026-11-06 11:30 ET"
    assert result["return_1d_pct"] == pytest.approx(3.0, abs=0.01)
    assert result["return_zscore"] == pytest.approx(expected_z, abs=0.01)
    assert result["compared_to"] == "the same time of day over the last 20 sessions"


def test_intraday_normal_volume_is_not_counted_as_a_low_day(monkeypatch):
    """The partial-day problem: by 11:30 only ~a third of a day's volume has traded.
    Compared with full days that reads as 0.32x. Compared with the same time of day
    it correctly reads as normal (1.0x)."""
    open_market(monkeypatch, cutoff="11:30")
    fake_open_market("TEST", today_move=0.001, volume_mult=1.0)

    result = market_tools.compute_moves("TEST")

    assert result["volume_vs_avg"] == pytest.approx(1.0)


def test_intraday_flags_movers_and_volume_spikes(monkeypatch, fake_market):
    open_market(monkeypatch, cutoff="13:00")
    fake_market.write_text("MOVER\nBUSY\nCALM\n")
    fake_open_market("MOVER", today_move=0.04, cutoff="13:00", seed=1)
    fake_open_market("BUSY", today_move=0.001, volume_mult=3.0, cutoff="13:00", seed=2)
    fake_open_market("CALM", today_move=0.001, cutoff="13:00", seed=3)

    result = market_tools.flag_events()

    assert result["session"] == {"status": "in_progress", "as_of": "2026-11-06 13:00 ET"}
    flagged = {m["ticker"]: m for m in result["flagged"]}
    assert set(flagged) == {"MOVER", "BUSY"}
    assert flagged["BUSY"]["volume_vs_avg"] == pytest.approx(3.0)
    assert [q["ticker"] for q in result["quiet"]] == ["CALM"]


def test_intraday_skips_past_half_days_that_closed_before_this_time(monkeypatch):
    """A past early-close session (ended 12:55) can't be compared at 14:00, so it's left out."""
    open_market(monkeypatch, cutoff="14:00")
    fake_open_market("TEST", today_move=0.01, cutoff="14:00", half_days=(date(2026, 10, 30),))

    result = market_tools.compute_moves("TEST")

    assert "error" not in result
    assert result["compared_to"] == "the same time of day over the last 19 sessions"


def test_intraday_needs_enough_history(monkeypatch):
    open_market(monkeypatch)
    fake_open_market("NEWIPO", today_move=0.02, past_days=5)

    assert market_tools.compute_moves("NEWIPO") == {"ticker": "NEWIPO", "error": "not enough intraday history"}


# ---------------------------------------------------------------------------
# News and MCP
# ---------------------------------------------------------------------------

def test_news_handles_both_yfinance_formats_and_caps_limit():
    new_format = {"id": "1", "content": {
        "title": "Beats estimates", "pubDate": "2026-11-02T13:00:00Z",
        "provider": {"displayName": "Reuters"},
        "canonicalUrl": {"url": "https://example.com/a"}, "summary": "x" * 500}}
    old_format = {"title": "Old headline", "publisher": "AP",
                  "link": "https://example.com/b", "providerPublishTime": 1762000000}
    FAKE_NEWS["NVDA"] = [new_format, old_format] * 10

    news = market_tools.get_news(" nvda ", limit=50)

    assert len(news) == 10  # capped
    assert news[0] == {"title": "Beats estimates", "publisher": "Reuters",
                       "published": "2026-11-02T13:00:00Z",
                       "url": "https://example.com/a", "summary": "x" * 300}
    assert news[1]["publisher"] == "AP"
    assert news[1]["url"] == "https://example.com/b"


def test_tools_work_through_mcp(fake_market):
    """Same calls the agent makes, through a real MCP client (in-process)."""
    fake_market.write_text("NVDA\n")
    spike = calm_returns(7)
    spike[-1] = 0.07
    FAKE_DAILY["NVDA"] = (spike, normal_volume())

    async def run():
        async with Client(market_tools.mcp) as client:
            tools = await client.list_tools()
            result = await client.call_tool("flag_events", {})
            return {t.name for t in tools.tools}, result

    names, result = asyncio.run(run())

    assert names == {"flag_events", "compute_moves", "get_news"}
    assert not result.is_error
    payload = json.loads(result.content[0].text)  # the JSON text the agent receives
    assert payload["session"]["status"] == "complete"
    assert payload["flagged"][0]["ticker"] == "NVDA"


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_data(monkeypatch):
    monkeypatch.setattr(market_tools.yf, "Ticker", REAL_TICKER)  # undo the fake data
    monkeypatch.setattr(market_tools, "now_et", lambda: datetime.now(ET))  # undo the fake clock
    session = market_tools.market_session()
    result = market_tools.compute_moves("AAPL")

    assert "error" not in result, result
    assert (result.get("last_close") or result.get("last_price")) > 0
    assert -50 < result["return_1d_pct"] < 50
    print("\nLive session:", session)
    print("Live AAPL:", result)
