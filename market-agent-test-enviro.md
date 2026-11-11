# Market Analyst Agent: Test Environment

A separate test environment with **two months of sample reports**, so you can see how the app behaves after long-term use: paging through weeks of history, month grouping, earnings days, a day that was never finalized, and questions about trends over time.

It runs your **real program's code** against its **own sample database**. Claude, market data, Voyage AI (for search), Discord (for alerts) and the events calendar's sources are simulated by default, so it costs nothing, needs no internet and never posts to your channel. It lives in its own folder next to `market-agent/` and **never writes anything into your program's folder**. An automated test checks this every time.

This builds on `market-agent-followups.md`. Your program should include everything up to that guide: the Previous days tab, charts, search, sector and market context, Discord alerts, the events calendar connected to briefs, alerts and Ask, finding and tracking stocks, and follow-through and story updates.

**Already set this up for an earlier version?**

1. Replace `sample_market.py`, `testenv.py` and `test_testenv.py` with the appendix versions.
2. Run `python testenv.py seed --reset`. This creates the test environment's **own watchlist**, `data/watchlist.txt`, so the Stocks tab never edits your real one, saves prices for quiet stocks, and works out two months of follow-through and story updates.
3. Run `python testenv.py build-frontend`.

---

## Contents

1. [What you get](#1-what-you-get)
2. [How it stays separate from your program](#2-how-it-stays-separate-from-your-program)
3. [Before you start](#3-before-you-start)
4. [Set it up](#4-set-it-up)
5. [What's in the sample data](#5-whats-in-the-sample-data)
6. [Things to test with two months of data](#6-things-to-test-with-two-months-of-data)
7. [Commands reference](#7-commands-reference)
8. [Using real Claude, Voyage, Discord or Yahoo (optional)](#8-using-real-claude-voyage-discord-or-yahoo-optional)
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
    │   ├── alerts_outbox.jsonl    the Discord alerts it "sent" (created by the first alert)
    │   ├── watchlist.txt          its own watchlist: the Stocks tab edits this copy, never yours
    │   └── sample_config.json     the settings used, so data can be recreated
    └── frontend-dist/             created by `build-frontend`: your app, built here
```

```
 Browser ── http://localhost:8100 ──▶ testenv.py serve
                                        │ uses your real api.py, run_brief.py, ask.py, reports_db.py
                                        │ (read from market-agent/, never written)
                                        ├── reads/writes ──▶ market-agent-testenv/data/reports.db (+ search.db)
                                        ├── Claude ─────────▶ simulated (offline answers)
                                        ├── market data ────▶ simulated (sample_market.py): prices, sectors, the S&P 500
                                        ├── Voyage AI ──────▶ simulated (topic-based stand-in for search)
                                        ├── Discord ────────▶ simulated (written to data/alerts_outbox.jsonl)
                                        ├── events calendar ▶ simulated company calendars and news, read by a stand-in for Claude
                                        ├── story updates ──▶ simulated later headlines, read by a stand-in for Claude
                                        ├── watchlist ──────▶ data/watchlist.txt (a copy; your real one is only read)
                                        └── stock search ───▶ simulated (a built-in list of US stocks and ETFs)
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
| Sector and market context | Every flagged move compared with its simulated sector ETF and S&P 500, with stock-specific, sector-wide, market-wide and mixed days in the sample |
| Discord alerts | Flag alerts and daily summaries by the real rules, written to a file (`python testenv.py alerts`), or sent to Discord with `--live-alerts` |
| Events calendar | Two months of calendar history and the weeks ahead (earnings, ex-dividend dates and news events), the daily update (`python testenv.py events`) and **Update now**, all checked and saved by your real `events.py` |
| Finding and tracking stocks | Search a built-in list of US stocks and ETFs offline; track, star and remove stocks in the test environment's own watchlist. A stock you add gets simulated prices and appears from the next run, as in real use |
| Follow-through and story updates | Two months of follow-through worked out by your real `followups.py` over the simulated prices: 27 moves, 18 with all three figures, 12 surprises. Every surprise's story checked by your real `stories.py`, reading simulated later headlines with a free stand-in for Claude, or real Claude with `--live-stories`. **Refresh prices** and **Check for updates** work offline |
| A year or more of history | `python testenv.py seed --reset --months 12` |

---

## 2. How it stays separate from your program

| Risk | How it's prevented |
|---|---|
| Changing your real reports | The test environment uses its own database, `market-agent-testenv/data/reports.db`, with its own search index and alert log. Before anything runs, it refuses to use any database inside `market-agent/`. |
| Changing your watchlist | The test environment has its own `data/watchlist.txt`, copied from yours the first time you seed. The Stocks tab and every simulated run use that copy; your `market-agent/watchlist.txt` is only read, to make it. A test checks your file is unchanged after adding, starring and removing stocks. |
| Changing your code | It only *reads* files in `market-agent/`. Python's cache folders (`__pycache__`) are switched off, so not even those get written. A test confirms every file in `market-agent/` is byte-for-byte unchanged. |
| Changing your frontend build | The app is built into `market-agent-testenv/frontend-dist/`. Your `frontend/dist/` is never touched. (Vite may update its own cache inside `node_modules`, as it does on any build.) |
| Clashing with the running app | The test app uses port **8100**. Your real API (8000) and dev server (5173) can run at the same time. |
| Spending money | Claude, market data and Voyage are simulated unless you choose `--live-ask`, `--live-runs`, `--live-embeddings`, `--live-calendar` or `--live-stories`. (`--live-search` uses Yahoo's free search.) |
| Posting to your Discord | Alerts are written to `data/alerts_outbox.jsonl` instead, even if `DISCORD_WEBHOOK_URL` is set in your terminal. Only `serve --live-alerts` sends them. A test checks that no connection to Discord is made. |
| Interfering with scheduled runs | Your cron or Task Scheduler entries aren't touched, and the test environment has no schedule of its own. |
| Being set up in the wrong place | If the test folder is inside `market-agent/`, it refuses to run. |

**Which code it tests:** always the current code in `market-agent/`. When you change your program, the test environment picks up the change on its next start (section 10).

---

## 3. Before you start

- [ ] Your program includes everything up to `market-agent-followups.md`, and its tests pass (`pytest -v` in `market-agent/` shows `276 passed, 3 skipped`)
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

This takes a second or two. It prints a summary like this (for a run on 6 November 2026, or with `--end 2026-11-06`):

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
  "sector_move_days": ["2026-09-15", "2026-10-29"],
  "kinds_of_move": {"market-wide": 7, "mixed": 4, "sector-wide": 3, "stock-specific": 13},
  "search_index": {"reports": 44, "passages": 73},
  "alerts": {"logged": 0, "outbox_messages": 0},
  "calendar": {"upcoming": 7, "past": 17, "scans": 9,
               "next": ["2026-11-09 Microsoft: Court hearing in patent case", "2026-11-12 Microsoft: Regulator's decision on deal",
                        "2026-11-16 Apple: Court hearing in patent case", "2026-11-19 JPMorgan Chase: Investor day"]},
  "watchlist": {"file": ".../market-agent-testenv/data/watchlist.txt", "tracked": 5, "main": ["AAPL", "MSFT", "NVDA"],
                "added_since_seeding": [], "removed_since_seeding": []},
  "follow_through": {"moves": 27, "settled": 18, "surprises": 12, "story_updates": 12}
}
```

Your numbers will differ, because the sample ends on the day you run it and uses your watchlist. `kinds_of_move` counts the verdicts on flagged moves in final reports. `sector_move_days` are the days the sample gave one of your sectors a big move of its own. `calendar` counts events from the "today" of the sample onwards (`upcoming`) and before it (`past`), and lists the next few. `watchlist` is the test environment's own list: its main stocks, and any stocks added or removed on the Stocks tab since you seeded. `follow_through` counts the moves followed up, those with all three figures (`settled`), the surprises, and the story updates.

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
Test environment: http://localhost:8100  ·  offline (no Claude, no Voyage, no Discord, no cost)  ·  database .../market-agent-testenv/data/reports.db
```

Press Ctrl+C to stop it.

### Step 7: Check it

In a second terminal (same folder, same Python environment):

```bash
pytest -v
```

Expect `33 passed`. The last test confirms your `market-agent/` folder is exactly as it was.

---

## 5. What's in the sample data

| Item | Detail |
|---|---|
| **Date range** | Two calendar months back from today (or from `--end`), trading days only. Weekends and NYSE holidays are skipped: ending 6 Nov 2026 gives 8 Sep to 6 Nov, 44 trading days, with Labor Day skipped. |
| **Tickers** | The test environment's own watchlist, `data/watchlist.txt`. The first `seed` copies your `market-agent/watchlist.txt` (only read) and, if it has no stars, stars the first 3 so the Today tab shows main stocks and "N more". Later seeds keep it, so stocks you added get two months of history. `--tickers` replaces it |
| **Stock search** | A built-in list of 35 well-known US stocks and ETFs (Costco, Coca-Cola, Berkshire Hathaway, SPY, SMH and so on), plus a few that can't be tracked (listings outside the US, Bitcoin, an index, a future, a mutual fund) to show the filtering. Searches and checks go through your real `watchlist.py` |
| **Stocks added later** | Get their own simulated prices, news days and company calendar, without changing anything for the stocks already in the sample. Past reports don't include them; they appear from the next run (`update`, `finalize` or Run update now), as in real use. Removed stocks leave the next run |
| **Prices and volume** | Simulated for each ticker with realistic day-to-day swings, built from a market move, a move for its sector, and its own move. **Not real prices.** |
| **Sectors and the S&P 500** | The S&P 500 (SPY) and all 11 sector ETFs are simulated too. AAPL, MSFT and NVDA are Technology (XLK), AMZN is Consumer Discretionary (XLY), JPM is Financials (XLF), and any other ticker gets a sector picked from its name. A few days give one sector a big move of its own ("A sector-wide rally in … stocks"), with busy trading in its tickers |
| **Verdicts and backdrop** | Worked out with your program's own rules from `market_tools.py` (`describe_context` and `describe_backdrop`), so the "Vs. sector and market" lines, the table's Vs. sector column and the "Market backdrop" section read exactly like real ones |
| **Alerts** | The seeded history has none. `update`, `finalize` and Run update now send simulated alerts by the real rules from then on |
| **Events calendar** | Built as daily use would have built it: a simulated scan each Monday of the two months, then one for "today". Each scan uses your real `events.py`, so the same checks, matching and storage rules apply. The data it reads is simulated: company calendars (quarterly earnings dates from each ticker's earnings day, sometimes an unconfirmed window, and ex-dividend dates for AAPL, MSFT and JPM); sample news announcing about two dated events a week (product launches, court hearings, investor days, shareholder votes, regulatory decisions), plus earnings previews; and a free stand-in for Claude that reports those events from the headlines it's given. |
| **Earnings** | One earnings day per ticker within the range: a large move on heavy volume, with a matching headline |
| **Other news** | About a 4% chance per ticker per day of a news-driven move (upgrades, downgrades, product news and so on), and roughly one market-wide day every 20 sessions |
| **Unexplained moves** | Normal random swings sometimes cross the flagging threshold. Those say "No clear catalyst found", as your agent should. |
| **News sources** | Fictional publishers (Sample Wire, Demo Markets Daily, Example Financial News) linking to `news.example.com`, a domain reserved for examples |
| **How reports were saved** | Through your real `save_report()`, following the real storage rules. Most days have intraday updates at 10:45 and 12:30, then a final report at 8:16 the next morning (or 4:30pm the same day), with timestamps to match. |
| **Edge cases** | One day mid-range was never finalized and shows "Intraday (not finalized)". The latest day is left as a live intraday report if the range ends on a trading day. Early-close days say so in the brief. |
| **Coming up** | Every sample brief ends with "Coming up": the next 7 days of earnings and ex-dividend dates, and news events announced by then, in your program's own line format. Simulated runs call `upcoming_events` like the real agent; the daily summary alert, offline Ask and the Today tab's card read the sample calendar through your real code |
| **Follow-through** | Worked out when you seed, by your real `followups.py`, from the simulated closes after each move flagged in a final report. The sample's "latest close" is its latest finished day, so today's live day is never used |
| **Story updates** | Most news-driven and earnings moves get a follow-up headline 2 to 6 days later ("Nvidia responds to last week's concerns"), from the same fictional publishers. Every surprise was checked when you seeded, as the final report a week after it would have done. The stand-in for Claude finds the follow-up headline if there is one ("Developed"), or says nothing newer is about the move ("No update"). Checks cost $0 |
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

- [ ] **Run update now** shows "Scanning the watchlist", "Checking the market and sectors", a "Reading news for…" line for each flagged ticker, then "Saved (updated) · $0.000", and the latest report moves on 15 minutes
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

**Sector and market context**

- [ ] The latest report has a "Market backdrop" section, and each flagged ticker has a "Vs. sector and market" line
- [ ] In the ticker table, flagged rows show the gap (for example "+5.09 pts vs XLK") with the verdict under it; hovering shows the full sentence
- [ ] Each `earnings_days` date reads **stock-specific**; each `sector_move_days` date reads **sector-wide** for that sector's flagged tickers; a market-wide day ("A broad market rally…" or "sell-off…") reads **market-wide**
- [ ] Ask "Was AMZN's move on [a sector_move_days date] about Amazon or its sector?" With `--live-ask`, the answer should use the verdict
- [ ] Search "sector-wide" finds the sector-move days

**Discord alerts**

- [ ] The run panel says **Discord alerts on** (simulated)
- [ ] With the latest day still intraday, **Run update now** (or `python testenv.py update`) ends with "Discord: sent flag alert: …" for the day's flagged ticker, and the status line shows "last sent … (TICKER)"
- [ ] `python testenv.py alerts` prints that message: the card title, figures, the sector sentence and the reason
- [ ] Running again doesn't repeat it, and `finalize` adds one daily summary (run `alerts` again to see it)
- [ ] `python testenv.py alerts --clear` empties the outbox. The alert log in the sample database stays, so already-sent alerts still aren't repeated; `seed --reset` starts alerts from scratch
- [ ] With `serve --live-alerts` (section 8), the same messages arrive in your Discord channel

**Events calendar**

- [ ] The **Calendar** tab opens on the sample's month, with just company names on each day. Today is circled, and past days are shown more quietly
- [ ] The `next` events from `status` are on their days. Clicking one opens its page: "In the news", one or two sentences, and a link to its (fictional) article
- [ ] Next month shows an earnings date marked "(date not confirmed)" with its window, an analysts' estimate and a Yahoo Finance link
- [ ] Past earnings days (`earnings_days` in `status`) are on the calendar, some with an "In the news" preview
- [ ] **Update now** shows "Checking …'s calendar and news" and "Reading … headlines", then "Updated" with the new time, and nothing is doubled. Pressing again straight away explains the cooldown (15 seconds here)
- [ ] In a second terminal, `python testenv.py events` (the daily update) refreshes the open calendar's "Updated" time within a couple of seconds
- [ ] At phone width, days show tickers, and an opened day scrolls into view
- [ ] The calendar is plain data you can read yourself: in `market-agent/`, `REPORTS_DB=../market-agent-testenv/data/reports.db python events.py list` lists the sample's upcoming events (from the real today onwards). Only use `list` or `show` this way: `scan` would use real Yahoo and Claude

**Coming up (the calendar in briefs, alerts and Ask)**

- [ ] The Today tab's **Coming up** card lists the `next` events from `status` that fall in the next week. Clicking one opens its day on the Calendar tab
- [ ] The latest report ends with a "Coming up" section listing the same events
- [ ] **Run update now** shows "Checking the events calendar" in its steps
- [ ] Ask **What's coming up next week?** (one of the examples: click it, then Ask). The offline answer lists the next events, cited as (calendar)
- [ ] Ask "What's next for MSFT?": the answer includes its next calendar event
- [ ] After `python testenv.py update` then `finalize`, `python testenv.py alerts` shows the daily summary ending with "Coming up:"
- [ ] Searching "earnings" finds the earnings days, not the days before them: "Coming up" is left out of search

**Finding and tracking stocks**

- [ ] The Today tab shows only the 3 main stocks, with "Showing your main stocks. 2 more in this report". Its link opens the **Stocks** tab
- [ ] The Stocks tab shows "5 of 25 tracked · 3 of 10 main", the main and other stocks in two groups, and each stock's price, status and next event
- [ ] Searching "costco" offers `COST` only (not `COST.MX`); "bitcoin" offers nothing; "semiconductor" offers `SMH`
- [ ] **Track as main** adds COST: `data/watchlist.txt` gains `*COST`, and its next earnings date appears within a few seconds. It says "first report next run"
- [ ] **Run update now** (or `python testenv.py update`): COST gets figures and joins the Today tab. Its chart opens from the Stocks tab
- [ ] Unstar the day's flagged stock: it moves under "Also flagged" on the Today tab
- [ ] **Remove** asks once more; **Keep** cancels
- [ ] Add a line such as `*KO` to `data/watchlist.txt` in an editor: the Stocks tab shows it within a few seconds
- [ ] `python testenv.py status` lists the stocks you added under `added_since_seeding`. `python testenv.py seed --reset` keeps them and gives them two months of history
- [ ] Your `market-agent/watchlist.txt` is unchanged throughout

**Follow-through and story updates**

- [ ] The Follow-through tab shows "12 held · 8 faded · 6 reversed" for all flagged moves a week later (with the sample ending 6 November), and 27 moves in the table. **A month later** shows only the moves old enough
- [ ] Hovering a bar shows its count; **Only surprises** leaves 12 moves; the stock filter shows one stock's moves
- [ ] **Refresh prices** shows "Prices updated"; pressing again straight away explains the wait
- [ ] A move without a story: **Check news**, then **Check for updates** on Story updates. It gives "Developed", "No update" or "No newer news" at $0, and the move leaves "Moves you can check"
- [ ] Automatic checks are labelled "automatically: a surprise (reversed within a week)" or "(kept going: as much again within a week)"
- [ ] **Run update now** shows "Checking how past moves played out", and the brief's "Worth watching" line ends with "Past moves: …"
- [ ] `python testenv.py finalize` in another terminal: the day's move appears on Follow-through without a reload
- [ ] Ask "Why was AMZN flagged?": the answer says how its last move played out a week later (follow-through), and its latest story update

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
| `python testenv.py alerts` | Prints the simulated Discord alerts (add `--clear` to empty the outbox) |
| `python testenv.py events` | Simulates the daily events-calendar update at the market open |
| `python testenv.py reset` | Deletes the sample data, its search index and the alerts outbox (only files in `market-agent-testenv/data/`). The test watchlist is kept |

**`seed` options**

| Option | Default | Effect |
|---|---|---|
| `--months N` | `2` | How far back the sample goes |
| `--end YYYY-MM-DD` | today | Last day of the sample |
| `--seed N` | `7` | A different, but repeatable, set of sample data |
| `--tickers A,B,C` | the test watchlist (a copy of yours the first time) | Replaces the test watchlist with these tickers (the first 3 main) |
| `--latest intraday` or `--latest final` | `intraday` if the end date is a trading day | Whether the latest day is still live or already final |
| `--reset` | off | Replaces existing sample data |

**`serve` options**

| Option | Effect |
|---|---|
| `--port N` | Use another port (default 8100) |
| `--live-ask` | Real Claude answers questions (section 8) |
| `--live-runs` | Run update now, and the charts, use the real agent and real market data (section 8) |
| `--live-embeddings` | Search and Ask's retrieval use real Voyage AI embeddings (section 8) |
| `--live-alerts` | Run update now sends real Discord alerts about the sample data (section 8) |
| `--live-calendar` | The calendar's Update now uses real Yahoo Finance and Claude (section 8) |
| `--live-search` | The Stocks tab searches and checks stocks with Yahoo Finance (free; section 8) |
| `--live-stories` | Story updates' checks read real Yahoo news with real Claude (section 8) |

**Settings:** set these before `serve` if you need them.

| Variable | Default here | Effect |
|---|---|---|
| `RUN_COOLDOWN_SECONDS` | `15` | Wait between Run now presses (your real app uses 300) |
| `CALENDAR_SCAN_COOLDOWN_SECONDS` | `15` | Wait between the calendar's Update now presses (your real app uses 300) |
| `FOLLOWUP_REFRESH_COOLDOWN_SECONDS`, `STORY_CHECK_COOLDOWN_SECONDS` | `15` | Wait between **Refresh prices** presses, and between story checks (your real app uses 60 and 30) |
| `REPORT_POLL_SECONDS` | `2` | How often the app checks for saves by other programs |
| `MARKET_AGENT_DIR` | `../market-agent` | Where your program is |

---

## 8. Using real Claude, Voyage, Discord or Yahoo (optional)

Offline mode tests everything except Claude's, Voyage's, Discord's and Yahoo's own output. When you want to see real answers over long history, set `ANTHROPIC_API_KEY` in the terminal and start the server with a live option.

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

**Real Discord alerts:**

```bash
python testenv.py serve --live-alerts      # needs DISCORD_WEBHOOK_URL in this terminal
```

Run update now then posts the sample day's alerts to your channel, by the real rules. This is a good way to see the messages before your real ones arrive. **Use a webhook for a test channel**, because the messages contain the simulated sample prices and news. `update` and `finalize` from the command line still write to the outbox.

**A real events calendar:**

```bash
python testenv.py serve --live-calendar     # needs ANTHROPIC_API_KEY and internet
```

The Calendar tab's **Update now** then reads real company calendars and news for your tickers and asks real Claude, saving into the **test** database. It costs a few cents per press. The real events land among the sample ones from today onwards, so you see real data in the calendar without touching your program's database. The daily `python testenv.py events` command stays simulated.

**Real stock search:**

```bash
python testenv.py serve --live-search      # needs internet; free
```

The Stocks tab then searches Yahoo Finance and checks tickers with it, as your real app does. Stocks you add still go into the **test** watchlist, and their prices are simulated like the rest of the sample.

**Real story checks:**

```bash
python testenv.py serve --live-stories     # needs ANTHROPIC_API_KEY and internet
```

**Check for updates** then reads Yahoo's real newest headlines for the stock and asks real Claude, saving into the **test** database. Each check costs a few cents (never more than $0.10). The sample's moves and explanations are fictional, so most real checks say "No update": this is for seeing how real headlines, verdicts and costs look. Automatic checks after `finalize` stay simulated.

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

Expect `33 passed`. They use temporary databases and watchlists, so they don't change your sample data.

| Test | Proves that |
|---|---|
| `test_calendar_follows_nyse_rules` | Holidays (Good Friday, observed July 4th, Labor Day, Thanksgiving) and early closes are correct |
| `test_sample_covers_two_months_of_trading_days` | The range runs from the first trading day two months back to the end date, weekdays only |
| `test_reports_were_stored_as_in_real_use` | 42 final reports, one never-finalized day plus a live today, revisions from real intraday updates, and realistic timestamps across the two months |
| `test_final_reports_are_permanent` | The real database protections apply to sample data too |
| `test_flagged_tickers_follow_the_flagging_rule` | Every flagged ticker meets the real threshold (z-score of ±2, or 2× volume) |
| `test_every_earnings_day_is_flagged_with_a_source` | Each ticker's earnings day is flagged, with a news source |
| `test_briefs_follow_the_agent_template` | Every brief has the same sections as your agent's (now including "Coming up"), and the sample-data notice |
| `test_sample_reports_include_sector_and_market_context` | Every flagged move has a benchmark, verdict and sentence; all four kinds appear; earnings days read stock-specific, market-wide days market-wide, and sector-move days sector-wide; every brief has a market backdrop; the sample uses the real program's sector ETFs |
| `test_same_settings_give_the_same_data` | Seeding is repeatable, and `--seed` changes it |
| `test_app_serves_two_months_of_reports` | Your real API serves all 44 days, pages through the 43 earlier ones, and returns two months of ticker history |
| `test_offline_run_now_updates_the_latest_day` | Run now works offline: progress steps, a newer update 15 minutes later, $0 |
| `test_offline_run_now_skips_once_the_day_is_final` | After finalizing, Run now is skipped, as in real use |
| `test_offline_ask_answers_from_the_sample_data` | Offline answers list a ticker's flagged days, at $0 |
| `test_charts_show_the_simulated_prices` | Charts get a full year of simulated prices for each range; a flagged day's close matches its report, and today's last point matches today's intraday move |
| `test_search_over_two_months_of_sample_data` | Search finds every earnings day by keyword ("quarterly") and by meaning only ("profit"), nonsense finds nothing, and all 44 reports are indexed |
| `test_offline_ask_and_briefs_know_whats_coming_up` | Offline Ask gives a ticker's next calendar event, cited as (calendar), and the latest brief's "Coming up" lists it |
| `test_offline_ask_shows_the_passages_it_retrieved` | Offline Ask lists the passages retrieval found, including meaning-based ones |
| `test_simulated_alerts_follow_the_real_rules` | `update` alerts the newly flagged ticker once, a second `update` doesn't repeat it, `finalize` sends one summary (ending with the week ahead from the calendar), and a skipped run sends nothing |
| `test_offline_mode_never_contacts_discord` | With `DISCORD_WEBHOOK_URL` set and any connection to Discord made to fail, Run now still "sends" its alert, to the outbox, and calls the market backdrop tool |
| `test_calendar_has_two_months_of_history_and_whats_coming` | Every sample earnings day is on the calendar. All three kinds are upcoming, including an unconfirmed date. News events cite sample articles, previews are attached to earnings dates, and nothing is doubled despite weekly scans |
| `test_offline_calendar_update_now` | The calendar's "today" is the sample's; **Update now** works offline at $0 without doubling anything; `events` (the daily update) works too |
| `test_update_and_finalize_simulate_scheduled_runs` | `update` and `finalize` follow the real storage rules and keep the search index current |
| `test_the_test_environment_has_its_own_watchlist` | Seeding writes `data/watchlist.txt` (first 3 main) and points your program's code at it; a new one copies your real list; an existing one is kept, unless `--tickers` replaces it |
| `test_find_stocks_offline` | The offline search, through your real `watchlist.py`: Costco but not its Mexican listing, Apple but not its German one, no Bitcoin, and ETFs |
| `test_add_star_and_remove_stocks_in_the_test_environment` | Through your real API: adding Costco as main (with its earnings date straight away), its figures after the next run, its chart, the real rules for crypto, unknown tickers and doubles, unstar and remove, and the next report leaving it out. **Your `market-agent/watchlist.txt` is unchanged** |
| `test_reseeding_gives_added_stocks_history` | `status` lists added stocks; `reset` keeps the test watchlist; reseeding gives an added stock all 44 days |
| `test_added_stocks_leave_the_rest_of_the_sample_unchanged` | Adding stocks doesn't change any existing stock's prices, news days or flags, or the calendar's events; the same stock always gets the same prices |
| `test_follow_through_over_two_months` | Every move flagged in a final report is followed up; moves 20 trading days old are settled; all three outcomes appear; every surprise was checked once, for free, with a link to its follow-up article |
| `test_offline_refresh_and_story_check` | **Refresh prices** and **Check for updates** work offline through your real API, at $0 |
| `test_offline_run_now_checks_past_moves_and_finalize_follows_up` | Run now calls `past_moves` and the brief mentions past moves; `finalize` follows up the new day's moves |
| `test_offline_ask_knows_how_moves_played_out` | Offline Ask gives a stock's last move's follow-through and its latest story update, and the overall patterns for general questions |
| `test_refuses_to_use_the_main_projects_database` | Pointing it at a database inside `market-agent/` is refused |
| `test_main_project_was_not_touched` | **Every file in `market-agent/` is unchanged** after all of the above. No `__pycache__` folders were created, and no search index or alerts outbox was written there |

**How this was checked before writing this guide:**

- **The suite catches mistakes.** With the safeguard that stops `__pycache__` folders deliberately switched off, the last test failed, as it should.
- **It works in a real browser.** The real `testenv.py serve` command was driven in Chromium over two months of sample data. These all worked: the 3-day preview, 43 days of history with paging and month grouping, the never-finalized day, an earnings day, offline Run now, offline Ask, and `update` and `finalize` from another terminal appearing live. There were no browser errors.
- **Your program stayed untouched.** Afterwards, every file in the program's folder was byte-for-byte unchanged.
- **It scales.** A 12-month seed (252 trading days) took under a second.
- **Search works in it.** The search box and Ask's retrieval were checked in a browser over the sample data (RAG guide, section 9.2). Again, the main project was unchanged afterwards.
- **Sector context and alerts work in it.** In a browser over the sample data:
  - The Vs. sector column and backdrop showed.
  - Run update now showed "Checking the market and sectors" and "Discord: sent flag alert: MSFT", and the status line updated.
  - The message was in the outbox.
  - An older sector-wide day showed its verdict.
  - Phone width and dark mode worked, with no browser errors.

  The main project was unchanged afterwards.
- **The calendar connections work in it.** In a browser over the sample, 7 checks passed with no browser errors:
  - the Today tab's card and its links
  - the brief's "Coming up"
  - the new Ask example
  - "Checking the events calendar" during a run
  - phone width and dark mode

  Every earlier browser check still passes too.
- **The events calendar works in it.** In a browser over the sample, all 8 checks passed with no browser errors:
  - the month view and a day's page
  - an unconfirmed earnings date
  - empty days, links to days and Back
  - Update now with its progress and cooldown
  - the keyboard
  - phone width
  - dark mode

  The earlier Today, Previous days, chart, search and alerts checks also still pass.
- **Tracked stocks work in it.** In a browser over the sample, 13 checks passed with no browser errors: the Today tab's main stocks and "N more" note, the Stocks tab's groups and counts, offline search (Costco yes, Bitcoin no), Track as main with its earnings date, "Also flagged" after unstarring, the new stock's figures after Run update now, its chart and calendar link, Remove with Keep, a hand edit showing up live, phone width and dark mode. Your real `watchlist.txt` was unchanged afterwards, and every earlier browser check still passes.
- **Follow-through and story updates work in it.** In a browser over the sample, 13 checks passed with no browser errors: the patterns and horizons, bar tooltips, the table's filters, a ticker's chart, Refresh prices and its cooldown, Check news through to an update, automatic checks labelled, the row linking to its update, past moves in a run's brief, Ask's follow-through lines, a `finalize` from another terminal appearing live, phone width and dark mode. Every earlier browser check still passes.
- **Charts work in it.** The chart was driven in a browser over the sample data, covering markers, ranges, hover, keyboard, opening reports from markers, phone width and dark mode. Afterwards, the main project was again unchanged by the test environment.

---

## 10. Keeping it in step with your program

| When you… | Do this in the test environment |
|---|---|
| Change Python code in `market-agent/` | Restart `serve`. It always uses your current code |
| Change the frontend | `python testenv.py build-frontend`, then restart `serve` |
| Change how reports are stored (`reports_db.py`) or split into passages (`search_index.py`) | `python testenv.py seed --reset`, so the sample database and search index are rebuilt |
| Change the verdict rules or sentences (`describe_context` in `market_tools.py`) | `python testenv.py seed --reset`: verdicts are saved with each sample report |
| Change `alerts.py` | Restart `serve`. To try alerts from scratch, `seed --reset` (the alert log lives in the sample database) |
| Change `events.py` (for example its checks or how it saves) | `python testenv.py seed --reset`, so the calendar history is rebuilt with the new rules |
| Change your real watchlist and want it here too | Delete `data/watchlist.txt`, then `python testenv.py seed --reset`. It copies your real list again |
| Add stocks on the test Stocks tab and want them to have history | `python testenv.py seed --reset`. The test watchlist is kept |
| Want "today" to match the real date | `python testenv.py seed --reset` |
| Change how moves are judged (`followups.py`) or checked (`stories.py`) | `python testenv.py seed --reset`, so the follow-through and story updates are worked out again |
| Have a live demo on GitHub Pages (`market-agent-demo.md`) | It makes its own copy of this sample. After changing your program, run `python demo.py build` then `python demo.py publish` in `market-agent-demo/` |
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
| `no such column: move_read` from `status` | The sample data is from before sector context. Run `python testenv.py seed --reset`. |
| No "simulated Discord" note after `update` | Nothing new to alert: those tickers were already alerted today, or nothing is flagged. See `python testenv.py alerts`, or `seed --reset` to start again. |
| The Follow-through tab is empty, or Story updates has none | The sample data is from before follow-through. Run `python testenv.py seed --reset`. |
| The Calendar tab says "Not updated yet" | The sample data is from before the calendar. Run `python testenv.py seed --reset`. |
| The Stocks tab doesn't match your real `watchlist.txt` | By design: the test environment has its own copy. To copy yours again, delete `data/watchlist.txt` and run `python testenv.py seed --reset`. |
| A stock you added stays at "first report next run" | Press **Run update now** or run `python testenv.py update`. If the latest day is already final, `python testenv.py seed --reset` gives it history instead. |
| Search can't find a company | The offline search only knows its built-in list (`STOCK_UNIVERSE` in `sample_market.py`). Add it there, or use `serve --live-search`. |
| `--live-alerts` sends nothing | `DISCORD_WEBHOOK_URL` isn't set in that terminal. The run log shows a warning if sending failed. |
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

Prices are built from a market move, a move for each sector, and each company's own
move, so the sample has stock-specific, sector-wide and market-wide days. Verdicts on
those (and the market backdrop line) use the real program's rules from market_tools.py.

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
    "COST": (0.012, 900.0), "WMT": (0.011, 95.0), "KO": (0.009, 70.0), "NFLX": (0.024, 1100.0), "AMD": (0.032, 150.0),
}
DEFAULT_PROFILE = (0.020, 100.0)

# Sector ETFs, as in the real program (market_tools.ETF_NAMES), and the sector of common tickers
SECTOR_NAMES = {
    "XLK": "Technology", "XLF": "Financials", "XLV": "Health Care", "XLE": "Energy", "XLI": "Industrials",
    "XLC": "Communication Services", "XLU": "Utilities", "XLY": "Consumer Discretionary",
    "XLP": "Consumer Staples", "XLB": "Materials", "XLRE": "Real Estate",
}
SECTORS = {"AAPL": "XLK", "MSFT": "XLK", "NVDA": "XLK", "AMZN": "XLY", "TSLA": "XLY",
           "JPM": "XLF", "GOOGL": "XLC", "META": "XLC",
           "COST": "XLP", "WMT": "XLP", "KO": "XLP", "PEP": "XLP", "DIS": "XLC", "NFLX": "XLC", "GOOG": "XLC",
           "AMD": "XLK", "INTC": "XLK", "AVGO": "XLK", "ORCL": "XLK", "CRM": "XLK", "ADBE": "XLK",
           "BRK-B": "XLF", "V": "XLF", "MA": "XLF", "BAC": "XLF", "XOM": "XLE", "UNH": "XLV",
           "HD": "XLY", "NKE": "XLY", "SBUX": "XLY"}  # anything else gets a sector picked from its name

PUBLISHERS = ["Sample Wire", "Demo Markets Daily", "Example Financial News"]  # fictional
NAMES = {"AAPL": "Apple Inc.", "MSFT": "Microsoft Corporation", "NVDA": "NVIDIA Corporation", "AMZN": "Amazon.com, Inc.",
         "JPM": "JPMorgan Chase & Co.", "GOOGL": "Alphabet Inc.", "META": "Meta Platforms, Inc.", "TSLA": "Tesla, Inc."}
SHORT_NAMES = {"AAPL": "Apple", "MSFT": "Microsoft", "NVDA": "Nvidia", "AMZN": "Amazon", "JPM": "JPMorgan",
               "GOOGL": "Alphabet", "META": "Meta", "TSLA": "Tesla"}  # as headlines write them
DIVIDEND_PAYERS = {"AAPL", "MSFT", "JPM", "GOOGL", "META", "COST", "WMT", "KO", "PEP"}

# What Yahoo Finance's search knows in the test environment: (symbol, name, quoteType, exchange).
# Prices for these are simulated like the rest. The last few can't be tracked (listed outside the
# US, crypto, an index, a future, a mutual fund), so the Stocks tab's filtering can be tested too.
STOCK_UNIVERSE = [
    ("AAPL", "Apple Inc.", "EQUITY", "NASDAQ"), ("MSFT", "Microsoft Corporation", "EQUITY", "NASDAQ"),
    ("NVDA", "NVIDIA Corporation", "EQUITY", "NASDAQ"), ("AMZN", "Amazon.com, Inc.", "EQUITY", "NASDAQ"),
    ("JPM", "JPMorgan Chase & Co.", "EQUITY", "NYSE"), ("GOOGL", "Alphabet Inc.", "EQUITY", "NASDAQ"),
    ("GOOG", "Alphabet Inc.", "EQUITY", "NASDAQ"), ("META", "Meta Platforms, Inc.", "EQUITY", "NASDAQ"),
    ("TSLA", "Tesla, Inc.", "EQUITY", "NASDAQ"), ("COST", "Costco Wholesale Corporation", "EQUITY", "NASDAQ"),
    ("WMT", "Walmart Inc.", "EQUITY", "NYSE"), ("KO", "The Coca-Cola Company", "EQUITY", "NYSE"),
    ("PEP", "PepsiCo, Inc.", "EQUITY", "NASDAQ"), ("DIS", "The Walt Disney Company", "EQUITY", "NYSE"),
    ("NFLX", "Netflix, Inc.", "EQUITY", "NASDAQ"), ("AMD", "Advanced Micro Devices, Inc.", "EQUITY", "NASDAQ"),
    ("INTC", "Intel Corporation", "EQUITY", "NASDAQ"), ("AVGO", "Broadcom Inc.", "EQUITY", "NASDAQ"),
    ("BRK-B", "Berkshire Hathaway Inc.", "EQUITY", "NYSE"), ("V", "Visa Inc.", "EQUITY", "NYSE"),
    ("MA", "Mastercard Incorporated", "EQUITY", "NYSE"), ("BAC", "Bank of America Corporation", "EQUITY", "NYSE"),
    ("XOM", "Exxon Mobil Corporation", "EQUITY", "NYSE"), ("UNH", "UnitedHealth Group Incorporated", "EQUITY", "NYSE"),
    ("HD", "The Home Depot, Inc.", "EQUITY", "NYSE"), ("NKE", "NIKE, Inc.", "EQUITY", "NYSE"),
    ("SBUX", "Starbucks Corporation", "EQUITY", "NASDAQ"), ("ORCL", "Oracle Corporation", "EQUITY", "NYSE"),
    ("CRM", "Salesforce, Inc.", "EQUITY", "NYSE"), ("ADBE", "Adobe Inc.", "EQUITY", "NASDAQ"),
    ("SPY", "SPDR S&P 500 ETF Trust", "ETF", "NYSEArca"), ("QQQ", "Invesco QQQ Trust, Series 1", "ETF", "NASDAQ"),
    ("SMH", "VanEck Semiconductor ETF", "ETF", "NASDAQ"), ("VTI", "Vanguard Total Stock Market Index Fund ETF", "ETF", "NYSEArca"),
    ("XLK", "Technology Select Sector SPDR Fund", "ETF", "NYSEArca"),
    ("COST.MX", "Costco Wholesale Corporation", "EQUITY", "Mexico"), ("APC.DE", "Apple Inc.", "EQUITY", "XETRA"),
    ("BTC-USD", "Bitcoin USD", "CRYPTOCURRENCY", "CCC"), ("^GSPC", "S&P 500", "INDEX", "SNP"),
    ("ES=F", "E-Mini S&P 500 Dec 26", "FUTURE", "Chicago Mercantile Exchange"),
    ("VFIAX", "Vanguard 500 Index Fund Admiral Shares", "MUTUALFUND", "Nasdaq"),
]
_UNIVERSE = {symbol: (name, kind, exchange) for symbol, name, kind, exchange in STOCK_UNIVERSE}


def search_quotes(query: str, limit: int = 15) -> list[dict]:
    """What yfinance's Search(...).quotes would return: ticker matches first, then name matches."""
    q = " ".join(query.lower().split())
    ranked = []
    for order, (symbol, name, kind, exchange) in enumerate(STOCK_UNIVERSE):
        sym, low = symbol.lower(), name.lower()
        rank = (0 if sym == q else 1 if sym.startswith(q) else
                2 if any(word.startswith(q) for word in low.replace(",", " ").split()) or q in low else None)
        if rank is not None:
            ranked.append((rank, order, {"symbol": symbol, "shortname": name, "longname": name, "quoteType": kind,
                                         "typeDisp": kind.title(), "exchDisp": exchange}))
    return [quote for _, _, quote in sorted(ranked, key=lambda r: r[:2])][:limit]


def ticker_info(ticker: str) -> dict:
    """What yfinance's Ticker(...).info would say: a name and type, or nearly nothing for an unknown ticker."""
    if ticker in _UNIVERSE:
        name, kind, _ = _UNIVERSE[ticker]
        return {"quoteType": kind, "longName": name, "shortName": name}
    if ticker in NAMES:
        return {"quoteType": "EQUITY", "longName": NAMES[ticker], "shortName": NAMES[ticker]}
    return {"trailingPegRatio": None}  # what Yahoo gives for a ticker it doesn't know


def sector_of(ticker: str) -> str:
    return SECTORS.get(ticker) or list(SECTOR_NAMES)[zlib.crc32(ticker.encode()) % len(SECTOR_NAMES)]
# Dated events the sample news announces ahead of time (fictional), for the events calendar
UPCOMING = [
    ("product", "{name} to hold product launch event on {when}",
     "{name} said it will unveil new products at an event on {when}."),
    ("court", "Court sets {when} hearing in {name} patent case",
     "A federal judge scheduled a hearing in the patent dispute for {when}."),
    ("investor", "{name} plans investor day for {when}",
     "{name} will present its long-term plans to investors on {when}."),
    ("vote", "{name} shareholders to vote on proposal {when}",
     "Shareholders will vote on the board's proposal at a special meeting on {when}."),
    ("regulator", "Regulator to rule on {name} deal by {when}",
     "A decision on the proposed acquisition is due on {when}, the regulator said."),
]
# Later headlines about a move's story (fictional), for Story updates: by what caused the move
STORY_FOLLOWUPS = {
    ("earnings", 1): ("Analysts raise price targets on {name} after its quarterly results",
                      "Several analysts raised their price targets, citing stronger guidance."),
    ("earnings", -1): ("{name} outlines cost cuts after a weak quarter",
                       "Management said it would cut costs after results missed expectations."),
    ("news", 1): ("{name} follows up on last week's announcement with more detail",
                  "The company gave more detail on the news that lifted its shares."),
    ("news", -1): ("{name} responds to last week's concerns",
                   "The company addressed the concerns that weighed on its shares last week."),
}
CATALYSTS = {
    ("earnings", 1): "Quarterly results beat expectations and guidance was raised.",
    ("earnings", -1): "Quarterly results missed expectations.",
    ("news", 1): ["An analyst upgrade lifted the shares.", "A new product announcement drew buyers.",
                  "Reports of a large contract win."],
    ("news", -1): ["An analyst downgrade weighed on the shares.", "Regulatory concerns were reported.",
                   "A senior executive departure was announced."],
    ("macro", 1): "A broad market rally after economic data.",
    ("macro", -1): "A broad market sell-off after economic data.",
    ("sector", 1): "A sector-wide rally in {sector} stocks.",
    ("sector", -1): "A sector-wide sell-off in {sector} stocks.",
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
        self.tickers = list(dict.fromkeys(t.upper() for t in tickers))  # the stocks the sample was made with
        self.watching = list(self.tickers)  # the stocks simulated runs report on (the test watchlist)
        self.added = []                     # stocks tracked after the sample was made (see add_ticker)
        self.seed = seed
        self.end = end
        self.days = trading_days(months_before(end, months), end)  # the reporting window
        if not self.days:
            raise ValueError("no trading days in that range")
        warmup_start = self.days[0] - timedelta(days=int(WARMUP_DAYS * 1.6))
        warmup = [d for d in trading_days(warmup_start, self.days[0]) if d < self.days[0]][-WARMUP_DAYS:]
        self.all_days = warmup + self.days
        self.index = {d: i for i, d in enumerate(self.all_days)}
        self.early_closes = set().union(*(early_closes(y) for y in {d.year for d in self.days}))
        rng = np.random.default_rng(seed)
        srng = np.random.default_rng(seed + 1000)  # sector moves have their own stream, so adding them
        n, w = len(self.all_days), len(warmup)     # left the rest of the sample (e.g. earnings days) unchanged
        self.warmup = w
        self.sector = {t: sector_of(t) for t in self.tickers}

        market = rng.normal(0, 0.008, n)
        self.events = {}  # (ticker, day) -> (kind, direction)
        self.macro_days = []
        for i in rng.choice(np.arange(w, n), size=max(1, len(self.days) // 20), replace=False):
            direction = int(rng.choice([-1, 1]))
            market[i] = direction * rng.uniform(0.025, 0.035)
            self.macro_days.append((int(i), direction))
            for t in self.tickers:
                self.events[(t, self.all_days[i])] = ("macro", direction)

        # Each sector ETF is the market plus that sector's own move. A few days have a big sector move.
        sector_moves = {etf: srng.normal(0, 0.006, n) for etf in SECTOR_NAMES}
        watched = sorted(set(self.sector.values()))
        sector_days = []
        for i in srng.choice(np.arange(w, n), size=max(1, len(self.days) // 15), replace=False):
            etf, direction = watched[int(srng.integers(len(watched)))], int(srng.choice([-1, 1]))
            sector_moves[etf][i] = direction * srng.uniform(0.025, 0.035)
            sector_days.append((etf, int(i), direction))
        self.etf_returns = {etf: market + move + srng.normal(0, 0.001, n) for etf, move in sector_moves.items()}
        self.etf_returns["SPY"] = market + srng.normal(0, 0.0005, n)
        sector_betas = {t: srng.uniform(0.8, 1.2) for t in self.tickers}
        self.market_moves, self.sector_moves, self.sector_days = market, sector_moves, sector_days

        self.returns, self.volumes, self.closes = {}, {}, {}
        live_ticker = self.tickers[int(rng.integers(len(self.tickers)))]  # gives the latest day a story
        for t in self.tickers:
            strength = self._simulate(t, rng, sector_betas[t], live=t == live_ticker)
            if strength is not None:
                live_strength = strength

        # The latest day's story: a move of 2.6 to 3.4 standard deviations, so it's flagged all day
        if self.events.get((live_ticker, self.all_days[-1])) == ("news", 1):
            r, baseline = self.returns[live_ticker], self.returns[live_ticker][-61:-1]
            r[-1] = baseline.mean() + live_strength * baseline.std(ddof=1)
            self.closes[live_ticker][-1] = self.closes[live_ticker][-2] * (1 + r[-1])

        # The sector-wide days: busy trading, and a headline, for that sector's tickers
        for etf, i, direction in sector_days:
            for t in self.tickers:
                if self.sector[t] == etf and (t, self.all_days[i]) not in self.events:
                    self.volumes[t][i] *= srng.uniform(1.8, 2.6)
                    self.events[(t, self.all_days[i])] = ("sector", direction)

    def _simulate(self, t: str, rng: np.random.Generator, sector_beta: float, live: bool = False) -> float | None:
        """One stock's daily returns, volumes and news days. Returns the size of its latest-day story, if it has one."""
        n, w = len(self.all_days), self.warmup
        vol, start_price = PROFILES.get(t, DEFAULT_PROFILE)
        beta = rng.uniform(0.7, 1.3)
        r = rng.normal(0.0004, vol, n) + beta * self.market_moves + sector_beta * self.sector_moves[self.sector[t]]
        v = rng.uniform(5e6, 6e7) * rng.lognormal(0, 0.2, n)
        for i in range(w, n):
            if (t, self.all_days[i]) in self.events:
                v[i] *= rng.uniform(1.6, 2.4)
        earnings = int(rng.integers(w + 3, n))  # one earnings day per ticker in the window
        direction = int(rng.choice([-1, 1], p=[0.35, 0.65]))
        r[earnings] = direction * rng.uniform(3.2, 5.0) * vol
        v[earnings] *= rng.uniform(2.6, 4.0)
        self.events[(t, self.all_days[earnings])] = ("earnings", direction)
        live_strength = None
        if live and (t, self.all_days[-1]) not in self.events:
            live_strength = rng.uniform(2.6, 3.4)  # sized by the caller, once the whole history is known
            r[-1] = live_strength * vol
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
        return live_strength

    def add_ticker(self, ticker: str) -> None:
        """Simulate a stock that was tracked after the sample was made (added on the Stocks tab).
        It gets its own random stream, so every stock already in the sample stays exactly as it was.
        Past reports don't include it, as in real use: it appears from the next simulated run."""
        t = ticker.upper()
        if t in self.returns:
            return
        rng = np.random.default_rng([self.seed, zlib.crc32(t.encode())])
        self.sector[t] = sector_of(t)
        for i, direction in self.macro_days:
            self.events[(t, self.all_days[i])] = ("macro", direction)
        self._simulate(t, rng, rng.uniform(0.8, 1.2))
        for etf, i, direction in self.sector_days:
            if self.sector[t] == etf and (t, self.all_days[i]) not in self.events:
                self.volumes[t][i] *= rng.uniform(1.8, 2.6)
                self.events[(t, self.all_days[i])] = ("sector", direction)
        self.added.append(t)

    def watch(self, tickers: list[str]) -> None:
        """Report on these stocks from now on (the test watchlist), simulating any new ones."""
        for t in tickers:
            self.add_ticker(t)
        self.watching = [t.upper() for t in tickers]

    # -- figures --------------------------------------------------------------

    @staticmethod
    def _move_z(returns, i: int, fraction: float) -> tuple[float, float]:
        """Day i's move (so far, if fraction < 1) and its z-score against the 60 days before."""
        baseline = returns[i - 60:i]
        move = returns[i] if fraction >= 1 else returns[i] * min(1.0, fraction ** 0.5)  # moves build through the day
        z = (move - baseline.mean()) / (baseline.std(ddof=1) * (1 if fraction >= 1 else fraction ** 0.5))
        return float(move), float(z)

    def figures(self, ticker: str, day: date, fraction: float = 1.0) -> dict:
        """flag_events-style figures for one ticker. fraction < 1 means part-way through the day."""
        i = self.index[day]
        r, v, c = self.returns[ticker], self.volumes[ticker], self.closes[ticker]
        move, z = self._move_z(r, i, fraction)
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

    def context(self, ticker: str, day: date, fraction: float = 1.0) -> dict:
        """The sector and market comparison flag_events adds to a flagged ticker, judged by the real rules."""
        import market_tools  # from the main project (the test environment puts it on the path)
        i, etf = self.index[day], self.sector[ticker]
        own, spy = self.returns[ticker], self.etf_returns["SPY"]
        move, _ = self._move_z(own, i, fraction)
        bench, _ = self._move_z(self.etf_returns[etf], i, fraction)
        market, market_z = self._move_z(spy, i, fraction)
        gap, gap_z = self._move_z(own - self.etf_returns[etf], i, fraction)
        _, sector_vs_market_z = self._move_z(self.etf_returns[etf] - spy, i, fraction)
        return market_tools.describe_context(
            ticker, round(move * 100, 2), etf, SECTOR_NAMES[etf], bench * 100, market * 100, gap * 100, gap_z,
            sector_vs_market_z, market_z, fraction < 1)

    def backdrop(self, day: date, fraction: float = 1.0) -> str:
        """What market_backdrop's summary would say."""
        import market_tools
        i = self.index[day]
        rows = []
        for etf in ["SPY", *SECTOR_NAMES]:
            move, z = self._move_z(self.etf_returns[etf], i, fraction)
            rows.append({"ticker": etf, "name": SECTOR_NAMES.get(etf, "S&P 500"),
                         "return_1d_pct": round(move * 100, 2), "return_zscore": round(z, 2)})
        sectors = sorted(rows[1:], key=lambda r: r["return_1d_pct"], reverse=True)
        return market_tools.describe_backdrop(rows[0], sectors, fraction < 1)

    def scan(self, day: date, as_of: str | None = None, fraction: float = 1.0) -> dict:
        """The same shape as the real flag_events() result."""
        flagged, quiet = [], []
        for t in self.watching:
            f = self.figures(t, day, fraction)
            if abs(f["return_zscore"]) >= 2 or f["volume_vs_avg"] >= 2:
                f["context"] = self.context(t, day, fraction)
                flagged.append(f)
            else:
                price = {k: f[k] for k in ("last_close", "last_price") if k in f}
                quiet.append({"ticker": t, **price, "return_1d_pct": f["return_1d_pct"]})
        status = "complete" if fraction >= 1 else "in_progress"
        session = {"status": status, "as_of": as_of or day.isoformat()}
        # "backdrop" and "coming_up" aren't part of flag_events: they're what market_backdrop and
        # upcoming_events would say, for the brief
        return {"session": session, "flagged": flagged, "quiet": quiet, "errors": [],
                "backdrop": self.backdrop(day, fraction), "coming_up": self.coming_up(day)}

    # -- news and briefs --------------------------------------------------------

    def catalyst(self, ticker: str, day: date) -> str | None:
        event = self.events.get((ticker, day))
        if not event:
            return None
        text = CATALYSTS[event]
        if isinstance(text, list):
            text = text[(day.toordinal() + len(ticker)) % len(text)]
        return text.format(sector=SECTOR_NAMES[self.sector[ticker]].lower())

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

    def follow_up_article(self, ticker: str, day: date) -> dict | None:
        """The later headline about one day's story, if it has one: most company-news and earnings
        moves get one, published 2 to 6 days later. Some don't, so "no newer headlines" happens too."""
        event = self.events.get((ticker, day))
        if event not in STORY_FOLLOWUPS:
            return None
        n = zlib.crc32(f"later{ticker}{day}".encode())
        if n % 4 == 0:
            return None
        published = day + timedelta(days=2 + n % 5)
        title, summary = STORY_FOLLOWUPS[event]
        return {"title": f"{ticker}: {title.format(name=SHORT_NAMES.get(ticker, ticker))}",
                "publisher": PUBLISHERS[n % len(PUBLISHERS)], "published": f"{published}T14:00:00Z", "summary": summary,
                "url": f"https://news.example.com/{published}/{ticker.lower()}-follow-up-{day}"}

    def later_news(self, ticker: str, as_of: date) -> list[dict]:
        """What get_news would return on a given day: the follow-up headlines of the last two months, newest first."""
        found = [a for (t, d) in self.events if t == ticker and 0 < (as_of - d).days <= 62
                 if (a := self.follow_up_article(t, d)) and a["published"][:10] <= as_of.isoformat()]
        return sorted(found, key=lambda a: a["published"], reverse=True)[:10]

    def brief(self, scan: dict, day: date, past: dict | None = None) -> str:
        """A brief in the same format as analyst_prompt.md asks the agent for."""
        session = scan["session"]
        intraday = session["status"] == "in_progress"
        lines = [f"# {'Intraday update' if intraday else 'Watchlist brief'}: {session['as_of']}", ""]
        if intraday:
            lines += [f"Market open: figures are as of {session['as_of']} and can change before the close.", ""]
        lines += ["*Sample data for the test environment: prices and news are simulated.*", ""]
        if day in self.early_closes:
            lines += ["Early close today: the market shut at 1pm.", ""]
        lines += ["## Market backdrop", "", scan["backdrop"], "", "## Notable moves", ""]
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
                f"- **Vs. sector and market:** {m['context']['summary']}",
            ]
            news = self.news(m["ticker"], day)
            if news:
                lines.append(f"- **Likely why:** {news[0]['summary']} [{news[0]['publisher']}]({news[0]['url']})")
            else:
                lines.append("- **Likely why:** No clear catalyst found.")
            history = (past or {}).get(m["ticker"]) or {}
            extra = f" Past moves: {history['summary']}." if history.get("worth_mentioning") and history.get("summary") else ""
            lines += [f"- **Worth watching:** whether the move holds into the next session.{extra}", ""]
        quiet = ", ".join(f"{q['ticker']} ({q['return_1d_pct']:+.2f}%)" for q in scan["quiet"])
        lines += ["## Quiet", "", quiet or "None.", ""]
        lines += ["## Coming up", ""]
        lines += [f"- {line}" for line in scan["coming_up"]] or ["Nothing on the calendar for the next week."]
        lines.append("")
        return "\n".join(lines)

    def price_history(self, ticker: str, period: str) -> list[dict]:
        """Daily closes in the same shape as prices.fetch_prices(), ending on the latest sample day."""
        sessions = {"1mo": 21, "3mo": 63, "6mo": 126, "1y": 252}[period]
        start = len(self.all_days) - sessions
        return [{"date": self.all_days[i].isoformat(), "close": round(float(self.closes[ticker][i]), 2),
                 "volume": int(self.volumes[ticker][i])} for i in range(start, len(self.all_days))]

    # -- the events calendar ------------------------------------------------------

    def company(self, ticker: str) -> str:
        return NAMES.get(ticker) or (_UNIVERSE.get(ticker) or (None,))[0] or f"{ticker} Holdings Inc."

    def _calendar_rng(self, ticker: str) -> np.random.Generator:
        return np.random.default_rng(zlib.crc32(f"calendar{ticker}{self.days[0]}".encode()))

    def calendar(self, ticker: str, as_of: date) -> dict:
        """What yfinance's Ticker.calendar would say on a given day: the next earnings date
        (quarterly, from the sample's earnings day) and, for dividend payers, the next ex-dividend date."""
        rng = self._calendar_rng(ticker)
        earnings_day = next(d for (t, d), (kind, _) in self.events.items() if t == ticker and kind == "earnings")
        quarters = [earnings_day + timedelta(days=91 * k) for k in range(-1, 6)]
        upcoming = [d for d in quarters if d >= as_of]
        cal = {}
        if upcoming:
            nxt = upcoming[0]
            # Like Yahoo: a window until the company confirms (here: unconfirmed until 3 weeks before)
            cal["Earnings Date"] = [nxt] if (nxt - as_of).days <= 21 or rng.random() < 0.5 else [nxt, nxt + timedelta(days=5)]
            eps = round(float(rng.uniform(0.8, 5.0)), 2)
            cal.update({"Earnings Average": eps, "Earnings Low": round(eps * 0.92, 2), "Earnings High": round(eps * 1.07, 2)})
        if ticker in DIVIDEND_PAYERS:
            first = self.days[0] + timedelta(days=int(rng.integers(5, 60)))
            ex_dates = [first + timedelta(days=91 * k) for k in range(-1, 6)]
            ex = next(d for d in ex_dates if d >= as_of)
            ex -= timedelta(days=max(0, ex.weekday() - 4))  # a weekday
            if ex < as_of:
                ex = next(d for d in ex_dates if d > ex + timedelta(days=7))
            cal["Ex-Dividend Date"], cal["Dividend Date"] = ex, ex + timedelta(days=7)
        return cal

    def planned_events(self) -> list[dict]:
        """About two news-announced events a week, from the start of the sample to two months past its end."""
        rng = np.random.default_rng(zlib.crc32(f"planned{self.days[0]}{len(self.tickers)}".encode()))
        days = trading_days(self.days[0], self.end + timedelta(days=60))
        planned = []
        for i in range(0, len(days), 3):
            event_day = days[min(len(days) - 1, i + int(rng.integers(0, 3)))]
            ticker = self.tickers[int(rng.integers(len(self.tickers)))]
            kind, title, summary = UPCOMING[int(rng.integers(len(UPCOMING)))]
            announced = event_day - timedelta(days=int(rng.integers(5, 21)))
            name = SHORT_NAMES.get(ticker, ticker)
            when = f"{event_day:%B} {event_day.day}"
            planned.append({"ticker": ticker, "date": event_day, "announced": announced, "kind": kind,
                            "headline": title.format(name=name, when=when), "summary": summary.format(name=name, when=when),
                            "title": {"product": "Product launch event", "court": "Court hearing in patent case",
                                      "investor": "Investor day", "vote": "Shareholder vote",
                                      "regulator": "Regulator's decision on deal"}[kind]})
        return planned

    def coming_up(self, day: date) -> list[str]:
        """What upcoming_events' this_week lines would say on a given day: the next 7 days of
        earnings and ex-dividend dates, and news events announced by then."""
        import events  # the real program's line format (the test environment puts it on the path)
        soon = []
        for t in self.watching:
            company = events.short_name(self.company(t))
            cal = self.calendar(t, day)
            if cal.get("Earnings Date"):
                window = len(cal["Earnings Date"]) > 1
                soon.append((cal["Earnings Date"][0], t, company,
                             "Earnings report (date not confirmed)" if window else "Earnings report"))
            if cal.get("Ex-Dividend Date"):
                soon.append((cal["Ex-Dividend Date"], t, company, "Ex-dividend date"))
        soon += [(e["date"], e["ticker"], events.short_name(self.company(e["ticker"])), e["title"])
                 for e in self.planned_events() if e["announced"] <= day and e["ticker"] in self.watching]
        soon = sorted(item for item in soon if day <= item[0] <= day + timedelta(days=7))
        return [events.event_line({"event_date": d.isoformat(), "ticker": t, "company": c, "title": title})
                for d, t, c, title in soon]

    def event_articles(self, ticker: str, as_of: date) -> list[dict]:
        """What get_news would return on a given day: announcements of upcoming events (made in the
        last two weeks), a preview of upcoming earnings, and the past week's catalyst headlines."""
        articles = []
        for e in self.planned_events():
            if e["ticker"] == ticker and e["announced"] <= as_of < e["date"] and (as_of - e["announced"]).days <= 21:
                articles.append({"title": f"{ticker}: {e['headline']}", "publisher": PUBLISHERS[e["date"].day % 3],
                                 "published": f"{e['announced']}T13:30:00Z", "summary": e["summary"],
                                 "url": f"https://news.example.com/{e['announced']}/{ticker.lower()}-{e['kind']}-{e['date']}"})
        earnings = self.calendar(ticker, as_of).get("Earnings Date")
        if earnings and (earnings[0] - as_of).days <= 14:
            articles.append({"title": f"{ticker}: what to expect from quarterly results", "publisher": PUBLISHERS[0],
                             "published": f"{as_of}T12:00:00Z",
                             "summary": "Analysts will watch guidance and margins when the company reports.",
                             "url": f"https://news.example.com/{as_of}/{ticker.lower()}-earnings-preview"})
        recent = [d for d in self.days if as_of - timedelta(days=7) <= d <= as_of]
        for d in recent:
            articles += self.news(ticker, d)
        return articles[:10]

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
    python testenv.py alerts            show the Discord alerts the simulated runs "sent"
    python testenv.py events            simulate the daily events-calendar update at the market open
    python testenv.py reset             delete the sample data (your test watchlist is kept)

Search (RAG) works offline too: a simulated stand-in for Voyage AI ranks passages by
topic. Use `serve --live-embeddings` to try real Voyage embeddings on the sample data.

Discord alerts follow the real rules but are written to data/alerts_outbox.jsonl instead
of being sent, even if DISCORD_WEBHOOK_URL is set. Use `serve --live-alerts` to really send.

The events calendar is filled from simulated company calendars and sample news, read by a
stand-in for Claude, and checked and saved by your real events.py. `serve --live-calendar`
uses real Yahoo Finance and Claude instead.

The test environment has its own watchlist, data/watchlist.txt, copied from the main project's
when you first seed. Finding, adding, starring and removing stocks on the Stocks tab edit that
copy, never the real one. Search finds stocks from a built-in list (no internet);
`serve --live-search` uses Yahoo Finance's real search. A stock you add is simulated from the
next run on, like real use; `seed --reset` gives it two months of history too.

Follow-through (the price after each flagged move) uses the simulated prices, and Story updates
read simulated later headlines with a stand-in for Claude. `serve --live-stories` checks stories
with real Yahoo news and Claude instead.
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
OUTBOX_NAME = "alerts_outbox.jsonl"  # where simulated Discord alerts go, next to the database
FRONTEND_DIST = HERE / "frontend-dist"
PORT = 8100
ET = ZoneInfo("America/New_York")
DEFAULT_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]

from sample_market import SampleMarket, search_quotes, ticker_info, trading_days  # noqa: E402  (after the bytecode setting)


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
    import market_tools
    market_tools.WATCHLIST_FILE = watchlist_path(db_path)  # the test watchlist: the Stocks tab never edits the real one
    return reports_db


def watchlist_path(db_path: Path = DB_PATH) -> Path:
    """The test environment's own watchlist.txt, next to its database."""
    return Path(db_path).resolve().with_name("watchlist.txt")


def config_path(db_path: Path) -> Path:
    return Path(db_path).with_name("sample_config.json")


def load_market(db_path: Path = DB_PATH) -> SampleMarket:
    path = config_path(db_path)
    if not path.is_file():
        sys.exit("No sample data yet. Run: python testenv.py seed")
    config = json.loads(path.read_text())
    if not watchlist_path(db_path).is_file():  # sample data made before the test environment had its own
        make_test_watchlist(db_path, config["tickers"])
    market = SampleMarket(config["tickers"], date.fromisoformat(config["end"]), config["months"], config["seed"])
    follow_watchlist(market, db_path)
    return market


def follow_watchlist(market: SampleMarket, db_path: Path = DB_PATH) -> SampleMarket:
    """Simulate the stocks on the test watchlist right now: added ones join, removed ones leave.
    The stocks already in the sample keep exactly the same data."""
    path = watchlist_path(db_path)
    tickers = read_tickers(path) if path.is_file() else []
    market.watch(tickers or market.tickers)
    return market


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


def install_fake_events(events, market, delay: float = 0.0) -> None:
    """The events calendar over the sample: simulated company calendars and news, and a free stand-in
    for Claude that reports the sample's planned events. Your real events.py still checks every one
    (watchlist ticker, a real article, a date in range) and saves them by its normal rules.
    delay slows each step a little, so "Update now" shows its progress like a real update."""
    import re
    import time as clock_time
    clock = {"today": market.end}  # the sample's "today"; seeding moves it back to fill in history

    def fake_news(ticker):
        clock_time.sleep(delay)
        market.add_ticker(ticker)  # a stock added on the Stocks tab (nothing changes for the others)
        return market.event_articles(ticker, clock["today"])

    def fake_calendar(ticker):
        market.add_ticker(ticker)
        return market.calendar(ticker, clock["today"])

    def fake_claude(prompt):
        clock_time.sleep(delay * 3)
        numbers = {title: int(n) for n, title in re.findall(r"^\[(\d+)\] .*\n    (.*)$", prompt, re.M)}
        known = re.findall(r"^- id (\d+): (\S+) (\w+) on (\S+): (.*)$", prompt, re.M)
        found = []
        for e in market.planned_events():
            n = numbers.get(f"{e['ticker']}: {e['headline']}")
            if n:
                same = next((int(i) for i, t, kind, _, title in known
                             if t == e["ticker"] and kind == "news" and title == e["title"]), None)
                found.append({"ticker": e["ticker"], "date": e["date"].isoformat(), "title": e["title"],
                              "details": e["summary"], "sources": [n], "same_as": same})
        for title, n in numbers.items():  # an earnings preview: attached to the earnings date
            ticker = title.split(":")[0]
            if title.endswith("what to expect from quarterly results"):
                same = next((int(i) for i, t, kind, *_ in known if t == ticker and kind == "earnings"), None)
                if same:
                    found.append({"ticker": ticker, "date": None, "title": "Earnings preview", "same_as": same,
                                  "details": "Analysts will watch guidance and margins.", "sources": [n]})
        return json.dumps({"events": found}), 0.0

    events.today_et = lambda: clock["today"]
    events.company_name = lambda ticker: events.short_name(market.company(ticker))
    events.fetch_calendar = fake_calendar
    events.fetch_news = fake_news
    events.ask_claude = fake_claude
    events.sample_clock = clock


def simulate_events_scan(db_path: Path = DB_PATH, as_of: date | None = None) -> str:
    """What the daily scan at the market open does, over the sample."""
    connect_main(db_path)
    market = load_market(db_path)
    import events
    install_fake_events(events, market)
    events.sample_clock["today"] = as_of or market.end
    try:
        result = events.scan("scheduled")
    finally:
        events.sample_clock["today"] = market.end
    return (f"{result['status']}: calendar updated as of {as_of or market.end}, "
            f"{result['events_found']} news events from {result['articles']} headlines")


def seed_events(db_path: Path, market) -> None:
    """Fill the calendar as daily use would have: a scan each Monday of the sample, then today."""
    mondays = [d for d in market.days if d.weekday() == 0]
    for day in [*mondays, market.end]:
        simulate_events_scan(db_path, day)


def update_search_index(db_path: Path = DB_PATH, live: bool = False) -> dict:
    """Index the sample reports for search (simulated embeddings unless live)."""
    connect_main(db_path)
    import search_index
    if not live:
        install_fake_embeddings(search_index)
    return search_index.sync()


def read_tickers(path: Path) -> list[str]:
    """The tickers in a watchlist.txt. A line can name a benchmark after the ticker, a * marks
    a main stock, and anything after # is a comment."""
    words = [line.split("#", 1)[0].replace("*", " ").split() for line in path.read_text().splitlines()]
    return [w[0].upper() for w in words if w]


def main_watchlist() -> list[str]:
    """The tickers in the main project's watchlist.txt (only read), or a default set."""
    path = MAIN / "watchlist.txt"
    if path.is_file():
        tickers = read_tickers(path)
        if tickers:
            return tickers
    return DEFAULT_TICKERS


TEST_MAIN_STOCKS = 3  # main stocks in a new test watchlist, so the Today tab shows "N more" too


def make_test_watchlist(db_path: Path = DB_PATH, tickers: list[str] | None = None) -> list[str]:
    """The test environment's own watchlist.txt, which the Stocks tab edits. Kept as it is if it
    already exists (so stocks you added get history when you reseed), unless tickers are given.
    A new one is a copy of the main project's (only read), with the first 3 as main stocks
    if it doesn't star any. Returns its tickers."""
    path = watchlist_path(db_path)
    if path.parent == MAIN or MAIN in path.parents:
        sys.exit(f"Refusing to write a watchlist inside the main project: {path}")
    if path.is_file() and not tickers and read_tickers(path):
        return read_tickers(path)
    real = MAIN / "watchlist.txt"
    if tickers:
        lines = [t.strip().upper() for t in tickers if t.strip()]
    elif real.is_file() and read_tickers(real):
        lines = real.read_text().splitlines()  # benchmarks and comments come along
    else:
        lines = list(DEFAULT_TICKERS)
    if not any("*" in line.split("#", 1)[0] for line in lines):
        starred = 0
        for i, line in enumerate(lines):
            code = line.split("#", 1)[0]
            if code.strip() and starred < TEST_MAIN_STOCKS:
                lines[i] = line.replace(code.strip(), "*" + code.strip(), 1)
                starred += 1
    path.parent.mkdir(parents=True, exist_ok=True)
    header = "# The test environment's watchlist (the Stocks tab edits this copy, never the real one)"
    if not lines or lines[0] != header:
        lines.insert(0, header)
    path.write_text("\n".join(lines) + "\n")
    return read_tickers(path)


# ---------------------------------------------------------------------------
# Discord alerts, simulated
# ---------------------------------------------------------------------------

def outbox_path(db_path: Path = DB_PATH) -> Path:
    return Path(db_path).with_name(OUTBOX_NAME)


def install_fake_alerts(alerts, db_path: Path = DB_PATH) -> None:
    """Alerts follow the real rules and are logged in the test database, but each message is
    written to the outbox file instead of Discord, even if DISCORD_WEBHOOK_URL is set."""
    path = outbox_path(db_path)

    def fake_send(payload):
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"written_at": _as_utc(datetime.now(timezone.utc)), **payload}) + "\n")
        return "offline"

    alerts.send = fake_send
    alerts.enabled = lambda: True


def simulated_alerts(day: date, db_path: Path = DB_PATH) -> str:
    """What a real run does after saving: send any alerts the saved report calls for."""
    connect_main(db_path)
    import alerts
    install_fake_alerts(alerts, db_path)
    outcome = alerts.notify(day.isoformat())
    return f" · simulated Discord: {'; '.join(outcome['sent'])}" if outcome["sent"] else ""


def read_outbox(db_path: Path = DB_PATH) -> list[dict]:
    path = outbox_path(db_path)
    if not path.is_file():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def print_outbox(db_path: Path = DB_PATH) -> None:
    messages = read_outbox(db_path)
    if not messages:
        print("No simulated alerts yet. Try: python testenv.py update   (then finalize)")
    for m in messages:
        print(f"--- {m['written_at']}  {m.get('content', '')}")
        for e in m.get("embeds", []):
            print(f"  {e['title']}")
            for line in e.get("description", "").splitlines():
                print(f"    {line}")


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
    tickers = make_test_watchlist(db_path, tickers)
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
    seed_events(db_path, market)
    for _ in range(10):  # each surprise checked, as the final report a week after it would have done
        if not follow_up(db_path, every_surprise=True)["checks"]:
            break
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
        reads = dict(conn.execute("""SELECT move_read, COUNT(*) FROM report_tickers t JOIN reports r USING (session_date)
                                     WHERE t.category = 'flagged' AND r.status = 'final' GROUP BY move_read"""))
    market = load_market(db_path)
    earnings = sorted((d.isoformat(), t) for (t, d), (kind, _) in market.events.items()
                      if kind == "earnings" and d >= market.days[0])
    sector_days = sorted({d.isoformat() for (t, d), (kind, _) in market.events.items()
                          if kind == "sector" and d >= market.days[0]})
    import alerts
    import search_index
    index = search_index.status()
    import events
    with closing(reports_db.connect(db_path, readonly=True)) as conn:
        logged = len(alerts.recent(conn, 10_000))
        on_calendar = events.events_between(conn, "2000-01-01", "2100-01-01")
        scans = conn.execute("SELECT COUNT(*) FROM event_scans").fetchone()[0] if on_calendar else 0
    upcoming = [e for e in on_calendar if e["event_date"] >= market.end.isoformat()]
    import watchlist
    tracked = watchlist.entries()
    import followups
    with closing(reports_db.connect(db_path, readonly=True)) as conn:
        followed = followups.moves(conn)
        try:
            story_count = conn.execute("SELECT COUNT(*) FROM story_checks WHERE status != 'running'").fetchone()[0]
        except Exception:
            story_count = 0
    return {"database": str(Path(db_path).resolve()), "main_project": str(MAIN), "days": row["days"],
            "first_day": row["first"], "last_day": row["last"], "final": row["final"],
            "intraday": intraday, "flagged_rows": flagged, "simulated_cost_usd": row["cost"],
            "earnings_days": {t: d for d, t in earnings}, "sector_move_days": sector_days,
            "kinds_of_move": reads,
            "search_index": {"reports": index["reports_indexed"], "passages": index["passages"]},
            "alerts": {"logged": logged, "outbox_messages": len(read_outbox(db_path))},
            "calendar": {"upcoming": len(upcoming), "past": len(on_calendar) - len(upcoming), "scans": scans,
                         "next": [f"{e['event_date']} {e['company']}: {e['title']}" for e in upcoming[:4]]},
            "watchlist": {"file": str(watchlist_path(db_path)), "tracked": len(tracked),
                          "main": [e["ticker"] for e in tracked if e["main"]],
                          "added_since_seeding": market.added,
                          "removed_since_seeding": [t for t in market.tickers if t not in market.watching]},
            "follow_through": {"moves": len(followed), "settled": sum(m["settled"] for m in followed),
                               "surprises": sum(m["surprise"] for m in followed), "story_updates": story_count}}


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
        return "skipped: the latest day is already final" + simulated_alerts(market.days[-1], db_path)
    day, as_of, fraction = point
    with closing(reports_db.connect(db_path)) as conn:
        outcome = _save(reports_db, conn, market, day, market.scan(day, as_of, fraction), "intraday",
                        datetime.now(timezone.utc), 0.0)
    update_search_index(db_path)
    return f"{outcome}: intraday report for {day} as of {as_of}" + simulated_alerts(day, db_path)


def simulate_finalize(db_path: Path = DB_PATH) -> str:
    """What the after-close (or next-morning) run does: the latest day's final report."""
    reports_db, market = connect_main(db_path), load_market(db_path)
    day = market.days[-1]
    with closing(reports_db.connect(db_path)) as conn:
        outcome = _save(reports_db, conn, market, day, market.scan(day), "final", datetime.now(timezone.utc), 0.0)
    update_search_index(db_path)
    alerted = simulated_alerts(day, db_path)
    followed = follow_up(db_path)  # as a real final run does, after its alerts
    f = followed["followups"] or {}
    note = (f" · follow-through: {f['added']} new, {f['updated']} updated, {len(followed['checks'])} story checks"
            if f else "")
    return f"{outcome}: final report for {day}{note}{alerted}"


def install_fake_runs(run_brief, reports_db, market, db_path: Path = DB_PATH) -> None:
    """Make "Run update now" use the simulated market instead of Claude and Yahoo Finance."""
    from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage
    plan = {}

    def fake_market_session():
        follow_watchlist(market, db_path)  # like a real run, report on the watchlist as it is now
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
        yield AssistantMessage(content=[ToolUseBlock(id="backdrop", name="mcp__market__market_backdrop", input={})],
                               model="offline-test")
        await asyncio.sleep(0.3)
        yield UserMessage(content=[ToolResultBlock(tool_use_id="backdrop", content=text({"summary": scan["backdrop"]}))])
        yield AssistantMessage(content=[ToolUseBlock(id="calendar", name="mcp__market__upcoming_events", input={})],
                               model="offline-test")
        await asyncio.sleep(0.2)
        yield UserMessage(content=[ToolResultBlock(tool_use_id="calendar", content=text({"this_week": scan["coming_up"]}))])
        past = {}
        if scan["flagged"]:
            import market_tools  # the real tool, reading the sample database
            ask_for = {"tickers": [m["ticker"] for m in scan["flagged"]], "kinds": [m["context"].get("read") for m in scan["flagged"]]}
            yield AssistantMessage(content=[ToolUseBlock(id="past", name="mcp__market__past_moves", input=ask_for)],
                                   model="offline-test")
            past_result = market_tools.past_moves(**ask_for)
            past = past_result.get("moves", {})
            await asyncio.sleep(0.2)
            yield UserMessage(content=[ToolResultBlock(tool_use_id="past", content=text(past_result))])
        for i, m in enumerate(scan["flagged"]):
            yield AssistantMessage(content=[ToolUseBlock(id=f"news{i}", name="mcp__market__get_news",
                                                         input={"ticker": m["ticker"]})], model="offline-test")
            await asyncio.sleep(0.4)
            news = market.news(m["ticker"], day)
            yield UserMessage(content=[ToolResultBlock(tool_use_id=f"news{i}",
                                                       content=[part for n in news for part in text(n)])])
        yield ResultMessage(subtype="success", duration_ms=0, duration_api_ms=0, is_error=False, num_turns=2,
                            session_id="offline-test", total_cost_usd=0.0, result=market.brief(scan, day, past))

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
            import events
            ahead = events.upcoming(conn, events.today_et(), ask.CALENDAR_DAYS, [t])
            if ahead:
                lines.append(f"  Next on the calendar: {events.event_line(ahead[0], company=False)} (calendar).")
            import followups
            import stories
            judged = [m for m in followups.moves(conn, t) if m["outcomes"]["5"]]
            if judged:
                m = judged[0]
                lines.append(f"  After its last judged move ({m['session_date']}, {m['move_pct']:+.2f}%): "
                             f"{m['outcomes']['5']} a week later ({m['after_5d']:+.2f}%) (follow-through).")
            checked = [c for c in stories.latest(conn, t, 5) if c["status"] in ("ok", "no_news")]
            if checked:
                c = checked[0]
                lines.append(f"  Latest story update, on its move of {c['session_date']}: {c['verdict_label']}. "
                             f"{c['update_text']} (story update, {c['finished_at'][:10]}).")
        if not tickers:
            top = conn.execute("""SELECT ticker, COUNT(*) FROM report_tickers WHERE category = 'flagged'
                                  GROUP BY ticker ORDER BY COUNT(*) DESC, ticker LIMIT 3""").fetchall()
            lines.append("Most-flagged tickers in the saved reports: "
                         + (", ".join(f"**{t}** ({n} days)" for t, n in top) or "none yet") + ".")
            import events
            ahead = events.upcoming(conn, events.today_et(), 7)
            if ahead:
                lines += ["", "Next on the calendar (calendar):"] + [f"- {events.event_line(e)}" for e in ahead[:3]]
            import followups
            found = followups.moves(conn)
            if found:
                lines += ["", "How flagged moves played out (follow-through): "
                          + followups.describe_group(followups.patterns(found, 5)["all"], 5) + "."]
    # The retrieval step real answers are built on: the passages that best match the question
    passages = ask.find_passages(question)[:3]
    if passages:
        lines += ["", "Most relevant passages:"]
        lines += [f"- {p['session_date']}: {p['heading']} (matched by {' and '.join(p['matched_by'])})" for p in passages]
    return "\n".join(lines)


def install_fake_prices(prices, reports_db, market, db_path: Path = DB_PATH) -> None:
    """Make the charts show the simulated market instead of downloading prices."""
    def fake_fetch(ticker, period):
        if ticker not in market.returns:
            if ticker not in follow_watchlist(market, db_path).watching:
                return []  # like Yahoo for a ticker it doesn't know
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


def install_fake_search(watchlist) -> None:
    """Finding stocks without the internet: the real watchlist.py (its filtering, checks and
    limits) over a built-in list of stocks and ETFs, instead of Yahoo Finance's search."""
    class FakeSearch:
        def __init__(self, query, max_results=15, **_):
            self.quotes = search_quotes(query, max_results)

    class FakeTicker:
        def __init__(self, ticker):
            self.info = ticker_info(ticker.upper())

    watchlist.yf = type("OfflineYahoo", (), {"Search": FakeSearch, "Ticker": FakeTicker})
    watchlist._search_cache.clear()


def install_fake_followups(followups, stories, reports_db, market, db_path: Path = DB_PATH, live_stories: bool = False) -> None:
    """Follow-through over the simulated prices, and Story updates from simulated later headlines,
    read by a free stand-in for Claude. Your real followups.py and stories.py do everything else."""
    import re

    def last_complete_session():  # the sample's latest finished day
        with closing(reports_db.connect(db_path, readonly=True)) as conn:
            row = conn.execute("SELECT status FROM reports WHERE session_date = ?", (market.days[-1].isoformat(),)).fetchone()
        return market.days[-1] if row and row["status"] == "final" else market.days[-2]

    def fake_claude(prompt):
        """Finds the newer headline that follows up this move's story, as Claude would."""
        ticker = re.search(r"^STOCK: (\S+)$", prompt, re.M).group(1)
        moved = date.fromisoformat(re.search(r"^MOVE: .* on (\d{4}-\d{2}-\d{2}) ", prompt, re.M).group(1))
        story = market.follow_up_article(ticker, moved)
        later = re.findall(r"^\[(\d+)\] (.*?) \| published (\S+)\n    (.*)$", prompt, re.M)
        about = [x for x in later if story and x[3] == story["title"] and x[2] == story["published"]]
        if not about:
            return json.dumps({"verdict": "no_update", "update": "None of the newer headlines is about this move.",
                               "sources": []}), 0.0
        n, publisher, published, title = about[0]
        update = f"On {published[:10]}, {publisher} reported: {title.split(': ', 1)[-1]}."
        return json.dumps({"verdict": "developed", "update": update, "sources": [int(n)]}), 0.0

    followups.last_complete_session = last_complete_session
    if not live_stories:
        stories.fetch_news = lambda ticker: market.later_news(ticker, market.end)
        stories.ask_claude = fake_claude


def follow_up(db_path: Path = DB_PATH, every_surprise: bool = False) -> dict:
    """What happens after each final report: follow-through filled in, and surprises' news checked.
    `every_surprise`: also the sample's older surprises, which real use would have checked in their own week."""
    reports_db, market = connect_main(db_path), load_market(db_path)
    import events
    import followups
    import prices
    import stories
    install_fake_events(events, market)
    install_fake_prices(prices, reports_db, market, db_path)
    install_fake_followups(followups, stories, reports_db, market, db_path)
    return stories.after_final_report(within_days=10_000 if every_surprise else None)


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
             live_embeddings: bool = False, live_alerts: bool = False, live_calendar: bool = False,
             live_search: bool = False, live_stories: bool = False, frontend_dist: Path = FRONTEND_DIST):
    reports_db = connect_main(db_path)
    market = load_market(db_path)
    import alerts
    import api
    import ask
    import events
    import prices
    import run_brief
    import followups
    import search_index
    import stories
    import watchlist
    if not live_search:
        install_fake_search(watchlist)
    install_fake_followups(followups, stories, reports_db, market, db_path, live_stories)
    api.FOLLOWUP_REFRESH_COOLDOWN_SECONDS = int(os.environ.get("FOLLOWUP_REFRESH_COOLDOWN_SECONDS", "15"))
    api.STORY_CHECK_COOLDOWN_SECONDS = int(os.environ.get("STORY_CHECK_COOLDOWN_SECONDS", "15"))
    if not live_embeddings:
        install_fake_embeddings(search_index)
    if not live_alerts:
        install_fake_alerts(alerts, db_path)
    if not live_calendar:
        install_fake_events(events, market, delay=0.3)
    api.CALENDAR_SCAN_COOLDOWN_SECONDS = int(os.environ.get("CALENDAR_SCAN_COOLDOWN_SECONDS", "15"))
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
    outbox_path(db_path).unlink(missing_ok=True)
    print(f"Deleted the sample data in {folder} (kept your test watchlist, {watchlist_path(db_path).name})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Test environment for the market analyst agent.")
    commands = parser.add_subparsers(dest="command", required=True)
    seed = commands.add_parser("seed", help="create sample reports")
    seed.add_argument("--end", type=date.fromisoformat, help="last day of the sample (default: today)")
    seed.add_argument("--months", type=int, default=2, help="how far back the sample goes (default: 2)")
    seed.add_argument("--seed", type=int, default=7, help="change for different (but repeatable) sample data")
    seed.add_argument("--tickers", help="comma-separated; replaces the test watchlist (default: keep it, or copy the main project's)")
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
    serve.add_argument("--live-alerts", action="store_true",
                       help="Run now sends real Discord alerts about the sample data (needs DISCORD_WEBHOOK_URL)")
    serve.add_argument("--live-calendar", action="store_true",
                       help="the calendar's Update now uses real Yahoo Finance and Claude (costs money; saves into the test database)")
    serve.add_argument("--live-search", action="store_true",
                       help="find stocks with Yahoo Finance's real search (free; still edits only the test watchlist)")
    serve.add_argument("--live-stories", action="store_true",
                       help="Story updates' checks read real Yahoo news with real Claude (costs a few cents each)")
    commands.add_parser("update", help="simulate a scheduled intraday run")
    commands.add_parser("finalize", help="simulate the run that writes the latest day's final report")
    commands.add_parser("events", help="simulate the daily events-calendar update")
    outbox = commands.add_parser("alerts", help="show the simulated Discord alerts")
    outbox.add_argument("--clear", action="store_true", help="empty the outbox (the alert log is kept)")
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
        app = make_app(live_ask=args.live_ask, live_runs=args.live_runs, live_embeddings=args.live_embeddings,
                       live_alerts=args.live_alerts, live_calendar=args.live_calendar, live_search=args.live_search,
                       live_stories=args.live_stories)
        live = [name for name, on in (("Claude", args.live_ask or args.live_runs or args.live_calendar or args.live_stories),
                                      ("Voyage", args.live_embeddings), ("Discord", args.live_alerts),
                                      ("Yahoo search", args.live_search)) if on]
        mode = f"LIVE {' + '.join(live)}" if live else "offline (no Claude, no Voyage, no Discord, no cost)"
        print(f"Test environment: http://localhost:{args.port}  ·  {mode}  ·  database {DB_PATH}")
        if not FRONTEND_DIST.is_dir():
            print("No frontend build yet, so only the API is available. Run: python testenv.py build-frontend")
        uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")
    elif args.command == "update":
        print(simulate_update())
    elif args.command == "finalize":
        print(simulate_finalize())
    elif args.command == "events":
        print(simulate_events_scan())
    elif args.command == "alerts":
        if args.clear:
            outbox_path().unlink(missing_ok=True)
            print("Emptied the simulated alerts outbox.")
        else:
            print_outbox()
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
import json
import sqlite3
import sys
import time
from contextlib import closing
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import testenv  # noqa: E402  (sets the no-bytecode rule before anything from the main project loads)
from sample_market import SECTOR_NAMES, SampleMarket, early_closes, nyse_holidays, trading_days  # noqa: E402

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
        assert "## Notable moves" in body and "## Quiet" in body and "## Coming up" in body
        assert "Sample data for the test environment" in body


def test_sample_reports_include_sector_and_market_context(conn):
    import market_tools
    assert SECTOR_NAMES == market_tools.ETF_NAMES  # the sample uses the real program's sector ETFs

    flagged = [dict(r) for r in conn.execute("""SELECT t.*, r.status FROM report_tickers t JOIN reports r
                                                USING (session_date) WHERE t.category = 'flagged'""")]
    assert all(f["benchmark"] and f["move_read"] and f["context_summary"] for f in flagged)
    final_reads = {f["move_read"] for f in flagged if f["status"] == "final"}
    assert {"stock-specific", "sector-wide", "market-wide", "mixed"} <= final_reads

    market = SampleMarket(TICKERS, END)
    reads = {(f["ticker"], f["session_date"]): f["move_read"] for f in flagged if f["status"] == "final"}
    for (ticker, day), (kind, _) in market.events.items():
        key = (ticker, day.isoformat())
        if key in reads and kind == "earnings":
            assert reads[key] == "stock-specific", key   # company news: judged stock-specific
        if key in reads and kind == "macro":
            assert reads[key] == "market-wide", key      # a market-wide day: judged market-wide
        if key in reads and kind == "sector":
            assert reads[key] == "sector-wide", key      # a sector-wide day: judged sector-wide

    for body, in conn.execute("SELECT body_md FROM reports"):
        assert "## Market backdrop" in body and "Strongest sector:" in body
    nvda_rows = [f for f in flagged if f["ticker"] == "NVDA"]
    assert all("its sector (Technology, XLK)" in f["context_summary"] for f in nvda_rows)


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


def test_offline_ask_and_briefs_know_whats_coming_up(db, client, conn):
    response = client(db).post("/api/ask", json={"question": "What's next for MSFT?"})
    done = [line for line in response.text.splitlines() if '"done"' in line][0]
    assert "Next on the calendar: Mon Nov 9: Court hearing in patent case (calendar)" in done

    latest = conn.execute("SELECT body_md FROM reports WHERE session_date = '2026-11-06'").fetchone()[0]
    assert "## Coming up\n\n- Mon Nov 9: Microsoft (MSFT): Court hearing in patent case" in latest


def test_offline_ask_shows_the_passages_it_retrieved(db, client):
    response = client(db).post("/api/ask", json={"question": "Which companies reported profits?"})
    done = [line for line in response.text.splitlines() if '"done"' in line][0]
    assert "Most relevant passages" in done and "matched by meaning" in done


def test_simulated_alerts_follow_the_real_rules(fresh_db):
    first = testenv.simulate_update(fresh_db)   # the latest day's flags haven't been alerted yet
    second = testenv.simulate_update(fresh_db)  # same tickers still flagged: no repeat
    final = testenv.simulate_finalize(fresh_db)
    again = testenv.simulate_update(fresh_db)   # skipped (already final): no second summary

    assert "simulated Discord: flag alert:" in first
    assert "simulated Discord" not in second and "simulated Discord" not in again
    assert final.endswith("simulated Discord: daily summary for 2026-11-06")
    outbox = testenv.read_outbox(fresh_db)
    assert [m["content"].split("**")[1] for m in outbox] == ["1 new flag", "Daily summary:"]
    assert outbox[0]["embeds"][0]["title"].endswith("so far today")
    assert "**Vs. sector and market:**" in outbox[0]["embeds"][0]["description"]
    assert ("**Coming up:**\n• Mon Nov 9: Microsoft (MSFT): Court hearing in patent case"
            in outbox[1]["embeds"][0]["description"])  # the summary lists the week ahead, from the calendar
    assert testenv.status_summary(fresh_db)["alerts"] == {"logged": 2, "outbox_messages": 2}


def test_offline_mode_never_contacts_discord(fresh_db, client, monkeypatch):
    import alerts
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/real-looking")

    def no_network(*args, **kwargs):
        raise AssertionError("the test environment tried to reach Discord")

    monkeypatch.setattr(alerts.urllib.request, "urlopen", no_network)
    app = client(fresh_db)
    app.post("/api/runs", json={})
    run = wait_for_run(app)

    assert run["state"] == "finished"
    assert any(e["type"] == "alert" for e in run["log"])  # the alert "went out"... to the outbox file
    assert "mcp__market__market_backdrop" in [e.get("tool") for e in run["log"]]
    status = app.get("/api/alerts").json()
    assert status["enabled"] and status["alerts"][0]["status"] == "sent"
    assert len(testenv.read_outbox(fresh_db)) == 1


def test_calendar_has_two_months_of_history_and_whats_coming(conn):
    import events
    on_calendar = events.events_between(conn, "2000-01-01", "2100-01-01")
    by_kind = {kind: [e for e in on_calendar if e["kind"] == kind] for kind in ("earnings", "dividend", "news")}

    # Every sample earnings day in the window was on the calendar, and stays there afterwards
    earnings_days = {(t, d.isoformat()) for (t, d), (kind, _) in SampleMarket(TICKERS, END).events.items()
                     if kind == "earnings" and d >= date(2026, 9, 14)}  # from the first weekly scan on
    assert earnings_days <= {(e["ticker"], e["event_date"]) for e in by_kind["earnings"]}
    upcoming = [e for e in on_calendar if e["event_date"] >= END.isoformat()]
    assert {e["kind"] for e in upcoming} == {"earnings", "dividend", "news"}
    assert any(e["date_note"] and e["date_note"].startswith("Estimated") for e in upcoming)  # an unconfirmed date
    # News events always cite a sample article, and earnings previews are attached to the earnings date
    assert all(e["sources"] and e["sources"][0]["url"].startswith("https://news.example.com/") for e in by_kind["news"])
    assert any(e["news_note"] for e in by_kind["earnings"])
    # No event appears twice, despite a scan every week
    keys = [(e["ticker"], e["event_date"], e["kind"], e["title"]) for e in on_calendar]
    assert len(keys) == len(set(keys))
    assert {e["company"] for e in on_calendar} <= {"Apple", "Microsoft", "NVIDIA", "Amazon.com", "JPMorgan Chase"}


def test_offline_calendar_update_now(fresh_db, client):
    app = client(fresh_db)
    before = app.get("/api/calendar").json()
    assert before["today"] == "2026-11-06" and before["last_scan"]["trigger"] == "scheduled"

    assert app.post("/api/calendar/scan", json={}).status_code == 202
    for _ in range(100):
        scan = app.get("/api/calendar/scan").json()["scan"]
        if scan["state"] != "running":
            break
        time.sleep(0.05)
    after = app.get("/api/calendar").json()

    assert scan["state"] == "finished" and scan["result"]["cost_usd"] == 0 and scan["result"]["trigger"] == "manual"
    assert len(after["events"]) == len(before["events"])  # nothing new since this morning, and nothing doubled
    assert testenv.simulate_events_scan(fresh_db).startswith("ok: calendar updated as of 2026-11-06")


def test_update_and_finalize_simulate_scheduled_runs(fresh_db):
    assert testenv.simulate_update(fresh_db).startswith("updated")
    assert testenv.simulate_finalize(fresh_db).startswith("finalized")
    assert testenv.simulate_update(fresh_db).startswith("skipped")
    import search_index
    assert search_index.status()["reports_indexed"] == 44  # search kept up with both
    assert (fresh_db.parent / "search.db").exists()


# ---------------------------------------------------------------------------
# Tracked stocks: the Stocks tab, over the test environment's own watchlist
# ---------------------------------------------------------------------------

def wait_for(check, tries=100):
    for _ in range(tries):
        if check():
            return True
        time.sleep(0.05)
    return False


def test_the_test_environment_has_its_own_watchlist(tmp_path):
    db = seed(tmp_path)
    path = testenv.watchlist_path(db)
    assert path == tmp_path / "watchlist.txt"
    lines = path.read_text().splitlines()
    assert lines[0].startswith("# The test environment's watchlist")
    assert lines[1:] == ["*AAPL", "*MSFT", "*NVDA", "AMZN", "JPM"]  # the first 3 are main stocks
    import market_tools
    assert market_tools.WATCHLIST_FILE == path  # what every main-project module reads

    # A new test watchlist copies the main project's (only reading it)
    other = tmp_path / "other" / "reports.db"
    assert testenv.make_test_watchlist(other) == testenv.main_watchlist()
    # An existing one is kept, so stocks you added survive `seed --reset`
    testenv.watchlist_path(other).write_text("*COST\nAAPL\n")
    assert testenv.make_test_watchlist(other) == ["COST", "AAPL"]
    assert testenv.make_test_watchlist(other, ["KO"]) == ["KO"]  # unless --tickers replaces it


def test_find_stocks_offline(db, client):
    app = client(db)
    found = app.get("/api/stocks/search?q=costco").json()["results"]
    assert [(r["ticker"], r["type"], r["tracked"]) for r in found] == [("COST", "Stock", False)]  # not COST.MX
    assert [r["ticker"] for r in app.get("/api/stocks/search?q=apple").json()["results"]] == ["AAPL"]  # not APC.DE
    assert app.get("/api/stocks/search?q=apple").json()["results"][0]["tracked"] is True
    assert app.get("/api/stocks/search?q=bitcoin").json()["results"] == []  # crypto can't be tracked
    assert {r["ticker"] for r in app.get("/api/stocks/search?q=s%26p").json()["results"]} == {"SPY"}  # ETFs can


def test_add_star_and_remove_stocks_in_the_test_environment(fresh_db, client):
    real = (testenv.MAIN / "watchlist.txt").read_bytes()
    app = client(fresh_db)
    view = app.get("/api/watchlist").json()
    assert [(s["ticker"], s["main"]) for s in view["stocks"]] == [
        ("AAPL", True), ("MSFT", True), ("NVDA", True), ("AMZN", False), ("JPM", False)]
    assert view["stocks"][0]["name"] == "Apple" and view["stocks"][0]["latest"]["status"] == "intraday"

    # Track Costco as a main stock: checked by the real watchlist.py, saved to the test watchlist
    added = app.post("/api/watchlist", json={"ticker": "cost", "main": True})
    assert added.status_code == 201 and added.json()["stock"]["name"] == "Costco Wholesale Corporation"
    cost = next(s for s in added.json()["watchlist"]["stocks"] if s["ticker"] == "COST")
    assert cost["main"] and cost["latest"] is None  # its first figures come with the next run
    assert "*COST" in testenv.watchlist_path(fresh_db).read_text()
    # Its earnings date is on the calendar straight away (simulated calendar, no cost)
    assert wait_for(lambda: next(s for s in app.get("/api/watchlist").json()["stocks"]
                                 if s["ticker"] == "COST")["next_event"])
    # The next run reports on it, and its chart works; the other stocks' data hasn't changed
    nvda_before = app.get("/api/tickers/NVDA/prices?range=1mo").json()["prices"][:-1]
    app.post("/api/runs", json={})
    assert wait_for_run(app)["result"]["outcome"] == "updated"
    cost = next(s for s in app.get("/api/watchlist").json()["stocks"] if s["ticker"] == "COST")
    assert cost["latest"]["session_date"] == "2026-11-06" and cost["latest"]["price"] > 0
    assert "COST" in app.get("/api/reports/latest").json()["body_md"]
    assert len(app.get("/api/tickers/COST/prices?range=1mo").json()["prices"]) == 21
    assert app.get("/api/tickers/NVDA/prices?range=1mo").json()["prices"][:-1] == nvda_before

    # The real rules apply: crypto, unknown tickers, doubles and the main-stock cap are refused
    assert "cryptocurrency" in app.post("/api/watchlist", json={"ticker": "BTC-USD"}).json()["error"]
    assert "doesn't know" in app.post("/api/watchlist", json={"ticker": "ZZZZ"}).json()["error"]
    assert app.post("/api/watchlist", json={"ticker": "COST"}).status_code == 409

    # Unstar and remove: the next run leaves it out
    assert app.post("/api/watchlist/COST", json={"main": False}).status_code == 200
    assert app.post("/api/watchlist/COST/remove", json={}).status_code == 200
    assert "COST" not in testenv.read_tickers(testenv.watchlist_path(fresh_db))
    assert testenv.simulate_finalize(fresh_db).startswith("finalized")
    tickers = [t["ticker"] for t in app.get("/api/reports/latest").json()["tickers"]]
    assert "COST" not in tickers and len(tickers) == 5
    assert (testenv.MAIN / "watchlist.txt").read_bytes() == real  # the real watchlist was never edited


def test_reseeding_gives_added_stocks_history(tmp_path):
    db = seed(tmp_path)
    testenv.connect_main(db)
    import watchlist
    testenv.install_fake_search(watchlist)
    watchlist.add("KO")
    status = testenv.status_summary(db)["watchlist"]
    assert status["added_since_seeding"] == ["KO"] and status["main"] == ["AAPL", "MSFT", "NVDA"]

    testenv.reset(db)
    assert testenv.watchlist_path(db).is_file()  # reset keeps the test watchlist
    testenv.seed_database(db, end=END)           # no --tickers: seeds what the test watchlist tracks
    reports_db = testenv.connect_main(db)
    with closing(reports_db.connect(db, readonly=True)) as c:
        days = c.execute("SELECT COUNT(*) FROM report_tickers WHERE ticker = 'KO'").fetchone()[0]
    assert days == 44 and testenv.status_summary(db)["watchlist"]["added_since_seeding"] == []


def test_added_stocks_leave_the_rest_of_the_sample_unchanged():
    before = SampleMarket(TICKERS, END)
    after = SampleMarket(TICKERS, END)
    after.watch([*TICKERS, "COST", "BRK-B"])
    for t in TICKERS:
        assert (after.closes[t] == before.closes[t]).all() and (after.volumes[t] == before.volumes[t]).all()
    assert after.planned_events() == before.planned_events()
    day = END
    assert [f["ticker"] for f in after.scan(day)["flagged"] if f["ticker"] in TICKERS] == \
           [f["ticker"] for f in before.scan(day)["flagged"]]
    # The same stock gets the same simulated prices however it was added
    again = SampleMarket(TICKERS, END)
    again.add_ticker("COST")
    assert (again.closes["COST"] == after.closes["COST"]).all() and after.sector["COST"] == "XLP"


# ---------------------------------------------------------------------------
# Follow-through and story updates
# ---------------------------------------------------------------------------

def test_follow_through_over_two_months(db, conn):
    assert testenv.status_summary(db)["follow_through"] == {"moves": 27, "settled": 18, "surprises": 12, "story_updates": 12}
    import followups
    import stories
    moves = followups.moves(conn)
    finals = conn.execute("""SELECT COUNT(*) FROM report_tickers t JOIN reports r USING (session_date)
                             WHERE t.category = 'flagged' AND r.status = 'final'""").fetchone()[0]
    assert len(moves) == finals  # every move flagged in a final report is followed up
    assert all(m["settled"] == (m["session_date"] <= "2026-10-07") for m in moves)  # 20 trading days have passed
    assert {m["outcomes"]["5"] for m in moves if m["outcomes"]["5"]} == {"held", "faded", "reversed"}
    result = followups.patterns(moves, 5)
    assert result["all"]["judged"] == sum(m["outcomes"]["5"] is not None for m in moves)
    checks = stories.latest(conn)
    assert {(c["session_date"], c["ticker"]) for c in checks} == {(m["session_date"], m["ticker"]) for m in moves if m["surprise"]}
    assert all(c["trigger"] == "surprise" and c["cost_usd"] == 0 for c in checks)  # every surprise, checked once, for free
    assert {c["status"] for c in checks} == {"ok", "no_news"}
    developed = next(c for c in checks if c["verdict"] == "developed")
    assert developed["sources"][0]["url"].startswith("https://news.example.com/")


def test_offline_refresh_and_story_check(fresh_db, client):
    app = client(fresh_db)
    started = app.post("/api/followups/refresh", json={})
    assert started.status_code == 202
    for _ in range(100):
        if app.get("/api/followups").json()["refresh"]["state"] != "running":
            break
        time.sleep(0.05)
    view = app.get("/api/followups?horizon=5").json()
    assert view["refresh"]["state"] == "finished" and view["updated"]["trigger"] == "manual"

    move = app.get("/api/stories").json()["unchecked"][0]
    assert app.post("/api/stories/check", json={"session_date": move["session_date"], "ticker": move["ticker"]}).status_code == 202
    for _ in range(100):
        stories_now = app.get("/api/stories").json()
        if stories_now["check"]["state"] != "running":
            break
        time.sleep(0.05)
    newest = stories_now["checks"][0]
    assert (newest["session_date"], newest["ticker"], newest["trigger"]) == (move["session_date"], move["ticker"], "manual")
    assert newest["status"] in ("ok", "no_news") and newest["cost_usd"] == 0


def test_offline_run_now_checks_past_moves_and_finalize_follows_up(fresh_db, client):
    app = client(fresh_db)
    app.post("/api/runs", json={})
    run = wait_for_run(app)
    tools = [e["tool"] for e in run["log"] if e["type"] == "tool_call"]
    assert "mcp__market__past_moves" in tools
    brief = app.get("/api/reports/latest").json()["body_md"]
    assert "Past moves: MSFT's flagged moves:" in brief and "Stock-specific moves across the watchlist:" in brief

    note = testenv.simulate_finalize(fresh_db)
    assert " · follow-through: " in note
    import followups
    reports_db = testenv.connect_main(fresh_db)
    with closing(reports_db.connect(fresh_db, readonly=True)) as c:
        latest = [m for m in followups.moves(c) if m["session_date"] == "2026-11-06"]
    assert latest and all(m["after_1d"] is None for m in latest)  # followed up, no later prices yet


def test_offline_ask_knows_how_moves_played_out(db, client):
    app = client(db)
    response = app.post("/api/ask", json={"question": "Why was AMZN flagged?"})
    done = json.loads([line for line in response.text.splitlines() if '"done"' in line][0])
    assert "a week later" in done["answer"] and "(follow-through)" in done["answer"]
    assert "(story update, " in done["answer"]
    general = app.post("/api/ask", json={"question": "What moved the most this week?"}).text
    assert "How flagged moves played out (follow-through): All flagged moves:" in general


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
    assert not (testenv.MAIN / testenv.OUTBOX_NAME).exists()
```
