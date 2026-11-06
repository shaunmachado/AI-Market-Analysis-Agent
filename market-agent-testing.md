# Market Analyst Agent: Testing Guide

How to test the market analyst agent, from quick offline checks to full runs with Claude. This goes with `market-agent-guide.md`: build the project from that guide first.

---

## Contents

1. [Testing strategy](#1-testing-strategy)
2. [Create the test file](#2-create-the-test-file)
3. [Run the offline tests](#3-run-the-offline-tests)
4. [Live data check](#4-live-data-check)
5. [Manual tool check with the MCP Inspector](#5-manual-tool-check-with-the-mcp-inspector)
6. [Agent test runs](#6-agent-test-runs)
7. [Schedule test](#7-schedule-test)
8. [Week-one quality log](#8-week-one-quality-log)
9. [Testing a new tool](#9-testing-a-new-tool)
10. [Troubleshooting the tests](#10-troubleshooting-the-tests)
11. [Appendix: test file source](#appendix-test-file-source)

---

## 1. Testing strategy

Test in layers, from fastest to slowest. Each layer catches a different kind of problem, so when something breaks you know where to look.

| Layer | What it checks | Needs | When to run it |
|---|---|---|---|
| Offline tests | The math and error handling in your tools | Nothing | After every code change |
| Live data check | yfinance is actually returning real data | Internet | Once at setup, then if data looks wrong |
| MCP Inspector | The tools work the way Claude will see them | Node.js, internet | After changing a tool |
| Agent test runs | Claude uses the tools well and writes a good brief | API key (uses credits) | After changing the prompt or tools |
| Schedule test | The scheduled job actually runs | Cron or Task Scheduler | Once, when setting up the schedule |
| Quality log | The briefs are useful over time | Your judgment | Daily for the first week |

**Where the problem is, by which layer fails:**

| Fails | Passes | Problem is in |
|---|---|---|
| Offline tests | — | Your tool code (`market_tools.py`) |
| Live data check | Offline tests | The data source: network, rate limits or yfinance version |
| Agent test run | Live data and Inspector | The prompt (`analyst_prompt.md`) or the agent settings (`run_brief.py`) |
| Schedule test | Manual agent run | The scheduler: paths, API key or computer asleep |

---

## 2. Create the test file

1. In the `market-agent` folder, create a folder named `tests`.
2. Inside it, create a file named `test_market_tools.py`.
3. Paste in the code from the [appendix](#appendix-test-file-source).

Your project should now look like this:

```
market-agent/
├── market_tools.py
├── run_brief.py
├── analyst_prompt.md
├── watchlist.txt
├── requirements.txt
└── tests/
    └── test_market_tools.py
```

**How the tests work:** they swap yfinance for a fake that returns made-up price and news data in the same shape as the real thing. They also use a temporary watchlist, so your real `watchlist.txt` is never touched. Results are the same every run, with no internet or API key needed.

---

## 3. Run the offline tests

With your virtual environment active, from the `market-agent` folder:

```bash
pip install pytest
pytest -v
```

**Expected result:** `8 passed, 1 skipped`. The skipped test is the live data check in step 4.

**What each test proves:**

| Test | Proves that |
|---|---|
| `test_watchlist_skips_comments_blanks_and_uppercases` | `watchlist.txt` is read correctly: comments and blank lines ignored, tickers uppercased |
| `test_zscore_matches_independent_calculation` | The z-score matches a separate hand calculation, and today's move isn't included in its own baseline |
| `test_big_move_is_flagged_and_calm_ticker_is_quiet` | A big price move gets flagged and a calm ticker lands in "quiet" |
| `test_volume_spike_alone_is_flagged` | A volume spike gets flagged even when the price barely moved |
| `test_thresholds_control_flagging` | Threshold 0 flags everything; threshold 99 flags nothing |
| `test_bad_tickers_are_reported_not_fatal` | Missing data and connection errors are reported per ticker without stopping the scan |
| `test_news_handles_both_yfinance_formats_and_caps_limit` | Both yfinance news formats are read, summaries are trimmed and results are capped at 10 |
| `test_tools_work_through_mcp` | The tools work through a real MCP client, the same way the agent calls them |
| `test_live_data` | Real data comes back from Yahoo Finance (skipped unless you turn it on) |

**Tip:** to check the tests can catch real bugs, temporarily change `baseline = returns.iloc[:-1]` to `baseline = returns` in `market_tools.py` and run `pytest` again. The z-score test should fail. Change it back afterwards.

---

## 4. Live data check

This fetches real AAPL data from Yahoo Finance and prints it.

**macOS / Linux**

```bash
LIVE_TESTS=1 pytest -v -s -k live
```

**Windows (PowerShell)**

```powershell
$env:LIVE_TESTS=1; pytest -v -s -k live
```

**Expected result:** `1 passed`, plus a printed line like `Live AAPL: {'ticker': 'AAPL', 'last_close': ...}`.

**Then check by eye:**

- [ ] `last_close` matches Yahoo Finance or your broker for that date
- [ ] `as_of` is the most recent trading day
- [ ] `return_1d_pct` matches the day's percentage change

If the offline tests pass but this fails, the problem is the data source, not your code. See [troubleshooting](#10-troubleshooting-the-tests).

Run this outside market hours. During trading hours yfinance includes the current partial day, so the numbers won't match end-of-day figures.

---

## 5. Manual tool check with the MCP Inspector

The Inspector lets you call each tool by hand with live data, seeing exactly what Claude will receive. It needs Node.js.

```bash
npx @modelcontextprotocol/inspector python market_tools.py
```

It opens in your browser. Click **Connect**, open the **Tools** tab, and try each tool:

| Tool | Try with | Check that |
|---|---|---|
| `flag_events` | default arguments | Every watchlist ticker appears in `flagged`, `quiet` or `errors` |
| `flag_events` | `z_threshold` = 0 | Every ticker is flagged |
| `compute_moves` | `AAPL` | Numbers match the live data check |
| `compute_moves` | `ZZZZ123` | Returns `not enough price history` instead of crashing |
| `get_news` | a ticker that moved recently | Headlines are recent, links work, publishers are filled in |

Also check that each tool's description reads clearly. Claude uses those descriptions to decide which tool to call.

---

## 6. Agent test runs

### 6.1 Set up a cheap test

1. Copy `watchlist.txt` to `watchlist.backup.txt`.
2. Cut `watchlist.txt` down to 2–3 tickers, ideally including one that moved a lot recently.
3. In `run_brief.py`, change `max_budget_usd=1.00` to `max_budget_usd=0.25`.

### 6.2 Run it

```bash
python run_brief.py
```

**Expected output:** a line for each tool call (`-> mcp__market__flag_events {}` first), then `Saved briefs/YYYY-MM-DD.md (N turns, $X.XXX)`.

**Check the tool calls in that output:**

- [ ] `flag_events` is called first
- [ ] `get_news` is called for each flagged ticker
- [ ] No unnecessary repeated calls

### 6.3 Check the brief

Straight after the run, call `flag_events` in the Inspector and compare it with the brief.

- [ ] Every number in the brief matches a tool result exactly
- [ ] Every ticker from the watchlist appears (in "Notable moves", "Quiet today" or "Data issues")
- [ ] Every "Likely why" has a link, and the article actually says that
- [ ] "No clear catalyst found" is used when the news doesn't explain a move
- [ ] No buy/sell recommendations or advice language
- [ ] The format matches the template in `analyst_prompt.md`

If a number doesn't match a tool result, Claude made it up. Tighten the rules in `analyst_prompt.md` and re-test.

### 6.4 Force each path

Each scenario tests a different part of the brief. Make the change, run `python run_brief.py`, check the result, then undo the change.

| Scenario | Change | Expected brief |
|---|---|---|
| Everything flagged | In `market_tools.py`, set the `flag_events` default to `z_threshold: float = 0.0` | Every ticker under "Notable moves", each with a news-based explanation or "No clear catalyst found" |
| Nothing flagged | Set `z_threshold: float = 99.0` and `volume_threshold: float = 99.0` | One line saying nothing notable today, and every ticker under "Quiet today" |
| Bad ticker | Add `ZZZZ123` to `watchlist.txt` | `ZZZZ123` listed under "Data issues"; the rest of the brief is normal |
| Cost cap | Set `max_budget_usd=0.01` | The run stops with `Run failed: error_max_budget_usd` and no brief is saved |

### 6.5 Clean up

- [ ] Restore `z_threshold` and `volume_threshold` to `2.0`
- [ ] Restore `watchlist.txt` from `watchlist.backup.txt`
- [ ] Set `max_budget_usd` back to your normal value
- [ ] Delete test briefs from `briefs/` if you don't want them

---

## 7. Schedule test

1. Set up the schedule from section 8 of the main guide, but set the time to 2–3 minutes from now.
2. Wait for it to run.
3. Check:
   - [ ] A new brief appeared in `briefs/`
   - [ ] `run.log` shows the tool calls and a `Saved ...` line, with no errors
4. Change the schedule to your real time.

If nothing happens, check that the paths are absolute, the API key is available to the scheduler, and the computer was awake.

---

## 8. Week-one quality log

The automated tests prove the code works. Only you can judge whether the briefs are useful. For the first week, fill in one row per brief:

| Date | Flagged | Explanations correct? | Missed anything? | Too noisy? | Notes / change to make |
|---|---|---|---|---|---|
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |
| | | | | | |

**What to do with the results:**

| Pattern in the log | Change |
|---|---|
| Often too noisy | Raise both thresholds (try 2.5) |
| Missing moves you cared about | Lower the thresholds (try 1.5) |
| Explanations often wrong or speculative | Tighten the "Likely why" rules in `analyst_prompt.md` |
| Same mistake every day | Add a specific rule against it in `analyst_prompt.md` |

Change one thing at a time, then run step 6 again so you know what helped.

---

## 9. Testing a new tool

Every new tool should get a test. Here's the pattern, using the `get_earnings_date` example from section 9.2 of the main guide. This pattern has been run and passes.

**1. Add `datetime` to the imports** at the top of the test file:

```python
import asyncio
import datetime
import json
```

**2. Add a place for fake data,** next to `FAKE_NEWS`:

```python
FAKE_CALENDAR = {}  # ticker -> yfinance calendar dict
```

**3. Give the fake a matching property.** Add this inside the `FakeTicker` class, after `news`:

```python
    @property
    def calendar(self):
        return FAKE_CALENDAR.get(self.ticker, {})
```

**4. Reset it between tests.** In the `fake_market` fixture, after `FAKE_NEWS.clear()`:

```python
    FAKE_CALENDAR.clear()
```

**5. Write the test.** Cover the normal case and the missing-data case:

```python
def test_earnings_date_found_and_missing():
    FAKE_CALENDAR["AAPL"] = {"Earnings Date": [datetime.date(2026, 1, 29)]}

    assert market_tools.get_earnings_date(" aapl ") == {"ticker": "AAPL", "next_earnings": ["2026-01-29"]}
    assert market_tools.get_earnings_date("MSFT")["next_earnings"] == []  # no calendar data
```

**6. Update the MCP test.** `test_tools_work_through_mcp` checks the exact list of tools, so add the new name:

```python
    assert names == {"flag_events", "compute_moves", "get_news", "get_earnings_date"}
```

**7. Run `pytest -v`.** Expect `9 passed, 1 skipped`. Then check the new tool in the Inspector with live data (step 5).

**General rules for tool tests:**

- Test the normal case, the missing-data case and the error case.
- Compare numbers against a separate calculation, not against the tool's own output.
- Find out what real data looks like (with the Inspector), then make the fake data match that shape.

---

## 10. Troubleshooting the tests

| Problem | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'market_tools'` | Run `pytest` from the `market-agent` folder, not from inside `tests/`. |
| `ModuleNotFoundError: No module named 'yfinance'` (or `mcp`, `pandas`) | The virtual environment isn't active. Activate it (main guide, step 4.2). |
| `pytest: command not found` | Run `pip install pytest` with the virtual environment active, or use `python -m pytest -v`. |
| Only `test_tools_work_through_mcp` fails | You have MCP version 1. Run `pip install -U "mcp>=2"`. |
| `test_zscore_matches_independent_calculation` fails | The z-score code in `_moves` has changed. Check the baseline excludes today. |
| Live test shows `skipped` | `LIVE_TESTS` isn't set. Use the exact command for your system in step 4. |
| Live test fails with `not enough price history` | Yahoo returned no data: rate limiting or a network problem. Wait a few minutes and retry, or run `pip install -U yfinance`. |
| Live test numbers don't match Yahoo's website | You ran it during market hours. Re-run after the close. |
| The Inspector won't start | Node.js isn't installed, or `python` points to the wrong interpreter. Use the virtual environment's Python (for example `.venv/bin/python`). |

---

## Appendix: test file source

Save this as `tests/test_market_tools.py`.

```python
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
    import yfinance

    monkeypatch.setattr(market_tools.yf, "Ticker", yfinance.Ticker)  # undo the fake
    result = market_tools.compute_moves("AAPL")

    assert "error" not in result, result
    assert result["last_close"] > 0
    assert -50 < result["return_1d_pct"] < 50
    print("\nLive AAPL:", result)
```
