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
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import market_tools  # noqa: E402
from mcp import Client  # noqa: E402

REAL_TICKER = market_tools.yf.Ticker  # captured before any test patches it

# ---------------------------------------------------------------------------
# Fake market data, shaped like yfinance's real output
# ---------------------------------------------------------------------------

DAYS = 63  # about 3 months of trading days


def calm_returns(seed: int) -> np.ndarray:
    return np.random.default_rng(seed).normal(0, 0.01, DAYS)


FAKE_DATA = {}  # ticker -> (daily returns, daily volumes), or "empty", or "raise"
FAKE_NEWS = {}  # ticker -> list of raw yfinance news items


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period="3mo"):
        spec = FAKE_DATA[self.ticker]
        if spec == "empty":
            return pd.DataFrame(columns=["Close", "Volume"])
        if spec == "raise":
            raise ConnectionError("Yahoo rate limit")
        returns, volumes = spec
        index = pd.bdate_range(end="2026-11-02", periods=DAYS, tz="America/New_York")
        close = 100 * np.cumprod(1 + returns)
        return pd.DataFrame({"Close": close, "Volume": volumes}, index=index)

    @property
    def news(self):
        return FAKE_NEWS.get(self.ticker, [])


@pytest.fixture(autouse=True)
def fake_market(monkeypatch, tmp_path):
    """Swap in fake data and a test watchlist for every test."""
    FAKE_DATA.clear()
    FAKE_NEWS.clear()
    monkeypatch.setattr(market_tools.yf, "Ticker", FakeTicker)
    watchlist = tmp_path / "watchlist.txt"
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    return watchlist


def normal_volume():
    return np.full(DAYS, 1_000_000.0)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_watchlist_skips_comments_blanks_and_uppercases(fake_market):
    fake_market.write_text("# my list\naapl\n\n  msft  \n#NVDA\n")
    assert market_tools.load_watchlist() == ["AAPL", "MSFT"]


def test_zscore_matches_independent_calculation():
    returns = calm_returns(1)
    returns[-1] = 0.04
    FAKE_DATA["TEST"] = (returns, normal_volume())

    result = market_tools.compute_moves("TEST")

    # Recompute by hand: today's return vs. the baseline of the days *before* today
    r = pd.Series(100 * np.cumprod(1 + returns)).pct_change().dropna()
    expected_z = (r.iloc[-1] - r.iloc[:-1].mean()) / r.iloc[:-1].std()
    assert result["return_zscore"] == pytest.approx(expected_z, abs=0.01)
    assert result["return_1d_pct"] == pytest.approx(4.0, abs=0.01)
    assert result["volume_vs_avg"] == pytest.approx(1.0)
    assert result["as_of"] == "2026-11-02"


def test_big_move_is_flagged_and_calm_ticker_is_quiet(fake_market):
    fake_market.write_text("NVDA\nAAPL\n")
    spike = calm_returns(2)
    spike[-1] = 0.07
    FAKE_DATA["NVDA"] = (spike, normal_volume())
    FAKE_DATA["AAPL"] = (calm_returns(3) * 0.1, normal_volume())

    result = market_tools.flag_events()

    assert [m["ticker"] for m in result["flagged"]] == ["NVDA"]
    assert [q["ticker"] for q in result["quiet"]] == ["AAPL"]
    assert result["errors"] == []


def test_volume_spike_alone_is_flagged(fake_market):
    fake_market.write_text("JPM\n")
    returns = calm_returns(4) * 0.1  # tiny price moves
    volumes = normal_volume()
    volumes[-1] = 3_000_000  # 3x average volume
    FAKE_DATA["JPM"] = (returns, volumes)

    result = market_tools.flag_events()

    assert result["flagged"][0]["ticker"] == "JPM"
    assert result["flagged"][0]["volume_vs_avg"] == pytest.approx(3.0)


def test_thresholds_control_flagging(fake_market):
    fake_market.write_text("AAPL\n")
    FAKE_DATA["AAPL"] = (calm_returns(5), normal_volume())

    assert len(market_tools.flag_events(z_threshold=0.0)["flagged"]) == 1   # everything flags
    assert len(market_tools.flag_events(z_threshold=99.0)["flagged"]) == 0  # nothing flags


def test_bad_tickers_are_reported_not_fatal(fake_market):
    fake_market.write_text("GOOD\nNODATA\nBROKEN\n")
    FAKE_DATA["GOOD"] = (calm_returns(6), normal_volume())
    FAKE_DATA["NODATA"] = "empty"
    FAKE_DATA["BROKEN"] = "raise"

    result = market_tools.flag_events()

    errors = {e["ticker"]: e["error"] for e in result["errors"]}
    assert errors["NODATA"] == "not enough price history"
    assert "rate limit" in errors["BROKEN"]
    assert len(result["flagged"]) + len(result["quiet"]) == 1


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
    FAKE_DATA["NVDA"] = (spike, normal_volume())

    async def run():
        async with Client(market_tools.mcp) as client:
            tools = await client.list_tools()
            result = await client.call_tool("flag_events", {})
            return {t.name for t in tools.tools}, result

    names, result = asyncio.run(run())

    assert names == {"flag_events", "compute_moves", "get_news"}
    assert not result.is_error
    payload = json.loads(result.content[0].text)  # the JSON text the agent receives
    assert payload["flagged"][0]["ticker"] == "NVDA"


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_data(monkeypatch):
    monkeypatch.setattr(market_tools.yf, "Ticker", REAL_TICKER)  # undo the fake
    result = market_tools.compute_moves("AAPL")

    assert "error" not in result, result
    assert result["last_close"] > 0
    assert -50 < result["return_1d_pct"] < 50
    print("\nLive AAPL:", result)
