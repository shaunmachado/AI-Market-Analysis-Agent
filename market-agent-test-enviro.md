# Market Analyst Agent: Test Environment

A separate test environment with **two months of sample reports**, so you can see how the app behaves after long-term use: paging through weeks of history, month grouping, earnings days, a day that was never finalized, and questions about trends over time.

It runs your **real program's code** against its **own sample database**. Claude, market data and Voyage AI (for search) are simulated by default, so it costs nothing and needs no internet. It lives in its own folder next to `market-agent/` and **never writes anything into your program's folder**. An automated test checks this every time.

This builds on `market-agent-rag.md`. Your program should include everything up to that guide: the Previous days tab, charts, and search.

**Already set this up for an earlier version?** Replace `sample_market.py`, `testenv.py` and `test_testenv.py` with the appendix versions, then run `python testenv.py seed --reset` and `python testenv.py build-frontend`.

---

## Contents

1. [What you get](#1-what-you-get)
2. [How it stays separate from your program](#2-how-it-stays-separate-from-your-program)
3. [Before you start](#3-before-you-start)
4. [Set it up](#4-set-it-up)
5. [What's in the sample data](#5-whats-in-the-sample-data)
6. [Things to test with two months of data](#6-things-to-test-with-two-months-of-data)
7. [Commands reference](#7-commands-reference)
8. [Using real Claude (optional)](#8-using-real-claude-optional)
9. [Test the test environment](#9-test-the-test-environment)
10. [Keeping it in step with your program](#10-keeping-it-in-step-with-your-program)
11. [Troubleshooting](#11-troubleshooting)
12. [Removing it](#12-removing-it)
13. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What you get

```
projects/
├── market-agent/                  your working program (never changed)
│   ├── api.py, run_brief.py, reports_db.py, ask.py, ...
│   ├── reports.db                 your real reports (never opened)
│   └── frontend/
└── market-agent-testenv/          the test environment (new)
    ├── sample_market.py           simulates 2 months of market data and news
    ├── testenv.py                 seed, serve, simulate runs, status, reset
    ├── test_testenv.py            checks the sample data and the isolation
    ├── data/                      created by `seed`
    │   ├── reports.db             the sample database
    │   ├── search.db              its search index
    │   └── sample_config.json     the settings used, so data can be recreated
    └── frontend-dist/             created by `build-frontend`: your app, built here
```

```
 Browser ── http://localhost:8100 ──▶ testenv.py serve
                                        │ uses your real api.py, run_brief.py, ask.py, reports_db.py
                                        │ (read from market-agent/, never written)
                                        ├── reads/writes ──▶ market-agent-testenv/data/reports.db (+ search.db)
                                        ├── Claude ─────────▶ simulated (offline answers)
                                        ├── market data ────▶ simulated (sample_market.py), including chart prices
                                        └── Voyage AI ──────▶ simulated (topic-based stand-in for search)
```

| You can test | How |
|---|---|
| Two months of history in both tabs | Sample reports back to two months ago |
| Live updates from scheduled runs | `python testenv.py update` in another terminal |
| The end of a trading day | `python testenv.py finalize` |
| Run update now | Simulated agent: shows progress steps, saves a newer update, costs $0 |
| Ask about your reports | Offline answers built from the sample data, or real Claude with `--live-ask` |
| Charts | Simulated price history (a full year) that matches the sample reports, so markers and prices line up |
| Search and RAG | Two months of reports indexed for search, with a topic-based stand-in for Voyage, or real Voyage with `--live-embeddings` |
| A year or more of history | `python testenv.py seed --reset --months 12` |

---

## 2. How it stays separate from your program

| Risk | How it's prevented |
|---|---|
| Changing your real reports | The test environment uses its own database, `market-agent-testenv/data/reports.db`, and its own search index beside it. Before anything runs, it refuses to use any database inside `market-agent/`. |
| Changing your code | It only *reads* files in `market-agent/`. Python's cache folders (`__pycache__`) are switched off, so not even those get written. A test confirms every file in `market-agent/` is byte-for-byte unchanged. |
| Changing your frontend build | The app is built into `market-agent-testenv/frontend-dist/`. Your `frontend/dist/` is never touched. (Vite may update its own cache inside `node_modules`, as it does on any build.) |
| Clashing with the running app | The test app uses port **8100**. Your real API (8000) and dev server (5173) can run at the same time. |
| Spending money | Claude, market data and Voyage are simulated unless you choose `--live-ask`, `--live-runs` or `--live-embeddings`. |
| Interfering with scheduled runs | Your cron or Task Scheduler entries aren't touched, and the test environment has no schedule of its own. |
| Being set up in the wrong place | If the test folder is inside `market-agent/`, it refuses to run. |

**Which code it tests:** always the current code in `market-agent/`. When you change your program, the test environment picks up the change on its next start (section 10).

---

## 3. Before you start

- [ ] Your program includes everything up to `market-agent-rag.md`, and its tests pass (`pytest -v` in `market-agent/` shows `106 passed, 1 skipped`)
- [ ] You've run `npm install` in `market-agent/frontend` (from the frontend guide)
- [ ] You know where your `market-agent` folder is. The test environment goes **next to it**, in the same parent folder

**Python environment:** the test environment uses the same packages as your program and installs nothing new. The simplest option is to use your program's virtual environment, which only reads it. If you'd rather keep them completely separate, create a new one and run `pip install -r ../market-agent/requirements.txt pytest` in it.

---

## 4. Set it up

### Step 1: Create the folder

In the folder that contains `market-agent`, create `market-agent-testenv`:

```bash
cd path/to/projects          # the folder that contains market-agent
mkdir market-agent-testenv
cd market-agent-testenv
```

If your program's folder has a different name or location, set `MARKET_AGENT_DIR` to its full path before running any command:

```bash
export MARKET_AGENT_DIR=/full/path/to/market-agent          # macOS / Linux
$env:MARKET_AGENT_DIR = "C:\full\path\to\market-agent"       # Windows PowerShell
```

### Step 2: Add the three files

Create these in `market-agent-testenv/` with the code from the [appendix](#appendix-full-source-code):

| File | What it does |
|---|---|
| [`sample_market.py`](#sample_marketpy) | Simulates prices, volumes, earnings days and news on the real NYSE calendar, and writes briefs in the same format as your agent |
| [`testenv.py`](#testenvpy) | Every command: seed, status, build the app, serve, simulate runs, reset |
| [`test_testenv.py`](#test_testenvpy) | Checks the sample data, the simulated runs, and that your program is untouched |

### Step 3: Activate the Python environment

```bash
source ../market-agent/.venv/bin/activate          # macOS / Linux
..\market-agent\.venv\Scripts\Activate.ps1          # Windows PowerShell
```

### Step 4: Create the sample data

```bash
python testenv.py seed
```

This takes about a second. It prints a summary like this (for a run on 6 November 2026):

```json
{
  "database": ".../market-agent-testenv/data/reports.db",
  "main_project": ".../market-agent",
  "days": 44,
  "first_day": "2026-09-08",
  "last_day": "2026-11-06",
  "final": 42,
  "intraday": ["2026-10-08", "2026-11-06"],
  "flagged_rows": 29,
  "simulated_cost_usd": 4.38,
  "earnings_days": {"NVDA": "2026-09-15", "JPM": "2026-09-17", "MSFT": "2026-10-13", "AAPL": "2026-10-22", "AMZN": "2026-11-04"},
  "search_index": {"reports": 44, "passages": 73}
}
```

Your numbers will differ, because the sample ends on the day you run it and uses your watchlist.

### Step 5: Build the app into the test folder

```bash
python testenv.py build-frontend
```

This builds your React app from `market-agent/frontend` into `market-agent-testenv/frontend-dist/`. If it can't find npm, run the equivalent yourself from `market-agent/frontend`:

```bash
npm run build -- --outDir ../../market-agent-testenv/frontend-dist --emptyOutDir
```

### Step 6: Start it

```bash
python testenv.py serve
```

Open **http://localhost:8100**. You'll see the app over two months of sample reports. The terminal shows the mode:

```
Test environment: http://localhost:8100  ·  offline (no Claude, no cost)  ·  database .../market-agent-testenv/data/reports.db
```

Press Ctrl+C to stop it.

### Step 7: Check it

In a second terminal (same folder, same Python environment):

```bash
pytest -v
```

Expect `18 passed`. The last test confirms your `market-agent/` folder is exactly as it was.

---

## 5. What's in the sample data

| Item | Detail |
|---|---|
| **Date range** | Two calendar months back from today (or from `--end`), trading days only. Weekends and NYSE holidays are skipped: ending 6 Nov 2026 gives 8 Sep to 6 Nov, 44 trading days, with Labor Day skipped. |
| **Tickers** | Your `market-agent/watchlist.txt` (only read), or `--tickers` |
| **Prices and volume** | Simulated for each ticker with realistic day-to-day swings, plus market-wide moves. **Not real prices.** |
| **Earnings** | One earnings day per ticker within the range: a large move on heavy volume, with a matching headline |
| **Other news** | About a 4% chance per ticker per day of a news-driven move (upgrades, downgrades, product news and so on), and roughly one market-wide day every 20 sessions |
| **Unexplained moves** | Normal random swings sometimes cross the flagging threshold. Those say "No clear catalyst found", as your agent should. |
| **News sources** | Fictional publishers (Sample Wire, Demo Markets Daily, Example Financial News) linking to `news.example.com`, a domain reserved for examples |
| **How reports were saved** | Through your real `save_report()`, following the real storage rules. Most days have intraday updates at 10:45 and 12:30, then a final report at 8:16 the next morning (or 4:30pm the same day), with timestamps to match. |
| **Edge cases** | One day mid-range was never finalized and shows "Intraday (not finalized)". The latest day is left as a live intraday report if the range ends on a trading day. Early-close days say so in the brief. |
| **Marked as sample** | Every brief says "Sample data for the test environment: prices and news are simulated." |
| **Repeatable** | The same settings always give identical data. Use `--seed` with any number for a different set. |
| **Simulated cost** | Each report has a plausible Claude cost, so cost totals have data. No money is spent. |
| **Search index** | Built when you seed, using a stand-in for Voyage that recognises topics (for example "profit", "earnings" and "quarterly" are one topic; "downgrade" and "rating cut" are another). It's much simpler than real embeddings, but it shows meaning-based matching working. `update` and `finalize` keep the index current |
| **Chart prices** | A full year of simulated daily prices per ticker, so the 1Y chart is complete. On days in the reports, the chart's close matches the report's price. While the latest day is intraday, the chart ends at the same move as today's report. |

The flagging, z-scores and volume figures follow the same rules as `market_tools.py`, so the tables, badges and briefs look exactly like real ones.

---

## 6. Things to test with two months of data

Work through these with `python testenv.py serve` running. Run `python testenv.py status` for the dates mentioned below (your earnings days, and the day that was never finalized).

**History and navigation**

- [ ] The Today tab's preview shows exactly the 3 days before the latest report
- [ ] The Previous days tab shows "30+ days", groups days under month headings, and **Load older days** brings in the rest (43 in the example), all the way back to the first day
- [ ] The day listed under `intraday` in `status` (other than today) shows **Intraday (not finalized)**
- [ ] Each `earnings_days` date shows a large move, "Quarterly results…" and a source link
- [ ] Copying a day's address (such as `http://localhost:8100/#/previous/2026-10-13`) into a new browser tab opens that day, and the Back button steps through days and tabs
- [ ] At phone width, the day list scrolls by itself and picking a day scrolls to its report

**A trading day in progress**

- [ ] **Run update now** shows "Scanning the watchlist", a "Reading news for…" line for each flagged ticker, then "Saved (updated) · $0.000", and the latest report moves on 15 minutes
- [ ] Pressing it again straight away shows the cooldown message. In the test environment it's 15 seconds; set `RUN_COOLDOWN_SECONDS=0` before `serve` to switch it off
- [ ] In a second terminal, `python testenv.py update` simulates a scheduled run. The open page updates within about 2 seconds, without a refresh
- [ ] `python testenv.py finalize` simulates the end-of-day run. The badge switches to **Final** live, and a later **Run update now** says the report is already saved

**Questions over long history**

- [ ] "Why was NVDA flagged?" (any ticker) streams an offline answer listing how many days it was flagged and the most recent dates. Check those against the Previous days tab
- [ ] A question without a ticker ("What moved the most?") lists the most-flagged tickers
- [ ] With `--live-ask` (section 8), real Claude's answers cite report dates from across the two months, including older earnings days for a ticker you name

**Charts**

- [ ] Clicking a ticker row opens its chart. The ▲/▼ markers fall on the days `status` and the Previous days tab show as flagged, and the "Flagged in reports" count matches the table under the chart
- [ ] 1M, 3M, 6M and 1Y show 21, 63, 126 and 252 days of prices
- [ ] An earnings day (from `status`) shows a big jump or drop with a marker. Clicking it opens that day's report
- [ ] After `python testenv.py update`, reopening a chart shows the new intraday price as its last point

**Search and RAG**

- [ ] On the Previous days tab, the "earnings" example finds every `earnings_days` date from `status`. The reports say "quarterly results", so this is a match by meaning
- [ ] "quarterly" matches the same days by keyword, with the word highlighted; "profit" finds them by meaning only
- [ ] Clicking a result opens that day's report below the search box
- [ ] Nonsense such as "zzzz" says "No matching passages."
- [ ] Ask "Which companies reported profits?": the offline answer lists the passages it retrieved
- [ ] After `python testenv.py update` or `finalize`, the new report is searchable straight away
- [ ] With `serve --live-embeddings` (section 8), the top right of the search box says "By meaning and keywords" and real Voyage results look sensible. This is a good place to tune `MEANING_CUTOFF` (RAG guide, section 11)

**Scale**

- [ ] `python testenv.py seed --reset --months 12` creates a year (about 250 trading days). Check that both tabs stay fast and **Load older days** pages through it all
- [ ] Your data in API form: `http://localhost:8100/api/tickers/NVDA/history?limit=365` returns every day's figures for charts

**Resetting between sessions:** sample data is fixed at the moment you seed it. To make "today" match the real date again, run `python testenv.py seed --reset`.

---

## 7. Commands reference

Run every command from `market-agent-testenv/` with the Python environment active.

| Command | What it does |
|---|---|
| `python testenv.py seed` | Creates the sample data. Options below |
| `python testenv.py status` | Date range, report counts, the not-finalized day(s), earnings days and paths |
| `python testenv.py build-frontend` | Builds your app into `frontend-dist/` (run again after changing the frontend) |
| `python testenv.py serve` | Runs the app at http://localhost:8100 over the sample data |
| `python testenv.py update` | Saves a newer intraday update for the latest day, 15 minutes after the last (like a scheduled run) |
| `python testenv.py finalize` | Saves the latest day's final report (like the after-close or morning run) |
| `python testenv.py reset` | Deletes the sample data and its search index (only files in `market-agent-testenv/data/`) |

**`seed` options**

| Option | Default | Effect |
|---|---|---|
| `--months N` | `2` | How far back the sample goes |
| `--end YYYY-MM-DD` | today | Last day of the sample |
| `--seed N` | `7` | A different, but repeatable, set of sample data |
| `--tickers A,B,C` | your watchlist | Which tickers to simulate |
| `--latest intraday` or `--latest final` | `intraday` if the end date is a trading day | Whether the latest day is still live or already final |
| `--reset` | off | Replaces existing sample data |

**`serve` options**

| Option | Effect |
|---|---|
| `--port N` | Use another port (default 8100) |
| `--live-ask` | Real Claude answers questions (section 8) |
| `--live-runs` | Run update now, and the charts, use the real agent and real market data (section 8) |
| `--live-embeddings` | Search and Ask's retrieval use real Voyage AI embeddings (section 8) |

**Settings:** set these before `serve` if you need them.

| Variable | Default here | Effect |
|---|---|---|
| `RUN_COOLDOWN_SECONDS` | `15` | Wait between Run now presses (your real app uses 300) |
| `REPORT_POLL_SECONDS` | `2` | How often the app checks for saves by other programs |
| `MARKET_AGENT_DIR` | `../market-agent` | Where your program is |

---

## 8. Using real Claude (optional)

Offline mode tests everything except Claude's and Voyage's own output. When you want to see real answers over long history, set `ANTHROPIC_API_KEY` in the terminal and start the server with a live option.

**Real answers to questions (recommended):**

```bash
python testenv.py serve --live-ask
```

Claude answers from the sample reports using your real `ask.py`. This is the best way to check how it handles two months of history. Each question costs up to $0.25, and answers will cite the fictional sample news.

**Real meaning-based search:**

```bash
python testenv.py serve --live-embeddings     # needs VOYAGE_API_KEY and `pip install voyageai`
```

On start, the sample passages are re-embedded with real Voyage AI, replacing the stand-in's vectors. This takes a few seconds and uses roughly 6,000 tokens (73 short sample passages), well within Voyage's free allowance. Search and Ask's retrieval then behave as they will with your real reports. Serving without the flag later switches back to the stand-in automatically. Combine it with `--live-ask` to see real answers built on real retrieval.

**Real agent runs:**

```bash
python testenv.py seed --reset --end YYYY-MM-DD      # use yesterday's date, so today has no sample report
python testenv.py serve --live-runs
```

Run update now then runs your real agent against real market data and saves a real report for today into the **test** database, after two months of sample history. This tests how a genuine report sits alongside long history. It costs the same as a normal run. In this mode the charts show real prices too, so they won't line up with the sample history.

Seed with yesterday as the end date first. If the sample already has a report for today, a real run is likely to be skipped: the sample report's time may be later than the real time, or the day may already be final.

---

## 9. Test the test environment

```bash
pytest -v
```

Expect `18 passed`. They use temporary databases, so they don't change your sample data.

| Test | Proves that |
|---|---|
| `test_calendar_follows_nyse_rules` | Holidays (Good Friday, observed July 4th, Labor Day, Thanksgiving) and early closes are correct |
| `test_sample_covers_two_months_of_trading_days` | The range runs from the first trading day two months back to the end date, weekdays only |
| `test_reports_were_stored_as_in_real_use` | 42 final reports, one never-finalized day plus a live today, revisions from real intraday updates, and realistic timestamps across the two months |
| `test_final_reports_are_permanent` | The real database protections apply to sample data too |
| `test_flagged_tickers_follow_the_flagging_rule` | Every flagged ticker meets the real threshold (z-score of ±2, or 2× volume) |
| `test_every_earnings_day_is_flagged_with_a_source` | Each ticker's earnings day is flagged, with a news source |
| `test_briefs_follow_the_agent_template` | Every brief has the same sections as your agent's, and the sample-data notice |
| `test_same_settings_give_the_same_data` | Seeding is repeatable, and `--seed` changes it |
| `test_app_serves_two_months_of_reports` | Your real API serves all 44 days, pages through the 43 earlier ones, and returns two months of ticker history |
| `test_offline_run_now_updates_the_latest_day` | Run now works offline: progress steps, a newer update 15 minutes later, $0 |
| `test_offline_run_now_skips_once_the_day_is_final` | After finalizing, Run now is skipped, as in real use |
| `test_offline_ask_answers_from_the_sample_data` | Offline answers list a ticker's flagged days, at $0 |
| `test_charts_show_the_simulated_prices` | Charts get a full year of simulated prices for each range; a flagged day's close matches its report, and today's last point matches today's intraday move |
| `test_search_over_two_months_of_sample_data` | Search finds every earnings day by keyword ("quarterly") and by meaning only ("profit"), nonsense finds nothing, and all 44 reports are indexed |
| `test_offline_ask_shows_the_passages_it_retrieved` | Offline Ask lists the passages retrieval found, including meaning-based ones |
| `test_update_and_finalize_simulate_scheduled_runs` | `update` and `finalize` follow the real storage rules and keep the search index current |
| `test_refuses_to_use_the_main_projects_database` | Pointing it at a database inside `market-agent/` is refused |
| `test_main_project_was_not_touched` | **Every file in `market-agent/` is unchanged** after all of the above. No `__pycache__` folders were created, and no search index was written there |

**How this was checked before writing this guide:**

- **The suite catches mistakes.** With the safeguard that stops `__pycache__` folders deliberately switched off, the last test failed, as it should.
- **It works in a real browser.** The real `testenv.py serve` command was driven in Chromium over two months of sample data. These all worked: the 3-day preview, 43 days of history with paging and month grouping, the never-finalized day, an earnings day, offline Run now, offline Ask, and `update` and `finalize` from another terminal appearing live. There were no browser errors.
- **Your program stayed untouched.** Afterwards, every file in the program's folder was byte-for-byte unchanged.
- **It scales.** A 12-month seed (252 trading days) took under a second.
- **Search works in it.** The search box and Ask's retrieval were checked in a browser over the sample data (RAG guide, section 9.2). Again, the main project was unchanged afterwards.
- **Charts work in it.** The chart was driven in a browser over the sample data, covering markers, ranges, hover, keyboard, opening reports from markers, phone width and dark mode. Afterwards, the main project was again unchanged by the test environment.

---

## 10. Keeping it in step with your program

| When you… | Do this in the test environment |
|---|---|
| Change Python code in `market-agent/` | Restart `serve`. It always uses your current code |
| Change the frontend | `python testenv.py build-frontend`, then restart `serve` |
| Change how reports are stored (`reports_db.py`) or split into passages (`search_index.py`) | `python testenv.py seed --reset`, so the sample database and search index are rebuilt |
| Change your watchlist | `python testenv.py seed --reset` to simulate the new tickers |
| Want "today" to match the real date | `python testenv.py seed --reset` |
| Add a feature that needs new sample data | Extend `sample_market.py` (for example, more event types) and add a check to `test_testenv.py` |

Run `pytest -v` in **both** folders after changes: the main project's tests check your program, and the test environment's tests check it against long history and confirm the two folders stay separate.

---

## 11. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Can't find the main project at …` | The test folder isn't next to `market-agent/`, or your program's folder has a different name. Move it, or set `MARKET_AGENT_DIR` (step 1). |
| `The test environment must be in its own folder, outside market-agent/` | The test folder was created inside your program. Move it next to `market-agent/` instead. |
| `Sample data already exists` | Add `--reset` to replace it: `python testenv.py seed --reset`. |
| `No sample data yet` | Run `python testenv.py seed` first. |
| `ModuleNotFoundError` (such as `starlette` or `claude_agent_sdk`) | The Python environment isn't active (step 3). |
| http://localhost:8100 shows "Not Found" | The app hasn't been built into the test folder. Run `python testenv.py build-frontend`, then restart `serve`. The API itself works without it. |
| `npm wasn't found` or `Run npm install …` | Install Node.js, or run `npm install` in `market-agent/frontend` (see the frontend guide). |
| `address already in use` | Something else is using port 8100. Use `python testenv.py serve --port 8101` and open that port. |
| **Please wait … seconds** after Run now | The test cooldown (15 seconds). Wait, or start `serve` with `RUN_COOLDOWN_SECONDS=0`. |
| Run now or `update` says the report is already saved | The latest day is final (after `finalize`, or with `--latest final`). Run `python testenv.py seed --reset` for a live day again. |
| The dates don't match today | Sample data is fixed when you seed it. Run `python testenv.py seed --reset`. |
| `update` doesn't show on the page | `serve` must be running from the same folder, so both use the same `data/` folder. |
| Search says "By keywords" with `--live-embeddings` | `VOYAGE_API_KEY` isn't set in that terminal, or `voyageai` isn't installed. Without `--live-embeddings`, the stand-in is used and it says "By meaning and keywords". |
| Search results look rougher than expected | Without `--live-embeddings`, matching by meaning uses the simple topic stand-in. Use `--live-embeddings` to judge real quality. |
| A test fails with `test_main_project_was_not_touched` | Something wrote into `market-agent/` during the tests. The assertion shows which files changed. Check that you're running the appendix version of `testenv.py`, which turns off `__pycache__` folders on its first lines. |

---

## 12. Removing it

Delete the `market-agent-testenv` folder. That's everything: nothing was installed or changed anywhere else.

---

## Appendix: full source code

### sample_market.py

```python
"""A simulated stock market for the test environment.

Generates realistic-looking but entirely made-up prices, volumes and news for the
watchlist, over any date range, and turns them into the same figures and briefs
the real agent produces. The same settings always give the same data.

Nothing here touches the internet, Claude, or the real program's database.
"""

import zlib
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

import numpy as np

ET = ZoneInfo("America/New_York")
WARMUP_DAYS = 260  # simulated sessions before the window: z-score history, and a full year for charts

# Daily volatility and starting price for common tickers; anything else gets the default
PROFILES = {
    "AAPL": (0.015, 190.0), "MSFT": (0.014, 410.0), "NVDA": (0.030, 120.0), "AMZN": (0.019, 180.0),
    "JPM": (0.013, 200.0), "GOOGL": (0.018, 165.0), "META": (0.024, 500.0), "TSLA": (0.035, 240.0),
}
DEFAULT_PROFILE = (0.020, 100.0)

PUBLISHERS = ["Sample Wire", "Demo Markets Daily", "Example Financial News"]  # fictional
CATALYSTS = {
    ("earnings", 1): "Quarterly results beat expectations and guidance was raised.",
    ("earnings", -1): "Quarterly results missed expectations.",
    ("news", 1): ["An analyst upgrade lifted the shares.", "A new product announcement drew buyers.",
                  "Reports of a large contract win."],
    ("news", -1): ["An analyst downgrade weighed on the shares.", "Regulatory concerns were reported.",
                   "A senior executive departure was announced."],
    ("macro", 1): "A broad market rally after economic data.",
    ("macro", -1): "A broad market sell-off after economic data.",
}


# ---------------------------------------------------------------------------
# Trading calendar (NYSE rules)
# ---------------------------------------------------------------------------

def _easter(year: int) -> date:
    a, b, c = year % 19, year // 100, year % 100
    d, e = b // 4, b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = c // 4, c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    return date(year, month, (h + l - 7 * m + 114) % 31 + 1)


def nyse_holidays(year: int) -> set[date]:
    def nth(month, weekday, n):
        first = date(year, month, 1)
        return first + timedelta(days=(weekday - first.weekday()) % 7 + 7 * (n - 1))

    def last(month, weekday):
        end = (date(year, month + 1, 1) if month < 12 else date(year + 1, 1, 1)) - timedelta(days=1)
        return end - timedelta(days=(end.weekday() - weekday) % 7)

    def observed(d):  # Saturday -> Friday, Sunday -> Monday
        return d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d

    days = {
        nth(1, 0, 3), nth(2, 0, 3), _easter(year) - timedelta(days=2), last(5, 0),
        observed(date(year, 6, 19)), observed(date(year, 7, 4)), nth(9, 0, 1), thanksgiving(year),
        observed(date(year, 12, 25)),
    }
    if date(year, 1, 1).weekday() != 5:  # NYSE doesn't close Dec 31 for a Saturday New Year's Day
        days.add(observed(date(year, 1, 1)))
    return days


def thanksgiving(year: int) -> date:
    first = date(year, 11, 1)
    return first + timedelta(days=(3 - first.weekday()) % 7 + 21)  # 4th Thursday


def early_closes(year: int) -> set[date]:
    """Days the market closes at 1pm."""
    days = {thanksgiving(year) + timedelta(days=1)}
    for d in (date(year, 7, 3), date(year, 12, 24)):
        if d.weekday() < 5 and d not in nyse_holidays(year):
            days.add(d)
    return days


def trading_days(start: date, end: date) -> list[date]:
    holidays = set().union(*(nyse_holidays(y) for y in range(start.year, end.year + 1)))
    days, d = [], start
    while d <= end:
        if d.weekday() < 5 and d not in holidays:
            days.append(d)
        d += timedelta(days=1)
    return days


def months_before(day: date, months: int) -> date:
    month_index = day.year * 12 + day.month - 1 - months
    year, month = divmod(month_index, 12)
    for d in range(day.day, 0, -1):  # e.g. 31 March minus one month -> 28/29 February
        try:
            return date(year, month + 1, d)
        except ValueError:
            continue


# ---------------------------------------------------------------------------
# The simulated market
# ---------------------------------------------------------------------------

class SampleMarket:
    def __init__(self, tickers: list[str], end: date, months: int = 2, seed: int = 7):
        self.tickers = list(dict.fromkeys(t.upper() for t in tickers))
        self.days = trading_days(months_before(end, months), end)  # the reporting window
        if not self.days:
            raise ValueError("no trading days in that range")
        warmup_start = self.days[0] - timedelta(days=int(WARMUP_DAYS * 1.6))
        warmup = [d for d in trading_days(warmup_start, self.days[0]) if d < self.days[0]][-WARMUP_DAYS:]
        self.all_days = warmup + self.days
        self.index = {d: i for i, d in enumerate(self.all_days)}
        self.early_closes = set().union(*(early_closes(y) for y in {d.year for d in self.days}))
        rng = np.random.default_rng(seed)
        n, w = len(self.all_days), len(warmup)

        market = rng.normal(0, 0.008, n)
        self.events = {}  # (ticker, day) -> (kind, direction)
        for i in rng.choice(np.arange(w, n), size=max(1, len(self.days) // 20), replace=False):
            direction = int(rng.choice([-1, 1]))
            market[i] = direction * rng.uniform(0.025, 0.035)
            for t in self.tickers:
                self.events[(t, self.all_days[i])] = ("macro", direction)

        self.returns, self.volumes, self.closes = {}, {}, {}
        live_ticker = self.tickers[int(rng.integers(len(self.tickers)))]  # gives the latest day a story
        for t in self.tickers:
            vol, start_price = PROFILES.get(t, DEFAULT_PROFILE)
            beta = rng.uniform(0.7, 1.3)
            r = rng.normal(0.0004, vol, n) + beta * market
            v = rng.uniform(5e6, 6e7) * rng.lognormal(0, 0.2, n)
            for i in range(w, n):
                if (t, self.all_days[i]) in self.events:
                    v[i] *= rng.uniform(1.6, 2.4)
            earnings = int(rng.integers(w + 3, n))  # one earnings day per ticker in the window
            direction = int(rng.choice([-1, 1], p=[0.35, 0.65]))
            r[earnings] = direction * rng.uniform(3.2, 5.0) * vol
            v[earnings] *= rng.uniform(2.6, 4.0)
            self.events[(t, self.all_days[earnings])] = ("earnings", direction)
            if t == live_ticker and (t, self.all_days[-1]) not in self.events:
                r[-1] = rng.uniform(2.6, 3.4) * vol
                v[-1] *= rng.uniform(2.0, 2.8)
                self.events[(t, self.all_days[-1])] = ("news", 1)
            for i in range(w, n):
                if i != earnings and (t, self.all_days[i]) not in self.events and rng.random() < 0.04:
                    direction = int(rng.choice([-1, 1]))
                    r[i] = direction * rng.uniform(2.3, 3.5) * vol
                    v[i] *= rng.uniform(1.8, 3.0)
                    self.events[(t, self.all_days[i])] = ("news", direction)
            self.returns[t], self.volumes[t] = r, v
            self.closes[t] = start_price * np.cumprod(1 + r)

    # -- figures --------------------------------------------------------------

    def figures(self, ticker: str, day: date, fraction: float = 1.0) -> dict:
        """flag_events-style figures for one ticker. fraction < 1 means part-way through the day."""
        i = self.index[day]
        r, v, c = self.returns[ticker], self.volumes[ticker], self.closes[ticker]
        baseline = r[i - 60:i]
        move = r[i] if fraction >= 1 else r[i] * min(1.0, fraction ** 0.5)  # moves build through the day
        z = (move - baseline.mean()) / (baseline.std(ddof=1) * (1 if fraction >= 1 else fraction ** 0.5))
        noise = np.random.default_rng(zlib.crc32(f"{ticker}{day}{fraction:.3f}".encode()))
        volume_ratio = v[i] / v[i - 20:i].mean() * (1 if fraction >= 1 else noise.uniform(0.9, 1.1))
        price = c[i - 1] * (1 + move)
        return {
            "ticker": ticker,
            "session": "complete" if fraction >= 1 else "in_progress",
            ("last_close" if fraction >= 1 else "last_price"): round(float(price), 2),
            "return_1d_pct": round(float(move) * 100, 2),
            "return_5d_pct": round(float(price / c[i - 5] - 1) * 100, 2),
            "return_zscore": round(float(z), 2),
            "volume_vs_avg": round(float(volume_ratio), 2),
            "compared_to": ("daily moves over the last 3 months" if fraction >= 1
                            else "the same time of day over the last 20 sessions"),
        }

    def scan(self, day: date, as_of: str | None = None, fraction: float = 1.0) -> dict:
        """The same shape as the real flag_events() result."""
        flagged, quiet = [], []
        for t in self.tickers:
            f = self.figures(t, day, fraction)
            if abs(f["return_zscore"]) >= 2 or f["volume_vs_avg"] >= 2:
                flagged.append(f)
            else:
                quiet.append({"ticker": t, "return_1d_pct": f["return_1d_pct"]})
        status = "complete" if fraction >= 1 else "in_progress"
        session = {"status": status, "as_of": as_of or day.isoformat()}
        return {"session": session, "flagged": flagged, "quiet": quiet, "errors": []}

    # -- news and briefs --------------------------------------------------------

    def catalyst(self, ticker: str, day: date) -> str | None:
        event = self.events.get((ticker, day))
        if not event:
            return None
        text = CATALYSTS[event]
        if isinstance(text, list):
            text = text[(day.toordinal() + len(ticker)) % len(text)]
        return text

    def news(self, ticker: str, day: date) -> list[dict]:
        """What get_news would return: a fictional headline for days with a real catalyst."""
        text = self.catalyst(ticker, day)
        if not text:
            return []
        kind, _ = self.events[(ticker, day)]
        publisher = PUBLISHERS[(day.toordinal() + len(ticker)) % len(PUBLISHERS)]
        published = datetime.combine(day, time(9, 5), ET).astimezone(ZoneInfo("UTC"))
        return [{
            "title": f"{ticker}: {text.rstrip('.')}",
            "publisher": publisher,
            "published": published.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "url": f"https://news.example.com/{day.isoformat()}/{ticker.lower()}-{kind}",
            "summary": text,
        }]

    def brief(self, scan: dict, day: date) -> str:
        """A brief in the same format as analyst_prompt.md asks the agent for."""
        session = scan["session"]
        intraday = session["status"] == "in_progress"
        lines = [f"# {'Intraday update' if intraday else 'Watchlist brief'}: {session['as_of']}", ""]
        if intraday:
            lines += [f"Market open: figures are as of {session['as_of']} and can change before the close.", ""]
        lines += ["*Sample data for the test environment: prices and news are simulated.*", ""]
        if day in self.early_closes:
            lines += ["Early close today: the market shut at 1pm.", ""]
        lines += ["## Notable moves", ""]
        if not scan["flagged"]:
            lines += ["Nothing unusual" + (" so far today." if intraday else " in this session."), ""]
        for m in scan["flagged"]:
            so_far = " so far today" if intraday else ""
            normal = "normal for this time of day" if intraday else "normal"
            lines += [
                f"### {m['ticker']}: {m['return_1d_pct']:+.2f}% (z-score {m['return_zscore']}, "
                f"volume {m['volume_vs_avg']}x normal)",
                f"- **What happened:** {m['ticker']} moved {m['return_1d_pct']:+.2f}%{so_far} on volume "
                f"{m['volume_vs_avg']}x {normal}.",
            ]
            news = self.news(m["ticker"], day)
            if news:
                lines.append(f"- **Likely why:** {news[0]['summary']} [{news[0]['publisher']}]({news[0]['url']})")
            else:
                lines.append("- **Likely why:** No clear catalyst found.")
            lines += ["- **Worth watching:** whether the move holds into the next session.", ""]
        quiet = ", ".join(f"{q['ticker']} ({q['return_1d_pct']:+.2f}%)" for q in scan["quiet"])
        lines += ["## Quiet", "", quiet or "None.", ""]
        return "\n".join(lines)

    def price_history(self, ticker: str, period: str) -> list[dict]:
        """Daily closes in the same shape as prices.fetch_prices(), ending on the latest sample day."""
        sessions = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252}[period]
        start = len(self.all_days) - sessions
        return [{"date": self.all_days[i].isoformat(), "close": round(float(self.closes[ticker][i]), 2),
                 "volume": int(self.volumes[ticker][i])} for i in range(start, len(self.all_days))]

    def sources(self, scan: dict, day: date) -> list[dict]:
        return [{**item, "ticker": m["ticker"]} for m in scan["flagged"] for item in self.news(m["ticker"], day)]
```

### testenv.py

```python
"""Test environment for the market analyst agent.

Runs the real program's code against its own database of simulated reports going
back two months, with Claude and market data faked by default. It lives in its own
folder next to market-agent/ and never writes anything into that folder.

    python testenv.py seed              create 2 months of sample reports
    python testenv.py status            summary of the sample data
    python testenv.py build-frontend    build the React app into this folder
    python testenv.py serve             run the app at http://localhost:8100
    python testenv.py update            simulate a scheduled intraday run (another program saving)
    python testenv.py finalize          simulate the run that writes the latest day's final report
    python testenv.py reset             delete the sample data

Search (RAG) works offline too: a simulated stand-in for Voyage AI ranks passages by
topic. Use `serve --live-embeddings` to try real Voyage embeddings on the sample data.
"""

import argparse
import asyncio
import json
import os
import random
import shutil
import subprocess
import sys
from contextlib import closing
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True                # never leave __pycache__ folders in the main project
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"   # ...including from programs started from here

HERE = Path(__file__).resolve().parent
MAIN = Path(os.environ.get("MARKET_AGENT_DIR") or HERE.parent / "market-agent").resolve()
DATA = HERE / "data"
DB_PATH = DATA / "reports.db"
FRONTEND_DIST = HERE / "frontend-dist"
PORT = 8100
ET = ZoneInfo("America/New_York")
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]

from sample_market import SampleMarket, trading_days  # noqa: E402  (after the bytecode setting)


# ---------------------------------------------------------------------------
# Safety: use the real code, never the real data
# ---------------------------------------------------------------------------

def connect_main(db_path: Path = DB_PATH):
    """Import the main project's reports_db, pointed at the test database.

    Refuses to run if the test environment or its database would be inside the main project.
    """
    db_path = Path(db_path).resolve()
    if not (MAIN / "reports_db.py").is_file():
        sys.exit(f"Can't find the main project at {MAIN}. Set MARKET_AGENT_DIR to its folder.")
    if HERE == MAIN or MAIN in HERE.parents:
        sys.exit("The test environment must be in its own folder, outside market-agent/.")
    if db_path.parent == MAIN or MAIN in db_path.parents:
        sys.exit(f"Refusing to use a database inside the main project: {db_path}")
    os.environ["REPORTS_DB"] = str(db_path)  # read by every main-project module that opens the database
    os.environ.pop("SEARCH_DB", None)        # so the search index sits next to the test database
    if str(MAIN) not in sys.path:
        sys.path.insert(0, str(MAIN))
    import reports_db
    reports_db.DB_PATH = db_path  # also covers the case where it was imported earlier
    return reports_db


def config_path(db_path: Path) -> Path:
    return Path(db_path).with_name("sample_config.json")


def load_market(db_path: Path = DB_PATH) -> SampleMarket:
    path = config_path(db_path)
    if not path.is_file():
        sys.exit("No sample data yet. Run: python testenv.py seed")
    config = json.loads(path.read_text())
    return SampleMarket(config["tickers"], date.fromisoformat(config["end"]), config["months"], config["seed"])


SIMULATED_TOPICS = {
    "rating down": ["downgrade", "rating cut", "cut its rating", "lowered its rating"],
    "rating up": ["upgrade", "raised its rating"],
    "results": ["quarterly", "earnings", "guidance", "profit"],
    "regulation": ["regulatory", "regulator", "investigation", "probe", "lawsuit"],
    "product": ["product", "launch"],
    "deal": ["contract", "deal"],
    "leadership": ["executive", "departure", "resign"],
    "market": ["broad market", "economic data", "rally", "sell-off"],
}


def install_fake_embeddings(search_index) -> None:
    """A free, offline stand-in for Voyage AI: each vector says which topics a text mentions,
    so different wording for the same thing still matches. Much simpler than the real thing."""
    import numpy as np

    def fake_embed(texts, input_type):
        vectors = []
        for text in texts:
            low = text.lower()
            # Passages get a small constant so none is all zeros; a query about no known topic
            # stays all zeros, so it matches nothing by meaning (only by keywords)
            bias = 0.1 if input_type == "document" else 0.0
            v = np.array([3.0 * sum(p in low for p in phrases) for phrases in SIMULATED_TOPICS.values()] + [bias],
                         dtype=np.float32)
            norm = np.linalg.norm(v)
            vectors.append((v / norm if norm else v).tolist())
        return vectors

    search_index.embed = fake_embed
    search_index.vector_search_available = lambda: True
    search_index.EMBED_MODEL = "simulated"  # real Voyage vectors replace these automatically


def update_search_index(db_path: Path = DB_PATH, live: bool = False) -> dict:
    """Index the sample reports for search (simulated embeddings unless live)."""
    connect_main(db_path)
    import search_index
    if not live:
        install_fake_embeddings(search_index)
    return search_index.sync()


def main_watchlist() -> list[str]:
    """The tickers in the main project's watchlist.txt (only read), or a default set."""
    path = MAIN / "watchlist.txt"
    if path.is_file():
        tickers = [ln.strip().upper() for ln in path.read_text().splitlines() if ln.strip() and not ln.startswith("#")]
        if tickers:
            return tickers
    return DEFAULT_TICKERS


# ---------------------------------------------------------------------------
# Seeding: two months of reports, written through the real storage rules
# ---------------------------------------------------------------------------

def _as_utc(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _save(reports_db, conn, market, day, scan, status, at: datetime, cost: float) -> str:
    """save_report() with the clock set to the simulated time, so timestamps look real."""
    real_clock = reports_db._utc_now
    reports_db._utc_now = lambda: _as_utc(at)
    try:
        body = market.brief(scan, day)
        return reports_db.save_report(
            conn, session_date=day.isoformat(), status=status, title=body.splitlines()[0][2:], body_md=body,
            as_of=scan["session"]["as_of"], cost_usd=round(cost, 4), scan=scan, sources=market.sources(scan, day))
    finally:
        reports_db._utc_now = real_clock


def seed_database(db_path: Path = DB_PATH, end: date | None = None, months: int = 2, seed: int = 7,
                  tickers: list[str] | None = None, latest: str | None = None) -> dict:
    """Create the sample database. Returns a summary."""
    reports_db = connect_main(db_path)
    db_path = Path(db_path)
    if db_path.exists():
        sys.exit(f"Sample data already exists at {db_path}. Use --reset to replace it.")
    end = end or datetime.now(ET).date()
    tickers = tickers or main_watchlist()
    market = SampleMarket(tickers, end, months, seed)
    latest_day = market.days[-1]
    latest = latest or ("intraday" if latest_day == end else "final")
    rng = random.Random(seed)
    not_finalized = market.days[len(market.days) // 2]  # one day whose final report was never written
    next_day = {d: n for d, n in zip(market.days, market.days[1:])}

    db_path.parent.mkdir(parents=True, exist_ok=True)
    config_path(db_path).write_text(json.dumps(
        {"end": end.isoformat(), "months": months, "seed": seed, "tickers": market.tickers}, indent=2))

    with closing(reports_db.connect(db_path)) as conn:
        for day in market.days:
            is_latest = day == latest_day
            stays_intraday = (is_latest and latest == "intraday") or day == not_finalized
            # Most days get intraday updates during market hours (10:45 and the 12:30 schedule)
            if stays_intraday or rng.random() < 0.8:
                for at, fraction in ((time(10, 45), 0.25), (time(12, 30), 0.5)):
                    as_of = f"{day} {at:%H:%M} ET"
                    _save(reports_db, conn, market, day, market.scan(day, as_of, fraction), "intraday",
                          datetime.combine(day, at, ET) + timedelta(minutes=1), rng.uniform(0.02, 0.05))
            if stays_intraday:
                continue
            # The final report: usually the next morning's 8:15 run, sometimes a run after the close
            if is_latest or rng.random() < 0.3:
                finalized = datetime.combine(day, time(16, 30), ET)
            else:
                finalized = datetime.combine(next_day[day], time(8, 16), ET)
            _save(reports_db, conn, market, day, market.scan(day), "final", finalized, rng.uniform(0.03, 0.06))
    update_search_index(db_path)
    return status_summary(db_path)


def status_summary(db_path: Path = DB_PATH) -> dict:
    reports_db = connect_main(db_path)
    with closing(reports_db.connect(db_path, readonly=True)) as conn:
        row = conn.execute("""SELECT COUNT(*) AS days, MIN(session_date) AS first, MAX(session_date) AS last,
                                     SUM(status = 'final') AS final, ROUND(SUM(total_cost_usd), 2) AS cost
                              FROM reports""").fetchone()
        flagged = conn.execute("SELECT COUNT(*) FROM report_tickers WHERE category = 'flagged'").fetchone()[0]
        intraday = [r[0] for r in conn.execute(
            "SELECT session_date FROM reports WHERE status = 'intraday' ORDER BY session_date")]
    market = load_market(db_path)
    earnings = sorted((d.isoformat(), t) for (t, d), (kind, _) in market.events.items()
                      if kind == "earnings" and d >= market.days[0])
    import search_index
    index = search_index.status()
    return {"database": str(Path(db_path).resolve()), "main_project": str(MAIN), "days": row["days"],
            "first_day": row["first"], "last_day": row["last"], "final": row["final"],
            "intraday": intraday, "flagged_rows": flagged, "simulated_cost_usd": row["cost"],
            "earnings_days": {t: d for d, t in earnings},
            "search_index": {"reports": index["reports_indexed"], "passages": index["passages"]}}


# ---------------------------------------------------------------------------
# Simulated runs (no Claude, no market data, no cost)
# ---------------------------------------------------------------------------

def next_intraday_point(reports_db, market, db_path: Path = DB_PATH):
    """The next simulated intraday update for the latest day: 15 minutes after the last one.
    Returns None if the latest day is already final."""
    day = market.days[-1]
    with closing(reports_db.connect(db_path, readonly=True)) as conn:
        row = conn.execute("SELECT status, as_of FROM reports WHERE session_date = ?", (day.isoformat(),)).fetchone()
    if row and row["status"] == "final":
        return None
    last = datetime.strptime(row["as_of"], "%Y-%m-%d %H:%M ET") if row else datetime.combine(day, time(9, 45))
    close = time(12, 55) if day in market.early_closes else time(15, 55)
    at = min((last + timedelta(minutes=15)).time(), close)
    minutes = (datetime.combine(day, at) - datetime.combine(day, time(9, 30))).seconds / 60
    return day, f"{day} {at:%H:%M} ET", min(1.0, max(0.05, minutes / 390))


def simulate_update(db_path: Path = DB_PATH) -> str:
    """What a scheduled intraday run does: another program saving a newer intraday report."""
    reports_db, market = connect_main(db_path), load_market(db_path)
    point = next_intraday_point(reports_db, market, db_path)
    if point is None:
        return "skipped: the latest day is already final"
    day, as_of, fraction = point
    with closing(reports_db.connect(db_path)) as conn:
        outcome = _save(reports_db, conn, market, day, market.scan(day, as_of, fraction), "intraday",
                        datetime.now(timezone.utc), 0.0)
    update_search_index(db_path)
    return f"{outcome}: intraday report for {day} as of {as_of}"


def simulate_finalize(db_path: Path = DB_PATH) -> str:
    """What the after-close (or next-morning) run does: the latest day's final report."""
    reports_db, market = connect_main(db_path), load_market(db_path)
    day = market.days[-1]
    with closing(reports_db.connect(db_path)) as conn:
        outcome = _save(reports_db, conn, market, day, market.scan(day), "final", datetime.now(timezone.utc), 0.0)
    update_search_index(db_path)
    return f"{outcome}: final report for {day}"


def install_fake_runs(run_brief, reports_db, market, db_path: Path = DB_PATH) -> None:
    """Make "Run update now" use the simulated market instead of Claude and Yahoo Finance."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage
    plan = {}

    def fake_market_session():
        point = next_intraday_point(reports_db, market, db_path)
        if point is None:
            return {"status": "complete", "as_of": market.days[-1].isoformat()}
        plan["day"], plan["as_of"], plan["fraction"] = point
        return {"status": "in_progress", "as_of": plan["as_of"]}

    async def fake_agent(*, prompt, options):
        day = plan["day"]
        scan = market.scan(day, plan["as_of"], plan["fraction"])
        text = lambda data: [{"type": "text", "text": json.dumps(data)}]  # noqa: E731
        yield AssistantMessage(content=[ToolUseBlock(id="scan", name="mcp__market__flag_events", input={})],
                               model="offline-test")
        await asyncio.sleep(0.6)
        yield UserMessage(content=[ToolResultBlock(tool_use_id="scan", content=text(scan))])
        for i, m in enumerate(scan["flagged"]):
            yield AssistantMessage(content=[ToolUseBlock(id=f"news{i}", name="mcp__market__get_news",
                                                         input={"ticker": m["ticker"]})], model="offline-test")
            await asyncio.sleep(0.4)
            news = market.news(m["ticker"], day)
            yield UserMessage(content=[ToolResultBlock(tool_use_id=f"news{i}",
                                                       content=[part for n in news for part in text(n)])])
        yield ResultMessage(subtype="success", duration_ms=0, duration_api_ms=0, is_error=False, num_turns=2,
                            session_id="offline-test", total_cost_usd=0.0, result=market.brief(scan, day))

    run_brief.market_session = fake_market_session
    run_brief.query = fake_agent


def offline_answer(reports_db, ask, question: str, db_path: Path = DB_PATH) -> str:
    """A plain answer built straight from the sample data, for testing Ask without Claude."""
    lines = ["*Offline test answer, built from the sample data without Claude.*", ""]
    with closing(reports_db.connect(db_path, readonly=True)) as conn:
        tickers = ask.mentioned_tickers(conn, question)
        for t in tickers:
            rows = conn.execute("""SELECT session_date, return_1d_pct FROM report_tickers
                                   WHERE ticker = ? AND category = 'flagged' ORDER BY session_date DESC""", (t,)).fetchall()
            if rows:
                recent = ", ".join(f"{r[0]} ({r[1]:+.2f}%)" for r in rows[:5])
                lines.append(f"- **{t}** was flagged on {len(rows)} day{'s' if len(rows) != 1 else ''}. Most recent: {recent}.")
            else:
                lines.append(f"- **{t}** hasn't been flagged in the saved reports.")
        if not tickers:
            top = conn.execute("""SELECT ticker, COUNT(*) FROM report_tickers WHERE category = 'flagged'
                                  GROUP BY ticker ORDER BY COUNT(*) DESC, ticker LIMIT 3""").fetchall()
            lines.append("Most-flagged tickers in the saved reports: "
                         + (", ".join(f"**{t}** ({n} days)" for t, n in top) or "none yet") + ".")
    # The retrieval step real answers are built on: the passages that best match the question
    passages = ask.find_passages(question)[:3]
    if passages:
        lines += ["", "Most relevant passages:"]
        lines += [f"- {p['session_date']}: {p['heading']} (matched by {' and '.join(p['matched_by'])})" for p in passages]
    return "\n".join(lines)


def install_fake_prices(prices, reports_db, market, db_path: Path = DB_PATH) -> None:
    """Make the charts show the simulated market instead of downloading prices."""
    def fake_fetch(ticker, period):
        if ticker not in market.tickers:
            return []
        rows = market.price_history(ticker, period)
        # While the latest sample day is still intraday, end the chart at the price its report shows
        with closing(reports_db.connect(db_path, readonly=True)) as conn:
            row = conn.execute("""SELECT r.status, t.return_1d_pct FROM reports r
                                  JOIN report_tickers t ON t.session_date = r.session_date
                                  WHERE r.session_date = ? AND t.ticker = ?""",
                               (market.days[-1].isoformat(), ticker)).fetchone()
        if row and row["status"] == "intraday" and row["return_1d_pct"] is not None and len(rows) > 1:
            rows[-1]["close"] = round(rows[-2]["close"] * (1 + row["return_1d_pct"] / 100), 2)
        return rows

    prices.fetch_prices = fake_fetch
    prices.CACHE_SECONDS = 0  # so charts follow `update` and `finalize` straight away
    prices._cache.clear()


def install_fake_ask(ask, reports_db, db_path: Path = DB_PATH) -> None:
    """Make "Ask" answer from the sample data without calling Claude."""
    from claude_agent_sdk import ResultMessage, StreamEvent

    async def fake_claude(*, prompt, options):
        answer = offline_answer(reports_db, ask, prompt.rsplit("Question:", 1)[-1].strip(), db_path)
        for word in answer.split(" "):
            await asyncio.sleep(0.03)
            yield StreamEvent(uuid="offline", session_id="offline", event={
                "type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": word + " "}})
        yield ResultMessage(subtype="success", duration_ms=0, duration_api_ms=0, is_error=False, num_turns=1,
                            session_id="offline", total_cost_usd=0.0, result=answer)

    ask.query = fake_claude


# ---------------------------------------------------------------------------
# Serving the real app against the test data
# ---------------------------------------------------------------------------

def make_app(db_path: Path = DB_PATH, live_ask: bool = False, live_runs: bool = False,
             live_embeddings: bool = False, frontend_dist: Path = FRONTEND_DIST):
    reports_db = connect_main(db_path)
    market = load_market(db_path)
    import api
    import ask
    import prices
    import run_brief
    import search_index
    if not live_embeddings:
        install_fake_embeddings(search_index)
    api.RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "15"))  # shorter for testing
    if not live_runs:  # live runs use real market data, so the charts do too
        install_fake_runs(run_brief, reports_db, market, db_path)
        install_fake_prices(prices, reports_db, market, db_path)
    if not live_ask:
        install_fake_ask(ask, reports_db, db_path)
    return api.create_app(frontend_dist=frontend_dist)


def build_frontend() -> None:
    """Build the main project's React app into this folder (its own dist/ is left alone)."""
    npm = shutil.which("npm")
    frontend = MAIN / "frontend"
    if not npm:
        sys.exit("npm wasn't found. Install Node.js (see the frontend guide).")
    if not (frontend / "node_modules").is_dir():
        sys.exit(f"Run `npm install` in {frontend} first (see the frontend guide).")
    subprocess.run([npm, "run", "build", "--", "--outDir", str(FRONTEND_DIST), "--emptyOutDir"], cwd=frontend, check=True)
    print(f"Built the app into {FRONTEND_DIST}")


def reset(db_path: Path = DB_PATH) -> None:
    folder = Path(db_path).resolve().parent
    if folder == MAIN or MAIN in folder.parents:
        sys.exit("Refusing to delete anything inside the main project.")
    for base in (Path(db_path).name, "search.db"):
        for suffix in ("", "-wal", "-shm"):
            (folder / (base + suffix)).unlink(missing_ok=True)
    (folder / "sample_config.json").unlink(missing_ok=True)
    print(f"Deleted the sample data in {folder}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test environment for the market analyst agent.")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed", help="create sample reports")
    seed.add_argument("--end", type=date.fromisoformat, help="last day of the sample (default: today)")
    seed.add_argument("--months", type=int, default=2, help="how far back the sample goes (default: 2)")
    seed.add_argument("--seed", type=int, default=7, help="change for different (but repeatable) sample data")
    seed.add_argument("--tickers", help="comma-separated (default: the main project's watchlist)")
    seed.add_argument("--latest", choices=["intraday", "final"], help="status of the latest day")
    seed.add_argument("--reset", action="store_true", help="replace existing sample data")
    commands.add_parser("status", help="summary of the sample data")
    commands.add_parser("build-frontend", help="build the React app into this folder")
    serve = commands.add_parser("serve", help="run the app against the sample data")
    serve.add_argument("--port", type=int, default=PORT)
    serve.add_argument("--live-ask", action="store_true", help="answer questions with real Claude (costs money)")
    serve.add_argument("--live-runs", action="store_true",
                       help="Run now (and the charts) use real Claude and market data (costs money; saves into the test database)")
    serve.add_argument("--live-embeddings", action="store_true",
                       help="search by meaning with real Voyage AI embeddings (needs VOYAGE_API_KEY)")
    commands.add_parser("update", help="simulate a scheduled intraday run")
    commands.add_parser("finalize", help="simulate the run that writes the latest day's final report")
    commands.add_parser("reset", help="delete the sample data")
    args = parser.parse_args()

    if args.command == "seed":
        if args.reset:
            reset()
        tickers = [t.strip() for t in args.tickers.split(",")] if args.tickers else None
        summary = seed_database(end=args.end, months=args.months, seed=args.seed, tickers=tickers, latest=args.latest)
        print(json.dumps(summary, indent=2))
    elif args.command == "status":
        if not DB_PATH.exists():
            sys.exit("No sample data yet. Run: python testenv.py seed")
        print(json.dumps(status_summary(), indent=2))
    elif args.command == "build-frontend":
        build_frontend()
    elif args.command == "serve":
        import uvicorn
        if not DB_PATH.exists():
            sys.exit("No sample data yet. Run: python testenv.py seed")
        app = make_app(live_ask=args.live_ask, live_runs=args.live_runs, live_embeddings=args.live_embeddings)
        live = [name for name, on in (("Claude", args.live_ask or args.live_runs), ("Voyage", args.live_embeddings)) if on]
        mode = f"LIVE {' + '.join(live)}" if live else "offline (no Claude, no Voyage, no cost)"
        print(f"Test environment: http://localhost:{args.port}  ·  {mode}  ·  database {DB_PATH}")
        if not FRONTEND_DIST.is_dir():
            print("No frontend build yet, so only the API is available. Run: python testenv.py build-frontend")
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    elif args.command == "update":
        print(simulate_update())
    elif args.command == "finalize":
        print(simulate_finalize())
    elif args.command == "reset":
        reset()


if __name__ == "__main__":
    main()
```

### test_testenv.py

```python
"""Checks for the test environment: the sample data, the simulated runs, and that the
main project is never touched. Run from this folder:  pytest -v
"""

import hashlib
import sqlite3
import sys
import time
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402  (sets the no-bytecode rule before anything from the main project loads)
from sample_market import SampleMarket, early_closes, nyse_holidays, trading_days  # noqa: E402

END = date(2026, 11, 6)
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]


def snapshot(folder: Path) -> dict:
    """Every file and folder in the main project (except installed packages and the real database)."""
    entries = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if {".venv", "node_modules", ".git"} & set(rel.parts) or path.name.startswith("reports.db"):
            continue
        entries[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "folder"
    return entries


MAIN_BEFORE = snapshot(testenv.MAIN)
MAIN_DB_EXISTED = (testenv.MAIN / "reports.db").exists()


def seed(folder: Path, **settings) -> Path:
    db = folder / "reports.db"
    testenv.seed_database(db, end=END, tickers=TICKERS, **settings)
    return db


@pytest.fixture(scope="module")
def db(tmp_path_factory):
    """One sample database shared by the read-only checks."""
    return seed(tmp_path_factory.mktemp("sample"))


@pytest.fixture
def conn(db):
    reports_db = testenv.connect_main(db)
    with closing(reports_db.connect(db, readonly=True)) as connection:
        yield connection


@pytest.fixture
def fresh_db(tmp_path):
    """A separate sample database for checks that change data."""
    return seed(tmp_path)


@pytest.fixture
def client(monkeypatch):
    """The real app, served over a given sample database, with simulated Claude and market data."""
    from starlette.testclient import TestClient
    monkeypatch.setenv("RUN_COOLDOWN_SECONDS", "0")
    opened = []

    def make(db_path):
        app = testenv.make_app(db_path, frontend_dist=db_path.parent / "no-frontend")
        import api
        monkeypatch.setattr(api, "runs", api.RunManager())
        test_client = TestClient(app).__enter__()  # kept open so background runs can finish
        opened.append(test_client)
        return test_client

    yield make
    for test_client in opened:
        test_client.__exit__(None, None, None)


def wait_for_run(client):
    for _ in range(100):
        run = client.get("/api/runs/current").json()["run"]
        if run["state"] in ("finished", "failed"):
            return run
        time.sleep(0.05)
    raise AssertionError("the simulated run didn't finish")


# ---------------------------------------------------------------------------
# The sample data
# ---------------------------------------------------------------------------

def test_calendar_follows_nyse_rules():
    holidays = nyse_holidays(2026)
    assert {date(2026, 4, 3), date(2026, 7, 3), date(2026, 9, 7), date(2026, 11, 26)} <= holidays  # Good Friday, July 4th (observed), Labor Day, Thanksgiving
    assert date(2026, 11, 27) in early_closes(2026)  # the day after Thanksgiving closes at 1pm
    days = trading_days(date(2026, 9, 1), date(2026, 9, 30))
    assert date(2026, 9, 7) not in days and all(d.weekday() < 5 for d in days)


def test_sample_covers_two_months_of_trading_days(conn):
    days = [r[0] for r in conn.execute("SELECT session_date FROM reports ORDER BY session_date")]
    assert days[0] == "2026-09-08"  # 6 Sep is a Sunday and 7 Sep is Labor Day
    assert days[-1] == "2026-11-06"
    assert len(days) == 44
    assert all(date.fromisoformat(d).weekday() < 5 for d in days)


def test_reports_were_stored_as_in_real_use(conn):
    rows = [dict(r) for r in conn.execute("SELECT * FROM reports ORDER BY session_date")]
    final = [r for r in rows if r["status"] == "final"]
    intraday = [r["session_date"] for r in rows if r["status"] == "intraday"]
    assert len(final) == 42
    assert intraday == ["2026-10-08", "2026-11-06"]  # one day never finalized, plus today, still live
    assert {r["revision"] for r in final} == {1, 3}  # finalized directly, or after two intraday updates
    assert any(r["revision"] == 3 for r in final) and any(r["revision"] == 1 for r in final)
    for r in final:  # finalized after that day's close, at a realistic time
        finalized = datetime.fromisoformat(r["finalized_at"].replace("Z", "+00:00")).astimezone(testenv.ET)
        assert finalized.date() >= date.fromisoformat(r["session_date"])
        assert finalized.date() - date.fromisoformat(r["session_date"]) < timedelta(days=5)
    assert rows[0]["created_at"].startswith("2026-09-08")  # timestamps span the two months
    assert rows[-1]["as_of"] == "2026-11-06 12:30 ET"


def test_final_reports_are_permanent(db):
    reports_db = testenv.connect_main(db)
    with closing(reports_db.connect(db)) as writable:
        with pytest.raises(sqlite3.IntegrityError, match="permanent"):
            writable.execute("UPDATE reports SET body_md = 'x' WHERE status = 'final'")


def test_flagged_tickers_follow_the_flagging_rule(conn):
    flagged = conn.execute("SELECT return_zscore, volume_vs_avg FROM report_tickers WHERE category = 'flagged'").fetchall()
    assert len(flagged) >= 20
    assert all(abs(z) >= 2 or v >= 2 for z, v in flagged)


def test_every_earnings_day_is_flagged_with_a_source(conn):
    market = SampleMarket(TICKERS, END)
    earnings = [(t, d) for (t, d), (kind, _) in market.events.items() if kind == "earnings"]
    assert {t for t, _ in earnings} == set(TICKERS)  # one earnings day per ticker, all in the window
    for ticker, day in earnings:
        row = conn.execute("""SELECT category FROM report_tickers WHERE ticker = ? AND session_date = ?""",
                           (ticker, day.isoformat())).fetchone()
        assert row["category"] == "flagged", (ticker, day)
        url = conn.execute("""SELECT url FROM report_sources WHERE ticker = ? AND session_date = ?""",
                           (ticker, day.isoformat())).fetchone()[0]
        assert url.startswith("https://news.example.com/") and url.endswith("earnings")


def test_briefs_follow_the_agent_template(conn):
    for body, status in conn.execute("SELECT body_md, status FROM reports"):
        title = "# Intraday update: " if status == "intraday" else "# Watchlist brief: "
        assert body.startswith(title)
        assert "## Notable moves" in body and "## Quiet" in body
        assert "Sample data for the test environment" in body


def test_same_settings_give_the_same_data(tmp_path):
    def bodies(folder, **settings):
        db = seed(folder, **settings)
        reports_db = testenv.connect_main(db)
        with closing(reports_db.connect(db, readonly=True)) as c:
            return [r[0] for r in c.execute("SELECT body_md FROM reports ORDER BY session_date")]

    first = bodies(tmp_path / "a")
    assert bodies(tmp_path / "b") == first
    assert bodies(tmp_path / "c", seed=99) != first


# ---------------------------------------------------------------------------
# The real app over the sample data
# ---------------------------------------------------------------------------

def test_app_serves_two_months_of_reports(db, client):
    app = client(db)
    assert len(app.get("/api/reports?limit=365").json()["reports"]) == 44
    page = app.get("/api/reports?before=2026-11-06&limit=30").json()["reports"]
    older = app.get(f"/api/reports?before={page[-1]['session_date']}&limit=30").json()["reports"]
    assert len(page) == 30 and len(older) == 13  # the Previous days tab's paging: 43 earlier days
    assert app.get("/api/reports/latest").json()["status"] == "intraday"
    assert len(app.get("/api/tickers/NVDA/history?limit=365").json()["history"]) == 44


def test_offline_run_now_updates_the_latest_day(fresh_db, client):
    app = client(fresh_db)
    assert app.post("/api/runs", json={}).status_code == 202
    run = wait_for_run(app)

    assert run["state"] == "finished"
    assert run["result"]["outcome"] == "updated" and run["result"]["cost_usd"] == 0
    assert [e["type"] for e in run["log"]][:2] == ["started", "tool_call"]
    latest = app.get("/api/reports/latest").json()
    assert latest["as_of"] == "2026-11-06 12:45 ET" and latest["revision"] == 3


def test_offline_run_now_skips_once_the_day_is_final(fresh_db, client):
    assert testenv.simulate_finalize(fresh_db).startswith("finalized")
    app = client(fresh_db)
    app.post("/api/runs", json={})
    assert wait_for_run(app)["result"]["type"] == "skipped"


def test_offline_ask_answers_from_the_sample_data(db, client, conn):
    latest_flag = conn.execute("""SELECT MAX(session_date) FROM report_tickers
                                  WHERE ticker = 'NVDA' AND category = 'flagged'""").fetchone()[0]
    app = client(db)
    response = app.post("/api/ask", json={"question": "Why was nvda flagged?"})
    done = [line for line in response.text.splitlines() if '"done"' in line][0]
    assert "NVDA" in done and "flagged on" in done and latest_flag in done
    assert '"cost_usd": 0' in done


def test_charts_show_the_simulated_prices(db, client, conn):
    app = client(db)
    year = app.get("/api/tickers/NVDA/prices?range=1y").json()["prices"]
    assert len(year) == 252 and year[-1]["date"] == "2026-11-06"
    assert [len(app.get(f"/api/tickers/NVDA/prices?range={r}").json()["prices"]) for r in ("1mo", "3mo", "6mo")] == [21, 63, 126]

    # The chart agrees with the reports: a flagged day's close matches its report's price...
    day, price = conn.execute("""SELECT t.session_date, t.price FROM report_tickers t JOIN reports r USING (session_date)
                                 WHERE t.ticker = 'NVDA' AND t.category = 'flagged' AND r.status = 'final'
                                 ORDER BY t.session_date LIMIT 1""").fetchone()
    assert next(p["close"] for p in year if p["date"] == day) == pytest.approx(price, abs=0.01)
    # ...and while today is intraday, the last point matches today's move so far
    move = conn.execute("""SELECT return_1d_pct FROM report_tickers
                           WHERE ticker = 'NVDA' AND session_date = '2026-11-06'""").fetchone()[0]
    assert year[-1]["change_pct"] == pytest.approx(move, abs=0.02)
    assert app.get("/api/tickers/ZZZZ/prices").status_code == 404  # not in the sample


def test_search_over_two_months_of_sample_data(db, client, conn):
    earnings_days = {d.isoformat() for (t, d), (kind, _) in SampleMarket(TICKERS, END).events.items()
                     if kind == "earnings"}
    app = client(db)

    by_word = app.get("/api/search?q=quarterly&limit=50").json()
    assert by_word["mode"] == "hybrid"  # with the simulated stand-in for Voyage
    assert {r["session_date"] for r in by_word["results"] if "keywords" in r["matched_by"]} == earnings_days

    # "profit" never appears in the reports, but means the same thing as "quarterly results"
    by_meaning = app.get("/api/search?q=profit&limit=50").json()["results"]
    assert {r["session_date"] for r in by_meaning} >= earnings_days
    assert all(r["matched_by"] == ["meaning"] for r in by_meaning)

    assert app.get("/api/search?q=zzzzqqq").json()["results"] == []  # nonsense finds nothing either way

    status = app.get("/api/search/status").json()
    assert status["reports_indexed"] == status["reports_total"] == 44


def test_offline_ask_shows_the_passages_it_retrieved(db, client):
    response = client(db).post("/api/ask", json={"question": "Which companies reported profits?"})
    done = [line for line in response.text.splitlines() if '"done"' in line][0]
    assert "Most relevant passages" in done and "matched by meaning" in done


def test_update_and_finalize_simulate_scheduled_runs(fresh_db):
    assert testenv.simulate_update(fresh_db).startswith("updated")
    assert testenv.simulate_finalize(fresh_db).startswith("finalized")
    assert testenv.simulate_update(fresh_db).startswith("skipped")
    import search_index
    assert search_index.status()["reports_indexed"] == 44  # search kept up with both
    assert (fresh_db.parent / "search.db").exists()


# ---------------------------------------------------------------------------
# Isolation from the main project
# ---------------------------------------------------------------------------

def test_refuses_to_use_the_main_projects_database():
    with pytest.raises(SystemExit, match="Refusing"):
        testenv.connect_main(testenv.MAIN / "reports.db")


def test_main_project_was_not_touched():
    """Runs last: nothing above changed, added or removed any file in the main project."""
    assert snapshot(testenv.MAIN) == MAIN_BEFORE
    assert (testenv.MAIN / "reports.db").exists() == MAIN_DB_EXISTED
```
