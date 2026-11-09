# Market Analyst Agent: Finding and Tracking Stocks

Until now, changing which stocks the agent follows meant editing `watchlist.txt` by hand. This guide adds that to the app:

| Where | What changes |
|---|---|
| **Stocks tab (new)** | Find US stocks and ETFs by company name or ticker, and track them. Star your **main** stocks, remove stocks, and see each one's latest price, status and next calendar event |
| **Today tab** | Shows only your main stocks (up to 10), in your order. Any other stock flagged today still appears, under "Also flagged", so nothing unusual is hidden. A note links to the rest |
| **`watchlist.txt`** | Still the one list everything reads. A `*` in front of a ticker marks a main stock. The app changes the file one line at a time, so your comments and benchmarks stay |
| **Everything else** | Every tracked stock, main or not, is in each brief, alert and calendar update, as before |

You can track up to **25 stocks** to keep costs down, and raise that with one setting when you need more (section 11). Starring a stock only decides where it's shown: it doesn't change what's analysed or what it costs.

This builds on `market-agent-calendar-connect.md`, and this guide's files include every earlier change.

---

## Contents

1. [What it looks like](#1-what-it-looks-like)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Add watchlist.py](#4-step-1-add-watchlistpy)
5. [Step 2: Update the agent and the calendar for longer lists](#5-step-2-update-the-agent-and-the-calendar-for-longer-lists)
6. [Step 3: Add the API endpoints](#6-step-3-add-the-api-endpoints)
7. [Step 4: Add the Stocks tab](#7-step-4-add-the-stocks-tab)
8. [Step 5: Add the tests](#8-step-5-add-the-tests)
9. [Step 6: Try it](#9-step-6-try-it)
10. [Test it](#10-test-it)
11. [Tracking more stocks](#11-tracking-more-stocks)
12. [Settings](#12-settings)
13. [Costs](#13-costs)
14. [Security](#14-security)
15. [Troubleshooting](#15-troubleshooting)
16. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it looks like

These examples are from the test environment, so the prices and events are simulated. Screenshots are in `stocks-preview.png`.

**The Stocks tab:**

```
FIND STOCKS                                              6 of 25 tracked · 3 of 10 main
┌──────────────────────────────────────────────────────────────────────────────────────┐
│ costco                                                                               │
└──────────────────────────────────────────────────────────────────────────────────────┘
US-listed stocks and ETFs, from Yahoo Finance.
  COST Costco Wholesale Corporation · Stock · NASDAQ                [Track] [Track as main]

TRACKED STOCKS                   Every tracked stock is in each report, alert and calendar update
      Ticker  Company            Price    Change   Status    Next event
MAIN: ON THE TODAY TAB (3 OF 10)
  ★   AAPL    Apple              76.64    -0.13%   quiet     Mon Nov 16: Court hearing in patent case
  ★   NVDA    NVIDIA             81.88    +0.31%   quiet     Tue Dec 15: Earnings report (date not confirmed)
  ★   COST    Costco Wholesale  960.19    -1.29%   quiet     Mon Jan 4: Earnings report
ALSO TRACKED (3)
  ☆   MSFT    Microsoft         323.91    +4.96%   flagged   Mon Nov 9: Court hearing in patent case
  ☆   AMZN    Amazon.com        180.67    +0.36%   quiet     —
  ☆   JPM     JPMorgan Chase    207.44    +0.37%   quiet     Thu Nov 19: Investor day
```

Each row ends with a **Remove** link.

- Click a star to make a stock main or not.
- Click a ticker to open its chart.
- Click a next event to open its day on the Calendar tab.
- **Remove** asks once more ("Remove COST" or "Keep").

**The Today tab** shows the main stocks. MSFT isn't main, but it was flagged today, so it's still shown:

```
Ticker   Status    Price    Change   z-score   Volume   Vs. sector
AAPL     quiet     76.64    -0.13%   —         —        —
NVDA     quiet     81.88    +0.31%   —         —        —
COST     quiet    960.19    -1.29%   —         —        —
ALSO FLAGGED (NOT A MAIN STOCK)
MSFT     flagged  323.91    +4.96%   3.0       1.68×    +5.09 pts vs XLK, stock-specific
Showing your main stocks. 2 more in this report: see all tracked stocks.
```

The brief underneath is unchanged and still covers every tracked stock. The Previous days tab still shows every stock for each day.

**`watchlist.txt`**, before and after adding Costco as a main stock. The file had no stars, so all three stocks were main; the first change from the app writes their stars in:

```
# One ticker per line. Lines starting with # are ignored.
AAPL
NVDA SMH          # compared with semiconductors
MSFT
```

```
# One ticker per line. Lines starting with # are ignored.
*AAPL
*NVDA SMH          # compared with semiconductors
*MSFT
*COST
```

Unstarring MSFT on the Stocks tab then changes just that line back to `MSFT`.

---

## 2. How it works

```
Stocks tab
  │ type "costco" ─────▶ GET /api/stocks/search ──▶ watchlist.search() ──▶ Yahoo Finance search
  │ Track ─────────────▶ POST /api/watchlist ─────▶ watchlist.add(): checks the ticker with Yahoo,
  │                                                  then adds one line to watchlist.txt
  │                                                  └─ in the background: its earnings and
  │                                                     dividend dates (Yahoo only, no Claude)
  │ ★ / Remove ────────▶ POST /api/watchlist/{TICKER} (or …/remove) ──▶ edits that one line
  ▼
watchlist.txt ──▶ the agent, alerts and the calendar scan: every tracked stock
              └─▶ GET /api/watchlist: main stocks first ──▶ Today tab (main only) and Stocks tab (all)
```

- **One list.** `watchlist.txt` stays the single source of truth, so the scheduled runs, the calendar job and the app always agree. You can still edit it by hand: open pages update within a few seconds.
- **Main stocks.** A `*` before a ticker marks a main stock. If no line has a `*`, the first 10 count as main, so your current file works unchanged. With 5 stocks, all 5 are main and the Today tab looks as it did before.
- **Safe edits.** The app changes one line and leaves every other line, comment and benchmark as it was. It writes a new copy of the file and swaps it in, so a run starting at that moment reads either the old list or the new one, never half of each. Edits from two browser tabs at once are applied one after the other.
- **The first edit adds stars.** If your file has no stars yet, the first change from the app writes a `*` in front of the stocks that are currently main (the first 10). Otherwise, adding an 11th stock could quietly change which ones are main.
- **Checked before it's added.** A stock is only added if:
  - it looks like a US ticker (letters, numbers and `-`, like `BRK-B`)
  - Yahoo Finance knows it
  - it's a stock or an ETF (not crypto, a mutual fund, a future or an index)
  - you aren't already tracking it, and you're under the limits (25 tracked, 10 main)
- **Search shows only what can be tracked.** Listings outside the US (Yahoo writes these with a dot, like `COST.MX`) and other types are filtered out. Results are cached for 10 minutes, and the app waits for a pause in typing before searching.
- **A new stock's first figures come with the next report.** Until then the Stocks tab says "first report next run". Its earnings and dividend dates are added to the calendar straight away. News events for it come with the next daily calendar scan.
- **Removing a stock keeps its history.** Its past reports, search results and calendar history stay. It's left out of future runs, alerts and "Coming up".
- **Every stock's price.** `flag_events` now includes the price for quiet stocks too, so the Stocks tab can show it. Reports saved before this change have no price for quiet stocks, so those show "—" until the next run.
- **Short company names.** Names come from Yahoo and are shortened as on the calendar, which now also drops a leading "The" ("The Coca-Cola Company" becomes "Coca-Cola").

---

## 3. Before you start

- [ ] You've done `market-agent-calendar-connect.md`, and `pytest` shows `208 passed, 2 skipped`.
- [ ] Your yfinance has Yahoo's search (check below).
- [ ] Optional: keep a copy of your list first (`cp watchlist.txt watchlist.backup.txt`, or `copy` on Windows). The app edits this file now.

**Check yfinance:**

```bash
python -c "import yfinance as yf; print(yf.__version__, hasattr(yf, 'Search'))"
```

If it prints `False`, run `pip install -U yfinance`. No other packages or keys are needed.

---

## 4. Step 1: Add watchlist.py

1. Add `watchlist.py` from the [appendix](#watchlistpy). Everything that reads or changes the list goes through it:

   | Function | What it does |
   |---|---|
   | `entries()` | Every tracked stock in file order: ticker, benchmark, and whether it's main |
   | `main_tickers()` | Just the main ones |
   | `add(ticker, main=False)` | Checks the ticker with Yahoo, then adds it |
   | `set_main(ticker, main)` | Stars or unstars it |
   | `remove(ticker)` | Stops tracking it |
   | `search(query)` | US stocks and ETFs matching a name or ticker, best match first |
   | `check_ticker(ticker)` | Confirms Yahoo knows it and it's a stock or ETF |

   Problems raise `WatchlistError` with a message ready to show, such as "You're already tracking COST."

2. Replace `market_tools.py` with the appendix version. Two small changes:
   - **It ignores the `*`** when reading `watchlist.txt`. The agent tracks every stock either way.
   - **Quiet stocks keep their price** in `flag_events`' result (`last_close`, or `last_price` while the market is open).

**Try it** (free, needs internet):

```bash
python -c "import watchlist; print(watchlist.search('costco'))"
python -c "import watchlist; print(watchlist.main_tickers())"
```

The first should list `COST` as a Stock on NASDAQ. The second lists your first 10 tickers (or all of them, if you have fewer).

**To choose main stocks by hand,** put a `*` in front of them in `watchlist.txt`. As soon as one line has a star, only starred stocks are main.

---

## 5. Step 2: Update the agent and the calendar for longer lists

Replace `run_brief.py` and `events.py` with the appendix versions.

- **`run_brief.py`: the agent gets more turns for a longer list.**
  - On a market-wide day most of your list can be flagged, and the agent reads the news for each flagged stock. With 25 stocks, the old fixed limit of 25 turns could stop a run before it finished.
  - `turn_limit()` now allows 10 more turns than you have stocks, and never fewer than 25. With 5 stocks nothing changes; with 25 stocks it's 35.
  - The cost cap (`max_budget_usd`, $1.00 a run) is unchanged, so this can't raise what a run may cost.
- **`events.py`: the calendar scan reads news in groups.**
  - Claude now reads the headlines for **10 companies at a time** (`BATCH_TICKERS`), one request per group, instead of the whole list in one request. With 25 stocks that's 3 small requests.
  - Each request has its own cost cap (`SCAN_BUDGET_USD`, $0.25), and the scan's cost is the total.
  - If one group fails, the others are still saved. The scan says `partial`, naming the group (for example "news scan (group 2 of 3): …").
  - `add_calendar_dates(ticker)` adds a new stock's earnings and dividend dates from Yahoo, with no Claude call. The API calls it when you add a stock.
  - `short_name()` drops a leading "The".

---

## 6. Step 3: Add the API endpoints

Replace `api.py` with the appendix version. It adds:

| Endpoint | What it does |
|---|---|
| `GET /api/watchlist` | Every tracked stock, main ones first, with its name, latest figures and next calendar event, plus the counts and limits |
| `GET /api/stocks/search?q=costco` | Up to 8 US stocks and ETFs matching a name or ticker, each marked if you already track it |
| `POST /api/watchlist` with `{"ticker": "COST", "main": false}` | Tracks a stock (`201`). Returns the stock and the updated list |
| `POST /api/watchlist/COST` with `{"main": true}` | Stars or unstars it |
| `POST /api/watchlist/COST/remove` with `{}` | Stops tracking it |

**What a stock looks like in `GET /api/watchlist`:**

```json
{"ticker": "COST", "main": true, "benchmark": null, "name": "Costco Wholesale",
 "latest": {"session_date": "2026-11-06", "status": "intraday", "category": "quiet", "price": 960.19,
            "return_1d_pct": -1.29, "return_zscore": null, "move_read": null},
 "next_event": {"event_date": "2027-01-04", "kind": "earnings", "title": "Earnings report",
                "line": "Mon Jan 4: Earnings report"}}
```

`latest` is `null` until the stock is in a report. Quiet stocks have no z-score or verdict (`null`), as in the reports. The list also has `tracked_count`, `main_count`, `max_tracked` and `max_main`.

**When something can't be done,** the reply has an `error` message to show:

| Status | When |
|---|---|
| `400` | Not a US ticker, Yahoo doesn't know it, it's not a stock or ETF, or the request is malformed |
| `404` | That stock isn't on your list |
| `409` | You already track it, or a limit is reached |
| `403` / `415` | The request came from another website, or isn't JSON (section 14) |
| `502` | Yahoo's search isn't answering. Try again shortly |

**Live updates.** Every change sends a `watchlist_changed` event, so all open pages refresh. The background check that already looks for new reports now also notices when `watchlist.txt` is edited by hand (within `REPORT_POLL_SECONDS`, 2 seconds by default).

**Try it** with the API running (`uvicorn api:app --port 8000`):

```bash
curl "http://127.0.0.1:8000/api/stocks/search?q=costco"
curl http://127.0.0.1:8000/api/watchlist
```

---

## 7. Step 4: Add the Stocks tab

Replace or add these files in `frontend/src/`:

| File | Change |
|---|---|
| `components/StocksTab.jsx` | **New:** Find stocks (search, Track, Track as main) and Tracked stocks (stars, charts, next events, Remove) |
| `components/TickerTable.jsx` | On the Today tab: main stocks only, then "Also flagged", then the "N more" note |
| `components/ReportView.jsx` | Passes the main stocks to the table |
| `App.jsx` | The Stocks tab; loads the list and keeps it current |
| `useRoute.js` | The `#/stocks` address |
| `api.js` | `getWatchlist`, `searchStocks`, `addStock`, `setMainStock`, `removeStock` |
| `styles.css` | Stars, search results and group rows. Also a fix: on a phone, hidden column labels could make the whole page scroll sideways; tables now keep them inside their own scroll area |

Then rebuild if you serve the built app (`cd frontend && npm run build`).

---

## 8. Step 5: Add the tests

1. Add `tests/test_watchlist.py` from the [appendix](#teststest_watchlistpy).
2. Run:

```bash
pytest -v
```

**Expected result:** `241 passed, 3 skipped`. The new skipped test is a live check of Yahoo's search (section 10.3).

The new file alone (`pytest -v tests/test_watchlist.py`) gives `33 passed, 1 skipped`. They use a temporary watchlist and database, so your real `watchlist.txt` is never touched.

---

## 9. Step 6: Try it

Start the app as usual (frontend guide, section 6), then:

1. **Open the Stocks tab.** Your stocks are listed with "Main: on the Today tab" at the top.
2. **Find a stock.** Type "costco". Only `COST` is offered (not Costco's Mexican listing). Click **Track**.
   - `watchlist.txt` gains one line at the end, `COST`. If the file had no stars, the first 10 stocks now have a `*`.
   - Within a few seconds, COST's next earnings date appears under "Next event", if it's within 60 days.
3. **Star it.** The Today tab now includes COST, after your other main stocks.
4. **Unstar a stock that's flagged today.** It leaves the main list, but the Today tab still shows it under "Also flagged".
5. **Run an update** (**Run update now**, or `python run_brief.py`). COST gets its first figures, and the brief includes it.
6. **Remove it.** Click **Remove**, then **Remove COST**. Its line leaves `watchlist.txt`.
7. **Edit by hand.** Add a line such as `*KO` to `watchlist.txt` and save. The Stocks tab shows it within a few seconds.

To try all of this without spending anything or changing your real list, use the test environment (`market-agent-test-enviro.md`). It has its own copy of the watchlist and an offline search.

---

## 10. Test it

### 10.1 Automated tests

*In `tests/test_watchlist.py`*

| Test | Proves that |
|---|---|
| `test_a_star_marks_a_main_stock` | Starred stocks are main; the agent still tracks every stock, and benchmarks still work |
| `test_without_stars_the_first_ten_are_main` | An unstarred file works as before: the first 10 are main |
| `test_adding_keeps_every_other_line_as_it_was` | Adding writes one line and changes nothing else |
| `test_the_first_edit_makes_the_implicit_main_stocks_explicit` | The first edit stars the current main stocks, so adding a stock can't change which ones are main |
| `test_adding_checks_the_ticker_first` (5 cases) | Unknown tickers, crypto, listings outside the US, a Yahoo outage and an empty ticker are refused with a clear message, and the file is unchanged |
| `test_limits_on_tracked_and_main_stocks` | Doubles, the tracked limit and the main limit are refused (`409`) |
| `test_star_and_unstar_keep_the_rest_of_the_line` | Stars come and go without touching benchmarks or comments |
| `test_remove` | Removing deletes just that line; removing again says it isn't on your list (`404`) |
| `test_edits_at_the_same_time_are_never_lost` | 8 stocks added at once all arrive, and no temporary files are left behind |
| `test_editing_keeps_the_files_permissions` | The file keeps its permissions after an edit |
| `test_search_finds_us_stocks_and_etfs_only` | Search keeps US stocks and ETFs, drops funds, crypto, indexes and foreign listings, and marks stocks you already track |
| `test_search_is_cached_and_problems_are_clear` | Repeat searches come from the cache, and a Yahoo outage gives a clear message |
| `test_api_lists_main_stocks_first_with_their_latest_figures` | The API lists main stocks first with their latest figures (prices for quiet stocks too), and fills in missing names in the background |
| `test_short_names_for_new_stocks` (3 cases) | "The Coca-Cola Company" becomes "Coca-Cola", and so on |
| `test_quiet_stocks_keep_their_price` | `flag_events` gives quiet stocks a price |
| `test_api_add_star_and_remove` | Add, star and remove through the API, with live updates, and the new stock's earnings date added in the background |
| `test_api_explains_what_went_wrong` (6 cases) | Each kind of problem gets the right status and message |
| `test_other_websites_cannot_change_the_list` | Requests from another website are refused (`403`) and the file is unchanged |
| `test_api_search` | The search endpoint, a missing query (`400`) and a Yahoo outage (`502`) |
| `test_editing_watchlist_txt_by_hand_updates_open_pages` | Saving the file by hand tells open pages to refresh |
| `test_bigger_watchlists_give_the_agent_more_turns` | 40 stocks give the agent 50 turns; the cost cap is unchanged |
| `test_calendar_scan_reads_a_long_watchlist_in_groups` | 23 stocks become 3 requests (10, 10 and 3 companies), costs add up, and one failed group doesn't lose the others |
| `test_live_search` | Live only: Yahoo's real search finds Costco, and `COST` checks out as a stock (section 10.3) |

**Check the tests catch real bugs.** Make one of these temporary changes, run `pytest tests/test_watchlist.py`, then change it back. Each was tried:

| Temporary change | Test that fails |
|---|---|
| `watchlist.py`: in `_can_add`, `len(current) >= MAX_TRACKED` → `>` | `test_limits_on_tracked_and_main_stocks` |
| `watchlist.py`: in `search`, delete `or not TICKER.fullmatch(symbol)` | `test_search_finds_us_stocks_and_etfs_only` and `test_api_search` |
| `watchlist.py`: in `_edit`, `if current and not any(e["starred"] for e in current):` → `if False:` | `test_the_first_edit_makes_the_implicit_main_stocks_explicit` |
| `events.py`: `BATCH_TICKERS = 10` → `100` | `test_calendar_scan_reads_a_long_watchlist_in_groups` |
| `market_tools.py`: drop `**price,` from the `quiet.append(...)` line | `test_quiet_stocks_keep_their_price` |
| `run_brief.py`: `options=dataclasses.replace(options, max_turns=turn_limit())` → `options=options` | `test_bigger_watchlists_give_the_agent_more_turns` |

### 10.2 What was also tested

- **From the guides alone:** both projects were rebuilt from the guides (this one included), and all tests passed.
- **In a real browser, against the test environment.** It now has its own watchlist, an offline search, and simulated prices for stocks you add. The 13 checks passed with no browser errors:
  1. The Today tab shows only the 3 main stocks, with "2 more in this report".
  2. The note's link opens the Stocks tab, with the counts, both groups, names, prices and status.
  3. Searching "costco" offers only `COST`. **Track as main** adds it, and its next earnings date appears.
  4. Searching "bitcoin" offers nothing.
  5. Unstarring MSFT, flagged that day, moves it under "Also flagged" on the Today tab.
  6. After **Run update now**, COST has figures and joins the main stocks on the Today tab.
  7. COST's chart opens from the Stocks tab.
  8. COST's next event opens its day on the Calendar tab.
  9. **Remove** asks once more; **Keep** cancels.
  10. A line added to the watchlist file by hand shows up without a reload.
  11. On a phone, nothing scrolls sideways.
  12. Dark mode renders.
  13. The main project's `watchlist.txt` was unchanged afterwards.

  The earlier Today, Previous days, chart, search, sector and alerts, calendar and Coming up checks all still pass.
- **Found and fixed while testing:**
  - Quiet stocks had no price in saved reports, so most of the Stocks tab's prices were blank. `flag_events` now includes it.
  - On a phone, the Stocks tab's page scrolled sideways. Hidden column labels were escaping the table's own scroll area (`styles.css`).

**Not tested here:** Yahoo's real search, because Yahoo Finance couldn't be reached from where this guide was built. Run the live check below once.

### 10.3 Checks with real data

**The live search test** (free, needs internet):

```bash
LIVE_TESTS=1 pytest -v -s -k live_search                  # macOS / Linux
$env:LIVE_TESTS=1; pytest -v -s -k live_search            # Windows PowerShell
```

**Expected result:** `1 passed`. It prints your yfinance version and Yahoo's matches for "costco", which should include `COST` (NASDAQ) as an `EQUITY`, then the checked stock.

**Then check by hand:**

- [ ] "berkshire" offers `BRK-B`, and "semiconductor" offers ETFs such as `SMH`. Non-US listings (with a dot) aren't offered
- [ ] Adding a stock adds one line at the end of `watchlist.txt`, and your comments and benchmarks are unchanged
- [ ] A new stock's next earnings date matches its investor-relations page (or says "not confirmed")
- [ ] The next brief includes the new stock, in "Quiet" or "Notable moves", and the Stocks tab shows its price
- [ ] With more than 10 stocks, `python events.py scan` prints "Reading … headlines for dated events (group 1 of 2)" and so on, then one cost for the whole scan
- [ ] After removing a stock, the Previous days tab still shows it on past days, and the next brief doesn't mention it

---

## 11. Tracking more stocks

The 25-stock limit keeps costs predictable. It only applies to adding stocks in the app. To track more:

1. **Raise the limit** where the API runs, then restart it:

   ```bash
   export MAX_TRACKED=40            # macOS / Linux, before: uvicorn api:app --port 8000
   $env:MAX_TRACKED=40              # Windows PowerShell
   ```

   If the API runs as a service, add `MAX_TRACKED=40` to its environment. Nothing else needs it: the scheduled runs track whatever is in `watchlist.txt`.
2. **Add the stocks** on the Stocks tab, or by hand. A hand-edited list can be longer than the limit; the app then just won't add more.

**What adjusts by itself as the list grows:**

| Part | How |
|---|---|
| The agent's turns | 10 more than the number of stocks (at least 25) |
| The calendar scan | One Claude request per 10 stocks, each with its own $0.25 cap |
| The Today tab | Still at most 10 main stocks, plus anything flagged |

**What to watch after growing the list:**

- **Cost per run.** Each run prints its cost. If runs on busy days stop with `error_max_budget_usd`, raise `max_budget_usd` in `run_brief.py` a little.
- **Run time.** Each stock is one more Yahoo download per run (plus 5-minute prices while the market is open), so runs take a little longer.
- **Yahoo's limits.** Yahoo Finance can slow down or refuse very frequent requests. If stocks start appearing under "Data issues", run less often or track fewer.
- **Discord.** More stocks means more flag alerts on busy days.

To show more than 10 main stocks on the Today tab, change `MAX_MAIN` in `watchlist.py`.

---

## 12. Settings

| Where | Setting | Default | What it does |
|---|---|---|---|
| Environment (where the API runs) | `MAX_TRACKED` | `25` | Most stocks the app will let you track |
| `watchlist.py` | `MAX_MAIN` | `10` | Most main stocks (the Today tab) |
| `watchlist.py` | `ALLOWED_TYPES` | stocks and ETFs | What can be tracked |
| `watchlist.py` | `SEARCH_CACHE_SECONDS` | `600` | How long search results are reused |
| `components/StocksTab.jsx` | `SEARCH_DELAY_MS` | `350` | Pause in typing before searching |
| `events.py` | `BATCH_TICKERS` | `10` | Companies per Claude request in the calendar scan |
| `run_brief.py` | `BASE_TURNS` | `25` | The agent's turn limit for short lists (longer lists get more) |
| `api.py` | `REPORT_POLL_SECONDS` (environment) | `2` | How often hand edits to `watchlist.txt` are noticed |

---

## 13. Costs

- **Finding and adding stocks:** free. Search, ticker checks, names and a new stock's earnings dates all come from Yahoo Finance, with no Claude call.
- **Main or not:** no difference. Every tracked stock is analysed the same way; starring only decides where it's shown. The number of **tracked** stocks is what drives cost.
- **Briefs:** a quiet stock adds one short line for Claude to read. A flagged stock adds a news check and a few paragraphs. More stocks means more flagged moves on an average day, so expect run costs to rise with the list, most on busy days. `max_budget_usd` still caps each run.
- **The calendar scan:** grows with the number of headlines read, so roughly in step with the list. With 25 stocks it's 3 requests per scan, each capped at $0.25. `events.py scan` prints the total.
- **Alerts and the app:** cost nothing extra.

---

## 14. Security

- **Other websites can't change your list.** Add, star and remove use the same protection as Run now: requests from another website are refused (`403`), and only JSON requests are accepted, which a plain web form can't send.
- **Nothing odd can be written into the file.** A ticker must be letters, numbers and `-`, and Yahoo must confirm it before it's written. A ticker can't contain a new line, a `#` or a `*`.
- **What Yahoo sees:** the text you type in the search box, and the tickers you add. Nothing else is sent.
- **Who can change the list:** anyone who can reach your API, the same as Run now. The API listens on your own computer only (`127.0.0.1`), as set up in the frontend guide. Don't make it reachable from the internet without adding a login.

---

## 15. Troubleshooting

| Problem | Cause and fix |
|---|---|
| "Searching needs a newer yfinance" | Your yfinance has no `Search`. Run `pip install -U yfinance`, then restart the API. |
| "Yahoo Finance search isn't answering right now" | Network trouble or Yahoo's rate limit. Wait a minute and try again. Searches are cached for 10 minutes, so retrying the same search is free once one works. |
| "Yahoo Finance doesn't know X" | A typo, or a ticker that's been delisted or renamed. Search by company name instead. |
| A stock you want isn't offered | It may be listed outside the US (Yahoo adds a dot, like `.L` or `.TO`), or be a mutual fund or index. Only US-listed stocks and ETFs can be tracked. |
| "You're tracking 25 stocks, the most allowed" | Remove one, or raise `MAX_TRACKED` (section 11). |
| "You already have 10 main stocks" | Unstar one first, or add the new stock as tracked only. |
| A new stock says "first report next run" | Normal until the next run. Press **Run update now**, or wait for the schedule. |
| A new stock has no next event | Yahoo has no earnings or dividend date for it within 60 days. News events come with the next daily calendar scan. |
| Prices show "—" for quiet stocks | The latest report was saved before this guide. The next run fills them in. |
| The Today tab shows fewer stocks than the brief | Working as intended: it shows main stocks, plus anything flagged. The note under the table links to the rest. |
| Hand edits to `watchlist.txt` don't show | Save the file, and check the page's dot says **Live**. Some editors save by writing a new file; the change still shows within a few seconds. |
| `watchlist.txt is missing` on the Stocks tab | The API can't find the file. Create it in the `market-agent` folder with one ticker per line. |
| The app removed my comment | It doesn't. Only the line for the stock you change is touched. A removed stock's line goes completely, including any comment on that line. |

---

## Appendix: full source code

### watchlist.py

```python
"""Tracked stocks: find them, add and remove them, and choose the main ones for the dashboard.

watchlist.txt stays the one list everything reads (the agent, alerts, the calendar).
A * in front of a ticker marks a main stock, shown first on the Today tab:

    *AAPL
    *NVDA  SMH      # a benchmark and a comment, as before
    MSFT

If no ticker has a *, the first 10 count as main, so older watchlists work unchanged.

The app edits the file one line at a time, so your other lines, benchmarks and comments
are kept. Each edit replaces the file in one step, so a run starting at that moment
sees either the old list or the new one, never half of each.
"""

import os
import re
import tempfile
import threading
import time

import yfinance as yf

import events
import market_tools

MAX_TRACKED = int(os.environ.get("MAX_TRACKED", "25"))  # raise when you want to track more (see the guide)
MAX_MAIN = 10                                          # main stocks shown on the dashboard
ALLOWED_TYPES = {"EQUITY": "Stock", "ETF": "ETF"}       # what can be tracked (no funds, futures, crypto...)
SEARCH_CACHE_SECONDS = 600
TICKER = re.compile(r"[A-Z0-9][A-Z0-9\-]{0,9}")         # US tickers as Yahoo writes them, e.g. BRK-B

_lock = threading.Lock()  # one edit at a time within this program
_search_cache: dict[str, tuple[float, list[dict]]] = {}


class WatchlistError(ValueError):
    """A request that can't be done, with a message to show as it is.
    status is the matching HTTP status for the API: 400, 404 (not on the list) or 409 (conflicts)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _path():
    return market_tools.WATCHLIST_FILE  # read each time, so tests and the test environment can point elsewhere


def _parse(line: str) -> dict | None:
    code = line.split("#", 1)[0]
    words = code.replace("*", " ").upper().split()
    if not words:
        return None
    return {"ticker": words[0], "benchmark": words[1] if len(words) > 1 else None, "starred": "*" in code}


def entries() -> list[dict]:
    """Every tracked stock in file order: ticker, benchmark, and whether it's a main stock."""
    found = [e for e in (_parse(line) for line in _path().read_text().splitlines()) if e]
    any_star = any(e["starred"] for e in found)
    for i, e in enumerate(found):
        e["main"] = e["starred"] if any_star else i < MAX_MAIN
    return found


def main_tickers() -> list[str]:
    return [e["ticker"] for e in entries() if e["main"]]


# ---------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------

def _write(lines: list[str]) -> None:
    """Replace the file in one step (write a temporary file, then swap it in)."""
    path = _path()
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".watchlist-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        try:
            os.chmod(temp, path.stat().st_mode & 0o777)  # keep the file's permissions
        except OSError:
            pass
        os.replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def _star(line: str, on: bool) -> str:
    """Add or remove the * in front of the ticker, keeping the rest of the line as it was."""
    code, sep, comment = line.partition("#")
    code = code.replace("*", "")
    if on:
        code = re.sub(r"^(\s*)(\S)", r"\1*\2", code, count=1)
    return code + sep + comment


def _edit(change) -> list[dict]:
    """Read the file, apply change(lines, rows, current) and write it back, all under the lock.
    rows maps each ticker to its line number; current is the list as entries() gives it."""
    with _lock:
        lines = _path().read_text().splitlines()
        rows = {}
        for i, line in enumerate(lines):
            parsed = _parse(line)
            if parsed:
                rows[parsed["ticker"]] = i
        current = entries()
        if current and not any(e["starred"] for e in current):  # make the implicit main stocks explicit first,
            for e in current:                                     # so the edit can't change which ones are main
                if e["main"]:
                    lines[rows[e["ticker"]]] = _star(lines[rows[e["ticker"]]], True)
        change(lines, rows, current)
        _write(lines)
    return entries()


def _can_add(ticker: str, main: bool, current: list[dict]) -> None:
    if ticker in {e["ticker"] for e in current}:
        raise WatchlistError(f"You're already tracking {ticker}.", 409)
    if len(current) >= MAX_TRACKED:
        raise WatchlistError(f"You're tracking {MAX_TRACKED} stocks, the most allowed. Remove one first, "
                             "or raise MAX_TRACKED (see the guide).", 409)
    if main and sum(e["main"] for e in current) >= MAX_MAIN:
        raise WatchlistError(f"You already have {MAX_MAIN} main stocks. Add it as tracked, or unstar one first.", 409)


def add(ticker: str, main: bool = False) -> dict:
    """Start tracking a stock, after checking it with Yahoo Finance. Returns its details."""
    ticker = ticker.strip().upper()
    if not TICKER.fullmatch(ticker):
        raise WatchlistError("That isn't a US ticker (letters, numbers and - only, like AAPL or BRK-B).")
    _can_add(ticker, main, entries())  # quick checks before asking Yahoo...
    info = check_ticker(ticker)

    def change(lines, rows, current):
        _can_add(ticker, main, current)  # ...and again under the lock, in case the list changed meanwhile
        lines.append(f"{'*' if main else ''}{ticker}")

    _edit(change)
    return {**info, "main": main}


def remove(ticker: str) -> None:
    """Stop tracking a stock. Its past reports and calendar history stay."""
    ticker = ticker.strip().upper()

    def change(lines, rows, current):
        if ticker not in rows:
            raise WatchlistError(f"{ticker} isn't on your list.", 404)
        del lines[rows[ticker]]

    _edit(change)


def set_main(ticker: str, main: bool) -> None:
    """Star (main, on the dashboard) or unstar a tracked stock."""
    ticker = ticker.strip().upper()

    def change(lines, rows, current):
        by_ticker = {e["ticker"]: e for e in current}
        if ticker not in by_ticker:
            raise WatchlistError(f"{ticker} isn't on your list.", 404)
        if main and not by_ticker[ticker]["main"] and sum(e["main"] for e in current) >= MAX_MAIN:
            raise WatchlistError(f"You already have {MAX_MAIN} main stocks. Unstar one first.", 409)
        lines[rows[ticker]] = _star(lines[rows[ticker]], main)

    _edit(change)


# ---------------------------------------------------------------------------
# Finding stocks with Yahoo Finance
# ---------------------------------------------------------------------------

def search_yahoo(query: str) -> list[dict]:
    """Yahoo Finance's own search (yfinance's Search). Tests and the test environment replace this."""
    if not hasattr(yf, "Search"):
        raise WatchlistError("Searching needs a newer yfinance: run pip install -U yfinance")
    return yf.Search(query, max_results=15, news_count=0, lists_count=0).quotes or []


def search(query: str, limit: int = 8) -> list[dict]:
    """US-listed stocks and ETFs matching a name or ticker, best match first."""
    query = " ".join(query.split())[:60]
    if not query:
        return []
    key = query.lower()
    cached = _search_cache.get(key)
    if cached and time.monotonic() - cached[0] < SEARCH_CACHE_SECONDS:
        quotes = cached[1]
    else:
        try:
            quotes = search_yahoo(query)
        except WatchlistError:
            raise
        except Exception as e:
            raise WatchlistError(f"Yahoo Finance search isn't answering right now ({e}). Try again shortly.") from None
        _search_cache[key] = (time.monotonic(), quotes)
        if len(_search_cache) > 200:  # keep the cache small
            _search_cache.pop(next(iter(_search_cache)))
    tracked = {e["ticker"] for e in entries()}
    results = []
    for q in quotes:
        symbol = str(q.get("symbol") or "").upper()
        kind = q.get("quoteType") or str(q.get("typeDisp") or "").upper()
        if kind not in ALLOWED_TYPES or not TICKER.fullmatch(symbol):  # a "." means a listing outside the US
            continue
        name = q.get("longname") or q.get("shortname") or symbol
        events._names.setdefault(symbol, events.short_name(name))  # remembered for the Stocks tab
        results.append({"ticker": symbol, "name": name, "type": ALLOWED_TYPES[kind],
                        "exchange": q.get("exchDisp") or q.get("exchange") or "", "tracked": symbol in tracked})
    return results[:limit]


def check_ticker(ticker: str) -> dict:
    """Confirm Yahoo Finance knows the ticker and it's a stock or ETF. Returns its name and type."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        raise WatchlistError(f"Couldn't check {ticker} with Yahoo Finance right now ({e}). Try again shortly.") from None
    kind = info.get("quoteType")
    name = info.get("longName") or info.get("shortName")
    if not kind or not name:
        raise WatchlistError(f"Yahoo Finance doesn't know {ticker}. Check the spelling, or search by company name.")
    if kind not in ALLOWED_TYPES:
        raise WatchlistError(f"{ticker} is a {kind.lower().replace('_', ' ')}. Only stocks and ETFs can be tracked.")
    events._names[ticker] = events.short_name(name)
    return {"ticker": ticker, "name": name, "type": ALLOWED_TYPES[kind]}
```

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

upcoming_events reads the events calendar (events.py) from the reports database, so
briefs can say what's coming up.

Every flagged move also comes with sector and market context: how the ticker did
against its sector ETF and the S&P 500, and whether that gap was unusual. That
tells the agent whether a move was about the company, its sector, or the market.

Test it on its own:  npx @modelcontextprotocol/inspector python market_tools.py
"""

from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer

import reports_db

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
    A * before the ticker marks a main stock for the dashboard (see watchlist.py); the
    agent tracks every ticker either way. Anything after a # is a comment."""
    entries = []
    for line in WATCHLIST_FILE.read_text().splitlines():
        words = line.split("#", 1)[0].replace("*", " ").upper().split()
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
        else:  # the price too, so the Stocks tab can show every tracked stock's price
            price = {k: m[k] for k in ("last_close", "last_price") if k in m}
            quiet.append({"ticker": ticker, **price, "return_1d_pct": m["return_1d_pct"]})

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


@mcp.tool()
def upcoming_events(ticker: str = "", days: int = 14) -> dict:
    """What's coming up, from the events calendar: earnings dates, ex-dividend dates and dated
    events found in the news, for the whole watchlist (or one ticker) over the next `days` days.
    `this_week` has ready-made lines for the next 7 days, for the brief's "Coming up" section.
    An event with `confirmed` false is an estimated date.
    """
    import events  # imported here, not at the top, because events.py imports this module
    today = now_et().date()
    days = max(1, min(int(days), 60))
    tickers = [ticker.strip().upper()] if ticker.strip() else load_watchlist()
    with closing(reports_db.connect(readonly=True)) as conn:
        found = events.upcoming(conn, today, days, tickers)
        scanned = events.last_scan(conn)
    rows = [{"date": e["event_date"], "days_away": (date.fromisoformat(e["event_date"]) - today).days,
             "ticker": e["ticker"], "company": e["company"], "kind": e["kind"], "title": e["title"],
             "confirmed": events.confirmed(e), "line": events.event_line(e)} for e in found]
    result = {"from": today.isoformat(), "to": (today + timedelta(days=days)).isoformat(),
              "calendar_updated": scanned["finished_at"] if scanned else None,
              "events": rows, "this_week": [r["line"] for r in rows if r["days_away"] <= 7]}
    if not scanned:
        result["note"] = "The events calendar hasn't been filled in yet, so upcoming events aren't known."
    return result


if __name__ == "__main__":
    mcp.run()  # speaks MCP over stdio; the agent starts this as a subprocess
```

### events.py

```python
"""Upcoming events calendar: earnings, ex-dividend dates, and dated events found in the news.

Once a day when the market opens (and whenever you press "Update now" in the app), scan():
1. reads each watchlist company's calendar from Yahoo Finance: earnings and ex-dividend dates,
2. reads each company's recent news headlines,
3. asks Claude to pick out upcoming events the news gives a specific date for (product
   launches, court rulings, regulatory decisions, shareholder votes...), citing the article,
4. checks every one of Claude's events in code (a watchlist ticker, a real article from
   step 2, a date in range), and saves them in the reports database for the Calendar tab.

Without an Anthropic key, or if Claude fails, the calendar dates from step 1 are still saved.

    python events.py scan                  scan now
    python events.py scan --only-if-open   scan only if the market is open (for the daily schedule)
    python events.py list                  upcoming events
    python events.py show 2026-11-12       one day's events, with their news links
    python events.py remove 42             delete one event (by the id that list and show print)
"""

import argparse
import asyncio
import json
import math
import re
import sys
from contextlib import closing, contextmanager
from datetime import date, datetime, timedelta, timezone

import yfinance as yf
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import market_tools
import reports_db

HORIZON_DAYS = 60        # how far ahead to look
NEWS_PER_TICKER = 10     # headlines read per company
MAX_EVENTS = 60          # most events accepted from one scan
MAX_TITLE, MAX_DETAILS = 80, 400
SCAN_BUDGET_USD = 0.25   # hard stop on Claude's cost per request
BATCH_TICKERS = 10       # companies per Claude request: a long watchlist becomes several small requests
STUCK_AFTER = timedelta(minutes=10)  # a "running" scan older than this is treated as crashed
KINDS = ("earnings", "dividend", "news")

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id          INTEGER PRIMARY KEY,
    event_date  TEXT NOT NULL,                -- YYYY-MM-DD
    ticker      TEXT NOT NULL,
    company     TEXT NOT NULL,                -- short display name, e.g. "Apple"
    kind        TEXT NOT NULL CHECK (kind IN ('earnings', 'dividend', 'news')),
    title       TEXT NOT NULL,
    details     TEXT NOT NULL DEFAULT '',
    date_note   TEXT,                         -- e.g. an estimated earnings window
    news_note   TEXT,                         -- what recent news says about a calendar event
    sources     TEXT NOT NULL DEFAULT '[]',   -- JSON list of {title, publisher, url, published}
    first_seen  TEXT NOT NULL,                -- UTC timestamps
    last_seen   TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events (event_date, ticker);

CREATE TABLE IF NOT EXISTS event_scans (
    id           INTEGER PRIMARY KEY,
    started_at   TEXT NOT NULL,
    finished_at  TEXT,
    trigger      TEXT NOT NULL,               -- scheduled, manual (the app) or command line
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'partial', 'failed')),
    tickers      INTEGER,
    articles     INTEGER,
    events_found INTEGER,
    dropped      INTEGER,
    cost_usd     REAL NOT NULL DEFAULT 0,
    message      TEXT
);
"""

SYSTEM_PROMPT = """You read recent news about a list of companies and pick out upcoming events that could move their share prices: product launches, court rulings, regulatory decisions, shareholder votes, investor days, conference presentations, deal deadlines and similar.

Rules:
- Only include an event if an article gives a specific future date for it, or one you can work out exactly from the article's published date ("next Tuesday"). If no specific day is given, leave it out.
- Only dates from TODAY to HORIZON_END (both given below).
- Every event must cite the numbered articles it comes from. Use nothing but these articles.
- Don't list earnings reports or dividend dates as new events: those come from a separate calendar. If an article adds something about one of them, attach it with same_as instead.
- title: short and plain, under 60 characters, e.g. "iPhone launch event" or "Court hearing on App Store case".
- details: one or two factual sentences from the articles. No predictions and no investment advice.
- If an event is already on the calendar (listed below), set same_as to its id. For a news event, also give its date (corrected, if the news says it moved).

Respond with only JSON, in this shape:
{"events": [{"ticker": "AAPL", "date": "2026-11-12", "title": "...", "details": "...", "sources": [3, 7], "same_as": null}]}
If there are none, respond {"events": []}."""

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],                 # it only reads the text it's given
    max_turns=1,
    max_budget_usd=SCAN_BUDGET_USD,
)


class ScanBusy(Exception):
    pass


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def today_et() -> date:
    return market_tools.now_et().date()


def connect():
    """The reports database, with the events tables added if they're missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


@contextmanager
def transaction(conn):
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


def _day(d: date) -> str:
    return f"{d:%b} {d.day}"  # "Nov 5" (written out, because %-d doesn't work on Windows)


# ---------------------------------------------------------------------------
# Company data from Yahoo Finance
# ---------------------------------------------------------------------------

_names: dict[str, str] = {}
SUFFIX = re.compile(r"[\s,]+(inc\.?|incorporated|corporation|corp\.?|company|co\.?|ltd\.?|limited|plc|"
                    r"n\.v\.|s\.a\.|ag|se|holdings?|group|&)$", re.I)


def short_name(name: str) -> str:
    """'JPMorgan Chase & Co.' -> 'JPMorgan Chase', 'NVIDIA Corporation' -> 'NVIDIA',
    'The Coca-Cola Company' -> 'Coca-Cola'."""
    name = " ".join((name or "").split())
    if name[:4].lower() == "the " and len(name) > 4:
        name = name[4:]
    while True:
        shorter = SUFFIX.sub("", name).strip(" ,")
        if shorter == name or not shorter:
            return name
        name = shorter


def company_name(ticker: str) -> str:
    """A short display name for the calendar, or the ticker if Yahoo doesn't have one."""
    if ticker not in _names:
        try:
            info = yf.Ticker(ticker).info or {}
            _names[ticker] = short_name(info.get("longName") or info.get("shortName") or "") or ticker
        except Exception:
            return ticker
    return _names[ticker]


def fetch_calendar(ticker: str):
    return yf.Ticker(ticker).calendar


def fetch_news(ticker: str) -> list[dict]:
    return market_tools.get_news(ticker, NEWS_PER_TICKER)


def _to_date(value) -> date | None:
    """A date from whatever Yahoo returns: date, datetime, pandas Timestamp, epoch seconds or text."""
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if hasattr(value, "date") and callable(value.date):  # pandas Timestamp
        try:
            return value.date()
        except Exception:
            return None
    if isinstance(value, (int, float)) and value > 0:
        return datetime.fromtimestamp(value, timezone.utc).date()
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return None


def _calendar_dict(cal) -> dict:
    """yfinance returns a dict; some older versions returned a small table instead."""
    if isinstance(cal, dict):
        return cal
    if hasattr(cal, "to_dict"):  # pandas DataFrame
        if "Earnings Date" in getattr(cal, "index", []):  # one row per field
            return {k: [v for v in row if v is not None and str(v) != "nan"] for k, row in cal.iterrows()}
        return {k: [v for v in values.values() if v is not None and str(v) != "nan"]
                for k, values in cal.to_dict().items()}
    return {}


def _dates(value) -> list[date]:
    values = value if isinstance(value, (list, tuple)) else [value]
    return sorted({d for d in (_to_date(v) for v in values) if d})


def _first(value):
    return value[0] if isinstance(value, (list, tuple)) and value else value


def _money(value) -> str | None:
    value = _first(value)
    return f"${value:,.2f}" if isinstance(value, (int, float)) and not math.isnan(value) else None


def calendar_events(ticker: str, company: str, cal, today: date, horizon_end: date) -> list[dict]:
    """Earnings and ex-dividend dates from a company's Yahoo Finance calendar."""
    cal = _calendar_dict(cal)
    quote_page = {"title": f"{company} on Yahoo Finance", "publisher": "Yahoo Finance",
                  "url": f"https://finance.yahoo.com/quote/{ticker}/", "published": None}
    found = []

    earnings = [d for d in _dates(cal.get("Earnings Date")) if d >= today]
    if earnings and earnings[0] <= horizon_end:
        estimate = len(earnings) > 1  # Yahoo gives a window when the exact day isn't confirmed
        details = []
        average, low, high = (_money(cal.get(k)) for k in ("Earnings Average", "Earnings Low", "Earnings High"))
        if average:
            details.append(f"Analysts' average estimate is {average} a share"
                           + (f" (range {low} to {high})." if low and high else "."))
        found.append({
            "ticker": ticker, "company": company, "kind": "earnings", "event_date": earnings[0].isoformat(),
            "title": "Earnings report (date not confirmed)" if estimate else "Earnings report",
            "details": " ".join(details),
            "date_note": (f"Estimated: Yahoo Finance shows a window of {_day(earnings[0])} to {_day(earnings[-1])}."
                          if estimate else None),
            "sources": [quote_page]})

    ex_dividend = _to_date(_first(cal.get("Ex-Dividend Date")))
    if ex_dividend and today <= ex_dividend <= horizon_end:
        paid = _to_date(_first(cal.get("Dividend Date")))
        details = "Shares bought on or after this date don't receive the next dividend."
        if paid and paid >= ex_dividend:
            details += f" It's paid on {_day(paid)}."
        found.append({"ticker": ticker, "company": company, "kind": "dividend", "event_date": ex_dividend.isoformat(),
                      "title": "Ex-dividend date", "details": details, "date_note": None, "sources": [quote_page]})
    return found


# ---------------------------------------------------------------------------
# Claude: reading the news for dated events
# ---------------------------------------------------------------------------

def build_prompt(articles: list[dict], known: list[dict], today: date, horizon_end: date) -> str:
    lines = [f"TODAY: {today.isoformat()} ({today:%A})", f"HORIZON_END: {horizon_end.isoformat()}", "",
             "Already on the calendar:"]
    lines += [f"- id {e['id']}: {e['ticker']} {e['kind']} on {e['event_date']}: {e['title']}" for e in known] or ["- (nothing yet)"]
    lines += ["", "Articles:"]
    for n, a in enumerate(articles, 1):
        lines += [f"[{n}] {a['ticker']} | {a.get('publisher') or 'unknown publisher'} | published {a.get('published') or 'unknown'}",
                  f"    {a.get('title') or ''}", f"    {(a.get('summary') or '').strip()}"]
    return "\n".join(lines)


async def _ask_claude_async(prompt: str) -> tuple[str, float]:
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't read the news: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(prompt))


def parse_reply(text: str) -> list:
    """The events list from Claude's reply, even if it's wrapped in a code fence or a sentence."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    events = data.get("events") if isinstance(data, dict) else None
    if not isinstance(events, list):
        raise ValueError('Claude\'s reply had no "events" list')
    return events


def validate(raw_events: list, articles: list[dict], companies: dict[str, str], known: dict[int, dict],
             today: date, horizon_end: date) -> tuple[list[dict], list[str]]:
    """Keep only events that pass every check. Returns (accepted, reasons for the rest)."""
    accepted, dropped, seen = [], [], set()
    for raw in raw_events[: MAX_EVENTS * 2]:
        if not isinstance(raw, dict):
            dropped.append("not an object")
            continue
        ticker = str(raw.get("ticker") or "").strip().upper()
        title = " ".join(str(raw.get("title") or "").split())
        label = f"{ticker or '?'} {title[:40]!r}"
        if ticker not in companies:
            dropped.append(f"{label}: not a watchlist ticker")
            continue
        refs = raw.get("sources")
        refs = [r for r in refs if isinstance(r, int) and 1 <= r <= len(articles)] if isinstance(refs, list) else []
        if not refs:
            dropped.append(f"{label}: no valid article cited")
            continue
        same_as = raw.get("same_as")
        target = known.get(same_as) if isinstance(same_as, int) else None
        if target and target["ticker"] != ticker:
            target = None
        if target and target["kind"] != "news":  # extra news for an earnings or dividend date: date stays as is
            event_date = date.fromisoformat(target["event_date"])
        else:
            try:
                event_date = date.fromisoformat(str(raw.get("date"))[:10])
            except ValueError:
                dropped.append(f"{label}: no valid date")
                continue
        if not today <= event_date <= horizon_end:
            dropped.append(f"{label}: date {event_date} is outside {today} to {horizon_end}")
            continue
        if not title and not target:
            dropped.append(f"{label}: no title")
            continue
        key = (ticker, event_date, (target or {}).get("id") or title.lower())
        if key in seen:
            continue
        seen.add(key)
        sources = [{k: articles[r - 1].get(k) for k in ("title", "publisher", "url", "published")}
                   for r in dict.fromkeys(refs)]
        accepted.append({
            "ticker": ticker, "company": companies[ticker], "kind": "news", "event_date": event_date.isoformat(),
            "title": title[:MAX_TITLE].rstrip() if title else target["title"],
            "details": " ".join(str(raw.get("details") or "").split())[:MAX_DETAILS],
            "sources": [s for s in sources if str(s.get("url") or "").startswith(("http://", "https://"))] or sources,
            "same_as": target["id"] if target else None,
        })
        if len(accepted) >= MAX_EVENTS:
            break
    return accepted, dropped


# ---------------------------------------------------------------------------
# Saving
# ---------------------------------------------------------------------------

def _merge_sources(old_json: str, new: list[dict]) -> str:
    merged = {s.get("url") or s.get("title"): s for s in json.loads(old_json or "[]")}
    for s in new:
        merged[s.get("url") or s.get("title")] = s
    return json.dumps(list(merged.values()))


def save_calendar(conn, ticker: str, found: list[dict], today: date) -> None:
    """Yahoo's calendar is the authority for earnings and dividend dates: upcoming ones it no
    longer lists (moved or cancelled) are removed. Past events are never changed."""
    now = _utc_now()
    keep = []
    for e in found:
        row = conn.execute("SELECT id, sources FROM events WHERE ticker = ? AND kind = ? AND event_date = ?",
                           (ticker, e["kind"], e["event_date"])).fetchone()
        if row:
            conn.execute("""UPDATE events SET company = ?, title = ?, details = ?, date_note = ?, sources = ?,
                            last_seen = ? WHERE id = ?""",
                         (e["company"], e["title"], e["details"], e["date_note"],
                          _merge_sources(row["sources"], e["sources"]), now, row["id"]))
            keep.append(row["id"])
        else:
            keep.append(conn.execute(
                """INSERT INTO events (event_date, ticker, company, kind, title, details, date_note, sources,
                   first_seen, last_seen) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (e["event_date"], ticker, e["company"], e["kind"], e["title"], e["details"], e["date_note"],
                 json.dumps(e["sources"]), now, now)).lastrowid)
    conn.execute(f"""DELETE FROM events WHERE ticker = ? AND kind IN ('earnings', 'dividend') AND event_date >= ?
                     AND id NOT IN ({','.join('?' * len(keep)) or 'NULL'})""", (ticker, today.isoformat(), *keep))


def save_news(conn, accepted: list[dict]) -> None:
    """News events build up over the days: an event stays on the calendar after the article
    about it drops out of the news feed. Matching events (same_as) are updated, not repeated."""
    now = _utc_now()
    for e in accepted:
        row = None
        if e["same_as"]:
            row = conn.execute("SELECT * FROM events WHERE id = ?", (e["same_as"],)).fetchone()
        if row is None:
            row = conn.execute("""SELECT * FROM events WHERE ticker = ? AND kind = 'news' AND event_date = ?
                                  AND lower(title) = lower(?)""", (e["ticker"], e["event_date"], e["title"])).fetchone()
        if row is None:
            conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, details, sources,
                            first_seen, last_seen) VALUES (?, ?, ?, 'news', ?, ?, ?, ?, ?)""",
                         (e["event_date"], e["ticker"], e["company"], e["title"], e["details"],
                          json.dumps(e["sources"]), now, now))
        elif row["kind"] == "news":
            conn.execute("""UPDATE events SET event_date = ?, title = ?, details = ?, sources = ?, last_seen = ?
                            WHERE id = ?""",
                         (e["event_date"], e["title"], e["details"] or row["details"],
                          _merge_sources(row["sources"], e["sources"]), now, row["id"]))
        else:  # news about an earnings or dividend date
            conn.execute("UPDATE events SET news_note = ?, sources = ?, last_seen = ? WHERE id = ?",
                         (e["details"] or row["news_note"], _merge_sources(row["sources"], e["sources"]), now, row["id"]))


# ---------------------------------------------------------------------------
# The scan
# ---------------------------------------------------------------------------

def _start_scan(conn, trigger: str) -> int:
    with transaction(conn):  # check and claim in one step, so two scans can't start together
        running = conn.execute("SELECT started_at FROM event_scans WHERE status = 'running' "
                               "ORDER BY id DESC LIMIT 1").fetchone()
        if running and _utc_now() < (datetime.fromisoformat(running[0].replace("Z", "+00:00"))
                                     + STUCK_AFTER).strftime("%Y-%m-%dT%H:%M:%SZ"):
            raise ScanBusy("An events scan is already running. Try again in a minute.")
        conn.execute("UPDATE event_scans SET status = 'failed', message = 'stopped unexpectedly' "
                     "WHERE status = 'running'")
        scan_id = conn.execute("INSERT INTO event_scans (started_at, trigger, status) VALUES (?, ?, 'running')",
                               (_utc_now(), trigger)).lastrowid
    return scan_id


def scan(trigger: str = "command line", emit=None) -> dict:
    """Update the calendar. Returns the finished scan's summary. Raises ScanBusy if one is running."""
    emit = emit or (lambda event: None)
    today = today_et()
    horizon_end = today + timedelta(days=HORIZON_DAYS)
    tickers = market_tools.load_watchlist()
    with closing(connect()) as conn:
        scan_id = _start_scan(conn, trigger)
        problems, cost, articles, accepted, dropped = [], 0.0, [], [], []
        try:
            companies = {}
            for ticker in tickers:
                emit({"type": "progress", "message": f"Checking {ticker}'s calendar and news"})
                companies[ticker] = company_name(ticker)
                try:
                    found = calendar_events(ticker, companies[ticker], fetch_calendar(ticker), today, horizon_end)
                    with transaction(conn):  # one ticker at a time
                        save_calendar(conn, ticker, found, today)
                except Exception as e:  # keep that ticker's saved dates; carry on with the rest
                    problems.append(f"{ticker} calendar: {e}")
                try:
                    articles += [{**a, "ticker": ticker} for a in fetch_news(ticker)]
                except Exception as e:
                    problems.append(f"{ticker} news: {e}")

            known_rows = [dict(r) for r in conn.execute(
                "SELECT id, ticker, kind, event_date, title FROM events WHERE event_date >= ? ORDER BY event_date",
                (today.isoformat(),))] if articles else []
            batches = [tickers[i:i + BATCH_TICKERS] for i in range(0, len(tickers), BATCH_TICKERS)]
            for n, batch in enumerate(batches, 1):
                batch_articles = [a for a in articles if a["ticker"] in batch]
                if not batch_articles:  # no headlines, no request (and no cost)
                    continue
                group = f" (group {n} of {len(batches)})" if len(batches) > 1 else ""
                emit({"type": "progress", "message": f"Reading {len(batch_articles)} headlines for dated events{group}"})
                try:
                    reply, batch_cost = ask_claude(build_prompt(
                        batch_articles, [r for r in known_rows if r["ticker"] in batch], today, horizon_end))
                    cost += batch_cost
                    found, left_out = validate(parse_reply(reply), batch_articles, companies,
                                               {r["id"]: r for r in known_rows}, today, horizon_end)
                    with transaction(conn):
                        save_news(conn, found)
                    accepted += found
                    dropped += left_out
                except Exception as e:  # one group failing doesn't lose the others
                    problems.append(f"news scan{group}: {e}")
            status = "partial" if problems else "ok"
            message = "; ".join(problems)[:1000] or None
        except Exception as e:
            status, message = "failed", str(e)[:1000] or type(e).__name__
        conn.execute("""UPDATE event_scans SET finished_at = ?, status = ?, tickers = ?, articles = ?,
                        events_found = ?, dropped = ?, cost_usd = ?, message = ? WHERE id = ?""",
                     (_utc_now(), status, len(tickers), len(articles), len(accepted), len(dropped),
                      round(cost, 4), message, scan_id))
        summary = last_scan(conn)
    summary["dropped_reasons"] = dropped
    emit({"type": "finished", "scan": summary})
    return summary


def add_calendar_dates(ticker: str) -> int:
    """A newly tracked company's earnings and dividend dates, straight away (Yahoo only: no Claude,
    no cost). Its news events follow with the next daily scan. Returns how many dates were found."""
    today = today_et()
    found = calendar_events(ticker, company_name(ticker), fetch_calendar(ticker), today,
                            today + timedelta(days=HORIZON_DAYS))
    with closing(connect()) as conn, transaction(conn):
        save_calendar(conn, ticker, found, today)
    return len(found)


# ---------------------------------------------------------------------------
# Reading (the API and the command line)
# ---------------------------------------------------------------------------

def _row(r) -> dict:
    event = dict(r)
    event["sources"] = json.loads(event["sources"] or "[]")
    return event


def events_between(conn, start: str, end: str) -> list[dict]:
    """Events from start to end (YYYY-MM-DD, inclusive), by date then company.
    Works on a read-only connection, even before the first scan."""
    try:
        rows = conn.execute("""SELECT * FROM events WHERE event_date BETWEEN ? AND ?
                               ORDER BY event_date, company, kind, title""", (start, end))
        return [_row(r) for r in rows]
    except Exception:  # no events table yet
        return []


def last_scan(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM event_scans ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:
        return None
    return dict(row) if row else None


def watchlist_tickers() -> list[str] | None:
    """The watchlist, or None (meaning every ticker) if it can't be read."""
    try:
        return market_tools.load_watchlist()
    except OSError:
        return None


def upcoming(conn, start: date, days: int, tickers=None) -> list[dict]:
    """Events from start to `days` days later (both included), for some tickers or all of them.
    Used by the brief's upcoming_events tool, the Discord alerts and Ask."""
    found = events_between(conn, start.isoformat(), (start + timedelta(days=days)).isoformat())
    return [e for e in found if tickers is None or e["ticker"] in tickers]


def confirmed(event: dict) -> bool:
    """False for an earnings date Yahoo only gives as an estimated window."""
    return not (event.get("date_note") or "").startswith("Estimated")


def event_line(event: dict, company: bool = True) -> str:
    """One event as a short line: 'Mon Nov 9: Microsoft (MSFT): Court hearing in patent case'."""
    d = date.fromisoformat(event["event_date"])
    who = f"{event['company']} ({event['ticker']}): " if company else ""
    return f"{d:%a} {_day(d)}: {who}{event['title']}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Upcoming events calendar.")
    commands = parser.add_subparsers(dest="command", required=True)
    run = commands.add_parser("scan", help="update the calendar now")
    run.add_argument("--only-if-open", action="store_true", help="skip unless the market is open (for the schedule)")
    commands.add_parser("list", help="upcoming events")
    show = commands.add_parser("show", help="one day's events")
    show.add_argument("date")
    remove = commands.add_parser("remove", help="delete one event, e.g. one the news got wrong")
    remove.add_argument("id", type=int)
    args = parser.parse_args()

    if args.command == "scan":
        if args.only_if_open and market_tools.market_session()["status"] != "in_progress":
            print("The market isn't open, so the scheduled events scan was skipped.")
            return
        try:
            result = scan("scheduled" if args.only_if_open else "command line",
                          emit=lambda e: print(e.get("message", "")) if e["type"] == "progress" else None)
        except ScanBusy as e:
            sys.exit(str(e))
        print(f"{result['status']}: {result['events_found']} news events from {result['articles']} headlines, "
              f"${result['cost_usd']:.3f}" + (f" ({result['message']})" if result["message"] else ""))
        for reason in result["dropped_reasons"]:
            print(f"  left out: {reason}")
    elif args.command == "remove":
        with closing(connect()) as conn:
            gone = conn.execute("DELETE FROM events WHERE id = ?", (args.id,)).rowcount
        print("Removed." if gone else f"No event with id {args.id}.")
    else:
        with closing(reports_db.connect(readonly=True)) as conn:
            if args.command == "list":
                start = today_et().isoformat()
                rows = events_between(conn, start, (today_et() + timedelta(days=HORIZON_DAYS)).isoformat())
            else:
                rows = events_between(conn, args.date, args.date)
        for e in rows:
            print(f"{e['id']:>5}  {e['event_date']}  {e['company']:<18} {e['kind']:<9} {e['title']}")
            if args.command == "show":
                for line in (e["date_note"], e["details"], e["news_note"]):
                    if line:
                        print(f"    {line}")
                for s in e["sources"]:
                    print(f"    - {s.get('publisher') or ''}: {s.get('title') or ''} {s.get('url') or ''}")
        if not rows:
            print("Nothing on the calendar." + (" Run: python events.py scan" if args.command == "list" else ""))


if __name__ == "__main__":
    main()
```

### run_brief.py

```python
"""Run the analyst agent once and save the report to the reports database.

Works at any time:
- Market open: writes an intraday update and saves it as today's report,
  replacing any earlier update from today.
- Market closed: writes the final report for the last session. Final reports
  are permanent; if it's already saved, this stops before calling Claude.

After saving, it sends any Discord alerts the report calls for (see alerts.py).

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_brief.py

The API's "Run update now" button calls run_once() from here too.
"""

import asyncio
import dataclasses
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

import alerts
import reports_db
import search_index
from market_tools import flag_events, load_watchlist, market_session, now_et

HERE = Path(__file__).parent
BASE_TURNS = 25  # enough for a small watchlist; turn_limit() adds room as the list grows

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
        "mcp__market__upcoming_events",
    ],
    max_turns=BASE_TURNS,    # each run uses turn_limit() instead (below)
    max_budget_usd=1.00,     # hard stop on cost per run
)


def turn_limit() -> int:
    """Turns for one run: room for a news check on every tracked stock, so a market-wide day
    (when most of the list can be flagged) still finishes. max_budget_usd still caps the cost."""
    try:
        return max(BASE_TURNS, len(load_watchlist()) + 10)
    except OSError:
        return BASE_TURNS


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


async def send_alerts(session_date: str, emit) -> None:
    """Discord alerts for the report just saved (or one whose alert failed before).
    Alerts never fail a run: problems are shown as warnings and retried next run."""
    try:
        outcome = await asyncio.to_thread(alerts.notify, session_date)
    except Exception as e:
        emit({"type": "warning", "message": f"Alerts couldn't be checked ({e}). The next run will try again."})
        return
    for label in outcome["sent"]:
        emit({"type": "alert", "message": f"Discord: sent {label}"})
    for label in outcome["failed"]:
        emit({"type": "warning", "message": f"Discord alert failed: {label}. The next run will try again."})


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
                await send_alerts(session_date, emit)  # retries a summary that failed to send earlier
                return event
        prompt = (f"It is {now:%Y-%m-%d %H:%M} ET and the market is closed. "
                  f"Write the watchlist brief for the {session_date} session.")
    else:
        prompt = f"It is {now:%Y-%m-%d %H:%M} ET and the market is open. Write an intraday update."
    emit({"type": "started", "session_date": session_date, "status": status})

    calls = {}  # tool_use_id -> (tool name, arguments)
    scan, sources, result = None, [], None
    async for message in query(prompt=prompt, options=dataclasses.replace(options, max_turns=turn_limit())):
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

    await send_alerts(session_date, emit)
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

### api.py

```python
"""JSON API for the frontend: reports, live updates, on-demand runs and questions.

Run:
    uvicorn api:app --port 8000

Endpoints:
    GET  /api/health
    GET  /api/reports?limit=30&before=YYYY-MM-DD&status=final|intraday
    GET  /api/reports/latest
    GET  /api/reports/{YYYY-MM-DD}
    GET  /api/tickers/{TICKER}/history?limit=30
    GET  /api/tickers/{TICKER}/prices?range=1mo|3mo|6mo|1y   daily prices for charts
    GET  /api/search?q=...&limit=12&ticker=&since=&until=     search passages in all reports
    GET  /api/search/status     what the search index contains
    GET  /api/alerts?limit=10   Discord alerts: whether they're on here, and the latest ones
    GET  /api/calendar?start=YYYY-MM-DD&end=YYYY-MM-DD   upcoming events (and past ones) between two dates
    POST /api/calendar/scan     update the events calendar now
    GET  /api/calendar/scan     the calendar update in progress, or the last one
    GET  /api/watchlist         tracked stocks, main ones first, with latest figures and next event
    GET  /api/stocks/search?q=  find US stocks and ETFs by name or ticker (Yahoo Finance)
    POST /api/watchlist                   track a stock: {"ticker": "COST", "main": false}
    POST /api/watchlist/{TICKER}          star or unstar it: {"main": true}
    POST /api/watchlist/{TICKER}/remove   stop tracking it
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules
(a run also logs the Discord alerts it sends). The events calendar is written the same
way, by events.py's scan (daily at the market open, or "Update now"). The Stocks tab edits
watchlist.txt, through watchlist.py's safe edits.
The API does write the search index (search.db), which is rebuilt from reports.db.
If frontend/dist exists (after `npm run build`), the app is served at /.
"""

import asyncio
import json
import logging
import os
import re
import threading
import time
from contextlib import asynccontextmanager, closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import alerts
import ask
import events as upcoming  # events.py ("events" here is the live-updates endpoint)
import market_tools
import prices
import reports_db
import run_brief
import search_index
import watchlist

log = logging.getLogger("uvicorn.error")

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "300"))  # between on-demand runs
CALENDAR_SCAN_COOLDOWN_SECONDS = int(os.environ.get("CALENDAR_SCAN_COOLDOWN_SECONDS", "300"))
MAX_CALENDAR_DAYS = 100                                                   # longest date range one request returns
POLL_SECONDS = float(os.environ.get("REPORT_POLL_SECONDS", "2"))          # how often to check for new reports
MAX_ACTIVE_QUESTIONS = 2
FRONTEND_DIST = Path(__file__).parent / "frontend" / "dist"


class BadRequest(ValueError):
    pass


def _error(status_code: int, message: str) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status_code)


def _limit(request, default: int = 30, maximum: int = 365) -> int:
    raw = request.query_params.get("limit", str(default))
    if not raw.isdigit() or not 1 <= int(raw) <= maximum:
        raise BadRequest(f"limit must be a whole number from 1 to {maximum}")
    return int(raw)


def _db():
    return closing(reports_db.connect(readonly=True))  # reading never writes


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ---------------------------------------------------------------------------
# Reports (read-only)
# ---------------------------------------------------------------------------

def health(request):
    with _db() as conn:
        count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
    return JSONResponse({"status": "ok", "reports": count})


def list_reports(request):
    try:
        limit = _limit(request)
        before = request.query_params.get("before")
        status = request.query_params.get("status")
        if before and not DATE.fullmatch(before):
            raise BadRequest("before must be a date like 2026-11-06")
        if status and status not in ("intraday", "final"):
            raise BadRequest("status must be 'intraday' or 'final'")
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        return JSONResponse({"reports": reports_db.list_reports(conn, limit, before, status)})


def latest_report(request):
    with _db() as conn:
        report = reports_db.latest_report(conn)
    return JSONResponse(report) if report else _error(404, "no reports yet")


def get_report(request):
    day = request.path_params["session_date"]
    if not DATE.fullmatch(day):
        return _error(400, "use a date like 2026-11-06, or 'latest'")
    with _db() as conn:
        report = reports_db.get_report(conn, day)
    return JSONResponse(report) if report else _error(404, f"no report for {day}")


def ticker_history(request):
    ticker = request.path_params["ticker"]
    if not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    try:
        limit = _limit(request)
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        history = reports_db.ticker_history(conn, ticker, limit)
    return JSONResponse({"ticker": ticker.upper(), "history": history})


def ticker_prices(request):
    """Daily closing prices for a chart. Runs in a worker thread, so a slow download
    doesn't hold up anything else."""
    ticker = request.path_params["ticker"]
    period = request.query_params.get("range", "3mo")
    if not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    if period not in prices.RANGES:
        return _error(400, f"range must be one of: {', '.join(prices.RANGES)}")
    try:
        rows = prices.get_prices(ticker.upper(), period)
    except Exception as e:  # network problem, rate limit, unknown ticker...
        return _error(502, f"couldn't load prices for {ticker.upper()} ({e})")
    if not rows:
        return _error(404, f"no price data for {ticker.upper()}")
    return JSONResponse({"ticker": ticker.upper(), "range": period, "prices": rows})


# ---------------------------------------------------------------------------
# Search (the retrieval part of RAG). The index lives in search.db, never in reports.db.
# ---------------------------------------------------------------------------

_index_lock = threading.Lock()  # one background embedding job at a time
_background = set()  # keeps background tasks alive until they finish


def _update_index_quietly() -> None:
    """Index and embed new reports. Problems are logged, never fatal."""
    with _index_lock:
        try:
            search_index.sync()
        except Exception as e:
            log.warning("Search index update failed (it will retry on the next report): %s", e)


def update_index_in_background() -> None:
    task = asyncio.create_task(asyncio.to_thread(_update_index_quietly))
    _background.add(task)
    task.add_done_callback(_background.discard)


def search_reports(request):
    q = request.query_params.get("q", "").strip()
    ticker = request.query_params.get("ticker")
    since, until = request.query_params.get("since"), request.query_params.get("until")
    try:
        limit = _limit(request, default=12, maximum=50)
        if not q:
            raise BadRequest("q is required")
        if len(q) > ask.MAX_QUESTION_CHARS:
            raise BadRequest(f"keep searches under {ask.MAX_QUESTION_CHARS} characters")
        if ticker and not TICKER.fullmatch(ticker):
            raise BadRequest("invalid ticker")
        for name, value in (("since", since), ("until", until)):
            if value and not DATE.fullmatch(value):
                raise BadRequest(f"{name} must be a date like 2026-11-06")
    except BadRequest as e:
        return _error(400, str(e))
    search_index.sync(embed_now=False)  # the newest reports are searchable by keyword straight away
    return JSONResponse(search_index.search(q, limit, ticker, since, until))


def search_status(request):
    return JSONResponse(search_index.status())


def alerts_status(request):
    """Whether runs started from this server send Discord alerts, and the latest alerts
    sent by any run (scheduled runs included)."""
    try:
        limit = _limit(request, default=10, maximum=100)
    except BadRequest as e:
        return _error(400, str(e))
    with _db() as conn:
        latest = alerts.recent(conn, limit)
    return JSONResponse({"enabled": alerts.enabled(), "alerts": latest})


def calendar(request):
    """Events between start and end. Without dates: this month's calendar (6 weeks from its first day)."""
    today = upcoming.today_et()
    start, end = request.query_params.get("start"), request.query_params.get("end")
    try:
        for name, value in (("start", start), ("end", end)):
            if value and not DATE.fullmatch(value):
                raise BadRequest(f"{name} must be a date like 2026-11-06")
        first = date.fromisoformat(start) if start else today.replace(day=1)
        last = date.fromisoformat(end) if end else first + timedelta(days=41)
        if last < first:
            raise BadRequest("end must be on or after start")
        if (last - first).days > MAX_CALENDAR_DAYS:
            raise BadRequest(f"ask for at most {MAX_CALENDAR_DAYS} days at a time")
    except BadRequest as e:
        return _error(400, str(e))
    except ValueError:
        return _error(400, "that isn't a real date")
    with _db() as conn:
        found = upcoming.events_between(conn, first.isoformat(), last.isoformat())
        scanned = upcoming.last_scan(conn)
    return JSONResponse({"today": today.isoformat(), "start": first.isoformat(), "end": last.isoformat(),
                         "events": found, "last_scan": scanned, "scan": calendar_scans.snapshot()})


# ---------------------------------------------------------------------------
# Tracked stocks (the Stocks tab, and the main ones on the Today tab)
# ---------------------------------------------------------------------------

_names_requested: set[str] = set()  # company names being looked up, so each is only asked for once


def _watchlist_view() -> dict:
    """Every tracked stock, main ones first, with its latest figures and next calendar event."""
    tracked = watchlist.entries()
    tickers = [e["ticker"] for e in tracked]
    with _db() as conn:
        latest = reports_db.latest_report(conn)
        rows = {t["ticker"]: {**t, "session_date": latest["session_date"], "status": latest["status"]}
                for t in (latest or {}).get("tickers", [])}
        for t in tickers:
            if t not in rows:  # not in the latest report (e.g. just added): its most recent figures, if any
                history = reports_db.ticker_history(conn, t, limit=1)
                if history:
                    rows[t] = history[0]
        next_event = {}
        for e in upcoming.upcoming(conn, upcoming.today_et(), upcoming.HORIZON_DAYS, tickers):
            next_event.setdefault(e["ticker"], {"event_date": e["event_date"], "kind": e["kind"], "title": e["title"],
                                                "line": upcoming.event_line(e, company=False)})
        try:
            calendar_names = dict(conn.execute("SELECT ticker, company FROM events GROUP BY ticker"))
        except Exception:  # no calendar yet
            calendar_names = {}
    stocks = []
    for e in sorted(tracked, key=lambda e: not e["main"]):  # main first, each group in list order
        row = rows.get(e["ticker"])
        stocks.append({
            "ticker": e["ticker"], "main": e["main"], "benchmark": e["benchmark"],
            "name": upcoming._names.get(e["ticker"]) or calendar_names.get(e["ticker"]),
            "latest": None if row is None else {k: row.get(k) for k in (
                "session_date", "status", "category", "price", "return_1d_pct", "return_zscore", "move_read")},
            "next_event": next_event.get(e["ticker"]),
        })
    return {"stocks": stocks, "tracked_count": len(stocks), "main_count": sum(s["main"] for s in stocks),
            "max_tracked": watchlist.MAX_TRACKED, "max_main": watchlist.MAX_MAIN}


def _in_background(coroutine) -> None:
    task = asyncio.create_task(coroutine)
    _background.add(task)
    task.add_done_callback(_background.discard)


async def _fill_names(tickers: list[str]) -> None:
    """Look up company names Yahoo hasn't given us yet, then tell open pages to refresh."""
    def look_up():
        for t in tickers:
            try:
                upcoming._names[t] = upcoming.company_name(t)
            except Exception:
                pass
    await asyncio.to_thread(look_up)
    hub.publish({"type": "watchlist_changed"})


async def _calendar_for_new_stock(ticker: str) -> None:
    """A new stock's earnings and dividend dates (Yahoo only, no cost), so its next event shows straight away."""
    try:
        await asyncio.to_thread(upcoming.add_calendar_dates, ticker)
        hub.publish({"type": "calendar_updated", "scan": None})
    except Exception as e:
        log.warning("Couldn't add %s's calendar dates (the next daily scan will): %s", ticker, e)


async def watchlist_view(request):
    try:
        view = await asyncio.to_thread(_watchlist_view)
    except FileNotFoundError:
        return _error(404, "watchlist.txt is missing: create it with one ticker per line")
    missing = [s["ticker"] for s in view["stocks"] if not s["name"] and s["ticker"] not in _names_requested]
    if missing:
        _names_requested.update(missing)
        _in_background(_fill_names(missing))
    return JSONResponse(view)


def search_stocks(request):
    q = request.query_params.get("q", "").strip()
    if not q:
        return _error(400, "q is required")
    if len(q) > 60:
        return _error(400, "keep searches under 60 characters")
    try:
        return JSONResponse({"query": q, "results": watchlist.search(q)})
    except watchlist.WatchlistError as e:
        return _error(502, str(e))


async def _watchlist_change(request, action):
    """Shared by add, star and remove: checks, the change itself, then live updates."""
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, "send JSON")
    if not isinstance(body, dict):
        return _error(400, "send a JSON object")
    try:
        result = await asyncio.to_thread(action, body)
    except watchlist.WatchlistError as e:
        return _error(e.status, str(e))
    hub.publish({"type": "watchlist_changed"})
    return result


async def add_stock(request):
    async def respond(info):
        _in_background(_calendar_for_new_stock(info["ticker"]))
        return JSONResponse({"stock": info, "watchlist": await asyncio.to_thread(_watchlist_view)}, status_code=201)

    def action(body):
        ticker = body.get("ticker")
        if not isinstance(ticker, str):
            raise watchlist.WatchlistError('send {"ticker": "COST"}')
        return watchlist.add(ticker, main=bool(body.get("main")))

    result = await _watchlist_change(request, action)
    return await respond(result) if isinstance(result, dict) else result


async def star_stock(request):
    def action(body):
        if not isinstance(body.get("main"), bool):
            raise watchlist.WatchlistError('send {"main": true} or {"main": false}')
        watchlist.set_main(request.path_params["ticker"], body["main"])
        return _watchlist_view()

    result = await _watchlist_change(request, action)
    return JSONResponse(result) if isinstance(result, dict) else result


async def remove_stock(request):
    def action(body):
        watchlist.remove(request.path_params["ticker"])
        return _watchlist_view()

    result = await _watchlist_change(request, action)
    return JSONResponse(result) if isinstance(result, dict) else result


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------

class EventHub:
    """Sends each event to every open browser connection."""

    def __init__(self):
        self.subscribers: set[asyncio.Queue] = set()

    def subscribe(self) -> asyncio.Queue:
        queue = asyncio.Queue(maxsize=200)
        self.subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self.subscribers.discard(queue)

    def publish(self, event: dict) -> None:
        for queue in list(self.subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:  # a stalled browser shouldn't block everyone else
                pass


hub = EventHub()


def _latest_calendar_scan() -> dict | None:
    """The most recent events scan, from any program (the daily schedule included)."""
    with _db() as conn:
        scanned = upcoming.last_scan(conn)
    return {k: scanned[k] for k in ("id", "status", "finished_at")} if scanned else None


def _latest_change() -> dict | None:
    """The most recently saved report: changes whenever any run saves (scheduled or on demand)."""
    with _db() as conn:
        row = conn.execute("""SELECT session_date, status, revision, updated_at FROM reports
                              ORDER BY updated_at DESC, session_date DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


async def watch_reports() -> None:
    """Checks the database every few seconds and announces new or updated reports."""
    def watchlist_stamp():
        try:
            return market_tools.WATCHLIST_FILE.stat().st_mtime_ns
        except OSError:
            return None

    def check():  # all in one trip to a worker thread
        return _latest_change(), _latest_calendar_scan(), watchlist_stamp()

    last, last_scan, last_stamp = await asyncio.to_thread(check)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current, scan, stamp = await asyncio.to_thread(check)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if stamp != last_stamp:  # watchlist.txt changed, by the app or by hand
            last_stamp = stamp
            hub.publish({"type": "watchlist_changed"})
        if current and current != last:
            last = current
            hub.publish({"type": "report_saved", **current})
            update_index_in_background()  # covers scheduled runs, which are separate programs
        if scan and scan != last_scan:
            last_scan = scan
            if scan["finished_at"]:  # a calendar update finished (scheduled or "Update now")
                hub.publish({"type": "calendar_updated", "scan": scan})


async def events(request):
    """Server-Sent Events stream. The browser's EventSource reconnects on its own."""
    queue = hub.subscribe()
    hello = {"type": "hello", "run": runs.snapshot(), "latest": await asyncio.to_thread(_latest_change),
             "calendar_scan": calendar_scans.snapshot()}

    async def stream():
        try:
            yield f"retry: 3000\ndata: {json.dumps(hello)}\n\n"
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15)
                except asyncio.TimeoutError:
                    yield ": keep-alive\n\n"  # stops idle connections being dropped
                    continue
                yield f"data: {json.dumps(event)}\n\n"
        finally:
            hub.unsubscribe(queue)

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
# Requests from the frontend: run now, ask a question
# ---------------------------------------------------------------------------

def _post_guard(request):
    """Stops other websites from triggering runs or questions through your browser."""
    origin = request.headers.get("origin")
    if origin and origin not in FRONTEND_ORIGINS and origin != f"{request.url.scheme}://{request.url.netloc}":
        return _error(403, "requests from this website aren't allowed")
    if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
        return _error(415, "send JSON (Content-Type: application/json)")
    return None


class AlreadyRunning(Exception):
    pass


class TooSoon(Exception):
    pass


class RunManager:
    """One on-demand run at a time, with a cooldown between runs to cap cost."""

    def __init__(self):
        self.task = None
        self.last_started = None
        self.state = {"state": "idle", "started_at": None, "finished_at": None,
                      "log": [], "result": None, "error": None}

    def snapshot(self) -> dict:
        return {**self.state, "log": list(self.state["log"])}

    def start(self) -> dict:
        if self.task and not self.task.done():
            raise AlreadyRunning("A report is already being written. Its progress is shown below.")
        if self.last_started is not None:
            wait = RUN_COOLDOWN_SECONDS - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(f"Please wait {seconds} second{'s' if seconds != 1 else ''} "
                              "before requesting another report.")
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None,
                      "log": [], "result": None, "error": None}
        hub.publish({"type": "run_started", "run": self.snapshot()})
        self.task = asyncio.create_task(self._run())
        return self.snapshot()

    def _emit(self, event: dict) -> None:
        self.state["log"].append(event)
        hub.publish({"type": "run_event", "event": event})

    async def _run(self) -> None:
        try:
            self.state["result"] = await run_brief.run_once(self._emit)
            self.state["state"] = "finished"
        except Exception as e:
            self.state.update(state="failed", error=str(e) or type(e).__name__)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": "run_finished", "run": self.snapshot()})


runs = RunManager()


class CalendarScanManager:
    """One "Update now" calendar scan at a time, with a cooldown to cap Claude's cost."""

    def __init__(self):
        self.task = None
        self.last_started = None
        self.state = {"state": "idle", "started_at": None, "finished_at": None, "message": None,
                      "result": None, "error": None}

    def snapshot(self) -> dict:
        return dict(self.state)

    def start(self) -> dict:
        if self.task and not self.task.done():
            raise AlreadyRunning("The calendar is already being updated.")
        if self.last_started is not None:
            wait = CALENDAR_SCAN_COOLDOWN_SECONDS - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(f"The calendar was just updated. Try again in {seconds} second{'s' if seconds != 1 else ''}.")
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None,
                      "message": "Starting…", "result": None, "error": None}
        hub.publish({"type": "calendar_scan", "scan": self.snapshot()})
        self.task = asyncio.create_task(self._run())
        return self.snapshot()

    def _progress(self, event: dict) -> None:
        if event["type"] == "progress":
            self.state["message"] = event["message"]
            hub.publish({"type": "calendar_scan", "scan": self.snapshot()})

    async def _run(self) -> None:
        loop = asyncio.get_running_loop()
        emit = lambda event: loop.call_soon_threadsafe(self._progress, event)  # noqa: E731  (scan runs in a thread)
        try:
            result = await asyncio.to_thread(upcoming.scan, "manual", emit)
            result.pop("dropped_reasons", None)
            self.state.update(state="finished", result=result, message=None)
        except Exception as e:  # including ScanBusy: the daily scan is running right now
            self.state.update(state="failed", error=str(e) or type(e).__name__, message=None)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": "calendar_scan", "scan": self.snapshot()})


calendar_scans = CalendarScanManager()


async def start_run(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        run = runs.start()
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"run": run}, status_code=202)


def current_run(request):
    return JSONResponse({"run": runs.snapshot()})


async def start_calendar_scan(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        scan = calendar_scans.start()
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"scan": scan}, status_code=202)


def current_calendar_scan(request):
    return JSONResponse({"scan": calendar_scans.snapshot()})


active_questions = 0


async def ask_question(request):
    """Streams the answer as newline-delimited JSON: delta events, then done (or error)."""
    global active_questions
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"question": "..."}')
    question = body.get("question") if isinstance(body, dict) else None
    if not isinstance(question, str) or not question.strip():
        return _error(400, "question is required")
    if len(question) > ask.MAX_QUESTION_CHARS:
        return _error(400, f"keep questions under {ask.MAX_QUESTION_CHARS} characters")
    if active_questions >= MAX_ACTIVE_QUESTIONS:
        return _error(429, "Another question is being answered. Try again in a moment.")

    queue: asyncio.Queue = asyncio.Queue()

    async def work():
        try:
            await ask.answer(question, queue.put_nowait)
        except Exception as e:
            queue.put_nowait({"type": "error", "error": str(e) or type(e).__name__})

    async def stream():
        global active_questions
        active_questions += 1
        task = asyncio.create_task(work())
        try:
            while True:
                event = await queue.get()
                yield json.dumps(event) + "\n"
                if event["type"] in ("done", "error"):
                    break
        finally:
            active_questions -= 1
            task.cancel()

    return StreamingResponse(stream(), media_type="application/x-ndjson", headers={"Cache-Control": "no-cache"})


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app):
    watcher = asyncio.create_task(watch_reports())
    update_index_in_background()  # catch up on anything saved while the API was off
    yield
    watcher.cancel()


def create_app(frontend_dist: Path = FRONTEND_DIST) -> Starlette:
    routes = [
        Route("/api/health", health),
        Route("/api/reports", list_reports),
        Route("/api/reports/latest", latest_report),  # must come before the {session_date} route
        Route("/api/reports/{session_date}", get_report),
        Route("/api/tickers/{ticker}/history", ticker_history),
        Route("/api/tickers/{ticker}/prices", ticker_prices),
        Route("/api/search", search_reports),
        Route("/api/search/status", search_status),
        Route("/api/alerts", alerts_status),
        Route("/api/calendar", calendar),
        Route("/api/calendar/scan", start_calendar_scan, methods=["POST"]),
        Route("/api/calendar/scan", current_calendar_scan, methods=["GET"]),
        Route("/api/watchlist", watchlist_view, methods=["GET"]),
        Route("/api/watchlist", add_stock, methods=["POST"]),
        Route("/api/watchlist/{ticker}", star_stock, methods=["POST"]),
        Route("/api/watchlist/{ticker}/remove", remove_stock, methods=["POST"]),
        Route("/api/stocks/search", search_stocks),
        Route("/api/events", events),
        Route("/api/runs", start_run, methods=["POST"]),
        Route("/api/runs/current", current_run),
        Route("/api/ask", ask_question, methods=["POST"]),
    ]
    if frontend_dist.is_dir():  # serve the built frontend (npm run build) at /
        routes.append(Mount("/", app=StaticFiles(directory=frontend_dist, html=True), name="frontend"))
    return Starlette(
        routes=routes,
        middleware=[Middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS,
                               allow_methods=["GET", "POST"], allow_headers=["Content-Type"])],
        lifespan=lifespan,
    )


app = create_app()
```

### frontend/src/components/StocksTab.jsx

```jsx
import { useEffect, useRef, useState } from 'react'
import { addStock, removeStock, searchStocks, setMainStock } from '../api'
import { useOpenChart } from '../chartContext'
import { number, percent } from '../format'
import { routes } from '../useRoute'

const SEARCH_DELAY_MS = 350 // wait for a pause in typing before searching

function Star({ on }) {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" aria-hidden="true">
      <path
        d="M12 3.5l2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"
        fill={on ? 'currentColor' : 'none'}
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinejoin="round"
      />
    </svg>
  )
}

// Find US stocks and ETFs by name or ticker, and add them
function FindStocks({ list, onChange }) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState(null)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState(null) // {text, error}
  const latest = useRef('')

  useEffect(() => {
    const q = query.trim()
    latest.current = q
    setMessage(null)
    if (!q) {
      setResults(null)
      return
    }
    const timer = setTimeout(() => {
      setBusy(true)
      searchStocks(q)
        .then((found) => latest.current === q && setResults(found))
        .catch((e) => latest.current === q && setMessage({ text: e.message, error: true }))
        .finally(() => setBusy(false))
    }, SEARCH_DELAY_MS)
    return () => clearTimeout(timer)
  }, [query])

  const add = async (stock, main) => {
    setMessage(null)
    try {
      const body = await addStock(stock.ticker, main)
      onChange(body.watchlist)
      setResults((current) => current?.map((r) => (r.ticker === stock.ticker ? { ...r, tracked: true } : r)))
      setMessage({ text: `Added ${stock.ticker}${main ? ' as a main stock' : ''}. Its first figures come with the next report.` })
    } catch (e) {
      setMessage({ text: e.message, error: true })
    }
  }

  const full = list && list.tracked_count >= list.max_tracked
  const mainFull = list && list.main_count >= list.max_main

  return (
    <section className="panel stocks-find" aria-label="Find stocks">
      <div className="section-head">
        <h2>Find stocks</h2>
        {list && (
          <span className="muted small">
            {list.tracked_count} of {list.max_tracked} tracked · {list.main_count} of {list.max_main} main
          </span>
        )}
      </div>
      <form role="search" onSubmit={(e) => e.preventDefault()}>
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Company name or ticker, e.g. Costco or COST"
          aria-label="Find a stock"
          maxLength={60}
        />
      </form>
      <p className="muted small">US-listed stocks and ETFs, from Yahoo Finance.</p>
      {message && <p className={message.error ? 'error' : 'notice'} role="status">{message.text}</p>}
      {busy && <p className="muted small">Searching…</p>}
      {results && !busy && results.length === 0 && <p className="muted small">No US stocks or ETFs match that.</p>}
      {results?.length > 0 && (
        <ul className="search-hits" aria-label="Matches">
          {results.map((r) => (
            <li key={r.ticker}>
              <div className="hit-name">
                <strong>{r.ticker}</strong> {r.name}
                <span className="muted small">
                  {' '}
                  · {r.type}
                  {r.exchange && ` · ${r.exchange}`}
                </span>
              </div>
              {r.tracked ? (
                <span className="muted small">Tracking</span>
              ) : (
                <div className="hit-actions">
                  <button type="button" className="chip" onClick={() => add(r, false)} disabled={full}>
                    Track
                  </button>
                  <button type="button" className="chip" onClick={() => add(r, true)} disabled={full || mainFull}>
                    Track as main
                  </button>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
      {full && <p className="muted small">You're tracking the most stocks allowed. Remove one to add another.</p>}
    </section>
  )
}

function StockRow({ stock, list, onChange, setMessage }) {
  const openChart = useOpenChart()
  const [confirming, setConfirming] = useState(false)
  const latest = stock.latest
  const run = async (action) => {
    setMessage(null)
    try {
      onChange(await action())
    } catch (e) {
      setMessage({ text: e.message, error: true })
    }
  }
  const starBlocked = !stock.main && list.main_count >= list.max_main

  return (
    <tr className={latest?.category === 'flagged' ? 'flagged' : undefined}>
      <td>
        <button
          type="button"
          className={`star ${stock.main ? 'on' : ''}`}
          aria-pressed={stock.main}
          aria-label={`Main stock: ${stock.ticker}`}
          title={stock.main ? 'Main: on the dashboard. Click to unstar.' : starBlocked ? `Up to ${list.max_main} main stocks` : 'Make it a main stock'}
          disabled={starBlocked}
          onClick={() => run(() => setMainStock(stock.ticker, !stock.main))}
        >
          <Star on={stock.main} />
        </button>
      </td>
      <td className="ticker">
        <button
          type="button"
          className="ticker-button"
          onClick={(e) => openChart(stock.ticker, e.currentTarget)}
          aria-label={`Show ${stock.ticker} chart`}
          title="Show chart"
        >
          {stock.ticker}
        </button>
      </td>
      <td className="stock-name">{stock.name || '…'}</td>
      <td className="num">{latest ? number(latest.price, 2) : '—'}</td>
      <td className={`num ${latest?.return_1d_pct > 0 ? 'up' : latest?.return_1d_pct < 0 ? 'down' : ''}`}>
        {latest ? percent(latest.return_1d_pct) : '—'}
      </td>
      <td>
        {latest ? (
          <span title={`From the ${latest.status} report of ${latest.session_date}`}>
            {latest.category === 'error' ? 'data issue' : latest.category}
          </span>
        ) : (
          <span className="muted">first report next run</span>
        )}
      </td>
      <td className="next-event">
        {stock.next_event ? (
          <a href={routes.calendar(stock.next_event.event_date)}>{stock.next_event.line}</a>
        ) : (
          <span className="muted">—</span>
        )}
      </td>
      <td className="row-actions">
        {confirming ? (
          <>
            <button type="button" className="link danger" onClick={() => run(() => removeStock(stock.ticker))}>
              Remove {stock.ticker}
            </button>
            <button type="button" className="link" onClick={() => setConfirming(false)}>
              Keep
            </button>
          </>
        ) : (
          <button type="button" className="link" onClick={() => setConfirming(true)} aria-label={`Remove ${stock.ticker}`}>
            Remove
          </button>
        )}
      </td>
    </tr>
  )
}

// Every tracked stock: star the main ones (shown on the Today tab), open charts, remove stocks
function TrackedStocks({ list, onChange }) {
  const [message, setMessage] = useState(null)
  if (!list) return null
  const main = list.stocks.filter((s) => s.main)
  const others = list.stocks.filter((s) => !s.main)
  const group = (label, stocks) => (
    <>
      <tr className="group-row">
        <th colSpan={8} scope="rowgroup">
          {label}
        </th>
      </tr>
      {stocks.map((s) => (
        <StockRow key={s.ticker} stock={s} list={list} onChange={onChange} setMessage={setMessage} />
      ))}
    </>
  )

  return (
    <section className="panel" aria-label="Tracked stocks">
      <div className="section-head">
        <h2>Tracked stocks</h2>
        <span className="muted small">Every tracked stock is in each report, alert and calendar update</span>
      </div>
      {message && <p className={message.error ? 'error' : 'notice'} role="status">{message.text}</p>}
      {list.stocks.length === 0 ? (
        <p className="muted">You're not tracking any stocks yet. Find one above.</p>
      ) : (
        <div className="table-wrap">
          <table className="tickers stocks">
            <thead>
              <tr>
                <th>
                  <span className="sr-only">Main</span>
                </th>
                <th>Ticker</th>
                <th>Company</th>
                <th className="num">Price</th>
                <th className="num">Change</th>
                <th>Status</th>
                <th>Next event</th>
                <th>
                  <span className="sr-only">Actions</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {group(`Main: on the Today tab (${main.length} of ${list.max_main})`, main)}
              {others.length > 0 && group(`Also tracked (${others.length})`, others)}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

export default function StocksTab({ list, onChange }) {
  return (
    <>
      <FindStocks list={list} onChange={onChange} />
      <TrackedStocks list={list} onChange={onChange} />
    </>
  )
}
```

### frontend/src/components/TickerTable.jsx

```jsx
import { useOpenChart } from '../chartContext'
import { number, percent, points } from '../format'
import { routes } from '../useRoute'

const ChartIcon = () => (
  <svg className="chart-icon" width="12" height="12" viewBox="0 0 12 12" aria-hidden="true">
    <polyline points="1,10 4,6 7,8 11,2" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
)

function Row({ t, openChart }) {
  return (
    <tr
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
  )
}

// Click a row (or Tab to its ticker and press Enter) to open that ticker's chart.
// focus (the Today tab): show only these tickers (your main stocks), in this order, plus any
// other ticker flagged in this report, so the dashboard never hides an unusual move.
export default function TickerTable({ tickers, focus }) {
  const openChart = useOpenChart()
  if (!tickers?.length) return null
  let shown = tickers
  let alsoFlagged = []
  if (focus?.length) {
    const byTicker = Object.fromEntries(tickers.map((t) => [t.ticker, t]))
    shown = focus.map((ticker) => byTicker[ticker]).filter(Boolean)
    alsoFlagged = tickers.filter((t) => t.category === 'flagged' && !focus.includes(t.ticker))
  }
  const hidden = tickers.length - shown.length - alsoFlagged.length
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
          {shown.map((t) => (
            <Row key={t.ticker} t={t} openChart={openChart} />
          ))}
          {alsoFlagged.length > 0 && (
            <tr className="group-row">
              <th colSpan={7} scope="rowgroup">Also flagged (not a main stock)</th>
            </tr>
          )}
          {alsoFlagged.map((t) => (
            <Row key={t.ticker} t={t} openChart={openChart} />
          ))}
        </tbody>
      </table>
      {focus?.length > 0 && hidden > 0 && (
        <p className="muted small table-note">
          Showing your main stocks. {hidden} more in this report: <a href={routes.stocks}>see all tracked stocks</a>.
        </p>
      )}
    </div>
  )
}
```

### frontend/src/components/ReportView.jsx

```jsx
import { formatTime, safeUrl } from '../format'
import Markdown from './Markdown'
import StatusBadge from './StatusBadge'
import TickerTable from './TickerTable'

// current: true for the latest report (see StatusBadge). focus: the main stocks, for the Today tab's table
export default function ReportView({ report, current = false, focus }) {
  return (
    <article className="report">
      <div className="report-head">
        <StatusBadge status={report.status} current={current} />
        <span className="muted small">
          As of {report.as_of} · saved {formatTime(report.updated_at)}
          {report.status === 'intraday' && current && ` · update ${report.revision}`}
        </span>
      </div>

      <TickerTable tickers={report.tickers} focus={focus} />
      <Markdown text={report.body_md} />

      {report.sources?.length > 0 && (
        <details className="sources">
          <summary>Sources ({report.sources.length})</summary>
          <ul>
            {report.sources.map((s, i) => (
              <li key={i}>
                <a href={safeUrl(s.url)} target="_blank" rel="noopener noreferrer">{s.title || s.url}</a>
                <span className="muted"> · {s.publisher} · {s.ticker}</span>
              </li>
            ))}
          </ul>
        </details>
      )}
    </article>
  )
}
```

### frontend/src/App.jsx

```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { getCurrentRun, getLatestReport, getWatchlist } from './api'
import { ChartContext } from './chartContext'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
import CalendarTab from './components/CalendarTab'
import ComingUp from './components/ComingUp'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'
import StocksTab from './components/StocksTab'
import TickerChart from './components/TickerChart'

export default function App() {
  const route = useRoute()
  const [latest, setLatest] = useState(null)
  const [latestError, setLatestError] = useState(null)
  const [run, setRun] = useState(null)
  const [lastSaved, setLastSaved] = useState(null) // tells the previous-days views to refresh
  const [chartTicker, setChartTicker] = useState(null)
  const [calendarScan, setCalendarScan] = useState(null) // "Update now" on the Calendar tab
  const [calendarVersion, setCalendarVersion] = useState(0) // tells the calendar to reload
  const [watchlist, setWatchlist] = useState(null) // tracked stocks; the main ones focus the Today tab
  const chartOpener = useRef(null) // gets focus back when the chart closes

  const openChart = useCallback((ticker, opener) => {
    chartOpener.current = opener
    setChartTicker(ticker)
  }, [])
  const closeChart = useCallback(() => {
    setChartTicker(null)
    setTimeout(() => chartOpener.current?.focus(), 0)
  }, [])

  const loadLatest = useCallback(() => {
    getLatestReport()
      .then((report) => {
        setLatest(report)
        setLatestError(null)
      })
      .catch((error) => setLatestError(error.message))
  }, [])

  const loadWatchlist = useCallback(() => {
    getWatchlist()
      .then(setWatchlist)
      .catch(() => {}) // the Today tab then shows every ticker, as before
  }, [])

  useEffect(() => {
    loadLatest()
    loadWatchlist()
    getCurrentRun().then(setRun).catch(() => {})
  }, [loadLatest, loadWatchlist])

  useEffect(() => {
    window.scrollTo(0, 0) // start each tab at the top
  }, [route.tab])

  const connected = useLiveEvents((event) => {
    if (event.type === 'hello') {
      setRun(event.run) // (re)connected: catch up on anything missed
      setCalendarScan(event.calendar_scan)
      setCalendarVersion((v) => v + 1)
      loadLatest()
    } else if (event.type === 'calendar_scan') {
      setCalendarScan(event.scan)
    } else if (event.type === 'calendar_updated') {
      setCalendarVersion((v) => v + 1) // any calendar update: the daily scan, or "Update now"
      loadWatchlist() // next events
    } else if (event.type === 'watchlist_changed') {
      loadWatchlist() // from this page, another tab, or watchlist.txt edited by hand
    } else if (event.type === 'report_saved') {
      loadLatest()
      loadWatchlist() // latest figures
      setLastSaved(event)
    } else if (event.type === 'run_started' || event.type === 'run_finished') {
      setRun(event.run)
    } else if (event.type === 'run_event') {
      setRun((current) => current && { ...current, log: [...current.log, event.event] })
    }
  })

  // The live stream may have already moved the run on by the time the button's response arrives
  const onRunStarted = (started) =>
    setRun((current) => (current && current.started_at === started.started_at ? current : started))
  const onCalendarScanStarted = (started) =>
    setCalendarScan((current) => (current && current.started_at === started.started_at ? current : started))

  const tabLink = (tab, href, label) => (
    <a href={href} className={`tab ${route.tab === tab ? 'active' : ''}`} aria-current={route.tab === tab ? 'page' : undefined}>
      {label}
    </a>
  )

  return (
    <ChartContext.Provider value={openChart}>
      <div className="app">
        <header className="topbar">
          <h1>Market Analyst</h1>
          <nav className="tabs" aria-label="Sections">
            {tabLink('today', routes.today, 'Today')}
            {tabLink('previous', routes.previous(), 'Previous days')}
            {tabLink('calendar', routes.calendar(), 'Calendar')}
            {tabLink('stocks', routes.stocks, 'Stocks')}
          </nav>
          <span className={`connection ${connected ? 'on' : 'off'}`}>
            {connected ? 'Live' : 'Reconnecting…'}
          </span>
        </header>

        {/* Both tabs stay mounted, so switching keeps a streamed answer or run progress on screen */}
        <div hidden={route.tab !== 'today'}>
          <main className="layout">
            <section className="panel latest" aria-label="Latest report">
              <h2>Latest report</h2>
              {latest ? (
                <ReportView report={latest} current focus={watchlist?.stocks.filter((s) => s.main).map((s) => s.ticker)} />
              ) : (
                <p className="muted">
                  {latestError === 'no reports yet'
                    ? 'No reports yet. Use "Run update now" to write the first one.'
                    : latestError || 'Loading…'}
                </p>
              )}
            </section>

            <aside className="side">
              <RunPanel run={run} onStarted={onRunStarted} lastSaved={lastSaved} />
              <ComingUp version={calendarVersion} />
              <AskPanel />
            </aside>
          </main>

          <PreviousDaysPreview latestDate={latest?.session_date} lastSaved={lastSaved} />
        </div>

        <div hidden={route.tab !== 'previous'}>
          <PreviousDaysTab
            latestDate={latest?.session_date}
            lastSaved={lastSaved}
            selectedDate={route.tab === 'previous' ? route.date : null}
          />
        </div>

        <div hidden={route.tab !== 'stocks'}>
          <StocksTab list={watchlist} onChange={setWatchlist} />
        </div>

        <div hidden={route.tab !== 'calendar'}>
          <CalendarTab
            selectedDate={route.tab === 'calendar' ? route.date : null}
            version={calendarVersion}
            scan={calendarScan}
            onScanStarted={onCalendarScanStarted}
          />
        </div>

        {chartTicker && <TickerChart ticker={chartTicker} latestDate={latest?.session_date} onClose={closeChart} />}
      </div>
    </ChartContext.Provider>
  )
}
```

### frontend/src/useRoute.js

```javascript
import { useEffect, useState } from 'react'

// A tiny router using the part of the address after #:
//   #/                      Today
//   #/previous              Previous days (newest day shown)
//   #/previous/2026-11-05   Previous days, with that day open
//   #/calendar              Upcoming events calendar
//   #/calendar/2026-11-12   The calendar, with that day's events open
//   #/stocks                Every tracked stock, and finding new ones
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date] = hash.replace(/^#/, '').split('/')
  if (tab === 'stocks') return { tab: 'stocks', date: null }
  if (tab !== 'previous' && tab !== 'calendar') return { tab: 'today', date: null }
  return { tab, date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
  calendar: (date) => (date ? `#/calendar/${date}` : '#/calendar'),
  stocks: '#/stocks',
}

export function useRoute() {
  const [route, setRoute] = useState(() => parse(window.location.hash))
  useEffect(() => {
    const onChange = () => setRoute(parse(window.location.hash))
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}
```

### frontend/src/api.js

```javascript
// Helpers for talking to the Python API. Paths start with /api: in development
// Vite forwards them to port 8000, and in production the API serves this app itself.

async function request(path, options) {
  const response = await fetch(path, options)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}

const postJSON = (path, data) =>
  fetch(path, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(data) })

export const getLatestReport = () => request('/api/reports/latest')

export const getReport = (date) => request(`/api/reports/${date}`)

export const listReports = ({ before, limit = 20 } = {}) =>
  request(`/api/reports?limit=${limit}${before ? `&before=${before}` : ''}`).then((body) => body.reports)

export const getCurrentRun = () => request('/api/runs/current').then((body) => body.run)

export const getPrices = (ticker, range) =>
  request(`/api/tickers/${encodeURIComponent(ticker)}/prices?range=${range}`).then((body) => body.prices)

export const searchReports = (q, limit = 12) =>
  request(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`)

export const getAlerts = (limit = 10) => request(`/api/alerts?limit=${limit}`)

export const getWatchlist = () => request('/api/watchlist')

export const searchStocks = (q) => request(`/api/stocks/search?q=${encodeURIComponent(q)}`).then((body) => body.results)

async function post(path, data) {
  const response = await postJSON(path, data)
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body
}

// Each returns the updated list (adding also returns the new stock's details)
export const addStock = (ticker, main = false) => post('/api/watchlist', { ticker, main })
export const setMainStock = (ticker, main) => post(`/api/watchlist/${encodeURIComponent(ticker)}`, { main })
export const removeStock = (ticker) => post(`/api/watchlist/${encodeURIComponent(ticker)}/remove`, {})

export const getCalendar = (start, end) => request(`/api/calendar?start=${start}&end=${end}`)

export async function startCalendarScan() {
  const response = await postJSON('/api/calendar/scan', {})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body.scan
}

export const getTickerHistory = (ticker, limit = 365) =>
  request(`/api/tickers/${encodeURIComponent(ticker)}/history?limit=${limit}`).then((body) => body.history)

export async function startRun() {
  const response = await postJSON('/api/runs', {})
  const body = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`)
  return body.run
}

// Streams Claude's answer. onEvent receives {type: 'delta', text} as it's written,
// then {type: 'done', answer, reports_used, cost_usd} or {type: 'error', error}.
export async function askQuestion(question, onEvent) {
  const response = await postJSON('/api/ask', { question })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new Error(body.error || `Request failed (${response.status})`)
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  for (;;) {
    const { value, done } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() // keep any half-received line for the next chunk
    for (const line of lines) if (line.trim()) onEvent(JSON.parse(line))
  }
  if (buffer.trim()) onEvent(JSON.parse(buffer))
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

.table-wrap { position: relative; overflow-x: auto; margin-bottom: 8px; } /* relative: keeps hidden labels inside the scroll area */
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
.alerts-status { margin: 10px 0 0; overflow-wrap: anywhere; }
.alerts-status .alert-failed { color: var(--down); }
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

/* Calendar tab */
.calendar .section-head { align-items: center; }
.cal-update { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }
.cal-nav { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.cal-nav .chip { font-size: 1.1rem; line-height: 1; padding: 4px 12px; cursor: pointer; }
.cal-month { margin: 0 4px; font-size: 1.05rem; min-width: 9.5em; text-align: center; }
.cal-grid { display: grid; grid-template-columns: repeat(7, minmax(0, 1fr)); gap: 4px; }
.cal-weekday { font-size: 0.75rem; font-weight: 600; color: var(--muted); text-align: center; padding: 2px 0; }
.cal-day {
  display: flex; flex-direction: column; gap: 2px; min-width: 0; min-height: 92px; padding: 6px;
  border: 1px solid var(--border); border-radius: 8px; background: var(--panel); color: var(--text); text-decoration: none;
}
.cal-day:hover { border-color: var(--accent); }
.cal-day:focus-visible { outline: 2px solid var(--accent); outline-offset: 1px; }
.cal-day.weekend .cal-date, .cal-day.past .cal-date { color: var(--muted); }
.cal-day.past { background: var(--bg); }  /* days gone by: kept for history, shown quieter */
.cal-day.past .cal-name { background: var(--panel); color: var(--muted); }
.cal-day.other-month { opacity: 0.5; }
.cal-day.today .cal-date { background: var(--accent); color: var(--accent-text); border-radius: 999px; padding: 0 7px; }
.cal-day.selected { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent); }
.cal-date { align-self: flex-start; font-size: 0.8rem; font-weight: 600; }
.cal-name {
  font-size: 0.8rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
  background: var(--bg); border-radius: 4px; padding: 1px 5px;
}
.cal-more { font-size: 0.75rem; color: var(--muted); }
.cal-name .short, .cal-more .short { display: none; }
.cal-note { margin: 10px 0 0; }
@media (max-width: 640px) {
  .cal-grid { gap: 2px; }
  .cal-day { min-height: 64px; padding: 4px 2px; border-radius: 6px; }
  .cal-name { font-size: 0.68rem; padding: 0 2px; }
  .cal-name .long, .cal-more .long { display: none; }
  .cal-name .short, .cal-more .short { display: inline; }
  .cal-month { min-width: 0; }
}
.cal-day-detail { margin-top: 16px; scroll-margin-top: 12px; }
.cal-event { border-top: 1px solid var(--border); padding: 12px 0; }
.cal-event:first-of-type { border-top: 0; padding-top: 0; }
.cal-event h3 { margin: 4px 0; font-size: 1rem; }
.cal-event p { margin: 4px 0; }
.cal-event-head { display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap; }
.kind { font-size: 0.75rem; font-weight: 600; border-radius: 999px; padding: 1px 8px; border: 1px solid transparent; }
.kind-earnings { color: var(--accent); border-color: var(--accent); }
.kind-dividend { color: var(--final); background: var(--final-bg); }
.kind-news { color: var(--live); background: var(--live-bg); }
.cal-sources { margin: 6px 0 0; padding-left: 18px; }
.cal-sources li { margin: 3px 0; overflow-wrap: anywhere; }

/* Coming up (Today tab) */
.coming-up ul { list-style: none; margin: 0; padding: 0; display: grid; gap: 2px; }
.coming-up li a { display: flex; gap: 10px; padding: 6px 8px; margin: 0 -8px; border-radius: 6px; color: var(--text); text-decoration: none; }
.coming-up li a:hover { background: var(--bg); }
.cu-date { flex: none; width: 6.5em; font-size: 0.85rem; font-weight: 600; color: var(--muted); }
.cu-what { min-width: 0; font-size: 0.9rem; }

/* Stocks tab, and the Today tab's focus on main stocks */
.sr-only { position: absolute; width: 1px; height: 1px; overflow: hidden; clip: rect(0 0 0 0); white-space: nowrap; }
.tickers .group-row th { padding-top: 14px; font-size: 0.78rem; font-weight: 600; color: var(--muted); text-transform: uppercase; letter-spacing: 0.04em; }
.table-note { margin: 6px 0 0; }
.stocks-find { margin-bottom: 16px; }
.stocks-find input[type="search"] {
  width: 100%; padding: 10px 12px; font: inherit; color: var(--text); background: var(--bg);
  border: 1px solid var(--border); border-radius: 8px;
}
.notice { color: var(--final); }
.search-hits { list-style: none; margin: 8px 0 0; padding: 0; display: grid; gap: 4px; }
.search-hits li {
  display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap;
  padding: 8px 10px; border: 1px solid var(--border); border-radius: 8px;
}
.hit-name { min-width: 0; overflow-wrap: anywhere; }
.hit-actions { display: flex; gap: 6px; }
.hit-actions .chip { cursor: pointer; }
.hit-actions .chip:disabled { opacity: 0.5; cursor: not-allowed; }
.star { background: none; border: 0; padding: 2px; color: var(--muted); cursor: pointer; line-height: 0; border-radius: 4px; }
.star.on { color: var(--live); }
.star:disabled { opacity: 0.4; cursor: not-allowed; }
.star:focus-visible { outline: 2px solid var(--accent); }
.stocks .stock-name { max-width: 16em; overflow: hidden; text-overflow: ellipsis; }
.stocks .next-event a { color: var(--text); }
.row-actions { text-align: right; }
.row-actions .link { padding: 0 0 0 10px; }
.link.danger { color: var(--down); }

```

### tests/test_watchlist.py

```python
"""Offline tests for tracked and main stocks: the watchlist file, finding stocks, the API,
and the calendar scan staying in small requests as the list grows. Yahoo Finance is faked.

Run from the project folder:
    pytest -v tests/test_watchlist.py

Live check of Yahoo's search (needs internet and a recent yfinance):
    LIVE_TESTS=1 pytest -v -s -k live_search
"""

import asyncio
import json
import os
import re
import sys
import threading
import time
from contextlib import closing
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
import watchlist  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TODAY = date(2026, 11, 6)
KNOWN = {  # what the fake Yahoo Finance knows: ticker -> (type, name)
    "AAPL": ("EQUITY", "Apple Inc."), "MSFT": ("EQUITY", "Microsoft Corporation"),
    "NVDA": ("EQUITY", "NVIDIA Corporation"), "COST": ("EQUITY", "Costco Wholesale Corporation"),
    "SPY": ("ETF", "SPDR S&P 500 ETF Trust"), "BTC-USD": ("CRYPTOCURRENCY", "Bitcoin USD"),
    **{f"T{i:02d}": ("EQUITY", f"Test Company {i}") for i in range(40)},
}
SEARCHES = []  # every query that reached the fake Yahoo search


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        if self.ticker == "FLAKY":
            raise ConnectionError("Yahoo rate limit")
        kind, name = KNOWN.get(self.ticker, (None, None))
        return {"quoteType": kind, "longName": name} if kind else {}


def fake_search(query):
    SEARCHES.append(query)
    if query == "broken":
        raise ConnectionError("timed out")
    return [
        {"symbol": "COST", "quoteType": "EQUITY", "longname": "Costco Wholesale Corporation", "exchDisp": "NASDAQ"},
        {"symbol": "CTCO.L", "quoteType": "EQUITY", "shortname": "Costco UK", "exchDisp": "London"},  # not US
        {"symbol": "XCOSX", "quoteType": "MUTUALFUND", "shortname": "Cost Fund"},
        {"symbol": "COST-USD", "quoteType": "CRYPTOCURRENCY", "shortname": "CostCoin"},
        {"symbol": "^COST", "quoteType": "INDEX", "shortname": "Cost index"},
        {"symbol": "SPY", "typeDisp": "ETF", "shortname": "SPDR S&P 500"},  # older format: no quoteType
        {"symbol": "AAPL", "quoteType": "EQUITY", "shortname": "Apple Inc.", "exchDisp": "NASDAQ"},
    ]


@pytest.fixture
def wl(tmp_path, monkeypatch):
    """A temporary watchlist and database, a fixed 'today', and fake Yahoo Finance. Returns the file."""
    path = tmp_path / "watchlist.txt"
    path.write_text("# my stocks\n*AAPL\n*NVDA  SMH   # vs. semiconductors\n\nMSFT\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", path)
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(watchlist.yf, "Ticker", FakeTicker)
    monkeypatch.setattr(watchlist, "search_yahoo", fake_search)
    monkeypatch.setattr(events, "today_et", lambda: TODAY)
    monkeypatch.setattr(events, "fetch_calendar", lambda t: {"Earnings Date": [date(2026, 11, 19)]} if t == "COST" else {})
    monkeypatch.setattr(events, "company_name", lambda t: events.short_name(KNOWN.get(t, ("", t))[1]))
    watchlist._search_cache.clear()
    events._names.clear()
    SEARCHES.clear()
    return path


# ---------------------------------------------------------------------------
# The file
# ---------------------------------------------------------------------------

def test_a_star_marks_a_main_stock(wl):
    found = watchlist.entries()

    assert [(e["ticker"], e["main"], e["benchmark"]) for e in found] == [
        ("AAPL", True, None), ("NVDA", True, "SMH"), ("MSFT", False, None)]
    assert market_tools.load_watchlist() == ["AAPL", "NVDA", "MSFT"]  # the agent still tracks all of them
    assert market_tools.load_benchmarks() == {"NVDA": "SMH"}
    assert watchlist.main_tickers() == ["AAPL", "NVDA"]


def test_without_stars_the_first_ten_are_main(wl):
    wl.write_text("\n".join(f"T{i:02d}" for i in range(12)) + "\n")
    assert watchlist.main_tickers() == [f"T{i:02d}" for i in range(10)]


def test_adding_keeps_every_other_line_as_it_was(wl):
    before = wl.read_text()

    info = watchlist.add("cost")

    assert info == {"ticker": "COST", "name": "Costco Wholesale Corporation", "type": "Stock", "main": False}
    assert wl.read_text() == before + "COST\n"


def test_the_first_edit_makes_the_implicit_main_stocks_explicit(wl):
    wl.write_text("AAPL\nMSFT  # mine\n")  # no stars: both are main
    watchlist.add("COST")  # added as tracked only, so it mustn't become main

    assert wl.read_text() == "*AAPL\n*MSFT  # mine\nCOST\n"
    assert watchlist.main_tickers() == ["AAPL", "MSFT"]


@pytest.mark.parametrize("ticker, message", [
    ("ZZZZ", "Yahoo Finance doesn't know ZZZZ"),
    ("BTC-USD", "BTC-USD is a cryptocurrency. Only stocks and ETFs can be tracked."),
    ("CTCO.L", "That isn't a US ticker"),
    ("FLAKY", "Couldn't check FLAKY with Yahoo Finance right now"),
    ("", "That isn't a US ticker"),
])
def test_adding_checks_the_ticker_first(wl, ticker, message):
    before = wl.read_text()
    with pytest.raises(watchlist.WatchlistError, match=re.escape(message)):
        watchlist.add(ticker)
    assert wl.read_text() == before


def test_limits_on_tracked_and_main_stocks(wl, monkeypatch):
    with pytest.raises(watchlist.WatchlistError, match="already tracking AAPL") as dup:
        watchlist.add("AAPL")
    assert dup.value.status == 409

    monkeypatch.setattr(watchlist, "MAX_TRACKED", 4)
    watchlist.add("COST")
    with pytest.raises(watchlist.WatchlistError, match="tracking 4 stocks, the most allowed"):
        watchlist.add("SPY")

    monkeypatch.setattr(watchlist, "MAX_MAIN", 2)
    with pytest.raises(watchlist.WatchlistError, match="already have 2 main stocks"):
        watchlist.set_main("MSFT", True)


def test_star_and_unstar_keep_the_rest_of_the_line(wl):
    watchlist.set_main("NVDA", False)
    assert "NVDA  SMH   # vs. semiconductors" in wl.read_text().splitlines()
    watchlist.set_main("MSFT", True)
    assert watchlist.main_tickers() == ["AAPL", "MSFT"]
    watchlist.set_main("NVDA", True)
    assert "*NVDA  SMH   # vs. semiconductors" in wl.read_text().splitlines()


def test_remove(wl):
    watchlist.remove("nvda")
    assert wl.read_text() == "# my stocks\n*AAPL\n\nMSFT\n"
    with pytest.raises(watchlist.WatchlistError, match="isn't on your list") as missing:
        watchlist.remove("NVDA")
    assert missing.value.status == 404


def test_edits_at_the_same_time_are_never_lost(wl):
    tickers = [f"T{i:02d}" for i in range(8)]
    threads = [threading.Thread(target=watchlist.add, args=(t,)) for t in tickers]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert set(tickers) <= set(market_tools.load_watchlist())
    assert len(market_tools.load_watchlist()) == 11
    assert not list(wl.parent.glob(".watchlist-*"))  # no temporary files left behind


@pytest.mark.skipif(os.name == "nt", reason="file permissions work differently on Windows")
def test_editing_keeps_the_files_permissions(wl):
    wl.chmod(0o644)
    watchlist.add("COST")
    assert wl.stat().st_mode & 0o777 == 0o644


# ---------------------------------------------------------------------------
# Finding stocks
# ---------------------------------------------------------------------------

def test_search_finds_us_stocks_and_etfs_only(wl):
    results = watchlist.search("  cost  ")

    assert [(r["ticker"], r["type"], r["tracked"]) for r in results] == [
        ("COST", "Stock", False), ("SPY", "ETF", False), ("AAPL", "Stock", True)]
    assert results[0]["name"] == "Costco Wholesale Corporation" and results[0]["exchange"] == "NASDAQ"
    assert SEARCHES == ["cost"]


def test_search_is_cached_and_problems_are_clear(wl):
    watchlist.search("cost")
    watchlist.search("COST")
    assert SEARCHES == ["cost"]  # the second search (any capitals) came from the cache
    assert watchlist.search("   ") == []
    with pytest.raises(watchlist.WatchlistError, match="search isn't answering right now"):
        watchlist.search("broken")


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(wl, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    reports_db.connect().close()  # the database exists, as it does once the program has run
    with TestClient(api.app) as test_client:
        yield test_client


def save_report(tickers):
    scan = {"session": {"status": "complete", "as_of": "2026-11-06"},
            "flagged": [{"ticker": tickers[0], "last_close": 190.0, "return_1d_pct": 4.1, "return_zscore": 2.9,
                         "volume_vs_avg": 2.0}],
            "quiet": [{"ticker": t, "last_close": 50.0, "return_1d_pct": 0.2} for t in tickers[1:]], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date="2026-11-06", status="final", title="Brief", body_md="# Brief",
                               as_of="2026-11-06", scan=scan)


def wait_until(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_lists_main_stocks_first_with_their_latest_figures(client):
    save_report(["AAPL", "MSFT"])
    events._names["AAPL"] = "Apple"

    body = client.get("/api/watchlist").json()

    assert [(s["ticker"], s["main"]) for s in body["stocks"]] == [("AAPL", True), ("NVDA", True), ("MSFT", False)]
    assert body["main_count"] == 2 and body["tracked_count"] == 3
    assert body["max_main"] == 10 and body["max_tracked"] == 25
    aapl, nvda, msft = body["stocks"]
    assert aapl["name"] == "Apple" and aapl["latest"]["category"] == "flagged" and aapl["latest"]["return_1d_pct"] == 4.1
    assert nvda["latest"] is None and nvda["benchmark"] == "SMH"  # not in any report yet
    assert msft["latest"]["category"] == "quiet" and msft["latest"]["price"] == 50.0
    # Names Yahoo hasn't given yet are looked up in the background
    wait_until(lambda: client.get("/api/watchlist").json()["stocks"][1]["name"] == "NVIDIA")


@pytest.mark.parametrize("name, short", [
    ("The Coca-Cola Company", "Coca-Cola"), ("The Home Depot, Inc.", "Home Depot"), ("Costco Wholesale Corporation", "Costco Wholesale"),
])
def test_short_names_for_new_stocks(name, short):
    assert events.short_name(name) == short


def test_quiet_stocks_keep_their_price(wl, monkeypatch):
    """flag_events gives quiet stocks a price too, so the Stocks tab can show every stock's."""
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    figures = {"AAPL": 0.4, "NVDA": 0.1, "MSFT": -0.2}
    monkeypatch.setattr(market_tools, "_measure", lambda t, session: (
        {"ticker": t, "last_price": 100.0 + figures[t], "return_1d_pct": figures[t], "return_zscore": 0.3,
         "volume_vs_avg": 1.0}, None))

    result = market_tools.flag_events()

    assert result["flagged"] == [] and result["quiet"][0] == {"ticker": "AAPL", "last_price": 100.4, "return_1d_pct": 0.4}


def test_api_add_star_and_remove(client):
    queue = api.hub.subscribe()

    added = client.post("/api/watchlist", json={"ticker": "COST"})
    starred = client.post("/api/watchlist/COST", json={"main": True})
    removed = client.post("/api/watchlist/MSFT/remove", json={})

    assert added.status_code == 201 and added.json()["stock"]["name"] == "Costco Wholesale Corporation"
    assert [s["ticker"] for s in added.json()["watchlist"]["stocks"]] == ["AAPL", "NVDA", "MSFT", "COST"]
    assert [s["ticker"] for s in starred.json()["stocks"] if s["main"]] == ["AAPL", "NVDA", "COST"]
    assert [s["ticker"] for s in removed.json()["stocks"]] == ["AAPL", "NVDA", "COST"]
    assert queue.qsize() >= 3 and queue.get_nowait() == {"type": "watchlist_changed"}
    # The new stock's earnings date is added in the background (Yahoo only, no Claude)
    wait_until(lambda: client.get("/api/watchlist").json()["stocks"][2]["next_event"])
    assert client.get("/api/watchlist").json()["stocks"][2]["next_event"]["line"] == "Thu Nov 19: Earnings report"


@pytest.mark.parametrize("path, body, status, message", [
    ("/api/watchlist", {"ticker": "AAPL"}, 409, "already tracking"),
    ("/api/watchlist", {"ticker": "ZZZZ"}, 400, "doesn't know"),
    ("/api/watchlist", {"symbol": "COST"}, 400, '{"ticker": "COST"}'),
    ("/api/watchlist/TSLA", {"main": True}, 404, "isn't on your list"),
    ("/api/watchlist/MSFT", {"main": "yes"}, 400, '{"main": true}'),
    ("/api/watchlist/TSLA/remove", {}, 404, "isn't on your list"),
])
def test_api_explains_what_went_wrong(client, path, body, status, message):
    response = client.post(path, json=body)
    assert response.status_code == status and message in response.json()["error"]


def test_other_websites_cannot_change_the_list(client, wl):
    before = wl.read_text()
    for path, body in (("/api/watchlist", {"ticker": "COST"}), ("/api/watchlist/AAPL/remove", {})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert wl.read_text() == before


def test_api_search(client):
    found = client.get("/api/stocks/search?q=cost").json()
    assert [r["ticker"] for r in found["results"]] == ["COST", "SPY", "AAPL"]
    assert client.get("/api/stocks/search").status_code == 400
    assert client.get("/api/stocks/search?q=broken").status_code == 502


def test_editing_watchlist_txt_by_hand_updates_open_pages(wl, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        wl.write_text(wl.read_text() + "COST\n")
        os.utime(wl, ns=(time.time_ns(), time.time_ns() + 10**9))  # make sure the change time moves on
        event = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return event

    assert asyncio.run(scenario()) == {"type": "watchlist_changed"}


# ---------------------------------------------------------------------------
# Growing the list: the agent gets room, and the calendar's Claude requests stay small
# ---------------------------------------------------------------------------

def test_bigger_watchlists_give_the_agent_more_turns(wl, monkeypatch):
    import run_brief
    assert run_brief.turn_limit() == 25  # 3 stocks: the usual limit
    wl.write_text("\n".join(f"T{i:02d}" for i in range(40)) + "\n")
    assert run_brief.turn_limit() == 50  # a news check for each stock, plus room for the other tools

    used = {}

    async def fake_query(*, prompt, options):  # stops the run once it has seen the options
        used["max_turns"], used["budget"] = options.max_turns, options.max_budget_usd
        raise RuntimeError("stop here")
        yield

    monkeypatch.setattr(run_brief, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    monkeypatch.setattr(run_brief, "query", fake_query)
    with pytest.raises(RuntimeError, match="stop here"):
        asyncio.run(run_brief.run_once())
    assert used == {"max_turns": 50, "budget": 1.00}  # the cost cap is unchanged
    assert run_brief.options.max_turns == 25           # the shared settings aren't changed


def test_calendar_scan_reads_a_long_watchlist_in_groups(wl, monkeypatch):
    wl.write_text("\n".join(f"T{i:02d}" for i in range(23)) + "\n")
    monkeypatch.setattr(events, "fetch_news", lambda t: [{"title": f"{t} news", "publisher": "Wire",
                                                          "published": "2026-11-05", "url": f"https://x.example/{t}",
                                                          "summary": "..."}])
    prompts = []

    def fake_claude(prompt):
        prompts.append(prompt)
        if len(prompts) == 2:
            raise RuntimeError("Claude couldn't read the news: error_max_budget_usd")
        return json.dumps({"events": []}), 0.02

    monkeypatch.setattr(events, "ask_claude", fake_claude)

    result = events.scan()

    assert len(prompts) == 3  # 10 + 10 + 3 companies
    assert [len(re.findall(r"^\[\d+\] ", p, re.M)) for p in prompts] == [10, 10, 3]
    assert "T10" not in prompts[0] and "T10 |" in prompts[1]  # each request sees only its own companies
    assert result["cost_usd"] == 0.04 and result["status"] == "partial"
    assert "news scan (group 2 of 3): Claude couldn't read the news" in result["message"]


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_search():
    import yfinance

    raw = watchlist.search_yahoo("costco")  # real Yahoo Finance (this test doesn't use the fakes)
    print(f"\nyfinance {yfinance.__version__}. Yahoo's matches for 'costco':",
          [(q.get("symbol"), q.get("quoteType"), q.get("exchDisp")) for q in raw])
    assert any(q.get("symbol") == "COST" for q in raw)
    info = watchlist.check_ticker("COST")
    print("Checked:", info)
    assert info["type"] == "Stock" and "Costco" in info["name"]
```
