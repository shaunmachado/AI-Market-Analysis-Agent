# Market Analyst Agent: Upcoming Events Calendar

A **Calendar** tab that shows what's coming up for your watchlist:

- earnings dates
- ex-dividend dates
- dated events found in the news, such as product launches, court hearings, regulatory decisions and shareholder votes

Each day shows just the company names. Click a date to open that day's page, with what the news says about each event and links to the articles.

The calendar updates itself once a day when the market opens, and there's an **Update now** button for updating it during the day.

This builds on `market-agent-alerts.md` (and the guides before it). This guide's files include all their changes.

---

## Contents

1. [What you get](#1-what-you-get)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Add the events scanner](#4-step-1-add-the-events-scanner)
5. [Step 2: Add the calendar to the API](#5-step-2-add-the-calendar-to-the-api)
6. [Step 3: Add the Calendar tab](#6-step-3-add-the-calendar-tab)
7. [Step 4: Add the tests](#7-step-4-add-the-tests)
8. [Step 5: Try it](#8-step-5-try-it)
9. [Step 6: Update it daily at the market open](#9-step-6-update-it-daily-at-the-market-open)
10. [Test it](#10-test-it)
11. [Settings](#11-settings)
12. [Costs](#12-costs)
13. [Commands and API reference](#13-commands-and-api-reference)
14. [Accuracy and safety](#14-accuracy-and-safety)
15. [Troubleshooting](#15-troubleshooting)
16. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What you get

**The month view.** Each day shows only the companies with something on, and today is circled. Past days stay on the calendar as history, shown more quietly. On a phone, the days show tickers instead of names.

```
  Mon          Tue          Wed          Thu              Fri
  9            10           11           12               13
  Microsoft                              Microsoft
  16           17           18           19               20
  Apple                                  JPMorgan Chase
```

**A day's page.** Click any date. Its events open below the calendar, and the address changes to `#/calendar/2026-11-12`, so you can bookmark or share a day:

```
THURSDAY, NOVEMBER 12, 2026                                              Close

Microsoft  MSFT  [In the news]
Regulator's decision on deal
A decision on the proposed acquisition is due on November 12, the regulator said.
  • MSFT: Regulator to rule on Microsoft deal by November 12 · Sample Wire · Nov 6
```

(These examples are from the test environment, so the companies' news is simulated.)

**Three kinds of event:**

| Kind | Where it comes from | What the day's page shows |
|---|---|---|
| **Earnings** | Yahoo Finance's company calendar | The date, marked "(date not confirmed)" if Yahoo only has an estimated window (with the window shown). Analysts' average earnings-per-share estimate. A link to the company on Yahoo Finance. If recent news previews the results, an "In the news" line and the article links |
| **Ex-dividend** | Yahoo Finance's company calendar | The ex-dividend date and when the dividend is paid |
| **In the news** | Recent headlines, read by Claude | The event, one or two sentences from the articles, and links to every article it came from |

**What stays on the calendar:**

| Situation | What happens |
|---|---|
| An event's date passes | It stays, as history |
| Yahoo moves an upcoming earnings or dividend date | The old date is removed and the new one added |
| The article about a news event drops out of the news feed | The event stays until its date |
| The news says an event moved | The same event moves to the new date, keeping its earlier links |
| The news got something wrong | Remove it with `python events.py remove ID` (section 13) |

---

## 2. How it works

```
events.py scan    (daily at the market open, or "Update now" in the app)
  for each watchlist company:
    1. Yahoo Finance calendar ──▶ earnings and ex-dividend dates  ──▶ saved straight away
    2. Yahoo Finance news ──────▶ up to 10 recent headlines and summaries
  3. Claude reads all the headlines once, numbered [1], [2], ...
       → "events with a specific future date, citing the article numbers"
  4. every event Claude suggests is checked in code:
       ✓ a ticker on your watchlist
       ✓ cites at least one article that this scan actually read
       ✓ a real date, from today to 60 days ahead
       ✓ not a repeat of an event already on the calendar
     anything else is left out (and listed, so you can see why)
  5. saved in reports.db (tables: events, event_scans) ──▶ the Calendar tab
```

- **Dates you can trust come from structured data.** Earnings and dividend dates are Yahoo's, not Claude's. Claude can attach a news preview to an earnings date, but it can never move it.
- **Claude only reads.** It has no tools and no internet access during the scan. It sees the headlines and short summaries, not the web addresses; the code adds the real links afterwards from the articles it fetched. So every link on the calendar is to an article the scan actually read.
- **Claude knows what's already there.** Each scan sends the upcoming events with their ids. If Claude finds the same event again, it says so (`same_as`), so events aren't doubled and a moved date updates the same event.
- **If Claude can't be reached** (no key, an outage, or the cost limit), the Yahoo dates are still saved. The scan is marked "partial", with the reason.
- **One scan at a time.** A second scan, from the schedule or the button, is refused while one is running. A scan that crashed is cleared after 10 minutes.

---

## 3. Before you start

- [ ] You've done `market-agent-alerts.md`, and `pytest` shows `148 passed, 1 skipped`.
- [ ] `ANTHROPIC_API_KEY` is set (as for briefs). Without it, the calendar still gets earnings and dividend dates, just no news events.

No new packages are needed.

---

## 4. Step 1: Add the events scanner

Create `events.py` from the [appendix](#eventspy).

It reuses the news tool from `market_tools.py` and the database from `reports_db.py`. It adds two tables to `reports.db` the first time it runs:

| Table | Holds |
|---|---|
| `events` | One row per event: date, ticker, company, kind, title, details, date note, news note, source links, and when it was first and last seen |
| `event_scans` | One row per scan: when, how it was started, how many headlines and events, anything left out, its Claude cost, and any problem |

---

## 5. Step 2: Add the calendar to the API

Replace `api.py` with the [appendix](#apipy) version. It adds:

| Endpoint | What it does |
|---|---|
| `GET /api/calendar?start=&end=` | Events between two dates (up to 100 days), the server's "today", and the last scan |
| `POST /api/calendar/scan` | "Update now": starts a scan. One at a time, with a 5-minute cooldown to cap cost |
| `GET /api/calendar/scan` | The "Update now" scan in progress, or the last one |

**Live updates:**

- While an update runs, the page shows its progress ("Checking AAPL's calendar and news", "Reading 23 headlines…").
- When any update finishes, open calendars reload by themselves. That includes the daily scheduled one, which is a separate program: the API notices it in the database within a couple of seconds.

The API imports `events.py` as `upcoming`, because `events` is already the name of its live-updates endpoint.

---

## 6. Step 3: Add the Calendar tab

Replace or add these files in `frontend/src/`:

| File | Change |
|---|---|
| `components/CalendarTab.jsx` | **New:** the month view, the day's page and "Update now" |
| `App.jsx` | The Calendar tab and its live updates. Also a fix: the Previous days tab now ignores a calendar date in the address |
| `useRoute.js` | Addresses `#/calendar` and `#/calendar/YYYY-MM-DD` |
| `api.js` | `getCalendar()` and `startCalendarScan()` |
| `format.js` | `formatFullDate()` ("Thursday, November 12, 2026") |
| `styles.css` | The calendar's styles, in light and dark mode |

Then rebuild if you serve the built app:

```bash
cd frontend
npm run build
```

**How the tab works:**

- **Navigating:** use ‹ and › to change months, and **This month** to come back.
- **Opening a day:** each day is a link. Click it, or Tab to it and press Enter, to open its page. Screen readers hear the full date and the companies, for example "Monday, November 16, 2026: Apple".
- **Busy days:** a day with more than three companies shows "+2 more".

---

## 7. Step 4: Add the tests

Add `tests/test_events.py` from the [appendix](#teststest_eventspy), then run:

```bash
pytest -v
```

**Expected result:** `195 passed, 2 skipped`. The second skipped test is the live calendar check (section 10.3).

---

## 8. Step 5: Try it

1. **Run a scan from the terminal:**

   ```bash
   python events.py scan
   ```

   It prints a line per company, then a summary like `ok: 4 news events from 37 headlines, $0.041`. It also lists anything it left out, and why (for example `left out: AAPL 'Holiday sale': no valid date`).

2. **Look at the calendar:**

   ```bash
   python events.py list                 # upcoming events, with their ids
   python events.py show 2026-11-12      # one day, with details and links
   ```

3. **Open the app's Calendar tab.** Click a few dates, follow a link, and try **Update now**.

---

## 9. Step 6: Update it daily at the market open

Add a scheduled job, the same way as the brief (main guide, section 8). The `--only-if-open` option makes it skip weekends, holidays and any day the market isn't open by then.

**macOS / Linux (cron).** Add this line to your crontab (`crontab -e`), below the `ANTHROPIC_API_KEY=...` line already there:

```
35 9 * * 1-5   /path/to/market-agent/.venv/bin/python /path/to/market-agent/events.py scan --only-if-open >> /path/to/market-agent/run.log 2>&1
```

**Windows (Task Scheduler):**

```powershell
schtasks /create /tn "MarketCalendar" /sc weekly /d MON,TUE,WED,THU,FRI /st 09:35 /tr "C:\path\to\market-agent\.venv\Scripts\python.exe C:\path\to\market-agent\events.py scan --only-if-open"
```

9:35am New York time is five minutes after the open, so the morning's news is in. Times are in your computer's time zone, so adjust if that isn't New York time. The computer must be on and awake. If it missed the time, press **Update now**.

---

## 10. Test it

### 10.1 Automated tests

| Test | Proves that |
|---|---|
| `test_short_company_names` (7 cases) | "JPMorgan Chase & Co." shows as "JPMorgan Chase", "NVIDIA Corporation" as "NVIDIA", and so on |
| `test_earnings_and_dividend_dates_from_yahoo` | Yahoo's earnings date, EPS estimate range, ex-dividend date and pay date become two events, with a Yahoo link |
| `test_an_unconfirmed_earnings_window_is_marked_as_an_estimate` | A two-date window goes on its first day, titled "(date not confirmed)", with the window explained |
| `test_past_and_far_off_dates_are_left_out` | Past dates, and dates more than 60 days ahead, aren't added |
| `test_other_calendar_formats_are_understood` (4 cases) | An older yfinance table format, datetimes, text dates and epoch seconds all work |
| `test_missing_or_odd_calendar_data_gives_no_events` (6 cases) | Missing or strange calendar data gives no events and no crash |
| `test_a_scan_saves_calendar_dates_and_checked_news_events` | Valid news events are saved with their real article links. Six bad ones are left out, each with its reason: off the watchlist, no article, an article that doesn't exist, in the past, too far ahead, no real date. Claude's prompt has today, the horizon, the calendar so far and numbered articles |
| `test_scanning_again_doesnt_duplicate_events` | A second identical scan updates the same rows |
| `test_a_moved_news_event_keeps_its_place_on_the_calendar` | When the news moves an event, it moves (same id) and keeps both articles |
| `test_news_about_an_earnings_date_is_attached_without_changing_the_date` | News can add a preview to an earnings date, but Claude can't change Yahoo's date |
| `test_yahoo_moving_an_earnings_date_replaces_the_old_one_but_never_touches_the_past` | A moved earnings date replaces the old one; past events are untouched |
| `test_news_events_stay_after_their_article_drops_out_of_the_feed` | News events stay until their date; with no headlines, Claude isn't asked at all (no cost) |
| `test_if_claude_fails_the_calendar_dates_are_still_saved` | Claude failing gives a "partial" scan, with Yahoo's dates still saved |
| `test_one_companys_calendar_failing_keeps_its_saved_dates` | A Yahoo error for one company keeps that company's saved dates |
| `test_claudes_reply_is_read_even_with_extra_text` (3 cases) | JSON wrapped in a code fence or a sentence is still read |
| `test_an_unreadable_reply_is_an_error` (4 cases) | A reply without the expected JSON is an error, not a silent empty calendar |
| `test_only_one_scan_runs_at_a_time` | A second scan is refused while one runs; a crashed one is cleared after 10 minutes |
| `test_the_daily_schedule_skips_days_the_market_is_closed` | `--only-if-open` does nothing when the market isn't open |
| `test_command_line_scan_list_show_and_remove` | The terminal commands print what's described in section 13, and `remove` deletes an event |
| `test_api_calendar_works_before_the_first_scan` | The calendar endpoint works on a new database, defaulting to this month |
| `test_update_now_scans_and_the_calendar_shows_the_results` | "Update now" runs a scan, recorded as manual, and the calendar shows its events |
| `test_update_now_has_a_cooldown_and_runs_one_at_a_time` | Pressing again too soon gives 429; a second scan while one runs gives 409 |
| `test_other_websites_cannot_start_a_scan` | Another website can't start a scan through your browser |
| `test_api_calendar_rejects_bad_dates` (4 cases) | Bad dates, reversed ranges, over-long ranges and impossible dates (30 February) get a clear error |
| `test_live_updates_announce_a_scan_from_the_daily_schedule` | A scan by another program (the schedule) is announced to open pages |
| `test_live_calendar_data` | Real Yahoo data (skipped unless you turn it on, section 10.3) |

**Check the tests catch real bugs.** Make one of these temporary changes in `events.py`, run `pytest tests/test_events.py`, then change it back. Each was tried:

| Temporary change | Tests that fail |
|---|---|
| In `validate`: `if not today <= event_date <= horizon_end:` → `if False:` | 5 tests, starting with `test_a_scan_saves_calendar_dates_and_checked_news_events` |
| In `validate`: `if not refs:` → `if False:` (accept events with no article) | The same 5 |
| In `save_calendar`: delete the final `DELETE FROM events ...` statement | `test_yahoo_moving_an_earnings_date_replaces_the_old_one_but_never_touches_the_past` |

### 10.2 What was also tested

- **From the guides alone:** the project was rebuilt from the guides (including this one), and all tests passed.
- **In a real browser, against the test environment.** Its calendar has two months of simulated history and the weeks ahead. All 8 checks passed, with no browser errors:
  1. The month shows just company names, with today marked.
  2. A date opens its page, with the event, the news and a link that opens in a new tab.
  3. December's unconfirmed earnings date says so, with the estimate and a Yahoo link.
  4. An empty day says so. A link to a day opens its month, and Back works.
  5. **Update now** shows progress, then reloads. Pressing again too soon explains the wait.
  6. Days work from the keyboard, with screen-reader labels.
  7. On a phone: tickers instead of names, no sideways scrolling, and an opened day scrolls into view.
  8. Dark mode renders.

  The Today, Previous days, chart, search and alerts checks from the earlier guides also still pass.

**Not tested here:** real Yahoo Finance calendar data, and Claude reading real headlines (no internet access while building this). Do the checks below once.

### 10.3 Checks with real data

- [ ] `LIVE_TESTS=1 pytest -v -s -k live_calendar` passes and prints Yahoo's calendar for AAPL, and the events made from it
- [ ] After `python events.py scan`, each company's next earnings date matches its investor-relations page (or Yahoo's quote page)
- [ ] Open three "In the news" events and follow their links: each article really gives that date
- [ ] The scan's printed cost is a few cents (section 12)
- [ ] The next morning, `run.log` shows the 9:35 scan, and the app's calendar says "Updated" with that time

---

## 11. Settings

At the top of `events.py`:

| Setting | Default | What it does |
|---|---|---|
| `HORIZON_DAYS` | `60` | How far ahead to look |
| `NEWS_PER_TICKER` | `10` | Headlines read per company |
| `MAX_EVENTS` | `60` | Most news events accepted from one scan |
| `SCAN_BUDGET_USD` | `0.25` | Hard stop on Claude's cost per scan |
| `STUCK_AFTER` | 10 minutes | When a "running" scan counts as crashed |
| `SYSTEM_PROMPT` | | What Claude is asked to find. Edit it to add or drop kinds of event |

In `api.py`: `CALENDAR_SCAN_COOLDOWN_SECONDS` (environment variable, default 300) sets the wait between "Update now" presses. In `components/CalendarTab.jsx`, `MAX_NAMES` (default 3) sets how many companies a day shows before "+N more".

---

## 12. Costs

- **Yahoo Finance:** free.
- **Claude:** one request per scan. It reads up to 10 headlines and summaries per company, and replies with a short list. With five companies, that's usually a few thousand words in, so a few cents per scan. The exact cost of each scan is printed by `events.py scan` and stored in `event_scans.cost_usd`.
- **Per month:** the daily scan is about 21 a month, plus any "Update now" presses. The 5-minute cooldown and the $0.25 per-scan cap keep this predictable.
- **Free scans:** a scan with no headlines (for example, Yahoo returned no news) doesn't call Claude at all.

---

## 13. Commands and API reference

```bash
python events.py scan                    # update now
python events.py scan --only-if-open     # what the daily schedule runs: skips unless the market is open
python events.py list                    # upcoming events, with ids
python events.py show 2026-11-12         # one day: details, notes and links
python events.py remove 42               # delete an event the news got wrong
```

A removed news event can come back if the same article is still in the news at the next scan. Remove it again after the article drops out.

`GET /api/calendar?start=2026-11-09&end=2026-11-15` returns:

```json
{
  "today": "2026-11-06",
  "start": "2026-11-09",
  "end": "2026-11-15",
  "events": [
    {"id": 19, "event_date": "2026-11-12", "ticker": "MSFT", "company": "Microsoft", "kind": "news",
     "title": "Regulator's decision on deal",
     "details": "A decision on the proposed acquisition is due on November 12, the regulator said.",
     "date_note": null, "news_note": null,
     "sources": [{"title": "MSFT: Regulator to rule on Microsoft deal by November 12", "publisher": "Sample Wire",
                  "url": "https://news.example.com/...", "published": "2026-11-06T13:30:00Z"}],
     "first_seen": "2026-11-06T14:35:12Z", "last_seen": "2026-11-06T14:35:12Z"}
  ],
  "last_scan": {"id": 10, "started_at": "2026-11-06T14:35:01Z", "finished_at": "2026-11-06T14:35:12Z",
                "trigger": "scheduled", "status": "ok", "tickers": 5, "articles": 37, "events_found": 4,
                "dropped": 0, "cost_usd": 0.041, "message": null},
  "scan": {"state": "idle", "started_at": null, "finished_at": null, "message": null, "result": null, "error": null}
}
```

**Leaving out the dates.** Without `start` and `end`, you get six weeks from the first of this month.

**`POST /api/calendar/scan` responses:**

| Code | Meaning |
|---|---|
| `202` | The scan started |
| `409` | One is running |
| `429` | Cooldown |
| `403` | The request came from another website |

**Live events on `/api/events`:**

| Event | When it's sent |
|---|---|
| `calendar_scan` | Progress of "Update now" |
| `calendar_updated` | Any scan finished |

---

## 14. Accuracy and safety

- **Check before acting.** News events come from headlines and short summaries, not full articles, and dates in the news change. Every event links to its source, so open it before relying on it. This is research, not investment advice.
- **Estimated earnings dates are marked.** Yahoo often shows a window until the company confirms. Those events say "(date not confirmed)" and give the window. Until then, a company's own investor-relations page is the authority.
- **Only dates, not times.** The calendar doesn't show whether earnings come before the open or after the close. The linked articles usually say.
- **News text can't take control.** Headlines are untrusted text, so:
  - Claude reads them with no tools.
  - Its reply is only accepted if it passes the checks in section 2.
  - The app shows everything as plain text, never as HTML.
  - Links only open if they're normal web addresses, in a new tab that can't reach back into the app.
- **What leaves your computer:** company names, tickers and the fetched headlines go to Anthropic during a scan, as with briefs. Nothing else is sent.

---

## 15. Troubleshooting

| Problem | Cause and fix |
|---|---|
| The calendar says "Not updated yet" | No scan has run. Press **Update now**, or run `python events.py scan`. |
| "Updated, but some sources couldn't be read: news scan: …" | Claude wasn't reached (check `ANTHROPIC_API_KEY` where the scan runs) or hit the cost cap. Yahoo's dates were still saved. |
| "… AAPL calendar: …" in that message | Yahoo didn't answer for that company, usually rate limiting. Its saved dates were kept; the next scan normally works. |
| "An events scan is already running" | Wait a minute. A scan that crashed is cleared automatically after 10 minutes. |
| "The calendar was just updated. Try again in … seconds" | The "Update now" cooldown (5 minutes). |
| A company never has news events | Its recent headlines didn't give specific dates. Run `python events.py scan` and check the "left out" lines. |
| An event looks wrong | Open its link. If the article doesn't support it, remove it with `python events.py remove ID` (ids are in `list` and `show`). |
| No earnings date for a company | Yahoo's date is more than 60 days away, or not announced yet. Raise `HORIZON_DAYS` to look further ahead. |
| The 9:35 scan didn't happen | The computer was asleep, the path is wrong, or the key isn't in the scheduler's environment. Check `run.log`. On market holidays, "skipped" is expected. |
| The Calendar tab is missing | Rebuild the frontend (`npm run build`), then hard-refresh. |
| `test_live_calendar_data` fails on `name == "Apple"` | Yahoo's company profile didn't load. Retry later, or run `pip install -U yfinance`. |

---

## Appendix: full source code

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
SCAN_BUDGET_USD = 0.25   # hard stop on Claude's cost per scan
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
    """'JPMorgan Chase & Co.' -> 'JPMorgan Chase', 'NVIDIA Corporation' -> 'NVIDIA'."""
    name = " ".join((name or "").split())
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

            if articles:
                emit({"type": "progress", "message": f"Reading {len(articles)} headlines for dated events"})
                known_rows = [dict(r) for r in conn.execute(
                    "SELECT id, ticker, kind, event_date, title FROM events WHERE event_date >= ? ORDER BY event_date",
                    (today.isoformat(),))]
                try:
                    reply, cost = ask_claude(build_prompt(articles, known_rows, today, horizon_end))
                    accepted, dropped = validate(parse_reply(reply), articles, companies,
                                                 {r["id"]: r for r in known_rows}, today, horizon_end)
                    with transaction(conn):
                        save_news(conn, accepted)
                except Exception as e:
                    problems.append(f"news scan: {e}")
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
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules
(a run also logs the Discord alerts it sends). The events calendar is written the same
way, by events.py's scan (daily at the market open, or "Update now").
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
import prices
import reports_db
import run_brief
import search_index

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
    def check():  # both in one trip to a worker thread
        return _latest_change(), _latest_calendar_scan()

    last, last_scan = await asyncio.to_thread(check)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current, scan = await asyncio.to_thread(check)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
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

### frontend/src/components/CalendarTab.jsx

```jsx
import { useEffect, useMemo, useRef, useState } from 'react'
import { getCalendar, startCalendarScan } from '../api'
import { formatDateTime, formatFullDate, formatMonth, formatShortDate, safeUrl } from '../format'
import { routes } from '../useRoute'

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const KINDS = { earnings: 'Earnings', dividend: 'Ex-dividend', news: 'In the news' }
const MAX_NAMES = 3 // company names shown in a day's box; the rest show as "+N more"

// Dates are handled as YYYY-MM-DD text, using UTC so time zones can't shift a day
const iso = (d) => d.toISOString().slice(0, 10)
const utc = (day) => new Date(`${day}T00:00:00Z`)
const localToday = () => {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// Every day shown for a month: whole weeks, Monday to Sunday
function monthGrid(month) {
  const first = utc(`${month}-01`)
  const start = new Date(first)
  start.setUTCDate(1 - ((first.getUTCDay() + 6) % 7))
  const last = new Date(Date.UTC(first.getUTCFullYear(), first.getUTCMonth() + 1, 0))
  const end = new Date(last)
  end.setUTCDate(last.getUTCDate() + 6 - ((last.getUTCDay() + 6) % 7))
  const days = []
  for (const d = new Date(start); d <= end; d.setUTCDate(d.getUTCDate() + 1)) days.push(iso(d))
  return { start: iso(start), end: iso(end), days }
}

function shiftMonth(month, by) {
  const d = utc(`${month}-01`)
  d.setUTCMonth(d.getUTCMonth() + by)
  return iso(d).slice(0, 7)
}

// News items carry their date as text, or (older yfinance) as seconds since 1970
function publishedOn(value) {
  if (typeof value === 'number') return iso(new Date(value * 1000))
  return /^\d{4}-\d{2}-\d{2}/.test(value || '') ? value.slice(0, 10) : null
}

function EventCard({ event }) {
  return (
    <article className="cal-event">
      <div className="cal-event-head">
        <strong>{event.company}</strong>
        <span className="muted small">{event.ticker}</span>
        <span className={`kind kind-${event.kind}`}>{KINDS[event.kind]}</span>
      </div>
      <h3>{event.title}</h3>
      {event.date_note && <p className="muted small">{event.date_note}</p>}
      {event.details && <p>{event.details}</p>}
      {event.news_note && (
        <p>
          <strong>In the news:</strong> {event.news_note}
        </p>
      )}
      {event.sources.length > 0 && (
        <ul className="cal-sources">
          {event.sources.map((s, i) => (
            <li key={i}>
              {safeUrl(s.url) ? (
                <a href={safeUrl(s.url)} target="_blank" rel="noopener noreferrer">
                  {s.title || s.url}
                </a>
              ) : (
                s.title
              )}
              {s.publisher && <span className="muted small"> · {s.publisher}</span>}
              {publishedOn(s.published) && (
                <span className="muted small"> · {formatShortDate(publishedOn(s.published))}</span>
              )}
            </li>
          ))}
        </ul>
      )}
    </article>
  )
}

// A month calendar of upcoming events: each day shows just the company names.
// Clicking a day opens its events below, with what the news says and links to the articles.
export default function CalendarTab({ selectedDate, version, scan, onScanStarted }) {
  const [month, setMonth] = useState(() => (selectedDate || localToday()).slice(0, 7))
  const [data, setData] = useState(null)
  const [dayEvents, setDayEvents] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const dayRef = useRef(null)
  const grid = useMemo(() => monthGrid(month), [month])
  const running = scan?.state === 'running'
  const today = data?.today || localToday()

  // Opening a day (or following a link to one) shows its month
  useEffect(() => {
    if (selectedDate) setMonth(selectedDate.slice(0, 7))
  }, [selectedDate])

  // The month's events: reloaded when the month changes or the calendar is updated
  useEffect(() => {
    let current = true
    getCalendar(grid.start, grid.end)
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [grid.start, grid.end, version])

  // The open day's events (fetched on their own, since you can browse to another month)
  useEffect(() => {
    if (!selectedDate) return
    let current = true
    setDayEvents(null)
    getCalendar(selectedDate, selectedDate)
      .then((body) => current && setDayEvents(body.events))
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [selectedDate, version])

  // Bring the day's events into view when a day is picked (after App's scroll-to-top on tab change)
  useEffect(() => {
    if (!selectedDate) return
    const timer = setTimeout(() => dayRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [selectedDate])

  const update = async () => {
    setStarting(true)
    setError(null)
    try {
      onScanStarted(await startCalendarScan())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const byDay = {}
  for (const e of data?.events || []) (byDay[e.event_date] ||= []).push(e)
  const last = data?.last_scan
  const status = running
    ? scan.message || 'Updating…'
    : last?.finished_at
      ? `Updated ${formatDateTime(last.finished_at)}`
      : 'Not updated yet'

  return (
    <>
      <section className="panel calendar" aria-label="Upcoming events calendar">
        <div className="section-head">
          <h2>Upcoming events</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={update} disabled={running || starting}>
              {running ? 'Updating…' : 'Update now'}
            </button>
          </div>
        </div>
        {error && <p className="error">{error}</p>}
        {scan?.state === 'failed' && <p className="error">The update didn't finish: {scan.error}</p>}
        {!running && last?.status === 'partial' && (
          <p className="muted small">Updated, but some sources couldn't be read: {last.message}</p>
        )}

        <div className="cal-nav">
          <button type="button" className="chip" onClick={() => setMonth(shiftMonth(month, -1))} aria-label="Previous month">
            ‹
          </button>
          <h3 className="cal-month">{formatMonth(`${month}-01`)}</h3>
          <button type="button" className="chip" onClick={() => setMonth(shiftMonth(month, 1))} aria-label="Next month">
            ›
          </button>
          {month !== today.slice(0, 7) && (
            <button type="button" className="link" onClick={() => setMonth(today.slice(0, 7))}>
              This month
            </button>
          )}
        </div>

        <div className="cal-grid">
          {WEEKDAYS.map((d) => (
            <div key={d} className="cal-weekday" aria-hidden="true">
              {d}
            </div>
          ))}
          {grid.days.map((day, i) => {
            const companies = [...new Map((byDay[day] || []).map((e) => [e.ticker, e])).values()]
            const classes = [
              'cal-day',
              day.slice(0, 7) !== month && 'other-month',
              i % 7 >= 5 && 'weekend',
              day < today && 'past',
              day === today && 'today',
              day === selectedDate && 'selected',
            ].filter(Boolean)
            return (
              <a
                key={day}
                className={classes.join(' ')}
                href={routes.calendar(day)}
                aria-label={`${formatFullDate(day)}: ${companies.map((c) => c.company).join(', ') || 'no events'}`}
                aria-current={day === selectedDate ? 'date' : undefined}
              >
                <span className="cal-date">{Number(day.slice(8))}</span>
                {companies.slice(0, MAX_NAMES).map((c) => (
                  <span key={c.ticker} className="cal-name">
                    <span className="long">{c.company}</span>
                    <span className="short">{c.ticker}</span>
                  </span>
                ))}
                {companies.length > MAX_NAMES && (
                  <span className="cal-more">
                    <span className="long">+{companies.length - MAX_NAMES} more</span>
                    <span className="short">+{companies.length - MAX_NAMES}</span>
                  </span>
                )}
              </a>
            )
          })}
        </div>
        <p className="muted small cal-note">
          Earnings and ex-dividend dates come from Yahoo Finance. Other events are found in recent news, each with a
          link to its source. The calendar updates every trading day when the market opens.
        </p>
      </section>

      {selectedDate && (
        <section className="panel cal-day-detail" id="calendar-day" ref={dayRef} aria-label={`Events on ${formatFullDate(selectedDate)}`}>
          <div className="section-head">
            <h2>{formatFullDate(selectedDate)}</h2>
            <a className="link" href={routes.calendar()}>
              Close
            </a>
          </div>
          {dayEvents === null ? (
            <p className="muted">Loading…</p>
          ) : dayEvents.length === 0 ? (
            <p className="muted">Nothing on the calendar for this day.</p>
          ) : (
            dayEvents.map((e) => <EventCard key={e.id} event={e} />)
          )}
        </section>
      )}
    </>
  )
}
```

### frontend/src/App.jsx

```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { getCurrentRun, getLatestReport } from './api'
import { ChartContext } from './chartContext'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
import CalendarTab from './components/CalendarTab'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'
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

  useEffect(() => {
    loadLatest()
    getCurrentRun().then(setRun).catch(() => {})
  }, [loadLatest])

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
    } else if (event.type === 'report_saved') {
      loadLatest()
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
                <ReportView report={latest} current />
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
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date] = hash.replace(/^#/, '').split('/')
  if (tab !== 'previous' && tab !== 'calendar') return { tab: 'today', date: null }
  return { tab, date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
  calendar: (date) => (date ? `#/calendar/${date}` : '#/calendar'),
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

### frontend/src/format.js

```javascript
// Display helpers

export const formatDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

export const formatFullDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'long', month: 'long', day: 'numeric', year: 'numeric',
  })

export const formatMonth = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

export const formatShortDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })

export const formatMonthShort = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'short' })

export const formatTime = (utc) =>
  utc ? new Date(utc).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ''

export const formatDateTime = (utc) =>
  utc
    ? new Date(utc).toLocaleString(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })
    : ''

export const number = (value, digits) => (value == null ? '—' : value.toFixed(digits))

export const percent = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`)

// Percentage points, for a gap between two percentages (e.g. a stock vs. its sector)
export const points = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)} pts`)

// Only allow normal web links from news sources
export const safeUrl = (url) => (/^https?:\/\//i.test(url || '') ? url : undefined)
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
```

### tests/test_events.py

```python
"""Offline tests for the upcoming events calendar. Yahoo Finance and Claude are faked.

Run from the project folder:
    pytest -v tests/test_events.py

Live check of Yahoo's calendar data (needs internet):
    LIVE_TESTS=1 pytest -v -s -k live_calendar
"""

import asyncio
import json
import os
import re
import sys
import time
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

TODAY = date(2026, 11, 6)
NAMES = {"AAPL": "Apple Inc.", "NVDA": "NVIDIA Corporation", "JPM": "JPMorgan Chase & Co."}
CALENDARS = {}  # ticker -> what yfinance's .calendar returns (or an exception to raise)
NEWS = {}       # ticker -> raw yfinance news items
JSON_HEADERS = {"Content-Type": "application/json"}


class FakeTicker:
    def __init__(self, ticker):
        self.ticker = ticker

    @property
    def info(self):
        return {"longName": NAMES.get(self.ticker)}

    @property
    def calendar(self):
        value = CALENDARS.get(self.ticker, {})
        if isinstance(value, Exception):
            raise value
        return value

    @property
    def news(self):
        return NEWS.get(self.ticker, [])


def article(ticker, slug, title, summary, published="2026-11-04T13:00:00Z"):
    return {"content": {"title": title, "summary": summary, "pubDate": published,
                        "provider": {"displayName": "Example Wire"},
                        "canonicalUrl": {"url": f"https://news.example.com/{ticker.lower()}-{slug}"}}}


class FakeClaude:
    """Stands in for Claude: replies with whatever the test sets, and keeps the prompts it was sent."""

    def __init__(self):
        self.prompts, self.reply = [], lambda prompt: {"events": []}

    def __call__(self, prompt):
        self.prompts.append(prompt)
        reply = self.reply(prompt)
        if isinstance(reply, Exception):
            raise reply
        return json.dumps(reply), 0.03


def number(prompt, slug):
    """The [N] a test article got in the prompt (found by its title, since addresses aren't sent to Claude)."""
    title = next(a["content"]["title"] for items in NEWS.values() for a in items
                 if a["content"]["canonicalUrl"]["url"].endswith(slug))
    match = re.search(rf"^\[(\d+)\] .*\n    {re.escape(title)}$", prompt, re.M)
    assert match, f"article {slug} not in the prompt"
    return int(match.group(1))


@pytest.fixture
def cal(tmp_path, monkeypatch):
    """A temporary database and watchlist, a fixed 'today', and fake Yahoo and Claude."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    watchlist = tmp_path / "watchlist.txt"
    watchlist.write_text("AAPL\nNVDA\nJPM\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    monkeypatch.setattr(events, "today_et", lambda: TODAY)
    monkeypatch.setattr(events.yf, "Ticker", FakeTicker)
    events._names.clear()
    CALENDARS.clear()
    NEWS.clear()
    claude = FakeClaude()
    monkeypatch.setattr(events, "ask_claude", claude)
    return claude


def stored(day_from="2000-01-01", day_to="2100-01-01"):
    with closing(reports_db.connect(readonly=True)) as conn:
        return events.events_between(conn, day_from, day_to)


def standard_news():
    NEWS["AAPL"] = [article("AAPL", "event", "Apple sets November 18 launch event",
                            "Apple will hold a product launch event on November 18, it said on Wednesday."),
                    article("AAPL", "earnings-preview", "What to expect from Apple's results",
                            "Analysts look for iPhone sales to rise when Apple reports.")]
    NEWS["NVDA"] = [article("NVDA", "court", "Court hearing in Nvidia patent case set for next Thursday",
                            "A federal judge set a hearing for next Thursday.", published="2026-11-05T15:00:00Z")]


def standard_reply(prompt):
    return {"events": [
        {"ticker": "AAPL", "date": "2026-11-18", "title": "Product launch event",
         "details": "Apple will hold a product launch event.", "sources": [number(prompt, "aapl-event")]},
        {"ticker": "NVDA", "date": "2026-11-12", "title": "Court hearing in patent case",
         "details": "A federal judge set a hearing.", "sources": [number(prompt, "nvda-court")]},
        {"ticker": "TSLA", "date": "2026-11-20", "title": "Not on the watchlist", "sources": [1]},
        {"ticker": "AAPL", "date": "2026-11-21", "title": "Made up", "sources": []},
        {"ticker": "AAPL", "date": "2026-12-01", "title": "Cites an article that doesn't exist", "sources": [99]},
        {"ticker": "NVDA", "date": "2026-10-01", "title": "Already happened", "sources": [1]},
        {"ticker": "NVDA", "date": "2027-06-01", "title": "Too far ahead", "sources": [1]},
        {"ticker": "JPM", "date": "soon", "title": "No real date", "sources": [1]},
    ]}


# ---------------------------------------------------------------------------
# Company names and Yahoo's calendar
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name, short", [
    ("Apple Inc.", "Apple"), ("NVIDIA Corporation", "NVIDIA"), ("JPMorgan Chase & Co.", "JPMorgan Chase"),
    ("Amazon.com, Inc.", "Amazon.com"), ("Meta Platforms, Inc.", "Meta Platforms"),
    ("Berkshire Hathaway Inc.", "Berkshire Hathaway"), ("Microsoft", "Microsoft"),
])
def test_short_company_names(name, short):
    assert events.short_name(name) == short


def test_earnings_and_dividend_dates_from_yahoo():
    cal = {"Earnings Date": [date(2026, 11, 19)], "Earnings Average": 2.35, "Earnings Low": 2.21,
           "Earnings High": 2.4, "Ex-Dividend Date": date(2026, 11, 10), "Dividend Date": date(2026, 11, 13)}

    found = events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60))

    earnings, dividend = found
    assert (earnings["kind"], earnings["event_date"], earnings["title"]) == ("earnings", "2026-11-19", "Earnings report")
    assert earnings["details"] == "Analysts' average estimate is $2.35 a share (range $2.21 to $2.40)."
    assert earnings["date_note"] is None
    assert earnings["sources"][0]["url"] == "https://finance.yahoo.com/quote/AAPL/"
    assert (dividend["kind"], dividend["event_date"], dividend["title"]) == ("dividend", "2026-11-10", "Ex-dividend date")
    assert dividend["details"].endswith("It's paid on Nov 13.")


def test_an_unconfirmed_earnings_window_is_marked_as_an_estimate():
    cal = {"Earnings Date": [date(2026, 11, 23), date(2026, 11, 18)]}

    (earnings,) = events.calendar_events("NVDA", "NVIDIA", cal, TODAY, TODAY + timedelta(days=60))

    assert earnings["event_date"] == "2026-11-18"  # the start of the window
    assert earnings["title"] == "Earnings report (date not confirmed)"
    assert earnings["date_note"] == "Estimated: Yahoo Finance shows a window of Nov 18 to Nov 23."


def test_past_and_far_off_dates_are_left_out():
    cal = {"Earnings Date": [date(2026, 10, 30)], "Ex-Dividend Date": date(2027, 3, 1)}
    assert events.calendar_events("JPM", "JPMorgan Chase", cal, TODAY, TODAY + timedelta(days=60)) == []


@pytest.mark.parametrize("cal", [
    pd.DataFrame({0: [pd.Timestamp("2026-11-19")], 1: [pd.Timestamp("2026-11-20")]}, index=["Earnings Date"]),
    {"Earnings Date": [datetime(2026, 11, 19, 16, 0, tzinfo=timezone.utc)]},
    {"Earnings Date": ["2026-11-19"]},
    {"Earnings Date": int(datetime(2026, 11, 19, 12, tzinfo=timezone.utc).timestamp())},
], ids=["older-table-format", "datetime", "text", "epoch-seconds"])
def test_other_calendar_formats_are_understood(cal):
    found = events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60))
    assert found[0]["event_date"] == "2026-11-19"


@pytest.mark.parametrize("cal", [None, {}, {"Earnings Date": []}, {"Earnings Date": "not a date"}, "junk", 42])
def test_missing_or_odd_calendar_data_gives_no_events(cal):
    assert events.calendar_events("AAPL", "Apple", cal, TODAY, TODAY + timedelta(days=60)) == []


# ---------------------------------------------------------------------------
# Scanning: calendar dates plus dated events from the news
# ---------------------------------------------------------------------------

def test_a_scan_saves_calendar_dates_and_checked_news_events(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    CALENDARS["JPM"] = {"Ex-Dividend Date": date(2026, 11, 10)}
    standard_news()
    cal.reply = standard_reply

    result = events.scan()

    assert result["status"] == "ok" and result["articles"] == 3 and result["cost_usd"] == 0.03
    assert result["events_found"] == 2 and result["dropped"] == 6
    reasons = " | ".join(result["dropped_reasons"])
    for why in ("not a watchlist ticker", "no valid article cited", "outside 2026-11-06 to 2027-01-05", "no valid date"):
        assert why in reasons
    saved = {(e["event_date"], e["company"], e["kind"]): e for e in stored()}
    assert set(saved) == {("2026-11-10", "JPMorgan Chase", "dividend"), ("2026-11-12", "NVIDIA", "news"),
                          ("2026-11-18", "Apple", "news"), ("2026-11-19", "Apple", "earnings")}
    launch = saved[("2026-11-18", "Apple", "news")]
    assert launch["title"] == "Product launch event"
    assert launch["sources"] == [{"title": "Apple sets November 18 launch event", "publisher": "Example Wire",
                                  "url": "https://news.example.com/aapl-event", "published": "2026-11-04T13:00:00Z"}]

    prompt = cal.prompts[0]
    assert "TODAY: 2026-11-06 (Friday)" in prompt and "HORIZON_END: 2027-01-05" in prompt
    assert re.search(r"- id \d+: AAPL earnings on 2026-11-19: Earnings report", prompt)  # Claude sees the calendar
    assert "[3] NVDA | Example Wire | published 2026-11-05T15:00:00Z" in prompt


def test_scanning_again_doesnt_duplicate_events(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = standard_reply

    events.scan()
    first = stored()
    events.scan()
    second = stored()

    assert len(second) == len(first) == 3
    assert [e["id"] for e in second] == [e["id"] for e in first]  # the same rows, updated in place


def test_a_moved_news_event_keeps_its_place_on_the_calendar(cal):
    NEWS["AAPL"] = [article("AAPL", "investor-day", "Apple investor day on Nov 20", "...")]
    cal.reply = lambda p: {"events": [{"ticker": "AAPL", "date": "2026-11-20", "title": "Investor day",
                                       "sources": [number(p, "investor-day")]}]}
    events.scan()
    (first,) = stored()

    NEWS["AAPL"] = [article("AAPL", "investor-day-moved", "Apple moves investor day to Nov 24", "...")]
    cal.reply = lambda p: {"events": [{"ticker": "AAPL", "date": "2026-11-24", "title": "Investor day (moved)",
                                       "sources": [number(p, "investor-day-moved")], "same_as": first["id"]}]}
    events.scan()
    (moved,) = stored()

    assert moved["id"] == first["id"] and moved["event_date"] == "2026-11-24"
    assert [s["url"] for s in moved["sources"]] == ["https://news.example.com/aapl-investor-day",
                                                   "https://news.example.com/aapl-investor-day-moved"]


def test_news_about_an_earnings_date_is_attached_without_changing_the_date(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()

    def reply(prompt):
        earnings_id = int(re.search(r"- id (\d+): AAPL earnings", prompt).group(1))
        return {"events": [{"ticker": "AAPL", "date": "2026-12-25", "title": "Results", "same_as": earnings_id,
                            "details": "Analysts look for iPhone sales to rise.",
                            "sources": [number(prompt, "earnings-preview")]}]}

    cal.reply = reply
    events.scan()
    (earnings,) = [e for e in stored() if e["kind"] == "earnings"]

    assert earnings["event_date"] == "2026-11-19" and earnings["title"] == "Earnings report"  # Yahoo's date stands
    assert earnings["news_note"] == "Analysts look for iPhone sales to rise."
    assert [s["publisher"] for s in earnings["sources"]] == ["Yahoo Finance", "Example Wire"]
    assert not [e for e in stored() if e["kind"] == "news"]


def test_yahoo_moving_an_earnings_date_replaces_the_old_one_but_never_touches_the_past(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    events.scan()
    with closing(events.connect()) as conn:  # an event that already happened
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, first_seen, last_seen)
                        VALUES ('2026-10-30', 'AAPL', 'Apple', 'earnings', 'Earnings report', 'x', 'x')""")
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 24)]}

    events.scan()

    assert [(e["event_date"], e["kind"]) for e in stored()] == [("2026-10-30", "earnings"), ("2026-11-24", "earnings")]


def test_news_events_stay_after_their_article_drops_out_of_the_feed(cal):
    standard_news()
    cal.reply = standard_reply
    events.scan()
    NEWS.clear()

    result = events.scan()

    assert len(cal.prompts) == 1  # no headlines, so Claude wasn't asked (and cost nothing)
    assert result["cost_usd"] == 0
    assert {e["title"] for e in stored()} == {"Product launch event", "Court hearing in patent case"}


def test_if_claude_fails_the_calendar_dates_are_still_saved(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = lambda prompt: RuntimeError("Claude couldn't read the news: error_max_budget_usd")

    result = events.scan()

    assert result["status"] == "partial"
    assert "news scan: Claude couldn't read the news" in result["message"]
    assert [e["kind"] for e in stored()] == ["earnings"]


def test_one_companys_calendar_failing_keeps_its_saved_dates(cal):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    events.scan()
    CALENDARS["AAPL"] = ConnectionError("Yahoo rate limit")

    result = events.scan()

    assert result["status"] == "partial" and "AAPL calendar: Yahoo rate limit" in result["message"]
    assert [e["event_date"] for e in stored()] == ["2026-11-19"]


@pytest.mark.parametrize("reply", [
    '{"events": []}',
    'Here you go:\n```json\n{"events": []}\n```',
    'Sure. {"events": []} Hope that helps.',
])
def test_claudes_reply_is_read_even_with_extra_text(reply):
    assert events.parse_reply(reply) == []


@pytest.mark.parametrize("reply", ["no json here", '{"items": []}', '{"events": "none"}', "{broken"])
def test_an_unreadable_reply_is_an_error(reply):
    with pytest.raises(ValueError):
        events.parse_reply(reply)


def test_only_one_scan_runs_at_a_time(cal):
    with closing(events.connect()) as conn:
        conn.execute("INSERT INTO event_scans (started_at, trigger, status) VALUES (?, 'scheduled', 'running')",
                     (events._utc_now(),))
    with pytest.raises(events.ScanBusy):
        events.scan()

    # A scan that stopped half-way (the computer slept, say) doesn't block scans for ever
    stuck = (datetime.now(timezone.utc) - events.STUCK_AFTER - timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with closing(events.connect()) as conn:
        conn.execute("UPDATE event_scans SET started_at = ?", (stuck,))
    assert events.scan()["status"] == "ok"
    with closing(events.connect()) as conn:
        assert [r[0] for r in conn.execute("SELECT status FROM event_scans ORDER BY id")] == ["failed", "ok"]


def test_the_daily_schedule_skips_days_the_market_is_closed(cal, monkeypatch, capsys):
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "complete", "as_of": "2026-11-06"})
    monkeypatch.setattr(sys, "argv", ["events.py", "scan", "--only-if-open"])

    events.main()

    assert "skipped" in capsys.readouterr().out
    with closing(events.connect()) as conn:
        assert conn.execute("SELECT COUNT(*) FROM event_scans").fetchone()[0] == 0


def test_command_line_scan_list_show_and_remove(cal, monkeypatch, capsys):
    CALENDARS["AAPL"] = {"Earnings Date": [date(2026, 11, 19)]}
    standard_news()
    cal.reply = standard_reply
    for argv in (["scan"], ["list"], ["show", "2026-11-18"]):
        monkeypatch.setattr(sys, "argv", ["events.py", *argv])
        events.main()
    out = capsys.readouterr().out

    assert "ok: 2 news events from 3 headlines, $0.030" in out
    assert "left out: TSLA 'Not on the watchlist': not a watchlist ticker" in out
    assert "2026-11-19  Apple              earnings  Earnings report" in out
    assert "- Example Wire: Apple sets November 18 launch event https://news.example.com/aapl-event" in out

    launch = next(e for e in stored() if e["title"] == "Product launch event")
    monkeypatch.setattr(sys, "argv", ["events.py", "remove", str(launch["id"])])
    events.main()
    assert "Removed." in capsys.readouterr().out
    assert "Product launch event" not in {e["title"] for e in stored()}


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(cal, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "calendar_scans", api.CalendarScanManager())
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for_scan(client):
    for _ in range(100):
        scan = client.get("/api/calendar/scan").json()["scan"]
        if scan["state"] in ("finished", "failed"):
            return scan
        time.sleep(0.05)
    raise AssertionError("the scan didn't finish")


def test_api_calendar_works_before_the_first_scan(client):
    body = client.get("/api/calendar").json()

    assert body["today"] == "2026-11-06" and body["start"] == "2026-11-01" and body["end"] == "2026-12-12"
    assert body["events"] == [] and body["last_scan"] is None and body["scan"]["state"] == "idle"


def test_update_now_scans_and_the_calendar_shows_the_results(client):
    CALENDARS["JPM"] = {"Ex-Dividend Date": date(2026, 11, 10)}
    standard_news()
    events.ask_claude.reply = standard_reply

    started = client.post("/api/calendar/scan", json={})
    scan = wait_for_scan(client)
    body = client.get("/api/calendar?start=2026-11-09&end=2026-11-15").json()

    assert started.status_code == 202 and started.json()["scan"]["state"] == "running"
    assert scan["state"] == "finished" and scan["result"]["events_found"] == 2 and scan["result"]["trigger"] == "manual"
    assert [(e["event_date"], e["company"]) for e in body["events"]] == [("2026-11-10", "JPMorgan Chase"),
                                                                          ("2026-11-12", "NVIDIA")]
    assert body["last_scan"]["status"] == "ok"


def test_update_now_has_a_cooldown_and_runs_one_at_a_time(client, monkeypatch):
    client.post("/api/calendar/scan", json={})
    wait_for_scan(client)
    assert client.post("/api/calendar/scan", json={}).status_code == 429  # cooldown

    monkeypatch.setattr(api, "CALENDAR_SCAN_COOLDOWN_SECONDS", 0)
    slow = events.scan
    monkeypatch.setattr(events, "scan", lambda *args: (time.sleep(0.5), slow(*args))[1])
    assert client.post("/api/calendar/scan", json={}).status_code == 202
    assert client.post("/api/calendar/scan", json={}).status_code == 409  # one at a time
    wait_for_scan(client)


def test_other_websites_cannot_start_a_scan(client):
    assert client.post("/api/calendar/scan", json={}, headers={"Origin": "https://evil.example"}).status_code == 403


@pytest.mark.parametrize("query", [
    "start=11-06-2026", "start=2026-11-10&end=2026-11-01", "start=2026-01-01&end=2026-12-31", "start=2026-02-30",
])
def test_api_calendar_rejects_bad_dates(client, query):
    response = client.get(f"/api/calendar?{query}")
    assert response.status_code == 400 and response.json()["error"]


def test_live_updates_announce_a_scan_from_the_daily_schedule(cal, monkeypatch):
    """The scheduled scan is a separate program, so the API spots it in the database and tells the browser."""
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)  # let the watcher take its first look
        await asyncio.to_thread(events.scan, "scheduled")
        event = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return event

    event = asyncio.run(scenario())

    assert event["type"] == "calendar_updated" and event["scan"]["status"] == "ok"


@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 to hit Yahoo Finance")
def test_live_calendar_data(monkeypatch):
    import yfinance

    monkeypatch.setattr(events.yf, "Ticker", yfinance.Ticker)  # real Yahoo Finance
    events._names.clear()
    today = date.today()
    name = events.company_name("AAPL")
    raw = events.fetch_calendar("AAPL")
    found = events.calendar_events("AAPL", name, raw, today, today + timedelta(days=events.HORIZON_DAYS))
    news = events.fetch_news("AAPL")

    assert name == "Apple"
    assert isinstance(events._calendar_dict(raw), dict) and events._calendar_dict(raw), raw
    assert news and news[0]["title"] and news[0]["url"]
    print("\nYahoo's calendar for AAPL:", raw)
    print("Events from it:", [(e["event_date"], e["title"], e["date_note"]) for e in found])
```
