# Market Analyst Agent: Connecting the Calendar

The events calendar used to sit on its own tab. This guide connects it to the rest of the app, so everything knows what's coming up:

| Where | What changes |
|---|---|
| **Briefs** | A new **Coming up** section lists the next week's events. Each flagged ticker's "Worth watching" line mentions its next event, and a big move just before a known event is described as coming "ahead of" it |
| **Discord** | The daily summary ends with **Coming up** for the week ahead. Each flag alert card shows that ticker's next event |
| **Ask** | Questions like "What's coming up next week?" or "When does NVDA report?" are answered from the calendar, cited as (calendar) |
| **Today tab** | A **Coming up** card lists the next week's events. Each one links to its day on the Calendar tab |

There are no new data sources, keys or scans: everything reads the calendar that `events.py` already keeps. This builds on `market-agent-events-calendar.md`, and this guide's files include every earlier change.

---

## Contents

1. [What it looks like](#1-what-it-looks-like)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Add the upcoming_events tool](#4-step-1-add-the-upcoming_events-tool)
5. [Step 2: Update the prompt and agent settings](#5-step-2-update-the-prompt-and-agent-settings)
6. [Step 3: Add what's coming up to Discord alerts](#6-step-3-add-whats-coming-up-to-discord-alerts)
7. [Step 4: Give Ask the calendar, and keep it out of search](#7-step-4-give-ask-the-calendar-and-keep-it-out-of-search)
8. [Step 5: Add the Coming up card](#8-step-5-add-the-coming-up-card)
9. [Step 6: Add the tests](#9-step-6-add-the-tests)
10. [Step 7: Try it](#10-step-7-try-it)
11. [Test it](#11-test-it)
12. [Settings](#12-settings)
13. [Costs](#13-costs)
14. [Troubleshooting](#14-troubleshooting)
15. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it looks like

These examples are from the test environment, so the events are simulated.

**In the brief,** after "Quiet":

```markdown
## Coming up

- Mon Nov 9: Microsoft (MSFT): Court hearing in patent case
- Thu Nov 12: Microsoft (MSFT): Regulator's decision on deal
```

The "Worth watching" line for a flagged ticker now names its next event, for example "the court hearing on Nov 9". If the date isn't confirmed, it says so.

**In Discord:**

- **The daily summary** ends with the week ahead. It never includes the report's own day:

  ```
  Coming up:
  • Mon Nov 9: Microsoft (MSFT): Court hearing in patent case
  • Thu Nov 12: Microsoft (MSFT): Regulator's decision on deal
  ```

- **A flag alert card** adds a line for that ticker's soonest event in the next two weeks, for example `Coming up: Mon Nov 16: Earnings report (date not confirmed)`.

**On the Today tab,** a Coming up card sits under "Request a fresh report":

```
COMING UP                                  Calendar
Mon, Nov 9    Microsoft  Court hearing in patent case
Thu, Nov 12   Microsoft  Regulator's decision on deal
```

**In Ask,** "What's coming up next week?" is now one of the example questions.

---

## 2. How it works

```
events.py scan (daily at 9:35am, or "Update now")  ──▶  events table in reports.db
                                                            │
     ┌──────────────────────────┬───────────────────────────┼──────────────────────┐
     ▼                          ▼                           ▼                      ▼
upcoming_events tool       alerts.calendar_for()      ask.calendar_section()   GET /api/calendar
(market_tools.py)          (alerts.py)                (ask.py)                 (the Today card)
the brief's "Coming up"    summary: next 7 days       next 30 days, plus the   next 7 days
and "Worth watching"       flag card: next 14 days    last 30 for tickers you
                                                      ask about
```

- **One format everywhere.** The lines come from `events.event_line()`, so the brief, Discord, Ask and the terminal all write events the same way.
- **The agent still does no date maths.** The tool gives each event its `days_away`, whether the date is `confirmed`, a ready-made `line`, and `this_week` (the lines for the next 7 days). The prompt tells the agent to copy those lines as given.
- **Only your watchlist.** Events for tickers you've since removed stay on the Calendar tab as history, but aren't listed as coming up.
- **How fresh it is.** The calendar updates at 9:35am. So the 8:15am brief (the final report for the day before) uses the previous morning's calendar, and the 12:30pm update uses that day's. Dates rarely change overnight. If the calendar has never been filled in, the brief says so instead of listing nothing.
- **Search leaves "Coming up" out.** Otherwise a search for "earnings" would find the days before every earnings date, not the earnings days themselves. Ask gets the calendar directly instead.

---

## 3. Before you start

- [ ] You've done `market-agent-events-calendar.md`, and `pytest` shows `195 passed, 2 skipped`.
- [ ] The calendar has been filled at least once (`python events.py scan`), so you have something to see.

No new packages or keys are needed.

---

## 4. Step 1: Add the upcoming_events tool

Replace `events.py` and `market_tools.py` with the appendix versions.

- **`events.py`** gains four small helpers at the end, used by everything in this guide:

  | Helper | What it does |
  |---|---|
  | `upcoming()` | Events from a date for N days, for some tickers or all |
  | `event_line()` | One event as a short line |
  | `confirmed()` | Whether an earnings date is confirmed |
  | `watchlist_tickers()` | The current watchlist |

- **`market_tools.py`** gets the new tool `upcoming_events(ticker="", days=14)`:
  - It reads the calendar through a read-only connection to the reports database.
  - With no ticker, it covers the whole watchlist. Give a ticker for just that company.
  - `days` is limited to 1–60.

  It imports `events` inside the function, because `events.py` imports `market_tools.py`.

You can try the tool in the MCP Inspector (`npx @modelcontextprotocol/inspector python market_tools.py`). It costs nothing.

---

## 5. Step 2: Update the prompt and agent settings

1. Replace `analyst_prompt.md` with the [appendix](#analyst_promptmd) version. If you've edited your prompt, merge these instead:
   - **Process, step 3:** call `upcoming_events` once.
   - **A new section, "Upcoming events":**
     - copy `this_week` as given
     - mention a flagged ticker's next event in "Worth watching"
     - "ahead of" is fine, but never claim an event caused a move unless the news says so
   - **Template:** a "## Coming up" section after "## Quiet".
2. Replace `run_brief.py` with the [appendix](#run_briefpy) version. The only change is one line in `allowed_tools`:

```python
        "mcp__market__upcoming_events",
```

The test `test_agent_can_use_every_market_tool` (from the sector guide) checks the tool is both allowed and named in the prompt.

---

## 6. Step 3: Add what's coming up to Discord alerts

Replace `alerts.py` with the [appendix](#alertspy) version.

- **The daily summary** lists watchlist events from the day after the report up to 7 days later. It shows up to 6 lines, then "…and N more on the calendar".
- **Each flag alert card** shows that ticker's soonest event from the report's day up to 14 days later, if there is one.
- **`python alerts.py preview`** shows these too.

---

## 7. Step 4: Give Ask the calendar, and keep it out of search

Replace `ask.py` and `search_index.py` with the appendix versions.

- **`ask.py`** adds an "Events calendar" section to what Claude reads:
  - every watchlist event in the next 30 days
  - the last 30 days of events for any ticker the question names

  The instructions tell Claude to cite these as (calendar) and to say when a date isn't confirmed.
- **`search_index.py`** skips the brief's "Coming up" section when it splits reports into passages. Reports saved before this change don't have that section, so there's nothing to rebuild.

---

## 8. Step 5: Add the Coming up card

Replace or add these files in `frontend/src/`:

| File | Change |
|---|---|
| `components/ComingUp.jsx` | **New:** the Coming up card |
| `App.jsx` | Shows the card under "Request a fresh report", and refreshes it when the calendar updates |
| `format.js` | `formatWeekdayDate()` ("Mon, Nov 9") |
| `components/RunPanel.jsx` | The run log shows "Checking the events calendar" |
| `components/AskPanel.jsx` | Says answers come from saved reports *and the calendar*, with "What's coming up next week?" as an example |
| `styles.css` | The card's styles |

Then rebuild if you serve the built app (`cd frontend && npm run build`).

---

## 9. Step 6: Add the tests

1. Replace `tests/test_market_tools.py` with the version in **`market-agent-testing.md`'s appendix**. Its MCP test now expects five tools.
2. Add `tests/test_calendar_links.py` from this guide's [appendix](#teststest_calendar_linkspy).
3. Run:

```bash
pytest -v
```

**Expected result:** `208 passed, 2 skipped`.

---

## 10. Step 7: Try it

1. **A brief:** run `python run_brief.py`.
   - The tool calls should include `-> mcp__market__upcoming_events {}`.
   - Then `python reports_db.py show latest` should end with "## Coming up", listing the same events as `python events.py list` for the next 7 days.
2. **The alerts preview:** `python alerts.py preview` (no webhook needed). A final report's summary ends with "Coming up:".
3. **Ask:** in the app, click "What's coming up next week?", then **Ask**. The answer should list events, cited as (calendar).
4. **The Today tab:** the Coming up card shows the next week's events. Click one to open its day on the Calendar tab.

---

## 11. Test it

### 11.1 Automated tests

*In `tests/test_calendar_links.py`*

| Test | Proves that |
|---|---|
| `test_upcoming_events_lists_the_next_two_weeks_for_the_watchlist` | The tool lists today and the next 14 days, for watchlist companies only, with `days_away`, `confirmed` and a ready-made `line`; `this_week` has the next 7 days |
| `test_upcoming_events_for_one_ticker_and_a_longer_range` | One ticker, a longer range, and the 1–60 day limits |
| `test_upcoming_events_before_the_calendar_exists` | Before the first scan, the tool says so instead of listing nothing |
| `test_upcoming_events_through_mcp` | The tool works through a real MCP client, as the agent calls it |
| `test_the_brief_has_a_coming_up_section` | The prompt has the section and the "don't claim cause" rule |
| `test_search_leaves_out_the_coming_up_section` | Search passages don't include "Coming up" |
| `test_daily_summary_lists_the_coming_week` | The summary lists the 7 days after the report's day, watchlist companies only |
| `test_daily_summary_caps_the_list` | At most 6 lines, then "…and N more on the calendar" |
| `test_a_flag_card_mentions_the_tickers_next_event` | Each card shows that ticker's soonest event, not a later one |
| `test_alerts_work_without_a_calendar` | No calendar yet: alerts work as before |
| `test_ask_sees_the_calendar` | Ask's calendar section has the next 30 days, with dates, and the last 30 days for named tickers |
| `test_ask_includes_the_calendar_in_its_context` | The section is part of what Claude reads, and Claude is told to cite it |
| `test_ask_without_a_calendar_has_no_calendar_section` | No calendar: no empty section |

Also, `test_tools_work_through_mcp` (testing guide) now expects five tools. `test_agent_can_use_every_market_tool` (sector guide) checks `upcoming_events` is allowed and in the prompt.

**Check the tests catch real bugs.** Make one of these temporary changes, run `pytest tests/test_calendar_links.py`, then change it back. Each was tried:

| Temporary change | Test that fails |
|---|---|
| `market_tools.py`: `this_week` uses `days_away"] <= 14` instead of `<= 7` | `test_upcoming_events_lists_the_next_two_weeks_for_the_watchlist` |
| `alerts.py`: in `summary_payload`, `report["session_date"] < e["event_date"]` → `<=` (the report's own day leaks in) | `test_daily_summary_lists_the_coming_week` |
| `search_index.py`: `if first_line.lstrip("#").strip() in SKIPPED_SECTIONS:` → `if False:` | `test_search_leaves_out_the_coming_up_section` |

### 11.2 What was also tested

- **From the guides alone:** the project was rebuilt from the guides (this one included), and all tests passed.
- **In a real browser, against the test environment.** Its sample briefs, simulated agent runs, alerts and offline Ask now include what's coming up. The 7 checks passed with no browser errors:
  1. The Today tab's card lists the next week, linked to each day.
  2. The brief has the same events under "Coming up".
  3. The new Ask example is answered from the calendar.
  4. "Run update now" shows "Checking the events calendar".
  5. Clicking an event opens its day on the Calendar tab.
  6. The card fits on a phone.
  7. Dark mode renders.

  The earlier Today, Previous days, chart, search, alerts and calendar checks all still pass.

**Not tested here:** how real Claude writes "Worth watching" and "ahead of" with real events. Check a few briefs (below).

### 11.3 Checks with real data

- [ ] A brief's "Coming up" matches `python events.py list` for the next 7 days, line for line
- [ ] A flagged ticker with an event in the next two weeks has it in "Worth watching", with "not confirmed" if it's an estimate
- [ ] No brief says an upcoming event *caused* a move unless its linked article says so
- [ ] The next daily summary in Discord ends with "Coming up", and a flag card shows its ticker's next event
- [ ] Ask "When does [a watchlist ticker] report earnings?": the answer gives the calendar's date, cited as (calendar)

---

## 12. Settings

| Where | Setting | Default | What it does |
|---|---|---|---|
| `market_tools.py` | `upcoming_events(days=…)` | 14 (the agent can ask for 1–60) | How far ahead the brief's tool looks; `this_week` is always the next 7 days |
| `alerts.py` | `COMING_UP_DAYS` | `7` | How far ahead the daily summary looks |
| `alerts.py` | `NEXT_EVENT_DAYS` | `14` | How soon an event must be to appear on a flag card |
| `alerts.py` | `MAX_COMING_UP` | `6` | Most lines in the summary's list |
| `ask.py` | `CALENDAR_DAYS` | `30` | How far ahead (all tickers) and back (named tickers) Ask sees |
| `search_index.py` | `SKIPPED_SECTIONS` | `("Coming up",)` | Brief sections left out of search |
| `components/ComingUp.jsx` | `DAYS`, `MAX_SHOWN` | `7`, `6` | The Today card's range and length |

---

## 13. Costs

- **Briefs:** one more tool call and a few short lines per brief, which is a small fraction of a run's cost.
- **Ask:** reads up to a month of calendar lines, usually well under a hundred.
- **Discord, the Today card and search:** cost nothing extra.
- **Updating the calendar:** no extra scans. It still updates once a day, plus any "Update now" presses.

---

## 14. Troubleshooting

| Problem | Cause and fix |
|---|---|
| The brief says the calendar "hasn't been filled in yet" | Run `python events.py scan` once, and set up the 9:35am job (calendar guide, section 9). |
| No "Coming up" section, and no `upcoming_events` in the tool calls | `run_brief.py` doesn't allow the tool, or the prompt wasn't updated. `pytest` catches both. |
| "Coming up" in the brief differs from the Calendar tab | The brief was written before the latest calendar update. The next brief catches up. |
| The summary has no "Coming up" | Nothing is on the calendar for the 7 days after that report's day, or every event is for tickers no longer on your watchlist. |
| Ask doesn't mention upcoming events | Check `alerts.py preview` or `events.py list` shows events. Ask only sees the next 30 days (`CALENDAR_DAYS`). |
| The Today tab has no Coming up card | Rebuild the frontend (`npm run build`) and hard-refresh. The card hides itself if the calendar can't be loaded. |
| `test_tools_work_through_mcp` fails, listing `upcoming_events` | `tests/test_market_tools.py` is the old version. Replace it from the testing guide's appendix. |

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

### analyst_prompt.md

```markdown
You are an equity research analyst writing a short brief on the user's watchlist.

## Process

1. Call `flag_events` first. It returns the session status, the tickers with unusual moves, and the quiet ones.
2. Call `market_backdrop` once, for how the S&P 500 and each sector moved.
3. Call `upcoming_events` once, for what's coming up (see below).
4. For each flagged ticker, read its `context` (see below), then call `get_news` to find the likely reason. Call `compute_moves` if you need more detail on a ticker.
5. Write the brief.

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

## Upcoming events

`upcoming_events` lists earnings dates, ex-dividend dates and dated news events from the events calendar.

- Under "Coming up", list its `this_week` lines exactly as given, one bullet each. If `this_week` is empty, write "Nothing on the calendar for the next week." If it has a `note`, write the note instead.
- In a flagged ticker's "Worth watching" line, mention that ticker's next event if `upcoming_events` lists one, with its date. If `confirmed` is false, say the date isn't confirmed.
- A move shortly before a known event can be described as coming "ahead of" it. Don't say the event caused the move unless the news says so.

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

## Coming up

- {each line from upcoming_events.this_week}

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

After saving, it sends any Discord alerts the report calls for (see alerts.py).

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

import alerts
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
        "mcp__market__upcoming_events",
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

### alerts.py

```python
"""Discord alerts for the market analyst agent.

After each run saves a report, run_brief.py calls notify(), which compares the saved
report with the alerts already sent and posts whatever is new:
- While the market is open: one message for tickers flagged for the first time today.
  A ticker alerts once per day, unless its move later grows a lot (or reverses).
- After the final report: one end-of-day summary per day.
Both include what's coming up, from the events calendar (events.py).
Every alert is logged in the reports database. One that fails is retried by the next run.

Set it up:
    export DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
    python alerts.py test

Other commands:
    python alerts.py preview [DATE]       what would be sent now, without sending (works without a webhook)
    python alerts.py log                  recent alerts
    python alerts.py summary DATE         send a day's summary (add --force to send it again)

The webhook address works like a password: anyone who has it can post in your channel.
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import events
import reports_db

WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
APP_URL = os.environ.get("ALERTS_APP_URL", "").rstrip("/")  # e.g. http://localhost:8000: adds links to the app
SEND_FLAG_ALERTS = True      # newly flagged tickers while the market is open
SEND_DAILY_SUMMARY = True    # one summary after each final report
ESCALATE_Z = 1.5             # alert a ticker again the same day if its |z-score| grows by this much
COMING_UP_DAYS = 7           # the daily summary lists calendar events this many days ahead
NEXT_EVENT_DAYS = 14         # a flag card mentions the ticker's next event if it's this soon
MAX_COMING_UP = 6            # most "Coming up" lines in a summary
PENDING_SECONDS = 120        # an alert being sent by another run counts as sent for this long
USERNAME = "Market Analyst"
COLORS = {"up": 0x12805C, "down": 0xC0392B, "neutral": 0x5F6B7A}
WEBHOOK_PREFIXES = tuple(f"https://{host}/api/webhooks/" for host in
                         ("discord.com", "discordapp.com", "canary.discord.com", "ptb.discord.com"))
# Discord's limits for one message
MAX_EMBEDS, MAX_TITLE, MAX_DESCRIPTION, MAX_CONTENT, MAX_TOTAL = 10, 256, 4096, 2000, 6000

SCHEMA = """
CREATE TABLE IF NOT EXISTS alerts (
    id            INTEGER PRIMARY KEY,
    session_date  TEXT NOT NULL,
    kind          TEXT NOT NULL CHECK (kind IN ('flag', 'summary')),
    ticker        TEXT,                -- flag alerts only
    return_1d_pct REAL,
    return_zscore REAL,
    as_of         TEXT,                -- the report's as_of when the alert was decided
    status        TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
    error         TEXT,
    created_at    TEXT NOT NULL,       -- UTC timestamps
    sent_at       TEXT
);
CREATE INDEX IF NOT EXISTS idx_alerts_day ON alerts (session_date, kind, ticker);
"""


class SendError(Exception):
    pass


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def webhook_url() -> str | None:
    """The webhook from the environment, or None. Raises ValueError if it isn't a Discord webhook."""
    url = os.environ.get(WEBHOOK_ENV, "").strip()
    if not url:
        return None
    if not url.startswith(WEBHOOK_PREFIXES):
        raise ValueError(f"{WEBHOOK_ENV} must be a Discord webhook URL (https://discord.com/api/webhooks/...)")
    return url


def enabled() -> bool:
    try:
        return webhook_url() is not None
    except ValueError:
        return False


def connect():
    """The reports database, with the alerts log table added if it's missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------

def post(payload: dict) -> str:
    """Send one message to the Discord webhook. Returns Discord's message id.

    Waits once and retries if Discord asks us to slow down. Error messages never
    include the webhook address.
    """
    url = webhook_url()
    if not url:
        raise SendError(f"{WEBHOOK_ENV} isn't set")
    body = json.dumps({"username": USERNAME, "allowed_mentions": {"parse": []}, **payload}).encode()
    request = urllib.request.Request(
        url + "?wait=true", data=body, method="POST",
        headers={"Content-Type": "application/json", "User-Agent": "market-agent-alerts/1.0"})
    for attempt in (1, 2):
        try:
            with urllib.request.urlopen(request, timeout=10) as response:
                return str(json.loads(response.read() or b"{}").get("id", ""))
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:300]
            if e.code == 429 and attempt == 1:  # rate limited: Discord says how long to wait, in seconds
                try:
                    wait = float(json.loads(detail).get("retry_after", 1))
                except ValueError:
                    wait = 1.0
                if wait <= 5:
                    time.sleep(wait)
                    continue
            if e.code == 404:
                raise SendError("Discord says this webhook doesn't exist (deleted?). Create a new one.") from None
            raise SendError(f"Discord refused the message ({e.code}): {detail}") from None
        except urllib.error.URLError as e:
            raise SendError(f"couldn't reach Discord ({e.reason})") from None
    raise SendError("Discord is rate limiting this webhook; try again shortly")


send = post  # tests and the test environment swap this for a fake


# ---------------------------------------------------------------------------
# Building messages from a saved report
# ---------------------------------------------------------------------------

MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\(([^)]*)\)")


def _shorten(text: str, limit: int) -> str:
    """Fit text in a limit. If it has to be cut, links are turned into plain text first,
    so a link is never cut in half."""
    text = text.strip()
    if len(text) <= limit:
        return text
    text = MARKDOWN_LINK.sub(r"\1", text)
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


def _section(body_md: str, heading: str) -> str:
    """The text under a markdown heading (## or ###), up to the next heading of any level."""
    match = re.search(rf"^#{{2,3}}\s+{heading}\b[^\n]*\n(.*?)(?=^#{{1,3}}\s|\Z)", body_md, re.M | re.S)
    return match.group(1).strip() if match else ""


def likely_why(body_md: str, ticker: str) -> str:
    """The agent's "Likely why" line for a ticker, from the brief."""
    match = re.search(r"^-\s*\*\*Likely why:\*\*\s*(.+)$", _section(body_md, re.escape(ticker)), re.M)
    return match.group(1).strip() if match else ""


def market_backdrop(body_md: str) -> str:
    return " ".join(_section(body_md, "Market backdrop").split())


def _app_link(path: str) -> dict:
    return {"url": f"{APP_URL}/{path}"} if APP_URL.startswith(("http://", "https://")) else {}


def flag_embed(t: dict, report: dict, previous: dict | None = None, next_event: dict | None = None) -> dict:
    intraday = report["status"] == "intraday"
    so_far = " so far today" if intraday else ""
    pct = t["return_1d_pct"] or 0
    title = f"{t['ticker']} {pct:+.2f}%{so_far}"
    if previous:
        title = f"Bigger move: {title}" if (previous["return_zscore"] or 0) * (t["return_zscore"] or 0) > 0 \
            else f"Reversal: {title}"
    lines = [f"z-score {t['return_zscore']} · volume {t['volume_vs_avg']}x normal"
             + (" for this time of day" if intraday else "")]
    if previous:
        lines.append(f"Was {previous['return_1d_pct']:+.2f}% at {str(previous['as_of'])[11:]}")
    if t.get("context_summary"):
        lines.append(f"**Vs. sector and market:** {_shorten(t['context_summary'], 600)}")
    why = likely_why(report["body_md"], t["ticker"])
    if why:
        lines.append(f"**Likely why:** {_shorten(why, 600)}")
    if next_event:
        lines.append(f"**Coming up:** {events.event_line(next_event, company=False)}")
    return {
        "title": _shorten(title, MAX_TITLE),
        "description": _shorten("\n".join(lines), MAX_DESCRIPTION),
        "color": COLORS["up" if pct > 0 else "down" if pct < 0 else "neutral"],
        "footer": {"text": f"As of {report['as_of']} · research, not investment advice"},
        **_app_link("#/"),
    }


def flags_payload(report: dict, items: list[tuple[dict, dict | None]], upcoming: list[dict] = ()) -> dict:
    new = sum(1 for _, previous in items if previous is None)
    bigger = len(items) - new
    parts = [f"{new} new flag{'s' if new != 1 else ''}"] if new else []
    if bigger:
        parts.append(f"{bigger} bigger move{'s' if bigger != 1 else ''}")
    content = f"**{' and '.join(parts).capitalize()}** in the intraday update as of {report['as_of'][11:]}"
    if len(items) > MAX_EMBEDS:
        content += f" (showing {MAX_EMBEDS}; the rest are in the app)"
    next_event = {}  # each ticker's soonest event (upcoming is in date order)
    for e in upcoming:
        next_event.setdefault(e["ticker"], e)
    return {"content": content, "embeds": _fit([flag_embed(t, report, prev, next_event.get(t["ticker"]))
                                                for t, prev in items[:MAX_EMBEDS]])}


def summary_payload(report: dict, upcoming: list[dict] = ()) -> dict:
    tickers = report["tickers"]
    flagged = [t for t in tickers if t["category"] == "flagged"]
    lines = []
    backdrop = market_backdrop(report["body_md"])
    if backdrop:
        lines += [f"**Market:** {_shorten(backdrop, 400)}", ""]
    for t in flagged:
        read = f" · {t['move_read']}" if t.get("move_read") else ""
        why = likely_why(report["body_md"], t["ticker"])
        lines.append(f"**{t['ticker']}** {t['return_1d_pct']:+.2f}% (z-score {t['return_zscore']}){read}"
                     + (f"\n{_shorten(why, 300)}" if why else ""))
    if not flagged:
        lines.append("Nothing unusual today.")
    quiet = [f"{t['ticker']} {t['return_1d_pct']:+.2f}%" for t in tickers
             if t["category"] == "quiet" and t["return_1d_pct"] is not None]
    if quiet:
        lines += ["", f"**Quiet:** {', '.join(quiet)}"]
    errors = [t["ticker"] for t in tickers if t["category"] == "error"]
    if errors:
        lines.append(f"**Data issues:** {', '.join(errors)}")
    last_day = (date.fromisoformat(report["session_date"]) + timedelta(days=COMING_UP_DAYS)).isoformat()
    soon = [e for e in upcoming if report["session_date"] < e["event_date"] <= last_day]
    if soon:
        lines += ["", "**Coming up:**"] + [f"• {events.event_line(e)}" for e in soon[:MAX_COMING_UP]]
        if len(soon) > MAX_COMING_UP:
            lines.append(f"…and {len(soon) - MAX_COMING_UP} more on the calendar")
    embed = {
        "title": _shorten(report["title"], MAX_TITLE),
        "description": _shorten("\n".join(lines), MAX_DESCRIPTION),
        "color": COLORS["neutral"],
        "footer": {"text": "End-of-day summary · research, not investment advice"},
        **_app_link(f"#/previous/{report['session_date']}"),
    }
    n = len(flagged)
    return {"content": f"**Daily summary:** {n} flagged move{'s' if n != 1 else ''}", "embeds": _fit([embed])}


def _fit(embeds: list[dict]) -> list[dict]:
    """Keep the whole message within Discord's 6,000-character limit by trimming descriptions."""
    def size():
        return sum(len(e.get("title", "")) + len(e.get("description", "")) + len(e.get("footer", {}).get("text", ""))
                   for e in embeds)
    while size() > MAX_TOTAL:
        longest = max(embeds, key=lambda e: len(e.get("description", "")))
        longest["description"] = _shorten(longest["description"], max(100, len(longest["description"]) - (size() - MAX_TOTAL) - 10))
    return embeds


# ---------------------------------------------------------------------------
# Deciding what to send
# ---------------------------------------------------------------------------

def _already(conn, session_date: str, kind: str, ticker: str | None = None) -> dict | None:
    """The latest alert of this kind that was sent (or is being sent right now by another run)."""
    recent = _stamp(_utc_now() - timedelta(seconds=PENDING_SECONDS))
    row = conn.execute(
        """SELECT * FROM alerts WHERE session_date = ? AND kind = ? AND ticker IS ?
           AND (status = 'sent' OR (status = 'pending' AND created_at >= ?))
           ORDER BY id DESC LIMIT 1""", (session_date, kind, ticker, recent)).fetchone()
    return dict(row) if row else None


def _grew(t: dict, previous: dict) -> bool:
    """Has the move grown a lot (or reversed) since its last alert?"""
    now, then = t["return_zscore"], previous["return_zscore"]
    if now is None or then is None:
        return False
    if now * then < 0:  # reversed direction
        return abs(now) >= 2
    return abs(now) >= abs(then) + ESCALATE_Z


def calendar_for(conn, report: dict) -> list[dict]:
    """Events from the report's day through the next couple of weeks (empty before the calendar exists)."""
    start = date.fromisoformat(report["session_date"])
    return events.upcoming(conn, start, max(COMING_UP_DAYS, NEXT_EVENT_DAYS), events.watchlist_tickers())


def plan(conn, session_date: str) -> dict:
    """What notify() would send now for a day's report: {"report", "flags", "summary"}."""
    report = reports_db.get_report(conn, session_date)
    result = {"report": report, "flags": [], "summary": False}
    if report is None:
        return result
    if report["status"] == "intraday" and SEND_FLAG_ALERTS:
        for t in report["tickers"]:
            if t["category"] != "flagged":
                continue
            previous = _already(conn, session_date, "flag", t["ticker"])
            if previous is None or _grew(t, previous):
                result["flags"].append((t, previous))
    if report["status"] == "final" and SEND_DAILY_SUMMARY:
        result["summary"] = _already(conn, session_date, "summary") is None
    return result


def _record(conn, session_date: str, kind: str, report: dict, t: dict | None = None) -> int:
    cursor = conn.execute(
        """INSERT INTO alerts (session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'pending', ?)""",
        (session_date, kind, t and t["ticker"], t and t["return_1d_pct"], t and t["return_zscore"],
         report["as_of"], _stamp(_utc_now())))
    return cursor.lastrowid


def _finish(conn, ids: list[int], error: str | None) -> None:
    conn.executemany("UPDATE alerts SET status = ?, error = ?, sent_at = ? WHERE id = ?",
                     [("failed" if error else "sent", error, None if error else _stamp(_utc_now()), i) for i in ids])


def notify(session_date: str, force_summary: bool = False) -> dict:
    """Send whatever alerts this day's saved report calls for. Safe to call after every run:
    anything already sent is skipped, and anything that failed before is tried again.

    Returns {"enabled", "sent": [...], "failed": [...]}, each entry a short description.
    """
    outcome = {"enabled": enabled(), "sent": [], "failed": []}
    if not outcome["enabled"]:
        return outcome
    with closing(connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")  # decide and claim in one step, so two runs can't both send
        try:
            todo = plan(conn, session_date)
            report = todo["report"]
            if report and force_summary and report["status"] == "final":
                todo["summary"] = True
            messages = []
            if todo["flags"]:
                ids = [_record(conn, session_date, "flag", report, t) for t, _ in todo["flags"]]
                label = "flag alert: " + ", ".join(t["ticker"] for t, _ in todo["flags"])
                messages.append((label, ids, flags_payload(report, todo["flags"], calendar_for(conn, report))))
            if todo["summary"]:
                messages.append((f"daily summary for {session_date}", [_record(conn, session_date, "summary", report)],
                                 summary_payload(report, calendar_for(conn, report))))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        for label, ids, payload in messages:
            try:
                send(payload)
                _finish(conn, ids, None)
                outcome["sent"].append(label)
            except Exception as e:  # recorded as failed: the next run tries again
                _finish(conn, ids, str(e) or type(e).__name__)
                outcome["failed"].append(f"{label} ({e})")
    return outcome


def recent(conn, limit: int = 20) -> list[dict]:
    """The latest alerts, newest first. Works on a read-only connection, even before the first alert."""
    try:
        return [dict(row) for row in conn.execute(
            """SELECT session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status, error,
                      created_at, sent_at FROM alerts ORDER BY id DESC LIMIT ?""", (limit,))]
    except Exception:  # no alerts table yet
        return []


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Discord alerts for the market analyst.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("test", help="send a test message")
    preview = commands.add_parser("preview", help="show what would be sent now, without sending")
    preview.add_argument("date", nargs="?", default="latest", help="YYYY-MM-DD or 'latest'")
    commands.add_parser("log", help="recent alerts")
    summary = commands.add_parser("summary", help="send a day's end-of-day summary")
    summary.add_argument("date")
    summary.add_argument("--force", action="store_true", help="send it even if it was sent already")
    args = parser.parse_args()

    if args.command == "test":
        try:
            send({"embeds": [{"title": "Alerts are set up", "color": COLORS["neutral"],
                              "description": "Flag alerts and daily summaries from your market analyst will appear here."}]})
        except (SendError, ValueError) as e:
            sys.exit(f"Couldn't send: {e}")
        print("Sent. Check your Discord channel.")
    elif args.command == "preview":
        with closing(connect()) as conn:
            day = args.date
            if day == "latest":
                row = conn.execute("SELECT session_date FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()
                if not row:
                    sys.exit("No reports yet.")
                day = row[0]
            todo = plan(conn, day)
            upcoming = calendar_for(conn, todo["report"]) if todo["report"] else []
        if todo["report"] is None:
            sys.exit(f"No report for {day}.")
        payloads = []
        if todo["flags"]:
            payloads.append(flags_payload(todo["report"], todo["flags"], upcoming))
        if todo["summary"]:
            payloads.append(summary_payload(todo["report"], upcoming))
        print(json.dumps(payloads, indent=2) if payloads else f"Nothing new to send for {day}.")
    elif args.command == "log":
        with closing(connect()) as conn:
            for a in recent(conn, 50):
                what = a["ticker"] or "summary"
                print(f"{a['created_at']}  {a['session_date']}  {a['kind']:<7}  {what:<8} {a['status']:<7} {a['error'] or ''}")
    elif args.command == "summary":
        if not enabled():
            sys.exit(f"Set {WEBHOOK_ENV} first (see the alerts guide).")
        outcome = notify(args.date, force_summary=args.force)
        print(outcome["sent"] or outcome["failed"] or "Nothing sent: the summary was already sent (use --force), "
                                                       "or that day has no final report.")


if __name__ == "__main__":
    main()
```

### ask.py

```python
"""Answer questions about saved reports with Claude, using retrieval (RAG).

For each question it gathers, within a size limit:
1. Figures across days for any watchlist ticker named in the question.
2. The events calendar: everything in the next 30 days, plus the last 30 days for named tickers.
3. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
4. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import events
import reports_db
import search_index

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports, passages and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05). Passages carry the date of the report they came from.
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- Dated events come from the events calendar: cite them as (calendar), and say so when a date isn't confirmed.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
CALENDAR_DAYS = 30               # events calendar: this far ahead (all tickers) and back (named tickers)
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


def calendar_section(conn, tickers: list[str]) -> str:
    """Upcoming events for the watchlist, and recent ones for the tickers asked about."""
    today = events.today_et()
    soon = events.upcoming(conn, today, CALENDAR_DAYS, events.watchlist_tickers())
    recent = events.upcoming(conn, today - timedelta(days=CALENDAR_DAYS), CALENDAR_DAYS - 1, tickers) if tickers else []
    if not soon and not recent:
        return ""
    lines = [f"## Events calendar (today is {today:%a} {today.isoformat()})", "", "Coming up:"]
    lines += [f"- {e['event_date']} {events.event_line(e)}" for e in soon] or ["- nothing in the next 30 days"]
    if recent:
        lines += ["", f"In the last {CALENDAR_DAYS} days, for {', '.join(tickers)}:"]
        lines += [f"- {e['event_date']} {events.event_line(e)}" for e in recent]
    return "\n".join(lines)


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

    calendar = calendar_section(conn, tickers)
    if calendar:
        add(calendar)

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

### search_index.py

```python
"""Search over saved reports: the "R" in RAG.

Each report is split into passages (one per flagged ticker, plus an overview). Two
kinds of search run over them and their rankings are blended:
- keywords: SQLite's built-in full-text search (finds "downgrade" for "downgraded")
- meaning:  Voyage AI embeddings (finds "analyst cut its rating" for "downgrade")

Ask uses this to pull relevant passages from any day in your history, and the app's
search box uses it directly. Without VOYAGE_API_KEY it still works, by keywords only.

The index is its own file, search.db, built from reports.db. Your reports are only
read; the index can be deleted and rebuilt at any time.

    python search_index.py sync                  index new or changed reports
    python search_index.py rebuild               delete the index and build it again
    python search_index.py status                what's indexed
    python search_index.py search "analyst downgrade"
"""

import argparse
import json
import os
import re
import sqlite3
from contextlib import closing
from pathlib import Path

import numpy as np

import reports_db

EMBED_MODEL = os.environ.get("VOYAGE_MODEL", "voyage-4")  # or voyage-finance-2, voyage-4-large...
EMBED_BATCH = 128       # passages per Voyage request (their limit is 1,000)
RRF_K = 60              # how keyword and meaning rankings are blended (reciprocal rank fusion)
MIN_SIMILARITY = 0.25   # meaning matches weaker than this are always left out
MEANING_CUTOFF = 0.85   # ...and so are those below 85% of the best match's similarity. Briefs share a
                        # template, so loosely related ones score fairly high; lower this to see more of them
MAX_QUERY_WORDS = 20

SCHEMA = """
CREATE TABLE IF NOT EXISTS indexed_reports (
    session_date TEXT PRIMARY KEY,
    revision     INTEGER NOT NULL        -- the report revision the passages were built from
);
CREATE TABLE IF NOT EXISTS chunks (
    id           INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,
    status       TEXT NOT NULL,
    ticker       TEXT,                   -- the ticker for its section; empty for the overview
    heading      TEXT NOT NULL,
    text         TEXT NOT NULL,
    embedding    BLOB,                   -- float32 vector; empty until embedded
    model        TEXT                    -- the embedding model that made it
);
CREATE INDEX IF NOT EXISTS idx_chunks_day ON chunks (session_date);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
    heading, text, content='chunks', content_rowid='id', tokenize='porter unicode61');
CREATE TRIGGER IF NOT EXISTS chunks_added AFTER INSERT ON chunks BEGIN
    INSERT INTO chunks_fts (rowid, heading, text) VALUES (new.id, new.heading, new.text);
END;
CREATE TRIGGER IF NOT EXISTS chunks_removed AFTER DELETE ON chunks BEGIN
    INSERT INTO chunks_fts (chunks_fts, rowid, heading, text) VALUES ('delete', old.id, old.heading, old.text);
END;
"""

TICKER_HEADING = re.compile(r"^### ([A-Z0-9.\-^=]{1,15})\b")
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9.\-']*")


def index_path() -> Path:
    """search.db next to reports.db, unless SEARCH_DB says otherwise."""
    return Path(os.environ.get("SEARCH_DB") or Path(reports_db.DB_PATH).with_name("search.db"))


def connect(path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(path or index_path(), timeout=10, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Embeddings (Voyage AI)
# ---------------------------------------------------------------------------

def vector_search_available() -> bool:
    return bool(os.environ.get("VOYAGE_API_KEY"))


def embed(texts: list[str], input_type: str) -> list[list[float]]:
    """Vectors from Voyage AI. input_type: "document" for passages, "query" for searches."""
    import voyageai  # pip install voyageai (only needed for meaning-based search)

    return voyageai.Client().embed(texts, model=EMBED_MODEL, input_type=input_type).embeddings


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------

SKIPPED_SECTIONS = ("Coming up",)  # forward-looking calendar lines: they'd make a search for "earnings"
                                   # find the days *before* each earnings date (Ask gets the calendar itself)


def chunk_report(report: dict) -> list[dict]:
    """Split a brief into passages: one per ticker section, plus an overview of the rest.
    Each passage starts with the report's title, so it carries its date wherever it goes."""
    news = {}
    for s in report.get("sources") or []:
        news.setdefault(s.get("ticker"), []).append(f"News: {s.get('title')} ({s.get('publisher')})")
    prefix = f"{report['title']} ({report['status']})"
    body = MARKDOWN_LINK.sub(r"\1", report["body_md"])  # index what readers see: link text, not URLs
    passages, overview = [], []
    for section in re.split(r"(?m)^(?=#{1,3} )", body):
        if not section.strip():
            continue
        first_line = section.strip().splitlines()[0]
        if first_line.lstrip("#").strip() in SKIPPED_SECTIONS:
            continue
        match = TICKER_HEADING.match(first_line)
        if match:
            ticker = match.group(1)
            text = "\n".join([section.strip(), *news.get(ticker, [])])
            passages.append({"ticker": ticker, "heading": first_line.lstrip("#").strip(), "text": f"{prefix}\n{text}"})
        else:
            overview.append(section.strip())
    if overview:
        passages.insert(0, {"ticker": None, "heading": "Overview", "text": f"{prefix}\n" + "\n\n".join(overview)})
    return passages


def embed_pending(conn) -> int:
    """Embed every passage that has no vector from the current model. Returns how many."""
    if not vector_search_available():
        return 0
    rows = conn.execute("SELECT id, text FROM chunks WHERE embedding IS NULL OR model IS NOT ?",
                        (EMBED_MODEL,)).fetchall()
    for start in range(0, len(rows), EMBED_BATCH):
        batch = rows[start:start + EMBED_BATCH]
        vectors = embed([r["text"] for r in batch], "document")
        conn.executemany("UPDATE chunks SET embedding = ?, model = ? WHERE id = ?",
                         [(np.asarray(v, dtype=np.float32).tobytes(), EMBED_MODEL, r["id"])
                          for r, v in zip(batch, vectors)])
    return len(rows)


def sync(embed_now: bool = True) -> dict:
    """Bring the index up to date with reports.db: index new reports, re-index changed
    ones (a newer intraday revision, or a day that was finalized), and drop removed ones.
    Passages are searchable by keyword straight away; embedding needs VOYAGE_API_KEY."""
    with closing(reports_db.connect(readonly=True)) as reports, closing(connect()) as conn:
        current = {r["session_date"]: r["revision"] for r in reports.execute("SELECT session_date, revision FROM reports")}
        conn.execute("BEGIN IMMEDIATE")  # one update at a time; a second one waits, then finds nothing to redo
        try:
            indexed = {r["session_date"]: r["revision"] for r in conn.execute("SELECT * FROM indexed_reports")}
            changed = [day for day, revision in current.items() if indexed.get(day) != revision]
            removed = [day for day in indexed if day not in current]
            for day in changed + removed:
                conn.execute("DELETE FROM chunks WHERE session_date = ?", (day,))
                conn.execute("DELETE FROM indexed_reports WHERE session_date = ?", (day,))
            for day in changed:
                report = reports_db.get_report(reports, day)
                conn.executemany(
                    "INSERT INTO chunks (session_date, status, ticker, heading, text) VALUES (?, ?, ?, ?, ?)",
                    [(day, report["status"], c["ticker"], c["heading"], c["text"]) for c in chunk_report(report)])
                conn.execute("INSERT INTO indexed_reports VALUES (?, ?)", (day, report["revision"]))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        embedded = embed_pending(conn) if embed_now else 0  # outside the transaction: searches carry on meanwhile
    return {"reports_indexed": len(changed), "reports_removed": len(removed), "passages_embedded": embedded}


def rebuild() -> dict:
    for suffix in ("", "-wal", "-shm"):
        Path(str(index_path()) + suffix).unlink(missing_ok=True)
    return sync()


def status() -> dict:
    with closing(reports_db.connect(readonly=True)) as reports, closing(connect()) as conn:
        total = reports.execute("SELECT COUNT(*) FROM reports").fetchone()[0]
        row = conn.execute("""SELECT (SELECT COUNT(*) FROM indexed_reports) AS reports,
                                     COUNT(*) AS passages, SUM(model IS ? AND embedding IS NOT NULL) AS embedded
                              FROM chunks""", (EMBED_MODEL,)).fetchone()
    return {"reports_total": total, "reports_indexed": row["reports"], "passages": row["passages"],
            "passages_embedded": row["embedded"] or 0, "model": EMBED_MODEL,
            "meaning_search": vector_search_available(), "index": str(index_path())}


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def search(query: str, limit: int = 10, ticker: str | None = None,
           since: str | None = None, until: str | None = None) -> dict:
    """Passages matching the query, best first. Each result says whether it matched by
    keywords, by meaning, or both. mode is "hybrid" or "keyword"."""
    words = WORD.findall(query)[:MAX_QUERY_WORDS]
    result = {"query": query, "mode": "keyword", "note": None, "terms": words, "results": []}
    if not words:
        return result
    filters, params = "", []
    for clause, value in (("c.ticker = ?", ticker and ticker.upper()), ("c.session_date >= ?", since),
                          ("c.session_date <= ?", until)):
        if value:
            filters += f" AND {clause}"
            params.append(value)

    with closing(connect()) as conn:
        # Keywords: every word is optional (OR); quoting stops punctuation being read as search syntax
        fts_query = " OR ".join('"' + w.replace('"', "") + '"' for w in words)
        keyword = [r[0] for r in conn.execute(
            f"""SELECT c.id FROM chunks_fts JOIN chunks c ON c.id = chunks_fts.rowid
                WHERE chunks_fts MATCH ?{filters} ORDER BY bm25(chunks_fts) LIMIT ?""",
            (fts_query, *params, limit * 3))]

        meaning = []
        if vector_search_available():
            rows = conn.execute(f"SELECT c.id, c.embedding FROM chunks c WHERE c.model = ? AND c.embedding IS NOT NULL{filters}",
                                (EMBED_MODEL, *params)).fetchall()
            if rows:
                try:
                    q = np.asarray(embed([query], "query")[0], dtype=np.float32)
                    matrix = np.vstack([np.frombuffer(r["embedding"], dtype=np.float32) for r in rows])
                    scores = matrix @ q / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(q) + 1e-9)
                    floor = max(MIN_SIMILARITY, float(scores.max()) * MEANING_CUTOFF)
                    meaning = [rows[i]["id"] for i in np.argsort(-scores)[:limit * 3] if scores[i] >= floor]
                    result["mode"] = "hybrid"
                except Exception as e:  # Voyage unreachable: keyword results still come back
                    result["note"] = f"Meaning-based search is unavailable right now ({e}); showing keyword matches."
            else:
                result["note"] = "The search index is still being embedded; showing keyword matches for now."

        fused = {}
        for ranking, label in ((keyword, "keywords"), (meaning, "meaning")):
            for rank, chunk_id in enumerate(ranking):
                entry = fused.setdefault(chunk_id, {"score": 0.0, "matched_by": []})
                entry["score"] += 1 / (RRF_K + rank + 1)
                entry["matched_by"].append(label)
        best = sorted(fused.items(), key=lambda item: -item[1]["score"])[:limit]
        if best:
            ids = [chunk_id for chunk_id, _ in best]
            rows = {r["id"]: r for r in conn.execute(
                f"SELECT * FROM chunks WHERE id IN ({','.join('?' * len(ids))})", ids)}
            result["results"] = [{
                "session_date": rows[i]["session_date"], "status": rows[i]["status"], "ticker": rows[i]["ticker"],
                "heading": rows[i]["heading"], "text": rows[i]["text"].split("\n", 1)[-1],  # without the title prefix
                "score": round(entry["score"], 5), "matched_by": entry["matched_by"],
            } for i, entry in best]
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Search index for saved reports.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("sync", help="index new or changed reports")
    commands.add_parser("rebuild", help="delete the index and build it again")
    commands.add_parser("status", help="what's indexed")
    find = commands.add_parser("search", help="search from the terminal")
    find.add_argument("query")
    args = parser.parse_args()
    if args.command == "search":
        for r in search(args.query)["results"]:
            print(f"{r['session_date']}  {r['heading']:<45} matched by {' + '.join(r['matched_by'])}")
    else:
        print(json.dumps({"sync": sync, "rebuild": rebuild, "status": status}[args.command](), indent=2))
```

### frontend/src/components/ComingUp.jsx

```jsx
import { useEffect, useState } from 'react'
import { getCalendar } from '../api'
import { formatWeekdayDate } from '../format'
import { routes } from '../useRoute'

const DAYS = 7  // how far ahead to look
const MAX_SHOWN = 6

const isoDay = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`

// The next week from the events calendar, on the Today tab. Each event links to its day on the Calendar tab.
export default function ComingUp({ version }) {
  const [data, setData] = useState(null)

  useEffect(() => {
    const start = new Date()
    const end = new Date()
    end.setDate(end.getDate() + DAYS + 1) // a day extra, in case the server's "today" is ahead of this computer's
    getCalendar(isoDay(start), isoDay(end))
      .then(setData)
      .catch(() => setData(null))
  }, [version])

  if (!data) return null
  const last = new Date(`${data.today}T12:00:00`)
  last.setDate(last.getDate() + DAYS)
  const soon = data.events.filter((e) => e.event_date >= data.today && e.event_date <= isoDay(last))

  return (
    <section className="panel coming-up" aria-label="Coming up">
      <div className="section-head">
        <h2>Coming up</h2>
        <a className="link small" href={routes.calendar()}>
          Calendar
        </a>
      </div>
      {soon.length === 0 ? (
        <p className="muted small">
          {data.last_scan ? 'Nothing on the calendar for the next week.' : 'The events calendar hasn’t been updated yet.'}
        </p>
      ) : (
        <ul>
          {soon.slice(0, MAX_SHOWN).map((e) => (
            <li key={e.id}>
              <a href={routes.calendar(e.event_date)}>
                <span className="cu-date">{e.event_date === data.today ? 'Today' : formatWeekdayDate(e.event_date)}</span>
                <span className="cu-what">
                  <strong>{e.company}</strong> <span className="muted">{e.title}</span>
                </span>
              </a>
            </li>
          ))}
        </ul>
      )}
      {soon.length > MAX_SHOWN && (
        <a className="link small" href={routes.calendar(soon[MAX_SHOWN].event_date)}>
          +{soon.length - MAX_SHOWN} more on the calendar
        </a>
      )}
    </section>
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
import ComingUp from './components/ComingUp'
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

### frontend/src/format.js

```javascript
// Display helpers

export const formatDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

export const formatWeekdayDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' })

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

### frontend/src/components/RunPanel.jsx

```jsx
import { useEffect, useState } from 'react'
import { getAlerts, startRun } from '../api'
import { formatDateTime, formatTime } from '../format'

const STEP_NAMES = {
  flag_events: () => 'Scanning the watchlist',
  get_news: (input) => `Reading news for ${input.ticker}`,
  compute_moves: (input) => `Checking ${input.ticker} in detail`,
  market_backdrop: () => 'Checking the market and sectors',
  upcoming_events: () => 'Checking the events calendar',
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

// One line on Discord alerts: on or off for runs started here, and the latest one sent by any run
function AlertsStatus({ refreshKey }) {
  const [info, setInfo] = useState(null)

  useEffect(() => {
    const load = () =>
      getAlerts()
        .then(setInfo)
        .catch(() => setInfo(null))
    load()
    const timer = setInterval(load, 60_000) // scheduled runs send alerts a moment after saving
    return () => clearInterval(timer)
  }, [refreshKey])

  if (!info) return null
  const last = info.alerts.find((a) => a.status !== 'pending')
  return (
    <p className="muted small alerts-status">
      {info.enabled ? 'Discord alerts on' : 'Discord alerts off for runs started here'}
      {last?.status === 'sent' &&
        ` · last sent ${formatDateTime(last.sent_at)} (${last.kind === 'summary' ? 'daily summary' : last.ticker})`}
      {last?.status === 'failed' && (
        <span className="alert-failed" title={last.error}>
          {' '}
          · last alert failed: {last.error}
        </span>
      )}
    </p>
  )
}

export default function RunPanel({ run, onStarted, lastSaved }) {
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
      <AlertsStatus refreshKey={`${lastSaved?.updated_at}|${run?.finished_at}`} />

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

### frontend/src/components/AskPanel.jsx

```jsx
import { useState } from 'react'
import { askQuestion } from '../api'
import Markdown from './Markdown'

const EXAMPLES = ['What moved the most this week?', 'Why was NVDA flagged?', "What's coming up next week?"]

export default function AskPanel() {
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState('')
  const [details, setDetails] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!question.trim() || busy) return
    setBusy(true)
    setAnswer('')
    setDetails(null)
    setError(null)
    try {
      await askQuestion(question, (event) => {
        if (event.type === 'delta') setAnswer((text) => text + event.text)
        else if (event.type === 'done') {
          setAnswer(event.answer)
          setDetails(event)
        } else if (event.type === 'error') setError(event.error)
      })
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <section className="panel">
      <h2>Ask about your reports</h2>
      <form onSubmit={submit}>
        <textarea
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && submit(e)}
          maxLength={500}
          rows={3}
          placeholder="e.g. Why was NVDA flagged this week?"
          aria-label="Your question"
        />
        <div className="row">
          <button className="primary" disabled={busy || !question.trim()}>
            {busy ? 'Answering…' : 'Ask'}
          </button>
          <span className="muted small">Answers come only from saved reports and the calendar.</span>
        </div>
      </form>
      <div className="examples">
        {EXAMPLES.map((q) => (
          <button key={q} type="button" className="chip" onClick={() => setQuestion(q)}>
            {q}
          </button>
        ))}
      </div>

      {error && <p className="error">{error}</p>}
      {answer && (
        <div className="answer" aria-live="polite">
          <Markdown text={answer} />
          {details && (
            <p className="muted small">
              Based on {details.reports_used.length} saved report{details.reports_used.length === 1 ? '' : 's'}
              {details.cost_usd > 0 && ` · $${details.cost_usd.toFixed(3)}`}
            </p>
          )}
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
```

### tests/test_calendar_links.py

```python
"""Offline tests for the events calendar's links to briefs, Discord alerts and Ask.

Run from the project folder:
    pytest -v tests/test_calendar_links.py
"""

import asyncio
import json
import sys
from contextlib import closing
from datetime import date, datetime, time
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import ask  # noqa: E402
import events  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
from mcp import Client  # noqa: E402

ET = ZoneInfo("America/New_York")
TODAY = date(2026, 11, 6)  # a Friday


def add(day, ticker, company, kind, title, date_note=None):
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, date_note, first_seen, last_seen)
                        VALUES (?, ?, ?, ?, ?, ?, 'x', 'x')""", (day, ticker, company, kind, title, date_note))


def calendar_updated():
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO event_scans (started_at, finished_at, trigger, status)
                        VALUES ('2026-11-06T14:35:00Z', '2026-11-06T14:35:09Z', 'scheduled', 'ok')""")


@pytest.fixture
def cal(tmp_path, monkeypatch):
    """A temporary database and watchlist, and the clock set to Friday 6 November 2026, 10am."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    watchlist = tmp_path / "watchlist.txt"
    watchlist.write_text("AAPL\nMSFT\nNVDA\nJPM\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", watchlist)
    monkeypatch.setattr(market_tools, "now_et", lambda: datetime.combine(TODAY, time(10, 0), ET))
    monkeypatch.setattr(events, "today_et", lambda: TODAY)


@pytest.fixture
def filled(cal):
    calendar_updated()
    add("2026-11-05", "AMZN", "Amazon.com", "earnings", "Earnings report")         # yesterday
    add("2026-11-06", "AAPL", "Apple", "dividend", "Ex-dividend date")             # today
    add("2026-11-09", "MSFT", "Microsoft", "news", "Court hearing in patent case")
    add("2026-11-16", "NVDA", "NVIDIA", "earnings", "Earnings report (date not confirmed)",
        "Estimated: Yahoo Finance shows a window of Nov 16 to Nov 20.")
    add("2026-11-19", "JPM", "JPMorgan Chase", "news", "Investor day")
    add("2026-11-25", "MSFT", "Microsoft", "news", "Shareholder vote")             # 19 days away
    add("2026-11-10", "TSLA", "Tesla", "news", "Not on the watchlist")


# ---------------------------------------------------------------------------
# The brief: the upcoming_events tool
# ---------------------------------------------------------------------------

def test_upcoming_events_lists_the_next_two_weeks_for_the_watchlist(filled):
    result = market_tools.upcoming_events()

    assert result["from"] == "2026-11-06" and result["to"] == "2026-11-20"
    assert [(e["date"], e["ticker"], e["days_away"]) for e in result["events"]] == [
        ("2026-11-06", "AAPL", 0), ("2026-11-09", "MSFT", 3), ("2026-11-16", "NVDA", 10), ("2026-11-19", "JPM", 13)]
    assert result["this_week"] == ["Fri Nov 6: Apple (AAPL): Ex-dividend date",
                                   "Mon Nov 9: Microsoft (MSFT): Court hearing in patent case"]
    nvda = result["events"][2]
    assert nvda["confirmed"] is False and nvda["line"] == "Mon Nov 16: NVIDIA (NVDA): Earnings report (date not confirmed)"
    assert result["calendar_updated"] == "2026-11-06T14:35:09Z" and "note" not in result


def test_upcoming_events_for_one_ticker_and_a_longer_range(filled):
    msft = market_tools.upcoming_events(" msft ", days=30)
    assert [e["date"] for e in msft["events"]] == ["2026-11-09", "2026-11-25"]
    assert market_tools.upcoming_events(days=500)["to"] == "2027-01-05"  # capped at 60 days
    assert market_tools.upcoming_events(days=0)["to"] == "2026-11-07"    # at least 1


def test_upcoming_events_before_the_calendar_exists(cal):
    result = market_tools.upcoming_events()
    assert result["events"] == [] and result["this_week"] == [] and result["calendar_updated"] is None
    assert "hasn't been filled in yet" in result["note"]


def test_upcoming_events_through_mcp(filled):
    async def call():
        async with Client(market_tools.mcp) as client:
            return await client.call_tool("upcoming_events", {"ticker": "JPM"})

    result = asyncio.run(call())

    assert not result.is_error
    assert [e["title"] for e in json.loads(result.content[0].text)["events"]] == ["Investor day"]


def test_the_brief_has_a_coming_up_section():
    prompt = (Path(market_tools.__file__).parent / "analyst_prompt.md").read_text()
    assert "## Coming up" in prompt and "upcoming_events.this_week" in prompt
    assert "Don't say the event caused the move unless the news says so." in prompt


def test_search_leaves_out_the_coming_up_section():
    """Otherwise a search for "earnings" would find the days before each earnings date."""
    import search_index
    body = ("# Watchlist brief: 2026-11-06\n\n## Market backdrop\n\nThe S&P 500 rose.\n\n## Quiet\n\nAAPL (+0.2%)\n\n"
            "## Coming up\n\n- Mon Nov 16: NVIDIA (NVDA): Earnings report\n")
    passages = search_index.chunk_report({"title": "Watchlist brief: 2026-11-06", "status": "final", "body_md": body})

    assert len(passages) == 1 and "The S&P 500 rose." in passages[0]["text"]
    assert "Earnings report" not in passages[0]["text"] and "Coming up" not in passages[0]["text"]


# ---------------------------------------------------------------------------
# Discord alerts
# ---------------------------------------------------------------------------

def save_report(status, flagged=("NVDA",)):
    as_of = "2026-11-06" if status == "final" else "2026-11-06 12:30 ET"
    scan = {"session": {"status": "complete" if status == "final" else "in_progress", "as_of": as_of},
            "flagged": [{"ticker": t, "last_price": 100.0, "return_1d_pct": -4.0, "return_zscore": -3.0,
                         "volume_vs_avg": 2.0} for t in flagged],
            "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.2}], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date="2026-11-06", status=status, title="Watchlist brief: 2026-11-06",
                               body_md="# Watchlist brief", as_of=as_of, scan=scan)


@pytest.fixture
def sent(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/secret")
    messages = []
    monkeypatch.setattr(alerts, "send", lambda payload: messages.append(payload) or "1")
    return messages


def test_daily_summary_lists_the_coming_week(filled, sent):
    save_report("final")
    alerts.notify("2026-11-06")
    text = sent[0]["embeds"][0]["description"]

    # Only the 7 days after the report's day, and only watchlist companies (not Tesla on Nov 10)
    assert text.endswith("**Coming up:**\n• Mon Nov 9: Microsoft (MSFT): Court hearing in patent case")


def test_daily_summary_caps_the_list(cal, sent):
    calendar_updated()
    for day in range(7, 14):  # 7 events in the coming week
        add(f"2026-11-{day:02d}", "MSFT", "Microsoft", "news", f"Event {day}")
    save_report("final")
    alerts.notify("2026-11-06")
    text = sent[0]["embeds"][0]["description"]

    assert text.count("• ") == alerts.MAX_COMING_UP and "…and 1 more on the calendar" in text


def test_a_flag_card_mentions_the_tickers_next_event(filled, sent):
    save_report("intraday", flagged=("NVDA", "MSFT"))
    alerts.notify("2026-11-06")
    cards = {e["title"].split()[0]: e["description"] for e in sent[0]["embeds"]}

    assert "**Coming up:** Mon Nov 16: Earnings report (date not confirmed)" in cards["NVDA"]
    assert "**Coming up:** Mon Nov 9: Court hearing in patent case" in cards["MSFT"]  # its soonest, not Nov 25


def test_alerts_work_without_a_calendar(cal, sent):
    save_report("intraday")
    alerts.notify("2026-11-06")
    assert "Coming up" not in sent[0]["embeds"][0]["description"]


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

def test_ask_sees_the_calendar(filled):
    with closing(reports_db.connect(readonly=True)) as conn:
        context = ask.calendar_section(conn, ["AMZN"])

    assert context.startswith("## Events calendar (today is Fri 2026-11-06)")
    assert "- 2026-11-16 Mon Nov 16: NVIDIA (NVDA): Earnings report (date not confirmed)" in context
    assert "- 2026-11-25 Wed Nov 25: Microsoft (MSFT): Shareholder vote" in context  # 30 days ahead
    assert "In the last 30 days, for AMZN:\n- 2026-11-05 Thu Nov 5: Amazon.com (AMZN): Earnings report" in context


def test_ask_includes_the_calendar_in_its_context(filled):
    save_report("final")
    with closing(reports_db.connect(readonly=True)) as conn:
        context, _ = ask.build_context(conn, "What's coming up next week?")
    assert "## Events calendar" in context and "Court hearing in patent case" in context
    assert "(calendar)" in ask.SYSTEM_PROMPT


def test_ask_without_a_calendar_has_no_calendar_section(cal):
    with closing(reports_db.connect(readonly=True)) as conn:
        assert ask.calendar_section(conn, ["NVDA"]) == ""
```
