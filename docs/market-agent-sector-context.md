# Market Analyst Agent: Sector and Market Context

Many "why did it move?" answers are really "its whole sector moved", and before this change the agent couldn't tell. Now every flagged move is compared, in code, with the ticker's sector ETF and the S&P 500. Each comparison comes with a verdict: was the move about the company, its sector, or the market? A new tool also gives each brief a one-line market backdrop.

This builds on `market-agent-rag.md`. Do this guide **before** `market-agent-alerts.md`, because the alerts use these verdicts and that guide's files include these changes.

---

## Contents

1. [What it adds](#1-what-it-adds)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Update the market tools](#4-step-1-update-the-market-tools)
5. [Step 2: Update the prompt and agent settings](#5-step-2-update-the-prompt-and-agent-settings)
6. [Step 3: Store the comparison with each report](#6-step-3-store-the-comparison-with-each-report)
7. [Step 4: Show it in the app](#7-step-4-show-it-in-the-app)
8. [Step 5: Add the tests](#8-step-5-add-the-tests)
9. [Step 6: Try it](#9-step-6-try-it)
10. [Test it](#10-test-it)
11. [Choosing a benchmark](#11-choosing-a-benchmark)
12. [Settings and tuning](#12-settings-and-tuning)
13. [Costs and speed](#13-costs-and-speed)
14. [Troubleshooting](#14-troubleshooting)
15. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it adds

Here is part of a brief from the test environment. The prices are simulated, but the format is what the agent now writes:

```markdown
## Market backdrop

The S&P 500 fell 0.33% so far today (z-score -0.4). Strongest sector: Utilities (XLU) +0.91%; weakest: Financials (XLF) -1.16%.

## Notable moves

### MSFT: +4.96% (z-score 2.98, volume 1.68x normal)
- **What happened:** MSFT moved +4.96% so far today on volume 1.68x normal for this time of day.
- **Vs. sector and market:** MSFT rose 4.96% so far today; its sector (Technology, XLK) fell 0.13% and the S&P 500 fell 0.33%. That is 5.09 points better than its sector, an unusual gap for MSFT (z-score 4.1), so the move looks specific to MSFT.
- **Likely why:** ...
```

| Where | What you'll see |
|---|---|
| Every brief | A "Market backdrop" section, and a "Vs. sector and market" line for each flagged ticker |
| The app's ticker table | A **Vs. sector** column (for example "+5.09 pts vs XLK") with the verdict under it. Hover to see the full sentence |
| The database | Seven new columns on each flagged ticker, so the comparison is kept with the report |
| Ask | The figures Ask uses now include the gap to the sector and the verdict |
| Search | The sentences are part of each ticker's passage, so searches like "sector-wide sell-off" work |
| Discord alerts (next guide) | Each alert says what kind of move it was |

---

## 2. How it works

```
flag_events ── measures every watchlist ticker (as before)
     │
     └─ for each FLAGGED ticker:
          benchmark = sector ETF (XLK, XLF, ...) from Yahoo's sector, or one you chose in watchlist.txt
          downloads the benchmark and SPY once per scan, then measures them over the same days
          gap = ticker's move − benchmark's move   (percentage points)
          how unusual is that gap?  → z-score against the gaps on the same past days
          verdict + one plain-English sentence, both worked out in code

market_backdrop ── SPY and the 11 sector ETFs, best to worst  → the "Market backdrop" line
```

**Same days, same window.** When the market is closed, the ticker and its benchmark are compared on the last session's daily moves, against about 60 earlier sessions. When the market is open, both are measured "so far today" and compared with the same time of day in recent sessions (about 20), just like the existing intraday figures. A partial day is never compared with full days.

**Why a z-score of the gap, not just the gap?** Some stocks always move a lot more than their sector. A 3-point gap is ordinary for NVDA but rare for JPM. Judging each ticker's gap against its own history makes the verdict fair for both.

**The verdict**, checked in this order:

| Verdict | Rule | What it means |
|---|---|---|
| `stock-specific` | The gap's z-score is 2 or more (either direction) | The ticker did something its sector didn't. Company news is the place to look. |
| `sector-wide` | Otherwise, if the sector's gap to the S&P 500 has a z-score of 2 or more | It moved with its sector, and the sector itself had an unusual day |
| `market-wide` | Otherwise, if the S&P 500's own move has a z-score of 2 or more | It moved with everything else on an unusual market day |
| `mixed` | Otherwise, if the gap's z-score is between 1 and 2 | Part sector, part its own: a wider gap than usual, but not an unusual one |
| `in line` | Anything else | It moved with its sector on an ordinary day (often a volume-only flag) |

The sentence that goes in the brief is built in code from the same numbers. The agent quotes it rather than doing any arithmetic, so the rule that every number comes from a tool still holds.

**The prompt changes too.** The agent is told to lead with "moved with its sector" (or market) for sector-wide and market-wide moves, and never to present company news as the main cause of those. For `mixed`, it says what the sector did, then looks to company news for the rest.

**Only flagged tickers are compared.** On a quiet day, nothing extra is downloaded. When several flagged tickers share a sector, its ETF is downloaded once. If a comparison can't be made (for example, Yahoo is rate limiting), the move is still reported. Only the comparison is left out, and the brief says "Sector comparison unavailable."

---

## 3. Before you start

- [ ] Your project includes everything up to `market-agent-rag.md`, and `pytest` shows `106 passed, 1 skipped`.
- [ ] Back up your reports database. With no run or API running, copy `reports.db` to `reports.backup.db`. The upgrade only adds empty columns, but a backup costs nothing.

No new packages or keys are needed.

**Customized your prompt or code?** Each step below says what changed, so you can merge rather than replace.

---

## 4. Step 1: Update the market tools

Replace `market_tools.py` with the version in the [appendix](#market_toolspy).

What changed:

- **`flag_events`** adds a `context` to each flagged ticker: the benchmark, its move, the S&P 500's move, the gap and its z-score, the verdict (`read`) and the sentence (`summary`).
- **`compute_moves`** includes the same `context` for any ticker you ask about.
- **New tool `market_backdrop`**: the S&P 500 and the 11 sector ETFs, best to worst, with any unusual sector moves named.
- **`watchlist.txt`** can now name a benchmark after a ticker, and comments can follow a ticker on the same line:

```
AAPL
NVDA  SMH      # compare with semiconductors instead of the whole tech sector
JPM
```

Your existing watchlist works unchanged. See [section 11](#11-choosing-a-benchmark) for when to set a benchmark.

---

## 5. Step 2: Update the prompt and agent settings

1. Replace `analyst_prompt.md` with the [appendix](#analyst_promptmd) version. If you've edited your prompt, merge these changes instead:
   - **Process, step 2:** call `market_backdrop` once.
   - **New section "Sector and market context":** what each verdict means and how to write about it.
   - **New rule:** never present company news as the main cause of a sector-wide or market-wide move.
   - **Template:** a "Market backdrop" section, and a "Vs. sector and market" line under each flagged ticker.
2. Replace `run_brief.py` with the [appendix](#run_briefpy) version. The only change is one line, which allows the new tool:

```python
        "mcp__market__market_backdrop",
```

The agent can only call tools listed in `allowed_tools`. A test (section 8) checks that every tool in `market_tools.py` is allowed and named in the prompt, so this can't silently drift.

---

## 6. Step 3: Store the comparison with each report

Replace `reports_db.py` and `ask.py` with the appendix versions.

**`reports_db.py`** adds seven columns to `report_tickers`: `benchmark`, `benchmark_return_pct`, `market_return_pct`, `vs_benchmark_pct`, `vs_benchmark_zscore`, `move_read` and `context_summary`.

**Your existing database is upgraded automatically.** The next run adds the empty columns. Older reports, final ones included, are not changed: they just have no comparison. The API reads older databases fine even before that first run.

**`ask.py`** adds two columns to the per-ticker figures it gives Claude ("vs sector (points)" and "kind of move"). That lets Ask answer questions like "Was NVDA's drop last week about NVDA or chips?"

---

## 7. Step 4: Show it in the app

Replace these files in `frontend/src/` with the appendix versions:

| File | Change |
|---|---|
| `format.js` | A `points()` helper ("+5.09 pts") |
| `components/TickerTable.jsx` | The **Vs. sector** column: the gap, the benchmark, and the verdict underneath. Hover for the sentence |
| `components/RunPanel.jsx` | The run log shows "Checking the market and sectors" for the new tool |
| `styles.css` | One line of styling for the verdict |

If you serve the built app (`uvicorn api:app` with `frontend/dist`), rebuild it:

```bash
cd frontend
npm run build
```

With the Vite dev server (`npm run dev`), the page updates by itself.

On a phone, the wider table scrolls sideways inside its box, as before. The page itself doesn't.

---

## 8. Step 5: Add the tests

1. Replace `tests/test_market_tools.py` with the version in **`market-agent-testing.md`'s appendix**. It adds 13 tests for the comparison, the verdicts, the backdrop and the watchlist format.
2. Add `tests/test_sector_context.py` from this guide's [appendix](#teststest_sector_contextpy).
3. Run:

```bash
pytest -v
```

**Expected result:** `125 passed, 1 skipped`.

---

## 9. Step 6: Try it

**1. With the MCP Inspector** (live data, no Claude cost):

```bash
npx @modelcontextprotocol/inspector python market_tools.py
```

- `market_backdrop` with no arguments: SPY plus about 11 sectors, best first, and a `summary`.
- `compute_moves` with `AAPL`: `context.benchmark` is `XLK`. Check `benchmark_return_pct` against XLK's change on Yahoo Finance.
- `flag_events`: each flagged ticker has a `context`.

**2. A real run:**

```bash
python run_brief.py
```

- The tool calls include `-> mcp__market__market_backdrop {}`, once.
- `python reports_db.py show latest` shows a "Market backdrop" section and a "Vs. sector and market" line for each flagged ticker.
- In the app, the Vs. sector column is filled in for flagged tickers.

**3. Ask** "Was [a flagged ticker]'s move about the company or its sector?" The answer should cite the verdict and the report date.

---

## 10. Test it

### 10.1 Automated tests

`pytest -v` runs everything, including these new tests.

*In `tests/test_market_tools.py` (see the testing guide for the full list)*

| Test | Proves that |
|---|---|
| `test_watchlist_can_name_a_benchmark_per_ticker` | `NVDA SMH # comment` reads as ticker NVDA, benchmark SMH |
| `test_benchmark_comes_from_sector_or_watchlist` | Your choice wins; otherwise the sector's ETF; ETFs, unknown companies and failed lookups use the S&P 500 |
| `test_stock_specific_move` | A 7% jump on a calm tech day is `stock-specific`, and its gap z-score matches a hand calculation |
| `test_sector_wide_move` | Moving with a sector that fell 5% on a flat market day is `sector-wide` |
| `test_market_wide_move` | Everything falling 4% together is `market-wide` |
| `test_volume_only_flag_is_in_line_with_peers` | A volume spike with an ordinary price move is `in line` |
| `test_partly_sector_move_is_mixed` | A wider-than-usual but not unusual gap is `mixed` |
| `test_quiet_tickers_are_not_compared` | Quiet days download no ETFs |
| `test_each_benchmark_is_downloaded_once_per_scan` | Two flagged tech stocks share one XLK download |
| `test_context_problem_never_hides_the_move` | If the ETF fails to download, the move is still flagged and the comparison says why it's missing |
| `test_compute_moves_includes_context` | `compute_moves` gives the same comparison |
| `test_intraday_context_compares_the_same_time_of_day` | While the market is open, the gap is judged against the same time of day, matching a hand calculation |
| `test_market_backdrop_ranks_sectors` | Sectors are sorted best to worst, unusual ones are named, and a missing ETF is reported, not fatal |

*In `tests/test_sector_context.py`*

| Test | Proves that |
|---|---|
| `test_context_is_saved_with_each_flagged_ticker` | The comparison is stored with each flagged ticker; quiet tickers have none |
| `test_unavailable_context_is_stored_as_empty` | A missing comparison is stored as empty, never as an error message in the figures |
| `test_database_from_an_earlier_version_still_reads_and_is_upgraded` | An older database reads fine, gets the new columns on the next run, and its final reports stay unchanged and permanent |
| `test_api_returns_context_in_reports_and_history` | The API returns the comparison in reports and ticker history |
| `test_ask_sees_the_kind_of_move` | Ask's figures include the gap and the verdict |
| `test_agent_can_use_every_market_tool` | Every tool in `market_tools.py` is allowed in `run_brief.py` and named in the prompt |

**Check the tests catch real bugs.** Make one of these temporary changes in `market_tools.py`, run `pytest tests/test_market_tools.py`, then change it back. Each was tried:

| Temporary change | Tests that fail |
|---|---|
| In `describe_context`: `if abs(gap_z) >= CONTEXT_Z:` → `if False:` | The stock-specific and intraday context tests |
| In `_gap`: `gaps.iloc[-1], gaps.iloc[:-1]` → `gaps.iloc[-1], gaps` (today's gap leaks into its own baseline) | The same two: their z-scores no longer match the hand calculation |
| In `flag_events`: pass `{}` instead of `measured` to `_context` | `test_each_benchmark_is_downloaded_once_per_scan` |

### 10.2 What was also tested

- **From the guides alone:** the project was rebuilt from the guides (including this one and the testing guide), and all tests passed.
- **In a real browser, against the test environment** (`market-agent-test-enviro.md`). The sector checks were:
  1. The ticker table shows the gap, benchmark and verdict, and hovering shows the sentence.
  2. The report has the backdrop and the vs. sector lines.
  3. "Run update now" shows "Checking the market and sectors".
  4. An older sector-wide day shows `sector-wide` in the Previous days tab.
  5. On a phone, the table scrolls inside its box, and the page doesn't scroll sideways.
  6. Dark mode renders, with no browser errors.

  The same run also checked the alerts guide's status line.
- **The verdict rules on two months of sample data:**
  - Every simulated earnings day came out `stock-specific`.
  - Every simulated market-wide day came out `market-wide`.
  - Every simulated sector-wide day came out `sector-wide`.

**Not tested here:** live Yahoo Finance data (no internet access while building this). The live data check in the testing guide covers it: it now checks Apple's benchmark is XLK and prints the backdrop.

### 10.3 Checks with real data

- [ ] `LIVE_TESTS=1 pytest -v -s -k live` passes and prints a sensible "Live AAPL vs. sector" sentence and backdrop
- [ ] On a day with a known sector story (for example, chip stocks all down), flagged chipmakers read `sector-wide` or `mixed`, not `stock-specific`
- [ ] On a day with company news (earnings), that ticker reads `stock-specific`
- [ ] The brief's "Vs. sector and market" lines match the tool results exactly
- [ ] For sector-wide moves, "Likely why" leads with the sector, not company news

---

## 11. Choosing a benchmark

By default, each company is compared with the Select Sector SPDR ETF for its Yahoo Finance sector:

| Yahoo sector | ETF | | Yahoo sector | ETF |
|---|---|---|---|---|
| Technology | XLK | | Consumer Cyclical | XLY |
| Financial Services | XLF | | Consumer Defensive | XLP |
| Healthcare | XLV | | Basic Materials | XLB |
| Energy | XLE | | Real Estate | XLRE |
| Industrials | XLI | | Utilities | XLU |
| Communication Services | XLC | | | |

ETFs in your watchlist (and companies with no sector on Yahoo) are compared with the S&P 500 (SPY).

**When to choose your own,** by adding it after the ticker in `watchlist.txt`:

- **A giant in its own sector.** Apple, Microsoft and Nvidia each make up a large share of XLK. When one of them moves a lot, XLK moves with it, and the gap looks smaller than it really is. An industry ETF compares them with their peers instead, for example `NVDA SMH` (semiconductors).
- **The industry matters more than the sector.** For example, a regional bank against `KRE` (regional banks) rather than all financials, or an oil producer against `XOP` (oil and gas exploration) rather than all energy.

Any ticker Yahoo Finance has three months of daily prices for will work (and 5-minute prices, for intraday comparisons). Check a new benchmark with `compute_moves` in the Inspector first.

---

## 12. Settings and tuning

At the top of `market_tools.py`:

| Setting | Default | What it does |
|---|---|---|
| `CONTEXT_Z` | `2.0` | How unusual a gap (or a sector's or the market's move) must be to count. It matches the flagging threshold |
| `MIXED_Z` | `1.0` | Gaps between this and `CONTEXT_Z` are `mixed`. Raise it to call more moves `in line` |
| `MIN_CONTEXT_DAYS` | `10` | Shared past sessions needed before a gap is judged |
| `SECTOR_ETFS` / `ETF_NAMES` | Select Sector SPDRs | The sector-to-ETF mapping and the names used in sentences |
| `MARKET_ETF` | `SPY` | The market benchmark |

**Use the quality log** (testing guide, section 9) to tune. For example, if a ticker is often `mixed` where you'd call it sector-wide, give it a closer benchmark rather than changing the thresholds for everything.

---

## 13. Costs and speed

- **No new keys or charges.** Prices still come from Yahoo Finance.
- **Claude:** one extra tool call per run, plus a few extra lines in each flagged ticker's result. That's a small increase in tokens per run, still well within `max_budget_usd`.
- **Time:** the backdrop downloads 12 ETFs, and each flagged ticker's comparison needs SPY plus its sector ETF (each downloaded once per scan). While the market is open, each also needs 5-minute prices. Expect a run to take a few seconds longer.

---

## 14. Troubleshooting

| Problem | Cause and fix |
|---|---|
| A brief says "Sector comparison unavailable" | Yahoo didn't return data for the ETF or SPY that time, usually rate limiting. Use `compute_moves` in the Inspector to see the `context.error`. It normally works on the next run. |
| Every ticker is compared with SPY, not its sector | The sector lookup (`yf.Ticker("AAPL").info`) is failing. Run `pip install -U yfinance`, or set benchmarks in `watchlist.txt`, which skips the lookup. |
| `context.error` says the two "don't share enough recent sessions" | A recent listing, or a benchmark with gaps in its history. Choose a longer-listed benchmark. |
| No "Market backdrop" section, and no `market_backdrop` in the tool calls | `run_brief.py` doesn't allow the tool, or the prompt wasn't updated. `pytest` catches both (`test_agent_can_use_every_market_tool`). |
| The agent still credits company news for a sector-wide move | Check the prompt has the new rule. If it keeps happening, add a specific example to the "Sector and market context" section. |
| No Vs. sector column in the app | Rebuild the frontend (`npm run build`), then hard-refresh the page. |
| The column shows "—" for older reports | Expected: reports saved before this change have no comparison. |
| `test_tools_work_through_mcp` fails, listing `market_backdrop` | `tests/test_market_tools.py` is the old version. Replace it from the testing guide's appendix. |
| The context tests fail but the others pass | `market_tools.py` is the old version. Replace it from this guide's appendix. |

---

## Appendix: full source code

### market_tools.py

```python
"""MCP server with the market tools the analyst agent can call.

Every number the agent reports comes from these functions, computed in code.
The agent never does math itself.

Works at any time of day:
- Market closed (evenings, weekends, holidays, pre-market): measures the last
  completed session against the previous 3 months of daily moves.
- Market open: measures today's move *so far* against the same time of day in
  recent sessions, so a partial day is never treated as a full one.

Every flagged move also comes with sector and market context: how the ticker did
against its sector ETF and the S&P 500, and whether that gap was unusual. That
tells the agent whether a move was about the company, its sector, or the market.

Test it on its own:  npx @modelcontextprotocol/inspector python market_tools.py
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer

WATCHLIST_FILE = Path(__file__).parent / "watchlist.txt"
ET = ZoneInfo("America/New_York")
MARKET_CLOSE = time(16, 0)
REFERENCE_TICKER = "SPY"             # used to tell whether the market is open
STALE_AFTER = timedelta(minutes=30)  # no new bar for this long means trading has stopped (early close)
MIN_INTRADAY_DAYS = 10               # past sessions needed for a same-time-of-day comparison

# Sector and market context
MARKET_ETF, MARKET_NAME = "SPY", "S&P 500"
CONTEXT_Z = 2.0         # a gap to the sector (or sector to market) this unusual counts as a real difference
MIXED_Z = 1.0           # a gap this wide, but not unusual, means the move was only partly its sector's
MIN_CONTEXT_DAYS = 10   # shared past sessions needed to judge a gap
SECTOR_ETFS = {         # Yahoo Finance sector name -> Select Sector SPDR ETF
    "Technology": "XLK", "Financial Services": "XLF", "Healthcare": "XLV", "Energy": "XLE",
    "Industrials": "XLI", "Communication Services": "XLC", "Utilities": "XLU",
    "Consumer Cyclical": "XLY", "Consumer Defensive": "XLP", "Basic Materials": "XLB", "Real Estate": "XLRE",
}
ETF_NAMES = {           # names used in briefs
    "XLK": "Technology", "XLF": "Financials", "XLV": "Health Care", "XLE": "Energy", "XLI": "Industrials",
    "XLC": "Communication Services", "XLU": "Utilities", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLB": "Materials", "XLRE": "Real Estate",
}

mcp = MCPServer("market-tools")


def now_et() -> datetime:
    return datetime.now(ET)


def _to_et(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_localize(ET) if index.tz is None else index.tz_convert(ET)


def _watchlist_entries() -> list[list[str]]:
    """Each line: a ticker, optionally followed by the benchmark to compare it with.
    Anything after a # is a comment."""
    entries = []
    for line in WATCHLIST_FILE.read_text().splitlines():
        words = line.split("#", 1)[0].upper().split()
        if words:
            entries.append(words)
    return entries


def load_watchlist() -> list[str]:
    return [words[0] for words in _watchlist_entries()]


def load_benchmarks() -> dict[str, str]:
    """Benchmarks chosen in watchlist.txt, e.g. `NVDA SMH` compares NVDA with semiconductors."""
    if not WATCHLIST_FILE.is_file():
        return {}
    return {words[0]: words[1] for words in _watchlist_entries() if len(words) > 1}


def market_session() -> dict:
    """Work out whether a US trading session is in progress right now.

    Uses the clock plus SPY's latest 5-minute bar, so weekends, holidays and
    early-close (half) days are handled without a holiday calendar.
    """
    bars = yf.Ticker(REFERENCE_TICKER).history(period="5d", interval="5m")
    if bars.empty:
        raise RuntimeError(f"no intraday data for {REFERENCE_TICKER}; can't tell if the market is open")
    last_bar = _to_et(bars.index)[-1]
    now = now_et()
    in_progress = (
        last_bar.date() == now.date()
        and now.time() < MARKET_CLOSE
        and now - (last_bar + timedelta(minutes=5)) < STALE_AFTER
    )
    if in_progress:
        return {"status": "in_progress", "as_of": last_bar.strftime("%Y-%m-%d %H:%M ET")}
    return {"status": "complete", "as_of": last_bar.date().isoformat()}


def _measure(ticker: str, session: dict) -> tuple[dict, pd.Series | None]:
    """Core calculation shared by the tools below.

    Returns the figures, plus the returns they were judged against, by date (today's last).
    The returns let a ticker be compared with its sector and the market on the same days.
    """
    daily = yf.Ticker(ticker).history(period="3mo")
    if len(daily) < 25:
        return {"ticker": ticker, "error": "not enough price history"}, None
    daily.index = _to_et(daily.index)
    if session["status"] == "in_progress":
        return _intraday_moves(ticker, daily, session)
    return _completed_session_moves(ticker, daily, session)


def _moves(ticker: str, session: dict) -> dict:
    return _measure(ticker, session)[0]


def _completed_session_moves(ticker: str, daily: pd.DataFrame, session: dict) -> tuple[dict, pd.Series | None]:
    """Last completed session vs. the previous 3 months of daily moves."""
    last_session = date.fromisoformat(session["as_of"])
    daily = daily[daily.index.date <= last_session]  # ignore any row for a session that hasn't finished
    if len(daily) < 25:
        return {"ticker": ticker, "error": "not enough price history"}, None

    close, volume = daily["Close"], daily["Volume"]
    returns = close.pct_change().dropna()
    today = returns.iloc[-1]
    baseline = returns.iloc[:-1]  # history before the session, so it doesn't skew its own baseline
    std = baseline.std()
    avg_volume = volume.iloc[-21:-1].mean()  # prior 20 sessions

    figures = {
        "ticker": ticker,
        "session": "complete",
        "as_of": daily.index[-1].date().isoformat(),
        "last_close": round(float(close.iloc[-1]), 2),
        "return_1d_pct": round(float(today) * 100, 2),
        "return_5d_pct": round(float(close.iloc[-1] / close.iloc[-6] - 1) * 100, 2),
        "return_zscore": round(float((today - baseline.mean()) / std), 2) if std > 0 else 0.0,
        "volume_vs_avg": round(float(volume.iloc[-1] / avg_volume), 2) if avg_volume > 0 else None,
        "compared_to": "daily moves over the last 3 months",
    }
    return figures, pd.Series(returns.to_numpy(), index=returns.index.date)


def _intraday_moves(ticker: str, daily: pd.DataFrame, session: dict) -> tuple[dict, pd.Series | None]:
    """Today's move so far vs. the same time of day in recent sessions."""
    bars = yf.Ticker(ticker).history(period="1mo", interval="5m")
    if bars.empty:
        return {"ticker": ticker, "error": "no intraday data"}, None
    bars.index = _to_et(bars.index)

    today = datetime.strptime(session["as_of"], "%Y-%m-%d %H:%M ET").date()
    today_bars = bars[bars.index.date == today]
    if today_bars.empty:
        return {"ticker": ticker, "error": "no trades yet today"}, None
    cutoff = today_bars.index[-1].time()  # compare every past session up to this same time

    closes = pd.Series(daily["Close"].to_numpy(), index=daily.index.date)

    def prev_close(day: date) -> float | None:
        earlier = closes[closes.index < day]
        return float(earlier.iloc[-1]) if len(earlier) else None

    past_bars = bars[bars.index.date < today]
    past_days, past_returns, past_volumes = [], [], []
    for day, day_bars in past_bars.groupby(past_bars.index.date):
        if day_bars.index[-1].time() < cutoff:  # session closed early, before this time of day
            continue
        upto = day_bars[day_bars.index.time <= cutoff]
        start = prev_close(day)
        if upto.empty or start is None:
            continue
        past_days.append(day)
        past_returns.append(upto["Close"].iloc[-1] / start - 1)
        past_volumes.append(upto["Volume"].sum())

    start_today = prev_close(today)
    if len(past_returns) < MIN_INTRADAY_DAYS or start_today is None:
        return {"ticker": ticker, "error": "not enough intraday history"}, None

    price = float(today_bars["Close"].iloc[-1])
    move = price / start_today - 1
    past = pd.Series(past_returns)
    std = past.std()
    avg_volume = sum(past_volumes) / len(past_volumes)
    earlier_closes = closes[closes.index < today]

    figures = {
        "ticker": ticker,
        "session": "in_progress",
        "as_of": f"{today.isoformat()} {cutoff:%H:%M} ET",
        "last_price": round(price, 2),
        "return_1d_pct": round(move * 100, 2),  # since the previous close
        "return_5d_pct": round(float(price / earlier_closes.iloc[-5] - 1) * 100, 2),
        "return_zscore": round(float((move - past.mean()) / std), 2) if std > 0 else 0.0,
        "volume_vs_avg": round(float(today_bars["Volume"].sum() / avg_volume), 2) if avg_volume > 0 else None,
        "compared_to": f"the same time of day over the last {len(past_returns)} sessions",
    }
    return figures, pd.Series(past_returns + [move], index=past_days + [today])


# ---------------------------------------------------------------------------
# Sector and market context
# ---------------------------------------------------------------------------

_sectors: dict[str, str | None] = {}  # ticker -> Yahoo sector name, looked up once per process


def sector_of(ticker: str) -> str | None:
    if ticker not in _sectors:
        try:
            _sectors[ticker] = (yf.Ticker(ticker).info or {}).get("sector")
        except Exception:  # not available for this ticker, or Yahoo is having a moment
            return None
    return _sectors[ticker]


def benchmark_for(ticker: str) -> tuple[str, str | None]:
    """(benchmark ticker, sector name) to compare a ticker with.

    A benchmark chosen in watchlist.txt wins; otherwise the sector ETF for the company's
    sector; otherwise (ETFs, unknown sectors) the S&P 500 itself.
    """
    chosen = load_benchmarks().get(ticker)
    if chosen:
        return chosen, ETF_NAMES.get(chosen)
    if ticker in ETF_NAMES or ticker == MARKET_ETF:
        return MARKET_ETF, None
    etf = SECTOR_ETFS.get(sector_of(ticker) or "")
    return (etf, ETF_NAMES[etf]) if etf else (MARKET_ETF, None)


def _gap(own: pd.Series, other: pd.Series) -> tuple[float, float] | None:
    """Today's gap between two return series in percentage points, and its z-score
    against the gaps on the same past days. None if they don't share enough days."""
    both = pd.concat([own, other], axis=1, join="inner").dropna()
    if len(both) <= MIN_CONTEXT_DAYS or both.index[-1] != own.index[-1]:
        return None
    gaps = both.iloc[:, 0] - both.iloc[:, 1]
    today, past = gaps.iloc[-1], gaps.iloc[:-1]
    std = past.std()
    return float(today) * 100, float((today - past.mean()) / std) if std > 0 else 0.0


def _verb(pct: float) -> str:
    if abs(pct) < 0.005:
        return "was flat"
    return f"{'rose' if pct > 0 else 'fell'} {abs(pct):.2f}%"


def describe_context(ticker: str, move_pct: float, benchmark: str, sector: str | None,
                     benchmark_pct: float, market_pct: float, gap_pct: float, gap_z: float,
                     benchmark_vs_market_z: float | None, market_z: float, in_progress: bool) -> dict:
    """Turn the numbers into a verdict and a sentence the agent can quote.

    read is one of (checked in this order):
      stock-specific  the ticker moved unusually differently from its sector (or the market)
      sector-wide     it moved with its sector, and the sector moved unusually vs. the market
      market-wide     it moved with its sector and the market, and the market's move was unusual
      mixed           a wider gap to its sector than usual, but not an unusual one: partly its peers, partly its own
      in line         it moved with its sector, and nothing unusual happened there (e.g. a volume-only flag)
    """
    so_far = " so far today" if in_progress else ""
    against_market = benchmark == MARKET_ETF
    if abs(gap_z) >= CONTEXT_Z:
        read = "stock-specific"
    elif not against_market and benchmark_vs_market_z is not None and abs(benchmark_vs_market_z) >= CONTEXT_Z:
        read = "sector-wide"
    elif abs(market_z) >= CONTEXT_Z:
        read = "market-wide"
    elif abs(gap_z) >= MIXED_Z:
        read = "mixed"
    else:
        read = "in line"

    group = "the market" if against_market else ("its sector" if sector else benchmark)  # what it's compared with
    peer = "the S&P 500" if against_market else (f"its sector ({sector}, {benchmark})" if sector else benchmark)
    text = f"{ticker} {_verb(move_pct)}{so_far}; {peer} {_verb(benchmark_pct)}"
    text += "." if against_market else f" and the S&P 500 {_verb(market_pct)}."
    better = "better" if gap_pct > 0 else "worse"
    if read == "stock-specific":
        text += (f" That is {abs(gap_pct):.2f} points {better} than {group}, an unusual gap for {ticker}"
                 f" (z-score {gap_z:.1f}), so the move looks specific to {ticker}.")
    elif read == "sector-wide":
        text += (f" {ticker} moved in line with {group}, and {'the sector' if sector else benchmark} moved unusually"
                 f" against the market (z-score {benchmark_vs_market_z:.1f}), so this looks like a sector-wide move.")
    elif read == "market-wide":
        text += (f" {ticker} moved in line with {group if against_market else group + ' and the market'},"
                 f" and the market's own move was unusual (z-score {market_z:.1f}), so this looks like a market-wide move.")
    elif read == "mixed":
        text += (f" Part of the move matches {group}, but {ticker} did {abs(gap_pct):.2f} points {better}: a wider gap"
                 f" than usual, though not an unusual one (z-score {gap_z:.1f}). Company news may explain the rest.")
    else:
        text += f" {ticker} moved in line with {group}, and nothing unusual happened in the sector or the market." \
            if not against_market else f" {ticker} moved in line with the market, and the market's move was ordinary."
    return {
        "benchmark": benchmark,
        "sector": sector,
        "benchmark_return_pct": round(benchmark_pct, 2),
        "market_return_pct": round(market_pct, 2),
        "vs_benchmark_pct": round(gap_pct, 2),
        "vs_benchmark_zscore": round(gap_z, 2),
        "benchmark_vs_market_zscore": None if benchmark_vs_market_z is None else round(benchmark_vs_market_z, 2),
        "market_zscore": round(market_z, 2),
        "read": read,
        "summary": text,
    }


def _context(ticker: str, figures: dict, returns: pd.Series, session: dict, cache: dict) -> dict:
    """Compare one ticker's move with its sector and the market on the same days.

    cache holds benchmark measurements, so a scan downloads each ETF once.
    """
    if ticker == MARKET_ETF:
        return {"error": f"{ticker} is the market benchmark itself"}

    def measured(symbol):
        if symbol not in cache:
            try:
                cache[symbol] = _measure(symbol, session)
            except Exception as e:  # e.g. a download problem for this one ETF
                cache[symbol] = {"ticker": symbol, "error": str(e)}, None
        return cache[symbol]

    benchmark, sector = benchmark_for(ticker)
    market, market_returns = measured(MARKET_ETF)
    bench, bench_returns = measured(benchmark)
    for name, result, series in ((MARKET_ETF, market, market_returns), (benchmark, bench, bench_returns)):
        if series is None:
            return {"error": f"no comparison data for {name} ({result.get('error', 'unknown problem')})"}
    gap = _gap(returns, bench_returns)
    if gap is None:
        return {"error": f"{ticker} and {benchmark} don't share enough recent sessions to compare"}
    bench_vs_market = None if benchmark == MARKET_ETF else _gap(bench_returns, market_returns)
    return describe_context(
        ticker, figures["return_1d_pct"], benchmark, sector, bench["return_1d_pct"], market["return_1d_pct"],
        gap[0], gap[1], bench_vs_market[1] if bench_vs_market else None, market["return_zscore"],
        session["status"] == "in_progress")


def _with_context(ticker: str, session: dict, cache: dict) -> dict:
    figures, returns = _measure(ticker, session)
    if "error" not in figures:
        try:
            figures["context"] = _context(ticker, figures, returns, session, cache)
        except Exception as e:  # context is extra: a problem here never hides the move itself
            figures["context"] = {"error": f"sector comparison failed ({e})"}
    return figures


@mcp.tool()
def flag_events(z_threshold: float = 2.0, volume_threshold: float = 2.0) -> dict:
    """Scan the whole watchlist and return only the tickers with unusual moves.

    A ticker is flagged if its return z-score is beyond +/- z_threshold, or its volume
    is at least volume_threshold times normal. Works whether or not the market is open:
    `session.status` is "complete" for the last finished session, or "in_progress" when
    the market is open, in which case moves are measured so far today and compared with
    the same time of day in recent sessions. Call this first when writing a brief.

    Each flagged ticker has a `context`: its move against its sector ETF and the S&P 500,
    with `read` saying whether the move was stock-specific, sector-wide, market-wide, mixed
    or in line with its peers, and a `summary` sentence you can use as written.
    """
    session = market_session()
    flagged, quiet, errors = [], [], []
    measured = {}  # ticker -> (figures, returns), reused when a watchlist ticker is also a benchmark
    for ticker in load_watchlist():
        try:
            m, returns = measured[ticker] = _measure(ticker, session)
        except Exception as e:  # one bad ticker shouldn't sink the whole scan
            errors.append({"ticker": ticker, "error": str(e)})
            continue
        if "error" in m:
            errors.append(m)
        elif abs(m["return_zscore"]) >= z_threshold or (m["volume_vs_avg"] or 0) >= volume_threshold:
            flagged.append(m)
        else:
            quiet.append({"ticker": ticker, "return_1d_pct": m["return_1d_pct"]})

    # Sector and market context for each flagged move (each ETF is downloaded once)
    for m in flagged:
        try:
            m["context"] = _context(m["ticker"], m, measured[m["ticker"]][1], session, measured)
        except Exception as e:  # context is extra: a problem here never hides the move itself
            m["context"] = {"error": f"sector comparison failed ({e})"}
    return {"session": session, "flagged": flagged, "quiet": quiet, "errors": errors}


@mcp.tool()
def compute_moves(ticker: str) -> dict:
    """Price and volume stats for one ticker: price, return since the previous close,
    5-day return, return z-score and volume vs. normal. When the market is open these
    are so far today, compared with the same time of day in recent sessions.
    Use this for any figure you report; never estimate numbers yourself.
    Includes the same sector and market `context` that flag_events gives flagged tickers.
    """
    return _with_context(ticker.strip().upper(), market_session(), {})


@mcp.tool()
def market_backdrop() -> dict:
    """How the whole market and each sector moved: the S&P 500 (SPY) and the 11 sector ETFs,
    best to worst, with z-scores (so far today when the market is open). Call it once per brief
    for the "Market backdrop" line, or to see whether a move was part of a wider trend.
    """
    session = market_session()
    in_progress = session["status"] == "in_progress"
    rows, errors = [], []
    for etf in [MARKET_ETF, *ETF_NAMES]:
        try:
            m = _moves(etf, session)
        except Exception as e:
            m = {"ticker": etf, "error": str(e)}
        if "error" in m:
            errors.append({"ticker": etf, "error": m["error"]})
        else:
            rows.append({"ticker": etf, "name": ETF_NAMES.get(etf, MARKET_NAME),
                         "return_1d_pct": m["return_1d_pct"], "return_zscore": m["return_zscore"]})
    market = next((r for r in rows if r["ticker"] == MARKET_ETF), None)
    sectors = sorted((r for r in rows if r["ticker"] != MARKET_ETF), key=lambda r: r["return_1d_pct"], reverse=True)
    return {"session": session, "market": market, "sectors": sectors, "errors": errors,
            "summary": describe_backdrop(market, sectors, in_progress)}


def describe_backdrop(market: dict | None, sectors: list[dict], in_progress: bool) -> str:
    """One or two sentences on the market and sectors (sectors sorted best first)."""
    so_far = " so far today" if in_progress else ""
    parts = []
    if market:
        parts.append(f"The {MARKET_NAME} {_verb(market['return_1d_pct'])}{so_far} (z-score {market['return_zscore']:.1f}).")
    if len(sectors) >= 2:
        best, worst = sectors[0], sectors[-1]
        parts.append(f"Strongest sector: {best['name']} ({best['ticker']}) {best['return_1d_pct']:+.2f}%; "
                     f"weakest: {worst['name']} ({worst['ticker']}) {worst['return_1d_pct']:+.2f}%.")
        unusual = [s for s in sectors if abs(s["return_zscore"]) >= CONTEXT_Z]
        if unusual:
            parts.append("Unusual sector moves: " + ", ".join(
                f"{s['name']} {s['return_1d_pct']:+.2f}% (z-score {s['return_zscore']:.1f})" for s in unusual) + ".")
    return " ".join(parts) or "Market data unavailable."


@mcp.tool()
def get_news(ticker: str, limit: int = 5) -> list[dict]:
    """Recent news headlines for one ticker: title, publisher, date, url and a short
    summary. Use this to find the likely reason behind a flagged move.
    """
    items = yf.Ticker(ticker.strip().upper()).news or []
    results = []
    for item in items[: min(limit, 10)]:
        c = item.get("content", item)  # yfinance has shipped two different formats
        results.append({
            "title": c.get("title"),
            "publisher": (c.get("provider") or {}).get("displayName") or c.get("publisher"),
            "published": c.get("pubDate") or c.get("providerPublishTime"),
            "url": (c.get("canonicalUrl") or {}).get("url") or c.get("link"),
            "summary": (c.get("summary") or "")[:300],
        })
    return results


if __name__ == "__main__":
    mcp.run()  # speaks MCP over stdio; the agent starts this as a subprocess
```

### analyst_prompt.md

```markdown
You are an equity research analyst writing a short brief on the user's watchlist.

## Process

1. Call `flag_events` first. It returns the session status, the tickers with unusual moves, and the quiet ones.
2. Call `market_backdrop` once, for how the S&P 500 and each sector moved.
3. For each flagged ticker, read its `context` (see below), then call `get_news` to find the likely reason. Call `compute_moves` if you need more detail on a ticker.
4. Write the brief.

## Market open vs. closed

Check `session.status` in the `flag_events` result.

- **`complete`**: the market is closed. Write a normal brief on the session dated `session.as_of`.
- **`in_progress`**: the market is open. Write an intraday update:
  - Use the intraday title from the template below.
  - Describe every move as "so far today". Describe volume as "vs. normal for this time of day".
  - Under the title, add one line: "Market open: figures are as of {session.as_of} and can change before the close."

## Sector and market context

Each flagged ticker's `context.read` says what kind of move it was, judged in code against its sector ETF and the S&P 500:

- **`stock-specific`**: it moved unusually differently from its sector. Look for company news first.
- **`sector-wide`**: it moved with its sector, and the sector moved unusually against the market. Say so first ("moved with its sector"), then mention any company news as a possible extra factor, not the main cause.
- **`market-wide`**: it moved with its sector and the market, and the market's move was unusual. Say so first, then any company news.
- **`mixed`**: part of the move matches its sector, and part is its own (a wider gap than usual, but not an unusual one). Say what the sector did, then look to company news for the rest.
- **`in line`**: it moved with its sector, and nothing unusual happened there (often a volume-only flag). Say so, and focus on why volume was high if the news explains it.

Use `context.summary` as written for the "Vs. sector and market" line. If `context` has an `error` instead, write "Sector comparison unavailable."

## Rules

- Every number must come from a tool result. Never estimate or calculate figures yourself.
- Cite a source (publisher and link) for every explanation.
- Keep facts separate from interpretation. If the news doesn't clearly explain a move, write "No clear catalyst found."
- Never present company news as the main cause of a move that `context.read` calls sector-wide or market-wide.
- If nothing was flagged, say so in one line. Don't invent significance.
- If a tool returned errors for some tickers, list them at the end.
- This is research, not investment advice. Never recommend buying or selling.

## Output

Respond with only the brief, in this markdown format:

# Watchlist brief: {session.as_of}
(When the market is open, use this title instead: # Intraday update: {session.as_of})

## Market backdrop

{market_backdrop.summary}

## Notable moves

### {TICKER}: {return_1d_pct}% (z-score {return_zscore}, volume {volume_vs_avg}x normal)
- **What happened:** one or two factual sentences.
- **Vs. sector and market:** {context.summary}
- **Likely why:** the catalyst, with [publisher](url). Or "No clear catalyst found."
- **Worth watching:** one line on what to check next.

## Quiet

{TICKER} ({return_1d_pct}%), ...

## Data issues

Only include this section if any tickers returned errors.
```

### run_brief.py

```python
"""Run the analyst agent once and save the report to the reports database.

Works at any time:
- Market open: writes an intraday update and saves it as today's report,
  replacing any earlier update from today.
- Market closed: writes the final report for the last session. Final reports
  are permanent; if it's already saved, this stops before calling Claude.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_brief.py

The API's "Run update now" button calls run_once() from here too.
"""

import asyncio
import json
import sys
from contextlib import closing
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

import reports_db
import search_index
from market_tools import flag_events, market_session, now_et

HERE = Path(__file__).parent

options = ClaudeAgentOptions(
    system_prompt=(HERE / "analyst_prompt.md").read_text(),
    mcp_servers={
        "market": {
            "type": "stdio",
            "command": sys.executable,
            "args": [str(HERE / "market_tools.py")],
        },
    },
    strict_mcp_config=True,  # use only the servers listed above
    tools=[],                # turn off built-in tools: no shell, no file access
    allowed_tools=[          # MCP tools are named mcp__<server>__<tool>
        "mcp__market__flag_events",
        "mcp__market__compute_moves",
        "mcp__market__get_news",
        "mcp__market__market_backdrop",
    ],
    max_turns=25,
    max_budget_usd=1.00,     # hard stop on cost per run
)


def report_key(session: dict) -> tuple[str, str]:
    """(session_date, status) for the database, from a market_session() result."""
    if session["status"] == "in_progress":
        return session["as_of"][:10], "intraday"
    return session["as_of"], "final"


def tool_payload(block: ToolResultBlock):
    """A tool result as Python data. MCP sends a dict as one JSON text part,
    and a list as one part per item."""
    content = block.content
    if isinstance(content, str):
        parts = [content]
    else:
        parts = [p.get("text", "") for p in content or [] if isinstance(p, dict) and p.get("type") == "text"]
    try:
        values = [json.loads(p) for p in parts if p.strip()]
    except json.JSONDecodeError:
        return None
    return values[0] if len(values) == 1 else values


async def run_once(emit=None) -> dict:
    """Run the agent once and save the report.

    emit(event) is called with progress events (dicts with a "type" key):
    started, tool_call, warning, then saved or skipped. Returns the last event.
    Raises RuntimeError if the run fails.
    """
    emit = emit or (lambda event: None)
    now = now_et()
    session = await asyncio.to_thread(market_session)  # checked first, so a data outage costs nothing
    session_date, status = report_key(session)

    if status == "final":
        with closing(reports_db.connect()) as conn:
            if reports_db.is_final(conn, session_date):
                event = {"type": "skipped", "session_date": session_date,
                         "message": f"The final report for {session_date} is already saved. Nothing to do."}
                emit(event)
                return event
        prompt = (f"It is {now:%Y-%m-%d %H:%M} ET and the market is closed. "
                  f"Write the watchlist brief for the {session_date} session.")
    else:
        prompt = f"It is {now:%Y-%m-%d %H:%M} ET and the market is open. Write an intraday update."
    emit({"type": "started", "session_date": session_date, "status": status})

    calls = {}  # tool_use_id -> (tool name, arguments)
    scan, sources, result = None, [], None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls[block.id] = (block.name, block.input)
                    emit({"type": "tool_call", "tool": block.name, "input": block.input})

        elif isinstance(message, UserMessage) and isinstance(message.content, list):
            # Keep the exact figures and news the agent saw, for the database
            for block in message.content:
                if not isinstance(block, ToolResultBlock) or block.is_error or block.tool_use_id not in calls:
                    continue
                name, args = calls[block.tool_use_id]
                payload = tool_payload(block)
                if name.endswith("__flag_events") and scan is None and isinstance(payload, dict):
                    scan = payload
                elif name.endswith("__get_news") and payload:
                    for item in payload if isinstance(payload, list) else [payload]:
                        sources.append({**item, "ticker": str(args.get("ticker", "")).strip().upper()})

        elif isinstance(message, ResultMessage):
            result = message

    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Run failed: {result.subtype if result else 'no result'}")

    if scan is None:
        emit({"type": "warning",
              "message": "Couldn't read the agent's flag_events result, so re-scanning for the database."})
        scan = await asyncio.to_thread(flag_events)
    # The scan's own session is what the figures describe (matters if the market closed mid-run)
    session_date, status = report_key(scan.get("session", session))
    as_of = scan.get("session", session)["as_of"]
    title = next((ln[2:].strip() for ln in result.result.splitlines() if ln.startswith("# ")), "Watchlist brief")
    cost = result.total_cost_usd or 0

    with closing(reports_db.connect()) as conn:
        outcome = reports_db.save_report(
            conn, session_date=session_date, status=status, title=title, body_md=result.result,
            as_of=as_of, cost_usd=cost, scan=scan, sources=sources)
    event = {"type": "saved", "outcome": outcome, "session_date": session_date, "status": status,
             "turns": result.num_turns, "cost_usd": round(cost, 4)}
    emit(event)

    # Keep the search index current. The report is already saved, so a problem here isn't fatal:
    # the index catches up next time (or run `python search_index.py sync`).
    try:
        await asyncio.to_thread(search_index.sync)
    except Exception as e:
        emit({"type": "warning", "message": f"Saved, but the search index wasn't updated ({e}). It will catch up later."})
    return event


def print_event(event: dict) -> None:
    """Show progress in the terminal."""
    if event["type"] == "tool_call":
        print(f"-> {event['tool']} {event['input']}")  # audit trail of every tool call
    elif event["type"] == "started":
        print(f"Writing the {event['status']} report for {event['session_date']}...")
    elif event["type"] == "saved":
        print(f"{event['outcome']}: {event['status']} report for {event['session_date']} "
              f"({event['turns']} turns, ${event['cost_usd']:.3f})")
    else:
        print(event.get("message", event))


async def main() -> None:
    try:
        await run_once(print_event)
    except RuntimeError as e:
        sys.exit(str(e))


if __name__ == "__main__":
    asyncio.run(main())
```

### reports_db.py

```python
"""Reports database: every brief the agent writes, stored in SQLite.

Storage rules:
- One report per trading day (session_date).
- While the market is open, that day's report has status "intraday" and each
  new run replaces it with fresher information.
- Once the session is over, the final report is saved with status "final".
  Final reports are permanent: the database itself refuses to change or delete them.

Browse from the terminal:
    python reports_db.py list
    python reports_db.py show latest
    python reports_db.py show 2026-11-06
"""

import argparse
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(os.environ.get("REPORTS_DB") or Path(__file__).parent / "reports.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS reports (
    session_date   TEXT PRIMARY KEY,           -- trading day covered, YYYY-MM-DD
    status         TEXT NOT NULL CHECK (status IN ('intraday', 'final')),
    title          TEXT NOT NULL,
    body_md        TEXT NOT NULL,              -- the brief, in markdown
    as_of          TEXT NOT NULL,              -- '2026-11-06' (final) or '2026-11-06 12:30 ET' (intraday)
    revision       INTEGER NOT NULL DEFAULT 1, -- how many times this day's report has been written
    total_cost_usd REAL NOT NULL DEFAULT 0,    -- Claude cost of every run saved for this day
    created_at     TEXT NOT NULL,              -- UTC timestamps
    updated_at     TEXT NOT NULL,
    finalized_at   TEXT
);

CREATE TABLE IF NOT EXISTS report_tickers (
    session_date   TEXT NOT NULL REFERENCES reports(session_date),
    ticker         TEXT NOT NULL,
    category       TEXT NOT NULL CHECK (category IN ('flagged', 'quiet', 'error')),
    price          REAL,   -- last close (final) or last price (intraday)
    return_1d_pct  REAL,
    return_5d_pct  REAL,
    return_zscore  REAL,
    volume_vs_avg  REAL,
    compared_to    TEXT,
    error          TEXT,
    -- Sector and market context (flagged tickers; empty for reports saved before it existed)
    benchmark            TEXT,   -- sector ETF it was compared with, e.g. XLK (or SPY)
    benchmark_return_pct REAL,
    market_return_pct    REAL,   -- S&P 500 (SPY)
    vs_benchmark_pct     REAL,   -- ticker minus benchmark, in percentage points
    vs_benchmark_zscore  REAL,   -- how unusual that gap was
    move_read            TEXT,   -- stock-specific, sector-wide, market-wide, mixed or in line
    context_summary      TEXT,
    PRIMARY KEY (session_date, ticker)
);

CREATE TABLE IF NOT EXISTS report_sources (
    id             INTEGER PRIMARY KEY,
    session_date   TEXT NOT NULL REFERENCES reports(session_date),
    ticker         TEXT NOT NULL,
    title          TEXT,
    publisher      TEXT,
    url            TEXT,
    published      TEXT
);

CREATE INDEX IF NOT EXISTS idx_report_tickers_ticker ON report_tickers (ticker, session_date);
CREATE INDEX IF NOT EXISTS idx_report_sources_day ON report_sources (session_date, ticker);

CREATE TRIGGER IF NOT EXISTS final_reports_no_update BEFORE UPDATE ON reports
WHEN OLD.status = 'final' BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;

CREATE TRIGGER IF NOT EXISTS final_reports_no_delete BEFORE DELETE ON reports
WHEN OLD.status = 'final' BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;
"""

# The tickers and sources of a final report are locked too.
for _table in ("report_tickers", "report_sources"):
    for _op, _row in (("INSERT", "NEW"), ("UPDATE", "OLD"), ("DELETE", "OLD")):
        SCHEMA += f"""
CREATE TRIGGER IF NOT EXISTS {_table}_final_no_{_op.lower()} BEFORE {_op} ON {_table}
WHEN (SELECT status FROM reports WHERE session_date = {_row}.session_date) = 'final'
BEGIN SELECT RAISE(ABORT, 'final reports are permanent'); END;
"""

# Columns added after the first version. connect() adds them to older databases.
ADDED_TICKER_COLUMNS = {
    "benchmark": "TEXT", "benchmark_return_pct": "REAL", "market_return_pct": "REAL",
    "vs_benchmark_pct": "REAL", "vs_benchmark_zscore": "REAL", "move_read": "TEXT", "context_summary": "TEXT",
}

# save_report() outcomes
CREATED, UPDATED, FINALIZED = "created", "updated", "finalized"
SKIPPED_FINAL, SKIPPED_STALE = "skipped_final_exists", "skipped_older_update"


def connect(path: Path | None = None, readonly: bool = False) -> sqlite3.Connection:
    """Open the database, creating it and its tables on first use.

    readonly=True opens it so that no write is possible (used by the API).
    """
    path = Path(path or DB_PATH)
    if readonly:
        if not path.exists():
            connect(path).close()  # create an empty database first
        conn = sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True, isolation_level=None)
    else:
        conn = sqlite3.connect(path, isolation_level=None, timeout=10)
        conn.execute("PRAGMA journal_mode = WAL")  # lets the API read while a run is writing
        conn.executescript(SCHEMA)
        _add_missing_columns(conn)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _add_missing_columns(conn) -> None:
    """Upgrade a database made by an earlier version. Existing rows (final ones included)
    are not changed: the new columns are simply empty for them."""
    existing = {row[1] for row in conn.execute("PRAGMA table_info(report_tickers)")}
    for name, kind in ADDED_TICKER_COLUMNS.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE report_tickers ADD COLUMN {name} {kind}")


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def is_final(conn: sqlite3.Connection, session_date: str) -> bool:
    row = conn.execute("SELECT status FROM reports WHERE session_date = ?", (session_date,)).fetchone()
    return bool(row) and row["status"] == "final"


def save_report(conn, *, session_date, status, title, body_md, as_of,
                cost_usd=0.0, scan=None, sources=()) -> str:
    """Save one run's report, following the storage rules. Returns what happened.

    scan:    the flag_events result ({"flagged": [...], "quiet": [...], "errors": [...]})
    sources: news items the agent looked at, each with a "ticker" key
    """
    if status not in ("intraday", "final"):
        raise ValueError("status must be 'intraday' or 'final'")
    now = _utc_now()
    conn.execute("BEGIN IMMEDIATE")  # one writer at a time
    try:
        conn.execute("PRAGMA defer_foreign_keys = ON")  # tickers can be written before their report row
        old = conn.execute("SELECT status, as_of FROM reports WHERE session_date = ?", (session_date,)).fetchone()

        if old and old["status"] == "final":
            outcome = SKIPPED_FINAL
        elif old and status == "intraday" and as_of < old["as_of"]:
            outcome = SKIPPED_STALE
        else:
            if old:  # replace the day's intraday details
                conn.execute("DELETE FROM report_tickers WHERE session_date = ?", (session_date,))
                conn.execute("DELETE FROM report_sources WHERE session_date = ?", (session_date,))
            _insert_details(conn, session_date, scan or {}, sources)
            finalized_at = now if status == "final" else None
            if old:
                conn.execute(
                    """UPDATE reports SET status = ?, title = ?, body_md = ?, as_of = ?,
                       revision = revision + 1, total_cost_usd = total_cost_usd + ?,
                       updated_at = ?, finalized_at = ? WHERE session_date = ?""",
                    (status, title, body_md, as_of, cost_usd, now, finalized_at, session_date))
            else:
                conn.execute(
                    """INSERT INTO reports (session_date, status, title, body_md, as_of, total_cost_usd,
                       created_at, updated_at, finalized_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (session_date, status, title, body_md, as_of, cost_usd, now, now, finalized_at))
            outcome = FINALIZED if status == "final" else (UPDATED if old else CREATED)
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return outcome


TICKER_COLUMNS = ("session_date", "ticker", "category", "price", "return_1d_pct", "return_5d_pct",
                  "return_zscore", "volume_vs_avg", "compared_to", "error", *ADDED_TICKER_COLUMNS)


def _insert_details(conn, session_date, scan, sources):
    rows = {}
    for category, key in (("flagged", "flagged"), ("quiet", "quiet"), ("error", "errors")):
        for m in scan.get(key) or []:
            context = m.get("context") or {}
            if "error" in context:  # comparison unavailable: keep the move, leave context empty
                context = {}
            rows[m["ticker"]] = (
                session_date, m["ticker"], category, m.get("last_close", m.get("last_price")),
                m.get("return_1d_pct"), m.get("return_5d_pct"), m.get("return_zscore"),
                m.get("volume_vs_avg"), m.get("compared_to"), m.get("error"),
                context.get("benchmark"), context.get("benchmark_return_pct"), context.get("market_return_pct"),
                context.get("vs_benchmark_pct"), context.get("vs_benchmark_zscore"), context.get("read"),
                context.get("summary"))
    conn.executemany(
        f"INSERT INTO report_tickers ({', '.join(TICKER_COLUMNS)}) VALUES ({', '.join('?' * len(TICKER_COLUMNS))})",
        rows.values())
    conn.executemany(
        """INSERT INTO report_sources (session_date, ticker, title, publisher, url, published)
           VALUES (?, ?, ?, ?, ?, ?)""",
        [(session_date, s.get("ticker"), s.get("title"), s.get("publisher"), s.get("url"),
          None if s.get("published") is None else str(s.get("published"))) for s in sources])


# ---------------------------------------------------------------------------
# Reading (used by the API and the command line)
# ---------------------------------------------------------------------------

def list_reports(conn, limit: int = 30, before: str | None = None, status: str | None = None) -> list[dict]:
    """Report summaries, newest first. before: only days earlier than this date."""
    sql = """SELECT r.session_date, r.status, r.title, r.as_of, r.revision,
                    r.created_at, r.updated_at, r.finalized_at,
                    (SELECT COUNT(*) FROM report_tickers t
                     WHERE t.session_date = r.session_date AND t.category = 'flagged') AS flagged_count
             FROM reports r WHERE 1 = 1"""
    params = []
    if before:
        sql += " AND r.session_date < ?"
        params.append(before)
    if status:
        sql += " AND r.status = ?"
        params.append(status)
    sql += " ORDER BY r.session_date DESC LIMIT ?"
    params.append(limit)
    return [dict(row) for row in conn.execute(sql, params)]


def get_report(conn, session_date: str) -> dict | None:
    """One full report: the brief plus every ticker's figures and the news sources used."""
    row = conn.execute("SELECT * FROM reports WHERE session_date = ?", (session_date,)).fetchone()
    if row is None:
        return None
    report = dict(row)
    report["tickers"] = [_ticker_row(t) for t in conn.execute(
        """SELECT * FROM report_tickers WHERE session_date = ?
           ORDER BY CASE category WHEN 'flagged' THEN 0 WHEN 'quiet' THEN 1 ELSE 2 END, ticker""",
        (session_date,))]
    report["sources"] = [dict(s) for s in conn.execute(
        """SELECT ticker, title, publisher, url, published FROM report_sources
           WHERE session_date = ? ORDER BY ticker, id""", (session_date,))]
    return report


def _ticker_row(row) -> dict:
    """One ticker's figures. SELECT * so a database from an earlier version still reads
    (it just has no context columns yet)."""
    data = dict(row)
    data.pop("session_date", None)
    for name in ADDED_TICKER_COLUMNS:
        data.setdefault(name, None)
    return data


def latest_report(conn) -> dict | None:
    row = conn.execute("SELECT session_date FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()
    return get_report(conn, row["session_date"]) if row else None


def ticker_history(conn, ticker: str, limit: int = 30) -> list[dict]:
    """One ticker's figures across days, newest first (for charts)."""
    rows = conn.execute(
        """SELECT t.*, r.status FROM report_tickers t JOIN reports r ON r.session_date = t.session_date
           WHERE t.ticker = ? ORDER BY t.session_date DESC LIMIT ?""",
        (ticker.upper(), limit))
    return [{"session_date": row["session_date"], **_ticker_row(row)} for row in rows]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Browse saved reports.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list the most recent reports")
    show = commands.add_parser("show", help="print one report")
    show.add_argument("date", nargs="?", default="latest", help="YYYY-MM-DD or 'latest'")
    args = parser.parse_args()

    conn = connect(readonly=True)
    if args.command == "list":
        for r in list_reports(conn, limit=50):
            print(f"{r['session_date']}  {r['status']:<8}  rev {r['revision']:<3} "
                  f"{r['flagged_count']} flagged  {r['title']}")
    else:
        report = latest_report(conn) if args.date == "latest" else get_report(conn, args.date)
        print(report["body_md"] if report else "No report found.")
```

### ask.py

```python
"""Answer questions about saved reports with Claude, using retrieval (RAG).

For each question it gathers, within a size limit:
1. Figures across days for any watchlist ticker named in the question.
2. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
3. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import reports_db
import search_index

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports, passages and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05). Passages carry the date of the report they came from.
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
MAX_CONTEXT_CHARS = 60_000       # keeps each question's cost predictable

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],                      # answers only from the text it's given
    max_turns=1,
    max_budget_usd=0.25,           # hard stop on cost per question
    include_partial_messages=True,  # stream the answer as it's written
)


def mentioned_tickers(conn, question: str) -> list[str]:
    """Tickers from the reports that the question names (any letter case)."""
    known = {row[0] for row in conn.execute("SELECT DISTINCT ticker FROM report_tickers")}
    words = {w.upper() for w in re.findall(r"[A-Za-z][A-Za-z.\-]{0,9}", question)}
    return sorted(words & known)


def find_passages(question: str) -> list[dict]:
    """The retrieval step. If the index isn't available, Ask still works from recent reports."""
    try:
        search_index.sync(embed_now=False)  # make sure the newest reports are searchable
        return search_index.search(question, limit=PASSAGES)["results"]
    except Exception:
        return []


def build_context(conn, question: str) -> tuple[str, list[str]]:
    """The material Claude answers from, and the report dates it draws on."""
    days = [r["session_date"] for r in reports_db.list_reports(conn, limit=RECENT_REPORTS)]
    tickers = mentioned_tickers(conn, question)
    for ticker in tickers:
        days += [row[0] for row in conn.execute(
            """SELECT session_date FROM report_tickers WHERE ticker = ? AND category = 'flagged'
               ORDER BY session_date DESC LIMIT ?""", (ticker, FLAGGED_REPORTS_PER_TICKER))]
    days = sorted(set(days), reverse=True)

    parts, used, size = [], set(), 0

    def add(text: str, day: str | None = None) -> bool:
        nonlocal size
        if size + len(text) > MAX_CONTEXT_CHARS:
            return False
        parts.append(text)
        size += len(text)
        if day:
            used.add(day)
        return True

    for ticker in tickers:
        lines = [f"## Figures for {ticker} (newest first)",
                 "date | status | category | return % | z-score | volume vs normal | vs sector (points) | kind of move"]
        for h in reports_db.ticker_history(conn, ticker, limit=60):
            vs_sector = "" if h["vs_benchmark_pct"] is None else f"{h['vs_benchmark_pct']} vs {h['benchmark']}"
            lines.append(f"{h['session_date']} | {h['status']} | {h['category']} | {h['return_1d_pct']} | "
                         f"{h['return_zscore']} | {h['volume_vs_avg']} | {vs_sector} | {h['move_read'] or ''}")
        add("\n".join(lines))

    # Retrieved passages from reports that aren't already included in full
    for p in find_passages(question):
        if p["session_date"] not in days:
            add(f"## Passage from the report of {p['session_date']} ({p['status']}): {p['heading']}\n\n{p['text']}",
                p["session_date"])

    for day in days:
        report = reports_db.get_report(conn, day)
        if not add(f"## Report {day} ({report['status']}, as of {report['as_of']})\n\n{report['body_md']}", day):
            break
    return "\n\n---\n\n".join(parts), sorted(used, reverse=True)


def gather(question: str) -> tuple[str, list[str]]:
    with closing(reports_db.connect(readonly=True)) as conn:
        return build_context(conn, question)


async def answer(question: str, emit) -> dict:
    """Answer one question. emit(event) receives {"type": "delta", "text": ...} as the
    answer is written, then {"type": "done", ...}. Returns the done event."""
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"questions must be 1 to {MAX_QUESTION_CHARS} characters")
    context, used = await asyncio.to_thread(gather, question)  # searching can take a moment
    if not used:
        event = {"type": "done", "answer": "There are no saved reports yet, so there's nothing to answer from.",
                 "reports_used": [], "cost_usd": 0}
        emit(event)
        return event

    prompt = f"Saved reports:\n\n{context}\n\n---\n\nQuestion: {question}"
    streamed, result = "", None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, StreamEvent):
            event = message.event
            if event.get("type") == "content_block_delta" and event.get("delta", {}).get("type") == "text_delta":
                streamed += event["delta"]["text"]
                emit({"type": "delta", "text": event["delta"]["text"]})
        elif isinstance(message, ResultMessage):
            result = message

    if result is None or result.is_error:
        raise RuntimeError(f"Claude couldn't answer: {result.subtype if result else 'no result'}")
    event = {"type": "done", "answer": result.result or streamed, "reports_used": used,
             "cost_usd": round(result.total_cost_usd or 0, 4)}
    emit(event)
    return event
```

### frontend/src/format.js

```javascript
// Display helpers

export const formatDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

export const formatMonth = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

export const formatShortDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export const formatMonthShort = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short' })

export const formatTime = (utc) =>
  utc ? new Date(utc).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ''

export const number = (value, digits) => (value == null ? '—' : value.toFixed(digits))

export const percent = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`)

// Percentage points, for a gap between two percentages (e.g. a stock vs. its sector)
export const points = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)} pts`)

// Only allow normal web links from news sources
export const safeUrl = (url) => (/^https?:\/\//i.test(url || '') ? url : undefined)
```

### frontend/src/components/TickerTable.jsx

```jsx
import { useOpenChart } from '../chartContext'
import { number, percent, points } from '../format'

const ChartIcon = () => (
  <svg className="chart-icon" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
    <polyline points="1,10 4,6 7,8 11,2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

// Click a row (or Tab to its ticker and press Enter) to open that ticker's chart
export default function TickerTable({ tickers }) {
  const openChart = useOpenChart()
  if (!tickers?.length) return null
  return (
    <div className="table-wrap">
      <table className="tickers">
        <thead>
          <tr>
            <th>Ticker</th>
            <th>Status</th>
            <th className="num">Price</th>
            <th className="num">Change</th>
            <th className="num">z-score</th>
            <th className="num">Volume</th>
            <th className="num">Vs. sector</th>
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => (
            <tr
              key={t.ticker}
              className={`${t.category} clickable`}
              onClick={(e) => openChart(t.ticker, e.currentTarget.querySelector('button'))}
            >
              <td className="ticker">
                <button type="button" className="ticker-button" aria-label={`Show ${t.ticker} chart`} title="Show chart">
                  {t.ticker} <ChartIcon />
                </button>
              </td>
              <td>{t.category === 'error' ? <span title={t.error}>data issue</span> : t.category}</td>
              <td className="num">{number(t.price, 2)}</td>
              <td className={`num ${t.return_1d_pct > 0 ? 'up' : t.return_1d_pct < 0 ? 'down' : ''}`}>
                {percent(t.return_1d_pct)}
              </td>
              <td className="num">{number(t.return_zscore, 1)}</td>
              <td className="num">{t.volume_vs_avg == null ? '—' : `${t.volume_vs_avg}×`}</td>
              <td className="num vs-sector" title={t.context_summary || undefined}>
                {t.vs_benchmark_pct == null ? (
                  '—'
                ) : (
                  <>
                    {points(t.vs_benchmark_pct)} <span className="muted">vs {t.benchmark}</span>
                    {t.move_read && <span className="move-read">{t.move_read}</span>}
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
```

### frontend/src/components/RunPanel.jsx

```jsx
import { useState } from 'react'
import { startRun } from '../api'
import { formatTime } from '../format'

const STEP_NAMES = {
  flag_events: () => 'Scanning the watchlist',
  get_news: (input) => `Reading news for ${input.ticker}`,
  compute_moves: (input) => `Checking ${input.ticker} in detail`,
  market_backdrop: () => 'Checking the market and sectors',
}

function describe(event) {
  switch (event.type) {
    case 'started':
      return `Writing the ${event.status} report for ${event.session_date}`
    case 'tool_call': {
      const name = event.tool.split('__').pop()
      return (STEP_NAMES[name] || (() => name))(event.input || {})
    }
    case 'saved':
      return `Saved (${event.outcome.replaceAll('_', ' ')}) · $${event.cost_usd.toFixed(3)}`
    default:
      return event.message || event.type
  }
}

export default function RunPanel({ run, onStarted }) {
  const [error, setError] = useState(null)
  const [sending, setSending] = useState(false)
  const running = run?.state === 'running'

  const start = async () => {
    setSending(true)
    setError(null)
    try {
      onStarted(await startRun())
    } catch (e) {
      setError(e.message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="panel">
      <h2>Request a fresh report</h2>
      <p className="muted small">
        Runs the agent now: an intraday update while the market is open, or the final report once it has closed.
      </p>
      <button className="primary" onClick={start} disabled={running || sending}>
        {running ? 'Writing report…' : 'Run update now'}
      </button>
      {error && <p className="error">{error}</p>}

      {run && run.state !== 'idle' && (
        <div className="run-log" aria-live="polite">
          <p className="muted small">
            {run.state === 'running' && `In progress · started ${formatTime(run.started_at)}`}
            {run.state === 'finished' && `Finished ${formatTime(run.finished_at)}`}
            {run.state === 'failed' && `Failed ${formatTime(run.finished_at)}`}
          </p>
          <ol>
            {run.log.map((event, i) => (
              <li key={i}>{describe(event)}</li>
            ))}
          </ol>
          {run.state === 'failed' && <p className="error">{run.error}</p>}
        </div>
      )}
    </section>
  )
}
```

### frontend/src/styles.css

```css
:root {
  --bg: #f6f7f9;
  --panel: #ffffff;
  --text: #1c2430;
  --muted: #5f6b7a;
  --border: #e2e6eb;
  --accent: #2456d6;
  --accent-text: #ffffff;
  --up: #12805c;
  --down: #c0392b;
  --live: #b45309;
  --live-bg: #fef3c7;
  --final: #1f6f43;
  --final-bg: #dcfce7;
  --flagged-bg: #fff7ed;
  --series-1: #2a78d6;   /* chart line (validated palette, light) */
  --grid: #e6e9ee;
  --mark-up: #12805c;    /* flagged-day markers; shape (▲▼) carries direction too */
  --mark-down: #c0392b;
  --radius: 10px;
  font-family: system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif;
  color: var(--text);
  background: var(--bg);
  line-height: 1.5;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #0f1419;
    --panel: #171d24;
    --text: #e6e9ed;
    --muted: #97a3b1;
    --border: #2a323c;
    --accent: #5b8cff;
    --accent-text: #0b1020;
    --up: #34d399;
    --down: #f87171;
    --live: #fbbf24;
    --live-bg: #3a2a07;
    --final: #4ade80;
    --final-bg: #0d2e1b;
    --flagged-bg: #2a1d0f;
    --series-1: #3987e5;  /* stepped for the dark surface, validated separately */
    --grid: #252d37;
    --mark-up: #1f9d63;
    --mark-down: #e66767;
  }
}

* { box-sizing: border-box; }
body { margin: 0; }

.app { max-width: 1280px; margin: 0 auto; padding: 16px; }

.topbar { display: flex; align-items: center; gap: 24px; margin-bottom: 16px; flex-wrap: wrap; }
.topbar h1 { font-size: 1.4rem; margin: 0; }
.topbar .connection { margin-left: auto; }

.tabs { display: flex; gap: 4px; }
.tab {
  color: var(--muted); text-decoration: none; font-weight: 600; font-size: 0.95rem;
  padding: 6px 12px; border-radius: 8px;
}
.tab:hover { color: var(--text); background: var(--panel); }
.tab.active { color: var(--text); background: var(--panel); box-shadow: inset 0 -2px 0 var(--accent); }
.connection { font-size: 0.85rem; display: inline-flex; align-items: center; gap: 6px; color: var(--muted); }
.connection::before { content: ''; width: 8px; height: 8px; border-radius: 50%; background: var(--down); }
.connection.on::before { background: var(--up); }

.layout { display: grid; grid-template-columns: minmax(0, 2fr) minmax(0, 1fr); gap: 16px; align-items: start; }
.side { display: grid; gap: 16px; }
@media (max-width: 960px) { .layout { grid-template-columns: minmax(0, 1fr); } }

.panel { background: var(--panel); border: 1px solid var(--border); border-radius: var(--radius); padding: 16px 20px; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.section-head > h2 { margin-bottom: 0; }
.panel > h2, .section-head > h2 { font-size: 1rem; margin: 0 0 12px; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.previous { margin-top: 16px; }

.muted { color: var(--muted); }
.small { font-size: 0.85rem; }
.error { color: var(--down); }

button { font: inherit; cursor: pointer; }
button:disabled { cursor: not-allowed; opacity: 0.6; }
.primary { background: var(--accent); color: var(--accent-text); border: 0; border-radius: 8px; padding: 8px 16px; font-weight: 600; }
.chip { background: transparent; border: 1px solid var(--border); color: var(--text); border-radius: 999px; padding: 4px 10px; font-size: 0.8rem; }
.link { background: none; border: 0; color: var(--accent); padding: 8px 0; text-decoration: none; font-weight: 600; }
.link:hover { text-decoration: underline; }
.row { display: flex; align-items: center; gap: 12px; margin-top: 8px; flex-wrap: wrap; }
.examples { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 10px; }

textarea {
  width: 100%; font: inherit; color: var(--text); background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px; resize: vertical;
}

.badge { display: inline-block; font-size: 0.75rem; font-weight: 600; border-radius: 999px; padding: 2px 8px; }
.badge.live { color: var(--live); background: var(--live-bg); }
.badge.final { color: var(--final); background: var(--final-bg); }

.report-head { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 12px; }

.table-wrap { overflow-x: auto; margin-bottom: 8px; }
.tickers { width: 100%; border-collapse: collapse; font-size: 0.9rem; }
.tickers th, .tickers td { padding: 6px 8px; border-bottom: 1px solid var(--border); text-align: left; white-space: nowrap; }
.tickers th { color: var(--muted); font-weight: 600; font-size: 0.8rem; }
.tickers .num { text-align: right; font-variant-numeric: tabular-nums; }
.tickers .ticker { font-weight: 600; }
.tickers tr.flagged { background: var(--flagged-bg); }
.tickers tr.error { color: var(--muted); }
.up { color: var(--up); }
.down { color: var(--down); }

.markdown { overflow-wrap: anywhere; }
.markdown h1 { font-size: 1.3rem; margin: 12px 0 8px; }
.markdown h2 { font-size: 1.1rem; margin: 16px 0 6px; }
.markdown h3 { font-size: 1rem; margin: 14px 0 4px; }
.markdown a { color: var(--accent); }
.markdown ul { padding-left: 20px; }

.sources { margin-top: 12px; font-size: 0.9rem; }
.sources summary { cursor: pointer; color: var(--muted); }
.sources a { color: var(--accent); }

.run-log { margin-top: 12px; border-top: 1px solid var(--border); padding-top: 8px; }
.run-log ol { margin: 0; padding-left: 20px; font-size: 0.9rem; }
.answer { margin-top: 12px; border-top: 1px solid var(--border); padding-top: 8px; }

/* Previous days preview (Today tab) */
.preview-cards { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 12px; }
@media (max-width: 760px) { .preview-cards { grid-template-columns: minmax(0, 1fr); } }
.preview-card {
  display: grid; gap: 10px; padding: 12px 14px; border: 1px solid var(--border); border-radius: 8px;
  color: var(--text); text-decoration: none; background: var(--bg);
}
.preview-card:hover { border-color: var(--accent); }
.preview-top { display: flex; align-items: center; justify-content: space-between; gap: 8px; flex-wrap: wrap; }
.preview-flagged { display: flex; flex-wrap: wrap; gap: 6px; align-items: center; }
.tick { font-size: 0.8rem; font-weight: 600; border: 1px solid var(--border); border-radius: 6px; padding: 2px 6px; background: var(--panel); }

/* Previous days tab */
.previous-grid { display: grid; grid-template-columns: 260px minmax(0, 1fr); gap: 16px; align-items: start; }
.day-list { max-height: 75vh; overflow-y: auto; }
@media (max-width: 760px) {
  .previous-grid { grid-template-columns: minmax(0, 1fr); }
  .day-list { max-height: 40vh; }
}
.day-list ul { list-style: none; margin: 0 0 8px; padding: 0; display: grid; gap: 4px; }
.month { font-size: 0.8rem; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; margin: 8px 0 4px; }
.day {
  display: grid; gap: 2px; padding: 8px 10px; border: 1px solid transparent; border-radius: 8px;
  color: var(--text); text-decoration: none;
}
.day:hover { border-color: var(--border); }
.day.active { border-color: var(--accent); background: var(--bg); }
.day-date { font-weight: 600; }
.day-meta { font-size: 0.8rem; color: var(--muted); }

/* Ticker rows open a chart */
.tickers tr.clickable { cursor: pointer; }
.tickers .move-read { display: block; font-size: 0.75rem; color: var(--muted); }
.tickers tr.clickable:hover td { background: var(--bg); }
.ticker-button {
  all: unset; cursor: pointer; font-weight: 600; display: inline-flex; align-items: center; gap: 4px; border-radius: 4px;
}
.ticker-button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.chart-icon { color: var(--muted); }

/* Chart dialog */
.modal-backdrop {
  position: fixed; inset: 0; z-index: 10; display: grid; place-items: center; padding: 16px;
  background: rgb(0 0 0 / 0.45);
}
.modal {
  width: min(880px, 100%); max-height: calc(100vh - 32px); overflow: auto; padding: 20px;
  background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: var(--radius);
  box-shadow: 0 10px 40px rgb(0 0 0 / 0.25);
}
.modal-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; }
.modal-head h2 { margin: 0; font-size: 1.4rem; }
.close {
  width: 36px; height: 36px; font-size: 1.3rem; line-height: 1; color: var(--text);
  background: transparent; border: 1px solid var(--border); border-radius: 8px;
}
.range-row { display: flex; gap: 4px; margin: 12px 0; }
.range {
  padding: 4px 12px; font-size: 0.85rem; font-weight: 600; color: var(--text);
  background: transparent; border: 1px solid var(--border); border-radius: 8px;
}
.range.active { background: var(--accent); border-color: var(--accent); color: var(--accent-text); }
.chart-stats { display: flex; gap: 32px; flex-wrap: wrap; margin-bottom: 8px; }
.chart-stats div { display: grid; }
.chart-stats strong { font-size: 1.25rem; }
.refreshing { opacity: 0.5; transition: opacity 0.2s; } /* keeps the old chart while a new range loads */
.table-title { font-size: 0.9rem; margin: 16px 0 6px; }
@media (max-width: 760px) {
  .modal { padding: 14px; }
  .chart-stats { gap: 16px; }
}

/* The price chart */
.price-chart { position: relative; outline: none; border-radius: 8px; }
.price-chart:focus-visible { box-shadow: 0 0 0 2px var(--accent); }
.price-chart svg { display: block; }
.grid { stroke: var(--grid); stroke-width: 1; }
.axis-label { fill: var(--muted); font-size: 11px; font-variant-numeric: tabular-nums; }
.price-line { fill: none; stroke: var(--series-1); stroke-width: 2; stroke-linejoin: round; stroke-linecap: round; }
.crosshair { stroke: var(--muted); stroke-width: 1; }
/* Dots and markers get a 2px ring in the surface color, so they stay clear where they cross the line */
.end-dot, .hover-dot, .flag-marker { stroke: var(--panel); stroke-width: 4; paint-order: stroke; }
.end-dot, .hover-dot { fill: var(--series-1); }
.flag-marker.up { fill: var(--mark-up); }
.flag-marker.down { fill: var(--mark-down); }
.end-label { fill: var(--text); font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
.hit-area { fill: transparent; }
.hit-area.clickable { cursor: pointer; }
.chart-tooltip {
  position: absolute; top: 8px; pointer-events: none; display: grid; gap: 2px; min-width: 150px; max-width: 240px;
  padding: 8px 10px; font-size: 0.85rem; background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
  box-shadow: 0 4px 16px rgb(0 0 0 / 0.12);
}
.chart-tooltip strong { font-size: 1rem; font-variant-numeric: tabular-nums; }
.tip-flag { display: grid; gap: 2px; margin-top: 4px; padding-top: 4px; border-top: 1px solid var(--border); }

/* Search (Previous days tab) */
.panel.search { margin-bottom: 16px; }
.search-row { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.search-row input {
  flex: 1; min-width: 0; font: inherit; color: var(--text); background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px; padding: 8px 10px;
}
.search-results { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 14px; }
.result-day { display: inline-flex; align-items: center; gap: 8px; color: var(--text); text-decoration: none; }
.result-day:hover .day-date { text-decoration: underline; }
.passage { margin-top: 6px; padding-left: 10px; border-left: 2px solid var(--border); }
.passage-head { display: flex; gap: 8px; align-items: baseline; flex-wrap: wrap; }
.passage-text {
  margin: 2px 0 0; font-size: 0.9rem; overflow-wrap: anywhere;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}
mark { background: var(--live-bg); color: inherit; border-radius: 2px; padding: 0 1px; }
```

### tests/test_sector_context.py

```python
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
```
