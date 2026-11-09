# Market Analyst Agent: A Live Demo on GitHub Pages

This guide gives your GitHub page a **"Try the live demo"** link. Visitors click it and your real app opens in their browser, with nothing to install and no account to make. They can use it as you do: read today's report, page through two months of history, open charts, search, ask questions, run an update, check the calendar, and add or star stocks.

| | |
|---|---|
| **What visitors see** | Your real React app, over the test environment's two months of sample data, with a banner saying it's simulated |
| **What runs it** | Nothing but GitHub Pages, which only hosts files. The app's requests are answered inside the browser by a small script, `demo-shim.js` |
| **Cost** | Free. There's no server, no Claude and no market data, so there are no keys to leak and nothing a visitor can run up |
| **Your program** | Untouched. The demo lives in its own folder next to `market-agent/` and `market-agent-testenv/`, and only reads them |

This builds on `market-agent-test-enviro.md`, which makes the sample data, and `market-agent-stocks.md`.

---

## Contents

1. [What it looks like](#1-what-it-looks-like)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Create the demo folder](#4-step-1-create-the-demo-folder)
5. [Step 2: Build the site](#5-step-2-build-the-site)
6. [Step 3: Try it on your computer](#6-step-3-try-it-on-your-computer)
7. [Step 4: Put the project on GitHub](#7-step-4-put-the-project-on-github)
8. [Step 5: Publish the demo](#8-step-5-publish-the-demo)
9. [Step 6: Turn on GitHub Pages](#9-step-6-turn-on-github-pages)
10. [Step 7: Link it from your README](#10-step-7-link-it-from-your-readme)
11. [Updating the demo](#11-updating-the-demo)
12. [What's real and what's simulated](#12-whats-real-and-whats-simulated)
13. [Test it](#13-test-it)
14. [Settings](#14-settings)
15. [Costs](#15-costs)
16. [Security and privacy](#16-security-and-privacy)
17. [Troubleshooting](#17-troubleshooting)
18. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it looks like

Visitors land on the Today tab, under a banner (screenshot: `demo-preview.png`):

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Live demo with sample data. Prices, news, runs and answers are simulated, and no AI is       │
│ called. Changes stay in this tab until you reload. See the code on GitHub                    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
 Market Analyst    Today   Previous days   Calendar   Stocks                              ● Live

 LATEST REPORT                                                  REQUEST A FRESH REPORT
 Intraday · updating   As of 2026-11-06 12:30 ET · saved 12:31 PM   [ Run update now ]
 AAPL  quiet    76.64   -0.13%                                  COMING UP
 MSFT  flagged 323.91   +4.96%  3.0  1.68×  +5.09 pts vs XLK    Mon, Nov 9   Microsoft Court hearing…
 NVDA  quiet    81.88   +0.31%                                  ASK ABOUT YOUR REPORTS
 Showing your main stocks. 2 more in this report: see all tracked stocks
```

The sample's "today" is the latest trading day when you built the demo, frozen at 12:33pm New York time. Everything else works as in your app:

- **Run update now** plays the next recorded update. The report moves on 15 minutes (12:45, 13:00, 13:15, 13:30), with the same progress steps and Discord line as a real run. After the fourth, it says that was the last one.
- **Ask** streams an answer built from the sample data, the same way the test environment's offline answers are.
- **Search**, **charts**, the **calendar** (and its **Update now**) and the **Stocks tab** all work. A visitor can find Costco, track it as a main stock, and see it get figures on the next run.
- **A reload starts the demo again**, so every visitor gets the same fresh start.

---

## 2. How it works

```
python demo.py build
  1. builds your React app into market-agent-demo/site/  (npm run build, with relative links)
  2. makes a sample with the test environment (in a scratch folder), then records:
       every answer the app asks for ─────────▶ site/demo-data/0/…
       4 "Run update now" runs, and what each changed ▶ site/demo-data/1/ … 4/
       a calendar "Update now", and the stocks a visitor could add ▶ site/demo-data/manifest.json
  3. adds demo-config.js and demo-shim.js to the page, before the app

A visitor's browser
  index.html ─▶ demo-shim.js ─▶ your app (unchanged)
                     │  fetch('/api/…')        answered from demo-data/, as your API would
                     │  EventSource('/api/events')  live updates, replayed from the recordings
                     │  the clock               set to the sample's day
                     └─ the banner
```

- **Your app's code isn't changed.** The shim answers the same requests, with the same shapes and the same error messages, as `api.py`. If the app works against the test environment, it works in the demo.
- **The data is real output from your program.** The exporter runs your real `api.py`, `run_brief.py`, `events.py`, `watchlist.py` and `search_index.py` over the test environment's simulated market, and saves what they answer. Nothing in the demo is hand-made.
- **Runs are recordings.** Each recorded run keeps its progress events and timing, and only the files that changed (the latest report, alerts, the search passages and so on). Playing run 2 serves run 2's files.
- **What's worked out in the browser:** paging through days, the calendar's date ranges, search, Ask's answers and the Stocks tab's rules. These are small ports of your Python code. For example, search uses a simple keyword ranking plus the test environment's topic stand-in for meaning, and the Stocks tab gives the same messages as `watchlist.py`.
- **The clock.** The shim sets the page's clock to the sample's day, so "today" on the calendar, the Coming up card and every time shown belong to the sample. Playing a run moves the clock to that run's time.
- **The sample is made in a scratch folder** (`market-agent-demo/.work/`, deleted afterwards). Your program's folder, your real reports and the test environment's own sample are never opened for writing. A test checks this.

---

## 3. Before you start

- [ ] The test environment works: in `market-agent-testenv/`, `pytest -v` shows `29 passed`.
- [ ] You've run `npm install` in `market-agent/frontend` (frontend guide).
- [ ] Git is installed (`git --version`), and you have a GitHub account.
- [ ] **A small fix from the stocks guide.** If you built the Stocks tab before this guide, add this line to `frontend/src/styles.css`, after `.table-note { margin: 6px 0 0; }`. It makes the Today tab's "see all tracked stocks" link readable in dark mode:

```css
.table-note a { color: var(--accent); }
```

  (`market-agent-stocks.md`'s appendix now includes it.)

No new Python or npm packages are needed. Use your program's virtual environment, as the test environment does.

---

## 4. Step 1: Create the demo folder

Next to `market-agent/` and `market-agent-testenv/`:

```bash
mkdir market-agent-demo
cd market-agent-demo
```

Add these three files from the [appendix](#appendix-full-source-code):

| File | What it does |
|---|---|
| [`demo.py`](#demopy) | `build`, `serve`, `check` and `publish` |
| [`demo-shim.js`](#demo-shimjs) | The in-browser stand-in for your API |
| [`test_demo.py`](#test_demopy) | Checks for the export, the safety checks and publishing |

Your folders now look like this:

```
projects/
├── market-agent/            your program (only read)
├── market-agent-testenv/    the test environment (only read: the demo uses its sample)
└── market-agent-demo/       the live demo
    ├── demo.py   demo-shim.js   test_demo.py
    ├── site/                created by build: exactly what gets published
    └── .work/               scratch sample databases while building (deleted afterwards)
```

---

## 5. Step 2: Build the site

With the virtual environment active, from `market-agent-demo/`:

```bash
source ../market-agent/.venv/bin/activate          # macOS / Linux
..\market-agent\.venv\Scripts\Activate.ps1          # Windows PowerShell

python demo.py build
```

It builds the app first (Vite's usual output), then makes and records the sample, which takes under a minute. Then it prints:

```
Built the demo in .../market-agent-demo/site
  sample: 44 days of reports, from 2026-09-08 to 2026-11-06, with 4 recorded runs
  size: 2.9 MB
Try it with: python demo.py serve
```

**Which stocks?** The demo uses the stocks in your `watchlist.txt` (only read), with your starred stocks as the main ones (or the first three, if none are starred). To show others, use `python demo.py build --tickers AAPL,MSFT,NVDA,AMZN,JPM`; the first three are then the main ones.

**The banner's GitHub link** comes from your repository's address, once the project is on GitHub (step 4). Build again after that, or give it yourself: `--repo-url https://github.com/USERNAME/REPOSITORY`.

---

## 6. Step 3: Try it on your computer

```bash
python demo.py serve
```

Open **http://localhost:8200**. These are the exact files GitHub Pages will serve, so what works here works there. Check:

- [ ] The banner is at the top, and the dot says **Live**
- [ ] **Run update now** shows its steps, then the report moves from 12:30 to 12:45 ET and "Discord: sent flag alert" appears. Pressing again straight away explains the 15-second wait
- [ ] **Ask** "Why was NVDA flagged?": the answer streams in, listing NVDA's flagged days
- [ ] **Previous days:** search "earnings", and the earnings days come up; a day opens below
- [ ] **Stocks:** search "costco", **Track as main**, and its next earnings date appears. After the next **Run update now**, COST has figures and is on the Today tab
- [ ] **Calendar:** today is circled, and **Update now** shows its progress
- [ ] Reload: everything is back to 12:30, with your original stocks
- [ ] On a phone-sized window, nothing scrolls sideways

Press Ctrl+C to stop.

---

## 7. Step 4: Put the project on GitHub

**Already on GitHub?** Skip to step 5. The demo publishes to a branch of its own, so it works whichever folders your repository holds.

**Not yet?** Put all three folders in one public repository, so visitors can see the program, the test environment and the demo.

1. **Keep keys and private data out.** In `projects/` (the folder holding all three), create `.gitignore`:

```
# Keys and private data: never commit these
.env
*.env
**/reports.db*
**/search.db*

# Installed packages, caches and builds
**/.venv/
**/node_modules/
**/__pycache__/
**/.pytest_cache/
market-agent/frontend/dist/
market-agent-testenv/data/
market-agent-testenv/frontend-dist/
market-agent-demo/site/
market-agent-demo/.work/
```

   Your keys are in environment variables (the earlier guides never put them in files), so nothing else is secret. Your `watchlist.txt` is included; remove it from the repository if you'd rather not share your list.

2. **Create the repository on GitHub:** github.com → **New repository** → a name such as `market-agent` → **Public** → don't add a README, `.gitignore` or license (you have your own) → **Create repository**.

3. **Commit and check before pushing.** From `projects/`:

```bash
git init
git add .
git status                                   # no reports.db, .env, node_modules or .venv in the list
git grep -nE "sk-ant-|discord(app)?\.com/api/webhooks" || echo "No keys found"
git commit -m "Market analyst agent"
git branch -M main
git remote add origin https://github.com/USERNAME/REPOSITORY.git
git push -u origin main
```

   If `git grep` prints a line, remove that key from the file (and change the key, to be safe) before committing.

---

## 8. Step 5: Publish the demo

```bash
python demo.py build      # again if you've just set up the repository, for the banner's link
python demo.py check
python demo.py publish
```

- **`check`** looks through every file in `site/` for anything that looks like an Anthropic key, a Discord webhook or a GitHub token, and for paths on your computer. It also confirms the page loads the shim and uses relative links. `publish` runs it too, and refuses if anything turns up.
- **`publish`** copies `site/` into a temporary folder and pushes it, and nothing else, to your repository's **`gh-pages`** branch. Your code's branch, your working folders and their history aren't touched. The branch is replaced each time, so it never builds up history. It pushes with the same git login you use for your code.

It prints:

```
Published the demo (3f2a9c1d7e44) to the gh-pages branch of https://github.com/USERNAME/REPOSITORY.git
Once GitHub Pages is on (Settings → Pages → Deploy from a branch → gh-pages), it's at https://USERNAME.github.io/REPOSITORY/
```

To publish somewhere else: `python demo.py publish --remote https://github.com/USERNAME/OTHER-REPOSITORY.git`.

---

## 9. Step 6: Turn on GitHub Pages

Once, on github.com:

1. Open your repository → **Settings** → **Pages**.
2. Under **Build and deployment**, set **Source** to **Deploy from a branch**.
3. Set **Branch** to **`gh-pages`** and the folder to **`/ (root)`**, then **Save**.
4. After a minute or two, the page shows "Your site is live at **https://USERNAME.github.io/REPOSITORY/**". Open it and run through the checklist in step 3.

GitHub Pages is free for public repositories. Later publishes go live within a minute or two, with no need to change the settings again.

---

## 10. Step 7: Link it from your README

**Put the link at the top of your README**, where visitors look first. A template for `README.md` at the top of your repository (replace USERNAME and REPOSITORY):

```markdown
# Market Analyst Agent

An AI agent that watches a list of stocks, flags unusual moves, explains them against the
sector and the market, and writes a daily brief, with a web app to read it all.

**[▶ Try the live demo](https://USERNAME.github.io/REPOSITORY/)**: it runs in your browser on
two months of simulated sample data, with nothing to install.

![The app's Today and Stocks tabs](docs/demo-preview.png)

## What it does

- Flags unusual moves in your watchlist (z-scores and volume), during the day and after the close
- Explains each move against its sector ETF and the S&P 500, with the likely reason from the news
- Saves every report, with a searchable history and price charts
- Answers questions about past reports (retrieval plus Claude)
- Keeps an events calendar (earnings, dividends, dated events from the news)
- Sends Discord alerts, and lets you find and track up to 25 stocks

Built with the Claude Agent SDK, MCP tools, yfinance, SQLite, Starlette and React.
```

To use the screenshot, save `demo-preview.png` (from this guide) or your own as `docs/demo-preview.png`, then commit and push.

**Also put the link at the top of the repository page:** on your repository's main page, click the gear next to **About**, paste the demo's address into **Website**, and save.

---

## 11. Updating the demo

The demo is a snapshot: it doesn't change when you push code. After changing your app:

```bash
python demo.py build && python demo.py publish
```

| When you… | Do this |
|---|---|
| Change the frontend, the API or how reports look | Build and publish again |
| Want the sample's "today" to be recent | Build and publish again (it uses the latest trading day) |
| Change only the sample (for example, different tickers) | `python demo.py build --skip-frontend --tickers …`, then publish. It keeps the built app |
| Change how a request is answered in `api.py` | Make the same change in `demo-shim.js`'s matching function, then build. `demo-shim.js` is small, and each part says which endpoint it stands in for |

---

## 12. What's real and what's simulated

Visitors see your real app, but they're told the data is simulated. Here's what that means:

| Part | In the demo |
|---|---|
| Reports, figures, verdicts, the backdrop | Your program's real output over the test environment's simulated market |
| Run update now | Four recorded runs of your real `run_brief.py` (with the test environment's stand-in for Claude), played back in order |
| Ask | The test environment's offline answer, built in the browser from the sample: flagged days, the next calendar event and the best-matching passages. No AI |
| Search | Keyword ranking plus the topic stand-in for meaning, in the browser. Good enough to show meaning-based matching; real Voyage search is better |
| Stocks tab | Search knows 35 US stocks and ETFs (plus a few that can't be tracked, to show the filtering). Track, star and remove follow `watchlist.py`'s rules and messages |
| Calendar and Update now | The sample's calendar; **Update now** replays a recorded update |
| Discord alerts | Shown as sent, as in the test environment. Nothing is sent |
| Live updates | Played back in the page, not from a server |
| What a visitor changes | Kept in that tab only, until they reload |

---

## 13. Test it

### 13.1 Automated tests

From `market-agent-demo/`, with the virtual environment active:

```bash
pytest -v
```

**Expected result:** `16 passed`, in about 40 seconds. They export a sample with two recorded runs into a temporary folder, and need no internet, npm, GitHub account or keys.

| Test | Proves that |
|---|---|
| `test_the_sample_starts_just_after_the_latest_update` | The demo starts at 12:33pm on the sample's day, with every day's report, all 44 days of history and four chart ranges per stock, search passages and the calendar. Times belong to the sample: today's calendar update was at 9:35am |
| `test_recorded_runs_move_the_day_on` | Each recorded run starts just after its time (12:45, then 13:00), shows the saved report once the run says it's saved, and stores only the files that changed. The MSFT alert is "sent" at the run's sample time |
| `test_the_calendar_update_is_recorded` | The calendar's Update now is recorded with its progress messages, at no cost |
| `test_stocks_a_visitor_can_add` | Costco has a name, its next earnings date, figures for each run and a year of chart prices. Bitcoin and Costco's Mexican listing can't be tracked, and the sample's own stocks can be removed and added back |
| `test_the_demo_uses_the_programs_own_settings` | The search, Ask and Stocks settings in the demo are read from your program and the test environment, not copied by hand |
| `test_exporting_leaves_your_projects_alone` | Every file in `market-agent/` and `market-agent-testenv/` is unchanged, and the scratch folder is deleted |
| `test_the_shim_loads_before_the_app` | The settings and the shim load before the app, the title says "live demo", and running it twice changes nothing |
| `test_finishing_the_site` | The settings file, the shim and `.nojekyll` (so GitHub Pages serves every file as it is) are added, and the site passes `check` |
| `test_check_finds_what_shouldnt_be_published` (3 cases) | An Anthropic key, a Discord webhook or a path on your computer stops publishing |
| `test_check_finds_absolute_paths_and_missing_files` | Links that would break on GitHub Pages, and a missing shim, are caught |
| `test_publish_puts_only_the_site_on_its_own_branch` | Against a local test repository: only the site's files are pushed, to `gh-pages` only, replacing the last publish. Publishing to `main` is refused, and so is a site with a key in it |
| `test_github_addresses` (3 cases) | The repository's page and the Pages address are worked out from HTTPS and SSH remotes |

**Check the tests catch real bugs.** Make one of these temporary changes, run `pytest`, then change it back. Each was tried:

| Temporary change in `demo.py` | Test that fails |
|---|---|
| In `export`, delete `install_clock(clock)` | `test_the_sample_starts_just_after_the_latest_update` and `test_recorded_runs_move_the_day_on` |
| In `add_shim`, `at = index_html.find("<script")` → `at = -1` | `test_the_shim_loads_before_the_app` |
| In `publish_site`, `if branch in ("main", "master"):` → `if False:` | `test_publish_puts_only_the_site_on_its_own_branch` |
| In `check_site`, the absolute-paths `if` → `if False:` | `test_check_finds_absolute_paths_and_missing_files` |

### 13.2 What was also tested

- **From the guides alone:** all three folders were rebuilt from the guides (this one included), and every test passed: 241 passed and 3 skipped in `market-agent/`, 29 in `market-agent-testenv/`, and 16 here.
- **In a real browser,** with the site served from a sub-folder (`/market-agent/`), as GitHub Pages serves it. The 14 checks passed, with no browser errors, failed requests or requests to any other website:
  1. The banner, **Live**, the sample day at 12:30, the main stocks and Coming up
  2. Previous days pages through all 43 earlier days, and a link straight to one day opens it
  3. Search finds the **same days as your real search** for "earnings", "quarterly" and "profit"; nonsense finds nothing
  4. Ask's answers **match the test environment's offline answers** line for line, passages included
  5. **Run update now** replays a run: progress, "Saved (updated)", the report moves to 12:45, and the alert line
  6. The Stocks tab: search, **Track as main** with its earnings date, crypto refused, unstar
  7. The next run gives COST figures, and it joins the main stocks on the Today tab
  8. Charts open for the sample's stocks and for added ones
  9. All four runs play in order, and a fifth press says it was the last
  10. The Calendar tab: the sample's month, **Update now**, and a day's page
  11. A reload starts the demo again
  12. Pressing **Run update now** again straight away explains the wait
  13. On a phone, the banner wraps and nothing scrolls sideways
  14. Dark mode, banner included
- **Found and fixed while testing:** the Today tab's "see all tracked stocks" link was hard to read in dark mode (the one-line fix in section 3).

**Not tested here:** your actual `npm run build` (Vite couldn't be installed where this guide was written, so the same app was bundled with esbuild instead), and pushing to GitHub itself (publishing was tested against a local git repository). Step 3's checklist covers both on your computer, and section 9's check covers the live site.

---

## 14. Settings

| Where | Setting | Default | What it does |
|---|---|---|---|
| `python demo.py build` | `--end YYYY-MM-DD` | the latest trading day | The sample's "today" (must be a trading day) |
| | `--tickers A,B,C` | your watchlist's | The sample's stocks (the first 3 are main) |
| | `--steps N` | `4` | Recorded runs for **Run update now** |
| | `--repo-url URL` | from git | The banner's "See the code on GitHub" link |
| | `--skip-frontend` | off | Only remake the sample, keeping the built app |
| `python demo.py serve` | `--port N` | `8200` | The local preview's port |
| `python demo.py publish` | `--remote URL` | `market-agent`'s `origin` | Where to publish |
| | `--branch NAME` | `gh-pages` | The branch GitHub Pages serves (never `main`) |
| Environment | `MARKET_AGENT_DIR`, `MARKET_AGENT_TESTENV_DIR` | the folders next to this one | Where your program and the test environment are |
| `demo.py` | `cooldown_seconds` (in `export`) | `15` | The wait between presses of Run update now and Update now |

---

## 15. Costs

- **GitHub Pages:** free for public repositories.
- **Claude, Voyage, market data:** none. The demo calls no API, when you build it or when visitors use it.
- **Visitors:** however many come, there's nothing to pay for and nothing to rate-limit.

---

## 16. Security and privacy

- **No keys, anywhere.** The site has no server and calls no API, so it needs no keys. `check` (run again by `publish`) refuses to publish anything that looks like an Anthropic key, a Discord webhook or a GitHub token.
- **Only sample data.** The exporter builds a fresh sample in a scratch folder. Your real `reports.db`, search index and alert log are never opened. Your `watchlist.txt` is only read, for its tickers; use `--tickers` if you'd rather not show them.
- **No paths from your computer.** `check` also refuses any file that mentions your home folder or your project folders.
- **Only the site is published,** to a branch of its own. The `gh-pages` branch holds `site/` and nothing else.
- **Nothing to break.** A visitor's changes live in their own tab and disappear on reload. Nothing is sent anywhere: the demo makes no requests to any other website (the browser test checks this).
- **Your real app's protections don't change.** The demo is a separate, static copy. Your API still listens on your own computer only.

---

## 17. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Can't find the test environment at …` | Set up `market-agent-testenv/` first (test environment guide), next to this folder, or set `MARKET_AGENT_TESTENV_DIR`. |
| `npm wasn't found` / `Run npm install …` | Install Node.js, or run `npm install` in `market-agent/frontend` (frontend guide). |
| `The sample's latest day … is already final` | `--end` was a weekend or holiday. Use a trading day, or leave `--end` out. |
| `ModuleNotFoundError` (such as `starlette`) | The virtual environment isn't active (step 2). |
| `--skip-frontend needs an earlier build` | Run `python demo.py build` once without it. |
| `index.html uses absolute paths` | The app was built without `--base ./`. Use `python demo.py build`, which adds it. |
| `No GitHub repository found for market-agent/` | The project isn't on GitHub yet (step 4), or use `--remote https://github.com/USERNAME/REPOSITORY.git`. |
| `git push failed` | Push your code once by hand (`git push`) to check your GitHub login works, then publish again. |
| The Pages address shows 404 | Pages isn't on yet, or it's set to the wrong branch (step 6: `gh-pages`, `/ (root)`). The first publish can take a few minutes to appear. |
| The page is blank, or stuck on "Loading…" | Open the browser's developer console. A `demo data missing` error means `site/` was only partly published: run `python demo.py build` and publish again. |
| The demo still shows the old version | Browsers keep pages for a few minutes. Hard-refresh (Ctrl+Shift+R, or Cmd+Shift+R on a Mac). |
| The banner has no GitHub link | The repository wasn't known when you built. Build again after step 4, or use `--repo-url`. |
| Visitors in far-off time zones see "Coming up" without today's events | The demo's clock is set to the sample's afternoon in New York, which is already the next day in East Asia and Australia. Tomorrow's events still show. |

---

## Appendix: full source code

### demo.py

```python
"""Live demo of the market analyst agent: a website anyone can try, on GitHub Pages.

The site is your real React app plus a small script, demo-shim.js, that answers the app's
requests inside the browser. Its data comes from the test environment: two months of
simulated reports, a few recorded "Run update now" runs, the events calendar and the
Stocks tab. There is no server and no Claude, so there are no keys to leak and nothing
that can run up costs.

    python demo.py build      make the site in site/ (sample data plus your app)
    python demo.py serve      try it at http://localhost:8200
    python demo.py check      look for anything that shouldn't be published
    python demo.py publish    put site/ on your GitHub repository's gh-pages branch

It lives next to market-agent/ and market-agent-testenv/, and never writes into either.
"""

import argparse
import functools
import hashlib
import http.server
import json
import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True                # never leave __pycache__ folders in the other projects
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = Path(__file__).resolve().parent
MAIN = Path(os.environ.get("MARKET_AGENT_DIR") or HERE.parent / "market-agent").resolve()
TESTENV = Path(os.environ.get("MARKET_AGENT_TESTENV_DIR") or HERE.parent / "market-agent-testenv").resolve()
SITE = HERE / "site"            # what gets published
WORK = HERE / ".work"           # scratch sample databases while building (deleted afterwards)
DATA = "demo-data"              # the sample data's folder inside the site
SHIM = HERE / "demo-shim.js"
PORT = 8200
STEPS = 4                       # recorded "Run update now" runs (each 15 sample minutes later)
ET = ZoneInfo("America/New_York")
PUBLISH_BRANCH = "gh-pages"
MAX_SITE_MB = 50
# Never publish anything that looks like a key or a webhook
SECRET_PATTERNS = [re.compile(p) for p in (r"sk-ant-[A-Za-z0-9_\-]{8,}", r"discord(?:app)?\.com/api/webhooks/\d+",
                                           r"\bpa-[A-Za-z0-9_\-]{20,}", r"ghp_[A-Za-z0-9]{20,}",
                                           r"github_pat_[A-Za-z0-9_]{20,}")]


# ---------------------------------------------------------------------------
# Using the test environment, safely
# ---------------------------------------------------------------------------

def load_testenv():
    """The test environment's code, which runs your program against sample data only."""
    if not (TESTENV / "testenv.py").is_file():
        sys.exit(f"Can't find the test environment at {TESTENV}. Set it up first (market-agent-test-enviro.md), "
                 "or set MARKET_AGENT_TESTENV_DIR.")
    for folder in (MAIN, TESTENV):
        if HERE == folder or folder in HERE.parents:
            sys.exit("The demo folder must be next to market-agent/ and market-agent-testenv/, not inside them.")
    os.environ.setdefault("MARKET_AGENT_DIR", str(MAIN))
    if str(TESTENV) not in sys.path:
        sys.path.insert(0, str(TESTENV))
    import testenv
    return testenv


class SampleClock:
    """One clock for every part of the program while building, set to the sample's day, so the
    times the demo shows (saved at, sent at, updated at) belong to the sample, not to the day you built it."""

    def __init__(self, moment: datetime):
        self.set(moment)

    def set(self, moment: datetime) -> None:
        self.base, self.started = moment.astimezone(timezone.utc), time.monotonic()

    def now(self) -> datetime:
        return self.base + timedelta(seconds=time.monotonic() - self.started)

    def stamp(self) -> str:
        return self.now().strftime("%Y-%m-%dT%H:%M:%SZ")


def install_clock(clock: SampleClock) -> None:
    import alerts
    import api
    import events
    import reports_db
    reports_db._utc_now = clock.stamp
    events._utc_now = clock.stamp
    api._utc_now = clock.stamp
    alerts._utc_now = clock.now


class Recorder:
    """Keeps every live update the app sends (run progress, saved reports, calendar updates), with its timing."""

    def __init__(self, hub):
        self.events, self.started = [], None
        original = hub.publish

        def publish(event):
            if self.started is not None:
                self.events.append({"at": round(time.monotonic() - self.started, 2), "event": json.loads(json.dumps(event))})
            original(event)

        hub.publish = publish

    def start(self) -> None:
        self.events, self.started = [], time.monotonic()

    def wait_for(self, kind: str, timeout: float = 15) -> bool:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if any(e["event"]["type"] == kind for e in self.events):
                return True
            time.sleep(0.05)
        return False

    def stop(self) -> list[dict]:
        self.started = None
        return self.events


def et_moment(day: date, hh: int, mm: int) -> datetime:
    return datetime(day.year, day.month, day.day, hh, mm, tzinfo=ET)


def as_of_moment(as_of: str) -> datetime:
    """'2026-11-06 12:45 ET' as a time."""
    return datetime.strptime(as_of, "%Y-%m-%d %H:%M ET").replace(tzinfo=ET)


def latest_trading_day(today: date) -> date:
    from sample_market import trading_days
    return trading_days(today - timedelta(days=10), today)[-1]


# ---------------------------------------------------------------------------
# Exporting: every answer the app will ask for, as files
# ---------------------------------------------------------------------------

def get(client, url: str):
    response = client.get(url)
    if response.status_code != 200:
        raise RuntimeError(f"{url} gave {response.status_code}: {response.text[:200]}")
    return response.json()


def collect(client, db: Path) -> dict:
    """The answers that can change when a run saves a report, keyed by their file in demo-data/."""
    import api
    import events
    import reports_db
    import search_index
    files = {}
    with closing(reports_db.connect(db, readonly=True)) as conn:
        days = [r["session_date"] for r in reports_db.list_reports(conn, limit=100_000)]
        files["reports.json"] = {"reports": reports_db.list_reports(conn, limit=100_000)}
        tickers = [r[0] for r in conn.execute("SELECT DISTINCT ticker FROM report_tickers ORDER BY ticker")]
        for t in tickers:
            files[f"tickers/{t}/history.json"] = {"ticker": t, "history": reports_db.ticker_history(conn, t, limit=100_000)}
        found = events.events_between(conn, "0001-01-01", "9999-12-31")
        for e in found:  # ready-made lines for the demo's offline answers
            e["_line"], e["_line_company"] = events.event_line(e, company=False), events.event_line(e)
        files["calendar.json"] = {"today": events.today_et().isoformat(), "events": found,
                                  "last_scan": events.last_scan(conn), "max_days": api.MAX_CALENDAR_DAYS}
    files["reports/latest.json"] = get(client, "/api/reports/latest")
    for day in days:
        files[f"reports/{day}.json"] = get(client, f"/api/reports/{day}")
    files["watchlist.json"] = get(client, "/api/watchlist")
    files["alerts.json"] = get(client, "/api/alerts?limit=100")
    files["runs/current.json"] = get(client, "/api/runs/current")
    for t in [s["ticker"] for s in files["watchlist.json"]["stocks"]]:
        for period in ("1mo", "3mo", "6mo", "1y"):
            files[f"tickers/{t}/prices-{period}.json"] = get(client, f"/api/tickers/{t}/prices?range={period}")
    search_index.sync()
    with closing(search_index.connect()) as conn:
        files["search/passages.json"] = {"passages": [dict(r) for r in conn.execute(
            "SELECT id, session_date, status, ticker, heading, text FROM chunks ORDER BY session_date, id")]}
    files["known_tickers.json"] = {"tickers": tickers}
    return files


def dump(value) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False)


def write_files(root: Path, files: dict) -> None:
    for name, value in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dump(value), encoding="utf-8")


def play_run(client, recorder, clock, reports_db, testenv, db: Path) -> list[dict] | None:
    """One simulated "Run update now", as the app's live updates saw it. None once the day is final."""
    market = testenv.load_market(db)
    point = testenv.next_intraday_point(reports_db, market, db)
    if point is None:
        return None
    clock.set(as_of_moment(point[1]) + timedelta(seconds=40))  # the run happens just after its as-of time
    recorder.start()
    response = client.post("/api/runs", json={})
    if response.status_code != 202:
        raise RuntimeError(f"Run now gave {response.status_code}: {response.text}")
    if not (recorder.wait_for("run_finished") and recorder.wait_for("report_saved")):
        raise RuntimeError("The simulated run didn't finish")
    recorded = recorder.stop()
    # Show the saved report as soon as the run says "Saved" (the real app notices within 2 seconds)
    saved = next(e for e in recorded if e["event"]["type"] == "run_event" and e["event"]["event"]["type"] == "saved")
    for e in recorded:
        if e["event"]["type"] == "report_saved":
            e["at"] = saved["at"] + 0.05
    keep = {"run_started", "run_event", "run_finished", "report_saved"}
    return sorted((e for e in recorded if e["event"]["type"] in keep), key=lambda e: e["at"])


def fresh_api_state(api, recorder_box: list) -> None:
    """A clean slate between the two sample databases (the api module stays loaded)."""
    api.runs = api.RunManager()
    api.calendar_scans = api.CalendarScanManager()
    api.hub = api.EventHub()
    recorder_box[:] = [Recorder(api.hub)]
    api.RUN_COOLDOWN_SECONDS = 0
    api.CALENDAR_SCAN_COOLDOWN_SECONDS = 0
    api.POLL_SECONDS = 0.2  # notice saved reports quickly while recording


def seed(testenv, db: Path, clock: SampleClock, end: date, tickers: list[str] | None) -> None:
    """The test environment's sample, with the calendar's daily scans timed at 9:35am on their days."""
    original = testenv.simulate_events_scan

    def scan_at_the_open(db_path=testenv.DB_PATH, as_of=None):
        day = as_of or end
        clock.set(et_moment(day, 9, 35))
        return original(db_path, as_of)

    testenv.simulate_events_scan = scan_at_the_open
    try:
        testenv.seed_database(db, end=end, tickers=tickers, latest="intraday")
    finally:
        testenv.simulate_events_scan = original


def export(out: Path, end: date | None = None, tickers: list[str] | None = None, steps: int = STEPS,
           repo_url: str = "") -> dict:
    """Write the demo's data into out/ (normally site/demo-data/). Returns the manifest."""
    testenv = load_testenv()
    from starlette.testclient import TestClient

    end = end or latest_trading_day(datetime.now(ET).date())
    shutil.rmtree(WORK, ignore_errors=True)
    main_db, universe_db = WORK / "sample" / "reports.db", WORK / "universe" / "reports.db"
    testenv.connect_main(main_db)  # also refuses anything inside your program's folder
    import api
    import ask
    import events
    import reports_db
    import search_index
    import watchlist
    clock = SampleClock(et_moment(end, 9, 0))
    install_clock(clock)

    # 1. The sample, and the start of the demo: a few minutes after the latest update was saved
    seed(testenv, main_db, clock, end, tickers)
    tickers = testenv.read_tickers(testenv.watchlist_path(main_db))
    with closing(reports_db.connect(main_db, readonly=True)) as conn:
        latest = reports_db.latest_report(conn)
    if latest["status"] != "intraday":
        sys.exit(f"The sample's latest day ({latest['session_date']}) is already final. Use --end with a trading day.")
    start = as_of_moment(latest["as_of"]) + timedelta(minutes=3)

    if out.exists():
        shutil.rmtree(out)
    versions: dict[str, list[int]] = {}
    recorded_runs, scan_events = [], []
    box: list = []
    app = testenv.make_app(main_db, frontend_dist=WORK / "no-frontend")
    fresh_api_state(api, box)
    with TestClient(app) as client:
        clock.set(start)
        current = collect(client, main_db)
        write_files(out / "0", current)
        for name in current:
            versions[name] = [0]
        # 2. Recorded runs: each saves a newer update, and only the files that changed are kept
        for k in range(1, steps + 1):
            run = play_run(client, box[0], clock, reports_db, testenv, main_db)
            if run is None:
                break
            files = collect(client, main_db)
            changed = {name: value for name, value in files.items() if dump(value) != dump(current.get(name))}
            write_files(out / str(k), changed)
            for name in changed:
                versions.setdefault(name, []).append(k)
            current.update(files)
            recorded_runs.append({"started_at": run[0]["event"]["run"]["started_at"], "events": run})
        # 3. A recorded calendar "Update now" (it doesn't change the events, only when they were last checked)
        clock.set(start)
        box[0].start()
        if client.post("/api/calendar/scan", json={}).status_code != 202:
            raise RuntimeError("The calendar's Update now didn't start")
        if not box[0].wait_for("calendar_updated"):
            raise RuntimeError("The simulated calendar update didn't finish")
        scan_events = [e for e in box[0].stop() if e["event"]["type"] in ("calendar_scan", "calendar_updated")]

    # 4. Stocks a visitor can add: names, next events, prices and their figures in each recorded run
    universe, written = export_universe(testenv, out, universe_db, clock, end, tickers, len(recorded_runs), box)
    for name in written:
        versions[name] = [0]

    reports = current["reports.json"]["reports"]
    summary = {"days": len(reports), "first_day": reports[-1]["session_date"]}
    manifest = {
        "version": 1,
        "built": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "today": end.isoformat(),
        "start": start.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_url": repo_url,
        "sample": summary,
        "versions": versions,
        "runs": recorded_runs,
        "calendar_scan": scan_events,
        "limits": {"max_tracked": watchlist.MAX_TRACKED, "max_main": watchlist.MAX_MAIN,
                   "allowed_types": watchlist.ALLOWED_TYPES, "ticker_pattern": watchlist.TICKER.pattern,
                   "search_cache_seconds": watchlist.SEARCH_CACHE_SECONDS},
        "search": {"topics": testenv.SIMULATED_TOPICS, "rrf_k": search_index.RRF_K,
                   "min_similarity": search_index.MIN_SIMILARITY, "meaning_cutoff": search_index.MEANING_CUTOFF,
                   "max_query_words": search_index.MAX_QUERY_WORDS},
        "ask": {"recent_reports": ask.RECENT_REPORTS, "flagged_reports_per_ticker": ask.FLAGGED_REPORTS_PER_TICKER,
                "passages": ask.PASSAGES, "calendar_days": ask.CALENDAR_DAYS, "max_question_chars": ask.MAX_QUESTION_CHARS},
        "cooldown_seconds": 15,
        "universe": universe,
    }
    (out / "manifest.json").write_text(dump(manifest), encoding="utf-8")
    shutil.rmtree(WORK, ignore_errors=True)
    return manifest


def export_universe(testenv, out: Path, db: Path, clock: SampleClock, end: date, tickers: list[str],
                    steps: int, box: list) -> tuple[list[dict], list[str]]:
    """A second copy of the sample with every searchable stock added, to record what each would show.
    Stocks added to the sample get their own simulated prices, so the first copy's stocks are unaffected."""
    from starlette.testclient import TestClient
    from sample_market import STOCK_UNIVERSE, ticker_info
    import api
    import events
    import reports_db
    import watchlist

    testenv.connect_main(db)
    seed(testenv, db, clock, end, tickers)
    saved_limit = watchlist.MAX_TRACKED
    watchlist.MAX_TRACKED = 10_000
    entries = {}
    for symbol, name, kind, exchange in STOCK_UNIVERSE:
        entries[symbol] = {"ticker": symbol, "name": name, "quote_type": kind, "exchange": exchange,
                           "trackable": kind in watchlist.ALLOWED_TYPES and bool(watchlist.TICKER.fullmatch(symbol))}
    for t in tickers:  # stocks in the sample (removing then adding them back must work too)
        if t not in entries:
            info = ticker_info(t)
            entries[t] = {"ticker": t, "name": info.get("longName") or t, "quote_type": info.get("quoteType") or "EQUITY",
                          "exchange": "", "trackable": True}
    for e in entries.values():
        e["in_sample"] = e["ticker"] in tickers
    to_add = [e["ticker"] for e in entries.values() if e["trackable"] and not e["in_sample"]]
    written = []
    try:
        app = testenv.make_app(db, frontend_dist=WORK / "no-frontend")
        fresh_api_state(api, box)
        with TestClient(app) as client:
            with closing(reports_db.connect(db, readonly=True)) as conn:
                clock.set(as_of_moment(reports_db.latest_report(conn)["as_of"]))
            for t in to_add:
                response = client.post("/api/watchlist", json={"ticker": t})
                if response.status_code != 201:
                    raise RuntimeError(f"Couldn't add {t} to the second sample: {response.text}")
            deadline = time.monotonic() + 20  # their calendar dates are added in the background
            while time.monotonic() < deadline:
                with closing(reports_db.connect(db, readonly=True)) as conn:
                    have = {r[0] for r in conn.execute("SELECT DISTINCT ticker FROM events")}
                view = get(client, "/api/watchlist")
                if all(s["name"] for s in view["stocks"]) and len(have & set(to_add)) >= len(to_add) * 0.5:
                    break
                time.sleep(0.2)
            time.sleep(1.0)
            view = {s["ticker"]: s for s in get(client, "/api/watchlist")["stocks"]}
            with closing(reports_db.connect(db, readonly=True)) as conn:
                calendar = events.events_between(conn, "0001-01-01", "9999-12-31")
            for t in to_add:
                entries[t]["short_name"] = view[t]["name"]
                entries[t]["next_event"] = view[t]["next_event"]
                entries[t]["events"] = [e for e in calendar if e["ticker"] == t]
                for e in entries[t]["events"]:
                    e["_line"], e["_line_company"] = events.event_line(e, company=False), events.event_line(e)
                entries[t]["steps"] = []
            for k in range(1, steps + 1):
                if play_run(client, box[0], clock, reports_db, testenv, db) is None:
                    break
                rows = {r["ticker"]: r for r in get(client, "/api/reports/latest")["tickers"]}
                view = {s["ticker"]: s for s in get(client, "/api/watchlist")["stocks"]}
                for t in to_add:
                    entries[t]["steps"].append({"row": rows.get(t), "latest": view[t]["latest"]})
                if k == 1:  # chart prices, once each stock is in an intraday report
                    for t in to_add:
                        files = {f"tickers/{t}/prices-{p}.json": get(client, f"/api/tickers/{t}/prices?range={p}")
                                 for p in ("1mo", "3mo", "6mo", "1y")}
                        write_files(out / "0", files)
                        written += list(files)
    finally:
        watchlist.MAX_TRACKED = saved_limit
    return list(entries.values()), written


# ---------------------------------------------------------------------------
# Building the site
# ---------------------------------------------------------------------------

def add_shim(index_html: str, title: str = "Market Analyst · live demo") -> str:
    """Load the demo's settings and stand-in API before the app itself."""
    tags = '<script src="./demo-config.js"></script>\n    <script src="./demo-shim.js"></script>\n    '
    if "demo-shim.js" not in index_html:
        at = index_html.find("<script")
        if at == -1:
            at = index_html.find("</head>")
        if at == -1:
            raise ValueError("index.html has no <script> or </head>: is it the built app?")
        index_html = index_html[:at] + tags + index_html[at:]
    return re.sub(r"<title>.*?</title>", f"<title>{title}</title>", index_html, count=1, flags=re.S)


def build_frontend(target: Path) -> None:
    """Build your React app into the site folder (your own frontend/dist/ is left alone).
    --base ./ makes every link relative, because GitHub Pages serves the site from /REPOSITORY/."""
    npm = shutil.which("npm")
    frontend = MAIN / "frontend"
    if not npm:
        sys.exit("npm wasn't found. Install Node.js (see the frontend guide).")
    if not (frontend / "node_modules").is_dir():
        sys.exit(f"Run `npm install` in {frontend} first (see the frontend guide).")
    subprocess.run([npm, "run", "build", "--", "--outDir", str(target), "--emptyOutDir", "--base", "./"],
                   cwd=frontend, check=True)


def build(args) -> None:
    repo_url = args.repo_url or guess_repo_url()
    tickers = [t.strip().upper() for t in args.tickers.split(",")] if args.tickers else None
    if args.skip_frontend:
        if not (SITE / "index.html").is_file():
            sys.exit("--skip-frontend needs an earlier build in site/ (run `python demo.py build` once).")
    else:
        build_frontend(SITE)
    manifest = export(SITE / DATA, end=args.end, tickers=tickers, steps=args.steps, repo_url=repo_url)
    finish_site(SITE, manifest)
    problems = check_site(SITE)
    print(f"Built the demo in {SITE}")
    print(f"  sample: {manifest['sample']['days']} days of reports, from {manifest['sample']['first_day']} "
          f"to {manifest['today']}, with {len(manifest['runs'])} recorded runs")
    print(f"  size: {site_size(SITE) / 1e6:.1f} MB")
    if problems:
        sys.exit("Problems:\n" + "\n".join(f"  - {p}" for p in problems))
    print("Try it with: python demo.py serve")


def finish_site(site: Path, manifest: dict) -> None:
    index = site / "index.html"
    index.write_text(add_shim(index.read_text(encoding="utf-8")), encoding="utf-8")
    shutil.copyfile(SHIM, site / "demo-shim.js")
    config = {"data": DATA, "start": manifest["start"], "today": manifest["today"], "repo_url": manifest["repo_url"]}
    (site / "demo-config.js").write_text(
        "// Written by demo.py: where the sample data is, and the moment the demo starts at\n"
        f"window.DEMO_CONFIG = {json.dumps(config)};\n", encoding="utf-8")
    (site / ".nojekyll").write_text("")  # GitHub Pages: serve every file as it is


GITHUB_REMOTE = re.compile(r"^(?:https://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")


def repo_page(remote: str) -> str:
    """'git@github.com:you/market-agent.git' -> 'https://github.com/you/market-agent' ('' if not GitHub)."""
    match = GITHUB_REMOTE.match(remote.strip())
    return f"https://github.com/{match.group(1)}/{match.group(2)}" if match else ""


def pages_address(remote: str) -> str:
    """Where GitHub Pages serves a repository's site."""
    match = GITHUB_REMOTE.match(remote.strip())
    return f"https://{match.group(1).lower()}.github.io/{match.group(2)}/" if match else ""


def origin_remote() -> str:
    try:
        return subprocess.run(["git", "-C", str(MAIN), "remote", "get-url", "origin"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def guess_repo_url() -> str:
    """Your repository's page on GitHub, for the demo's banner (from git, if it knows)."""
    return repo_page(origin_remote())


# ---------------------------------------------------------------------------
# Checking and publishing
# ---------------------------------------------------------------------------

def site_size(site: Path) -> int:
    return sum(p.stat().st_size for p in site.rglob("*") if p.is_file())


def check_site(site: Path) -> list[str]:
    """Reasons not to publish: missing pieces, anything that looks like a key, or local paths."""
    problems = []
    for name in ("index.html", "demo-shim.js", "demo-config.js", f"{DATA}/manifest.json"):
        if not (site / name).is_file():
            problems.append(f"{name} is missing: run `python demo.py build`")
    index = site / "index.html"
    if index.is_file():
        html = index.read_text(encoding="utf-8")
        if "demo-shim.js" not in html:
            problems.append("index.html doesn't load demo-shim.js")
        if re.search(r'(?:src|href)="/(?!/)', html):
            problems.append("index.html uses absolute paths (/assets/...), which break on GitHub Pages: build with --base ./")
    private = [s for s in {str(Path.home()), str(MAIN), str(HERE.parent)} if len(s) > 3]
    for path in sorted(p for p in site.rglob("*") if p.is_file()):
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2"):
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        rel = path.relative_to(site)
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{rel} contains something that looks like a key or webhook ({pattern.pattern[:12]}…)")
        for folder in private:
            if folder in text:
                problems.append(f"{rel} mentions a folder on your computer ({folder})")
                break
    if site.is_dir() and site_size(site) > MAX_SITE_MB * 1e6:
        problems.append(f"the site is over {MAX_SITE_MB} MB")
    return problems


def check(args) -> None:
    problems = check_site(SITE)
    if problems:
        sys.exit("Not ready to publish:\n" + "\n".join(f"  - {p}" for p in problems))
    print(f"OK: {sum(1 for p in SITE.rglob('*') if p.is_file())} files, {site_size(SITE) / 1e6:.1f} MB, "
          "no keys, webhooks or local paths found")


def git(*args, cwd: Path, check_result: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=check_result)


def publish_site(site: Path, remote: str, branch: str = PUBLISH_BRANCH) -> str:
    """Push the site, and nothing else, to a branch of its own. The branch is replaced each time,
    so it never builds up history. Your other branches and your working folders are untouched."""
    if branch in ("main", "master"):
        raise ValueError("Publish to a branch of its own (gh-pages), never to your code's branch.")
    problems = check_site(site)
    if problems:
        raise ValueError("Not ready to publish:\n" + "\n".join(f"  - {p}" for p in problems))
    with tempfile.TemporaryDirectory(prefix="market-agent-demo-") as tmp:
        work = Path(tmp) / "site"
        shutil.copytree(site, work)
        git("init", "-q", cwd=work)
        git("checkout", "-q", "-b", branch, cwd=work)
        git("add", "-A", cwd=work)
        who = [] if git("config", "user.email", cwd=work, check_result=False).stdout.strip() else \
            ["-c", "user.name=market-agent demo", "-c", "user.email=demo@users.noreply.github.com"]
        digest = hashlib.sha256(b"".join(p.read_bytes() for p in sorted(work.rglob("*")) if p.is_file()
                                         and ".git" not in p.parts)).hexdigest()[:12]
        git(*who, "commit", "-q", "-m", f"Live demo ({digest})", cwd=work)
        pushed = git("push", "--force", remote, f"HEAD:refs/heads/{branch}", cwd=work, check_result=False)
        if pushed.returncode != 0:
            raise RuntimeError(f"git push failed:\n{pushed.stderr.strip()}")
    return digest


def publish(args) -> None:
    remote = args.remote or origin_remote()
    if not remote:
        sys.exit("No GitHub repository found for market-agent/. Use: python demo.py publish --remote "
                 "https://github.com/USERNAME/REPOSITORY.git")
    try:
        digest = publish_site(SITE, remote, args.branch)
    except (ValueError, RuntimeError) as e:
        sys.exit(str(e))
    print(f"Published the demo ({digest}) to the {args.branch} branch of {remote}")
    if pages_address(remote):
        print(f"Once GitHub Pages is on (Settings → Pages → Deploy from a branch → {args.branch}), it's at "
              f"{pages_address(remote)}  (allow a minute or two after each publish)")


def serve(args) -> None:
    if not (SITE / "index.html").is_file():
        sys.exit("No site yet. Run: python demo.py build")
    handler = functools.partial(QuietHandler, directory=str(SITE))
    with http.server.ThreadingHTTPServer(("127.0.0.1", args.port), handler) as server:
        print(f"Live demo: http://localhost:{args.port}  (the same files GitHub Pages will serve; Ctrl+C to stop)")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def main() -> None:
    parser = argparse.ArgumentParser(description="Live demo of the market analyst agent, for GitHub Pages.")
    commands = parser.add_subparsers(dest="command", required=True)
    b = commands.add_parser("build", help="make the site in site/")
    b.add_argument("--end", type=date.fromisoformat,
                   help="the sample's 'today', a trading day (default: the latest trading day)")
    b.add_argument("--tickers", help="comma-separated (default: the test environment's watchlist)")
    b.add_argument("--steps", type=int, default=STEPS, help=f"recorded Run now updates (default {STEPS})")
    b.add_argument("--repo-url", help="your repository's GitHub page, linked from the demo's banner (default: from git)")
    b.add_argument("--skip-frontend", action="store_true", help="only refresh the sample data (keeps the built app)")
    s = commands.add_parser("serve", help="try the site locally")
    s.add_argument("--port", type=int, default=PORT)
    commands.add_parser("check", help="look for anything that shouldn't be published")
    p = commands.add_parser("publish", help="push site/ to your repository's gh-pages branch")
    p.add_argument("--remote", help="the repository to publish to (default: market-agent's origin)")
    p.add_argument("--branch", default=PUBLISH_BRANCH)
    args = parser.parse_args()
    {"build": build, "serve": serve, "check": check, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
```

### demo-shim.js

```javascript
/* Live demo: answers the app's /api requests inside the browser, from the sample data in
   demo-data/ (made by demo.py from the test environment). It's loaded before the app, so the
   app's own code runs unchanged: it calls fetch('/api/...') and opens EventSource('/api/events')
   as usual, and gets the same answers your Python API would give for the sample.

   Nothing here contacts a server or an AI. What a visitor changes (stocks, runs played) lives
   in this tab only, and a reload starts the demo again.

   It also:
   - sets the page's clock to the sample's trading day, so "today" matches the sample
   - adds a short banner saying the data is simulated */
;(function () {
  'use strict'

  const config = window.DEMO_CONFIG || {}
  const realFetch = window.fetch.bind(window)
  const RealDate = window.Date
  const RealEventSource = window.EventSource
  const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

  // ---------------------------------------------------------------------------
  // The clock: the sample's day, moving on to each recorded run's time when it's played
  // ---------------------------------------------------------------------------

  let offset = 0
  const now = () => RealDate.now() + offset
  const nowISO = () => new RealDate(now()).toISOString().replace(/\.\d{3}Z$/, 'Z')
  const setClock = (ms) => {
    offset = ms - RealDate.now()
  }

  class DemoDate extends RealDate {
    constructor(...args) {
      if (args.length === 0) super(RealDate.now() + offset)
      else super(...args)
    }

    static now() {
      return RealDate.now() + offset
    }
  }
  window.Date = DemoDate
  if (config.start) setClock(RealDate.parse(config.start))

  // ---------------------------------------------------------------------------
  // The sample data. Each file has versions: 0 is the start, and N is from the Nth recorded run.
  // ---------------------------------------------------------------------------

  const dataRoot = new URL(`${config.data || 'demo-data'}/`, document.baseURI)
  const files = new Map()
  let manifest = null
  const state = {
    step: 0, // recorded runs played so far
    run: null,
    scan: { state: 'idle', started_at: null, finished_at: null, message: null, result: null, error: null },
    lastScan: null, // set once "Update now" has been played
    stocks: [], // [{ticker, main, benchmark}] in list order
    addedAt: {}, // ticker -> runs played when it was added
    eventsReady: {}, // ticker -> its calendar dates have been "looked up"
    lastRunStart: -Infinity,
    lastScanStart: -Infinity,
  }
  let universe = {}

  function loadFile(path) {
    if (!files.has(path)) {
      files.set(
        path,
        realFetch(new URL(path, dataRoot)).then((response) => {
          if (!response.ok) throw new Error(`demo data missing: ${path}`)
          return response.json()
        }),
      )
    }
    return files.get(path)
  }

  function versionOf(name) {
    let found = null
    for (const v of manifest.versions[name] || []) if (v <= state.step) found = v
    return found
  }

  // A copy of the file as it is after the runs played so far, or null if there's no such file
  async function data(name) {
    const v = versionOf(name)
    if (v === null) return null
    return JSON.parse(JSON.stringify(await loadFile(`${v}/${name}`)))
  }

  const ready = loadFile('manifest.json').then(async (m) => {
    manifest = m
    universe = Object.fromEntries(m.universe.map((u) => [u.ticker, u]))
    const list = await data('watchlist.json')
    state.stocks = list.stocks.map((s) => ({ ticker: s.ticker, main: s.main, benchmark: s.benchmark }))
    state.run = (await data('runs/current.json')).run
  })

  // ---------------------------------------------------------------------------
  // Live updates: a stand-in for the EventSource the app opens on /api/events
  // ---------------------------------------------------------------------------

  const openStreams = new Set()

  function emit(event) {
    for (const stream of openStreams) setTimeout(() => stream._deliver(event), 0)
  }

  class DemoEventSource {
    constructor(url, options) {
      const target = new URL(url, window.location.href)
      if (!target.pathname.startsWith('/api/') && RealEventSource) return new RealEventSource(url, options)
      this.url = target.href
      this.withCredentials = false
      this.readyState = 0
      this.onopen = this.onmessage = this.onerror = null
      this._listeners = {}
      openStreams.add(this)
      ready.then(() => {
        if (this.readyState === 2) return
        this.readyState = 1
        this._fire('open', new Event('open'))
        this._deliver({ type: 'hello', run: state.run, latest: null, calendar_scan: state.scan })
      })
    }

    _deliver(event) {
      if (this.readyState === 1) this._fire('message', new MessageEvent('message', { data: JSON.stringify(event) }))
    }

    _fire(type, event) {
      if (typeof this[`on${type}`] === 'function') this[`on${type}`](event)
      for (const listener of this._listeners[type] || []) listener.call(this, event)
    }

    addEventListener(type, listener) {
      ;(this._listeners[type] = this._listeners[type] || []).push(listener)
    }

    removeEventListener(type, listener) {
      this._listeners[type] = (this._listeners[type] || []).filter((l) => l !== listener)
    }

    close() {
      this.readyState = 2
      openStreams.delete(this)
    }
  }
  DemoEventSource.CONNECTING = 0
  DemoEventSource.OPEN = 1
  DemoEventSource.CLOSED = 2
  window.EventSource = DemoEventSource

  // ---------------------------------------------------------------------------
  // Helpers shared by the endpoints
  // ---------------------------------------------------------------------------

  class ApiError extends Error {
    constructor(status, message) {
      super(message)
      this.status = status
    }
  }

  const DATE = /^\d{4}-\d{2}-\d{2}$/
  const json = (body, status = 200) =>
    new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })

  function limitOf(params, fallback, maximum) {
    const raw = params.get('limit') ?? String(fallback)
    const n = /^\d+$/.test(raw) ? Number(raw) : NaN
    if (!(n >= 1 && n <= maximum)) throw new ApiError(400, `limit must be a whole number from 1 to ${maximum}`)
    return n
  }

  const plural = (n, word) => `${n} ${word}${n === 1 ? '' : 's'}`
  const signed = (v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}`

  function addDays(day, n) {
    const d = new RealDate(`${day}T00:00:00Z`)
    d.setUTCDate(d.getUTCDate() + n)
    return d.toISOString().slice(0, 10)
  }

  function realDate(day) {
    return DATE.test(day) && new RealDate(`${day}T00:00:00Z`).toISOString().slice(0, 10) === day
  }

  const byEvent = (a, b) =>
    a.event_date.localeCompare(b.event_date) ||
    a.company.localeCompare(b.company) ||
    a.kind.localeCompare(b.kind) ||
    a.title.localeCompare(b.title)

  // Stocks added on the Stocks tab that weren't in the sample (they have recorded figures per run)
  const addedFromUniverse = () => state.stocks.filter((s) => universe[s.ticker] && !universe[s.ticker].in_sample)

  function figuresFor(ticker) {
    const runs = state.step - (state.addedAt[ticker] ?? 0)
    return runs > 0 ? universe[ticker].steps?.[state.step - 1] || null : null
  }

  async function calendarEvents() {
    const calendar = await data('calendar.json')
    const extra = addedFromUniverse().flatMap((s) => (state.eventsReady[s.ticker] ? universe[s.ticker].events || [] : []))
    return { calendar, events: [...calendar.events, ...extra].sort(byEvent) }
  }

  // ---------------------------------------------------------------------------
  // Reports, charts, alerts
  // ---------------------------------------------------------------------------

  const CATEGORY_ORDER = { flagged: 0, quiet: 1, error: 2 }

  // Today's report also lists stocks added since, once a run has been played (as a real run would)
  function withAddedStocks(report) {
    if (!report || report.session_date !== manifest.today) return report
    for (const s of addedFromUniverse()) {
      const row = figuresFor(s.ticker)?.row
      if (row && !report.tickers.some((t) => t.ticker === s.ticker)) report.tickers.push(row)
    }
    report.tickers.sort(
      (a, b) => (CATEGORY_ORDER[a.category] ?? 3) - (CATEGORY_ORDER[b.category] ?? 3) || a.ticker.localeCompare(b.ticker),
    )
    return report
  }

  async function getReport(day) {
    if (day !== 'latest' && !DATE.test(day)) throw new ApiError(400, "use a date like 2026-11-06, or 'latest'")
    const report = await data(day === 'latest' ? 'reports/latest.json' : `reports/${day}.json`)
    if (!report) throw new ApiError(404, day === 'latest' ? 'no reports yet' : `no report for ${day}`)
    return withAddedStocks(report)
  }

  async function listReports(params) {
    const limit = limitOf(params, 30, 365)
    const before = params.get('before')
    const status = params.get('status')
    if (before && !DATE.test(before)) throw new ApiError(400, 'before must be a date like 2026-11-06')
    if (status && status !== 'intraday' && status !== 'final') throw new ApiError(400, "status must be 'intraday' or 'final'")
    const { reports } = await data('reports.json')
    return {
      reports: reports
        .filter((r) => (!before || r.session_date < before) && (!status || r.status === status))
        .slice(0, limit),
    }
  }

  async function tickerHistory(ticker, params) {
    const limit = limitOf(params, 30, 365)
    const found = await data(`tickers/${ticker.toUpperCase()}/history.json`)
    return { ticker: ticker.toUpperCase(), history: found ? found.history.slice(0, limit) : [] }
  }

  async function tickerPrices(ticker, params) {
    const range = params.get('range') || '3mo'
    if (!['1mo', '3mo', '6mo', '1y'].includes(range)) throw new ApiError(400, 'range must be one of: 1mo, 3mo, 6mo, 1y')
    const found = await data(`tickers/${ticker.toUpperCase()}/prices-${range}.json`)
    if (!found || !found.prices.length) throw new ApiError(404, `no price data for ${ticker.toUpperCase()}`)
    return found
  }

  async function alerts(params) {
    const limit = limitOf(params, 10, 100)
    const found = await data('alerts.json')
    return { enabled: found.enabled, alerts: found.alerts.slice(0, limit) }
  }

  // ---------------------------------------------------------------------------
  // "Run update now": replays the recorded runs, one per press
  // ---------------------------------------------------------------------------

  function startRun() {
    if (state.run && state.run.state === 'running')
      throw new ApiError(409, 'A report is already being written. Its progress is shown below.')
    const wait = manifest.cooldown_seconds * 1000 - (now() - state.lastRunStart)
    if (wait > 0) {
      const seconds = Math.floor(wait / 1000) + 1
      throw new ApiError(429, `Please wait ${plural(seconds, 'second')} before requesting another report.`)
    }
    const step = state.step + 1
    const recorded = manifest.runs[step - 1]
    if (!recorded) return lastRunSkipped()
    setClock(Math.max(now(), RealDate.parse(recorded.started_at))) // the run happens at its sample time
    state.lastRunStart = now()
    const first = recorded.events[0].event
    state.run = JSON.parse(JSON.stringify(first.run))
    emit(first)
    for (const { at, event } of recorded.events.slice(1)) {
      setTimeout(() => {
        if (event.type === 'run_event') state.run.log.push(event.event)
        else if (event.type === 'run_finished') state.run = JSON.parse(JSON.stringify(event.run))
        else if (event.type === 'report_saved') state.step = step // the new report's files from now on
        emit(event)
      }, at * 1000)
    }
    return { run: JSON.parse(JSON.stringify(state.run)) }
  }

  function lastRunSkipped() {
    state.lastRunStart = now()
    state.run = { state: 'running', started_at: nowISO(), finished_at: null, log: [], result: null, error: null }
    emit({ type: 'run_started', run: JSON.parse(JSON.stringify(state.run)) })
    const skipped = {
      type: 'skipped',
      session_date: manifest.today,
      message: 'That was the last recorded update in this demo. Reload the page to start it again.',
    }
    setTimeout(() => {
      state.run.log.push(skipped)
      emit({ type: 'run_event', event: skipped })
      state.run = { ...state.run, state: 'finished', finished_at: nowISO(), result: skipped }
      emit({ type: 'run_finished', run: JSON.parse(JSON.stringify(state.run)) })
    }, 600)
    return { run: JSON.parse(JSON.stringify(state.run)) }
  }

  // ---------------------------------------------------------------------------
  // The events calendar, and its "Update now" (replays the recorded update, at the current time)
  // ---------------------------------------------------------------------------

  async function calendar(params) {
    const { calendar: cal, events } = await calendarEvents()
    const start = params.get('start')
    const end = params.get('end')
    for (const [name, value] of [['start', start], ['end', end]]) {
      if (value && !DATE.test(value)) throw new ApiError(400, `${name} must be a date like 2026-11-06`)
      if (value && !realDate(value)) throw new ApiError(400, "that isn't a real date")
    }
    const first = start || `${cal.today.slice(0, 8)}01`
    const last = end || addDays(first, 41)
    if (last < first) throw new ApiError(400, 'end must be on or after start')
    const span = (RealDate.parse(`${last}T00:00:00Z`) - RealDate.parse(`${first}T00:00:00Z`)) / 86400000
    if (span > cal.max_days) throw new ApiError(400, `ask for at most ${cal.max_days} days at a time`)
    return {
      today: cal.today,
      start: first,
      end: last,
      events: events
        .filter((e) => e.event_date >= first && e.event_date <= last)
        .map(({ _line, _line_company, ...e }) => e), // eslint-disable-line no-unused-vars
      last_scan: state.lastScan || cal.last_scan,
      scan: state.scan,
    }
  }

  // Moves every "..._at" time in a recorded event so the recording starts now
  function shiftTimes(value, by) {
    if (Array.isArray(value)) return value.map((v) => shiftTimes(v, by))
    if (!value || typeof value !== 'object') return value
    const out = {}
    for (const [key, v] of Object.entries(value)) {
      out[key] =
        key.endsWith('_at') && typeof v === 'string'
          ? new RealDate(RealDate.parse(v) + by).toISOString().replace(/\.\d{3}Z$/, 'Z')
          : shiftTimes(v, by)
    }
    return out
  }

  function startCalendarScan() {
    if (state.scan.state === 'running') throw new ApiError(409, 'The calendar is already being updated.')
    const wait = manifest.cooldown_seconds * 1000 - (now() - state.lastScanStart)
    if (wait > 0) {
      const seconds = Math.floor(wait / 1000) + 1
      throw new ApiError(429, `The calendar was just updated. Try again in ${plural(seconds, 'second')}.`)
    }
    state.lastScanStart = now()
    const recorded = manifest.calendar_scan
    const by = now() - RealDate.parse(recorded[0].event.scan.started_at)
    const events = recorded.map(({ at, event }) => ({ at, event: shiftTimes(event, by) }))
    state.scan = events[0].event.scan
    emit(events[0].event)
    for (const { at, event } of events.slice(1)) {
      setTimeout(() => {
        if (event.type === 'calendar_scan') {
          state.scan = event.scan
          if (event.scan.result) state.lastScan = event.scan.result // the calendar's "Updated" time
        }
        emit(event)
      }, at * 1000)
    }
    return { scan: state.scan }
  }

  // ---------------------------------------------------------------------------
  // Tracked stocks: the same rules and messages as watchlist.py
  // ---------------------------------------------------------------------------

  const shortName = (name) => name.replace(/^The\s+/i, '').replace(/[\s,]+(Inc\.?|Corporation|Company|Co\.?|Incorporated)$/i, '')

  async function watchlistView() {
    const sample = Object.fromEntries((await data('watchlist.json')).stocks.map((s) => [s.ticker, s]))
    const stocks = state.stocks.map((entry) => {
      if (sample[entry.ticker]) return { ...sample[entry.ticker], main: entry.main, benchmark: entry.benchmark }
      const u = universe[entry.ticker]
      return {
        ticker: entry.ticker,
        main: entry.main,
        benchmark: entry.benchmark,
        name: u.short_name || shortName(u.name),
        latest: figuresFor(entry.ticker)?.latest || null,
        next_event: state.eventsReady[entry.ticker] ? u.next_event || null : null,
      }
    })
    const ordered = [...stocks.filter((s) => s.main), ...stocks.filter((s) => !s.main)]
    return {
      stocks: ordered,
      tracked_count: ordered.length,
      main_count: ordered.filter((s) => s.main).length,
      max_tracked: manifest.limits.max_tracked,
      max_main: manifest.limits.max_main,
    }
  }

  const tickerPattern = () => new RegExp(`^(?:${manifest.limits.ticker_pattern})$`)
  const mainCount = () => state.stocks.filter((s) => s.main).length

  function canAdd(ticker, main) {
    const { max_tracked: maxTracked, max_main: maxMain } = manifest.limits
    if (state.stocks.some((s) => s.ticker === ticker)) throw new ApiError(409, `You're already tracking ${ticker}.`)
    if (state.stocks.length >= maxTracked)
      throw new ApiError(
        409,
        `You're tracking ${maxTracked} stocks, the most allowed. Remove one first, or raise MAX_TRACKED (see the guide).`,
      )
    if (main && mainCount() >= maxMain)
      throw new ApiError(409, `You already have ${maxMain} main stocks. Add it as tracked, or unstar one first.`)
  }

  async function addStock(body) {
    if (!body || typeof body !== 'object' || typeof body.ticker !== 'string')
      throw new ApiError(400, 'send {"ticker": "COST"}')
    const ticker = body.ticker.trim().toUpperCase()
    const main = Boolean(body.main)
    if (!tickerPattern().test(ticker))
      throw new ApiError(400, "That isn't a US ticker (letters, numbers and - only, like AAPL or BRK-B).")
    canAdd(ticker, main)
    const u = universe[ticker]
    if (!u) throw new ApiError(400, `Yahoo Finance doesn't know ${ticker}. Check the spelling, or search by company name.`)
    const type = manifest.limits.allowed_types[u.quote_type]
    if (!type)
      throw new ApiError(
        400,
        `${ticker} is a ${u.quote_type.toLowerCase().replaceAll('_', ' ')}. Only stocks and ETFs can be tracked.`,
      )
    await sleep(250) // as long as a quick check with Yahoo takes
    canAdd(ticker, main)
    state.stocks.push({ ticker, main, benchmark: null })
    state.addedAt[ticker] = state.step
    emit({ type: 'watchlist_changed' })
    setTimeout(() => {
      state.eventsReady[ticker] = true // its earnings and dividend dates, "from Yahoo"
      emit({ type: 'calendar_updated', scan: null })
    }, 700)
    return { stock: { ticker, name: u.name, type, main }, watchlist: await watchlistView() }
  }

  async function setMain(ticker, body) {
    if (!body || typeof body.main !== 'boolean') throw new ApiError(400, 'send {"main": true} or {"main": false}')
    const entry = state.stocks.find((s) => s.ticker === ticker)
    if (!entry) throw new ApiError(404, `${ticker} isn't on your list.`)
    if (body.main && !entry.main && mainCount() >= manifest.limits.max_main)
      throw new ApiError(409, `You already have ${manifest.limits.max_main} main stocks. Unstar one first.`)
    entry.main = body.main
    emit({ type: 'watchlist_changed' })
    return watchlistView()
  }

  async function removeStock(ticker) {
    if (!state.stocks.some((s) => s.ticker === ticker)) throw new ApiError(404, `${ticker} isn't on your list.`)
    state.stocks = state.stocks.filter((s) => s.ticker !== ticker)
    delete state.addedAt[ticker]
    delete state.eventsReady[ticker]
    emit({ type: 'watchlist_changed' })
    return watchlistView()
  }

  // Yahoo Finance's search, over the stocks the sample knows: ticker matches first, then names
  function searchStocks(params) {
    const raw = (params.get('q') || '').trim()
    if (!raw) throw new ApiError(400, 'q is required')
    if (raw.length > 60) throw new ApiError(400, 'keep searches under 60 characters')
    const query = raw.split(/\s+/).join(' ').slice(0, 60)
    const q = query.toLowerCase()
    const ranked = []
    manifest.universe.forEach((u, order) => {
      const sym = u.ticker.toLowerCase()
      const low = u.name.toLowerCase()
      const nameMatch = low.replaceAll(',', ' ').split(/\s+/).some((w) => w.startsWith(q)) || low.includes(q)
      const rank = sym === q ? 0 : sym.startsWith(q) ? 1 : nameMatch ? 2 : null
      if (rank !== null) ranked.push({ rank, order, u })
    })
    ranked.sort((a, b) => a.rank - b.rank || a.order - b.order)
    const tracked = new Set(state.stocks.map((s) => s.ticker))
    const pattern = tickerPattern()
    const results = ranked
      .slice(0, 15)
      .map((r) => r.u)
      .filter((u) => manifest.limits.allowed_types[u.quote_type] && pattern.test(u.ticker))
      .slice(0, 8)
      .map((u) => ({
        ticker: u.ticker,
        name: u.name,
        type: manifest.limits.allowed_types[u.quote_type],
        exchange: u.exchange,
        tracked: tracked.has(u.ticker),
      }))
    return { query, results }
  }

  // ---------------------------------------------------------------------------
  // Search: keywords (a simple BM25) plus the test environment's topic stand-in for meaning
  // ---------------------------------------------------------------------------

  const WORD = /[A-Za-z0-9][A-Za-z0-9.\-']*/g
  const SUFFIXES = ['ations', 'ation', 'ings', 'ing', 'edly', 'ed', 'ly', 'es', 's']

  function stem(word) {
    let w = word.toLowerCase()
    if (w.length <= 3 || /^\d+$/.test(w)) return w
    if (w.endsWith('ies') && w.length > 4) return `${w.slice(0, -3)}y`
    for (const suffix of SUFFIXES) {
      if (w.endsWith(suffix) && w.length - suffix.length >= 3) {
        w = w.slice(0, -suffix.length)
        if ((suffix === 'ed' || suffix === 'ing') && /([^aeioulsz])\1$/.test(w)) w = w.slice(0, -1) // flagged -> flag
        break
      }
    }
    if (w.endsWith('e') && w.length > 4) w = w.slice(0, -1)
    return w
  }

  const tokens = (text) => (text.toLowerCase().match(/[a-z0-9]+/g) || []).map(stem)
  const indexes = new Map()

  async function searchIndex() {
    const v = versionOf('search/passages.json')
    if (!indexes.has(v)) {
      const { passages } = await data('search/passages.json')
      const topics = Object.values(manifest.search.topics)
      const docs = passages.map((p) => {
        const full = `${p.heading} ${p.text}`
        const terms = {}
        const list = tokens(full)
        for (const t of list) terms[t] = (terms[t] || 0) + 1
        return { p, terms, length: list.length, vector: topicVector(p.text, topics, 0.1) }
      })
      const df = {}
      for (const d of docs) for (const t of Object.keys(d.terms)) df[t] = (df[t] || 0) + 1
      const avg = docs.reduce((sum, d) => sum + d.length, 0) / Math.max(1, docs.length)
      indexes.set(v, { docs, df, avg, topics })
    }
    return indexes.get(v)
  }

  function topicVector(text, topics, bias) {
    const low = text.toLowerCase()
    const v = [...topics.map((phrases) => 3 * phrases.filter((p) => low.includes(p)).length), bias]
    const norm = Math.hypot(...v)
    return norm ? v.map((x) => x / norm) : v
  }

  async function search(query, limit = 10, { ticker, since, until } = {}) {
    const s = manifest.search
    const words = (query.match(WORD) || []).slice(0, s.max_query_words)
    const result = { query, mode: 'hybrid', note: null, terms: words, results: [] }
    if (!words.length) return { ...result, mode: 'keyword' }
    const { docs, df, avg, topics } = await searchIndex()
    const n = docs.length
    const allowed = docs.filter(
      ({ p }) =>
        (!ticker || p.ticker === ticker.toUpperCase()) &&
        (!since || p.session_date >= since) &&
        (!until || p.session_date <= until),
    )
    const groups = words.map((w) => tokens(w)).filter((g) => g.length)
    const keyword = allowed
      .map((d) => {
        let score = 0
        for (const group of groups) {
          if (!group.every((t) => d.terms[t])) continue
          for (const t of group) {
            const idf = Math.max(1e-6, Math.log((n - df[t] + 0.5) / (df[t] + 0.5)))
            const tf = d.terms[t]
            score += (idf * tf * 2.2) / (tf + 1.2 * (0.25 + (0.75 * d.length) / avg))
          }
        }
        return { d, score }
      })
      .filter((x) => x.score > 0)
      .sort((a, b) => b.score - a.score || a.d.p.id - b.d.p.id)
      .slice(0, limit * 3)
      .map((x) => x.d)
    const q = topicVector(query, topics, 0)
    const scored = allowed.map((d) => ({ d, score: d.vector.reduce((sum, x, i) => sum + x * q[i], 0) }))
    const best = Math.max(0, ...scored.map((x) => x.score))
    const floor = Math.max(s.min_similarity, best * s.meaning_cutoff)
    const meaning = scored
      .filter((x) => x.score >= floor)
      .sort((a, b) => b.score - a.score || a.d.p.id - b.d.p.id)
      .slice(0, limit * 3)
      .map((x) => x.d)
    const fused = new Map()
    for (const [ranking, label] of [[keyword, 'keywords'], [meaning, 'meaning']]) {
      ranking.forEach((d, rank) => {
        const entry = fused.get(d) || { score: 0, matched_by: [] }
        entry.score += 1 / (s.rrf_k + rank + 1)
        entry.matched_by.push(label)
        fused.set(d, entry)
      })
    }
    result.results = [...fused.entries()]
      .sort((a, b) => b[1].score - a[1].score)
      .slice(0, limit)
      .map(([d, entry]) => ({
        session_date: d.p.session_date,
        status: d.p.status,
        ticker: d.p.ticker,
        heading: d.p.heading,
        text: d.p.text.split('\n').slice(1).join('\n'), // without the title line
        score: Math.round(entry.score * 1e5) / 1e5,
        matched_by: entry.matched_by,
      }))
    return result
  }

  async function searchEndpoint(params) {
    const q = (params.get('q') || '').trim()
    const limit = limitOf(params, 12, 50)
    if (!q) throw new ApiError(400, 'q is required')
    if (q.length > manifest.ask.max_question_chars)
      throw new ApiError(400, `keep searches under ${manifest.ask.max_question_chars} characters`)
    for (const name of ['since', 'until'])
      if (params.get(name) && !DATE.test(params.get(name))) throw new ApiError(400, `${name} must be a date like 2026-11-06`)
    return search(q, limit, { ticker: params.get('ticker'), since: params.get('since'), until: params.get('until') })
  }

  // ---------------------------------------------------------------------------
  // Ask: an answer built straight from the sample data (as the test environment's offline answers are)
  // ---------------------------------------------------------------------------

  async function flaggedDays(ticker) {
    const found = await data(`tickers/${ticker}/history.json`)
    return found ? found.history.filter((h) => h.category === 'flagged') : []
  }

  async function upcoming(start, days, tickers) {
    const { events } = await calendarEvents()
    const last = addDays(start, days)
    return events.filter((e) => e.event_date >= start && e.event_date <= last && (!tickers || tickers.includes(e.ticker)))
  }

  async function answer(question) {
    const a = manifest.ask
    const { tickers: known } = await data('known_tickers.json')
    const words = new Set((question.match(/[A-Za-z][A-Za-z.\-]{0,9}/g) || []).map((w) => w.toUpperCase()))
    const tickers = known.filter((t) => words.has(t)).sort()
    const today = manifest.today
    const lines = ['*Demo answer, built from the sample data without Claude.*', '']
    const days = new Set((await data('reports.json')).reports.slice(0, a.recent_reports).map((r) => r.session_date))
    for (const t of tickers) {
      const rows = await flaggedDays(t)
      rows.slice(0, a.flagged_reports_per_ticker).forEach((r) => days.add(r.session_date))
      if (rows.length) {
        const recent = rows.slice(0, 5).map((r) => `${r.session_date} (${signed(r.return_1d_pct)}%)`).join(', ')
        lines.push(`- **${t}** was flagged on ${plural(rows.length, 'day')}. Most recent: ${recent}.`)
      } else {
        lines.push(`- **${t}** hasn't been flagged in the saved reports.`)
      }
      const ahead = await upcoming(today, a.calendar_days, [t])
      if (ahead.length) lines.push(`  Next on the calendar: ${ahead[0]._line} (calendar).`)
    }
    if (!tickers.length) {
      const counts = await Promise.all(known.map(async (t) => [t, (await flaggedDays(t)).length]))
      const top = counts
        .filter(([, n]) => n > 0)
        .sort((x, y) => y[1] - x[1] || x[0].localeCompare(y[0]))
        .slice(0, 3)
      lines.push(
        `Most-flagged tickers in the saved reports: ${top.map(([t, n]) => `**${t}** (${n} days)`).join(', ') || 'none yet'}.`,
      )
      const ahead = await upcoming(today, 7)
      if (ahead.length) lines.push('', 'Next on the calendar (calendar):', ...ahead.slice(0, 3).map((e) => `- ${e._line_company}`))
    }
    const passages = (await search(question, a.passages)).results
    passages.forEach((p) => days.add(p.session_date))
    if (passages.length) {
      lines.push('', 'Most relevant passages:')
      for (const p of passages.slice(0, 3)) lines.push(`- ${p.session_date}: ${p.heading} (matched by ${p.matched_by.join(' and ')})`)
    }
    return { text: lines.join('\n'), used: [...days].sort().reverse() }
  }

  function askEndpoint(body) {
    const question = body && typeof body.question === 'string' ? body.question : null
    if (!question || !question.trim()) throw new ApiError(400, 'question is required')
    if (question.length > manifest.ask.max_question_chars)
      throw new ApiError(400, `keep questions under ${manifest.ask.max_question_chars} characters`)
    const encoder = new TextEncoder()
    const line = (event) => encoder.encode(`${JSON.stringify(event)}\n`)
    const stream = new ReadableStream({
      async start(controller) {
        try {
          const { text, used } = await answer(question.trim())
          for (const word of text.split(' ')) {
            await sleep(25)
            controller.enqueue(line({ type: 'delta', text: `${word} ` }))
          }
          controller.enqueue(line({ type: 'done', answer: text, reports_used: used, cost_usd: 0 }))
        } catch (e) {
          controller.enqueue(line({ type: 'error', error: String(e.message || e) }))
        }
        controller.close()
      },
    })
    return new Response(stream, { status: 200, headers: { 'Content-Type': 'application/x-ndjson' } })
  }

  // ---------------------------------------------------------------------------
  // Routing: the same paths as api.py
  // ---------------------------------------------------------------------------

  function bodyOf(init) {
    try {
      return init && typeof init.body === 'string' ? JSON.parse(init.body) : null
    } catch {
      return null
    }
  }

  async function route(url, init) {
    await ready
    const method = ((init && init.method) || 'GET').toUpperCase()
    const path = url.pathname.replace(/\/+$/, '')
    const params = url.searchParams
    const body = bodyOf(init)
    let m
    if (method === 'GET') {
      if (path === '/api/health') return { status: 'ok', reports: (await data('reports.json')).reports.length }
      if (path === '/api/reports') return listReports(params)
      if ((m = path.match(/^\/api\/reports\/([^/]+)$/))) return getReport(decodeURIComponent(m[1]))
      if ((m = path.match(/^\/api\/tickers\/([^/]+)\/history$/))) return tickerHistory(decodeURIComponent(m[1]), params)
      if ((m = path.match(/^\/api\/tickers\/([^/]+)\/prices$/))) return tickerPrices(decodeURIComponent(m[1]), params)
      if (path === '/api/runs/current') return { run: state.run }
      if (path === '/api/search') return searchEndpoint(params)
      if (path === '/api/alerts') return alerts(params)
      if (path === '/api/watchlist') return watchlistView()
      if (path === '/api/stocks/search') return searchStocks(params)
      if (path === '/api/calendar') return calendar(params)
    } else if (method === 'POST') {
      if (path === '/api/runs') return [202, startRun()]
      if (path === '/api/ask') return askEndpoint(body)
      if (path === '/api/calendar/scan') return [202, startCalendarScan()]
      if (path === '/api/watchlist') return [201, await addStock(body)]
      if ((m = path.match(/^\/api\/watchlist\/([^/]+)\/remove$/))) return removeStock(decodeURIComponent(m[1]).toUpperCase())
      if ((m = path.match(/^\/api\/watchlist\/([^/]+)$/))) return setMain(decodeURIComponent(m[1]).toUpperCase(), body)
    }
    throw new ApiError(404, 'not found')
  }

  window.fetch = async function demoFetch(input, init) {
    const raw = typeof input === 'string' ? input : input instanceof Request ? input.url : String(input)
    const url = new URL(raw, window.location.href)
    if (url.origin !== window.location.origin || !url.pathname.startsWith('/api/')) return realFetch(input, init)
    try {
      const result = await route(url, init)
      if (result instanceof Response) return result
      return Array.isArray(result) ? json(result[1], result[0]) : json(result)
    } catch (e) {
      if (e instanceof ApiError) return json({ error: e.message }, e.status)
      return json({ error: `demo: ${e.message || e}` }, 500)
    }
  }

  // ---------------------------------------------------------------------------
  // The banner
  // ---------------------------------------------------------------------------

  function addBanner() {
    const style = document.createElement('style')
    style.textContent = `
      .demo-banner { padding: 8px 16px; text-align: center; font-size: 0.875rem; line-height: 1.45;
        background: var(--live-bg, #fef3c7); color: var(--text, #1c2430); border-bottom: 1px solid var(--border, #e2e6eb); }
      .demo-banner a { color: var(--accent, #2456d6); font-weight: 600; white-space: nowrap; }`
    document.head.appendChild(style)
    const bar = document.createElement('div')
    bar.className = 'demo-banner'
    bar.setAttribute('role', 'note')
    const strong = document.createElement('strong')
    strong.textContent = 'Live demo with sample data.'
    bar.append(
      strong,
      ' Prices, news, runs and answers are simulated, and no AI is called. Changes stay in this tab until you reload.',
    )
    if (/^https:\/\/github\.com\/[\w.-]+\/[\w.-]+$/.test(config.repo_url || '')) {
      const link = document.createElement('a')
      link.href = config.repo_url
      link.textContent = 'See the code on GitHub'
      bar.append(' ', link)
    }
    document.body.prepend(bar)
  }

  if (document.body) addBanner()
  else document.addEventListener('DOMContentLoaded', addBanner)
})()
```

### test_demo.py

```python
"""Checks for the live demo: the sample data it exports, the safety checks, and publishing.
Run from this folder:  pytest -v   (no internet, npm, GitHub account or keys needed)
"""

import hashlib
import json
import subprocess
import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import demo  # noqa: E402  (turns off __pycache__ folders before anything else loads)

END = date(2026, 11, 6)
TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]
SKIP = {".venv", "node_modules", ".git", "__pycache__", ".pytest_cache", "data", "frontend-dist", "dist"}


def snapshot(folder: Path) -> dict:
    """Every file in a folder (except installed packages, databases and build output), with its contents' hash."""
    found = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if SKIP & set(rel.parts) or path.name.startswith(("reports.db", "search.db")):
            continue
        found[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "folder"
    return found


MAIN_BEFORE, TESTENV_BEFORE = snapshot(demo.MAIN), snapshot(demo.TESTENV)


@pytest.fixture(scope="module")
def exported(tmp_path_factory):
    """One export (two recorded runs, to keep it quick), shared by the checks below."""
    out = tmp_path_factory.mktemp("site") / demo.DATA
    manifest = demo.export(out, end=END, tickers=TICKERS, steps=2, repo_url="https://github.com/someone/market-agent")
    return out, manifest


def read(out: Path, step: int, name: str):
    return json.loads((out / str(step) / name).read_text())


def newest(out: Path, manifest: dict, name: str, step: int):
    """A file as the demo serves it after `step` recorded runs."""
    version = max(v for v in manifest["versions"][name] if v <= step)
    return read(out, version, name)


# ---------------------------------------------------------------------------
# The exported sample
# ---------------------------------------------------------------------------

def test_the_sample_starts_just_after_the_latest_update(exported):
    out, manifest = exported
    assert manifest["today"] == "2026-11-06" and manifest["start"] == "2026-11-06T17:33:00Z"  # 12:33pm ET
    assert manifest["sample"] == {"days": 44, "first_day": "2026-09-08"}
    assert manifest["repo_url"] == "https://github.com/someone/market-agent"
    latest = read(out, 0, "reports/latest.json")
    assert latest["as_of"] == "2026-11-06 12:30 ET" and latest["status"] == "intraday"
    listing = read(out, 0, "reports.json")["reports"]
    assert all((out / "0" / f"reports/{r['session_date']}.json").is_file() for r in listing)
    for t in TICKERS:
        assert len(read(out, 0, f"tickers/{t}/history.json")["history"]) == 44
        assert [len(read(out, 0, f"tickers/{t}/prices-{p}.json")["prices"]) for p in ("1mo", "3mo", "6mo", "1y")] == [21, 63, 126, 252]
    assert len(read(out, 0, "search/passages.json")["passages"]) >= 44
    calendar = read(out, 0, "calendar.json")
    assert calendar["today"] == "2026-11-06" and calendar["events"]
    assert all(e["_line"] and e["_line_company"] for e in calendar["events"])
    # Times belong to the sample, not to the day the demo was built: today's calendar update was at 9:35am ET
    assert calendar["last_scan"]["started_at"] == "2026-11-06T14:35:00Z"


def test_recorded_runs_move_the_day_on(exported):
    out, manifest = exported
    assert [r["started_at"] for r in manifest["runs"]] == ["2026-11-06T17:45:40Z", "2026-11-06T18:00:40Z"]
    for run in manifest["runs"]:
        kinds = [e["event"]["type"] for e in run["events"]]
        assert kinds[0] == "run_started" and "run_finished" in kinds and kinds.count("report_saved") == 1
        saved = next(i for i, e in enumerate(run["events"]) if e["event"].get("event", {}).get("type") == "saved")
        assert kinds.index("report_saved") > saved  # the new report shows once the run says it's saved
    assert [newest(out, manifest, "reports/latest.json", k)["as_of"] for k in (0, 1, 2)] == [
        "2026-11-06 12:30 ET", "2026-11-06 12:45 ET", "2026-11-06 13:00 ET"]
    assert manifest["versions"]["reports/latest.json"] == [0, 1, 2]
    assert manifest["versions"]["reports/2026-11-05.json"] == [0]  # only what changed is stored again
    sent = newest(out, manifest, "alerts.json", 1)["alerts"]
    assert sent[0]["ticker"] == "MSFT" and sent[0]["sent_at"].startswith("2026-11-06T17:45")


def test_the_calendar_update_is_recorded(exported):
    _, manifest = exported
    events = manifest["calendar_scan"]
    assert events[0]["event"]["scan"]["state"] == "running"
    messages = [e["event"]["scan"]["message"] for e in events if e["event"]["type"] == "calendar_scan"]
    assert "Checking AAPL's calendar and news" in messages
    finished = [e["event"]["scan"] for e in events if e["event"]["type"] == "calendar_scan" and e["event"]["scan"]["result"]]
    assert finished and finished[-1]["result"]["trigger"] == "manual" and finished[-1]["result"]["cost_usd"] == 0


def test_stocks_a_visitor_can_add(exported):
    out, manifest = exported
    universe = {u["ticker"]: u for u in manifest["universe"]}
    cost = universe["COST"]
    assert cost["trackable"] and not cost["in_sample"] and cost["short_name"] == "Costco Wholesale"
    assert cost["next_event"]["line"] == "Mon Jan 4: Earnings report" and cost["events"]
    assert len(cost["steps"]) == 2 and cost["steps"][0]["latest"]["price"] > 0 and cost["steps"][0]["row"]["ticker"] == "COST"
    assert len(read(out, 0, "tickers/COST/prices-1y.json")["prices"]) == 252
    assert manifest["versions"]["tickers/COST/prices-1y.json"] == [0]
    assert not universe["BTC-USD"]["trackable"] and not universe["COST.MX"]["trackable"]
    assert all(universe[t]["in_sample"] for t in TICKERS)  # removing a sample stock and adding it back works too


def test_the_demo_uses_the_programs_own_settings(exported):
    _, manifest = exported
    testenv = demo.load_testenv()
    import ask
    import search_index
    import watchlist
    assert manifest["search"]["topics"] == testenv.SIMULATED_TOPICS
    assert manifest["search"]["meaning_cutoff"] == search_index.MEANING_CUTOFF
    assert manifest["ask"]["calendar_days"] == ask.CALENDAR_DAYS
    assert manifest["limits"]["max_tracked"] == watchlist.MAX_TRACKED and manifest["limits"]["max_main"] == watchlist.MAX_MAIN
    assert manifest["limits"]["ticker_pattern"] == watchlist.TICKER.pattern


def test_exporting_leaves_your_projects_alone(exported):
    assert snapshot(demo.MAIN) == MAIN_BEFORE
    assert snapshot(demo.TESTENV) == TESTENV_BEFORE
    assert not demo.WORK.exists()  # the scratch databases are deleted


# ---------------------------------------------------------------------------
# Building, checking and publishing the site
# ---------------------------------------------------------------------------

VITE_INDEX = """<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <title>Market Analyst</title>
    <script type="module" crossorigin src="./assets/index-abc123.js"></script>
    <link rel="stylesheet" crossorigin href="./assets/index-def456.css">
  </head>
  <body><div id="root"></div></body>
</html>"""


def test_the_shim_loads_before_the_app():
    html = demo.add_shim(VITE_INDEX)
    assert html.index("demo-config.js") < html.index("demo-shim.js") < html.index("assets/index-abc123.js")
    assert "<title>Market Analyst · live demo</title>" in html
    assert demo.add_shim(html) == html  # running it twice changes nothing
    with pytest.raises(ValueError):
        demo.add_shim("<p>not the app</p>")


def make_site(folder: Path) -> Path:
    site = folder / "site"
    (site / demo.DATA).mkdir(parents=True)
    (site / "index.html").write_text(demo.add_shim(VITE_INDEX))
    (site / demo.DATA / "manifest.json").write_text('{"version": 1}')
    demo.finish_site(site, {"start": "2026-11-06T17:33:00Z", "today": "2026-11-06", "repo_url": ""})
    return site


def test_finishing_the_site(tmp_path):
    site = make_site(tmp_path)
    config = (site / "demo-config.js").read_text()
    assert 'window.DEMO_CONFIG = {"data": "demo-data", "start": "2026-11-06T17:33:00Z"' in config
    assert (site / "demo-shim.js").read_text() == demo.SHIM.read_text()
    assert (site / ".nojekyll").is_file()  # GitHub Pages serves every file as it is
    assert demo.check_site(site) == []


@pytest.mark.parametrize("name, content, problem", [
    ("demo-data/0/oops.json", '{"key": "sk-ant-api03-abcdefghijklmnop"}', "looks like a key"),
    ("notes.txt", "https://discord.com/api/webhooks/123456/abc", "looks like a key or webhook"),
    ("demo-data/0/where.json", f'"{demo.MAIN}"', "mentions a folder on your computer"),
])
def test_check_finds_what_shouldnt_be_published(tmp_path, name, content, problem):
    site = make_site(tmp_path)
    (site / name).parent.mkdir(parents=True, exist_ok=True)
    (site / name).write_text(content)
    assert any(problem in p for p in demo.check_site(site))


def test_check_finds_absolute_paths_and_missing_files(tmp_path):
    site = make_site(tmp_path)
    (site / "index.html").write_text(demo.add_shim(VITE_INDEX.replace("./assets/", "/assets/")))
    (site / "demo-shim.js").unlink()
    problems = demo.check_site(site)
    assert any("absolute paths" in p for p in problems) and any("demo-shim.js is missing" in p for p in problems)


def git(*args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def test_publish_puts_only_the_site_on_its_own_branch(tmp_path):
    remote = tmp_path / "remote.git"
    git("init", "-q", "--bare", str(remote), cwd=tmp_path)
    site = make_site(tmp_path)

    demo.publish_site(site, str(remote))
    (site / "extra.txt").write_text("a second publish")
    demo.publish_site(site, str(remote))

    published = git("ls-tree", "-r", "--name-only", "gh-pages", cwd=remote).splitlines()
    assert sorted(published) == sorted(str(p.relative_to(site)) for p in site.rglob("*") if p.is_file())
    assert git("rev-list", "--count", "gh-pages", cwd=remote) == "1"  # replaced, not piled up
    assert git("branch", "--list", cwd=remote) == "gh-pages"  # no other branch was touched or made
    with pytest.raises(ValueError, match="branch of its own"):
        demo.publish_site(site, str(remote), branch="main")
    (site / "leak.txt").write_text("sk-ant-api03-abcdefghijklmnop")
    with pytest.raises(ValueError, match="Not ready to publish"):
        demo.publish_site(site, str(remote))


@pytest.mark.parametrize("remote, page, address", [
    ("https://github.com/someone/market-agent.git", "https://github.com/someone/market-agent", "https://someone.github.io/market-agent/"),
    ("git@github.com:Someone/market-agent.git", "https://github.com/Someone/market-agent", "https://someone.github.io/market-agent/"),
    ("https://gitlab.com/someone/market-agent.git", "", ""),
])
def test_github_addresses(remote, page, address):
    assert demo.repo_page(remote) == page and demo.pages_address(remote) == address
```
