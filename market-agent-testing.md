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

**How the tests work:** they swap yfinance for a fake that returns made-up daily prices, 5-minute bars and news in the same shape as the real thing. They also fake the clock, so they can test "market open", "weekend", "holiday" and "early close" on any day you run them. They use a temporary watchlist, so your real `watchlist.txt` is never touched. Results are the same every run, with no internet or API key needed.

---

## 3. Run the offline tests

With your virtual environment active, from the `market-agent` folder:

```bash
pip install pytest
pytest -v
```

**Expected result:** `21 passed, 1 skipped`. The skipped test is the live data check in step 4.

**What each test proves:**

*Market open or closed*

| Test | Proves that |
|---|---|
| `test_market_session[weekend]` | On a Saturday, the market counts as closed and Friday is the last session |
| `test_market_session[market-open]` | Mid-morning on a trading day, the market counts as open (`in_progress`) |
| `test_market_session[pre-market]` | At 8am, the last session is yesterday's, not today's |
| `test_market_session[after-close]` | After 4pm, today's session counts as finished |
| `test_market_session[holiday]` | On Thanksgiving, the last session is the day before |
| `test_market_session[after-early-close]` | After the 1pm close on the day after Thanksgiving, the market counts as closed |
| `test_market_session[during-half-day]` | Before the 1pm close on that half day, the market counts as open |

*Market closed: last finished session*

| Test | Proves that |
|---|---|
| `test_watchlist_skips_comments_blanks_and_uppercases` | `watchlist.txt` is read correctly: comments and blank lines ignored, tickers uppercased |
| `test_zscore_matches_independent_calculation` | The z-score matches a separate hand calculation, and the session's move isn't included in its own baseline |
| `test_big_move_is_flagged_and_calm_ticker_is_quiet` | A big price move gets flagged and a calm ticker lands in "quiet" |
| `test_volume_spike_alone_is_flagged` | A volume spike gets flagged even when the price barely moved |
| `test_thresholds_control_flagging` | Threshold 0 flags everything; threshold 99 flags nothing |
| `test_bad_tickers_are_reported_not_fatal` | Missing data and connection errors are reported per ticker without stopping the scan |
| `test_premarket_ignores_todays_unfinished_row` | Before the open, an unfinished row for today is never treated as a full day |

*Market open: today so far*

| Test | Proves that |
|---|---|
| `test_intraday_zscore_matches_independent_calculation` | Today's move so far is compared with each past session's move to the same time of day, matching a hand calculation |
| `test_intraday_normal_volume_is_not_counted_as_a_low_day` | A normal morning's volume reads as 1.0× normal, not as a 0.32× low-volume day (the partial-day problem) |
| `test_intraday_flags_movers_and_volume_spikes` | While the market is open, big movers and volume spikes are flagged and calm tickers aren't |
| `test_intraday_skips_past_half_days_that_closed_before_this_time` | A past early-close day that ended before the current time is left out of the comparison |
| `test_intraday_needs_enough_history` | A ticker with too little 5-minute history (such as a new IPO) returns a clear error instead of a misleading number |

*News and MCP*

| Test | Proves that |
|---|---|
| `test_news_handles_both_yfinance_formats_and_caps_limit` | Both yfinance news formats are read, summaries are trimmed and results are capped at 10 |
| `test_tools_work_through_mcp` | The tools work through a real MCP client, the same way the agent calls them, and report the session status |
| `test_live_data` | Real data comes back from Yahoo Finance (skipped unless you turn it on) |

**Tip: check the tests catch real bugs.** Make one of these temporary changes in `market_tools.py`, run `pytest`, then change it back:

| Temporary change | Tests that should fail |
|---|---|
| `baseline = returns.iloc[:-1]` → `baseline = returns` | The closed-market z-score test |
| `if session["status"] == "in_progress":` → `if False:` (turns off intraday mode) | All 5 intraday tests: this is what the partial-day problem looks like |
| `if day_bars.index[-1].time() < cutoff:` → `if False:` | The half-day test |

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

**Expected result:** `1 passed`, plus two printed lines: `Live session: {...}` and `Live AAPL: {...}`.

You can run it at any time. Check by eye:

| | Market closed | Market open |
|---|---|---|
| `Live session` shows | `'status': 'complete'` and the last trading day | `'status': 'in_progress'` and a time a few minutes ago |
| AAPL's price field | `last_close` matches the last close on Yahoo Finance or your broker | `last_price` is close to the live quote (it can lag by a few minutes) |
| `return_1d_pct` | Matches that day's percentage change | Matches today's change so far |
| `compared_to` | "daily moves over the last 3 months" | "the same time of day over the last N sessions" (about 20) |

Ideally, run it once while the market is open and once while it's closed, so both modes are checked with real data.

If the offline tests pass but this fails, the problem is the data source, not your code. See [troubleshooting](#10-troubleshooting-the-tests).

---

## 5. Manual tool check with the MCP Inspector

The Inspector lets you call each tool by hand with live data, seeing exactly what Claude will receive. It needs Node.js.

```bash
npx @modelcontextprotocol/inspector python market_tools.py
```

It opens in your browser. Click **Connect**, open the **Tools** tab, and try each tool:

| Tool | Try with | Check that |
|---|---|---|
| `flag_events` | default arguments | Every watchlist ticker appears in `flagged`, `quiet` or `errors`, and `session.status` is right for the time you ran it |
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

**Expected output:** a line for each tool call (`-> mcp__market__flag_events {}` first), then `Saved briefs/YYYY-MM-DD_HHMM.md (N turns, $X.XXX)`. While the market is open, the file name ends in `_intraday.md`.

**Check the tool calls in that output:**

- [ ] `flag_events` is called first
- [ ] `get_news` is called for each flagged ticker
- [ ] No unnecessary repeated calls

### 6.3 Check the brief

Straight after the run, call `flag_events` in the Inspector and compare it with the brief.

- [ ] Every number in the brief matches a tool result exactly
- [ ] Every ticker from the watchlist appears (in "Notable moves", "Quiet" or "Data issues")
- [ ] The title matches the session: "Watchlist brief" when closed, "Intraday update" when open
- [ ] Every "Likely why" has a link, and the article actually says that
- [ ] "No clear catalyst found" is used when the news doesn't explain a move
- [ ] No buy/sell recommendations or advice language
- [ ] The format matches the template in `analyst_prompt.md`

If a number doesn't match a tool result, Claude made it up. Tighten the rules in `analyst_prompt.md` and re-test.

### 6.4 Force each path

Each scenario tests a different part of the brief. Make the change, run `python run_brief.py`, check the result, then undo the change.

| Scenario | Change | Expected brief |
|---|---|---|
| Market closed | No change; run in the evening or at the weekend | Title "Watchlist brief: {last session date}"; moves described as that session's |
| Market open | No change; run between 10:30am and 4pm New York time | Title "Intraday update: {date and time}", the "Market open: figures are as of…" line under it, moves described as "so far today" and volume as "vs. normal for this time of day" |
| Everything flagged | In `market_tools.py`, set the `flag_events` default to `z_threshold: float = 0.0` | Every ticker under "Notable moves", each with a news-based explanation or "No clear catalyst found" |
| Nothing flagged | Set `z_threshold: float = 99.0` and `volume_threshold: float = 99.0` | One line saying nothing notable, and every ticker under "Quiet" |
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
5. If you added the midday run, check the first real one: its file name should end in `_intraday.md` and its title should say "Intraday update".

If nothing happens, check that the paths are absolute, the API key is available to the scheduler, and the computer was awake.

---

## 8. Week-one quality log

The automated tests prove the code works. Only you can judge whether the briefs are useful. For the first week, fill in one row per brief:

| Date | Run (morning / intraday) | Flagged | Explanations correct? | Missed anything? | Too noisy? | Notes / change to make |
|---|---|---|---|---|---|---|
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |
| | | | | | | |

**What to do with the results:**

| Pattern in the log | Change |
|---|---|
| Often too noisy | Raise both thresholds (try 2.5) |
| Missing moves you cared about | Lower the thresholds (try 1.5) |
| Explanations often wrong or speculative | Tighten the "Likely why" rules in `analyst_prompt.md` |
| Same mistake every day | Add a specific rule against it in `analyst_prompt.md` |
| Intraday updates noisier than morning briefs | Move the midday run later (for example 1:30pm) |

Change one thing at a time, then run step 6 again so you know what helped.

---

## 9. Testing a new tool

Every new tool should get a test. Here's the pattern, using the `get_earnings_date` example from section 9.2 of the main guide. This pattern has been run and passes.

**1. Add a place for fake data,** next to `FAKE_NEWS`:

```python
FAKE_CALENDAR = {}  # ticker -> yfinance calendar dict
```

**2. Give the fake a matching property.** Add this inside the `FakeTicker` class, after `news`:

```python
    @property
    def calendar(self):
        return FAKE_CALENDAR.get(self.ticker, {})
```

**3. Reset it between tests.** In the `fake_market` fixture, after `FAKE_NEWS.clear()`:

```python
    FAKE_CALENDAR.clear()
```

**4. Write the test.** Cover the normal case and the missing-data case. (`date` is already imported at the top of the test file.)

```python
def test_earnings_date_found_and_missing():
    FAKE_CALENDAR["AAPL"] = {"Earnings Date": [date(2026, 1, 29)]}

    assert market_tools.get_earnings_date(" aapl ") == {"ticker": "AAPL", "next_earnings": ["2026-01-29"]}
    assert market_tools.get_earnings_date("MSFT")["next_earnings"] == []  # no calendar data
```

**5. Update the MCP test.** `test_tools_work_through_mcp` checks the exact list of tools, so add the new name:

```python
    assert names == {"flag_events", "compute_moves", "get_news", "get_earnings_date"}
```

**6. Run `pytest -v`.** Expect `22 passed, 1 skipped`. Then check the new tool in the Inspector with live data (step 5).

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
| `test_zscore_matches_independent_calculation` fails | The z-score code in `_completed_session_moves` has changed. Check the baseline excludes the session being measured. |
| The intraday and `test_market_session` tests fail, but the others pass | Your `market_tools.py` is an older version without market-hours support. Replace it with the current code from the main guide's appendix. |
| Live test shows `skipped` | `LIVE_TESTS` isn't set. Use the exact command for your system in step 4. |
| Live test fails with `not enough price history` | Yahoo returned no data: rate limiting or a network problem. Wait a few minutes and retry, or run `pip install -U yfinance`. |
| Live test fails with `no intraday data for SPY` | Yahoo's 5-minute data didn't load (rate limiting or a network problem). Wait a few minutes and retry. |
| Live test numbers are slightly off from Yahoo's website while the market is open | Normal: intraday data can lag the live quote by a few minutes. Compare after the close for an exact match. |
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
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import market_tools  # noqa: E402
from mcp import Client  # noqa: E402

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
    import yfinance

    monkeypatch.setattr(market_tools.yf, "Ticker", yfinance.Ticker)  # undo the fake data
    monkeypatch.setattr(market_tools, "now_et", lambda: datetime.now(ET))  # undo the fake clock
    session = market_tools.market_session()
    result = market_tools.compute_moves("AAPL")

    assert "error" not in result, result
    assert (result.get("last_close") or result.get("last_price")) > 0
    assert -50 < result["return_1d_pct"] < 50
    print("\nLive session:", session)
    print("Live AAPL:", result)
```
