# Market Analyst Agent: Reports Database & API

Adds a database that stores every report the agent writes, plus a read-only API that a frontend can use to display them.

This builds on `market-agent-guide.md` (the version with market-hours support). Finish that guide and get its tests passing first.

---

## Contents

1. [What you're building](#1-what-youre-building)
2. [How reports are stored](#2-how-reports-are-stored)
3. [Before you start](#3-before-you-start)
4. [Step 1: Create the database module](#4-step-1-create-the-database-module)
5. [Step 2: Update run_brief.py](#5-step-2-update-run_briefpy)
6. [Step 3: Create the API](#6-step-3-create-the-api)
7. [Step 4: Update requirements and .gitignore](#7-step-4-update-requirements-and-gitignore)
8. [Step 5: Try it out](#8-step-5-try-it-out)
9. [Test it](#9-test-it)
10. [API reference for the frontend](#10-api-reference-for-the-frontend)
11. [Database reference](#11-database-reference)
12. [Backups and corrections](#12-backups-and-corrections)
13. [Security before going live](#13-security-before-going-live)
14. [Troubleshooting](#14-troubleshooting)
15. [Next steps toward the frontend](#15-next-steps-toward-the-frontend)
16. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What you're building

```
 run_brief.py  ──writes──▶  reports.db  ◀──reads only──  api.py  ◀──HTTP / JSON──  your frontend
 (the agent)                (SQLite)                     (Starlette)
                               ▲
                               └── python reports_db.py list | show     (browse from the terminal)
```

| File | Status | Role |
|---|---|---|
| `reports_db.py` | **New** | Creates the database, enforces the storage rules, reads reports back, and has a small command-line browser |
| `api.py` | **New** | Read-only JSON API for the frontend |
| `tests/test_reports_db.py` | **New** | Offline tests for the database, the API and how runs are saved |
| `run_brief.py` | **Changed** | Saves each run to the database instead of the `briefs/` folder |
| `requirements.txt` | **Changed** | Lists the web server packages |
| `market_tools.py`, `analyst_prompt.md`, `watchlist.txt` | Unchanged | |

**Why SQLite:** it's built into Python, the whole database is one file, there's no server to run, and it easily handles years of daily reports. The agent can write while the API reads at the same time. When you host this for many users, move to PostgreSQL (see [next steps](#15-next-steps-toward-the-frontend)).

**Why Starlette for the API:** it's already installed as part of the MCP library, so there's nothing new to install. FastAPI is built on Starlette, so switching later is easy if you want its auto-generated docs.

---

## 2. How reports are stored

### The rules

1. **One report per trading day.**
2. **While the market is open**, that day's report has status `intraday`. Each run replaces it with fresher information: the text, the figures and the news sources. Its `revision` number goes up each time. An older update can never overwrite a newer one.
3. **Once the session is over**, the next run while the market is closed saves the day's **final** report. It replaces the intraday version and gets status `final`.
4. **Final reports are permanent.** The database itself refuses to change or delete them, so neither a bug nor a stray SQL command can alter one. (For a deliberate correction, see [section 12](#12-backups-and-corrections).)
5. **No wasted runs.** If the final report for the last session already exists, `run_brief.py` stops before calling Claude, so the run costs nothing.

### Example week, with the 8:15am and 12:30pm schedule from the main guide

| Run | Market | What happens in the database |
|---|---|---|
| Thu 12:30pm | Open | Thursday's report is **created** (`intraday`, revision 1) |
| Thu 2:00pm (manual run) | Open | Thursday's report is **updated** with newer figures (revision 2) |
| Fri 8:15am | Closed | Thursday's report is **finalized**: the end-of-day brief replaces the intraday version and is now permanent |
| Fri 12:30pm | Open | Friday's report is **created** (`intraday`) |
| Fri 6:00pm (manual run) | Closed | Friday's report is **finalized** |
| Mon 8:15am | Closed | Friday is already final, so the run **stops** without calling Claude |
| Mon 12:30pm | Open | Monday's report is **created** |

### What's saved for each report

| Saved | Where | Used for |
|---|---|---|
| The brief, in markdown | `reports.body_md` | Displaying the report |
| Title, status, `as_of` time, revision, timestamps, Claude cost | `reports` | Lists, "Live" badges, refresh checks |
| Every watchlist ticker's figures, grouped as flagged, quiet or error | `report_tickers` | Tables, heatmaps, charts over time |
| The news articles the agent read | `report_sources` | A "Sources" panel with links |

Quiet tickers only store their 1-day return. That's by design: `flag_events` keeps quiet tickers brief so the agent's input stays small.

**The figures match the brief exactly.** `run_brief.py` saves the same `flag_events` and `get_news` results the agent received, rather than fetching the data again. If it ever can't read them, it re-runs the scan and prints a warning.

---

## 3. Before you start

- Complete the main guide (market-hours version) and confirm `pytest -v` shows `21 passed, 1 skipped`.
- **Nothing new to install.** `sqlite3` is built into Python, and `starlette` and `uvicorn` come with the MCP library. They're added to `requirements.txt` anyway so the dependency is explicit.

---

## 4. Step 1: Create the database module

Create `reports_db.py` in the `market-agent` folder with the code from the [appendix](#reports_dbpy).

**What's in it:**

| Part | What it does |
|---|---|
| `SCHEMA` | The three tables, plus **triggers**: database rules that block any update or delete on a final report and its tickers and sources |
| `connect()` | Opens `reports.db` and creates the tables on first use. `connect(readonly=True)` opens it so that no write is possible; the API uses this. |
| `save_report()` | Applies the storage rules from section 2 in one transaction, and returns what happened (table below) |
| `list_reports()`, `get_report()`, `latest_report()`, `ticker_history()` | Read reports back as plain dictionaries, ready to send as JSON |
| Command line | `python reports_db.py list` and `python reports_db.py show [date or latest]` |

**`save_report()` outcomes:**

| Outcome | Meaning |
|---|---|
| `created` | First report for that day (intraday) |
| `updated` | The day's intraday report was replaced with newer information |
| `finalized` | The final report was saved. It's permanent from now on |
| `skipped_final_exists` | That day already has a final report, so nothing changed |
| `skipped_older_update` | This intraday update is older than the one already saved, so nothing changed |

**Where the database lives:** `reports.db` in the project folder. To put it somewhere else, set the `REPORTS_DB` environment variable to a file path. Every process that uses it (runs, API, tests) must see the same value.

---

## 5. Step 2: Update run_brief.py

Replace `run_brief.py` with the version in the [appendix](#run_briefpy).

**What changed:**

- **Saves to the database** instead of writing files to `briefs/`. Your existing files in `briefs/` are left alone, but new reports no longer go there.
- **Checks first.** If the market is closed and the last session's final report already exists, it prints `The final report for 2026-11-05 is already saved. Nothing to do.` and stops before calling Claude.
- **Captures what the agent saw.** It records the `flag_events` result and each `get_news` result from the agent's run, so the database figures match the brief.
- **Handles the market closing mid-run.** If a run starts at 3:59pm and the agent's figures are for the finished session, the report is saved as final.
- **New last line of output.** It reports the outcome, for example:

```
-> mcp__market__flag_events {}
-> mcp__market__get_news {'ticker': 'NVDA'}
updated: intraday report for 2026-11-06 (5 turns, $0.041)
```

Your schedule from the main guide doesn't need to change.

---

## 6. Step 3: Create the API

Create `api.py` with the code from the [appendix](#apipy).

- **Read-only.** It opens the database in read-only mode and only accepts GET requests, so the frontend can never change a report.
- **CORS** controls which websites may call the API from a browser. By default it allows `http://localhost:3000` (React, Next.js) and `http://localhost:5173` (Vite). To change this, set `FRONTEND_ORIGINS` to a comma-separated list:

```bash
export FRONTEND_ORIGINS="http://localhost:3000,https://reports.example.com"   # macOS / Linux
$env:FRONTEND_ORIGINS = "http://localhost:3000,https://reports.example.com"    # Windows PowerShell
```

- **Local only by default.** `uvicorn` listens on `127.0.0.1`, so only your computer can reach it. See [security](#13-security-before-going-live) before changing that.

The full endpoint list is in the [API reference](#10-api-reference-for-the-frontend).

---

## 7. Step 4: Update requirements and .gitignore

Replace `requirements.txt` with the version in the [appendix](#requirementstxt), then run:

```bash
pip install -r requirements.txt
```

If you use git, add a `.gitignore` file so the database and its working files are never committed:

```
.venv/
__pycache__/
reports.db
reports.db-wal
reports.db-shm
run.log
```

---

## 8. Step 5: Try it out

1. **Save a report.** Run `python run_brief.py`. The last line shows the outcome (`created`, `updated` or `finalized`).
2. **Browse it from the terminal:**

```bash
python reports_db.py list
python reports_db.py show latest
python reports_db.py show 2026-11-06
```

`list` prints one line per day:

```
2026-11-06  intraday  rev 2   1 flagged  Intraday update: 2026-11-06 12:30 ET
2026-11-05  final     rev 1   1 flagged  Watchlist brief: 2026-11-05
```

3. **Start the API** in a second terminal (with the virtual environment active) and leave it running:

```bash
uvicorn api:app --port 8000
```

4. **Open it in your browser:** go to `http://localhost:8000/api/reports` or `http://localhost:8000/api/reports/latest`. You'll see the JSON your frontend will get.
5. **Watch the rules work:**
   - During market hours, run `python run_brief.py` twice. `list` shows the same day with `rev 2`.
   - After the close, run it again. The day shows `final`.
   - Run it once more. It prints `...already saved. Nothing to do.`

---

## 9. Test it

### 9.1 Automated tests

Create `tests/test_reports_db.py` with the code from the [appendix](#teststest_reports_dbpy). Then, from the project folder:

```bash
pytest -v
```

**Expected result:** `54 passed, 1 skipped`, which is 21 market-tool tests plus 33 new ones. To run only the new tests, use `pytest -v tests/test_reports_db.py` (expect `33 passed`).

They use a temporary database and a fake agent, so they need no internet or API key and never touch your real `reports.db`.

**What the new tests prove:**

*Storage rules*

| Test | Proves that |
|---|---|
| `test_database_and_tables_are_created_on_first_use` | The database sets itself up, and opening it again is safe |
| `test_intraday_report_is_updated_in_place_during_the_day` | A second intraday run replaces the day's text and figures, bumps the revision, keeps the creation time, and leaves one report for the day |
| `test_older_intraday_update_never_overwrites_a_newer_one` | A slow run that finishes late can't overwrite fresher data |
| `test_final_report_replaces_the_days_intraday_report` | The final report replaces the intraday text, figures and sources |
| `test_final_report_is_permanent` | Later runs can't change a final report |
| `test_database_itself_blocks_changes_to_final_reports` (7 cases) | Direct SQL updates, deletes and inserts on a final report, its tickers or its sources are all refused |
| `test_a_new_day_never_touches_past_reports` | Saving today's reports leaves earlier days exactly as they were |
| `test_list_reports_newest_first_with_filters` | Listing order, `limit`, `before` and `status` filters work |
| `test_ticker_history_across_days` | One ticker's figures can be pulled across days for charts |

*API*

| Test | Proves that |
|---|---|
| `test_api_lists_reports` | `/api/reports` returns summaries newest first, with filters |
| `test_api_returns_a_full_report` | `/api/reports/{date}` includes the brief, every ticker and the sources |
| `test_api_latest_and_health` | `/api/reports/latest` and `/api/health` work |
| `test_api_ticker_history` | `/api/tickers/{ticker}/history` works and isn't case-sensitive |
| `test_api_rejects_bad_requests_clearly` (7 cases) | Bad dates, limits, filters and tickers get a 400 or 404 with an error message |
| `test_api_is_read_only` | POST and DELETE are refused, and the API's database connection can't write |
| `test_api_allows_the_frontend_origin` | Your frontend's origin is allowed by CORS and other websites aren't |
| `test_api_works_before_any_report_exists` | A brand-new install returns an empty list instead of crashing |

*Saving runs*

| Test | Proves that |
|---|---|
| `test_run_saves_report_with_figures_and_sources` | A run saves the brief, title, cost, every ticker's figures and each news source the agent read |
| `test_run_skips_claude_when_final_report_already_exists` | Claude isn't called when there's nothing new to do |
| `test_run_rescans_if_the_agent_result_cannot_be_read` | The figures are still saved if the agent's tool result can't be read |
| `test_run_saves_as_final_if_the_market_closed_mid_run` | The report is saved as the session the figures actually describe |

**Check the tests catch real bugs.** Make one temporary change, run `pytest tests/test_reports_db.py`, then undo it:

| File | Temporary change | Test that should fail |
|---|---|---|
| `reports_db.py` | `elif old and status == "intraday" and as_of < old["as_of"]:` → `elif False:` | The older-update test |
| `run_brief.py` | `if reports_db.is_final(conn, session_date):` → `if False:` | The skip-Claude test |
| `api.py` | Change the default origins `"http://localhost:3000,http://localhost:5173"` to `"*"` | The CORS test |

### 9.2 Manual checks with real runs

- [ ] After a run during market hours, `python reports_db.py list` shows today as `intraday`
- [ ] A second run during market hours shows the same day with a higher `rev`
- [ ] After the close, a run shows the day as `final`, and another run prints `already saved. Nothing to do.`
- [ ] `show latest` prints the same brief that `http://localhost:8000/api/reports/latest` returns in `body_md`
- [ ] The figures in `/api/reports/latest` match the numbers in the brief
- [ ] The protection works. Once a final report exists, run the command below. It must fail with `final reports are permanent`:

```bash
python -c "import reports_db; reports_db.connect().execute(\"UPDATE reports SET body_md = 'test' WHERE status = 'final'\")"
```

(On Windows PowerShell, put the Python code in a file and run that instead, because of quoting.)

---

## 10. API reference for the frontend

**Base URL:** `http://localhost:8000` · **Methods:** GET only · **Format:** JSON

**Errors** come back as `{"error": "message"}` with status `400` (bad request) or `404` (not found).

### Endpoints

| Endpoint | Returns |
|---|---|
| `GET /api/health` | `{"status": "ok", "reports": 12}` |
| `GET /api/reports` | `{"reports": [summary, ...]}`, newest first |
| `GET /api/reports/latest` | The most recent full report (404 if there are none yet) |
| `GET /api/reports/{YYYY-MM-DD}` | One full report (404 if that day has none) |
| `GET /api/tickers/{TICKER}/history` | `{"ticker": "NVDA", "history": [...]}`, newest first |

**Query parameters**

| Endpoint | Parameter | Values | Default |
|---|---|---|---|
| `/api/reports` | `limit` | 1–365 | 30 |
| `/api/reports` | `before` | `YYYY-MM-DD`: only days before this one (for paging) | none |
| `/api/reports` | `status` | `intraday` or `final` | both |
| `/api/tickers/{TICKER}/history` | `limit` | 1–365 | 30 |

**Paging:** to load older reports, pass the oldest `session_date` you have as `before`.

### Report summary (in `/api/reports`)

```json
{
  "session_date": "2026-11-06",
  "status": "intraday",
  "title": "Intraday update: 2026-11-06 12:30 ET",
  "as_of": "2026-11-06 12:30 ET",
  "revision": 2,
  "created_at": "2026-11-06T15:45:12Z",
  "updated_at": "2026-11-06T17:30:40Z",
  "finalized_at": null,
  "flagged_count": 1
}
```

### Full report (`/api/reports/latest` and `/api/reports/{date}`)

The summary fields (except `flagged_count`), plus:

```json
{
  "body_md": "# Watchlist brief: 2026-11-05\n\n## Notable moves\n...",
  "total_cost_usd": 0.041,
  "tickers": [
    {"ticker": "NVDA", "category": "flagged", "price": 151.2, "return_1d_pct": 6.5,
     "return_5d_pct": 9.1, "return_zscore": 4.1, "volume_vs_avg": 2.9,
     "compared_to": "daily moves over the last 3 months", "error": null},
    {"ticker": "AAPL", "category": "quiet", "price": null, "return_1d_pct": 0.4,
     "return_5d_pct": null, "return_zscore": null, "volume_vs_avg": null,
     "compared_to": null, "error": null}
  ],
  "sources": [
    {"ticker": "NVDA", "title": "Nvidia beats estimates", "publisher": "Reuters",
     "url": "https://...", "published": "2026-11-05T13:00:00Z"}
  ]
}
```

Tickers come sorted flagged first, then quiet, then errors, and alphabetically within each group.

### Field meanings

| Field | Meaning |
|---|---|
| `session_date` | The trading day the report covers. Unique: one report per day |
| `status` | `intraday` (market was open, may still change) or `final` (permanent) |
| `title` | The brief's first heading |
| `body_md` | The full brief in markdown |
| `as_of` | `2026-11-06` for final reports, or `2026-11-06 12:30 ET` for intraday ones: the time of the figures |
| `revision` | How many times this day's report has been written. Goes up with each intraday update and once more when finalized |
| `created_at`, `updated_at`, `finalized_at` | UTC timestamps (`finalized_at` is `null` until final) |
| `total_cost_usd` | Claude API cost of every run saved for this day |
| `tickers[].category` | `flagged` (unusual move), `quiet` or `error` (data problem; see `error`) |
| `tickers[].price` | Last close (final) or latest price (intraday). `null` for quiet tickers |
| `tickers[].return_1d_pct` | % change since the previous close (so far today, if intraday) |
| `tickers[].return_zscore` | How unusual the move is: ±2 or beyond is unusual |
| `tickers[].volume_vs_avg` | Volume vs. normal (normal for this time of day, if intraday) |
| `tickers[].compared_to` | What the move was compared with |
| `sources[]` | News articles the agent read, with links. `published` may be an ISO date or a Unix timestamp, depending on Yahoo's format |

### Tips for building the frontend

- **Render `body_md`** with any markdown library (for example `react-markdown`).
- **Show a "Live" badge** when `status` is `intraday`.
- **Refresh intraday reports by polling** `/api/reports/latest` every few minutes. Only re-render when `revision` or `updated_at` changes.
- **Cache final reports forever.** They never change.
- **Use `tickers`** for tables and heatmaps, and ticker history for charts over time.

Minimal fetch example:

```js
const response = await fetch("http://localhost:8000/api/reports/latest");
if (!response.ok) throw new Error((await response.json()).error);
const report = await response.json();
console.log(report.title, report.status, report.tickers);
```

---

## 11. Database reference

### Tables

**`reports`**: one row per trading day

| Column | Type | Notes |
|---|---|---|
| `session_date` | TEXT, primary key | `YYYY-MM-DD` |
| `status` | TEXT | `intraday` or `final` |
| `title` | TEXT | |
| `body_md` | TEXT | The brief in markdown |
| `as_of` | TEXT | Session date (final) or `YYYY-MM-DD HH:MM ET` (intraday) |
| `revision` | INTEGER | Starts at 1 |
| `total_cost_usd` | REAL | Sum across all saved runs for the day |
| `created_at`, `updated_at`, `finalized_at` | TEXT | UTC, `YYYY-MM-DDTHH:MM:SSZ` |

**`report_tickers`**: one row per ticker per day (primary key: `session_date`, `ticker`)

| Column | Type | Notes |
|---|---|---|
| `session_date` | TEXT | Links to `reports` |
| `ticker` | TEXT | |
| `category` | TEXT | `flagged`, `quiet` or `error` |
| `price`, `return_1d_pct`, `return_5d_pct`, `return_zscore`, `volume_vs_avg` | REAL | Empty for quiet tickers, except `return_1d_pct` |
| `compared_to`, `error` | TEXT | |

**`report_sources`**: news articles the agent read

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER, primary key | |
| `session_date` | TEXT | Links to `reports` |
| `ticker`, `title`, `publisher`, `url`, `published` | TEXT | |

**Protections:** 8 triggers. Two block updates and deletes on final rows in `reports`; six block inserts, updates and deletes on `report_tickers` and `report_sources` rows that belong to a final report.

### Looking at the data yourself

[DB Browser for SQLite](https://sqlitebrowser.org) is a free app for browsing the database. Use **Open Database Read Only** so you can't change anything by accident. Some useful queries:

```sql
-- Every day NVDA was flagged
SELECT session_date, return_1d_pct, return_zscore
FROM report_tickers WHERE ticker = 'NVDA' AND category = 'flagged'
ORDER BY session_date DESC;

-- Claude cost per month
SELECT substr(session_date, 1, 7) AS month, ROUND(SUM(total_cost_usd), 2) AS cost
FROM reports GROUP BY month ORDER BY month;

-- Most-flagged tickers
SELECT ticker, COUNT(*) AS times_flagged
FROM report_tickers WHERE category = 'flagged'
GROUP BY ticker ORDER BY times_flagged DESC;
```

---

## 12. Backups and corrections

### Backups

The database is one file, `reports.db`. While it's in use you'll also see `reports.db-wal` and `reports.db-shm`; these are normal working files. Don't copy `reports.db` by hand while a run might be writing, because you could miss recent changes. Use SQLite's built-in backup instead, which is safe at any time:

```bash
python -c "import sqlite3; sqlite3.connect('reports.db').backup(sqlite3.connect('backup-2026-11-06.db'))"
```

Keep backups somewhere other than the project folder, such as cloud storage.

### Correcting a final report (deliberate exception)

Final reports are permanent by design. If one is genuinely wrong (for example, a data outage produced a bad report), you can remove it on purpose:

1. Make a backup (above).
2. Make sure no run is scheduled in the next few minutes.
3. Save the following as `remove_final_report.py`, set `DAY`, and run it once:

```python
import reports_db

DAY = "2026-11-05"  # the final report to remove

conn = reports_db.connect()
for trigger in ("final_reports_no_delete", "report_tickers_final_no_delete", "report_sources_final_no_delete"):
    conn.execute(f"DROP TRIGGER {trigger}")
conn.execute("DELETE FROM report_sources WHERE session_date = ?", (DAY,))
conn.execute("DELETE FROM report_tickers WHERE session_date = ?", (DAY,))
conn.execute("DELETE FROM reports WHERE session_date = ?", (DAY,))
conn.close()
reports_db.connect().close()  # reconnecting puts the protections back
```

4. To regenerate it, run `python run_brief.py` while the market is closed. **This only works for the most recent session**, because the tools always measure the latest one. An older day can be removed but not recreated.

---

## 13. Security before going live

| Today (on your computer) | Before anyone else can reach it |
|---|---|
| The API only listens on your computer (`127.0.0.1`) | Add authentication (an API key header, or your frontend's login) |
| No login needed | Serve it over HTTPS |
| CORS allows local development servers | Set `FRONTEND_ORIGINS` to your real frontend address only |

Also:

- The API is read-only. Keep it that way: the frontend should never write reports.
- Never put `reports.db` or your `ANTHROPIC_API_KEY` in the frontend's code or a public folder.
- Starting uvicorn with `--host 0.0.0.0` makes the API reachable from your whole network. Only do that once authentication is in place.

---

## 14. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `sqlite3.OperationalError: database is locked` | Two runs tried to write at once (for example, a manual run overlapping a scheduled one). Each waits up to 10 seconds before giving up. Retry, and avoid overlapping runs. |
| `sqlite3.IntegrityError: final reports are permanent` | Something tried to change a final report. That's the protection working. For a deliberate fix, see [section 12](#12-backups-and-corrections). |
| `attempt to write a readonly database` | Expected if it comes from a read-only connection, such as the API. Only `run_brief.py` writes. |
| A run prints `skipped_older_update` | A slower run finished after a newer one. Nothing was lost; the newer data was kept. |
| A run prints `skipped_final_exists` | The market closed while the run was in progress and that day's final report already existed. Nothing changed. |
| `Warning: couldn't read the agent's flag_events result` | The figures were re-fetched for the database. During market hours they may differ slightly from the brief. If it happens every run, send me the output. |
| The API returns an empty list | No run has saved a report yet, or the API and the runs use different database files. Both use `reports.db` in the project folder unless `REPORTS_DB` is set; it must match for both. |
| The browser shows a CORS error | Add the frontend's exact address (scheme, host and port, such as `http://localhost:5173`) to `FRONTEND_ORIGINS` and restart the API. |
| `uvicorn: command not found` | The virtual environment isn't active. Activate it, or use `python -m uvicorn api:app --port 8000`. |
| `Address already in use` | Another program is using port 8000. Use another port: `uvicorn api:app --port 8001`. |
| Tests fail importing `TestClient`, mentioning `httpx` | You have an older Starlette. Run `pip install -U "starlette>=1.0"` (or `pip install httpx`). |

---

## 15. Next steps toward the frontend

1. **Build the frontend against the API.** Section 10 has everything it needs. A React or Next.js app with a report list, a report page and a ticker chart is a good first version.
2. **Keep the API running.** For now, run it in a terminal. Later, run it as a background service or host it alongside the frontend.
3. **Add authentication** before anyone else can reach it (section 13).
4. **Move to PostgreSQL** when the API runs on a server, or when several machines need the same data. The tables carry over directly, and the protections become PostgreSQL triggers. Only `reports_db.py` needs to change.
5. **Push updates instead of polling** (for example, server-sent events), if near-real-time intraday updates matter.

---

## Appendix: full source code

### requirements.txt

```
claude-agent-sdk>=0.2
mcp>=2.0
yfinance
pandas
starlette>=1.0
uvicorn
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
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


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


def _insert_details(conn, session_date, scan, sources):
    rows = {}
    for category, key in (("flagged", "flagged"), ("quiet", "quiet"), ("error", "errors")):
        for m in scan.get(key) or []:
            rows[m["ticker"]] = (
                session_date, m["ticker"], category, m.get("last_close", m.get("last_price")),
                m.get("return_1d_pct"), m.get("return_5d_pct"), m.get("return_zscore"),
                m.get("volume_vs_avg"), m.get("compared_to"), m.get("error"))
    conn.executemany("INSERT INTO report_tickers VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", rows.values())
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
    report["tickers"] = [dict(t) for t in conn.execute(
        """SELECT ticker, category, price, return_1d_pct, return_5d_pct, return_zscore,
                  volume_vs_avg, compared_to, error
           FROM report_tickers WHERE session_date = ?
           ORDER BY CASE category WHEN 'flagged' THEN 0 WHEN 'quiet' THEN 1 ELSE 2 END, ticker""",
        (session_date,))]
    report["sources"] = [dict(s) for s in conn.execute(
        """SELECT ticker, title, publisher, url, published FROM report_sources
           WHERE session_date = ? ORDER BY ticker, id""", (session_date,))]
    return report


def latest_report(conn) -> dict | None:
    row = conn.execute("SELECT session_date FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()
    return get_report(conn, row["session_date"]) if row else None


def ticker_history(conn, ticker: str, limit: int = 30) -> list[dict]:
    """One ticker's figures across days, newest first (for charts)."""
    return [dict(row) for row in conn.execute(
        """SELECT t.session_date, r.status, t.category, t.price, t.return_1d_pct, t.return_5d_pct,
                  t.return_zscore, t.volume_vs_avg, t.compared_to, t.error
           FROM report_tickers t JOIN reports r ON r.session_date = t.session_date
           WHERE t.ticker = ? ORDER BY t.session_date DESC LIMIT ?""",
        (ticker.upper(), limit))]


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

### run_brief.py

This replaces the version in the main guide.

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


async def main() -> None:
    now = now_et()
    session = market_session()  # checked before calling Claude, so a data outage costs nothing
    session_date, status = report_key(session)

    if status == "final":
        with closing(reports_db.connect()) as conn:
            if reports_db.is_final(conn, session_date):
                print(f"The final report for {session_date} is already saved. Nothing to do.")
                return
        prompt = (f"It is {now:%Y-%m-%d %H:%M} ET and the market is closed. "
                  f"Write the watchlist brief for the {session_date} session.")
    else:
        prompt = f"It is {now:%Y-%m-%d %H:%M} ET and the market is open. Write an intraday update."

    calls = {}  # tool_use_id -> (tool name, arguments)
    scan, sources, result = None, [], None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls[block.id] = (block.name, block.input)
                    print(f"-> {block.name} {block.input}")  # audit trail of every tool call

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
        sys.exit(f"Run failed: {result.subtype if result else 'no result'}")

    if scan is None:
        print("Warning: couldn't read the agent's flag_events result, so re-scanning for the database.")
        scan = flag_events()
    # The scan's own session is what the figures describe (matters if the market closed mid-run)
    session_date, status = report_key(scan.get("session", session))
    as_of = scan.get("session", session)["as_of"]
    title = next((ln[2:].strip() for ln in result.result.splitlines() if ln.startswith("# ")), "Watchlist brief")
    cost = result.total_cost_usd or 0

    with closing(reports_db.connect()) as conn:
        outcome = reports_db.save_report(
            conn, session_date=session_date, status=status, title=title, body_md=result.result,
            as_of=as_of, cost_usd=cost, scan=scan, sources=sources)
    print(f"{outcome}: {status} report for {session_date} ({result.num_turns} turns, ${cost:.3f})")


if __name__ == "__main__":
    asyncio.run(main())
```

### api.py

```python
"""Read-only JSON API over the reports database, for the frontend.

Run:
    uvicorn api:app --port 8000

Endpoints (all GET):
    /api/health
    /api/reports?limit=30&before=YYYY-MM-DD&status=final|intraday
    /api/reports/latest
    /api/reports/{YYYY-MM-DD}
    /api/tickers/{TICKER}/history?limit=30

Allowed frontend origins come from FRONTEND_ORIGINS (comma-separated).
"""

import os
import re
from contextlib import closing

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from starlette.routing import Route

import reports_db

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]


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
    return closing(reports_db.connect(readonly=True))  # the API can never write


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


app = Starlette(
    routes=[
        Route("/api/health", health),
        Route("/api/reports", list_reports),
        Route("/api/reports/latest", latest_report),  # must come before the {session_date} route
        Route("/api/reports/{session_date}", get_report),
        Route("/api/tickers/{ticker}/history", ticker_history),
    ],
    middleware=[Middleware(CORSMiddleware, allow_origins=FRONTEND_ORIGINS, allow_methods=["GET"])],
)
```

### tests/test_reports_db.py

```python
"""Offline tests for the reports database, the API and how run_brief.py saves reports.

Run from the project folder:
    pytest -v tests/test_reports_db.py
"""

import asyncio
import json
import sqlite3
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage,
)
from starlette.testclient import TestClient  # noqa: E402

OPEN = {"status": "in_progress", "as_of": "2026-11-06 12:30 ET"}
CLOSED = {"status": "complete", "as_of": "2026-11-06"}


def scan(session, flagged=("NVDA",), quiet=("AAPL",), errors=()):
    """A flag_events result shaped like the real one."""
    price_key = "last_price" if session["status"] == "in_progress" else "last_close"
    return {
        "session": session,
        "flagged": [{"ticker": t, price_key: 150.0, "return_1d_pct": 6.5, "return_5d_pct": 9.1,
                     "return_zscore": 4.2, "volume_vs_avg": 2.8, "compared_to": "test baseline"}
                    for t in flagged],
        "quiet": [{"ticker": t, "return_1d_pct": 0.3} for t in quiet],
        "errors": [{"ticker": t, "error": "not enough price history"} for t in errors],
    }


def save(conn, session_date="2026-11-06", status="intraday", as_of="2026-11-06 12:30 ET",
         body="# Intraday update\n\nbody", **kwargs):
    kwargs.setdefault("scan", scan(OPEN if status == "intraday" else CLOSED))
    return reports_db.save_report(conn, session_date=session_date, status=status, title=body.splitlines()[0][2:],
                                  body_md=body, as_of=as_of, **kwargs)


@pytest.fixture
def conn(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    connection = reports_db.connect()
    yield connection
    connection.close()


# ---------------------------------------------------------------------------
# Storage rules
# ---------------------------------------------------------------------------

def test_database_and_tables_are_created_on_first_use(conn):
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert {"reports", "report_tickers", "report_sources"} <= tables
    reports_db.connect().close()  # opening again is safe


def test_intraday_report_is_updated_in_place_during_the_day(conn):
    assert save(conn, as_of="2026-11-06 10:30 ET", body="# Intraday update\n\nmorning",
                scan=scan(OPEN, flagged=("NVDA",))) == reports_db.CREATED
    first = reports_db.get_report(conn, "2026-11-06")

    assert save(conn, as_of="2026-11-06 12:30 ET", body="# Intraday update\n\nmidday",
                scan=scan(OPEN, flagged=("TSLA",)), cost_usd=0.05) == reports_db.UPDATED
    report = reports_db.get_report(conn, "2026-11-06")

    assert report["status"] == "intraday"
    assert report["body_md"].endswith("midday")
    assert report["revision"] == 2
    assert report["created_at"] == first["created_at"]
    assert [t["ticker"] for t in report["tickers"] if t["category"] == "flagged"] == ["TSLA"]  # replaced
    assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 1  # still one report for the day


def test_older_intraday_update_never_overwrites_a_newer_one(conn):
    save(conn, as_of="2026-11-06 13:30 ET", body="# Intraday update\n\nnewer")
    assert save(conn, as_of="2026-11-06 12:30 ET", body="# Intraday update\n\nolder") == reports_db.SKIPPED_STALE
    assert reports_db.get_report(conn, "2026-11-06")["body_md"].endswith("newer")


def test_final_report_replaces_the_days_intraday_report(conn):
    save(conn, status="intraday", sources=[{"ticker": "NVDA", "title": "old news", "url": "https://a"}])

    outcome = save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief: 2026-11-06\n\nfinal",
                   scan=scan(CLOSED, flagged=("AMD",)),
                   sources=[{"ticker": "AMD", "title": "new news", "url": "https://b"}])
    report = reports_db.get_report(conn, "2026-11-06")

    assert outcome == reports_db.FINALIZED
    assert report["status"] == "final" and report["finalized_at"]
    assert report["body_md"].endswith("final")
    assert [t["ticker"] for t in report["tickers"] if t["category"] == "flagged"] == ["AMD"]
    assert [s["title"] for s in report["sources"]] == ["new news"]


def test_final_report_is_permanent(conn):
    save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief\n\noriginal")

    assert save(conn, status="final", as_of="2026-11-06", body="# Watchlist brief\n\nrewrite") == reports_db.SKIPPED_FINAL
    assert save(conn, status="intraday", body="# Intraday update\n\nlate") == reports_db.SKIPPED_FINAL
    report = reports_db.get_report(conn, "2026-11-06")
    assert report["body_md"].endswith("original")
    assert report["revision"] == 1


@pytest.mark.parametrize("sql", [
    "UPDATE reports SET body_md = 'hacked'",
    "DELETE FROM reports",
    "UPDATE report_tickers SET price = 0",
    "DELETE FROM report_tickers",
    "INSERT INTO report_tickers (session_date, ticker, category) VALUES ('2026-11-06', 'ZZZ', 'quiet')",
    "DELETE FROM report_sources",
    "INSERT INTO report_sources (session_date, ticker) VALUES ('2026-11-06', 'ZZZ')",
])
def test_database_itself_blocks_changes_to_final_reports(conn, sql):
    save(conn, status="final", as_of="2026-11-06", sources=[{"ticker": "NVDA", "title": "news"}])
    with pytest.raises(sqlite3.IntegrityError, match="final reports are permanent"):
        conn.execute(sql)


def test_a_new_day_never_touches_past_reports(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", body="# Watchlist brief\n\nthursday")
    before = reports_db.get_report(conn, "2026-11-05")

    save(conn, session_date="2026-11-06", status="intraday", body="# Intraday update\n\nfriday")
    save(conn, session_date="2026-11-06", status="final", as_of="2026-11-06", body="# Watchlist brief\n\nfriday")

    assert reports_db.get_report(conn, "2026-11-05") == before


def test_list_reports_newest_first_with_filters(conn):
    for day in ("2026-11-03", "2026-11-04", "2026-11-05"):
        save(conn, session_date=day, status="final", as_of=day)
    save(conn, session_date="2026-11-06", status="intraday")

    assert [r["session_date"] for r in reports_db.list_reports(conn)] == [
        "2026-11-06", "2026-11-05", "2026-11-04", "2026-11-03"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, limit=2)] == ["2026-11-06", "2026-11-05"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, before="2026-11-05")] == ["2026-11-04", "2026-11-03"]
    assert [r["session_date"] for r in reports_db.list_reports(conn, status="intraday")] == ["2026-11-06"]
    assert reports_db.list_reports(conn)[0]["flagged_count"] == 1


def test_ticker_history_across_days(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", scan=scan(CLOSED, flagged=("NVDA",)))
    save(conn, session_date="2026-11-06", status="intraday", scan=scan(OPEN, flagged=(), quiet=("NVDA",)))

    history = reports_db.ticker_history(conn, "nvda")

    assert [(h["session_date"], h["status"], h["category"]) for h in history] == [
        ("2026-11-06", "intraday", "quiet"), ("2026-11-05", "final", "flagged")]
    assert history[1]["price"] == 150.0  # last_close for a final report


# ---------------------------------------------------------------------------
# API for the frontend
# ---------------------------------------------------------------------------

@pytest.fixture
def client(conn):
    save(conn, session_date="2026-11-05", status="final", as_of="2026-11-05", body="# Watchlist brief: 2026-11-05\n\nx",
         sources=[{"ticker": "NVDA", "title": "Beats estimates", "publisher": "Reuters", "url": "https://a"}])
    save(conn, session_date="2026-11-06", status="intraday", body="# Intraday update: 2026-11-06 12:30 ET\n\ny")
    return TestClient(api.app)


def test_api_lists_reports(client):
    response = client.get("/api/reports")
    assert response.status_code == 200
    assert [(r["session_date"], r["status"]) for r in response.json()["reports"]] == [
        ("2026-11-06", "intraday"), ("2026-11-05", "final")]
    assert client.get("/api/reports?status=final&limit=1").json()["reports"][0]["session_date"] == "2026-11-05"


def test_api_returns_a_full_report(client):
    report = client.get("/api/reports/2026-11-05").json()
    assert report["title"] == "Watchlist brief: 2026-11-05"
    assert report["status"] == "final"
    assert {t["ticker"]: t["category"] for t in report["tickers"]} == {"NVDA": "flagged", "AAPL": "quiet"}
    assert report["sources"][0]["publisher"] == "Reuters"


def test_api_latest_and_health(client):
    assert client.get("/api/reports/latest").json()["session_date"] == "2026-11-06"
    assert client.get("/api/health").json() == {"status": "ok", "reports": 2}


def test_api_ticker_history(client):
    data = client.get("/api/tickers/nvda/history").json()
    assert data["ticker"] == "NVDA"
    assert [h["session_date"] for h in data["history"]] == ["2026-11-06", "2026-11-05"]


@pytest.mark.parametrize("path, status_code", [
    ("/api/reports/2026-12-25", 404),
    ("/api/reports/yesterday", 400),
    ("/api/reports?limit=0", 400),
    ("/api/reports?limit=abc", 400),
    ("/api/reports?before=nov-5", 400),
    ("/api/reports?status=draft", 400),
    ("/api/tickers/not%20a%20ticker/history", 400),
])
def test_api_rejects_bad_requests_clearly(client, path, status_code):
    response = client.get(path)
    assert response.status_code == status_code
    assert "error" in response.json()


def test_api_is_read_only(client):
    assert client.post("/api/reports", json={}).status_code == 405
    assert client.delete("/api/reports/2026-11-05").status_code == 405
    readonly = reports_db.connect(readonly=True)  # the kind of connection the API uses
    with pytest.raises(sqlite3.OperationalError, match="readonly"):
        readonly.execute("DELETE FROM report_sources")
    readonly.close()


def test_api_allows_the_frontend_origin(client):
    response = client.get("/api/reports", headers={"Origin": "http://localhost:5173"})
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/api/reports", headers={"Origin": "https://evil.example"})
    assert "access-control-allow-origin" not in other.headers


def test_api_works_before_any_report_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "new.db")
    client = TestClient(api.app)
    assert client.get("/api/reports").json() == {"reports": []}
    assert client.get("/api/reports/latest").status_code == 404


# ---------------------------------------------------------------------------
# run_brief.py: saving what the agent produced
# ---------------------------------------------------------------------------

def agent_messages(flag_result, news=None, brief="# Intraday update: 2026-11-06 12:30 ET\n\nbrief text"):
    """The message stream the Agent SDK yields for a typical run."""
    messages = [AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})],
                                 model="test")]
    if flag_result is not None:
        messages.append(UserMessage(content=[ToolResultBlock(
            tool_use_id="t1", content=[{"type": "text", "text": json.dumps(flag_result)}])]))
    if news:
        messages.append(AssistantMessage(content=[ToolUseBlock(
            id="t2", name="mcp__market__get_news", input={"ticker": "nvda"})], model="test"))
        messages.append(UserMessage(content=[ToolResultBlock(  # MCP sends a list as one part per item
            tool_use_id="t2", content=[{"type": "text", "text": json.dumps(item)} for item in news])]))
    messages.append(ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False,
                                  num_turns=4, session_id="s", total_cost_usd=0.04, result=brief))
    return messages


@pytest.fixture
def fake_run(conn, monkeypatch):
    """Point run_brief at fake market status and a fake agent. Returns the list of prompts sent."""
    prompts = []

    def setup(session, messages):
        monkeypatch.setattr(run_brief, "market_session", lambda: session)

        async def fake_query(*, prompt, options):
            prompts.append(prompt)
            for m in messages:
                yield m

        monkeypatch.setattr(run_brief, "query", fake_query)
        return prompts
    return setup


def test_run_saves_report_with_figures_and_sources(conn, fake_run):
    news = [{"title": "Beats estimates", "publisher": "Reuters", "published": "2026-11-06T13:00:00Z",
             "url": "https://a", "summary": "..."},
            {"title": "Guidance raised", "publisher": "AP", "published": 1762000000, "url": "https://b", "summary": ""}]
    fake_run(OPEN, agent_messages(scan(OPEN), news))

    asyncio.run(run_brief.main())
    report = reports_db.get_report(conn, "2026-11-06")

    assert report["status"] == "intraday"
    assert report["title"] == "Intraday update: 2026-11-06 12:30 ET"
    assert report["as_of"] == "2026-11-06 12:30 ET"
    assert report["total_cost_usd"] == pytest.approx(0.04)
    assert {t["ticker"] for t in report["tickers"]} == {"NVDA", "AAPL"}
    assert [(s["ticker"], s["publisher"]) for s in report["sources"]] == [("NVDA", "Reuters"), ("NVDA", "AP")]


def test_run_skips_claude_when_final_report_already_exists(conn, fake_run):
    save(conn, status="final", as_of="2026-11-06")
    prompts = fake_run(CLOSED, agent_messages(scan(CLOSED)))

    asyncio.run(run_brief.main())

    assert prompts == []  # Claude was never called, so the run cost nothing


def test_run_rescans_if_the_agent_result_cannot_be_read(conn, fake_run, monkeypatch):
    fake_run(CLOSED, agent_messages(flag_result=None, brief="# Watchlist brief: 2026-11-06\n\nx"))
    monkeypatch.setattr(run_brief, "flag_events", lambda: scan(CLOSED, flagged=("AMD",)))

    asyncio.run(run_brief.main())

    report = reports_db.get_report(conn, "2026-11-06")
    assert report["status"] == "final"
    assert "AMD" in {t["ticker"] for t in report["tickers"]}


def test_run_saves_as_final_if_the_market_closed_mid_run(conn, fake_run):
    """Started at 3:59pm, but the figures the agent got were for the finished session."""
    fake_run(OPEN, agent_messages(scan(CLOSED), brief="# Watchlist brief: 2026-11-06\n\nx"))

    asyncio.run(run_brief.main())

    assert reports_db.get_report(conn, "2026-11-06")["status"] == "final"
```
