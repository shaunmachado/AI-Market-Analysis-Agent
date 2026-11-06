# Market Analyst Agent: Frontend (React + Vite)

A local web app for the market analyst agent, with two tabs.

**Today tab:**

- **Latest report:** today's report, updating live as new information is saved.
- **Request a fresh report:** a button that runs the agent now, with progress shown step by step.
- **Ask about your reports:** type a question and Claude answers from saved reports, word by word.
- **Previous days preview:** the last 3 days at a glance, each linking to its full report.

**Previous days tab:** every earlier day's report, grouped by month, with the chosen day shown beside the list.

This builds on `market-agent-database.md`. Finish that guide first, so `reports.db` exists and its tests pass.

**Already built the earlier version of this guide?** The backend is unchanged. In `frontend/src/`:

- **Add** `useRoute.js`, `components/PreviousDaysPreview.jsx` and `components/PreviousDaysTab.jsx`
- **Replace** `App.jsx`, `format.js`, `styles.css`, `components/StatusBadge.jsx` and `components/ReportView.jsx`
- **Delete** `components/PreviousDays.jsx`

All the code is in the [appendix](#appendix-full-source-code).

---

## Contents

1. [What you're building](#1-what-youre-building)
2. [How the live updates work](#2-how-the-live-updates-work)
3. [Before you start](#3-before-you-start)
4. [Part A: Backend](#4-part-a-backend)
5. [Part B: Frontend](#5-part-b-frontend)
6. [Run it](#6-run-it)
7. [Using the app](#7-using-the-app)
8. [Settings and costs](#8-settings-and-costs)
9. [Test it](#9-test-it)
10. [API additions reference](#10-api-additions-reference)
11. [Security](#11-security)
12. [Troubleshooting](#12-troubleshooting)
13. [Next steps](#13-next-steps)
14. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What you're building

### The Today tab

```
┌ Market Analyst   [Today]  Previous days ─────────────────── ● Live ┐
│ ┌ LATEST REPORT ──────────────────── ┐ ┌ RUN NOW ─────────────── ┐ │
│ │ [Intraday · updating] As of 14:05  │ │ [Run update now]        │ │
│ │ Ticker  Status   Price  Change     │ │ 1. Scanning watchlist   │ │
│ │ TSLA    flagged  255.0  +5.90%     │ │ 2. News for NVDA        │ │
│ │ Intraday update: ... (the brief)   │ └─────────────────────────┘ │
│ │ Sources (3)                        │ ┌ ASK ─────────────────── ┐ │
│ └────────────────────────────────────┘ │ [question]  [Ask]       │ │
│                                        │ answer appears live     │ │
│                                        └─────────────────────────┘ │
│ ┌ PREVIOUS DAYS ──────────────────────── See all previous days → ┐ │
│ │ ┌ Nov 5 Final ──── ┐ ┌ Nov 4 Final ──── ┐ ┌ Nov 3 Final ──── ┐ │ │
│ │ │ NVDA +6.50%      │ │ Nothing flagged  │ │ JPM -2.80%       │ │ │
│ │ └──────────────────┘ └──────────────────┘ └──────────────────┘ │ │
│ └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

The preview always shows the **3 days before the latest report**. Each card shows the day's flagged tickers and opens that day on the Previous days tab.

### The Previous days tab

```
┌ Market Analyst    Today  [Previous days] ────────────────── ● Live ┐
│ ┌ ALL PREVIOUS DAYS ─────────────────────────────────── 30+ days ┐ │
│ │ NOVEMBER 2026           │ [Final] As of 2026-11-05             │ │
│ │ ▸ Thu, Nov 5  1 flagged │ Ticker  Status   Price  Change       │ │
│ │   Wed, Nov 4  0 flagged │ NVDA    flagged  150.0  +6.50%       │ │
│ │ OCTOBER 2026            │                                      │ │
│ │   Fri, Oct 30 1 flagged │ Watchlist brief: 2026-11-05          │ │
│ │   ...                   │ (the brief)                          │ │
│ │ [Load older days]       │                                      │ │
│ └────────────────────────────────────────────────────────────────┘ │
└────────────────────────────────────────────────────────────────────┘
```

Every day before the latest report, newest first and grouped by month, 30 at a time. The newest day opens by default.

**Tabs use the page address**, so they can be bookmarked and the browser's Back button works:

| Address | Shows |
|---|---|
| `http://localhost:5173/` | Today |
| `http://localhost:5173/#/previous` | Previous days, newest day open |
| `http://localhost:5173/#/previous/2026-11-05` | Previous days, with 5 November open |

Both tabs stay loaded in the background, so switching tabs never loses a streamed answer or a run's progress. The app works in light and dark mode, and stacks into one column on a phone.

### How the pieces connect

```
 Browser (React app, port 5173)
    │   GET  /api/reports...         read reports
    │   GET  /api/events             live updates (stays open)
    │   POST /api/runs               "Run update now"
    │   POST /api/ask                questions (answer streams back)
    ▼
 Vite dev server ──forwards /api──▶ api.py (port 8000) ──reads──▶ reports.db
                                      │                               ▲
                                      ├── run_brief.run_once() ───────┤ writes
                                      └── ask.py ──▶ Claude           │
                                                                      │
 Scheduled runs (cron / Task Scheduler) ── run_brief.py ──────────────┘
```

### Files

| File | Status | Role |
|---|---|---|
| `run_brief.py` | **Changed** | Reports each step as it goes, so the app can show progress. The command line works the same |
| `ask.py` | **New** | Answers questions from saved reports |
| `api.py` | **Changed** | Adds live updates, Run now, Ask, and serving the built app |
| `tests/test_frontend_api.py` | **New** | Offline tests for everything above |
| `frontend/` | **New** | The React app |
| `market_tools.py`, `reports_db.py`, `analyst_prompt.md`, `watchlist.txt`, `requirements.txt` | Unchanged | |

**No new Python packages.** The frontend needs Node.js and three npm packages: React, `marked` (turns markdown into HTML) and `dompurify` (strips anything unsafe from it).

---

## 2. How the live updates work

**Server-Sent Events (SSE).** The browser opens one long-lived connection to `/api/events`, and the API pushes a small message whenever something happens. Browsers support this natively through `EventSource`, which also reconnects automatically if the API restarts.

| Event | Sent when | What the page does |
|---|---|---|
| `hello` | The page connects or reconnects | Loads the latest report and any run in progress, so nothing is missed |
| `report_saved` | **Any** run saves a report, including scheduled runs | Reloads the latest report, the 3-day preview and the Previous days tab |
| `run_started` | Someone presses Run update now | Shows the run's progress panel |
| `run_event` | Each step of that run (scanning, reading news, saved) | Adds a line to the progress list |
| `run_finished` | The run finishes or fails | Shows the result or the error |

**Catching scheduled runs.** Scheduled runs are separate programs, so the API can't hear them directly. Instead it checks the database every 2 seconds and sends `report_saved` when the newest report changes. This is how a 12:30pm scheduled update appears on an open page without a refresh.

**Run now runs inside the API.** Pressing the button runs the same `run_once()` used by `run_brief.py`, with the same storage rules. Only one run can happen at a time, with a 5-minute cooldown between on-demand runs to keep costs down. Everyone with the page open sees the same progress.

**Ask streams its answer.** `/api/ask` sends the answer back as it's written, one small JSON message per line, and the page appends each piece as it arrives.

---

## 3. Before you start

- [ ] You've completed `market-agent-database.md`, and `pytest -v` shows `54 passed, 1 skipped`
- [ ] You have **Node.js 22 LTS** or newer. Check with `node --version`; install from [nodejs.org](https://nodejs.org) if needed
- [ ] `ANTHROPIC_API_KEY` is set in the terminal where you'll run the API (Run now and Ask both call Claude)

---

## 4. Part A: Backend

Work in the `market-agent` folder with your virtual environment active.

### Step 1: Update run_brief.py

Replace `run_brief.py` with the version in the [appendix](#run_briefpy).

**What changed:**

- The work now lives in `run_once(emit)`. It calls `emit(event)` at each step (`started`, `tool_call`, `warning`, then `saved` or `skipped`), which is what feeds the progress panel.
- Slow data calls run in the background (`asyncio.to_thread`), so the API stays responsive during a run.
- A failed run now raises an error instead of exiting, so the API can show it on the page.
- **The command line is unchanged.** `python run_brief.py` prints the same lines as before, plus a "Writing the … report" line at the start.

### Step 2: Create ask.py

Create `ask.py` with the code from the [appendix](#askpy).

**How it answers without RAG:** it gathers the right material straight from the database:

1. The 10 most recent reports.
2. For any watchlist ticker named in the question (any letter case, such as `nvda`): that ticker's figures across days, plus up to 10 more reports where it was flagged.
3. All of this is capped at 60,000 characters, newest first, to keep each question's cost predictable.

Claude is told to answer only from that material, to cite report dates, never to estimate numbers, and never to give buy/sell advice. It has no tools, and each question is capped at $0.25.

When your history grows large, RAG replaces step 1 and step 2 with a search. Nothing else in the app has to change.

### Step 3: Replace api.py

Replace `api.py` with the version in the [appendix](#apipy). Every endpoint from the database guide still works the same.

**What's new:**

| Addition | Purpose |
|---|---|
| `GET /api/events` and `watch_reports()` | Live updates (section 2) |
| `POST /api/runs` and `GET /api/runs/current` | Run update now, and its progress for anyone who opens the page mid-run |
| `POST /api/ask` | Questions, with the answer streamed back |
| `_post_guard()` | Stops other websites from triggering runs or questions through your browser (section 11) |
| `create_app()` | Also serves the built React app at `/` once you run `npm run build` |

Report data is still only read through a read-only database connection. The only thing that writes is a run, using the normal storage rules.

### Step 4: Add and run the backend tests

Create `tests/test_frontend_api.py` with the code from the [appendix](#teststest_frontend_apipy), then run:

```bash
pytest -v
```

**Expected result:** `74 passed, 1 skipped` (54 from before, plus 20 new). [Section 9](#9-test-it) explains what each new test proves.

---

## 5. Part B: Frontend

### Step 5: Create the React app

From the `market-agent` folder:

```bash
npm create vite@latest frontend -- --template react
cd frontend
npm install
npm install marked dompurify
```

If `npm create` asks any questions, accept the defaults. If it offers to install and start the app now, you can say no; you've just done the install yourself.

### Step 6: Configure Vite

Replace these two files in `frontend/` with the versions in the appendix:

- [`vite.config.js`](#frontendviteconfigjs): runs the app on port 5173 and forwards every `/api` request, including the live stream, to the API on port 8000. Because of this, the browser only ever talks to one address.
- [`index.html`](#frontendindexhtml): sets the page title.

### Step 7: Add the app code

In `frontend/src/`, create a `components` folder, then create these files with the code from the appendix:

| File | What it does |
|---|---|
| [`main.jsx`](#frontendsrcmainjsx) | Starts the app (replace the generated one) |
| [`App.jsx`](#frontendsrcappjsx) | The two tabs, the page layout, and handling of live events (replace the generated one) |
| [`api.js`](#frontendsrcapijs) | Every call to the API, including reading the streamed answer |
| [`useLiveEvents.js`](#frontendsrcuseliveeventsjs) | Keeps the live-updates connection open |
| [`useRoute.js`](#frontendsrcuseroutejs) | Works out which tab and day to show from the page address |
| [`format.js`](#frontendsrcformatjs) | Formats dates, numbers and links for display |
| [`styles.css`](#frontendsrcstylescss) | All styling, including dark mode |
| [`components/StatusBadge.jsx`](#frontendsrccomponentsstatusbadgejsx) | The "Final", "Intraday · updating" and "Intraday (not finalized)" badges |
| [`components/Markdown.jsx`](#frontendsrccomponentsmarkdownjsx) | Renders a brief safely |
| [`components/TickerTable.jsx`](#frontendsrccomponentstickertablejsx) | The figures table |
| [`components/ReportView.jsx`](#frontendsrccomponentsreportviewjsx) | One full report: badge, table, brief and sources |
| [`components/RunPanel.jsx`](#frontendsrccomponentsrunpaneljsx) | Run update now and its progress |
| [`components/AskPanel.jsx`](#frontendsrccomponentsaskpaneljsx) | The question box and the streamed answer |
| [`components/PreviousDaysPreview.jsx`](#frontendsrccomponentspreviousdayspreviewjsx) | The 3-day preview cards on the Today tab |
| [`components/PreviousDaysTab.jsx`](#frontendsrccomponentspreviousdaystabjsx) | The Previous days tab: every day by month, with paging and the open report |

The generated `src/App.css`, `src/index.css` and `src/assets/` folder are no longer used. You can delete them.

Your project now looks like this:

```
market-agent/
├── market_tools.py   reports_db.py   run_brief.py   ask.py   api.py
├── analyst_prompt.md   watchlist.txt   requirements.txt   reports.db
├── tests/
│   ├── test_market_tools.py   test_reports_db.py   test_frontend_api.py
└── frontend/
    ├── index.html   vite.config.js   package.json   node_modules/
    └── src/
        ├── main.jsx   App.jsx   api.js   useLiveEvents.js   useRoute.js   format.js   styles.css
        └── components/
            ├── StatusBadge.jsx   Markdown.jsx   TickerTable.jsx   ReportView.jsx
            ├── RunPanel.jsx   AskPanel.jsx
            └── PreviousDaysPreview.jsx   PreviousDaysTab.jsx
```

If you use git, add these lines to `.gitignore`:

```
frontend/node_modules/
frontend/dist/
```

---

## 6. Run it

### While developing (two terminals)

**Terminal 1: the API.** From `market-agent`, with the virtual environment active and `ANTHROPIC_API_KEY` set:

```bash
uvicorn api:app --port 8000
```

**Terminal 2: the frontend.** From `market-agent/frontend`:

```bash
npm run dev
```

Open **http://localhost:5173**. The dot in the top right should say **Live**. The Previous days tab is at http://localhost:5173/#/previous. Edits to files in `src/` show up immediately.

### As one server (no dev server)

```bash
cd frontend
npm run build      # creates frontend/dist
cd ..
uvicorn api:app --port 8000
```

Open **http://localhost:8000**. The API now serves the app too. Run `npm run build` again after changing the frontend, then restart uvicorn.

Scheduled runs keep working exactly as before. Their reports appear on any open page within about 2 seconds.

---

## 7. Using the app

| Part | How to use it |
|---|---|
| **Tabs** | **Today** and **Previous days**, at the top. The Back button moves between tabs and days you've opened. |
| **Latest report** (Today) | Shows the newest report. "Intraday · updating" means the market is open and it will refresh by itself; "Final" means the day is done and the report is permanent. |
| **Request a fresh report** (Today) | Press **Run update now**. Each step appears as it happens, and the latest report refreshes when it's saved. During market hours you get an intraday update; after the close, you get the day's final report (or a note that it's already saved, at no cost). |
| **Ask about your reports** (Today) | Type a question or pick an example, then press **Ask** (or Enter). The answer appears as it's written, with report dates cited. The line underneath shows how many reports it used and what it cost. |
| **Previous days preview** (Today) | The 3 days before the latest report, with their flagged tickers. Click a card to read that day, or **See all previous days →** for the full list. |
| **Previous days tab** | Every day before the latest one, grouped by month. Click a day to read it; use **Load older days** for more. Copy the address to bookmark or share a day. |

**Badges:** "Final" is a finished, permanent report. "Intraday · updating" is today's report while the market is open. "Intraday (not finalized)" on an older day means no run happened while the market was closed afterwards, so its final report was never written (for example, the computer was off overnight). It won't change any more.

---

## 8. Settings and costs

Set these environment variables in the API's terminal before starting uvicorn:

| Variable | Default | What it controls |
|---|---|---|
| `RUN_COOLDOWN_SECONDS` | `300` | Minimum wait between Run now presses |
| `REPORT_POLL_SECONDS` | `2` | How often the API checks for reports saved by scheduled runs |
| `FRONTEND_ORIGINS` | `http://localhost:3000,http://localhost:5173` | Website addresses allowed to call the API, including Run now and Ask |
| `REPORTS_DB` | `reports.db` in the project folder | Database location (from the database guide) |

The question settings live at the top of `ask.py`: `RECENT_REPORTS`, `FLAGGED_REPORTS_PER_TICKER`, `MAX_CONTEXT_CHARS`, and the `max_budget_usd` cost cap.

**Costs:**

| Action | Cost |
|---|---|
| Run update now | One agent run, the same as a scheduled run (capped at $1). Free if the final report already exists |
| Ask a question | One Claude call, capped at $0.25. Shown under each answer |
| Reading reports, live updates, Previous days | Free (no Claude calls) |

---

## 9. Test it

### 9.1 Automated tests

```bash
pytest -v
```

Expect `74 passed, 1 skipped`. They need no internet or API key: Claude, market data and the database are all replaced with test versions.

**What the new tests prove (`tests/test_frontend_api.py`):**

| Test | Proves that |
|---|---|
| `test_run_once_reports_progress_events` | A run reports its steps in order (started, each tool call, saved) |
| `test_run_now_writes_a_report_and_shows_progress` | Run now starts in the background, saves a report, and its full progress can be fetched |
| `test_run_now_allows_one_run_at_a_time_then_a_cooldown` | A second press during a run is refused (409), then the cooldown applies (429) |
| `test_run_now_failure_is_reported` | A failed run shows its error instead of disappearing |
| `test_other_websites_cannot_trigger_runs_or_questions` (2 cases) | Requests from other websites, and plain form posts, are refused |
| `test_frontend_origin_can_post` | Your frontend's address is allowed |
| `test_events_stream_sends_hello_then_live_events` | The live stream starts with a catch-up message, passes on events, and cleans up when a tab closes |
| `test_watcher_announces_reports_saved_by_any_run` | Saves made by other programs (scheduled runs) are announced, including each intraday update |
| `test_ask_streams_the_answer` | Answers stream piece by piece, finish with the full answer and the reports used, and include figures for a ticker named in lowercase |
| `test_ask_includes_older_reports_for_the_ticker_asked_about` | Naming a ticker brings in its older flagged reports |
| `test_ask_context_stays_within_its_size_limit` | The material sent to Claude never exceeds the cap |
| `test_ask_with_no_reports_does_not_call_claude` | With an empty database, it says so without spending anything |
| `test_ask_failure_is_streamed_as_an_error` | Claude errors reach the page as a readable message |
| `test_ask_rejects_bad_questions` (4 cases), `test_ask_rejects_broken_json` | Empty, too-long or malformed questions get a 400 |
| `test_built_frontend_is_served_alongside_the_api` | After `npm run build`, the API serves the app at `/` and the API still works |

**What was also tested before this guide was written:** the React app was built and driven in a real Chromium browser against the real API, with Claude and market data faked and 40 days of sample reports. All of these passed, with no browser errors:

1. The Today tab shows the latest report and the "Live" connection; the Previous days tab starts hidden.
2. Unsafe HTML and `javascript:` links planted in a report are stripped, and nothing runs.
3. Run update now shows each step live, then the latest report refreshes by itself. A second press shows the cooldown message.
4. A question's answer streams in piece by piece, with markdown formatting.
5. The preview shows exactly the 3 days before the latest report, with their flagged tickers.
6. **See all previous days** opens the tab: the first 30 days, grouped by month, with the newest day open.
7. **Load older days** brings in the rest (39 days in total), without repeating month headings.
8. Picking a day opens it and updates the address. A day that was never finalized is labelled "Intraday (not finalized)".
9. The Back button steps back through days, then tabs, and the Today tab still shows its earlier answer.
10. Clicking a preview card opens that day on the Previous days tab.
11. A bookmarked address for a day (`#/previous/2026-11-02`) opens straight to it.
12. Reports saved by a separate program (like a scheduled run) appear without a reload, and finalizing the day switches the badge to "Final" while the preview still shows the 3 days before it.
13. At phone width, neither tab scrolls sideways, and picking a day scrolls down to its report.
14. Dark mode renders correctly.

**Not yet tested:** Vite's own dev server and proxy (the browser test bundled the app with a different tool), and runs and answers from real Claude. The checks below cover both.

### 9.2 Manual checks on your machine

- [ ] `npm run dev` starts with no errors, and http://localhost:5173 shows "Live"
- [ ] The latest report matches `python reports_db.py show latest`
- [ ] **Run update now** shows its steps and ends with "Saved (…)", and the latest report updates without a refresh
- [ ] Pressing it again straight away shows "Please wait … seconds"
- [ ] A question such as "Why was NVDA flagged?" streams an answer that cites report dates, and the cost line appears underneath
- [ ] With the page open, run `python run_brief.py` in another terminal. When it finishes, the page updates within a few seconds
- [ ] Stop the API (Ctrl+C). The page shows "Reconnecting…". Start the API again and it goes back to "Live" by itself
- [ ] The Today tab's preview shows the 3 days before the latest report, and clicking a card opens that day on the Previous days tab
- [ ] The Previous days tab lists every earlier day by month, and **Load older days** appears once you have more than 30
- [ ] Copying the address of an open day into a new browser tab opens the same day, and the Back button moves between days and tabs
- [ ] After `npm run build` and restarting the API, http://localhost:8000 shows the same app

---

## 10. API additions reference

The endpoints from the database guide are unchanged. New ones:

### `GET /api/events`: live updates

A Server-Sent Events stream. Each message is `data: {json}` with a `type`:

```
data: {"type": "hello", "run": {...}, "latest": {"session_date": "2026-11-06", "status": "intraday", "revision": 2, "updated_at": "2026-11-06T19:05:12Z"}}
data: {"type": "report_saved", "session_date": "2026-11-06", "status": "intraday", "revision": 3, "updated_at": "..."}
data: {"type": "run_started", "run": {...}}
data: {"type": "run_event", "event": {"type": "tool_call", "tool": "mcp__market__get_news", "input": {"ticker": "NVDA"}}}
data: {"type": "run_finished", "run": {...}}
```

A keep-alive comment is sent every 15 seconds when nothing else happens.

### The run object

```json
{
  "state": "finished",
  "started_at": "2026-11-06T19:04:40Z",
  "finished_at": "2026-11-06T19:05:12Z",
  "log": [
    {"type": "started", "session_date": "2026-11-06", "status": "intraday"},
    {"type": "tool_call", "tool": "mcp__market__flag_events", "input": {}},
    {"type": "saved", "outcome": "updated", "session_date": "2026-11-06", "status": "intraday", "turns": 5, "cost_usd": 0.041}
  ],
  "result": {"type": "saved", "outcome": "updated", "...": "..."},
  "error": null
}
```

`state` is `idle` (no run yet since the API started), `running`, `finished` or `failed`. Log entries may also be `warning` or `skipped`, each with a `message`.

### `POST /api/runs`: run update now

Send `{}` with `Content-Type: application/json`.

| Status | Meaning |
|---|---|
| `202` | Started. Body: `{"run": {...}}`. Follow progress through `/api/events` or `/api/runs/current` |
| `409` | A run is already in progress |
| `429` | The cooldown hasn't passed. The error message says how long to wait |
| `403` / `415` | Blocked by the safety check (section 11) |

### `GET /api/runs/current`

Returns `{"run": {...}}`: the run in progress, or the last one.

### `POST /api/ask`: ask a question

Send `{"question": "Why was NVDA flagged?"}` with `Content-Type: application/json`. Questions can be up to 500 characters.

The response streams one JSON object per line (`application/x-ndjson`):

```
{"type": "delta", "text": "NVDA was flagged "}
{"type": "delta", "text": "after earnings (2026-11-05)."}
{"type": "done", "answer": "NVDA was flagged after earnings (2026-11-05).", "reports_used": ["2026-11-06", "2026-11-05"], "cost_usd": 0.012}
```

or, if something goes wrong, `{"type": "error", "error": "..."}`.

| Status | Meaning |
|---|---|
| `200` | Streaming (check the last line for `done` or `error`) |
| `400` | Missing, empty or too-long question, or invalid JSON |
| `429` | Two questions are already being answered |
| `403` / `415` | Blocked by the safety check |

---

## 11. Security

**Already in place:**

- **Local only.** The API listens on `127.0.0.1` and Vite on `localhost`, so only your computer can reach them.
- **Other websites can't spend your money.** Without protection, any web page you visit could quietly send a request to `localhost:8000` and trigger runs. `_post_guard()` refuses requests from addresses not in `FRONTEND_ORIGINS`, and requires JSON, which browsers won't send cross-site without permission.
- **Reports can't inject code.** Briefs quote news headlines from the web, so `Markdown.jsx` runs everything through DOMPurify, which strips scripts, event handlers, images and styles, and source links must start with `http`. The browser test confirmed planted attacks were neutralised.
- **Costs are capped:** one run at a time, a cooldown, $1 per run, $0.25 per question, and at most two questions at once.
- **Reports stay protected.** The frontend can't edit or delete anything, and final reports remain permanent at the database level.

**Before anyone else can use it:**

- Add a login. Today anyone who can reach the app can press Run now and ask questions on your API key.
- Serve it over HTTPS, and set `FRONTEND_ORIGINS` to the real address only.
- Consider limiting Run now and Ask to specific users, since those are the actions that cost money.
- Never put `ANTHROPIC_API_KEY` in the frontend code. It belongs only in the API's environment, as it is now.

---

## 12. Troubleshooting

| Problem | Cause and fix |
|---|---|
| The page says **Reconnecting…** | The API isn't running, or isn't on port 8000. Check terminal 1. Vite forwards to `http://127.0.0.1:8000`. |
| `npm: command not found` | Node.js isn't installed, or the terminal was opened before installing it. Install Node.js 22 LTS and open a new terminal. |
| Run now or Ask gives **requests from this website aren't allowed** | Vite started on a different port (such as 5174, because 5173 was busy). Add that address to `FRONTEND_ORIGINS` and restart the API, or free port 5173. |
| A run fails with an authentication error | `ANTHROPIC_API_KEY` isn't set in the API's terminal. Set it and restart uvicorn. |
| A run fails with `CLINotFoundError` | The Claude Agent SDK install is incomplete. Run `pip install -U claude-agent-sdk` in the virtual environment. |
| A run fails with `no intraday data for SPY` | Yahoo's data didn't load. Wait a minute and try again (the cooldown still applies). |
| **Please wait … seconds** | That's the cooldown. Lower `RUN_COOLDOWN_SECONDS` if you need to test faster. |
| The answer says there are no saved reports | Run the agent at least once first. |
| Changes appear only after a refresh | Something between the browser and the API is holding back the live stream (some antivirus or proxy software does this). Test directly with `curl -N http://127.0.0.1:8000/api/events`; you should see a `hello` line straight away. |
| A blank page at http://localhost:8000 | The API checks for `frontend/dist` when it starts. Run `npm run build`, then restart uvicorn. |
| The preview or Previous days tab is empty | There's only one day of reports so far. Earlier days appear once you have them. |
| The preview shows fewer than 3 days | There are fewer than 3 days before the latest report so far. |
| An older day says **Intraday (not finalized)** | No run happened while the market was closed after that day, so its final report was never written. Keep the computer on for the morning run (or run the agent after the close). Later days aren't affected. |
| The page opens on the wrong tab | The address ends in `#/previous`. Click **Today**, or remove everything from `#` onwards. |
| Tests fail with `ModuleNotFoundError: ask` | Create `ask.py` in the project folder (Step 2). |

---

## 13. Next steps

1. **Charts and filters:** `/api/tickers/{ticker}/history` already returns each ticker's figures across days. A chart under each flagged ticker, or a "days this ticker was flagged" filter on the Previous days tab, are natural next additions.
2. **Search and RAG:** once you have a few months of reports, replace the report selection in `ask.py` with search. Start with keyword search, then add vector search (the RAG plan we discussed).
3. **Login:** add one before sharing beyond your computer (section 11).
4. **Hosting:** run the API and the built frontend on a small server, move the database to PostgreSQL, and switch the scheduled runs from your laptop to the server.

---

## Appendix: full source code

### run_brief.py

Replaces the version in the database guide.

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

### ask.py

```python
"""Answer questions about saved reports with Claude.

No RAG yet: it picks the relevant reports straight from the database (the 10
most recent, plus the figures and flagged-day reports for any ticker named in
the question) and asks Claude to answer from those alone, citing report dates.
"""

import re
from contextlib import closing

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import reports_db

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05).
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included
FLAGGED_REPORTS_PER_TICKER = 10  # extra reports for each ticker named in the question
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


def build_context(conn, question: str) -> tuple[str, list[str]]:
    """The material Claude answers from, and the report dates it includes."""
    days = [r["session_date"] for r in reports_db.list_reports(conn, limit=RECENT_REPORTS)]
    tickers = mentioned_tickers(conn, question)
    for ticker in tickers:
        days += [row[0] for row in conn.execute(
            """SELECT session_date FROM report_tickers WHERE ticker = ? AND category = 'flagged'
               ORDER BY session_date DESC LIMIT ?""", (ticker, FLAGGED_REPORTS_PER_TICKER))]

    parts, size = [], 0
    for ticker in tickers:
        lines = [f"## Figures for {ticker} (newest first)",
                 "date | status | category | return % | z-score | volume vs normal"]
        lines += [f"{h['session_date']} | {h['status']} | {h['category']} | {h['return_1d_pct']} | "
                  f"{h['return_zscore']} | {h['volume_vs_avg']}"
                  for h in reports_db.ticker_history(conn, ticker, limit=60)]
        parts.append("\n".join(lines))
        size += len(parts[-1])

    used = []
    for day in sorted(set(days), reverse=True):
        report = reports_db.get_report(conn, day)
        block = f"## Report {day} ({report['status']}, as of {report['as_of']})\n\n{report['body_md']}"
        if size + len(block) > MAX_CONTEXT_CHARS:
            break
        parts.append(block)
        used.append(day)
        size += len(block)
    return "\n\n---\n\n".join(parts), used


async def answer(question: str, emit) -> dict:
    """Answer one question. emit(event) receives {"type": "delta", "text": ...} as the
    answer is written, then {"type": "done", ...}. Returns the done event."""
    question = question.strip()
    if not question or len(question) > MAX_QUESTION_CHARS:
        raise ValueError(f"questions must be 1 to {MAX_QUESTION_CHARS} characters")
    with closing(reports_db.connect(readonly=True)) as conn:
        context, used = build_context(conn, question)
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

### api.py

Replaces the version in the database guide.

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
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes is a run, through run_brief.py's normal storage rules.
If frontend/dist exists (after `npm run build`), the app is served at /.
"""

import asyncio
import json
import os
import re
import time
from contextlib import asynccontextmanager, closing
from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import ask
import reports_db
import run_brief

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "300"))  # between on-demand runs
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


def _latest_change() -> dict | None:
    """The most recently saved report: changes whenever any run saves (scheduled or on demand)."""
    with _db() as conn:
        row = conn.execute("""SELECT session_date, status, revision, updated_at FROM reports
                              ORDER BY updated_at DESC, session_date DESC LIMIT 1""").fetchone()
    return dict(row) if row else None


async def watch_reports() -> None:
    """Checks the database every few seconds and announces new or updated reports."""
    last = await asyncio.to_thread(_latest_change)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current = await asyncio.to_thread(_latest_change)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if current and current != last:
            last = current
            hub.publish({"type": "report_saved", **current})


async def events(request):
    """Server-Sent Events stream. The browser's EventSource reconnects on its own."""
    queue = hub.subscribe()
    hello = {"type": "hello", "run": runs.snapshot(), "latest": await asyncio.to_thread(_latest_change)}

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
    yield
    watcher.cancel()


def create_app(frontend_dist: Path = FRONTEND_DIST) -> Starlette:
    routes = [
        Route("/api/health", health),
        Route("/api/reports", list_reports),
        Route("/api/reports/latest", latest_report),  # must come before the {session_date} route
        Route("/api/reports/{session_date}", get_report),
        Route("/api/tickers/{ticker}/history", ticker_history),
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

### tests/test_frontend_api.py

```python
"""Offline tests for the frontend's backend: live updates, run-now, and questions.

Run from the project folder:
    pytest -v tests/test_frontend_api.py
"""

import asyncio
import json
import sys
import time
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import (  # noqa: E402
    AssistantMessage, ResultMessage, StreamEvent, ToolResultBlock, ToolUseBlock, UserMessage,
)
from starlette.testclient import TestClient  # noqa: E402

OPEN = {"status": "in_progress", "as_of": "2026-11-06 12:30 ET"}
JSON = {"Content-Type": "application/json"}


def scan(session=OPEN, flagged=("NVDA",), quiet=("AAPL",)):
    return {"session": session,
            "flagged": [{"ticker": t, "last_price": 150.0, "return_1d_pct": 6.5, "return_zscore": 4.2,
                         "volume_vs_avg": 2.8} for t in flagged],
            "quiet": [{"ticker": t, "return_1d_pct": 0.3} for t in quiet], "errors": []}


def save(day="2026-11-06", status="intraday", as_of="2026-11-06 12:30 ET", body="brief", flagged=("NVDA",)):
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=day, status=status, title=f"Report {day}",
                                      body_md=f"# Report {day}\n\n{body}", as_of=as_of, scan=scan(flagged=flagged))


def result(text="done", is_error=False, cost=0.01):
    return ResultMessage(subtype="error_during_execution" if is_error else "success", duration_ms=1,
                         duration_api_ms=1, is_error=is_error, num_turns=1, session_id="s",
                         total_cost_usd=cost, result=text)


def wait_until(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


@pytest.fixture(autouse=True)
def fresh_state(tmp_path, monkeypatch):
    """A temporary database, and fresh live-update and run state, for every test."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "runs", api.RunManager())
    reports_db.connect().close()


def fake_run_once(delay=0.0, fail=None):
    """Stands in for run_brief.run_once: reports progress, then saves a report."""
    async def run_once(emit):
        emit({"type": "started", "session_date": "2026-11-06", "status": "intraday"})
        emit({"type": "tool_call", "tool": "mcp__market__flag_events", "input": {}})
        await asyncio.sleep(delay)
        if fail:
            raise RuntimeError(fail)
        outcome = save()
        event = {"type": "saved", "outcome": outcome, "session_date": "2026-11-06", "status": "intraday",
                 "turns": 3, "cost_usd": 0.04}
        emit(event)
        return event
    return run_once


# ---------------------------------------------------------------------------
# run_brief.run_once progress events
# ---------------------------------------------------------------------------

def test_run_once_reports_progress_events(monkeypatch):
    messages = [
        AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})], model="m"),
        UserMessage(content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": json.dumps(scan())}])]),
        AssistantMessage(content=[ToolUseBlock(id="t2", name="mcp__market__get_news", input={"ticker": "NVDA"})],
                         model="m"),
        result("# Intraday update: 2026-11-06 12:30 ET\n\ntext"),
    ]

    async def fake_query(*, prompt, options):
        for m in messages:
            yield m

    monkeypatch.setattr(run_brief, "market_session", lambda: OPEN)
    monkeypatch.setattr(run_brief, "query", fake_query)
    events = []

    final = asyncio.run(run_brief.run_once(events.append))

    assert [e["type"] for e in events] == ["started", "tool_call", "tool_call", "saved"]
    assert events[1]["tool"] == "mcp__market__flag_events"
    assert final == events[-1] and final["outcome"] == "created"


# ---------------------------------------------------------------------------
# Run now
# ---------------------------------------------------------------------------

def test_run_now_writes_a_report_and_shows_progress(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once())
    with TestClient(api.app) as client:
        response = client.post("/api/runs", json={})
        assert response.status_code == 202
        assert response.json()["run"]["state"] == "running"

        run = wait_until(lambda: (r := client.get("/api/runs/current").json()["run"])["state"] != "running" and r)

    assert run["state"] == "finished"
    assert [e["type"] for e in run["log"]] == ["started", "tool_call", "saved"]
    assert run["result"]["outcome"] == "created"
    assert run["started_at"] and run["finished_at"]


def test_run_now_allows_one_run_at_a_time_then_a_cooldown(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once(delay=0.5))
    with TestClient(api.app) as client:
        assert client.post("/api/runs", json={}).status_code == 202
        busy = client.post("/api/runs", json={})
        assert busy.status_code == 409 and "already being written" in busy.json()["error"]

        wait_until(lambda: client.get("/api/runs/current").json()["run"]["state"] == "finished")
        too_soon = client.post("/api/runs", json={})
        assert too_soon.status_code == 429 and "Please wait" in too_soon.json()["error"]

        monkeypatch.setattr(api, "RUN_COOLDOWN_SECONDS", 0)
        assert client.post("/api/runs", json={}).status_code == 202


def test_run_now_failure_is_reported(monkeypatch):
    monkeypatch.setattr(run_brief, "run_once", fake_run_once(fail="Run failed: error_max_budget_usd"))
    with TestClient(api.app) as client:
        client.post("/api/runs", json={})
        run = wait_until(lambda: (r := client.get("/api/runs/current").json()["run"])["state"] != "running" and r)

    assert run["state"] == "failed"
    assert run["error"] == "Run failed: error_max_budget_usd"


@pytest.mark.parametrize("path", ["/api/runs", "/api/ask"])
def test_other_websites_cannot_trigger_runs_or_questions(path):
    client = TestClient(api.app)
    evil = client.post(path, json={"question": "hi"}, headers={"Origin": "https://evil.example"})
    assert evil.status_code == 403
    form = client.post(path, content="question=hi", headers={"Content-Type": "application/x-www-form-urlencoded"})
    assert form.status_code == 415  # plain form posts (which skip browser safety checks) are refused


def test_frontend_origin_can_post():
    client = TestClient(api.app)
    response = client.post("/api/ask", json={"question": "anything new?"}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


# ---------------------------------------------------------------------------
# Live updates
# ---------------------------------------------------------------------------

def test_events_stream_sends_hello_then_live_events():
    async def scenario():
        response = await api.events(None)
        stream = response.body_iterator
        hello = await anext(stream)
        api.hub.publish({"type": "run_event", "event": {"type": "tool_call", "tool": "x", "input": {}}})
        live = await anext(stream)
        await stream.aclose()
        return hello, live

    hello, live = asyncio.run(scenario())

    assert hello.startswith("retry: 3000\ndata: ")
    assert json.loads(hello.split("data: ", 1)[1])["type"] == "hello"
    assert json.loads(live.removeprefix("data: "))["event"]["tool"] == "x"
    assert api.hub.subscribers == set()  # a closed browser tab is cleaned up


def test_watcher_announces_reports_saved_by_any_run(monkeypatch):
    """Covers scheduled runs too: they're separate programs, so the API spots their saves in the database."""
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.1)
        save(as_of="2026-11-06 11:00 ET")
        first = await asyncio.wait_for(queue.get(), 2)
        save(as_of="2026-11-06 12:30 ET")
        second = await asyncio.wait_for(queue.get(), 2)
        watcher.cancel()
        return first, second

    first, second = asyncio.run(scenario())

    assert first == {"type": "report_saved", "session_date": "2026-11-06", "status": "intraday",
                     "revision": 1, "updated_at": first["updated_at"]}
    assert second["revision"] == 2


# ---------------------------------------------------------------------------
# Questions
# ---------------------------------------------------------------------------

def fake_claude(monkeypatch, *messages):
    """Replace Claude in ask.py. Returns the list of prompts it was sent."""
    prompts = []

    async def fake_query(*, prompt, options):
        prompts.append(prompt)
        for m in messages:
            yield m

    monkeypatch.setattr(ask, "query", fake_query)
    return prompts


def delta(text):
    return StreamEvent(uuid="u", session_id="s",
                       event={"type": "content_block_delta", "index": 0, "delta": {"type": "text_delta", "text": text}})


def ask_lines(question):
    response = TestClient(api.app).post("/api/ask", json={"question": question})
    assert response.status_code == 200
    return [json.loads(line) for line in response.text.splitlines()]


def test_ask_streams_the_answer(monkeypatch):
    save(day="2026-11-05", status="final", as_of="2026-11-05", body="NVDA jumped on earnings.")
    prompts = fake_claude(monkeypatch, delta("NVDA was flagged "), delta("on earnings (2026-11-05)."),
                          result("NVDA was flagged on earnings (2026-11-05).", cost=0.012))

    lines = ask_lines("why was nvda flagged?")

    assert [line["type"] for line in lines] == ["delta", "delta", "done"]
    assert "".join(line["text"] for line in lines[:2]) == lines[-1]["answer"]
    assert lines[-1]["reports_used"] == ["2026-11-05"]
    assert lines[-1]["cost_usd"] == 0.012
    assert "## Figures for NVDA" in prompts[0]  # ticker spotted, whatever the letter case
    assert "NVDA jumped on earnings." in prompts[0]


def test_ask_includes_older_reports_for_the_ticker_asked_about():
    save(day="2026-10-01", status="final", as_of="2026-10-01", flagged=("TSLA",))  # old, outside the recent 10
    for day in range(10, 22):
        save(day=f"2026-10-{day}", status="final", as_of=f"2026-10-{day}", flagged=("NVDA",))

    with closing(reports_db.connect()) as conn:
        _, used_general = ask.build_context(conn, "what happened this week?")
        _, used_tsla = ask.build_context(conn, "What about TSLA?")

    assert len(used_general) == 10 and "2026-10-01" not in used_general
    assert "2026-10-01" in used_tsla


def test_ask_context_stays_within_its_size_limit(monkeypatch):
    for day in range(10, 20):
        save(day=f"2026-10-{day}", status="final", as_of=f"2026-10-{day}", body="x" * 5000)
    monkeypatch.setattr(ask, "MAX_CONTEXT_CHARS", 12_000)

    with closing(reports_db.connect()) as conn:
        context, used = ask.build_context(conn, "summary?")

    assert len(context) <= 12_000
    assert used == ["2026-10-19", "2026-10-18"]  # newest first, until the limit


def test_ask_with_no_reports_does_not_call_claude(monkeypatch):
    prompts = fake_claude(monkeypatch, result("should not happen"))

    lines = ask_lines("anything?")

    assert lines[-1]["type"] == "done" and "no saved reports" in lines[-1]["answer"]
    assert prompts == []


def test_ask_failure_is_streamed_as_an_error(monkeypatch):
    save()
    fake_claude(monkeypatch, result(is_error=True))

    lines = ask_lines("anything?")

    assert lines == [{"type": "error", "error": "Claude couldn't answer: error_during_execution"}]


@pytest.mark.parametrize("body", [{"question": ""}, {"question": "x" * 501}, {"wrong": "key"}, ["not", "an", "object"]])
def test_ask_rejects_bad_questions(body):
    assert TestClient(api.app).post("/api/ask", json=body).status_code == 400


def test_ask_rejects_broken_json():
    assert TestClient(api.app).post("/api/ask", content="{not json", headers=JSON).status_code == 400


# ---------------------------------------------------------------------------
# Serving the built frontend
# ---------------------------------------------------------------------------

def test_built_frontend_is_served_alongside_the_api(tmp_path):
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<div id='root'></div>")

    client = TestClient(api.create_app(frontend_dist=dist))

    assert "id='root'" in client.get("/").text
    assert client.get("/api/health").json()["status"] == "ok"
```

### frontend/vite.config.js

```js
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During development, the app runs on port 5173 and Vite forwards every /api
// request (including the live-updates stream) to the Python API on port 8000.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
```

### frontend/index.html

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" href="data:," />
    <title>Market Analyst</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
```

### frontend/src/main.jsx

```jsx
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.jsx'
import './styles.css'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
```

### frontend/src/App.jsx

```jsx
import { useCallback, useEffect, useState } from 'react'
import { getCurrentRun, getLatestReport } from './api'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'

export default function App() {
  const route = useRoute()
  const [latest, setLatest] = useState(null)
  const [latestError, setLatestError] = useState(null)
  const [run, setRun] = useState(null)
  const [lastSaved, setLastSaved] = useState(null) // tells the previous-days views to refresh

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
      loadLatest()
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

  const tabLink = (tab, href, label) => (
    <a href={href} className={`tab ${route.tab === tab ? 'active' : ''}`} aria-current={route.tab === tab ? 'page' : undefined}>
      {label}
    </a>
  )

  return (
    <div className="app">
      <header className="topbar">
        <h1>Market Analyst</h1>
        <nav className="tabs" aria-label="Sections">
          {tabLink('today', routes.today, 'Today')}
          {tabLink('previous', routes.previous(), 'Previous days')}
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
            <RunPanel run={run} onStarted={onRunStarted} />
            <AskPanel />
          </aside>
        </main>

        <PreviousDaysPreview latestDate={latest?.session_date} lastSaved={lastSaved} />
      </div>

      <div hidden={route.tab !== 'previous'}>
        <PreviousDaysTab latestDate={latest?.session_date} lastSaved={lastSaved} selectedDate={route.date} />
      </div>
    </div>
  )
}
```

### frontend/src/api.js

```js
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

### frontend/src/useLiveEvents.js

```js
import { useEffect, useRef, useState } from 'react'

// Keeps one live connection to /api/events open and calls onEvent for every update.
// If the server restarts, the browser reconnects by itself (and gets a fresh "hello").
export function useLiveEvents(onEvent) {
  const [connected, setConnected] = useState(false)
  const handler = useRef(onEvent)

  useEffect(() => {
    handler.current = onEvent
  })

  useEffect(() => {
    const source = new EventSource('/api/events')
    source.onopen = () => setConnected(true)
    source.onerror = () => setConnected(false)
    source.onmessage = (message) => handler.current(JSON.parse(message.data))
    return () => source.close()
  }, [])

  return connected
}
```

### frontend/src/useRoute.js

```js
import { useEffect, useState } from 'react'

// A tiny router using the part of the address after #:
//   #/                      Today
//   #/previous              Previous days (newest day shown)
//   #/previous/2026-11-05   Previous days, with that day open
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date] = hash.replace(/^#/, '').split('/')
  if (tab !== 'previous') return { tab: 'today', date: null }
  return { tab: 'previous', date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
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

### frontend/src/format.js

```js
// Display helpers

export const formatDate = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, {
    weekday: 'short', month: 'short', day: 'numeric', year: 'numeric',
  })

export const formatMonth = (day) =>
  new Date(`${day}T12:00:00`).toLocaleDateString(undefined, { month: 'long', year: 'numeric' })

export const formatTime = (utc) =>
  utc ? new Date(utc).toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) : ''

export const number = (value, digits) => (value == null ? '—' : value.toFixed(digits))

export const percent = (value) => (value == null ? '—' : `${value > 0 ? '+' : ''}${value.toFixed(2)}%`)

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
```

### frontend/src/components/StatusBadge.jsx

```jsx
// current: true for the latest report, which can still be updated during the day.
// An older day that's still "intraday" was never finalized (no run happened while
// the market was closed before the next session), so it won't change any more.
export default function StatusBadge({ status, current = false }) {
  if (status === 'final') return <span className="badge final">Final</span>
  return current ? (
    <span className="badge live">Intraday · updating</span>
  ) : (
    <span className="badge live" title="No final report was saved for this day">Intraday (not finalized)</span>
  )
}
```

### frontend/src/components/Markdown.jsx

```jsx
import { useMemo } from 'react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'

// Links inside reports open in a new tab
DOMPurify.addHook('afterSanitizeAttributes', (node) => {
  if (node.tagName === 'A') {
    node.setAttribute('target', '_blank')
    node.setAttribute('rel', 'noopener noreferrer')
  }
})

// Renders markdown from the agent. Reports quote news headlines from the web,
// so DOMPurify strips anything that could run code (and images, which reports
// never need) before it reaches the page.
export default function Markdown({ text }) {
  const html = useMemo(
    () => DOMPurify.sanitize(marked.parse(text || ''), { FORBID_TAGS: ['img', 'style'], FORBID_ATTR: ['style'] }),
    [text],
  )
  return <div className="markdown" dangerouslySetInnerHTML={{ __html: html }} />
}
```

### frontend/src/components/TickerTable.jsx

```jsx
import { number, percent } from '../format'

export default function TickerTable({ tickers }) {
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
          </tr>
        </thead>
        <tbody>
          {tickers.map((t) => (
            <tr key={t.ticker} className={t.category}>
              <td className="ticker">{t.ticker}</td>
              <td>{t.category === 'error' ? <span title={t.error}>data issue</span> : t.category}</td>
              <td className="num">{number(t.price, 2)}</td>
              <td className={`num ${t.return_1d_pct > 0 ? 'up' : t.return_1d_pct < 0 ? 'down' : ''}`}>
                {percent(t.return_1d_pct)}
              </td>
              <td className="num">{number(t.return_zscore, 1)}</td>
              <td className="num">{t.volume_vs_avg == null ? '—' : `${t.volume_vs_avg}×`}</td>
            </tr>
          ))}
        </tbody>
      </table>
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

// current: true for the latest report (see StatusBadge)
export default function ReportView({ report, current = false }) {
  return (
    <article className="report">
      <div className="report-head">
        <StatusBadge status={report.status} current={current} />
        <span className="muted small">
          As of {report.as_of} · saved {formatTime(report.updated_at)}
          {report.status === 'intraday' && current && ` · update ${report.revision}`}
        </span>
      </div>

      <TickerTable tickers={report.tickers} />
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

### frontend/src/components/RunPanel.jsx

```jsx
import { useState } from 'react'
import { startRun } from '../api'
import { formatTime } from '../format'

const STEP_NAMES = {
  flag_events: () => 'Scanning the watchlist',
  get_news: (input) => `Reading news for ${input.ticker}`,
  compute_moves: (input) => `Checking ${input.ticker} in detail`,
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

### frontend/src/components/AskPanel.jsx

```jsx
import { useState } from 'react'
import { askQuestion } from '../api'
import Markdown from './Markdown'

const EXAMPLES = ['What moved the most this week?', 'Why was NVDA flagged?', 'Which tickers keep getting flagged?']

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
          <span className="muted small">Answers come only from saved reports.</span>
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

### frontend/src/components/PreviousDaysPreview.jsx

```jsx
import { useEffect, useState } from 'react'
import { getReport, listReports } from '../api'
import { formatDate, percent } from '../format'
import { routes } from '../useRoute'
import StatusBadge from './StatusBadge'

const PREVIEW_DAYS = 3
const TICKERS_PER_CARD = 4

// The last few days before the latest report, as cards on the Today tab.
// Each card opens that day on the Previous days tab, which lists every day.
export default function PreviousDaysPreview({ latestDate, lastSaved }) {
  const [reports, setReports] = useState([])
  const [error, setError] = useState(null)

  useEffect(() => {
    if (!latestDate) return
    listReports({ before: latestDate, limit: PREVIEW_DAYS })
      .then((days) => Promise.all(days.map((d) => getReport(d.session_date))))
      .then((full) => {
        setReports(full)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [latestDate, lastSaved])

  return (
    <section className="panel previous" aria-label="Recent days">
      <div className="section-head">
        <h2>Previous days</h2>
        <a className="link" href={routes.previous()}>See all previous days →</a>
      </div>
      {error && <p className="error">{error}</p>}
      {reports.length === 0 ? (
        <p className="muted">No earlier reports yet.</p>
      ) : (
        <div className="preview-cards">
          {reports.map((report) => {
            const flagged = report.tickers.filter((t) => t.category === 'flagged')
            return (
              <a key={report.session_date} className="preview-card" href={routes.previous(report.session_date)}>
                <span className="preview-top">
                  <span className="day-date">{formatDate(report.session_date)}</span>
                  <StatusBadge status={report.status} />
                </span>
                <span className="preview-flagged">
                  {flagged.length === 0 && <span className="muted small">Nothing flagged</span>}
                  {flagged.slice(0, TICKERS_PER_CARD).map((t) => (
                    <span key={t.ticker} className={`tick ${t.return_1d_pct > 0 ? 'up' : t.return_1d_pct < 0 ? 'down' : ''}`}>
                      {t.ticker} {percent(t.return_1d_pct)}
                    </span>
                  ))}
                  {flagged.length > TICKERS_PER_CARD && (
                    <span className="muted small">+{flagged.length - TICKERS_PER_CARD} more</span>
                  )}
                </span>
              </a>
            )
          })}
        </div>
      )}
    </section>
  )
}
```

### frontend/src/components/PreviousDaysTab.jsx

```jsx
import { useEffect, useRef, useState } from 'react'
import { getReport, listReports } from '../api'
import { formatDate, formatMonth } from '../format'
import { routes } from '../useRoute'
import ReportView from './ReportView'
import StatusBadge from './StatusBadge'

const PAGE_SIZE = 30

// Every report before the latest one, grouped by month, with the chosen day beside it.
export default function PreviousDaysTab({ latestDate, lastSaved, selectedDate }) {
  const [days, setDays] = useState([])
  const [hasMore, setHasMore] = useState(false)
  const [report, setReport] = useState(null)
  const [error, setError] = useState(null)
  const loaded = useRef(PAGE_SIZE) // how many days the list shows, kept when it refreshes
  const reportRef = useRef(null)

  const shownDate = selectedDate || days[0]?.session_date // the newest day, unless one is chosen
  const refreshShown = lastSaved?.session_date === shownDate ? lastSaved : null

  // The list: refreshed when the latest day changes or any report is saved
  useEffect(() => {
    if (!latestDate) return
    const limit = Math.min(loaded.current, 365)
    listReports({ before: latestDate, limit })
      .then((reports) => {
        setDays(reports)
        setHasMore(reports.length === limit)
      })
      .catch((e) => setError(e.message))
  }, [latestDate, lastSaved])

  // The open day: reloaded when you pick another day, or when that day is saved again
  useEffect(() => {
    if (!shownDate) return
    getReport(shownDate)
      .then((r) => {
        setReport(r)
        setError(null)
      })
      .catch((e) => setError(e.message))
  }, [shownDate, refreshShown])

  // On a phone the report sits under the list, so bring it into view when a day is picked.
  // (setTimeout lets App's scroll-to-top on tab change happen first.)
  useEffect(() => {
    if (!selectedDate || window.innerWidth >= 760) return
    const timer = setTimeout(() => reportRef.current?.scrollIntoView({ behavior: 'smooth' }), 0)
    return () => clearTimeout(timer)
  }, [selectedDate])

  const loadOlder = () =>
    listReports({ before: days[days.length - 1].session_date, limit: PAGE_SIZE })
      .then((reports) => {
        loaded.current += reports.length
        setDays((current) => [...current, ...reports])
        setHasMore(reports.length === PAGE_SIZE)
      })
      .catch((e) => setError(e.message))

  const months = []
  for (const day of days) {
    const label = formatMonth(day.session_date)
    if (months.at(-1)?.label !== label) months.push({ label, days: [] })
    months.at(-1).days.push(day)
  }

  return (
    <section className="panel" aria-label="All previous days">
      <div className="section-head">
        <h2>All previous days</h2>
        <span className="muted small">
          {days.length}
          {hasMore ? '+' : ''} day{days.length === 1 ? '' : 's'}
        </span>
      </div>
      {error && <p className="error">{error}</p>}

      {days.length === 0 && !selectedDate ? (
        <p className="muted">No earlier reports yet.</p>
      ) : (
        <div className="previous-grid">
          <nav className="day-list" aria-label="Days">
            {months.map((month) => (
              <div key={month.label}>
                <h3 className="month">{month.label}</h3>
                <ul>
                  {month.days.map((d) => (
                    <li key={d.session_date}>
                      <a
                        className={`day ${d.session_date === shownDate ? 'active' : ''}`}
                        href={routes.previous(d.session_date)}
                        aria-current={d.session_date === shownDate ? 'true' : undefined}
                      >
                        <span className="day-date">{formatDate(d.session_date)}</span>
                        <span className="day-meta">
                          <StatusBadge status={d.status} /> {d.flagged_count} flagged
                        </span>
                      </a>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
            {hasMore && (
              <button className="link" onClick={loadOlder}>Load older days</button>
            )}
          </nav>
          <div className="day-report" ref={reportRef}>
            {report ? <ReportView report={report} /> : <p className="muted">Loading…</p>}
          </div>
        </div>
      )}
    </section>
  )
}
```
