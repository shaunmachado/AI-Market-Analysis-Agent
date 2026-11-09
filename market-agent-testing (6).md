# Market Analyst Agent: Testing Guide

How to test the market analyst agent, from quick offline checks to full runs with Claude, Discord alerts, the events calendar, tracked stocks and the schedule.

This version covers the whole project, up to the guide that adds finding and tracking stocks (`market-agent-stocks.md`). For trying the app on two months of sample data, see `market-agent-test-enviro.md`.

---

## Contents

1. [Testing strategy](#1-testing-strategy)
2. [The test files](#2-the-test-files)
3. [Run the offline tests](#3-run-the-offline-tests)
4. [Live data check](#4-live-data-check)
5. [Manual tool check with the MCP Inspector](#5-manual-tool-check-with-the-mcp-inspector)
6. [Agent test runs](#6-agent-test-runs)
7. [Alerts, calendar and Stocks tab checks](#7-alerts-calendar-and-stocks-tab-checks)
8. [Schedule test](#8-schedule-test)
9. [Quality log](#9-quality-log)
10. [Testing a new tool](#10-testing-a-new-tool)
11. [Troubleshooting the tests](#11-troubleshooting-the-tests)
12. [Appendix: test file source](#appendix-test-file-source)

---

## 1. Testing strategy

Test in layers, from fastest to slowest. Each layer catches a different kind of problem, so when something breaks you know where to look.

| Layer | What it checks | Needs | When to run it |
|---|---|---|---|
| Offline tests | Tool math, sector verdicts, storage rules, API, search, alerts, the events calendar, tracked stocks | Nothing | After every code change |
| Live data check | Yahoo Finance returns real data, including sectors, sector ETFs, company calendars and stock search | Internet | Once at setup, then if data looks wrong |
| MCP Inspector | The tools work the way Claude will see them | Node.js, internet | After changing a tool |
| Agent test runs | Claude uses the tools well and writes a good brief | API key (uses credits) | After changing the prompt or tools |
| Alerts check | Messages reach your Discord channel and phone | A Discord webhook | Once at setup, then after changing alerts |
| Calendar check | Real earnings dates and news events are right, with working links | API key (a few cents a scan) | Once at setup, then now and then |
| Schedule test | The scheduled job actually runs, with all its keys | Cron or Task Scheduler | Once, when setting up the schedule |
| Quality log | The briefs and alerts are useful over time | Your judgment | Daily for the first week or two |

**Where the problem is, by which layer fails:**

| Fails | Passes | Problem is in |
|---|---|---|
| Offline tests | — | Your code. The failing test's file names the area. |
| Live data check | Offline tests | The data source: network, rate limits or the yfinance version |
| Agent test run | Live data and Inspector | The prompt (`analyst_prompt.md`) or the agent settings (`run_brief.py`) |
| Alerts check | Offline alert tests | The webhook address, or the network to Discord |
| Calendar check | Offline calendar tests | Yahoo's data, or what Claude reads in the news (check the "left out" lines and the links) |
| Schedule test | Manual agent run | The scheduler: paths, keys missing from its environment, or the computer asleep |

---

## 2. The test files

```
market-agent/
└── tests/
    ├── conftest.py                 keeps every test away from your real Discord and Voyage
    ├── test_market_tools.py        the tools: market hours, moves, sector context, backdrop, news, MCP
    ├── test_reports_db.py          the storage rules, the API's report endpoints, runs saving reports
    ├── test_frontend_api.py        run now, live updates, Ask
    ├── test_charts.py              price charts
    ├── test_search.py              search and RAG
    ├── test_sector_context.py      sector context: storage, upgrades, API, Ask, agent setup
    ├── test_alerts.py              Discord alerts
    ├── test_events.py              the events calendar: Yahoo dates, news events, checks, API
    ├── test_calendar_links.py      the calendar in briefs, Discord alerts, Ask and search
    └── test_watchlist.py           tracked and main stocks: the watchlist file, search, API, longer lists
```

| File | Tests | Comes from |
|---|---|---|
| `test_market_tools.py` | 34, plus 1 live check | This guide's [appendix](#appendix-test-file-source) |
| `test_reports_db.py` | 33 | `market-agent-database.md` |
| `test_frontend_api.py` | 20 | `market-agent-frontend.md` |
| `test_charts.py` | 7 | `market-agent-frontend.md` |
| `test_search.py` | 25 | `market-agent-rag.md` |
| `test_sector_context.py` | 6 | `market-agent-sector-context.md` |
| `test_alerts.py` | 23 | `market-agent-alerts.md` |
| `test_events.py` | 47, plus 1 live check | `market-agent-events-calendar.md` |
| `test_calendar_links.py` | 13 | `market-agent-calendar-connect.md` |
| `test_watchlist.py` | 33, plus 1 live check | `market-agent-stocks.md` |
| `conftest.py` | (shared setup) | `market-agent-alerts.md` |

To create or update `test_market_tools.py`, replace its contents with the code from the [appendix](#appendix-test-file-source). **It matches `market_tools.py` from the sector context guide.** With an older `market_tools.py`, its 13 sector-context tests fail.

**How the tests work:**

- **Market data is faked.** yfinance is swapped for a fake that returns made-up daily prices, 5-minute bars, news and company profiles (for sectors), in the same shape as the real thing.
- **The clock is faked.** "Market open", "weekend", "holiday" and "early close" can be tested on any day.
- **Nothing real is touched.** The tests use a temporary watchlist and temporary databases, so your real `watchlist.txt` and `reports.db` are never touched.
- **Claude, Voyage and Discord are faked.** `conftest.py` removes `DISCORD_WEBHOOK_URL` and `VOYAGE_API_KEY` for every test, so tests can't reach them even if they're set in your terminal.

Results are the same on every run, and no internet or keys are needed.

---

## 3. Run the offline tests

With your virtual environment active, from the `market-agent` folder:

```bash
pip install pytest
pytest -v
```

**Expected result:** `241 passed, 3 skipped`. The skipped tests are the three live data checks in section 4.

If you're partway through the guides, the total so far:

| Done up to | Expected |
|---|---|
| `market-agent-rag.md` (with the older test file) | `106 passed, 1 skipped` |
| `market-agent-sector-context.md` | `125 passed, 1 skipped` |
| `market-agent-alerts.md` | `148 passed, 1 skipped` |
| `market-agent-events-calendar.md` | `195 passed, 2 skipped` |
| `market-agent-calendar-connect.md` | `208 passed, 2 skipped` |
| `market-agent-stocks.md` | `241 passed, 3 skipped` |

To run one area only, name its file: `pytest -v tests/test_market_tools.py` should give `34 passed, 1 skipped`.

**What each test in `test_market_tools.py` proves.** The other files' tests are listed in their own guides.

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
| `test_watchlist_can_name_a_benchmark_per_ticker` | A line like `NVDA SMH  # semis` reads as ticker NVDA with benchmark SMH |
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

*Sector and market context*

| Test | Proves that |
|---|---|
| `test_benchmark_comes_from_sector_or_watchlist` | Your chosen benchmark wins; otherwise the sector's ETF; ETFs, unknown companies and failed lookups use the S&P 500 |
| `test_stock_specific_move` | A 7% jump on a calm day for its sector is `stock-specific`, and the gap's z-score matches a hand calculation |
| `test_sector_wide_move` | Moving with a sector that fell 5% on a flat market day is `sector-wide` |
| `test_market_wide_move` | Everything falling 4% together is `market-wide` |
| `test_volume_only_flag_is_in_line_with_peers` | A volume spike with an ordinary price move is `in line` |
| `test_partly_sector_move_is_mixed` | A wider-than-usual but not unusual gap is `mixed` |
| `test_quiet_tickers_are_not_compared` | Quiet days download no ETFs |
| `test_each_benchmark_is_downloaded_once_per_scan` | Two flagged tech stocks share one XLK download |
| `test_context_problem_never_hides_the_move` | If an ETF fails to download, the move is still flagged and the comparison says what's missing |
| `test_compute_moves_includes_context` | `compute_moves` gives the same comparison |
| `test_intraday_context_compares_the_same_time_of_day` | While the market is open, the gap is judged against the same time of day, matching a hand calculation |
| `test_market_backdrop_ranks_sectors` | The backdrop sorts sectors best to worst, names unusual ones, and reports a missing ETF without failing |

*News and MCP*

| Test | Proves that |
|---|---|
| `test_news_handles_both_yfinance_formats_and_caps_limit` | Both yfinance news formats are read, summaries are trimmed and results are capped at 10 |
| `test_tools_work_through_mcp` | All five tools work through a real MCP client, the same way the agent calls them |
| `test_live_data` | Real data comes back from Yahoo Finance, including Apple's sector ETF and the backdrop (skipped unless you turn it on) |

**Tip: check the tests catch real bugs.** Make one of these temporary changes in `market_tools.py`, run `pytest tests/test_market_tools.py`, then change it back:

| Temporary change | Tests that should fail |
|---|---|
| `baseline = returns.iloc[:-1]` → `baseline = returns` | The closed-market z-score test |
| `if session["status"] == "in_progress":` → `if False:` (turns off intraday mode) | The intraday tests: this is what the partial-day problem looks like |
| `if day_bars.index[-1].time() < cutoff:` → `if False:` | The half-day test |
| In `describe_context`: `if abs(gap_z) >= CONTEXT_Z:` → `if False:` | The stock-specific and intraday context tests |
| In `flag_events`: pass `{}` instead of `measured` to `_context` | `test_each_benchmark_is_downloaded_once_per_scan` |

The alerts guide (section 11.1) and the calendar guide (section 10.1) have the same kind of checks for `alerts.py` and `events.py`.

---

## 4. Live data check

This fetches real data from Yahoo Finance and prints it:

- Apple's figures.
- Apple compared with its sector.
- The market backdrop.
- Apple's company calendar (earnings and dividend dates).
- Yahoo's search for "costco", as the Stocks tab uses it.

**macOS / Linux**

```bash
LIVE_TESTS=1 pytest -v -s -k live
```

**Windows (PowerShell)**

```powershell
$env:LIVE_TESTS=1; pytest -v -s -k live
```

**Expected result:** `3 passed`. You'll see:

- from `test_live_data`: `Live session`, `Live AAPL`, `Live AAPL vs. sector` and `Live backdrop`
- from `test_live_calendar_data`: `Yahoo's calendar for AAPL` and `Events from it`
- from `test_live_search`: your yfinance version, `Yahoo's matches for 'costco'` and `Checked:`

It downloads about 15 tickers, so it takes a few seconds.

Check by eye:

| | Market closed | Market open |
|---|---|---|
| `Live session` shows | `'status': 'complete'` and the last trading day | `'status': 'in_progress'` and a time a few minutes ago |
| AAPL's price field | `last_close` matches the last close on Yahoo Finance or your broker | `last_price` is close to the live quote (it can lag a few minutes) |
| `return_1d_pct` | Matches that day's percentage change | Matches today's change so far |
| `compared_to` | "daily moves over the last 3 months" | "the same time of day over the last N sessions" (about 20) |
| `Live AAPL vs. sector` | Names "its sector (Technology, XLK)", and XLK's move matches Yahoo | The same, "so far today" |
| `Live backdrop` | The S&P 500's move matches SPY on Yahoo; the best and worst sectors look right | The same, "so far today" |
| `Events from it` | Apple's next earnings date matches its investor-relations page (or says "date not confirmed" with a window) | The same |
| `Yahoo's matches for 'costco'` | Includes `('COST', 'EQUITY', 'NASDAQ')`. Any listings with a dot (outside the US) are dropped by the app, not here | The same |

Ideally, run it once while the market is open and once while it's closed, so both modes are checked with real data.

If the offline tests pass but this fails, the problem is the data source, not your code. See [troubleshooting](#11-troubleshooting-the-tests).

---

## 5. Manual tool check with the MCP Inspector

The Inspector lets you call each tool by hand with live data, seeing exactly what Claude will receive. It needs Node.js.

```bash
npx @modelcontextprotocol/inspector python market_tools.py
```

It opens in your browser. Click **Connect**, open the **Tools** tab, and try each tool:

| Tool | Try with | Check that |
|---|---|---|
| `flag_events` | default arguments | Every watchlist ticker appears in `flagged`, `quiet` or `errors`; `session.status` is right for the time; each flagged ticker has a `context` |
| `flag_events` | `z_threshold` = 0 | Every ticker is flagged, each with a `context` |
| `compute_moves` | `AAPL` | Numbers match the live data check; `context.benchmark` is `XLK` |
| `compute_moves` | `ZZZZ123` | Returns `not enough price history` instead of crashing |
| `market_backdrop` | no arguments | SPY plus about 11 sectors, best first, and a readable `summary` |
| `get_news` | a ticker that moved recently | Headlines are recent, links work, publishers are filled in |

Also check that each tool's description reads clearly. Claude uses those descriptions to decide which tool to call.

---

## 6. Agent test runs

### 6.1 Set up a cheap, separate test

Test runs save reports and can send alerts, so keep them apart from your real ones:

1. **Use a scratch database and search index.** A run after the close saves that day's final report permanently, so point test runs at scratch files. Set both: the search index would otherwise sit next to your real one and be rebuilt from the test reports.

   ```bash
   export REPORTS_DB=test-reports.db SEARCH_DB=test-search.db                 # macOS / Linux
   $env:REPORTS_DB="test-reports.db"; $env:SEARCH_DB="test-search.db"         # Windows PowerShell
   ```

2. **Don't alert your real channel.** Run `unset DISCORD_WEBHOOK_URL` (PowerShell: `Remove-Item Env:DISCORD_WEBHOOK_URL`). Or set it to a webhook in a test channel, which also tests alerts.
3. **Keep it small.** Copy `watchlist.txt` to `watchlist.backup.txt`, then cut `watchlist.txt` down to 2–3 tickers, ideally including one that moved a lot recently.
4. **Cap the cost.** In `run_brief.py`, change `max_budget_usd=1.00` to `max_budget_usd=0.25`.

These settings last until you close the terminal.

### 6.2 Run it

```bash
python run_brief.py
```

**Expected output:**

```
Writing the intraday report for 2026-11-06...        (or "final", when the market is closed)
-> mcp__market__flag_events {}
-> mcp__market__market_backdrop {}
-> mcp__market__upcoming_events {}
-> mcp__market__get_news {'ticker': 'NVDA'}
created: intraday report for 2026-11-06 (5 turns, $0.041)
Discord: sent flag alert: NVDA                       (only with a webhook set, and something new to alert)
```

The outcome is `created`, `updated` (a newer intraday update for the same day) or `finalized`. Running after the final report is saved prints "The final report for ... is already saved. Nothing to do." without calling Claude.

**Check the tool calls in that output:**

- [ ] `flag_events` is called first
- [ ] `market_backdrop` and `upcoming_events` are each called once
- [ ] `get_news` is called for each flagged ticker
- [ ] No unnecessary repeated calls

### 6.3 Check the brief

Read the saved report:

```bash
python reports_db.py show latest
```

Straight after the run, call `flag_events`, `market_backdrop` and `upcoming_events` in the Inspector, and compare.

- [ ] Every number in the brief matches a tool result exactly
- [ ] Every ticker from the watchlist appears (in "Notable moves", "Quiet" or "Data issues")
- [ ] The title matches the session: "Watchlist brief" when closed, "Intraday update" when open
- [ ] "Market backdrop" is the backdrop tool's `summary`
- [ ] Each flagged ticker's "Vs. sector and market" line is its `context.summary`, word for word
- [ ] For a `sector-wide` or `market-wide` move, "Likely why" leads with the sector or market, not company news
- [ ] "Coming up" lists `upcoming_events`' `this_week` lines exactly (or says nothing is on the calendar)
- [ ] A flagged ticker with an upcoming event has it in "Worth watching", with "not confirmed" when `confirmed` is false
- [ ] No upcoming event is described as the *cause* of a move unless the news says so ("ahead of" is fine)
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
| Everything flagged | In `market_tools.py`, set the `flag_events` default to `z_threshold: float = 0.0` | Every ticker under "Notable moves", each with a "Vs. sector and market" line and a news-based explanation or "No clear catalyst found" |
| Nothing flagged | Set `z_threshold: float = 99.0` and `volume_threshold: float = 99.0` | One line saying nothing notable, every ticker under "Quiet", and still a market backdrop |
| Your own benchmark | With everything flagged, change a line to `NVDA SMH` | NVDA's line compares it with SMH instead of XLK |
| Broken benchmark | With everything flagged, change a line to `AAPL ZZZZ123` | AAPL's line says "Sector comparison unavailable"; the rest of the brief is normal |
| Bad ticker | Add `ZZZZ123` on its own line | `ZZZZ123` listed under "Data issues"; the rest of the brief is normal |
| Cost cap | Set `max_budget_usd=0.01` | The run stops with `Run failed: error_max_budget_usd` and no report is saved |

**Checking a market-wide day.** On a day the whole market moves sharply, run once and check that flagged tickers read `market-wide` and the brief says so. That's the clearest real-world check of the verdicts.

### 6.5 Clean up

- [ ] Restore `z_threshold` and `volume_threshold` to `2.0`
- [ ] Restore `watchlist.txt` from `watchlist.backup.txt`
- [ ] Set `max_budget_usd` back to your normal value
- [ ] Close the terminal (or run `unset REPORTS_DB SEARCH_DB`), so your next runs use your real database again
- [ ] Delete `test-reports.db` and `test-search.db` (and their `-wal` and `-shm` files) when you're done

---

## 7. Alerts, calendar and Stocks tab checks

### 7.1 Alerts

Do this once you've set up Discord (`market-agent-alerts.md`). It uses your real webhook, so use a test channel if you'd rather not see test messages.

1. **Connection:** `python alerts.py test` posts "Alerts are set up".
2. **Preview:** `python alerts.py preview` prints what the latest report would send, without sending.
3. **A flag alert:**
   1. During market hours, with a scratch database (section 6.1) and the webhook set, run `python run_brief.py` with everything flagged (section 6.4).
   2. One message arrives with a card per ticker.
   3. Run again: nothing repeats.
4. **The summary:** after the close, run once more. The final report is saved and one summary arrives. Run again: no second summary.
5. **The log:** `python alerts.py log` lists each alert as `sent`.

**Check the messages:**

- [ ] The figures and sector sentences match the saved report
- [ ] Each card's stripe is green for up and red for down
- [ ] Publisher names link to the articles
- [ ] The footer says "research, not investment advice"
- [ ] Your phone shows a notification (alerts guide, section 12)

**Check failure and recovery:**

1. In the test channel, delete the webhook, then run with everything flagged. The run still succeeds, the last line is a warning ("Discord says this webhook doesn't exist"), and `python alerts.py log` shows `failed`.
2. Create a new webhook, set it, and run again. The alert is sent.

Afterwards, set your real webhook again.

### 7.2 The events calendar

Do this once you've built the calendar (`market-agent-events-calendar.md`). A scan costs a few cents. Use the scratch database from section 6.1 if you want to keep test scans apart from your real calendar.

1. **Run a scan:** `python events.py scan`. It prints a line per company, then something like `ok: 4 news events from 37 headlines, $0.041`, then any events it left out and why.
2. **List what it found:** `python events.py list`, then `python events.py show DATE` for a day with a news event.
3. **Check the Yahoo dates:** each company's next earnings date matches its investor-relations page, or is marked "(date not confirmed)" with a window.
4. **Check the news events:** for three of them, open the link (in the app, or from `show`). Each article should really give that date. Remove any it got wrong with `python events.py remove ID`.
5. **Check the "left out" lines:** they should be events without a specific date, or outside the 60 days. If real dated events are being left out, adjust `SYSTEM_PROMPT` in `events.py`.
6. **In the app:**
   - The Calendar tab shows the same events.
   - Clicking a date opens its page.
   - **Update now** shows progress, then "Updated" with the new time.
   - Pressing it again straight away explains the cooldown.
7. **Without Claude:** in a terminal without `ANTHROPIC_API_KEY`, `python events.py scan` gives `partial: ... (news scan: ...)`, but the earnings and dividend dates still update.
8. **Everywhere else it appears** (`market-agent-calendar-connect.md`):
   - **The Today tab:** the Coming up card lists the same next-week events, and each opens its day.
   - **The alerts preview:** `python alerts.py preview` on a final report ends with "Coming up:". A flag card shows its ticker's next event.
   - **Ask:** "What's coming up next week?" lists events cited as (calendar). "When does [a ticker] report earnings?" gives the calendar's date.

### 7.3 The Stocks tab

Do this once you've added finding and tracking stocks (`market-agent-stocks.md`). It edits your real `watchlist.txt`, so keep a copy first (`cp watchlist.txt watchlist.backup.txt`), or try it in the test environment, which has its own copy. Searching and adding are free; only runs cost money.

1. **Search:** on the Stocks tab, "costco" offers `COST` only; "berkshire" offers `BRK-B`; "bitcoin" offers nothing.
2. **Add:** **Track** a stock. `watchlist.txt` gains one line at the end, and nothing else changes (apart from stars added the first time, if the file had none). Its next earnings date appears within a few seconds, if it's within 60 days.
3. **Main stocks:** star and unstar a stock. The Today tab follows. A flagged stock that isn't main still shows, under "Also flagged".
4. **The next run:** after `python run_brief.py` (or **Run update now**), the new stock has a price and status, and the brief includes it.
5. **Limits:** the Track buttons are greyed out at 25 stocks, and the stars at 10 main stocks. A stock you already track shows "Tracking" in the results instead of the buttons.
6. **Hand edits:** add a line to `watchlist.txt` and save. The Stocks tab shows it within a few seconds.
7. **Remove:** **Remove**, then confirm. Its line goes, and the Previous days tab still shows it on past days.
8. **Longer lists:** with more than 10 stocks, `python events.py scan` reads the headlines in groups ("group 1 of 2") and prints one cost for the whole scan.

Afterwards, put back your own list if you changed it.

---

## 8. Schedule test

1. Set up the schedule from section 8 of the main guide, but set the time to 2–3 minutes from now.
   - **Cron:** the crontab needs every key the run uses: `ANTHROPIC_API_KEY`, plus `VOYAGE_API_KEY` and `DISCORD_WEBHOOK_URL` if you use search and alerts.
   - **The calendar's 9:35am job:** test it the same way, temporarily set to a few minutes from now. It only scans while the market is open, so test it during market hours; otherwise `run.log` says it was skipped.
   - **Task Scheduler:** set them with `setx`, then sign out and back in.
2. Wait for it to run.
3. Check:
   - [ ] `python reports_db.py list` shows the new or updated report at the top
   - [ ] `run.log` shows the tool calls and a `created`, `updated` or `finalized` line, with no errors or warnings
   - [ ] With a webhook set: the alert or summary arrived, and `run.log` shows a `Discord: sent ...` line
   - [ ] With the app open: it updated by itself within a few seconds
   - [ ] For the calendar job: `run.log` shows the scan's `ok:` line, and the Calendar tab's "Updated" time changed by itself
4. Change the schedule to your real times.
5. If you added the midday run, check the first real one: its report says "Intraday update" and the app's badge says it's still updating.

**If nothing happens:**

- The paths must be absolute.
- The keys must be available to the scheduler.
- The computer must have been awake.

**If a run happened but no alert came,** the scheduler is missing `DISCORD_WEBHOOK_URL`. Search still works without `VOYAGE_API_KEY`, but only by keyword.

---

## 9. Quality log

The automated tests prove the code works. Only you can judge whether the briefs and alerts are useful. For the first week or two, fill in one row per report:

| Date | Run (morning / intraday) | Flagged | Explanations correct? | Verdicts right? (stock / sector / market) | Missed anything? | Too noisy? | Alerts useful? | Notes / change to make |
|---|---|---|---|---|---|---|---|---|
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |
| | | | | | | | | |

**What to do with the results:**

| Pattern in the log | Change |
|---|---|
| Often too noisy (briefs or alerts) | Raise both flagging thresholds (try 2.5) |
| Missing moves you cared about | Lower the thresholds (try 1.5) |
| Explanations often wrong or speculative | Tighten the "Likely why" rules in `analyst_prompt.md` |
| A giant company is often `mixed` or `in line` when its own news drove the move | Give it an industry benchmark in `watchlist.txt` (sector guide, section 11) |
| Company news credited for sector-wide days | Add an example of the right wording to the prompt's "Sector and market context" section |
| Too many "Bigger move" alerts | Raise `ESCALATE_Z` in `alerts.py` (try 2.0) |
| Alerts arrive too late to be useful | Add intraday runs to the schedule (alerts guide, section 13) |
| Calendar news events often wrong | Check the links; remove bad ones (`events.py remove`), and tighten the rules in `SYSTEM_PROMPT` in `events.py` |
| Calendar misses events you saw in the news | Check the scan's "left out" lines: usually the article gave no specific date |
| Briefs ignore upcoming events in "Worth watching" | Add an example to the prompt's "Upcoming events" section, using a real line from `upcoming_events` |
| Same mistake every day | Add a specific rule against it in `analyst_prompt.md` |

Change one thing at a time, then run section 6 again so you know what helped.

---

## 10. Testing a new tool

Every new tool should get a test. Here's the pattern, using the `get_earnings_date` example from section 9.2 of the main guide.

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
    assert names == {"flag_events", "compute_moves", "get_news", "market_backdrop", "upcoming_events",
                     "get_earnings_date"}
```

**6. Let the agent use it.** Add `"mcp__market__get_earnings_date"` to `allowed_tools` in `run_brief.py`, and mention `` `get_earnings_date` `` in `analyst_prompt.md` (when to call it). `test_agent_can_use_every_market_tool` fails until you've done both, which stops a tool being added that the agent can't use.

**7. Run `pytest -v`.** Expect one more test than before (`242 passed, 3 skipped` with everything up to the stocks guide). Then check the new tool in the Inspector with live data (section 5).

**General rules for tool tests:**

- Test the normal case, the missing-data case and the error case.
- Compare numbers against a separate calculation, not against the tool's own output.
- Find out what real data looks like (with the Inspector), then make the fake data match that shape.

---

## 11. Troubleshooting the tests

| Problem | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'market_tools'` | Run `pytest` from the `market-agent` folder, not from inside `tests/`. |
| `ModuleNotFoundError: No module named 'yfinance'` (or `mcp`, `pandas`, `starlette`) | The virtual environment isn't active, or `pip install -r requirements.txt` wasn't run after the last guide. |
| `ModuleNotFoundError: No module named 'alerts'` | `test_alerts.py` is there but `alerts.py` isn't. Do the alerts guide, or remove `test_alerts.py` until you do. |
| `pytest: command not found` | Run `pip install pytest` with the virtual environment active, or use `python -m pytest -v`. |
| Only `test_tools_work_through_mcp` fails | It lists the tools it expects. Either MCP is version 1 (run `pip install -U "mcp>=2"`), or `market_tools.py` and this test file are from different guides. |
| The 13 sector-context tests fail, the rest pass | `market_tools.py` is older than this test file. Replace it from `market-agent-sector-context.md`. |
| `test_agent_can_use_every_market_tool` fails | A tool exists in `market_tools.py` but isn't in `allowed_tools` in `run_brief.py`, or isn't named in `analyst_prompt.md`. |
| `test_zscore_matches_independent_calculation` fails | The z-score code in `_completed_session_moves` has changed. Check the baseline excludes the session being measured. |
| The intraday and `test_market_session` tests fail, but the others pass | `market_tools.py` is a version from before market-hours support. Replace it with the current one. |
| Test messages appear in your Discord channel | `tests/conftest.py` is missing. Add it from the alerts guide. |
| `ModuleNotFoundError: No module named 'events'` | `test_events.py` is there but `events.py` isn't. Do the calendar guide, or remove `test_events.py` until you do. |
| Calendar tests fail with `no such table: events` | An old `events.py`. Replace it from the calendar guide's appendix. |
| `test_live_calendar_data` fails | Yahoo's calendar or company profile didn't load. Retry later, or run `pip install -U yfinance`. |
| `ModuleNotFoundError: No module named 'watchlist'` | `test_watchlist.py` is there but `watchlist.py` isn't. Do the stocks guide, or remove `test_watchlist.py` until you do. |
| `test_live_search` fails with "Searching needs a newer yfinance" | Run `pip install -U yfinance`. |
| `test_live_search` fails without finding `COST` | Yahoo's search didn't answer (rate limiting or a network problem). Wait a few minutes and retry. |
| Live test shows `skipped` | `LIVE_TESTS` isn't set. Use the exact command for your system in section 4. |
| Live test fails with `not enough price history` | Yahoo returned no data: rate limiting or a network problem. Wait a few minutes and retry, or run `pip install -U yfinance`. |
| Live test fails on `benchmark == "XLK"` | Yahoo's company profile (sector) didn't load. Retry later, or run `pip install -U yfinance`. Briefs still work meanwhile, comparing with the S&P 500. |
| Live test fails with `no intraday data for SPY` | Yahoo's 5-minute data didn't load (rate limiting or a network problem). Wait a few minutes and retry. |
| Live test numbers are slightly off from Yahoo's website while the market is open | Normal: intraday data can lag the live quote by a few minutes. Compare after the close for an exact match. |
| The Inspector won't start | Node.js isn't installed, or `python` points to the wrong interpreter. Use the virtual environment's Python (for example `.venv/bin/python`). |

---

## Appendix: test file source

Save this as `tests/test_market_tools.py`, replacing any earlier version.

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
FAKE_INFO = {}      # ticker -> company profile (e.g. {"sector": "Technology"}), or "raise"
HISTORY_CALLS = []  # every daily download, to check nothing is fetched twice


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    def history(self, period="3mo", interval="1d"):
        if interval != "1d":
            return FAKE_INTRADAY.get(self.ticker, pd.DataFrame(columns=["Close", "Volume"])).copy()
        HISTORY_CALLS.append(self.ticker)
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

    @property
    def info(self):
        if FAKE_INFO.get(self.ticker) == "raise":
            raise ConnectionError("Yahoo rate limit")
        return FAKE_INFO.get(self.ticker, {})


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
    FAKE_INFO.clear()
    HISTORY_CALLS.clear()
    market_tools._sectors.clear()  # sector lookups are remembered for the life of the process
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


def test_watchlist_can_name_a_benchmark_per_ticker(fake_market):
    fake_market.write_text("nvda  smh   # compare with semiconductors\nAAPL # no benchmark: uses its sector\n")
    assert market_tools.load_watchlist() == ["NVDA", "AAPL"]
    assert market_tools.load_benchmarks() == {"NVDA": "SMH"}


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
# Sector and market context
# ---------------------------------------------------------------------------

def tech_day(nvda_today, xlk_today, spy_today, volume_mult=1.0):
    """Three related return series: the market, the tech sector (market + sector noise) and
    NVDA (sector + company noise), with chosen moves for the last session."""
    spy = calm_returns(10) * 0.8
    xlk = spy + calm_returns(11) * 0.3
    nvda = xlk + calm_returns(12) * 0.5
    spy[-1], xlk[-1], nvda[-1] = spy_today, xlk_today, nvda_today
    volumes = normal_volume()
    volumes[-1] *= volume_mult
    FAKE_DAILY["SPY"] = (spy, normal_volume())
    FAKE_DAILY["XLK"] = (xlk, normal_volume())
    FAKE_DAILY["NVDA"] = (nvda, volumes)
    FAKE_INFO["NVDA"] = {"sector": "Technology"}
    return nvda, xlk, spy


def gap_zscore(a, b):
    """Recompute by hand: today's gap between two tickers vs. their gaps on past days."""
    ra = pd.Series(100 * np.cumprod(1 + a)).pct_change().dropna()
    rb = pd.Series(100 * np.cumprod(1 + b)).pct_change().dropna()
    gaps = ra - rb
    return (gaps.iloc[-1] - gaps.iloc[:-1].mean()) / gaps.iloc[:-1].std()


def test_benchmark_comes_from_sector_or_watchlist(fake_market):
    fake_market.write_text("NVDA SMH\nAAPL\nJPM\nQQQ\nNEWCO\nFLAKY\n")
    FAKE_INFO.update({"AAPL": {"sector": "Technology"}, "JPM": {"sector": "Financial Services"},
                      "QQQ": {"quoteType": "ETF"}, "FLAKY": "raise"})

    assert market_tools.benchmark_for("NVDA") == ("SMH", None)            # chosen in watchlist.txt
    assert market_tools.benchmark_for("AAPL") == ("XLK", "Technology")
    assert market_tools.benchmark_for("JPM") == ("XLF", "Financials")
    assert market_tools.benchmark_for("XLE") == ("SPY", None)             # a sector ETF: vs. the market
    assert market_tools.benchmark_for("QQQ") == ("SPY", None)             # no sector
    assert market_tools.benchmark_for("NEWCO") == ("SPY", None)           # unknown company
    assert market_tools.benchmark_for("FLAKY") == ("SPY", None)           # lookup failed: still works


def test_stock_specific_move(fake_market):
    fake_market.write_text("NVDA\n")
    nvda, xlk, spy = tech_day(nvda_today=0.07, xlk_today=0.004, spy_today=0.002)

    m = market_tools.flag_events()["flagged"][0]
    c = m["context"]

    assert c["benchmark"] == "XLK" and c["sector"] == "Technology"
    assert c["read"] == "stock-specific"
    assert c["vs_benchmark_pct"] == pytest.approx(7.0 - 0.4, abs=0.01)
    assert c["vs_benchmark_zscore"] == pytest.approx(gap_zscore(nvda, xlk), abs=0.01)
    assert c["benchmark_return_pct"] == pytest.approx(0.4, abs=0.01)
    assert c["market_return_pct"] == pytest.approx(0.2, abs=0.01)
    assert c["summary"].startswith("NVDA rose 7.00%; its sector (Technology, XLK) rose 0.40% "
                                   "and the S&P 500 rose 0.20%.")
    assert "specific to NVDA" in c["summary"]


def test_sector_wide_move(fake_market):
    fake_market.write_text("NVDA\n")
    tech_day(nvda_today=-0.052, xlk_today=-0.05, spy_today=-0.001)

    c = market_tools.flag_events()["flagged"][0]["context"]

    assert c["read"] == "sector-wide"
    assert abs(c["vs_benchmark_zscore"]) < 2
    assert c["benchmark_vs_market_zscore"] < -2
    assert "sector-wide move" in c["summary"]


def test_market_wide_move(fake_market):
    fake_market.write_text("NVDA\n")
    tech_day(nvda_today=-0.043, xlk_today=-0.041, spy_today=-0.04)

    c = market_tools.flag_events()["flagged"][0]["context"]

    assert c["read"] == "market-wide"
    assert c["market_zscore"] < -2
    assert "market-wide move" in c["summary"]


def test_volume_only_flag_is_in_line_with_peers(fake_market):
    fake_market.write_text("NVDA\n")
    tech_day(nvda_today=0.001, xlk_today=0.001, spy_today=0.0005, volume_mult=3)

    c = market_tools.flag_events()["flagged"][0]["context"]

    assert c["read"] == "in line"
    assert c["summary"].endswith("NVDA moved in line with its sector, and nothing unusual happened in the sector "
                                 "or the market.")


def test_partly_sector_move_is_mixed():
    """A gap wider than usual but not unusual (z-score between 1 and 2): partly the sector, partly the company."""
    c = market_tools.describe_context("AMZN", -5.46, "XLY", "Consumer Discretionary", -1.64, -1.01,
                                      -3.82, -1.86, -0.9, -1.2, in_progress=False)

    assert c["read"] == "mixed"
    assert "Part of the move matches its sector, but AMZN did 3.82 points worse" in c["summary"]


def test_quiet_tickers_are_not_compared(fake_market):
    """Context is only worked out for flagged moves, so quiet days download no ETFs."""
    fake_market.write_text("NVDA\n")
    tech_day(nvda_today=0.001, xlk_today=0.001, spy_today=0.001)

    result = market_tools.flag_events()

    assert result["flagged"] == [] and HISTORY_CALLS == ["NVDA"]


def test_each_benchmark_is_downloaded_once_per_scan(fake_market):
    fake_market.write_text("NVDA\nAMD\n")
    nvda, _, _ = tech_day(nvda_today=0.07, xlk_today=0.004, spy_today=0.002)
    FAKE_DAILY["AMD"] = (nvda * 1.1, normal_volume())
    FAKE_INFO["AMD"] = {"sector": "Technology"}

    result = market_tools.flag_events()

    assert {m["ticker"] for m in result["flagged"]} == {"NVDA", "AMD"}
    assert sorted(HISTORY_CALLS) == ["AMD", "NVDA", "SPY", "XLK"]


def test_context_problem_never_hides_the_move(fake_market):
    fake_market.write_text("NVDA\n")
    tech_day(nvda_today=0.07, xlk_today=0.004, spy_today=0.002)
    FAKE_DAILY["XLK"] = "raise"

    m = market_tools.flag_events()["flagged"][0]

    assert m["ticker"] == "NVDA" and m["return_1d_pct"] == pytest.approx(7.0, abs=0.01)
    assert "XLK" in m["context"]["error"]


def test_compute_moves_includes_context(fake_market):
    tech_day(nvda_today=-0.052, xlk_today=-0.05, spy_today=-0.001)

    result = market_tools.compute_moves("nvda")

    assert result["context"]["read"] == "sector-wide"


def test_intraday_context_compares_the_same_time_of_day(monkeypatch, fake_market):
    open_market(monkeypatch, cutoff="11:30")
    fake_market.write_text("NVDA\n")
    fake_open_market("NVDA", today_move=0.04, seed=1)
    fake_open_market("XLK", today_move=0.002, seed=2)
    fake_open_market("SPY", today_move=0.001, seed=3)
    FAKE_INFO["NVDA"] = {"sector": "Technology"}

    c = market_tools.flag_events()["flagged"][0]["context"]

    # Recompute by hand: each past session's return to 11:30, NVDA minus XLK
    def to_cutoff(ticker):
        intraday, daily = FAKE_INTRADAY[ticker], FAKE_DAILY[ticker]
        closes = {ts.date(): c for ts, c in zip(daily.index, daily["Close"])}
        sessions = sorted(closes)
        out = {}
        for day in sorted(set(intraday.index.date)):
            prev = closes[sessions[sessions.index(day) - 1]]
            at = intraday[(intraday.index.date == day) & (intraday.index.time <= time(11, 30))]
            out[day] = at["Close"].iloc[-1] / prev - 1
        return pd.Series(out)
    gaps = to_cutoff("NVDA") - to_cutoff("XLK")
    expected = (gaps.iloc[-1] - gaps.iloc[:-1].mean()) / gaps.iloc[:-1].std()

    assert c["read"] == "stock-specific"
    assert c["vs_benchmark_pct"] == pytest.approx(3.8, abs=0.01)
    assert c["vs_benchmark_zscore"] == pytest.approx(expected, abs=0.01)
    assert "so far today" in c["summary"]


def test_market_backdrop_ranks_sectors(fake_market):
    rng = np.random.default_rng(20)
    for etf in ["SPY", *market_tools.ETF_NAMES]:
        FAKE_DAILY[etf] = (rng.normal(0, 0.008, DAYS), normal_volume())
    FAKE_DAILY["XLE"][0][-1] = 0.045   # energy jumps
    FAKE_DAILY["XLK"][0][-1] = -0.012
    FAKE_DAILY["XLRE"] = "empty"       # one ETF with no data

    result = market_tools.market_backdrop()

    names = [s["ticker"] for s in result["sectors"]]
    assert names[0] == "XLE" and len(names) == 10
    assert [s["return_1d_pct"] for s in result["sectors"]] == sorted(
        [s["return_1d_pct"] for s in result["sectors"]], reverse=True)
    assert result["market"]["ticker"] == "SPY"
    assert result["errors"] == [{"ticker": "XLRE", "error": "not enough price history"}]
    assert "Strongest sector: Energy (XLE) +4.50%" in result["summary"]
    assert "Unusual sector moves: Energy +4.50%" in result["summary"]


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

    assert names == {"flag_events", "compute_moves", "get_news", "market_backdrop", "upcoming_events"}
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
    backdrop = market_tools.market_backdrop()

    assert "error" not in result, result
    assert (result.get("last_close") or result.get("last_price")) > 0
    assert -50 < result["return_1d_pct"] < 50
    assert result["context"].get("benchmark") == "XLK", result["context"]  # Apple's sector, looked up live
    assert backdrop["market"] and len(backdrop["sectors"]) >= 10, backdrop["errors"]
    print("\nLive session:", session)
    print("Live AAPL:", {k: v for k, v in result.items() if k != "context"})
    print("Live AAPL vs. sector:", result["context"]["summary"])
    print("Live backdrop:", backdrop["summary"])
```
