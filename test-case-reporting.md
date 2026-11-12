# Test Case Reporting

What was tested, what was found, what changed because of it, and how to repeat the process for the next version of the market analyst agent.

| | |
|---|---|
| **Date** | 2026-11-10 (first round), 2026-11-12 (second round: company filings) |
| **Version tested** | First round: `main` at commit `6922fdc` ("Add follow-through and story updates..."), plus the fixes listed in [section 4](#4-bug-log). Second round: the same, plus company filings (`market-agent-filings.md`) and BUG-10 to BUG-12 |
| **Machine** | Windows 11 Pro, Python 3.13.3 (default text encoding: cp1252) |
| **Key packages** | pytest 9.2.0, pandas 3.1.0, numpy 2.5.4, yfinance 1.8.0, starlette 1.10.0, mcp 2.3.0, claude-agent-sdk 0.2.177 |

---

## Contents

1. [Summary](#1-summary)
2. [New test files](#2-new-test-files)
3. [Test run log](#3-test-run-log)
4. [Bug log](#4-bug-log)
5. [Open issues and what wasn't tested](#5-open-issues-and-what-wasnt-tested)
6. [The testing process (reuse this for every version)](#6-the-testing-process-reuse-this-for-every-version)
7. [Templates](#7-templates)

---

## 1. Summary

| | Before | After |
|---|---|---|
| Offline tests | 284 passed, 4 skipped | **439 passed**, 4 skipped, 1 expected failure (xfail) |
| Test files | 11 | 13 (`test_regressions.py` and `test_edge_cases.py` added) |
| Flaky failures (full suite, repeated) | 2 failures in 35 runs | 0 failures in 20 runs |
| Live Yahoo Finance checks (`LIVE_TESTS=1`) | 1 of 3 broken | 3 of 3 pass |
| Bugs found | | **9 found, 9 fixed** (2 high, 3 medium, 4 low) |
| Open issues | | 1 security issue, logged and tracked by an xfail test (OPEN-01) |

**The two big errors:**

- **BUG-01: one edit on the Stocks tab could break the whole app on Windows.** `watchlist.txt` was read in Windows' default encoding (cp1252) but written as UTF-8. With an em dash (—) in a comment, one star, unstar, add or remove turned it into bytes cp1252 can't read. From then on, every read of the watchlist crashed with `UnicodeDecodeError`: the agent's scan, alerts, the calendar and the Stocks tab. It stayed broken until someone fixed the file by hand. Smart quotes (“ ”) typed into a comment crashed it straight away.
- **BUG-02: "database is locked" when two parts of the app create a database at the same moment.** This was the cause of a flaky test (`test_api_shows_alert_status`, about 1 run in 17). It can also hit a real first start, because the API's startup index update and the first page load both create `reports.db` and `search.db`. In a stress test, 16 of 40 attempts failed before the fix and none after it.

**Changes made to the program** (67 lines added, 27 removed, across 10 files):

| File | Change | Bug |
|---|---|---|
| `market_tools.py` | New `read_watchlist_text()`: reads the watchlist as UTF-8, skips a byte-order mark, falls back to the old Windows encoding | BUG-01 |
| `market_tools.py` | Rows with no closing price are dropped from Yahoo's daily and 5-minute data | BUG-03 |
| `watchlist.py` | Reads through `read_watchlist_text()`; "Remove" removes every copy of a ticker | BUG-01, BUG-07 |
| `run_brief.py` | Reads `analyst_prompt.md` as UTF-8 | BUG-01 |
| `reports_db.py` | New `SETUP_LOCK`: creating or setting up a database happens one thread at a time | BUG-02 |
| `search_index.py` | Uses the same lock for `search.db` | BUG-02 |
| `api.py` | `limit` and `horizon` accept only plain 0-9 digits | BUG-04 |
| `events.py` | A JSON `true` is no longer read as article or event number 1 | BUG-05 |
| `prices.py` | A zero close gives no % change instead of failing the chart | BUG-06 |
| `alerts.py` | The daily summary handles a flagged stock with a missing figure | BUG-08 |
| `tests/test_market_tools.py` | The live data check saves the real `yfinance.Ticker` before the fake replaces it | BUG-09 |

No database tables, report formats or normal API responses changed: only the failing cases above now behave differently (a 400 instead of a 500, a chart instead of a 502, and so on). Every test that passed before still passes.

### Second round: company filings (2026-11-12)

`market-agent-filings.md` added `edgar.py`, `filings.py`, the Filings tab, and changes to runs, briefs, Ask, the calendar and the API. It was merged with this project's own changes (the after-close run, the project API key, and BUG-01 to BUG-09), and the test environment and live demo were updated from their new guides.

| | Before | After |
|---|---|---|
| Offline tests | 439 passed, 4 skipped, 1 xfailed | **584 passed**, 5 skipped, 1 xfailed |
| Test files | 13 | 14 (`test_filings.py` added: 139 passed, 1 skipped, as the guide says) |
| Test environment (`market-agent-testenv/`) | 33 passed (its previous guide) | **40 passed** |
| Live demo (`market-agent-demo/`) | 17 passed (its previous guide) | **18 passed** |
| Browser checks (test environment and demo) | | All the filings guide's checks passed, with no browser errors (section 3, row 21) |
| Flaky failures (full suite, repeated) | | 2 failed runs in 10 at first; **0 in 10** after BUG-13's fix |
| Bugs found | | **4 found, 4 fixed** (BUG-10 to BUG-13: 1 medium, 3 low), all Windows or merge problems the guides' own testing couldn't see |

**Changes beyond the guide:**

| File | Change | Why |
|---|---|---|
| `filings.py` | Reads use the project's API key (`run_brief.AGENT_ENV`), like runs and Ask | This project bills `MARKET_AGENT_ANTHROPIC_KEY` rather than `ANTHROPIC_API_KEY` |
| `filings.py` | The command line prints UTF-8 when its output goes to a file or a pipe | BUG-11 |
| `watchlist.py` | Replacing `watchlist.txt` is tried again for up to 2 seconds while Windows has it locked | BUG-10 |
| `tests/test_watchlist.py` | The watcher test creates its database before the watcher starts | BUG-13 |
| `tests/test_events.py` | `wait_for_scan` waits up to 20 s instead of about 5 | Row 28b |
| `.env.example` | A `SEC_CONTACT=` line | The filings check needs your name and email for the SEC; `.env` is read by every entry point |
| `market-agent-testenv/testenv.py` (not in this repository) | The after-close run is switched off in the test environment; its few text reads and writes name UTF-8 | BUG-12, and BUG-01's lesson |

---

## 2. New test files

```
tests/
├── test_regressions.py   one group per bug in the bug log, named by its ID (bug01, bug02...)
└── test_edge_cases.py    limits, empty and odd input, bad data from Yahoo and Claude, requests from other websites
```

Both use the same setup as the other test files: a temporary database and watchlist, fake Yahoo Finance data (borrowed from `test_market_tools.py`), and no Claude, Discord or Voyage. They need no internet and no keys.

### 2.1 `test_regressions.py` (29 tests)

Each test failed before its fix and passes after it. Run one bug's tests with `pytest -v tests/test_regressions.py -k bug03`.

| Bug | Tests | What they check |
|---|---|---|
| BUG-01 | 5 | Three app edits keep an em dash, smart quotes and "café" exactly as they were. Smart quotes, a byte-order mark and an old Windows file all read correctly. **A guard test reads every `.py` file in the project and fails if any text file is opened without naming an encoding**, so this whole kind of bug can't come back. |
| BUG-02 | 2 | 8 threads open a brand-new `reports.db` (half read-only, like the API) or `search.db` at the same instant, 15 times over, with no errors |
| BUG-03 | 3 | A daily row with no price (the latest or an older one) gives exactly the same figures as if the row were missing. An empty 5-minute bar while the market is open is skipped. |
| BUG-04 | 6 | `limit=²`, `limit=¹`, `horizon=¹` and `limit=٣` get a 400 with a message, never a 500 |
| BUG-05 | 2 | `"sources": [true]` cites nothing; `"same_as": true` attaches to no event |
| BUG-06 | 1 | A chart with a zero close loads, with no % change after the zero |
| BUG-07 | 1 | Removing a ticker listed twice removes both lines |
| BUG-08 | 1 | The daily summary is built when a flagged stock has no return or z-score, and normal lines look exactly as before |
| BUG-09 | 1 | The live check's saved `yfinance.Ticker` is the real one while every other test sees the fake (runs offline, every time) |
| BUG-10 | 3 | An edit waits while the file is refused twice, then succeeds. On Windows, a real reader holding `watchlist.txt` open for 0.3 s delays an edit instead of failing it (skipped elsewhere). A file that stays locked still fails cleanly, leaving no temporary file and the list unchanged. |
| BUG-11 | 3 | With output in cp1252 (as Windows uses for a file or a pipe), printing "✓" and "✗" crashes without the fix and works with it (both shown, as two cases). Every `filings.py` command sets its output up first. |
| OPEN-01 | 1 (xfail) | A request whose Origin matches a spoofed Host header should be refused. It isn't yet, so the test is marked "expected to fail". |

### 2.2 `test_edge_cases.py` (133 tests)

These cover behaviour that already worked, at its edges, so later versions keep it working. Each limit is tested at the limit and one step past it.

| Area | Tests | Examples |
|---|---|---|
| Market math (`market_tools.py`) | 12 | Flat prices give a z-score of 0 (no division by zero). No volume history gives no volume ratio (not infinity). 25 days of history works and 24 doesn't. The flag threshold includes the limit itself. An empty watchlist scans nothing. `upcoming_events` keeps its range between 1 and 60 days. |
| Watchlist (`watchlist.py`) | 12 | A 10-character ticker is allowed, 11 isn't. `BRK.B`, `-ABC`, and a ticker containing a line break or `#` are refused. ` cost ` becomes `COST`. Adding to a file with no final line break starts a new line. Starring twice adds one star. Editing a stock that isn't listed is a 404 and changes nothing. |
| Storage (`reports_db.py`) | 6 | An intraday update with the same time replaces the earlier one. `Robert'); DROP TABLE reports;--` is stored as plain text. A 700 KB report with emoji comes back exactly. A failed save leaves nothing half-written, and the connection still works. |
| API (`api.py`) | 40 | `limit` of 365, 100 and 50 works on each endpoint and one more is a 400. 15- and 16-character tickers. A calendar range of 100 days works and 101 doesn't. Leap days, and Feb 29 in a non-leap year. Bad JSON. Posts from `Origin: null` (local files, sandboxed frames) are refused. The built frontend never serves files outside its folder (`%2e%2e/`, `..%2f`). |
| Discord alerts (`alerts.py`) | 13 | A z-score growth of exactly 1.5 alerts again and 1.49 doesn't; reversal limits. Only real `https://` Discord webhooks are accepted, so `discord.com.evil.example` and `http://` are refused. Shortening never cuts a link in half. |
| Follow-through (`followups.py`) | 12 | Giving back exactly 25% of a move still counts as held, and 26% is faded. A price exactly back where it started is reversed. A 0% move doesn't divide by zero. Surprise limits. |
| Claude's replies (`events.py`, `stories.py`) | 15 | Items that aren't events are dropped with a reason. Dates exactly on the window's first and last day are kept, and a day outside is dropped. Duplicates are kept once. 200 events are capped at 60. `javascript:` links are dropped. Story replies with an unknown verdict, no text or no real citation are refused. |
| Search (`search_index.py`) | 6 | Queries with no usable words (`???`, `—`, Japanese text, lone quotes) return nothing without an error. Long queries use the first 20 words. |
| Chart prices (`prices.py`) | 1 | Cached prices expire after 5 minutes; an empty download isn't cached |
| Ask (`ask.py`) | 5 | Tickers are found however they're written (`nvda's`, `Brk-b`). Empty and 501-character questions are refused before any cost, and exactly 500 characters is accepted. |
| Runs (`run_brief.py`) | 11 | Tool results are read whatever their shape (text, several parts, an image part, not JSON). Longer watchlists get more turns. News with odd characters survives the trip through JSON. |

**Do the new tests actually catch bugs?** I planted 12 small bugs in the program, one at a time, and ran the matching edge-case tests (a "mutation check": [section 6, step 5](#step-5-check-the-tests-catch-real-bugs-mutation-check)). For example, a comparison was moved by one step at the flag threshold, the alert-again limit, the 25% "held" limit, the 100-day calendar limit and the 25-day history minimum; the webhook check became "contains discord.com"; the `javascript:` link filter was removed; and `Origin: null` was let through. **All 12 were caught.** One needed both of its duplicate checks mutated (`len(daily) < 25` appears twice in `market_tools.py`), which shows the second check really is a backstop.

---

## 3. Test run log

In the order they were run. "Suite" means `pytest` over the whole `tests/` folder.

| # | What was run | Result | Effect on the program |
|---|---|---|---|
| 1 | Suite, first baseline | 284 passed, 4 skipped (26 s) | The guide `market-agent-testing.md` says 276 passed, 3 skipped, so it's out of date (see [section 5.3](#53-guides-to-update)) |
| 2 | Suite again | **1 failed**, 283 passed | A flaky test: the same code gave a different result |
| 3 | Suite × 33 more (35 in total) | 1 more failure: `test_alerts.py::test_api_shows_alert_status`, `sqlite3.OperationalError: database is locked` | Led to BUG-02 |
| 4 | Read every module, then probe scripts for suspected edge cases | 9 suspicions confirmed (BUG-01 and BUG-03 to BUG-08, plus OPEN-01) | Bug log entries written |
| 5 | Stress probe: 8 threads open a new database at once, 40 rounds | `reports.db`: 16/40 rounds failed ("database is locked" ×30, "no such table" ×2), and 22/40 on a second run. `search.db`: 27/40 failed. | Confirmed BUG-02's cause, outside the test suite |
| 6 | **New `test_regressions.py` against the unfixed code** | **20 failed**, 1 passed, 1 xfailed | Proves each test catches its bug. (The one pass is the old-Windows-encoding case, which only works today *because* cp1252 is the default. It stops the fix from breaking those files.) |
| 7 | Fixes applied (section 1 table), regression tests again | 21 passed, 1 xfailed | |
| 8 | Suite | 305 passed, 4 skipped, 1 xfailed | Nothing that worked before broke |
| 9 | New `test_edge_cases.py` | 133 passed | No new bugs; these lock current behaviour in |
| 10 | Mutation check: 12 planted bugs | 12/12 caught (one after mutating both copies of a duplicated check) | Confirms the edge-case tests aren't empty |
| 11 | Live checks (`LIVE_TESTS=1 pytest -k live`) | **`test_live_data` failed: `KeyError: 'AAPL'`** inside the *fake* Yahoo. The same failure on a clean copy of commit `6922fdc`. | Led to BUG-09 (a bug in the test, not the app) |
| 12 | Live checks after fixing the test | 3 passed: real AAPL figures, XLK sector context, backdrop, calendar and search | Confirms the market-data fix (BUG-03) works on real yfinance data |
| 13 | Suite, final | **439 passed, 4 skipped, 1 xfailed** | |
| 14 | Suite × 20, after fixes | 20 of 20 runs with no failures: 439 passed, 4 skipped, 1 xfailed (31-46 s). The first 3 runs show 438 because the BUG-09 test was added while the loop was running. | Flaky failure gone (it was 2 in 35 before) |

**Second round: company filings (2026-11-12)**

| # | What was run | Result | Effect on the program |
|---|---|---|---|
| 15 | The filings guide's files merged in (three-way, against the follow-through guide's versions, so this project's own changes stay), then the suite | 578 passed, 5 skipped, 1 xfailed (47 s). `tests/test_filings.py` alone: 139 passed, 1 skipped, as the guide says | The 5th skip is the live SEC check. BUG-01's guard test passes on `edgar.py` and `filings.py` |
| 16 | `python filings.py check --no-read`, `list` and `show`, without `SEC_CONTACT`, output to a file | A clear "Set SEC_CONTACT…" message and nothing sent; `list` and `show` work | |
| 17 | `python -c "print('✓')" > file` on this machine | `UnicodeEncodeError` (cp1252) | Led to BUG-11, since the filings commands print ✓ and ✗ |
| 18 | `npm run build` | Built, no warnings | |
| 19 | Test environment, from its new guide: `pytest`; then `seed --reset` and `build-frontend` | 40 passed. Sample: 23 filings (24 once the sample's clock passes 12:40), 5 first takes, 18 figures confirmed, 5 waiting | |
| 20 | Demo, from its new guide (its earlier Windows fixes merged back in): `pytest` | 18 passed | |
| 21 | Browser, over the test environment (`testenv.py serve`) | All passed, no browser errors: the list and first takes; a quote and a figure's source row; confirmed figures and a bank's 3 rows; every filter; **Read this filing** and its cooldown; **Check now** and its cooldown; the calendar's "Reported on Sep 22" on a Sep 23 earnings date, its link opening the filing picked out; Coming up's "Reported: first take ready" link, arriving live; **Run update now** logging "Checking company filings", with the brief citing the company filing; Ask's first-take line; a ticker's chart; `finalize` from another terminal confirming Amazon's five figures without a reload; phone width (no sideways scroll, the figures table scrolls in its box); dark mode. Light mode uses the same colour variables (no fixed colours in the new styles) | |
| 22 | `python demo.py build` | **Failed:** `Run now gave 409` | Led to BUG-12 |
| 23 | `python demo.py build` after BUG-12's fix | **Failed:** `PermissionError: [WinError 5]` replacing `watchlist.txt` | Led to BUG-10 |
| 24 | Reproduction: `os.replace` onto a file another handle has open | WinError 5 while open, works once closed | Confirmed BUG-10's cause, outside the project |
| 25 | New BUG-10 and BUG-11 tests against the unfixed code | 3 failed, 3 passed. The passes are by design: the locked-for-good case behaves the same before and after, and BUG-11's two output cases call the new function directly; the third BUG-11 test, which checks every command uses it, failed | Each bug has a test that catches it |
| 26 | `python demo.py build`, `check`, `serve`, after the fixes; then a browser | Built: 44 days, 4 recorded runs, 3.4 MB. Check: no keys, webhooks or local paths. In the browser: the banner, the Filings tab, a recorded read, **Check now**, and a run that finds the 12:40 filing, after which the tab shows it without a reload. No browser errors | |
| 27 | All three suites | Program: **584 passed, 5 skipped, 1 xfailed**. Test environment: 40 passed (its last test confirms this folder was left byte-for-byte unchanged). Demo: 18 passed | |
| 28 | Suite × 10 (some runs overlapping the live checks, row 29) | **2 failed runs:** `test_watchlist.py::test_editing_watchlist_txt_by_hand_updates_open_pages` once, `test_events.py::test_update_now_has_a_cooldown_and_runs_one_at_a_time` once. 8 runs: 584 passed, 5 skipped, 1 xfailed | Led to BUG-13 |
| 28a | The watcher test alone × 12, then the same steps in a script with timings | 1 failed in 12; 3 in 40 (script). Timing showed a 1.3 to 2.3 s first look, all of it in closing the new database | BUG-13's cause. Fixed in the test |
| 28b | `test_events.py` alone × 25 | 25 passed: the failure didn't come back | Its one traceback line was in `wait_for_scan`, whose limit was about 5 s. Most likely the same Windows stall; the limit is now 20 s (a passing test still returns as soon as the scan finishes). Not proven, so noted in section 5.2 |
| 28c | Suite × 10, after BUG-13's fix (full tracebacks kept) | **10 of 10: 584 passed, 5 skipped, 1 xfailed** (45-58 s) | |
| 29 | Live checks (`LIVE_TESTS=1 pytest -k live`) | `test_live_data`, `test_live_calendar_data` and `test_live_search` passed on real Yahoo data; `test_live_filings` skipped (no `SEC_CONTACT`) | See section 5.2 |

**The 4 skipped tests** (5 since the filings round) are expected: the live checks (they need `LIVE_TESTS=1` and internet, and the SEC's also needs `SEC_CONTACT`), and `test_editing_keeps_the_files_permissions`, which is skipped on Windows because file permissions work differently there.

**Not run** (they cost money or need setup outside this machine): agent test runs with Claude, the Discord alert check, the calendar and follow-through checks with Claude, and the schedule test. See [section 5.2](#52-what-wasnt-tested).

---

## 4. Bug log

Severity: **High** = breaks the app or gives wrong figures with no warning. **Medium** = a clear error, or wrong data in an unusual case. **Low** = a rare case with a small effect.

### BUG-01: one app edit to the watchlist could make it unreadable on Windows — High, fixed

| | |
|---|---|
| **Where** | `market_tools.py` (`_watchlist_entries`), `watchlist.py` (`entries`, `_edit`), `run_brief.py` (the prompt file) |
| **Symptom** | `UnicodeDecodeError: 'charmap' codec can't decode byte 0x9d` from every part of the app that reads the watchlist: the agent's `flag_events`, alerts, the calendar scan and the Stocks tab. A Notepad byte-order mark turned the first ticker into `ÏAAPL`. |
| **How to reproduce (before the fix)** | Put `*NVDA  SMH  # semis — chips` in `watchlist.txt` (saved as UTF-8, as every modern editor does). Star or unstar any stock on the Stocks tab. The em dash is rewritten as `Ã¢â‚¬â€` and the next read crashes. |
| **Root cause** | `Path.read_text()` with no encoding uses the computer's default. On Windows that's cp1252, not UTF-8. The app *writes* the file as UTF-8 (`watchlist._write`), so reading and writing disagreed, and each edit made it worse. Mac and Linux default to UTF-8, which is why it didn't show up there. |
| **Fix** | `market_tools.read_watchlist_text()` reads the bytes as UTF-8 (skipping a byte-order mark), and falls back to cp1252 for files saved by older Windows editors. Every reader uses it. `analyst_prompt.md` is read as UTF-8 too. |
| **Regression tests** | `test_bug01_*` (5), including `test_bug01_the_app_always_names_an_encoding_for_text_files`, which fails if any project file reads or writes text without naming an encoding |
| **Lesson** | On Windows, always pass `encoding="utf-8"` to `read_text`, `write_text` and `open`. The guard test enforces it. |

### BUG-02: "database is locked" when two threads create a database at once — High, fixed

| | |
|---|---|
| **Where** | `reports_db.connect()`, `search_index.connect()` |
| **Symptom** | `sqlite3.OperationalError: database is locked` at `PRAGMA journal_mode = WAL`, or `no such table: reports` on a read-only connection. Seen as a flaky `test_api_shows_alert_status` (2 failures in 35 suite runs), together with the log line `Search index update failed ...: database is locked`. |
| **How to reproduce (before the fix)** | Start 8 threads at the same instant, each opening a brand-new database with `reports_db.connect()` (half read-only). In two runs of 40 attempts, 16 and 22 failed. For `search.db`, 27 of 40 failed. |
| **Root cause** | Two problems on a brand-new file. (1) Two connections setting up WAL mode and the tables at once can make SQLite refuse one of them *immediately*: SQLite won't wait when waiting could deadlock, so the 10-second timeout doesn't help. (2) The read-only path checked `path.exists()`. A file another thread had *just* created passed that check, and was read before its tables existed. The API does exactly this on its first start: `lifespan` starts an index update in a background thread while the first page load opens the database. |
| **Fix** | `reports_db.SETUP_LOCK`: within one program, creating and setting up a database (including the read-only path's "does it exist yet?" check) happens one thread at a time. `search_index.connect()` uses the same lock. Read-only connections still never write to an existing database. On an existing database the lock is held for about 1 ms per writable connection (measured: 1.4 ms) and 0.2 ms per read-only one. |
| **Regression tests** | `test_bug02_a_new_reports_database_can_be_opened_by_many_threads_at_once`, `test_bug02_a_new_search_index_can_be_opened_by_many_threads_at_once` |
| **Limit** | The lock covers threads within one program. Two separate programs creating the same brand-new database within milliseconds of each other (a scheduled run and the API both starting for the very first time) could still collide once. On any database that already exists, this can't happen. |
| **Lesson** | Flaky tests are real bugs until proven otherwise. Run the suite many times before a release ([step 2](#step-2-run-it-again-and-again-flaky-tests)). |

### BUG-03: a missing price in Yahoo's data was reported as a real figure — Medium, fixed

| | |
|---|---|
| **Where** | `market_tools._measure()`, `_intraday_moves()` |
| **Symptom** | Market closed: if the latest daily row had no close (NaN), the stock showed `last_close: nan`, `return_5d_pct: nan`, and the *previous* day's return labelled as the latest session's. Market open: one empty 5-minute bar made every figure NaN, so the stock could never be flagged. |
| **Root cause** | yfinance can return rows with no price (a bar not filled in yet, or a data glitch). The code used them as they were. `pct_change()` turns them into gaps that `dropna()` removed from the returns, but not from the prices. `prices.py` already dropped such rows for the charts; `market_tools.py` didn't. |
| **Fix** | `.dropna(subset=["Close"])` on both downloads, so a row with no price counts the same as a missing row (which the code already handled). |
| **Regression tests** | `test_bug03_*` (3). They compare against the same data with the row removed, so the expected figures are exact. |

### BUG-04: unusual digits in a number crashed four endpoints with a 500 — Medium, fixed

| | |
|---|---|
| **Where** | `api._limit()` (used by `/api/reports`, `/api/alerts`, `/api/search`, `/api/tickers/{t}/history`), `api.followups_view()` |
| **Symptom** | `GET /api/reports?limit=²` → `500 Internal Server Error` (`ValueError` in `int()`) |
| **Root cause** | `str.isdigit()` is true for superscripts like `²`, which `int()` can't read |
| **Fix** | Accept only ASCII digits: `raw.isascii() and raw.isdigit()` |
| **Regression tests** | `test_bug04_unusual_digits_in_numbers_are_a_clear_400` (6) |

### BUG-05: `true` in Claude's calendar reply was read as the number 1 — Low, fixed

| | |
|---|---|
| **Where** | `events.validate()` |
| **Symptom** | `"sources": [true]` cited the first article, and `"same_as": true` attached a news item to calendar event 1 (moving it to that event's date) |
| **Root cause** | In Python, `True` is an `int`, so `isinstance(True, int)` is true. `stories.parse_reply()` already guarded against this with `type(r) is int`; `events.py` didn't. |
| **Fix** | `type(r) is int` and `type(same_as) is int` |
| **Regression tests** | `test_bug05_*` (2) |

### BUG-06: a zero close failed the whole chart — Low, fixed

| | |
|---|---|
| **Where** | `prices.get_prices()` |
| **Symptom** | `502: couldn't load prices for ... (float division by zero)` |
| **Fix** | No % change for the day after a zero close |
| **Regression test** | `test_bug06_a_zero_price_doesnt_break_the_chart` |

### BUG-07: "Remove" left a ticker that was listed twice — Low, fixed

| | |
|---|---|
| **Where** | `watchlist.remove()` |
| **Symptom** | With `AAPL` on two lines (added again by hand), Remove said it was done, but the stock was still tracked and still shown |
| **Fix** | Remove every line for that ticker |
| **Regression test** | `test_bug07_removing_a_stock_listed_twice_removes_it` |

### BUG-08: the daily summary crashed on a missing figure — Low, fixed

| | |
|---|---|
| **Where** | `alerts.summary_payload()` |
| **Symptom** | `TypeError: unsupported format string passed to NoneType.__format__`. The summary was marked failed and retried, and failed, after every later run. |
| **Root cause** | A flagged stock's return can be stored empty (SQLite stores NaN as NULL, see BUG-03). The intraday flag alert already handled this (`pct = t["return_1d_pct"] or 0`); the summary didn't. |
| **Fix** | Leave out a missing figure instead of formatting it. Lines with figures are unchanged. |
| **Regression test** | `test_bug08_summary_handles_a_flagged_stock_without_figures` |

### BUG-09: the live data check could never reach Yahoo — Medium (a test bug), fixed

| | |
|---|---|
| **Where** | `tests/test_market_tools.py::test_live_data` |
| **Symptom** | `LIVE_TESTS=1 pytest -k live` → `KeyError: 'AAPL'` from `FakeTicker`, on the original code too |
| **Root cause** | The autouse fixture replaces `Ticker` on the shared `yfinance` module. The live test "undid" it with `yfinance.Ticker`, which by then *was* the fake. It's skipped by default, so nobody saw it fail. |
| **Fix** | Save the real class when the test file loads (`REAL_TICKER`), and use that. The live test also checks it's the real one. |
| **Regression test** | `test_bug09_the_live_check_keeps_the_real_yahoo_finance` (runs offline, every time) |
| **Lesson** | A skipped test can rot. Run the live checks before each release ([step 3](#step-3-live-data-checks)). |

### BUG-10: an edit on the Stocks tab could fail with "Access is denied" on Windows — Medium, fixed

| | |
|---|---|
| **Where** | `watchlist._write()` |
| **Symptom** | `PermissionError: [WinError 5] Access is denied: '...\.watchlist-qdkx652h.tmp' -> '...\watchlist.txt'`, a 500 from add, remove, star or unstar. Found when `python demo.py build` added stocks through the API while recorded runs were reading the list. |
| **How to reproduce (before the fix)** | Open `watchlist.txt` in Python (`open(path, "rb")`) and keep it open, then star a stock. Or, with nothing else: on Windows, `os.replace(new, path)` while any other handle has `path` open fails with WinError 5, and works as soon as it's closed. |
| **Root cause** | Each edit writes a temporary file and swaps it in with `os.replace`, so a reader sees the old list or the new one, never half of each. Windows refuses to replace a file that anything has open: a run or the API reading the list at that instant, or a virus scanner looking at the new file. Mac and Linux allow it, which is why the guides' testing didn't see it. |
| **Fix** | `watchlist._replace()` tries the swap again every 50 ms, for up to 2 seconds, then gives up with the same error as before. Readers hold the file for milliseconds, so the edit simply waits. |
| **Regression tests** | `test_bug10_*` (3) |
| **Lesson** | On Windows, anything that replaces or deletes a file other parts of the program read needs to expect a brief "Access is denied". |

### BUG-11: the filings command line crashed when its output went to a log file — Low, fixed

| | |
|---|---|
| **Where** | `filings.py` (`main`, and the `show`, `read` and `check` commands' printing) |
| **Symptom** | `UnicodeEncodeError: 'charmap' codec can't encode character '✓'` from `python filings.py show ...  > filings.log`, or from the scheduled `python filings.py check >> filings.log` that the filings guide suggests, once a figure is confirmed or a filing's wording has a character outside cp1252. A console was fine. |
| **How to reproduce (before the fix)** | `python -c "print('✓')" > out.txt` on Windows. |
| **Root cause** | On Windows, Python writes to a console in UTF-8, but to a file or a pipe in the computer's default encoding, cp1252, which has no "✓" or "✗". |
| **Fix** | `filings._utf8_output()`, called first by every command: output that isn't already UTF-8 is switched to UTF-8 (unprintable characters become "?"). A console is left as it is. |
| **Regression tests** | `test_bug11_*` (3) |
| **Lesson** | The same lesson as BUG-01, for output: never rely on Windows' default encoding. |

### BUG-12: the live demo couldn't be built, because the after-close run started by itself — Low, fixed

| | |
|---|---|
| **Where** | `market-agent-testenv/testenv.py` (`make_app`), which the demo uses too. Not in this repository. |
| **Symptom** | `python demo.py build` stopped with `RuntimeError: Run now gave 409: {"error":"A report is already being written..."}` |
| **Root cause** | This project's API runs the day's final report by itself after the close (`AUTO_CLOSE_RUN`, a local change the guides don't have). The test environment hosts the real API, so that loop started there too, on the sample's clock. The demo's recording now takes longer (it records a read of every filing), long enough for the loop's first check, which found the sample's clock past 4:15pm and started a run of its own in the middle of the demo's. |
| **Fix** | `make_app` sets `api.AUTO_CLOSE = False`: the test environment has no schedule of its own (its guide says so), and `update` and `finalize` stand in for scheduled runs. The test environment guide's appendix and safety table say so too. |
| **Regression test** | `test_testenv.py::test_offline_run_now_updates_the_latest_day` checks `api.AUTO_CLOSE` is off |
| **Lesson** | A local change to the program needs checking in the test environment and demo too, not only in the program's own tests. |

### BUG-13: a watcher test failed about 1 run in 15 on this machine — Low (a test bug), fixed

| | |
|---|---|
| **Where** | `tests/test_watchlist.py::test_editing_watchlist_txt_by_hand_updates_open_pages` |
| **Symptom** | `TimeoutError`: no `watchlist_changed` event within 2 seconds. 1 failure in 10 full-suite runs; then, run on its own, 1 in 12. |
| **How to reproduce (before the fix)** | Run the test 20 times. Or the same steps in a script with timings: 3 failures in 40. |
| **Root cause** | The test gives the watcher 0.3 s to take its first look before it edits the file. That first look creates the brand-new test database, which usually takes 45 ms. About 1 time in 100 on this machine, it took 1.3 to 2.3 s, so the watcher looked after the edit and saw nothing change. Timing each step showed the time is all in closing the new database (1,332 ms), not in reading it. On close, SQLite deletes its WAL files, and on Windows, when another program has one open (most likely the virus scanner, checking the new file), it retries 10 times, waiting 25, 50 … 250 ms: 1,375 ms in all, which matches. It isn't from the filings code: the same create-and-close is in BUG-02's fix, and plain SQLite does it too. |
| **Fix** | The test creates the database before starting the watcher. Instrumented scenario afterwards: 0 failures in 100. |
| **Effect on the program** | None worth changing: creating a brand-new database can take about 1.4 s longer on Windows, once. |
| **Lesson** | A test with a fixed wait (here 0.3 s) is only as reliable as the slowest thing before it. On Windows, file creation and deletion can stall for a second or more. |

---

## 5. Open issues and what wasn't tested

### 5.1 OPEN-01: the "other websites" check trusts the Host header — security, not fixed

`api._post_guard()` stops other websites from triggering runs, questions and watchlist edits through your browser. It allows a request whose `Origin` equals the API's own address, and it works out that address from the request's `Host` header. With **DNS rebinding**, a malicious page makes its own domain point at `127.0.0.1`. The browser then sends `Origin: http://evil.example:8000` and `Host: evil.example:8000`, which match, so the check passes. That page could start runs (up to $1 each, one a minute), ask questions ($0.25 each), edit the watchlist, and read reports.

- **Likelihood:** low. It needs a targeted attack on this app's port while the API is running.
- **Why it isn't fixed here:** the fix changes which addresses the app accepts. Opening it from another device on your network, or the public demo, would need its address added to a setting. That's a decision for you, not a test change.
- **Recommended fix:** only treat the request as same-origin when the host is `localhost`, `127.0.0.1` or `[::1]`, or is listed in `FRONTEND_ORIGINS` (or a new `ALLOWED_HOSTS` setting). Starlette's `TrustedHostMiddleware` does this for every request.
- **Since the filings round:** **Check now** and **Read this filing** (`POST /api/filings/check` and `/api/filings/read`) use the same check, so they share this issue. A filing read costs a few cents (at most $0.50), runs one at a time and 30 seconds apart, and only for filings already listed.
- **Tracking:** `test_open01_a_rebound_host_cannot_post` is marked `xfail(strict=True)`. When the fix lands, the test passes, pytest reports it as `XPASS(strict)` (a failure), and you remove the `@pytest.mark.xfail` line. That way the fix is confirmed and stays tested.

### 5.2 What wasn't tested

| Not tested | Why | How to cover it |
|---|---|---|
| The React frontend (`frontend/src`) | No JavaScript test runner is set up | Add Vitest and React Testing Library. Start with `Markdown.jsx` (link sanitising), `safeUrl`, and `format.js`. |
| Agent runs with Claude | Costs money per run | `market-agent-testing.md` section 6, after any change to the prompt or tools |
| Discord, calendar and follow-through checks with real services | Need a webhook or API credits | `market-agent-testing.md` section 7 |
| The scheduled job | Needs Task Scheduler or cron | `market-agent-testing.md` section 8 |
| Two separate programs creating a brand-new database at once | A cross-process timing test would be slow and unreliable | See BUG-02 "Limit". Low risk: it only matters on the very first start. |
| The test environment and demo folders (`market-agent-testenv/`, `market-agent-demo/`) | Not in this repository | Run their own `pytest -v` as their guides describe. They read `watchlist.txt` through the same code, so BUG-01's fix applies there too. (Second round: both were run, 40 and 18 passed.) |
| The real SEC (`test_live_filings`, `python filings.py check` against sec.gov) | `SEC_CONTACT` must be your real name and email, which the SEC sees with every request. It wasn't set, and wasn't set for you. | Add `SEC_CONTACT=Your Name you@yourmail.com` to `.env`, then `$env:LIVE_TESTS=1; pytest -v -s -k live_filings` and the filings guide's section 12.5 |
| Why `test_events.py::test_update_now_has_a_cooldown_and_runs_one_at_a_time` failed once | It failed once in 20 suite runs and not in 35 more, so its full traceback wasn't caught | Its wait limit is now 20 s. If it fails again, run step 2 with `--tb=long` saved per run (as in row 28c) and log what it shows |
| First takes by real Claude, and their real cost | Costs a few cents a read | `python filings.py read ACCESSION` on a recent results announcement (filings guide, section 12.5). It prints the cost. |

### 5.3 Guides to update

- `market-agent-testing.md` section 3 says `415 passed, 4 skipped` (after the filings guide). On Windows today the full suite gives **584 passed, 5 skipped, 1 xfailed**: 590 tests in all, which is the guide's 419 (415 + 4), plus `test_regressions.py` (29) and `test_edge_cases.py` (133), plus 9 tests this project added to the guides' own files (such as the after-close run's, in `test_frontend_api.py`). The 5th skip is the Windows-only file-permissions test, and the xfail is OPEN-01. (First round: the guide said 276 passed, 3 skipped, and the suite gave 439 passed, 4 skipped, 1 xfailed.)
- The guide's [appendix](market-agent-testing.md#appendix-test-file-source) holds the full source of `tests/test_market_tools.py`, and says to replace the file with it. **That would undo the BUG-09 fix.** Copy the two changes into the appendix (the `REAL_TICKER = market_tools.yf.Ticker` line near the top, and its use in `test_live_data`), or stop replacing the file from the guide.
- `test_events.py::test_live_calendar_data` uses the same "undo the fake with `yfinance.Ticker`" line. It works today only because that test doesn't use the `cal` fixture, which is what swaps in the fake (and isn't autouse). If the fixture is added to the test or made autouse, the same bug appears. Saving the real class at import, as `test_market_tools.py` now does, would make it safe.

---

## 6. The testing process (reuse this for every version)

Run these steps, in order, before calling a version done. Steps 1-5 are free and take about 15 minutes. Steps 6-7 cost a little and are needed only when what they cover has changed.

Commands are for Windows PowerShell from the project folder, with the virtual environment active (`.venv\Scripts\Activate.ps1`). Mac/Linux equivalents are given where they differ.

### Step 1: Baseline

```powershell
pip install pytest
pytest -q
```

Write down the result in your run log ([template](#71-run-log-entry)). **Expected now:** `584 passed, 5 skipped, 1 xfailed` on Windows. On Mac/Linux it should be `584 passed, 5 skipped, 1 xfailed` too: the file-permissions test runs there, and the Windows-only BUG-10 test is skipped instead (not yet confirmed on a Mac). Any change in the numbers needs an explanation: new tests, removed tests, or a bug.

- `failed`: a real problem. Read the first failure only, fix it, run again.
- `XPASS(strict)` on an `open01` test: the open issue has been fixed. Remove its `xfail` mark and move it to the bug log as fixed.
- More `skipped` than expected: check the reasons with `pytest -rs`.

### Step 2: Run it again and again (flaky tests)

One green run isn't enough: BUG-02 failed only about 1 run in 17. Run the suite 20 times:

```powershell
1..20 | ForEach-Object { pytest -q -p no:cacheprovider 2>&1 | Select-Object -Last 1 }
```

Mac/Linux: `for i in $(seq 20); do pytest -q -p no:cacheprovider | tail -1; done`

Every line should be identical. If one isn't, rerun with `-rf --tb=long`, saving each run's output to its own file, until you catch the failing test's traceback, then log it as a bug. Look for anything that depends on timing: threads, background tasks, the API's `lifespan` (any test using `with TestClient(api.app)`), and file or database creation.

### Step 3: Live data checks

```powershell
$env:LIVE_TESTS=1; pytest -v -s -k live; Remove-Item Env:LIVE_TESTS
```

**Expected:** 4 passed with `SEC_CONTACT` set (3 passed, 1 skipped without it), printing real figures for AAPL, its sector (XLK), the market backdrop, Apple's calendar and a "costco" search, and Apple's latest filings, press release and quarterly revenue from the SEC. These catch yfinance changing its data format, which the offline fakes can't. Run them after upgrading yfinance or pandas, and before every release.

### Step 4: Test what changed, and its edges

For each feature added or changed in this version:

1. **Make sure its normal behaviour is tested** in the feature's own test file. Each guide adds those tests.
2. **Add edge cases to `tests/test_edge_cases.py`**, under the matching heading. Go through this checklist:

| Check | Example from this round |
|---|---|
| Every limit: exactly at it, and one past it | `limit=365` works and `366` is a 400. Giving back 25% is held and 26% is faded. |
| Empty, blank and missing input | `"   "` as a question, an empty watchlist, no volume history |
| Odd text: unicode, emoji, quotes, very long | `Robert'); DROP TABLE`, a 700 KB report, Japanese search text |
| Odd numbers: zero, NaN, negative, non-ASCII digits | Flat prices (std 0), a zero close, `limit=²` |
| Bad data from Yahoo | Rows with no price, too little history, a download error |
| Bad replies from Claude | No JSON, the wrong shape, `true` where a number belongs, citations out of range, `javascript:` links |
| Requests from other websites | `Origin: null`, a wrong content type, broken JSON, `../` in paths |
| Two things at once | Two threads creating a database, two edits to the watchlist |
| Windows and Mac/Linux differences | Text encoding (cp1252 vs UTF-8), file permissions, paths with spaces |

3. **Run the new tests against the code before you rely on them.** A test that passes the first time might not test anything; that's what step 5 checks.

### Step 5: Check the tests catch real bugs (mutation check)

For each important rule, plant a small bug and confirm a test fails:

1. Change one thing: `>=` to `>`, `< 25` to `< 24`, or delete a filter line.
2. Run the related tests: `pytest -q tests/test_edge_cases.py -k <name>`.
3. **A test must fail.** If none does, add one.
4. Change it back, and check `git diff` shows no leftover change.

Watch for a check written in two places, like `len(daily) < 25`: change both, or the second one hides the first. `market-agent-testing.md` section 3 lists more mutations for `market_tools.py`.

### Step 6: Agent test runs, alerts, calendar and follow-through (cost money)

Follow `market-agent-testing.md`:

- Section 6 (agent runs) after changing `analyst_prompt.md` or any tool
- Section 7 (alerts, calendar, Stocks tab, follow-through) after changing those features
- Section 8 (schedule) after changing how runs are scheduled

### Step 7: Log what you found

For every failure that turns out to be a real bug:

1. **Reproduce it** in the smallest way you can: a short script in a scratch folder, not in the project.
2. **Write a regression test first**, in `tests/test_regressions.py`, under a new `BUG-NN` heading with a short explanation. Name it `test_bugNN_<what should happen>`.
3. **Run it and see it fail.** Record the failure in the run log.
4. **Fix the code**, as narrowly as you can.
5. **Run it and see it pass**, then run the whole suite (step 1) and the repeat run (step 2).
6. **Add it to the bug log** in this file ([template](#72-bug-log-entry)): symptom, how to reproduce, root cause, fix, test name, and the lesson if there is one.

For a problem you won't fix yet, write the test anyway, mark it `@pytest.mark.xfail(strict=True, reason="OPEN-NN: ...")`, and add it to section 5. The suite then reminds you of it on every run, and tells you when it's been fixed.

### Release gate

A version is ready when all of these are true:

- [ ] Step 1: no failures, and the counts are explained
- [ ] Step 2: 20 identical runs
- [ ] Step 3: live checks pass
- [ ] Every new feature has edge-case tests (step 4), and each important rule survived a mutation check (step 5)
- [ ] Steps 6-7 done for whatever changed
- [ ] Every new bug has a regression test and a bug log entry; every open issue has an xfail test
- [ ] The expected counts in this file and in `market-agent-testing.md` are updated

---

## 7. Templates

### 7.1 Run log entry

```markdown
| # | What was run | Result | Effect on the program |
|---|---|---|---|
| 1 | Suite, baseline (version X, commit abc1234) | 439 passed, 4 skipped, 1 xfailed (30 s) | — |
```

### 7.2 Bug log entry

```markdown
### BUG-NN: <what goes wrong, in plain words> — <High/Medium/Low>, <fixed/open>

| | |
|---|---|
| **Where** | file and function |
| **Symptom** | the exact error message, or what the user sees |
| **How to reproduce (before the fix)** | the smallest steps that show it |
| **Root cause** | why it happened |
| **Fix** | what changed |
| **Regression tests** | test_bugNN_... |
| **Lesson** | what to do differently next time (optional) |
```

### 7.3 Regression test

```python
# ---------------------------------------------------------------------------
# BUG-NN: <one or two lines: what went wrong and when>
# ---------------------------------------------------------------------------

def test_bugNN_<what_should_happen>(temp_files):
    ...  # set up the case that used to fail
    assert ...  # what should happen now
```
