# Market Analyst Agent: The App in a Container

This guide packages the app as a **Docker image**: one file-like bundle that holds the app and everything it needs. Anyone with Docker can then download it and run it on their own computer with one command, and it runs the same way on Windows, macOS and Linux.

| | |
|---|---|
| **What people do** | `docker run --rm -p 127.0.0.1:8100:8100 ghcr.io/YOU/YOUR-REPOSITORY`, then open http://localhost:8100 |
| **The demo (the default)** | Your real app over the test environment's simulated sample. No AI is called, no keys, no account, and once it is downloaded, no internet |
| **Real mode** | The same image runs the real app for anyone who gives it their own Anthropic key. Their reports and watchlist stay in a Docker volume on their computer, and the scheduled runs are built in |
| **Updating** | After you add a feature: `python container.py publish`. People get it with `docker pull` |
| **Your program** | One line changes in `market_tools.py` (in this project, `events.py` and `stories.py` also changed: see below). Everything else is a new folder next to `market-agent/` and `market-agent-testenv/`, which only reads them |

This builds on `market-agent-test-enviro.md` (the sample data and the simulated services) and `market-agent-filings.md` (the newest feature).

**Read section 15 before you publish.** The computer this was written on could not download from Docker Hub, PyPI or npm, so parts of the build were tested with stand-ins. Section 15 says exactly which parts, and how to check them on your computer.

**This project's version.** This copy describes the container as built for this project, whose main folder is `AI-Market-Analysis-Agent/` and holds the guides and test notes too. Where it differs from the guide as first written, it says *This project:*. In short:

- The container's programs are told where the main folder is with `MARKET_AGENT_DIR`, as the test environment is (section 4.1).
- Only prompt files (`*_prompt.md`) go into the image, not every `.md` file: the guides quote example keys, and the notes name folders on your computer (section 5).
- `run_brief.py` takes `ANTHROPIC_API_KEY` out of the environment and gives the agent `MARKET_AGENT_ANTHROPIC_KEY`. In the container the key goes under both names, and either name is accepted (section 11.1).
- This project's own after-close report is part of the container's schedule, so it is off unless `SCHEDULE=on` (section 11.3).
- A `.env` file is never read (section 12).
- `events.py` and `stories.py` now give Claude the project's key too, like every other Claude call. Without that, the calendar update and story checks couldn't run in a container (BUG-18 in `test-case-reporting.md`).

---

## Contents

1. [What you get](#1-what-you-get)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Create the container folder](#4-step-1-create-the-container-folder)
5. [Step 2: Build the image](#5-step-2-build-the-image)
6. [Step 3: Test the image](#6-step-3-test-the-image)
7. [Step 4: Try it](#7-step-4-try-it)
8. [Step 5: Publish it](#8-step-5-publish-it)
9. [Step 6: Tell people how to run it](#9-step-6-tell-people-how-to-run-it)
10. [Updating after you add a feature](#10-updating-after-you-add-a-feature)
11. [Real mode](#11-real-mode)
12. [Settings](#12-settings)
13. [What's real and what's simulated](#13-whats-real-and-whats-simulated)
14. [Test it](#14-test-it)
15. [What was tested, and what you need to check](#15-what-was-tested-and-what-you-need-to-check)
16. [Costs](#16-costs)
17. [Security and privacy](#17-security-and-privacy)
18. [Troubleshooting](#18-troubleshooting)
19. [Sources](#19-sources)
20. [Appendix A: the container folder](#appendix-a-the-container-folder)
21. [Appendix B: the changed file in market-agent](#appendix-b-the-changed-file-in-market-agent)

---

## 1. What you get

Someone who has never seen your project types one command and gets this at http://localhost:8100 (screenshot: `container-preview.png`):

```
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Demo with sample data. Prices, news, company filings, runs and answers are simulated, and   │
│ no AI is called. Everything starts again when the container restarts. Version 2026.11.12    │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
 Market Analyst   Today  Previous days  Calendar  Stocks  Follow-through  Story updates  Filings  ● Live

 LATEST REPORT                                                  REQUEST A FRESH REPORT
 Intraday · updating   As of 2026-11-12 12:30 ET · update 2     [ Run update now ]
 AAPL  quiet    76.64   -0.13%                                  COMING UP
 MSFT  flagged 323.91   +4.96%  3.0  1.72×  +5.09 pts vs XLK    Fri, Nov 13  NVIDIA Product launch event
 NVDA  quiet    81.88   +0.31%                                  ASK ABOUT YOUR REPORTS
```

Everything works, because it is your real program running, not a recording:

- **Run update now** writes a new intraday update every time (12:45, 13:00, 13:15...), with the same progress steps as a real run. The agent is simulated, so it costs nothing.
- **Ask** streams an answer built from the sample reports.
- **Search**, **charts**, the **calendar**, the **Stocks tab**, **Follow-through**, **Story updates** and **Filings** all work, with their buttons.
- **The sample's "today" is always current.** It is made when the container starts: two months of reports ending on the latest trading day.
- **A restart starts again.** Whatever a visitor adds or changes is gone when the container is removed, so everyone gets the same clean demo.

### How this differs from the GitHub Pages demo

You now have two demos, and both are worth keeping.

| | GitHub Pages demo (`market-agent-demo.md`) | Container (this guide) |
|---|---|---|
| To try it | Click a link | Install Docker, run one command |
| What runs | Recorded answers, replayed in the browser | Your real Python program, with its real database |
| Run update now | 4 recorded runs | As many as you like |
| Internet | Needed (it's a website) | Only for the first download |
| Can become the real app | No | Yes: real mode, with the person's own key |

---

## 2. How it works

```
 market-agent/ ───────────┐
 market-agent-testenv/ ───┤  (only read)
                          ▼
 python container.py build
   1. copies the code, and only the code, into market-agent-container/.build/
   2. checks the copy for keys, webhooks, databases and paths on your computer
   3. docker build, from that copy:
        Node stage     builds your React app (npm run build)
        Python stage   installs requirements.txt, adds the code and start.py
                          ▼
                 image  market-agent:local
                          ▼
 python container.py test      runs it with networking off; its self-test must pass in both modes
 python container.py publish   builds it for Intel/AMD and ARM computers and sends it to ghcr.io
                          ▼
 anyone:   docker run --rm -p 127.0.0.1:8100:8100 ghcr.io/you/your-repository
```

Inside the container, one small program, `start.py`, decides what to run:

| | Demo (`MODE=demo`, the default) | Real (`MODE=real`) |
|---|---|---|
| Data | A fresh sample, made at start by the test environment's own `seed_database` | `/data`: `reports.db`, `search.db`, `watchlist.txt` |
| App | The test environment's `make_app`: your real API with Claude, Yahoo, Voyage, Discord and the SEC replaced by simulations | Your real API, `api.create_app()` |
| Keys | Ignored, even if given | `ANTHROPIC_API_KEY` and the others, given when it starts |
| Schedule | None | Built in, if switched on (section 11) |

Because the demo is the test environment, **whatever you add to the test environment shows up in the container the next time you build it.** That is what makes updating one command (section 10).

---

## 3. Before you start

- [ ] The test environment is set up and its tests pass: `pytest -v` in `market-agent-testenv/` gives `40 passed`
- [ ] The main tests pass: `pytest -v` in `market-agent/` gives `415 passed, 4 skipped` (*this project:* `663 passed, 5 skipped, 1 xfailed`)
- [ ] The frontend builds on your computer: `npm run build` in `market-agent/frontend/` works (so `package.json` and `package-lock.json` are there)
- [ ] **Docker Desktop** is installed and running. Get it from [docker.com/products/docker-desktop](https://www.docker.com/products/docker-desktop/). Check with:

  ```bash
  docker --version
  docker info
  ```

  If `docker info` ends with an error, Docker Desktop isn't running yet: start it and wait for its icon to settle.
- [ ] To publish: the project is on GitHub (`market-agent-demo.md`, step 4). The image goes to GitHub's own image store, `ghcr.io`, under your account.

**About Docker Desktop's licence.** Docker's licence page says Docker Desktop is free for personal use, education, non-commercial open source projects, and small businesses (fewer than 250 employees and less than $10 million in annual revenue); larger companies need a paid subscription. That applies to the people who run your image too, so say so if you share it with colleagues at a large firm. On Linux, Docker Engine (without Desktop) is an alternative. Check the page yourself before relying on this: [Docker Desktop license agreement](https://docs.docker.com/subscription/desktop-license/).

---

## 4. Step 1: Create the container folder

### 4.1 The folder

Create `market-agent-container` next to the other folders:

```
your-projects/
├── market-agent/              your program (one line changes: 4.2)
├── market-agent-testenv/      the test environment (not changed)
├── market-agent-demo/         the GitHub Pages demo (not changed)
└── market-agent-container/    new
    ├── Dockerfile             the recipe for the image
    ├── start.py               what runs inside the container
    ├── container.py           what you run: build, test, run, publish
    ├── demo-banner.js         the demo's banner
    └── test_container.py      the tests
```

Copy the five files from [Appendix A](#appendix-a-the-container-folder). `Dockerfile` has no ending: name it exactly that.

*This project:* the folders are `C:\shaun\AI-Market-Analysis-Agent`, `C:\shaun\market-agent-testenv` and `C:\shaun\market-agent-container`. The main folder isn't called `market-agent`, so in each terminal you run `container.py` or `pytest` from, say where it is, as for the test environment:

```powershell
$env:MARKET_AGENT_DIR = "C:\shaun\AI-Market-Analysis-Agent"
```

The image doesn't need this: inside it, the folders are called `market-agent` and `market-agent-testenv`.

`container.py` makes a `.build/` folder here each time it builds. If this folder is in git, add this line to `.gitignore`:

```
.build/
```

### 4.2 The one change to your program

In real mode, the watchlist has to live in the data folder with the reports, so that it survives updates and the Stocks tab can edit it. The app could already be pointed there, but the agent's tools couldn't: the agent starts `market_tools.py` as a program of its own, which only sees settings from the environment.

In `market-agent/market_tools.py`, add `import os` with the other imports, and change the `WATCHLIST_FILE` line:

```python
import os
```

```python
# WATCHLIST_FILE moves the list somewhere else (the container keeps it with its data). It is an environment
# setting, not an argument, because the agent starts this file as a program of its own.
WATCHLIST_FILE = Path(os.environ.get("WATCHLIST_FILE") or Path(__file__).parent / "watchlist.txt")
```

The whole file is in [Appendix B](#appendix-b-the-changed-file-in-market-agent). Without the setting, nothing changes: the list is still `watchlist.txt` next to the code. Your tests still give `415 passed, 4 skipped`.

`container.py` refuses to build if this change is missing, and says why.

---

## 5. Step 2: Build the image

From `market-agent-container/`, with your virtual environment active:

```bash
python container.py build
```

**Expected result** (the first time, Docker downloads Python, Node and your packages, which takes several minutes; later builds reuse them):

```
Clean copy: 52 files, 0.6 MB in .../market-agent-container/.build (no keys, databases, logs or personal watchlist)
...Docker's own progress...
Built market-agent:local (version 2026.11.12). Next: python container.py test
```

(Your number of files will differ a little.) What went in, and what didn't:

| Goes into the image | Never goes in |
|---|---|
| `market-agent/`'s top-level `.py` files, its prompts (`*_prompt.md`) and `requirements.txt` | `.env`, anything starting with a dot |
| The frontend's `package.json`, `package-lock.json`, `index.html`, `vite.config.*`, `src/`, `public/` | `node_modules/`, `dist/` (the image builds its own) |
| `market-agent-testenv/`'s top-level `.py` files | `tests/`, `test_*.py`, `README*` |
| `Dockerfile`, `start.py`, `demo-banner.js` | Databases, logs, `.jsonl`, `.zip`, `.pem`, `.key` |
| A starter watchlist: AAPL, MSFT, NVDA, AMZN, JPM | **Your own `watchlist.txt`** |
| | The guides, reports and test notes: *this project* keeps them in `market-agent/`, and they quote example keys and name folders on your computer, so only prompts go in |

The copy is then searched for anything that looks like an Anthropic, Voyage or GitHub key or a Discord webhook, and for paths on your computer. If it finds one, it stops and names the file. To see the list of files without building: `python container.py context`.

Two options:

```bash
python container.py build --tickers AAPL,MSFT,GOOGL,KO     # the image's watchlist: the demo's stocks, and where real mode starts
python container.py build --version 1.4                     # the version shown in the banner (default: today's date)
```

---

## 6. Step 3: Test the image

```bash
python container.py test
```

It starts the image three times and removes each container afterwards. **Expected result** (shortened):

```
1. The demo, with networking switched off (proof it needs nothing from the internet)
  ok    the demo starts
      Self-test of http://127.0.0.1:8100 (demo mode)
        ok    the app answers (44 reports)
        ok    the page opens
        ok    the page's file /demo-banner.js
        ok    GET /api/alerts
        ...every address the API has...
        ok    a request sent to another name is refused
        ok    another website can't start a run
        ok    Run update now (simulated): updated the intraday report for 2026-11-12
        ok    Ask (simulated): answered in 106 words
        ok    Filings: Check now (simulated SEC)
      All 28 checks passed.
  ok    the demo passes its self-test offline
  ok    the app runs as an ordinary user, not as root (user 10001)
  ok    docker stop ends it promptly, even with a tab open (2s, exit code 143)
2. Real mode, with no key and networking off (it must start, explain what's missing, and call nothing)
  ok    real mode starts without a key
      ...
        skip  GET /api/reports/latest: nothing saved yet
        skip  GET /api/stocks/search: needs the internet
        ok    the agent's program (Claude Code) starts: 2.1.308 (Claude Code)
      All 20 checks passed.
  ok    real mode passes its (read-only) self-test
  ok    it starts a watchlist in /data (AAPL, MSFT, NVDA, AMZN, JPM)
  ok    its log says the key is missing
3. The demo again, opened from this computer the way a browser does
  ok    the demo starts
  ok    the app opens at http://localhost:49153
The image works. Next: python container.py publish
```

What the three parts prove:

1. **The demo needs nothing.** With networking off, the page, every API address, a simulated run, a question and a filings check all work. The self-test reads the list of addresses from the app itself, so a feature you add later is tried without changing anything.
2. **Real mode is safe to start.** With no key it starts, says what's missing, and its self-test only reads: it never starts a run, a question or a filing read, so it can never cost money. It also asks the agent's own program (Claude Code, which comes inside the `claude-agent-sdk` package) for its version, which proves that program is in the image and can start.
3. **It opens from your computer** through a published port, the way visitors will use it.

If a line says `FAIL`, the container's log is printed under it.

---

## 7. Step 4: Try it

```bash
python container.py run
```

Open http://localhost:8100. Check:

- [ ] The banner says "Demo with sample data", with today's version
- [ ] The Today tab shows an intraday report for the latest trading day
- [ ] **Run update now** finishes with "Saved (updated)" and the report moves on 15 minutes
- [ ] **Ask** answers
- [ ] The Filings, Calendar, Stocks, Follow-through and Story updates tabs open
- [ ] Turn off your Wi-Fi and reload: it still works

Press Ctrl+C in the terminal to stop it. It stops within about 2 seconds, even with the page open.

To try real mode with the key already in your terminal (`ANTHROPIC_API_KEY`, and `SEC_CONTACT` if you set it):

```bash
python container.py run --real
```

This is your first real check of real mode: press **Run update now** and watch a real brief being written inside the container. It costs what a run costs. Its data goes to a Docker volume called `market-agent-data`, not to your `market-agent/` folder, so your own reports are untouched. Section 11 has the details.

---

## 8. Step 5: Publish it

The image goes to GitHub's Container registry, `ghcr.io`, which is free for public images.

### 8.1 Sign in to the registry (once)

GitHub's registry only accepts a **personal access token (classic)**, not your password.

1. Open https://github.com/settings/tokens/new?scopes=write:packages
2. Give it a name such as "publish market-agent image", choose an expiry, and press **Generate token**. Copy it.
3. Sign in, pasting the token when asked for a password:

   ```bash
   docker login ghcr.io -u YOUR-GITHUB-NAME
   ```

The token is a key. Don't put it in any file in the project.

### 8.2 Publish

```bash
python container.py publish
```

This does everything in order, and stops at the first problem:

1. Makes the clean copy and checks it (step 2).
2. Builds `market-agent:local` and tests it (step 3). **If the test fails, nothing is published.**
3. Builds the image again for two kinds of processor, `linux/amd64` (Intel and AMD) and `linux/arm64` (Apple silicon Macs, Raspberry Pi), and sends both to the registry under two names:
   - `ghcr.io/YOU/YOUR-REPOSITORY:latest`, the one people get by default
   - `ghcr.io/YOU/YOUR-REPOSITORY:2026.11.12`, the dated version, kept so anyone can go back to it

The name comes from `market-agent/`'s GitHub address. To choose another: `python container.py publish --image ghcr.io/your-github-name/market-agent`.

The first time, it creates a builder called `market-agent-builder`. Building for two processors at once needs one of that kind, and creating a separate one leaves your other Docker projects alone. Building for the processor your computer doesn't have is done by emulation, so expect this step to take much longer than step 2. I couldn't time it.

### 8.3 Make it public (once)

GitHub's documentation says: "When you first publish a package, the default visibility is private." To let anyone download it:

1. On GitHub, click your profile picture, then **Your profile**, then the **Packages** tab.
2. Click the package's name.
3. Click **Package settings** on the right.
4. At the bottom, under "Danger Zone", click **Change visibility**.
5. Select **Public**, type the package's name, and click **I understand the consequences, change package visibility**.

GitHub warns: "Once you make a package public, you cannot make it private again." The image holds your code (section 17), so only do this if the code may be public.

### 8.4 Check it as a stranger

```bash
docker logout ghcr.io
docker pull ghcr.io/YOU/YOUR-REPOSITORY
docker run --rm -p 127.0.0.1:8100:8100 ghcr.io/YOU/YOUR-REPOSITORY
```

If the pull works while signed out, anyone can do it. (Sign in again before you next publish.)

---

## 9. Step 6: Tell people how to run it

Add this to your `README.md`, with your image's name:

````markdown
## Run it on your own computer

You need [Docker Desktop](https://www.docker.com/products/docker-desktop/) (or Docker Engine on Linux).

```bash
docker run --rm -p 127.0.0.1:8100:8100 ghcr.io/YOU/YOUR-REPOSITORY
```

Then open http://localhost:8100. This is a demo on simulated data: no AI is called, no key or account is
needed, and after the first download it works without internet. Press Ctrl+C to stop it.

To get a newer version later: `docker pull ghcr.io/YOU/YOUR-REPOSITORY`
````

Notes on that command, for you:

- `--rm` removes the container when it stops. The demo keeps nothing, so there is nothing to lose.
- `-p 127.0.0.1:8100:8100` makes the app reachable from that computer only. Without `127.0.0.1:`, other devices on the same network could open it.
- There is no `--pull always`. With it, the command would fail whenever there is no internet. Updating is a separate `docker pull`.
- If port 8100 is taken: `-p 127.0.0.1:9000:8100`, then open http://localhost:9000.

---

## 10. Updating after you add a feature

The routine:

1. Build the feature in `market-agent/`, and its simulated side in `market-agent-testenv/`, as every guide so far has done. Get the tests passing.
2. From `market-agent-container/`:

   ```bash
   pytest -v
   python container.py publish
   ```

3. People update with `docker pull ghcr.io/YOU/YOUR-REPOSITORY` and start it again. The banner shows the new version.

Nothing in the container folder needs editing for an ordinary feature, because nothing in it lists your files or addresses by name:

| You add | How it gets into the image |
|---|---|
| A Python file in `market-agent/` or `market-agent-testenv/` | The copy takes every top-level `.py` |
| A React component, a style, a new tab | The copy takes all of `frontend/src/`, and the image builds the frontend itself |
| A package in `requirements.txt` | The image installs `requirements.txt` when it's built |
| An npm package | The image installs from `package.json` and `package-lock.json` |
| A new API address | The self-test reads the addresses from the app, and tries it |
| Simulated data for it in the test environment | The demo is the test environment |
| A database change | `reports_db.py` already adds missing tables and columns to an older database when it opens it, so real-mode data survives an update |

The four cases where you do edit something here:

| The feature adds | Change | Where |
|---|---|---|
| Another kind of file the code reads (say `sectors.json`, or a Markdown file whose name doesn't end in `_prompt.md`) | Add its pattern to `MAIN_FILES` | `container.py` |
| An API address that needs something in it (`?q=...`, or `/api/things/{id}`) | The self-test fails and tells you what to add: a line in `QUERY_SAMPLES`, or a value in `values` | `start.py` |
| A scheduled job (a new cron line in a guide) | Add it to `JOBS` | `start.py` |
| A new key or secret setting | Add its name to `KEYS`, so the demo ignores it and real mode strips quotes from it | `start.py` |

If you forget, the test step catches the first two (the feature fails in the image, or the self-test says what to add). The last two don't break anything: the job just isn't scheduled in the container, and the key isn't ignored by the demo, which uses simulations either way.

---

## 11. Real mode

Real mode is the app as you run it, for someone with their own Anthropic key. Each person's reports, search index and watchlist live in a Docker volume on their own computer. Nothing is sent to you.

### 11.1 A settings file

Create a text file, for example `market-agent.env`, somewhere private (not in a project folder that gets published):

```
MODE=real
ANTHROPIC_API_KEY=sk-ant-...
SEC_CONTACT=Your Name you@your-company.com
SCHEDULE=on
```

No quotes and no spaces around the `=`. Docker passes quotes through as part of the value; `start.py` takes them off the settings it knows and says so, but it's cleaner to leave them out. Optional lines: `VOYAGE_API_KEY=...` (search by meaning), `DISCORD_WEBHOOK_URL=...` and `ALERTS_APP_URL=http://localhost:8100` (alerts, with links back to the app).

- `SEC_CONTACT` is the name and email address the SEC asks callers to identify themselves with (`market-agent-filings.md`, section 5). It is sent to the SEC with each request and nowhere else. Without it, company filings stay off.
- `SCHEDULE=on` turns on the scheduled runs (11.3). Leave the line out to write reports only when you press **Run update now**.
- *This project:* the key can also be named `MARKET_AGENT_ANTHROPIC_KEY`, as in your `.env`. Either way, the container gives it to the agent under that name, because `run_brief.py` takes `ANTHROPIC_API_KEY` out of the environment (on your own computer, so that Claude Code keeps using your login).

### 11.2 Start it

```bash
docker run -d --name market-agent --restart unless-stopped -p 127.0.0.1:8100:8100 -v market-agent-data:/data --env-file market-agent.env ghcr.io/YOU/YOUR-REPOSITORY
```

| Part | What it does |
|---|---|
| `-d` | Runs in the background |
| `--name market-agent` | A name to use in the commands below |
| `--restart unless-stopped` | Starts it again whenever Docker starts, so the schedule keeps running. (Set Docker Desktop to open at login for this to be automatic.) |
| `-v market-agent-data:/data` | Keeps the data in a volume called `market-agent-data`, which survives updates |
| `--env-file market-agent.env` | Your settings |

See what it says:

```bash
docker logs market-agent
```

```
Market analyst · version 2026.11.12 · real mode
Your reports, search index and watchlist are in /data.
Schedule: on, weekdays, New York time: filings 08:00, brief 08:15, calendar 09:35, brief 12:30, filings 16:35.
Schedule: the day's final report is also written after the close, at 16:15 New York time (the app's own after-close run).
Open http://localhost:8100 (or the port you chose with -p). Stop with Ctrl+C or docker stop.
```

If something is missing it says so in plain words here: no key, no `SEC_CONTACT`, or no volume ("your reports live inside this container and are deleted with it").

Open http://localhost:8100. The app starts empty, with the starter watchlist. Change the stocks on the Stocks tab, then press **Run update now** for the first report.

### 11.3 The schedule

With `SCHEDULE=on`, the container does what the cron lines in the earlier guides do:

| Job | When (New York time, Monday to Friday) | The same as | Needs |
|---|---|---|---|
| Company filings check | 08:00 and 16:35 | `python filings.py check` | `SEC_CONTACT` |
| Brief | 08:15 and 12:30 | `python run_brief.py` | `ANTHROPIC_API_KEY` |
| Calendar update | 09:35 | `python events.py scan --only-if-open` | `ANTHROPIC_API_KEY` |
| Final report (*this project:* the app's own after-close run) | 16:15 | Run update now, once the market has closed | `ANTHROPIC_API_KEY` |

- **Times are New York time whatever the computer's own time zone is**, including when the clocks change. (Cron needed the hours adjusting.)
- **A sleeping computer is allowed for.** A job whose time passed while the computer slept still runs if it wakes within 2 hours. After that it waits for the next one.
- **Holidays cost nothing extra.** The jobs themselves already check: a brief on a closed day finds the final report saved and stops before calling Claude, and the calendar update skips unless the market is open.
- **A job that fails is logged and not retried in a loop.** The schedule carries on. A job from before the container started never runs late.
- **Each run costs what a run costs** (the main guide, section 10), which is why the schedule is off unless you ask for it.
- To change the times, add lines to the settings file, for example `RUN_TIMES=08:15,12:30,16:10`. An empty value (`CALENDAR_TIMES=`) switches that job off.
- *This project:* outside a container, the app writes the day's final report after the close by itself (`AUTO_CLOSE_RUN`, on by default). In the container it belongs to the schedule: on only with `SCHEDULE=on` and a key, so a container never spends anything you didn't ask for. `AUTO_CLOSE_RUN=0` leaves it out; its time is `AUTO_CLOSE_TIME` (default 16:15).

Every job's output goes to the container's log: `docker logs -f market-agent` follows it live, with lines like `[schedule] brief: starting (run_brief.py)`.

If you already run the app with cron on the same computer, don't also switch the schedule on here with the same key: the two keep separate databases, so you would pay for every run twice.

### 11.4 Everyday commands

| To | Command |
|---|---|
| Stop it | `docker stop market-agent` |
| Start it again | `docker start market-agent` |
| Follow the log | `docker logs -f market-agent` |
| Update to a new version | `docker pull ghcr.io/YOU/YOUR-REPOSITORY`, then `docker rm -f market-agent`, then the `docker run` line from 11.2 again. The data is in the volume, so it is still there |
| Copy the data out (a backup, or to open `reports.db` in a SQLite tool) | `docker stop market-agent`, then `docker cp market-agent:/data ./market-agent-backup`, then `docker start market-agent` |
| Start over with no data | `docker rm -f market-agent`, then `docker volume rm market-agent-data` |

The reports database follows the same rules as always (`market-agent-database.md`): a finished day's report is permanent, and today's is updated through the day. Stopping first before copying gives a clean copy.

### 11.5 A folder instead of a volume

A volume is kept by Docker. To have the data in an ordinary folder you can see, make the folder first, then replace `-v market-agent-data:/data` with its path:

```bash
mkdir -p "$HOME/market-agent-data"
```

```bash
-v "$HOME/market-agent-data:/data"
```

On Linux, also add `--user $(id -u):$(id -g)` so the files belong to you. On macOS and Windows I recommend the volume instead: the database uses SQLite's write-ahead mode, and SQLite's documentation says "All processes using a database must be on the same host computer; WAL does not work over a network filesystem." Docker Desktop shares folders with containers through a file-sharing layer, and I could not test whether that layer is safe for it. The volume has no such question, and `docker cp` (11.4) gets the files out whenever you want them.

---

## 12. Settings

Given to `docker run` with `-e NAME=value`, or as lines in an `--env-file`.

| Setting | Default | What it does |
|---|---|---|
| `MODE` | `demo` | `demo` or `real` |
| `ANTHROPIC_API_KEY` | (none) | Real mode: runs, Ask, calendar updates, first takes. Ignored in the demo. *This project:* `MARKET_AGENT_ANTHROPIC_KEY` works too |
| `SEC_CONTACT` | (none) | Real mode: turns on company filings |
| `VOYAGE_API_KEY`, `DISCORD_WEBHOOK_URL`, `ALERTS_APP_URL` | (none) | Real mode: as in their guides |
| `SCHEDULE` | `off` | `on` runs the schedule in 11.3 (real mode only) |
| `RUN_TIMES` | `08:15,12:30` | Brief times, New York time |
| `CALENDAR_TIMES` | `09:35` | Calendar update times |
| `FILINGS_TIMES` | `08:00,16:35` | Filings check times |
| `AUTO_CLOSE_RUN` | `1` | *This project:* `0` leaves the app's own after-close report out of the schedule (11.3) |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | The names the app answers to (section 17). Add your computer's name or address to open it from another device; `*` for any |
| `PORT`, `HOST` | `8100`, `0.0.0.0` | Where the app listens inside the container. You normally change the outside port with `-p` instead |
| `MAX_TRACKED`, `RUN_COOLDOWN_SECONDS` and the app's other settings | as in their guides | Passed straight through to the app |

A `.env` file is never read: settings come only from `docker run`. The image has no `.env`; when the container's programs run on your own computer (as its tests do), this keeps the project's `.env`, with your real keys and webhook, out of the demo and the tests. (`start.py` sets python-dotenv's `PYTHON_DOTENV_DISABLED=1`.)

`container.py`'s options:

| Option | For | What it does |
|---|---|---|
| `--tickers A,B,C` | `build`, `publish`, `context` | The image's watchlist (default AAPL, MSFT, NVDA, AMZN, JPM) |
| `--version TEXT` | `build`, `publish`, `context` | The version in the banner and the dated tag (default: today's date) |
| `--image NAME` | `publish`, `test`, `run` | Where to publish, or which image to test or run |
| `--platforms LIST` | `publish` | Default `linux/amd64,linux/arm64` |
| `--builder NAME` | `publish` | Default `market-agent-builder`; `default` uses Docker's own |
| `--skip-test` | `publish` | Publish without testing first (not recommended) |
| `--no-port-check` | `test`, `publish` | Skip part 3 of the test |
| `--real`, `--port N` | `run` | Real mode with this terminal's keys; another port |

Two settings for unusual networks: `CONTAINER_IMAGE` (the same as `--image`), and `CONTAINER_BUILD_FLAGS`, extra flags for `docker build`, for example `CONTAINER_BUILD_FLAGS="--build-arg PYTHON_IMAGE=python:3.13-slim"` to try another Python.

---

## 13. What's real and what's simulated

| | Demo | Real mode |
|---|---|---|
| Your API, database code, search, alerts rules, React app | Real | Real |
| Claude (briefs, Ask, calendar, story checks, first takes) | Simulated | Real, with the person's key |
| Prices, news, company search (Yahoo Finance) | Simulated | Real |
| The SEC | Simulated (`sec.example.com`) | Real, with `SEC_CONTACT` |
| Search by meaning (Voyage) | Simulated | Real with `VOYAGE_API_KEY`; keywords only without |
| Discord | Written to a file inside the container | Real with `DISCORD_WEBHOOK_URL` |
| The schedule | None | Built in, if switched on |
| Data | Made at start, gone when the container is removed | Kept in `/data` |

The same image does both. A demo that someone likes becomes their real app by adding four lines of settings.

---

## 14. Test it

From `market-agent-container/`, with your virtual environment active:

```bash
pytest -v
```

**Expected result:** `71 passed, 1 skipped` in about 40 seconds (*this project*, on Windows: `69 passed, 3 skipped` in about 80 seconds, because symlinks and `docker stop`'s signal can't be tried there). Docker isn't needed. The skipped test is the one that tests a built image; to include it after `python container.py build`:

```bash
CONTAINER_TEST_IMAGE=market-agent:local pytest -v
```

That gives `72 passed` (on Windows PowerShell: `$env:CONTAINER_TEST_IMAGE="market-agent:local"; pytest -v`).

Your other suites don't change: `415 passed, 4 skipped` in `market-agent/`, `40 passed` in `market-agent-testenv/`, `18 passed` in `market-agent-demo/`.

| Area | Tests | What they prove |
|---|---|---|
| The clean copy | 16 | Code goes in; keys, `.env`, databases, logs, tests, `node_modules`, hidden files, symlinks and your own watchlist don't. Anything that looks like a key (5 kinds) stops the build without printing it. A new feature's files come along unasked. The copy is made fresh, and only ever replaces a folder it made. The version can only be plain characters |
| The Dockerfile | 3 | Every file it copies exists in the clean copy. The app runs as an ordinary user with a health check. No keys in it, and the base images are pinned |
| Names and commands | 8 | The image name comes from the GitHub address, in lower case. `publish` tests first and sends nothing if the test fails. Test containers run with networking off, are never given a key, and are always removed. The port is opened on this computer only, and keys are passed by name, never written into a command |
| Settings | 3 | A wrong `MODE` or `PORT` is explained. Quotes from a settings file are taken off. A user without a home folder gets one |
| The demo's sample | 5 | Its "today" is the latest trading day (weekends and holidays included). It is made once a day and replaced whole the next day, a half-made one is made again, and a folder that isn't a sample is never wiped. Real keys are dropped before anything runs |
| Real mode's settings | 6 | The app, the scheduled jobs and the agent's tools are all pointed at the data folder. A missing volume is noticed. *This project:* the key reaches the agent (in a program of its own, where `run_brief.py` takes it out of the environment), and the start-up checks and the schedule still see it; either name works; the app's own after-close run is on only with the schedule; a `.env` is never read |
| The banner | 2 | Added once, to a copy; the real app's page is untouched |
| Names the app answers to | 2 | `localhost`, `127.0.0.1` and `[::1]` only, whatever the port; `localhost.evil.example` is refused |
| The schedule | 9 | Off unless asked for. The default times match the guides. Weekdays only, New York time across clock changes, up to 2 hours late, once each, never from before the start, and a failing job isn't retried in a loop |
| The app, started as the container starts it | 16 | The demo starts, passes its self-test, and stops within seconds with a tab open. The self-test names what's broken: a missing address, an address needing a value, a missing banner, a missing guard, a failed run. Real mode starts without keys, keeps its data in its folder, keeps an existing watchlist, and its self-test only reads. An agent program that is missing or can't start is caught. The agent's tools follow the watchlist setting |
| A built image | 1 | (When named.) The image passes `container.py test` |
| Isolation | 1 | `market-agent/` and `market-agent-testenv/` are exactly as they were |

---

## 15. What was tested, and what you need to check

The computer this guide was written on could run Docker, but could not download from Docker Hub, PyPI or npm. So I'll be exact about what I saw work and what I didn't.

### What I tested

- **The tests above:** `66 passed, 1 skipped`, and `67 passed` with the image test on (the guide's own tests, before this project added 5). The other three suites are unchanged.
- **Deliberate breakages:** I broke the code 79 ways, one at a time (the guard removed, the key check removed, weekends allowed, and so on). The tests caught all 79.
- **The real `Dockerfile`, built by Docker**, on stand-in base images made from that computer's own Python 3.13 and Node 22. In the stand-ins, `pip`, `apt-get` and `npm` were replaced by small scripts, because there was nothing to download from; the packages (Starlette, uvicorn, pandas, numpy, the Claude Agent SDK with Claude Code inside it, and `tini`) were real, except `yfinance`, which was the tests' stand-in.
- **That image, in real containers with networking off:** `container.py test` parts 1 and 2 exactly as in section 6 (28 and 20 checks), including Claude Code starting inside the container as the app's ordinary user, and Docker's own health check reporting "healthy".
- **In a browser, against the container** (10 checks): the banner and version, Run update now, Ask, every tab, Filings and Check now, adding Costco on the Stocks tab, a restart keeping the same day's sample, a new container starting clean, a phone-sized screen, dark mode, and real mode's empty app with no banner. No request left the computer.
- **By hand, in containers:** a volume keeps the watchlist and database across containers; starting as another user works for the demo and gives a clear message in real mode; a settings file with quotes; the schedule starting `run_brief.py`, `events.py` and `filings.py` at the right New York minute and carrying on after a failure; and I planted a fake key, a `.env`, a database, a log and a personal watchlist in the project and confirmed none of them was anywhere in the image.
- **Older Pythons:** the new files load and their dependency-free parts work on Python 3.11 and 3.12.

One real bug was found this way and fixed: with a browser tab open, `docker stop` hung for 10 seconds until Docker killed the app. It now stops in 2.

### On this project's computer (Windows 11, no Docker)

Docker isn't installed on the computer this project was built on, so the image wasn't built. What was done instead, on 2026-11-12:

- **The tests:** `69 passed, 3 skipped`. The main suite: `663 passed, 5 skipped, 1 xfailed`; the test environment's `40 passed`, the demo's `18 passed`.
- **The clean copy** of the real projects: 52 files, 0.7 MB, no problems found. Every Python file in it compiles on Python 3.12, the image's version.
- **The Dockerfile's frontend stage, by hand:** `npm ci` and `npm run build` on the clean copy alone. Both worked, so `package.json` and `package-lock.json` agree.
- **The image's layout, without Docker:** the clean copy laid out as the Dockerfile lays out `/app`, with the frontend it built, then `start.py prepare` and `start.py` as the container runs them.
  - The demo's self-test passed **28 of 28**, as section 6 shows. In a browser it showed the banner with its version, the report and the Filings tab.
  - Real mode's self-test passed **22 of 22** (20 here, plus 2 that needed the internet), including Claude Code 2.1.317 starting. It started with no key and said what was missing, and kept its data and the starter watchlist in its data folder.
- **Four places where the guide's container didn't fit this project** were found this way and changed. They're listed at the top of this guide and in `test-case-reporting.md` (fourth round).

### What I could not test

| Not tested | Why it matters | How you check it |
|---|---|---|
| Downloading the real base images, `pip install -r requirements.txt`, `apt-get install tini`, `npm ci` and Vite's `npm run build` inside Docker | This is the first thing that will run on your computer | Step 2. If it fails, the error names the step: see section 18 |
| The real `yfinance` and `voyageai` inside the image, and Python 3.12 running the whole app (the tests ran on 3.13) | Real mode needs them | Step 3's real-mode self-test imports the whole app, so a broken install shows there |
| The image's size | I expect several hundred MB (the Claude Code program alone is about 290 MB), but didn't measure it | `docker images market-agent` after step 2 |
| Opening the app through a published port (`-p`), and part 3 of `container.py test` | That computer's Docker had no port publishing; I reached the app another way | Steps 3 and 4 |
| Building for ARM, the `market-agent-builder`, pushing to `ghcr.io`, making the package public, pulling as a stranger | Publishing | Step 5, including 8.4 |
| Docker Desktop on macOS or Windows | It was all on Linux | Steps 2 to 4 |
| **A real run in real mode:** Claude writing a brief inside the container, the real SEC, Discord, Voyage | No key and no internet there. What I did see: the agent's program starts in the container, and the schedule launches the jobs | Step 4, `python container.py run --real`, then the checklist below |
| A folder instead of a volume on macOS or Windows | See 11.5 | Use the volume |

### Checklist for your first real-mode run

- [ ] `python container.py run --real` prints "real mode" and no "No ANTHROPIC_API_KEY" line
- [ ] **Run update now** shows the agent's tool calls and ends with "Saved"
- [ ] The report's figures look like the ones your own app gives for the same stocks
- [ ] **Ask** answers a question about that report
- [ ] On the Stocks tab, add a stock, press **Run update now**, and the new stock is in the report (this proves the agent's tools read the watchlist in `/data`)
- [ ] With `SEC_CONTACT` set, the Filings tab's **Check now** lists filings
- [ ] Stop it, start it again: the report and the stock are still there

---

## 16. Costs

| | Cost |
|---|---|
| Building and testing | Free |
| GitHub's Container registry | GitHub's documentation says GitHub Packages is free for public packages |
| Docker Desktop | Free for personal use and small businesses; see the licence note in section 3 |
| The demo, for anyone, any number of times | Nothing. No AI or data service is called |
| Real mode | The person's own Anthropic usage: the same per run as in the main guide (section 10). With `SCHEDULE=on`, two briefs and a calendar update each weekday, plus first takes on new results (capped by the filings guide's budget) |
| You, when others use real mode | Nothing. They use their own key; nothing comes through you |

---

## 17. Security and privacy

**What is in the image.** Your code, a starter watchlist, and the packages it needs. No key, no `.env`, no database, no log, not your watchlist. `container.py` copies by pattern into a clean folder, then searches that folder for keys, webhooks and paths on your computer before Docker ever sees it. A key pasted into a source file stops the build.

**A public image publishes your code.** Anyone can download the image and read the Python and the built frontend inside it. That is the same as a public repository. If your repository is private, publishing a public image makes the code public anyway, and GitHub won't let you make the package private again.

**Other people's software is inside it.** The image contains Python, Node-built files, the Python packages in `requirements.txt`, and the Claude Agent SDK, which includes Anthropic's Claude Code program. Each has its own licence or terms. Before publishing publicly, check that they allow you to pass copies on inside an image, the Claude Agent SDK's in particular. I'm not a lawyer, and I haven't checked this for you.

**Keys in real mode.** Keys are given when the container starts and are never written into the image or the data volume. Anyone who can use Docker on that computer can read them with `docker inspect`, which is the same trust as reading the settings file. Keep the settings file out of project folders.

**The demo can't spend anything.** In demo mode the keys are removed from the program's environment before anything else runs, and every outside service is simulated. `container.py test` runs the demo with networking off to prove it needs none.

**Only that computer can open the app.**

- The `docker run` commands in this guide publish the port as `127.0.0.1:8100:8100`. Other devices on the network can't reach it.
- The app refuses requests from other websites, as before (`_post_guard` in `api.py`).
- New here: the container also refuses any request that wasn't addressed to `localhost`, `127.0.0.1` or `[::1]`. This closes a way around the previous rule, where a website points its own name at `127.0.0.1` so that the browser treats it as "the same site". To open the app from another device on purpose, publish the port without `127.0.0.1:` and set `ALLOWED_HOSTS` to the computer's name or address. Anyone on that network can then use the app, including pressing Run update now with your key, so only do this on a network you trust.

**It runs as an ordinary user** inside the container (not as root), with the code read-only to it. It can write to `/data` and to temporary folders only.

**Nothing reports back to you.** This guide's code sends nothing anywhere. Real mode uses the same services your app uses on your own computer: Anthropic (through Claude Code, which has its own usage reporting to Anthropic), Yahoo Finance, the SEC, and Voyage and Discord if set.

**Pinned versions.** Every publish also gets a dated tag. If a new version misbehaves, people can run the previous one: `ghcr.io/YOU/YOUR-REPOSITORY:2026.11.12`.

---

## 18. Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `Docker wasn't found` or `isn't running` | Install Docker Desktop, start it, wait for it to settle, and open a new terminal. |
| `Can't find the main project at ...market-agent` | *This project:* set `MARKET_AGENT_DIR` (section 4.1). |
| `Not building: frontend/package.json is missing` | The frontend isn't set up with npm on this computer. Do `market-agent-frontend.md`, section 5, and check `npm run build` works. |
| `Not building: ... contains something that looks like a key` | A key or webhook is in the named source file. Remove it (keys belong in the environment), and if it was ever committed, replace the key. |
| `Not building: market_tools.py doesn't read the WATCHLIST_FILE setting yet` | Step 1, part 4.2. |
| The build fails at `npm ci` | `package.json` and `package-lock.json` disagree. Run `npm install` in `market-agent/frontend/`, then build again. |
| The build fails at `pip install` | Read the last lines: it names the package. If it happens only when publishing (the ARM build), a package may have no ARM version: publish with `--platforms linux/amd64` for now. |
| The build fails at `apt-get` | No internet inside the build, often a company proxy. Set the proxy in Docker Desktop's settings and try again. |
| `container.py test` says `FAIL  GET /api/...: it needs something in its address` | A new address needs a sample value. Add it to `QUERY_SAMPLES` in `start.py`, as the message says. |
| `FAIL  the agent's program (Claude Code): it isn't here` | The `claude-agent-sdk` package for that processor came without its program. Check with `docker run --rm --entrypoint ls market-agent:local /usr/local/lib/python3.12/site-packages/claude_agent_sdk/_bundled`. The SDK also accepts a `claude` program on the PATH, so installing Claude Code in the Dockerfile is the fix; I have not tested that route. The demo isn't affected. |
| `FAIL  docker stop ends it promptly` | Something is holding the app open. Check `timeout_graceful_shutdown` is still passed to `uvicorn.run` in `start.py`. |
| Publishing fails with `denied` or `unauthorized` | Not signed in to `ghcr.io`, the token lacks `write:packages`, or the image name isn't under your GitHub name. Section 8.1; `--image`. |
| Publishing fails building for the other processor | Try `--platforms linux/amd64` (or `linux/arm64` on an Apple silicon Mac) to publish one now. On Linux without Docker Desktop, emulation may need installing first: see Docker's [multi-platform builds](https://docs.docker.com/build/building/multi-platform/) page. |
| A visitor's `docker pull` says `denied` | The package is still private. Section 8.3. |
| `port is already allocated` | Something else uses 8100. Use `-p 127.0.0.1:9000:8100` and open http://localhost:9000. |
| The page says "This app only answers at 127.0.0.1, [::1], localhost" | It was opened under another name or address. Use http://localhost:8100, or set `ALLOWED_HOSTS` (section 17). |
| Real mode: `Can't write to /data` | A `--user` was given with a volume, or a Linux folder was mounted without one. Use the volume and no `--user`, or see 11.5. |
| Real mode: the log says `No ANTHROPIC_API_KEY` although it's in the settings file | The file wasn't passed (`--env-file`), or the line has a space around `=`. |
| Real mode: scheduled runs don't happen | The log's `Schedule:` line says why: off, or a key missing. They only run while the container is running, on weekdays, New York time. |
| Real mode: reports gone after an update | The container was started without `-v market-agent-data:/data`. The log warns about this at start. |
| The demo shows yesterday as "today" | The container has been running since yesterday. Restart it: `docker restart NAME` makes a fresh sample for the new day. |
| `docker run` re-downloads nothing but the app is old | `docker run` uses the copy already on the computer. `docker pull` first. |
| Everything is slow on an Apple silicon Mac | An Intel-only image is being emulated. Publish with both platforms (the default). |

---

## 19. Sources

- [Working with the Container registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry) (GitHub Docs): the image name, classic tokens with `write:packages`, signing in, private by default, anonymous pulls of public images
- [Configuring a package's access control and visibility](https://docs.github.com/en/packages/learn-github-packages/configuring-a-packages-access-control-and-visibility) (GitHub Docs): the steps in 8.3 and the warning quoted there
- [GitHub Packages billing](https://docs.github.com/en/billing/concepts/product-billing/github-packages) (GitHub Docs): free for public packages
- [Docker Desktop license agreement](https://docs.docker.com/subscription/desktop-license/) (Docker Docs): who can use Docker Desktop without paying. I read this page through a summary, not word for word, so check the figures there
- [Multi-platform builds](https://docs.docker.com/build/building/multi-platform/) (Docker Docs): building for two processors. Also read through a summary
- [Write-Ahead Logging](https://www.sqlite.org/wal.html) (SQLite): the sentence quoted in 11.5

How `docker run -e NAME`, `--env-file`, `--network none`, volumes and health checks behave was checked directly, on Docker 29.9, rather than from documentation.

---

## Appendix A: the container folder

The five files of `market-agent-container/`.

### Dockerfile

```dockerfile
# The market analyst app in one image: the demo by default, your real app with -e MODE=real.
#
# Don't build this from a project folder. `python container.py build` makes a clean copy first
# (.build/: code only, no keys, databases or personal watchlist) and builds from that.

ARG NODE_IMAGE=node:22-slim
ARG PYTHON_IMAGE=python:3.12-slim

# 1. Build the React app. This stage runs on the build computer's own processor, whichever
#    processors the image is for: its output is plain files that work everywhere.
FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS frontend
WORKDIR /frontend
COPY frontend/package*.json ./
RUN if [ -f package-lock.json ]; then npm ci; else npm install; fi
COPY frontend/ ./
RUN npm run build

# 2. The app itself
FROM ${PYTHON_IMAGE}
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

# tini passes Ctrl+C and `docker stop` on to the app and tidies up after the programs a run starts
RUN apt-get update \
    && apt-get install -y --no-install-recommends tini \
    && rm -rf /var/lib/apt/lists/*

# Python packages first, so changing the code doesn't download them again
WORKDIR /app
COPY app/market-agent/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt tzdata

# An ordinary user to run as, and the folder real mode keeps its data in
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /data \
    && chown app:app /data

COPY app/ ./
COPY --from=frontend /frontend/dist ./market-agent/frontend/dist
COPY start.py demo-banner.js VERSION ./
RUN python start.py prepare

USER app
ENV MODE=demo \
    PORT=8100
EXPOSE 8100
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD ["python", "/app/start.py", "healthcheck"]
ENTRYPOINT ["tini", "--", "python", "/app/start.py"]

ARG VERSION=dev
ARG SOURCE=
LABEL org.opencontainers.image.title="Market analyst" \
      org.opencontainers.image.description="Market analyst agent: a demo on simulated data (no AI, no keys, works offline), or your own app with MODE=real." \
      org.opencontainers.image.version="${VERSION}" \
      org.opencontainers.image.source="${SOURCE}"
```

### start.py

```python
"""Starts the market analyst app inside its container (or on your own computer, to try it without Docker).

    python start.py                 start the app: the demo (MODE=demo, the default) or your real app (MODE=real)
    python start.py prepare         when the image is built: make the demo's copy of the built app, with its banner
    python start.py healthcheck     exit 0 if the app is answering (Docker asks every 30 seconds)
    python start.py selftest        try every address of the API, and in the demo a run, a question and a filings check

Demo mode serves the test environment's simulated sample: no AI, no market data, no keys and no internet.
The sample is made when the container starts, so its "today" is always the latest trading day.

Real mode is your own app. It needs ANTHROPIC_API_KEY, keeps its reports and its watchlist in /data
(put a Docker volume there), and with SCHEDULE=on starts the scheduled runs itself, on New York time.

Settings (all optional), given to `docker run` with -e NAME=value:
    MODE            demo (default) or real
    PORT, HOST      where the app listens inside the container (8100, 0.0.0.0)
    ALLOWED_HOSTS   names the app answers to (localhost,127.0.0.1,[::1]); * for any
    DATA_DIR        real mode's folder (/data)
    SCHEDULE        on to run the schedule below (real mode only; each run costs what a run costs)
    RUN_TIMES       briefs, default 08:15,12:30      CALENDAR_TIMES  calendar update, default 09:35
    FILINGS_TIMES   filings checks, default 08:00,16:35      (New York time, weekdays; empty for never)
    AUTO_CLOSE_RUN  0 to leave out the app's own after-close final report (16:15), which SCHEDULE=on includes

A .env file is never read: the image has none, and on your own computer the project's real keys stay out.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time as clock
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.dont_write_bytecode = True                # never leave __pycache__ folders in the projects
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"   # ...including from programs started from here
# Settings come only from `docker run` (-e, --env-file). The image has no .env file, but when this runs on
# your own computer, the project's .env (your real keys and webhook) must not reach the demo or the tests.
# python-dotenv reads nothing while this is set, here and in every program started from here.
os.environ["PYTHON_DOTENV_DISABLED"] = "1"

HERE = Path(__file__).resolve().parent


def _beside(name: str) -> Path:
    """In the image the two projects sit inside this folder; on your computer they sit next to it."""
    inside = HERE / name
    return inside if inside.is_dir() else HERE.parent / name


MAIN = Path(os.environ.get("MARKET_AGENT_DIR") or _beside("market-agent")).resolve()
TESTENV = Path(os.environ.get("MARKET_AGENT_TESTENV_DIR") or _beside("market-agent-testenv")).resolve()
DEMO_FRONTEND = HERE / "frontend-demo"        # the built app plus the demo's banner (made by `prepare`)
BANNER = HERE / "demo-banner.js"
DATA = Path(os.environ.get("DATA_DIR") or "/data")
DEMO_DATA = Path(os.environ.get("DEMO_DIR") or Path(tempfile.gettempdir()) / "market-agent-demo")
ET = ZoneInfo("America/New_York")
DEFAULT_PORT = 8100
DEFAULT_HOSTS = "localhost,127.0.0.1,[::1]"
STARTER_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]   # a new real watchlist, if the image has none
# MARKET_AGENT_ANTHROPIC_KEY is this project's own name for the Anthropic key (run_brief.py), so a .env
# passed with --env-file works too
KEYS = ("ANTHROPIC_API_KEY", "VOYAGE_API_KEY", "DISCORD_WEBHOOK_URL", "SEC_CONTACT", "MARKET_AGENT_ANTHROPIC_KEY")
SETTINGS = ("MODE", "PORT", "HOST", "ALLOWED_HOSTS", "SCHEDULE", "RUN_TIMES", "CALENDAR_TIMES", "FILINGS_TIMES",
            "ALERTS_APP_URL", "AUTO_CLOSE_RUN", *KEYS)
GRACE = timedelta(hours=2)                    # how late a scheduled job may start (the computer was asleep)
JOB_TIMEOUT_SECONDS = 30 * 60
STOP_SECONDS = 2                              # how long requests in progress get when the app is told to stop
# The built-in schedule: name, the setting holding its times, default times, the command, and what it needs
JOBS = (
    ("filings", "FILINGS_TIMES", "08:00,16:35", ["filings.py", "check"], ("SEC_CONTACT",)),
    ("brief", "RUN_TIMES", "08:15,12:30", ["run_brief.py"], ("ANTHROPIC_API_KEY",)),
    ("calendar", "CALENDAR_TIMES", "09:35", ["events.py", "scan", "--only-if-open"], ("ANTHROPIC_API_KEY",)),
)


def say(text: str = "") -> None:
    print(text, flush=True)


def version() -> str:
    path = HERE / "VERSION"
    return path.read_text().strip() if path.is_file() else "dev"


def unquote_settings(env=os.environ) -> list[str]:
    """Docker's --env-file keeps quotes as part of the value: KEY="sk-ant-..." arrives with its quotes on,
    and the key stops working. Take them off. Returns the names it changed."""
    changed = []
    for name in SETTINGS:
        value = env.get(name) or ""
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            env[name] = value[1:-1]
            changed.append(name)
    return changed


def read_mode(env=os.environ) -> str:
    mode = (env.get("MODE") or "demo").strip().lower()
    if mode not in ("demo", "real"):
        sys.exit(f"MODE must be demo or real, not {env.get('MODE')!r}.")
    return mode


def read_port(env=os.environ) -> int:
    raw = (env.get("PORT") or str(DEFAULT_PORT)).strip()
    if not raw.isdigit() or not 1 <= int(raw) <= 65535:
        sys.exit(f"PORT must be a number from 1 to 65535, not {raw!r}.")
    return int(raw)


def writable_home(env=os.environ) -> str:
    """Claude Code and yfinance keep small files in the home folder. If the container was started as a
    user without one (docker run --user ...), give it a folder it can write to."""
    home = env.get("HOME", "")
    if not home or not os.access(home, os.W_OK):
        fallback = Path(tempfile.gettempdir()) / "market-agent-home"
        fallback.mkdir(parents=True, exist_ok=True)
        env["HOME"] = home = str(fallback)
    return home


# ---------------------------------------------------------------------------
# Demo mode: the test environment's sample, with everything simulated
# ---------------------------------------------------------------------------

def load_testenv():
    """The test environment's code, which runs the real program against sample data only."""
    if not (TESTENV / "testenv.py").is_file():
        sys.exit(f"Can't find the test environment at {TESTENV}.")
    os.environ.setdefault("MARKET_AGENT_DIR", str(MAIN))
    if str(TESTENV) not in sys.path:
        sys.path.insert(0, str(TESTENV))
    import testenv
    return testenv


def sample_day(today: date | None = None) -> date:
    """The sample's "today": the latest trading day, so there is always a day in progress to update."""
    load_testenv()
    from sample_market import trading_days
    today = today or datetime.now(ET).date()
    return trading_days(today - timedelta(days=10), today)[-1]


def sample_is_ready(folder: Path, day: date) -> bool:
    """True if a finished sample for this day is already there (the container was only restarted)."""
    try:
        return (folder / "ready").read_text().strip() == day.isoformat() and (folder / "reports.db").is_file()
    except OSError:
        return False


def make_sample(folder: Path, day: date) -> bool:
    """Create the sample in this folder unless today's is already there. Returns True if it made one.
    An older sample is replaced whole, so every start begins from the same clean demo."""
    if sample_is_ready(folder, day):
        return False
    ours = (folder / "ready").is_file() or (folder / "sample_config.json").is_file()
    if folder.is_dir() and any(folder.iterdir()) and not ours:
        sys.exit(f"{folder} holds files that aren't a demo sample, so the demo won't replace them. "
                 "Point DEMO_DIR at an empty folder.")
    testenv = load_testenv()
    shutil.rmtree(folder, ignore_errors=True)
    testenv.seed_database(folder / "reports.db", end=day, latest="intraday")
    (folder / "ready").write_text(day.isoformat() + "\n")  # written last: a half-made sample is made again
    return True


def demo_frontend() -> Path:
    """The built app with the demo's banner (in the image), or the test environment's own build."""
    return DEMO_FRONTEND if DEMO_FRONTEND.is_dir() else TESTENV / "frontend-dist"


def demo_app(folder: Path = DEMO_DATA, today: date | None = None, frontend: Path | None = None):
    """The real app over a fresh sample, with Claude, Yahoo, Voyage, Discord and the SEC all simulated.
    Returns the app and a few facts for the start-up message."""
    testenv = load_testenv()
    ignored = [name for name in KEYS if os.environ.pop(name, None)]  # the demo must never use (or cost) anything real
    day = sample_day(today)
    made = make_sample(folder, day)
    app = testenv.make_app(folder / "reports.db", frontend_dist=frontend or demo_frontend())
    return app, {"day": day, "made": made, "ignored": ignored, "folder": folder}


# ---------------------------------------------------------------------------
# Real mode: your own app, with its data in /data
# ---------------------------------------------------------------------------

def is_mounted(folder: Path, mounts: Path = Path("/proc/self/mountinfo")) -> bool:
    """True if a volume (or a folder from the computer) is attached at this folder. Linux lists every
    attached folder in /proc/self/mountinfo; the fifth word of each line is where."""
    try:
        places = {line.split()[4] for line in mounts.read_text().splitlines() if len(line.split()) > 4}
    except OSError:
        return os.path.ismount(folder)
    return str(Path(folder).resolve()) in places


def real_app(data: Path | None = None, frontend: Path | None = None):
    """The real app, with its reports, search index and watchlist in the data folder.
    Returns the app and notes for the start-up message (what's missing, in plain words)."""
    data = Path(data or DATA)
    try:
        data.mkdir(parents=True, exist_ok=True)
        probe = data / ".write-test"
        probe.write_text("")
        probe.unlink()
    except OSError:
        sys.exit(f"Can't write to {data}. Use a Docker volume (-v market-agent-data:/data) and leave out --user. "
                 "If you mounted a folder from a Linux computer instead, add: --user $(id -u):$(id -g)")
    watchlist = data / "watchlist.txt"
    if not watchlist.is_file():  # first start: begin from the image's starter list; the Stocks tab edits this copy
        starter = MAIN / "watchlist.txt"
        watchlist.write_bytes(starter.read_bytes() if starter.is_file() else ("\n".join(STARTER_TICKERS) + "\n").encode())
    # The Anthropic key, under either of its names. This project's run_brief.py takes ANTHROPIC_API_KEY out of
    # the environment (on your own computer, so that Claude Code keeps using your login) and hands the agent
    # MARKET_AGENT_ANTHROPIC_KEY instead. A container has no login to keep, so the key goes under both names.
    key = (os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("MARKET_AGENT_ANTHROPIC_KEY") or "").strip()
    if key:
        os.environ["MARKET_AGENT_ANTHROPIC_KEY"] = key
    os.environ["REPORTS_DB"] = str(data / "reports.db")  # read by the app and by every scheduled job
    os.environ["WATCHLIST_FILE"] = str(watchlist)        # ...and by the agent's tools, which run as their own program
    os.environ.pop("SEARCH_DB", None)                    # so the search index sits next to the reports
    if str(MAIN) not in sys.path:
        sys.path.insert(0, str(MAIN))
    import market_tools
    import reports_db
    reports_db.DB_PATH = data / "reports.db"  # also covers the case where they were imported earlier
    market_tools.WATCHLIST_FILE = watchlist
    import api
    if key:
        os.environ["ANTHROPIC_API_KEY"] = key  # put back after run_brief.py took it out (the checks below look for it)
    api.AUTO_CLOSE = after_close_wanted()  # the app's own after-close run belongs to the schedule here

    notes = []
    if not os.environ.get("ANTHROPIC_API_KEY"):
        notes.append("No ANTHROPIC_API_KEY: the app opens, but runs, questions and first takes won't work. "
                     "Add -e ANTHROPIC_API_KEY to the docker run command.")
    if not os.environ.get("SEC_CONTACT"):
        notes.append("No SEC_CONTACT: company filings stay off until you set it to your name and email address "
                     "(the SEC asks who is calling; it is sent to the SEC and nowhere else).")
    if not is_mounted(data):
        notes.append(f"{data} isn't a volume: your reports live inside this container and are deleted with it. "
                     "Add -v market-agent-data:/data to keep them.")
    return (api.create_app(frontend_dist=frontend) if frontend else api.create_app()), notes


# ---------------------------------------------------------------------------
# Only answer to the names you use (stops other websites reaching the app through your browser)
# ---------------------------------------------------------------------------

def allowed_hosts(text: str | None = None) -> set[str]:
    raw = os.environ.get("ALLOWED_HOSTS") if text is None else text
    return {h.strip().lower().rstrip(".") for h in (raw or DEFAULT_HOSTS).split(",") if h.strip()}


def host_name(header: str) -> str:
    """The name in a Host header, without its port: 'LocalHost:8100' -> 'localhost', '[::1]:8100' -> '[::1]'."""
    host = header.strip().lower()
    if host.startswith("["):
        return host[:host.find("]") + 1]
    return host.rsplit(":", 1)[0].rstrip(".")


def only_hosts(app, allowed: set[str]):
    """Refuse requests that were sent to any other name. The API already refuses requests that come from
    other websites; this closes the way around that, where a website points its own name at 127.0.0.1."""
    if "*" in allowed:
        return app

    async def guarded(scope, receive, send):
        if scope["type"] == "http":
            name = host_name(next((v for k, v in scope.get("headers", []) if k == b"host"), b"").decode("latin-1"))
            if name not in allowed:
                shown = name if re.fullmatch(r"[\w.\-\[\]:]{1,100}", name) else "that name"
                body = (f"This app only answers at {', '.join(sorted(allowed))}. To open it as {shown}, "
                        f"start it with -e ALLOWED_HOSTS={shown}\n").encode()
                await send({"type": "http.response.start", "status": 403,
                            "headers": [(b"content-type", b"text/plain; charset=utf-8"),
                                        (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await app(scope, receive, send)

    return guarded


# ---------------------------------------------------------------------------
# The built-in schedule (real mode, SCHEDULE=on): what cron does in the main guide
# ---------------------------------------------------------------------------

def parse_times(text: str, setting: str) -> list[time]:
    """'08:15,12:30' -> times of day. Empty means never."""
    times = []
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        match = re.fullmatch(r"(\d{1,2}):(\d{2})", part)
        if not match or int(match.group(1)) > 23 or int(match.group(2)) > 59:
            sys.exit(f"{setting} must be times like 08:15,12:30 (New York time), not {text!r}.")
        times.append(time(int(match.group(1)), int(match.group(2))))
    return sorted(set(times))


def schedule_on(env=os.environ) -> bool:
    return (env.get("SCHEDULE") or "off").strip().lower() in ("on", "1", "true", "yes")


def after_close_wanted(env=os.environ) -> bool:
    """Whether the app's own after-close run (api.AUTO_CLOSE: the day's final report, 16:15 New York time) is on.
    Outside a container it is on by default; here it is part of the schedule, so a container never spends
    anything nobody asked for: on only with SCHEDULE=on and a key, and AUTO_CLOSE_RUN=0 still turns it off."""
    has_key = bool(env.get("ANTHROPIC_API_KEY") or env.get("MARKET_AGENT_ANTHROPIC_KEY"))
    return schedule_on(env) and has_key and (env.get("AUTO_CLOSE_RUN") or "1").strip() != "0"


def plan_schedule(env=os.environ) -> tuple[list[tuple[str, time, list[str]]], list[str]]:
    """What the schedule will run, as (job, New York time, command), and notes for the start-up message."""
    if not schedule_on(env):
        return [], ["Schedule: off. Reports are written when you press Run update now. "
                    "Add -e SCHEDULE=on for the weekday runs (each one costs what a run costs)."]
    slots, notes = [], []
    for name, setting, default, command, needs in JOBS:
        times = parse_times(env[setting] if setting in env else default, setting)
        missing = [n for n in needs if not env.get(n)]
        if times and missing:
            notes.append(f"Schedule: {name} is off, because {' and '.join(missing)} isn't set.")
            continue
        slots += [(name, at, command) for at in times]
    slots.sort(key=lambda slot: (slot[1], slot[0]))
    if slots:
        listed = ", ".join(f"{name} {at:%H:%M}" for name, at, _ in slots)
        notes.insert(0, f"Schedule: on, weekdays, New York time: {listed}.")
    else:
        notes.append("Schedule: on, but nothing can run yet.")
    return slots, notes


def due(slots, now: datetime, started: datetime, done: set) -> list[tuple[datetime, str, list[str]]]:
    """The jobs to start now, earliest first. A job is due on a weekday from its time until 2 hours after
    (so one missed while the computer slept still runs), once, and never if its time was before this start."""
    now = now.astimezone(ET)
    found = []
    for day in (now.date() - timedelta(days=1), now.date()):  # yesterday too: a late-evening job checked after midnight
        if day.weekday() >= 5:
            continue
        for name, at, command in slots:
            moment = datetime.combine(day, at, ET)
            if started <= moment <= now <= moment + GRACE and (name, moment.isoformat()) not in done:
                found.append((moment, name, command))
    return sorted(found, key=lambda job: (job[0], job[1]))


def run_job(name: str, command: list[str]) -> int:
    """One scheduled job, as its own program in the main project, like a cron line. Its output goes to the
    container's log (docker logs)."""
    say(f"[schedule] {name}: starting ({' '.join(command)})")
    try:
        code = subprocess.run([sys.executable, *command], cwd=MAIN, timeout=JOB_TIMEOUT_SECONDS).returncode
    except subprocess.TimeoutExpired:
        code = -1
        say(f"[schedule] {name}: stopped after {JOB_TIMEOUT_SECONDS // 60} minutes")
    except OSError as e:
        code = -1
        say(f"[schedule] {name}: couldn't start ({e})")
    say(f"[schedule] {name}: {'finished' if code == 0 else f'failed (exit code {code})'}")
    return code


def tick(slots, now: datetime, started: datetime, done: set, runner=run_job) -> list[str]:
    """Start whatever is due, one after another. Returns the names of the jobs it ran."""
    ran = []
    for moment, name, command in due(slots, now, started, done):
        done.add((name, moment.isoformat()))  # marked first: a job that fails is not tried again and again
        runner(name, command)
        ran.append(name)
    return ran


def run_schedule(slots) -> None:
    started, done = datetime.now(ET), set()
    while True:
        try:
            tick(slots, datetime.now(ET), started, done)
        except Exception as e:  # the schedule must outlive any one bad job
            say(f"[schedule] problem: {e}")
        clock.sleep(20)


# ---------------------------------------------------------------------------
# Starting
# ---------------------------------------------------------------------------

def serve() -> None:
    unquoted = unquote_settings()
    mode, port = read_mode(), read_port()
    host = (os.environ.get("HOST") or "0.0.0.0").strip()
    writable_home()
    say(f"Market analyst · version {version()} · {mode} mode")
    if unquoted:
        say(f"Removed the quotes around {', '.join(unquoted)} (a settings file needs none).")
    slots = []
    if mode == "demo":
        app, info = demo_app()
        say(f"Sample data {'made' if info['made'] else 'kept'}: two months of reports up to "
            f"{info['day']:%A %B} {info['day'].day}. Prices, news, filings, runs and answers are simulated: "
            "no AI is called and nothing is sent anywhere.")
        if info["ignored"]:
            say(f"Ignored in demo mode: {', '.join(info['ignored'])}. Add -e MODE=real to use your own keys.")
        if not demo_frontend().is_dir():
            say("No built frontend was found, so only the API is available.")
    else:
        app, notes = real_app()
        slots, schedule_notes = plan_schedule()
        import api
        if api.AUTO_CLOSE:
            schedule_notes.append(f"Schedule: the day's final report is also written after the close, at "
                                  f"{api.AUTO_CLOSE_TIME} New York time (the app's own after-close run).")
        say(f"Your reports, search index and watchlist are in {DATA}.")
        for note in notes + schedule_notes:
            say(note)
    hosts = allowed_hosts()
    say(f"Open http://localhost:{port} (or the port you chose with -p). Stop with Ctrl+C or docker stop.")
    if slots:
        threading.Thread(target=run_schedule, args=(slots,), daemon=True).start()
    import uvicorn
    # Open browser tabs hold a live-updates connection that never ends by itself, so when asked to stop
    # (Ctrl+C, docker stop), wait 2 seconds for requests in progress and then close whatever is left
    uvicorn.run(only_hosts(app, hosts), host=host, port=port, log_level="warning", timeout_graceful_shutdown=STOP_SECONDS)


# ---------------------------------------------------------------------------
# prepare (image build): the demo's copy of the built app
# ---------------------------------------------------------------------------

BANNER_TAG = '<script src="/demo-banner.js" defer></script>'


def add_banner(index_html: str, title: str = "Market Analyst · demo") -> str:
    """Load the demo's banner in the built app's page. Doing it twice changes nothing."""
    if "demo-banner.js" not in index_html:
        at = index_html.find("</head>")
        if at == -1:
            raise ValueError("index.html has no </head>: is it the built app?")
        index_html = index_html[:at] + BANNER_TAG + "\n  " + index_html[at:]
    return re.sub(r"<title>.*?</title>", f"<title>{title}</title>", index_html, count=1, flags=re.S)


def prepare(dist: Path | None = None, target: Path = DEMO_FRONTEND, banner: Path = BANNER) -> Path:
    """Copy the built app and add the banner to the copy. Real mode keeps serving the original."""
    dist = dist or MAIN / "frontend" / "dist"
    if not (dist / "index.html").is_file():
        sys.exit(f"No built app at {dist}. Build the frontend first (npm run build).")
    if not banner.is_file():
        sys.exit(f"{banner} is missing.")
    shutil.rmtree(target, ignore_errors=True)
    shutil.copytree(dist, target)
    index = target / "index.html"
    index.write_text(add_banner(index.read_text(encoding="utf-8")), encoding="utf-8")
    shown = re.sub(r"[^A-Za-z0-9_.\-]", "", version())  # it goes into the page's script, so nothing but plain characters
    (target / "demo-banner.js").write_text(banner.read_text(encoding="utf-8").replace("__VERSION__", shown), encoding="utf-8")
    return target


# ---------------------------------------------------------------------------
# healthcheck and selftest: asking the running app, the way a browser would
# ---------------------------------------------------------------------------

_opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # straight to the app, never through a proxy


def request(method: str, url: str, body=None, headers: dict | None = None, timeout: float = 30):
    """One request. Returns (status, content type, body); a live stream is closed as soon as it answers."""
    data = None if body is None else json.dumps(body).encode()
    headers = {**({"Content-Type": "application/json"} if body is not None else {}), **(headers or {})}
    try:
        with _opener.open(urllib.request.Request(url, data=data, method=method, headers=headers), timeout=timeout) as r:
            kind = r.headers.get_content_type()
            return r.status, kind, b"" if kind == "text/event-stream" else r.read()
    except urllib.error.HTTPError as e:
        with e:
            return e.code, e.headers.get_content_type(), e.read()


def healthcheck(port: int | None = None) -> int:
    try:
        status, _, body = request("GET", f"http://127.0.0.1:{port or read_port()}/api/health", timeout=4)
        return 0 if status == 200 and json.loads(body).get("status") == "ok" else 1
    except (OSError, ValueError):
        return 1


def api_routes() -> list[str]:
    """Every address the API answers GET requests at, read from the app itself, so a new feature's
    addresses are tried without changing this file."""
    if str(MAIN) not in sys.path:
        sys.path.insert(0, str(MAIN))
    import api
    from starlette.routing import Route
    app = api.create_app(frontend_dist=HERE / "no-frontend")
    return sorted({r.path for r in app.routes
                   if isinstance(r, Route) and "GET" in (r.methods or ()) and r.path.startswith("/api/")})


# What to put in the addresses that need something. A new feature whose address needs a new kind of value
# makes the self-test say so: add a line here.
QUERY_SAMPLES = {"/api/search": {"q": "earnings"}, "/api/stocks/search": {"q": "micro"}}


class Checks:
    def __init__(self, out=say):
        self.out, self.passed, self.failed = out, 0, []

    def ok(self, what: str) -> None:
        self.passed += 1
        self.out(f"  ok    {what}")

    def fail(self, what: str, why: str) -> None:
        self.failed.append(what)
        self.out(f"  FAIL  {what}: {why}")

    def skip(self, what: str, why: str) -> None:
        self.out(f"  skip  {what}: {why}")


def _json(body: bytes):
    try:
        return json.loads(body)
    except ValueError:
        return None


def _wait(base: str, path: str, read_state, seconds: float = 60):
    """Ask until a background job has finished. Returns its last state, or None if it never did."""
    end = clock.monotonic() + seconds
    while clock.monotonic() < end:
        status, _, body = request("GET", base + path)
        state = read_state(_json(body) or {}) if status == 200 else None
        if state and state.get("state") in ("finished", "failed"):
            return state
        clock.sleep(0.25)
    return None


def selftest(base: str, mode: str, routes: list[str] | None = None, out=say) -> int:
    """Try the running app. Returns how many checks failed.

    Demo mode expects every address to work, then starts a simulated run, asks a question and checks for
    filings. Real mode only reads (it never starts anything that could cost money) and accepts "nothing
    here yet" answers, since a new installation has no reports."""
    base, checks, demo = base.rstrip("/"), Checks(out), mode == "demo"
    out(f"Self-test of {base} ({mode} mode)")

    # 1. The app answers
    try:
        status, _, body = request("GET", base + "/api/health", timeout=10)
    except OSError as e:
        checks.fail("the app answers", f"nothing is listening at {base} ({e})")
        out("1 problem.")
        return 1
    health = _json(body) or {}
    if status == 200 and health.get("status") == "ok":
        checks.ok(f"the app answers ({health.get('reports')} reports)")
    else:
        checks.fail("the app answers", f"/api/health said {status}")

    # 2. The page and everything it loads
    status, kind, body = request("GET", base + "/")
    page = body.decode("utf-8", "replace")
    if status != 200 or kind != "text/html" or 'id="root"' not in page:
        checks.fail("the page opens", f"/ answered {status} ({kind})")
    else:
        checks.ok("the page opens")
        for link in sorted(set(re.findall(r'(?:src|href)="([^"]+)"', page))):
            if link.startswith(("data:", "http:", "https:", "//", "#")):
                continue
            status, _, body = request("GET", urllib.parse.urljoin(base + "/", link))
            if status == 200 and body:
                checks.ok(f"the page's file {link}")
            else:
                checks.fail(f"the page's file {link}", f"answered {status}")
        if demo and "demo-banner.js" not in page:
            checks.fail("the demo's banner", "the page doesn't load demo-banner.js")
        elif not demo and "demo-banner.js" in page:
            checks.fail("no demo banner in real mode", "the page loads demo-banner.js")

    # 3. Every GET address of the API
    values = {}
    status, _, body = request("GET", base + "/api/watchlist")
    stocks = (_json(body) or {}).get("stocks") or []
    if stocks:
        values["ticker"] = stocks[0]["ticker"]
    status, _, body = request("GET", base + "/api/reports/latest")
    report = (_json(body) or {}) if status == 200 else {}
    values["session_date"] = (report.get("report") or report).get("session_date") or datetime.now(ET).date().isoformat()
    for route in routes if routes is not None else api_routes():
        names = re.findall(r"{(\w+)(?::\w+)?}", route)
        unknown = [n for n in names if n not in values]
        if unknown:
            checks.fail(f"GET {route}", f"the self-test has no sample value for {unknown[0]!r}. Add one to `values` "
                        "in start.py's selftest" + (" (is the watchlist empty?)" if unknown[0] == "ticker" else ""))
            continue
        path = re.sub(r"{(\w+)(?::\w+)?}", lambda m: urllib.parse.quote(str(values[m.group(1)])), route)
        query = QUERY_SAMPLES.get(route)
        url = base + path + ("?" + urllib.parse.urlencode(query) if query else "")
        try:
            status, kind, body = request("GET", url)
        except OSError as e:
            checks.fail(f"GET {path}", f"no answer ({e}). If it is a live stream, it must say text/event-stream")
            continue
        if status == 200:
            checks.ok(f"GET {path}")
        elif status == 400 and not query:
            checks.fail(f"GET {path}", f"it needs something in its address: {(_json(body) or {}).get('error', body[:80])}. "
                        "Add a sample to QUERY_SAMPLES in start.py")
        elif not demo and status in (404, 502, 503):
            checks.skip(f"GET {path}", "nothing saved yet" if status == 404 else "needs the internet")
        else:
            checks.fail(f"GET {path}", f"answered {status}: {body[:120].decode('utf-8', 'replace')}")

    # 4. Only this computer's own pages can use it
    if "*" not in allowed_hosts():
        status, _, _ = request("GET", base + "/api/health", headers={"Host": "other-site.example"})
        if status == 403:
            checks.ok("a request sent to another name is refused")
        else:
            checks.fail("a request sent to another name is refused", f"answered {status}")

    if demo:
        _demo_checks(base, checks)
    else:
        _agent_check(checks)

    count = len(checks.failed)
    out(f"{checks.passed} checks passed, {count} failed." if count else f"All {checks.passed} checks passed.")
    return count


def claude_code() -> str | None:
    """Where the agent's own program (Claude Code) is: inside the claude-agent-sdk package, or on the PATH.
    (The same two places the SDK looks.)"""
    try:
        import claude_agent_sdk
    except ImportError:
        return None
    bundled = Path(claude_agent_sdk.__file__).parent / "_bundled" / ("claude.exe" if os.name == "nt" else "claude")
    return str(bundled) if bundled.is_file() else shutil.which("claude")


def _agent_check(checks: Checks) -> None:
    """Real mode's reports are written by Claude Code, a program that comes inside the claude-agent-sdk
    package. Asking it for its version costs nothing, calls nobody, and proves it is here and can start."""
    what = "the agent's program (Claude Code)"
    program = claude_code()
    if not program:
        checks.fail(what, "it isn't here, so runs, questions and first takes would fail (see the guide's troubleshooting)")
        return
    try:
        result = subprocess.run([program, "--version"], capture_output=True, text=True, timeout=120)
        answer = (result.stdout.strip().splitlines() or [""])[0][:60]
        started = result.returncode == 0 and bool(answer)
    except (OSError, subprocess.SubprocessError) as e:
        answer, started = str(e)[:120], False
    if started:
        checks.ok(f"{what} starts: {answer}")
    else:
        checks.fail(what, f"it is here but didn't start ({answer or 'no answer'})")


def _demo_checks(base: str, checks: Checks) -> None:
    """The simulated AI: a run, a question and a filings check. Safe to start, because nothing in the demo is real."""
    status, _, _ = request("POST", base + "/api/runs", {}, headers={"Origin": "https://other-site.example"})
    if status == 403:
        checks.ok("another website can't start a run")
    else:
        checks.fail("another website can't start a run", f"answered {status}")

    status, _, body = request("POST", base + "/api/runs", {})
    if status in (409, 429):
        checks.skip("Run update now", (_json(body) or {}).get("error", "a run was started moments ago"))
    elif status != 202:
        checks.fail("Run update now", f"answered {status}: {body[:120].decode('utf-8', 'replace')}")
    else:
        run = _wait(base, "/api/runs/current", lambda data: data.get("run"))
        result = (run or {}).get("result") or {}
        if run and run["state"] == "finished" and result.get("type") in ("saved", "skipped"):
            checks.ok("Run update now (simulated): " + (f"{result.get('outcome')} the {result.get('status')} report for "
                                                        f"{result.get('session_date')}" if result["type"] == "saved"
                                                        else result.get("message", "nothing to do")))
        else:
            checks.fail("Run update now", (run or {}).get("error") or "the simulated run didn't finish in a minute")

    status, _, body = request("POST", base + "/api/ask", {"question": "What moved the most this week, and why?"}, timeout=60)
    events = [e for e in (_json(line) for line in body.splitlines() if line.strip()) if isinstance(e, dict)]
    answer = "".join(str(e.get("text", "")) for e in events if e.get("type") == "delta")
    if status == 200 and events and events[-1].get("type") == "done" and len(answer.split()) >= 5:
        checks.ok(f"Ask (simulated): answered in {len(answer.split())} words")
    else:
        problem = next((e.get("error") for e in events if e.get("type") == "error"), None)
        checks.fail("Ask", problem or f"answered {status} without a finished answer")

    status, _, body = request("POST", base + "/api/filings/check", {})
    if status in (409, 429):
        checks.skip("Filings: Check now", (_json(body) or {}).get("error", "checked moments ago"))
    elif status != 202:
        checks.fail("Filings: Check now", f"answered {status}: {body[:120].decode('utf-8', 'replace')}")
    else:
        job = _wait(base, "/api/filings", lambda data: data.get("check"))
        if job and job["state"] == "finished":
            checks.ok("Filings: Check now (simulated SEC)")
        else:
            checks.fail("Filings: Check now", (job or {}).get("error") or "the check didn't finish in a minute")


# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Starts the market analyst app in its container.")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("serve", help="start the app (the default)")
    commands.add_parser("prepare", help="make the demo's copy of the built app (used when the image is built)")
    commands.add_parser("healthcheck", help="exit 0 if the app is answering")
    test = commands.add_parser("selftest", help="try the running app")
    test.add_argument("--url", help="the app's address (default: this container's own)")
    test.add_argument("--mode", choices=["demo", "real"], help="default: the MODE setting")
    args = parser.parse_args()

    if args.command == "prepare":
        say(f"Made the demo's copy of the app in {prepare()}")
    elif args.command == "healthcheck":
        sys.exit(healthcheck())
    elif args.command == "selftest":
        url = args.url or f"http://127.0.0.1:{read_port()}"
        sys.exit(1 if selftest(url, args.mode or read_mode()) else 0)
    else:
        serve()


if __name__ == "__main__":
    main()
```

### container.py

```python
"""Builds, tests and publishes the market analyst app as a Docker image.

    python container.py build      make the image market-agent:local from your two project folders
    python container.py test       start it with networking off and run its self-test (the demo, then real mode)
    python container.py run        try it at http://localhost:8100   (--real for real mode)
    python container.py publish    build, test, then publish it to ghcr.io for Intel/AMD and ARM computers
    python container.py context    only make the clean copy the image is built from, and check it

After adding a feature to the app and the test environment, one command updates the image everyone
downloads:  python container.py publish

This folder sits next to market-agent/ and market-agent-testenv/ and only reads them. The image is never
built from those folders themselves: `context` copies the code (and nothing else) into .build/ here, so
keys, databases, logs and your own watchlist can't end up inside an image other people download.
"""

import argparse
import fnmatch
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

sys.dont_write_bytecode = True                # never leave __pycache__ folders in the other projects
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

HERE = Path(__file__).resolve().parent
MAIN = Path(os.environ.get("MARKET_AGENT_DIR") or HERE.parent / "market-agent").resolve()
TESTENV = Path(os.environ.get("MARKET_AGENT_TESTENV_DIR") or HERE.parent / "market-agent-testenv").resolve()
CONTEXT = HERE / ".build"                     # the clean copy the image is built from
MARKER = ".market-agent-build"                # marks a folder as one this program made (and may replace)
LOCAL_IMAGE = "market-agent:local"
PLATFORMS = "linux/amd64,linux/arm64"         # Intel/AMD computers, and ARM ones (Apple silicon, Raspberry Pi)
BUILDER = "market-agent-builder"
PORT = 8100
MAX_CONTEXT_MB = 20
STARTER_TICKERS = ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]  # the image's watchlist: the demo's stocks, and where real mode starts
TICKER = re.compile(r"[A-Z0-9][A-Z0-9\-]{0,9}")
VERSION = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_.\-]{0,59}")   # it becomes the image's tag, and is shown in the banner

# What goes into the image. Top-level files only, by pattern, so a new feature's files come along by
# themselves. If a feature adds another kind of file (say, a .json the code reads), add its pattern here.
# Of the Markdown files, only prompts (analyst_prompt.md): the guides, reports and test notes that sit in
# market-agent/ are for you, and they quote example keys and folders on your computer.
MAIN_FILES = ("*.py", "*_prompt.md", "requirements.txt")
TESTENV_FILES = ("*.py",)
FRONTEND_FILES = ("package.json", "package-lock.json", "index.html", "vite.config.*")
FRONTEND_FOLDERS = ("src", "public")
OWN_FILES = ("Dockerfile", "start.py", "demo-banner.js")
# ...and what never does, whatever the patterns above say
NEVER = (".*", "test_*", "*_test.py", "conftest.py", "README*", "watchlist.txt", "*.db", "*.db-*", "*.sqlite*",
         "*.log", "*.jsonl", "*.pem", "*.key", "*.zip")
REQUIRED = ("Dockerfile", "start.py", "demo-banner.js", "VERSION", "app/market-agent/api.py",
            "app/market-agent/run_brief.py", "app/market-agent/market_tools.py", "app/market-agent/requirements.txt",
            "app/market-agent/watchlist.txt", "app/market-agent-testenv/testenv.py",
            "app/market-agent-testenv/sample_market.py", "frontend/package.json", "frontend/index.html")
# Never publish anything that looks like a key or a webhook
SECRET_PATTERNS = [re.compile(p) for p in (r"sk-ant-[A-Za-z0-9_\-]{8,}", r"discord(?:app)?\.com/api/webhooks/\d+",
                                           r"\bpa-[A-Za-z0-9_\-]{20,}", r"ghp_[A-Za-z0-9]{20,}",
                                           r"github_pat_[A-Za-z0-9_]{20,}")]
BINARY = (".png", ".jpg", ".jpeg", ".gif", ".ico", ".webp", ".woff", ".woff2")


# ---------------------------------------------------------------------------
# The clean copy the image is built from
# ---------------------------------------------------------------------------

def allowed(path: Path, patterns) -> bool:
    name = path.name
    return (path.is_file() and not path.is_symlink() and any(fnmatch.fnmatch(name, p) for p in patterns)
            and not any(fnmatch.fnmatch(name, p) for p in NEVER))


def copy_top_level(source: Path, target: Path, patterns) -> None:
    target.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.iterdir()):
        if allowed(path, patterns):
            shutil.copyfile(path, target / path.name)


def copy_folder(source: Path, target: Path) -> None:
    """A whole folder of the frontend (src/, public/), except hidden files and anything in NEVER."""
    for path in sorted(source.rglob("*")):
        rel = path.relative_to(source)
        if any(part.startswith(".") or part in ("node_modules", "__pycache__") for part in rel.parts):
            continue
        if allowed(path, ("*",)):
            (target / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target / rel)


def read_tickers(text: str | None) -> list[str]:
    """The stocks for the image's watchlist, from --tickers (or the starter five)."""
    if not text:
        return list(STARTER_TICKERS)
    tickers = [t.strip().upper() for t in text.split(",") if t.strip()]
    bad = [t for t in tickers if not TICKER.fullmatch(t)]
    if bad or not tickers or len(set(tickers)) != len(tickers) or len(tickers) > 25:
        sys.exit("--tickers takes up to 25 different tickers separated by commas, like AAPL,MSFT,NVDA"
                 + (f" (not {', '.join(bad)})" if bad else ""))
    return tickers


def default_version() -> str:
    return date.today().strftime("%Y.%m.%d")


def assemble(out: Path = CONTEXT, tickers: list[str] | None = None, version: str | None = None) -> list[str]:
    """Make the clean copy. Returns the files in it. Your project folders are only read."""
    out, version = Path(out).resolve(), version or default_version()
    if not VERSION.fullmatch(version):
        sys.exit(f"--version can only have letters, digits, dots, dashes and underscores (like 1.4 or 2026.11.12), not {version!r}.")
    for folder in (MAIN, TESTENV):
        if out == folder or folder in out.parents or out in folder.parents:
            sys.exit(f"The build folder can't be inside (or around) {folder.name}/.")
        if HERE == folder or folder in HERE.parents:
            sys.exit("The container folder must be next to market-agent/ and market-agent-testenv/, not inside them.")
    if not (MAIN / "api.py").is_file():
        sys.exit(f"Can't find the main project at {MAIN}. Set MARKET_AGENT_DIR to its folder.")
    if not (TESTENV / "testenv.py").is_file():
        sys.exit(f"Can't find the test environment at {TESTENV}. Set it up first (market-agent-test-enviro.md), "
                 "or set MARKET_AGENT_TESTENV_DIR.")
    if out.exists() and any(out.iterdir()) and not (out / MARKER).is_file():
        sys.exit(f"{out} has files this program didn't make, so it won't replace them. Remove it or choose another folder.")
    shutil.rmtree(out, ignore_errors=True)
    out.mkdir(parents=True)
    (out / MARKER).write_text("Made by container.py. Safe to delete: it is rebuilt every time.\n")

    copy_top_level(MAIN, out / "app" / "market-agent", MAIN_FILES)
    (out / "app" / "market-agent" / "watchlist.txt").write_text("\n".join(tickers or STARTER_TICKERS) + "\n")
    copy_top_level(TESTENV, out / "app" / "market-agent-testenv", TESTENV_FILES)
    frontend = MAIN / "frontend"
    if frontend.is_dir():
        copy_top_level(frontend, out / "frontend", FRONTEND_FILES)
        for name in FRONTEND_FOLDERS:
            if (frontend / name).is_dir():
                copy_folder(frontend / name, out / "frontend" / name)
    for name in OWN_FILES:
        if (HERE / name).is_file():
            shutil.copyfile(HERE / name, out / name)
    (out / "VERSION").write_text(version + "\n")
    return list_files(out)


def list_files(out: Path) -> list[str]:
    return sorted(p.relative_to(out).as_posix() for p in out.rglob("*") if p.is_file() and p.name != MARKER)


def context_size(out: Path) -> int:
    return sum(p.stat().st_size for p in out.rglob("*") if p.is_file())


def check_context(out: Path = CONTEXT) -> list[str]:
    """Reasons not to build: missing pieces, anything that looks like a key, or something personal."""
    problems = []
    files = set(list_files(out)) if out.is_dir() else set()
    for name in REQUIRED:
        if name not in files:
            hint = {"frontend/package.json": ": set up the frontend first (market-agent-frontend.md, section 5)",
                    "app/market-agent-testenv/testenv.py": ": set up the test environment first"}.get(name, "")
            problems.append(f"{name} is missing{hint}")
    tools = out / "app" / "market-agent" / "market_tools.py"
    if tools.is_file() and 'os.environ.get("WATCHLIST_FILE")' not in tools.read_text(encoding="utf-8"):
        problems.append("market_tools.py doesn't read the WATCHLIST_FILE setting yet (see the container guide): "
                        "in real mode the agent would use the image's starter watchlist instead of yours")
    private = [s for s in {str(Path.home()), str(MAIN), str(TESTENV), str(HERE.parent)} if len(s) > 3]
    for rel in sorted(files):
        path = out / rel
        if any(fnmatch.fnmatch(path.name, p) for p in NEVER if p != "watchlist.txt"):  # (the starter list is ours)
            problems.append(f"{rel} shouldn't be in an image")
        if path.suffix.lower() in BINARY:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        for pattern in SECRET_PATTERNS:
            if pattern.search(text):
                problems.append(f"{rel} contains something that looks like a key or webhook ({pattern.pattern[:12]}…)")
        for folder in private:
            if folder in text:
                problems.append(f"{rel} mentions a folder on your computer ({folder})")
                break
    if out.is_dir() and context_size(out) > MAX_CONTEXT_MB * 1e6:
        problems.append(f"the copy is over {MAX_CONTEXT_MB} MB: something that isn't code was copied")
    return problems


def make_context(args) -> Path:
    files = assemble(CONTEXT, read_tickers(getattr(args, "tickers", None)), getattr(args, "version", None))
    problems = check_context(CONTEXT)
    if problems:
        sys.exit("Not building:\n" + "\n".join(f"  - {p}" for p in problems))
    print(f"Clean copy: {len(files)} files, {context_size(CONTEXT) / 1e6:.1f} MB in {CONTEXT} "
          "(no keys, databases, logs or personal watchlist)")
    return CONTEXT


# ---------------------------------------------------------------------------
# Where it is published
# ---------------------------------------------------------------------------

GITHUB_REMOTE = re.compile(r"^(?:https://github\.com/|git@github\.com:)([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")
IMAGE_NAME = re.compile(r"[a-z0-9]+(?:[.\-][a-z0-9]+)*(?::\d+)?(?:/[a-z0-9]+(?:[._\-]+[a-z0-9]+)*)+")


def origin_remote() -> str:
    try:
        return subprocess.run(["git", "-C", str(MAIN), "remote", "get-url", "origin"],
                              capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""


def repo_page(remote: str) -> str:
    """'git@github.com:You/market-agent.git' -> 'https://github.com/You/market-agent' ('' if not GitHub)."""
    match = GITHUB_REMOTE.match(remote.strip())
    return f"https://github.com/{match.group(1)}/{match.group(2)}" if match else ""


def image_for(remote: str) -> str:
    """The image's name in GitHub's registry, from the repository's address ('' if not GitHub).
    Image names are always lower case."""
    match = GITHUB_REMOTE.match(remote.strip())
    return f"ghcr.io/{match.group(1).lower()}/{match.group(2).lower()}" if match else ""


def choose_image(given: str | None, remote: str) -> str:
    image = (given or os.environ.get("CONTAINER_IMAGE") or image_for(remote)).strip()
    if not image:
        sys.exit("Say where to publish it: --image ghcr.io/YOUR-GITHUB-NAME/market-agent "
                 "(market-agent/ has no GitHub address to work it out from).")
    if not IMAGE_NAME.fullmatch(image):
        sys.exit(f"{image!r} isn't an image name. Use lower case and no tag, like ghcr.io/your-github-name/market-agent.")
    return image


# ---------------------------------------------------------------------------
# Docker
# ---------------------------------------------------------------------------

def docker(*args, capture: bool = False, check: bool = True) -> subprocess.CompletedProcess:
    result = subprocess.run(["docker", *args], capture_output=capture, text=True)
    if check and result.returncode != 0:
        if capture:
            sys.stderr.write(result.stdout + result.stderr)
        sys.exit(f"`docker {' '.join(args[:2])}` failed (see above).")
    return result


def need_docker() -> None:
    if not shutil.which("docker"):
        sys.exit("Docker wasn't found. Install Docker Desktop (docker.com/products/docker-desktop), start it, "
                 "and open a new terminal.")
    if subprocess.run(["docker", "info"], capture_output=True).returncode != 0:
        sys.exit("Docker is installed but isn't running. Start Docker Desktop and try again.")


def extra_flags() -> list[str]:
    """Extra `docker build` flags from CONTAINER_BUILD_FLAGS, e.g. for a company proxy or another base image:
    CONTAINER_BUILD_FLAGS="--build-arg PYTHON_IMAGE=python:3.13-slim"."""
    return shlex.split(os.environ.get("CONTAINER_BUILD_FLAGS", ""))


def build_args(version: str, source: str) -> list[str]:
    return ["--build-arg", f"VERSION={version}", "--build-arg", f"SOURCE={source}"]


def build_command(context: Path, tag: str, version: str, source: str = "", extra=()) -> list[str]:
    """Build for this computer's own processor, into Docker here."""
    return ["build", "--tag", tag, *build_args(version, source), *extra, str(context)]


def publish_command(context: Path, image: str, version: str, source: str = "", platforms: str = PLATFORMS,
                    builder: str = BUILDER, extra=()) -> list[str]:
    """Build for every platform and send the result straight to the registry, as :latest and :VERSION."""
    command = ["buildx", "build"]
    if builder != "default":
        command += ["--builder", builder]
    return [*command, "--platform", platforms, "--tag", f"{image}:latest", "--tag", f"{image}:{version}",
            *build_args(version, source), *extra, "--push", str(context)]


def ensure_builder(name: str = BUILDER) -> None:
    """Building for two kinds of processor at once needs a builder of the 'docker-container' kind.
    This makes one the first time, without changing which builder your other projects use."""
    if name == "default" or docker("buildx", "inspect", name, capture=True, check=False).returncode == 0:
        return
    print(f"Creating the builder {name} (once)...")
    docker("buildx", "create", "--name", name, "--driver", "docker-container")


def version_in(context: Path) -> str:
    return (context / "VERSION").read_text().strip()


def build(args) -> None:
    need_docker()
    context = make_context(args)
    docker(*build_command(context, LOCAL_IMAGE, version_in(context), repo_page(origin_remote()), extra_flags()))
    print(f"Built {LOCAL_IMAGE} (version {version_in(context)}). Next: python container.py test")


# ---------------------------------------------------------------------------
# Testing the image
# ---------------------------------------------------------------------------

# What an open browser tab does: connect to the live-updates stream and stay connected
OPEN_TAB = ("import time, urllib.request; "
            f"r = urllib.request.build_opener(urllib.request.ProxyHandler({{}})).open('http://127.0.0.1:{PORT}/api/events'); "
            "time.sleep(120)")


def started(name: str, seconds: float = 90) -> bool:
    """Wait until the app in a container answers. False if it stopped or never did."""
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        state = docker("inspect", "--format", "{{.State.Running}}", name, capture=True, check=False).stdout.strip()
        if state != "true":
            return False
        if docker("exec", name, "python", "/app/start.py", "healthcheck", capture=True, check=False).returncode == 0:
            return True
        time.sleep(1)
    return False


def remove(name: str) -> None:
    docker("rm", "--force", name, capture=True, check=False)


def tried(name: str, what: str, problems: list[str], ok: bool, show_log: bool = True) -> bool:
    print(f"  {'ok  ' if ok else 'FAIL'}  {what}")
    if not ok:
        problems.append(what)
        if show_log:
            log = docker("logs", "--tail", "40", name, capture=True, check=False)
            print("        the container's log:\n" + "\n".join("        " + ln for ln in (log.stdout + log.stderr).splitlines()))
    return ok


def fetch(url: str) -> int:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))  # this computer, not a proxy
    try:
        with opener.open(url, timeout=10) as response:
            return response.status
    except OSError as e:
        return getattr(e, "code", 0) or 0


def test_image(image: str = LOCAL_IMAGE, port_check: bool = True) -> list[str]:
    """Run the image the way people will, and return what went wrong (nothing, if it is fit to publish)."""
    problems: list[str] = []
    name = f"market-agent-test-{os.getpid()}"

    print("1. The demo, with networking switched off (proof it needs nothing from the internet)")
    remove(name)
    docker("run", "--detach", "--name", name, "--network", "none", image, capture=True)
    try:
        if tried(name, "the demo starts", problems, started(name)):
            result = docker("exec", name, "python", "/app/start.py", "selftest", capture=True, check=False)
            print("\n".join("      " + ln for ln in result.stdout.splitlines()))
            tried(name, "the demo passes its self-test offline", problems, result.returncode == 0)
            user = docker("exec", name, "id", "-u", capture=True, check=False).stdout.strip()
            tried(name, f"the app runs as an ordinary user, not as root (user {user})", problems, user not in ("", "0"), False)
            # A browser tab holds a live-updates connection open for as long as it is open. Stopping must not wait for it.
            docker("exec", "--detach", name, "python", "-c", OPEN_TAB, capture=True, check=False)
            time.sleep(1)
            began = time.monotonic()
            docker("stop", "--time", "20", name, capture=True, check=False)
            took = time.monotonic() - began
            code = docker("inspect", "--format", "{{.State.ExitCode}}", name, capture=True, check=False).stdout.strip()
            tried(name, f"docker stop ends it promptly, even with a tab open ({took:.0f}s, exit code {code})", problems,
                  code in ("0", "143") and took < 15)  # 137 would mean Docker gave up waiting and killed it
    finally:
        remove(name)

    print("2. Real mode, with no key and networking off (it must start, explain what's missing, and call nothing)")
    docker("run", "--detach", "--name", name, "--network", "none", "--env", "MODE=real", image, capture=True)
    try:
        if tried(name, "real mode starts without a key", problems, started(name)):
            result = docker("exec", name, "python", "/app/start.py", "selftest", capture=True, check=False)
            print("\n".join("      " + ln for ln in result.stdout.splitlines()))
            tried(name, "real mode passes its (read-only) self-test", problems, result.returncode == 0)
            listed = docker("exec", name, "cat", "/data/watchlist.txt", capture=True, check=False).stdout.split()
            tried(name, f"it starts a watchlist in /data ({', '.join(listed) or 'empty'})", problems, bool(listed), False)
            log = docker("logs", name, capture=True, check=False)
            said = "ANTHROPIC_API_KEY" in log.stdout + log.stderr
            tried(name, "its log says the key is missing", problems, said)
    finally:
        remove(name)

    if port_check:
        print("3. The demo again, opened from this computer the way a browser does")
        docker("run", "--detach", "--name", name, "--publish", f"127.0.0.1::{PORT}", image, capture=True)
        try:
            if tried(name, "the demo starts", problems, started(name)):
                where = docker("port", name, f"{PORT}/tcp", capture=True, check=False).stdout.split()
                address = f"http://localhost:{where[0].rsplit(':', 1)[1]}" if where else ""
                ok = bool(address) and fetch(address + "/api/health") == 200 and fetch(address + "/") == 200
                tried(name, f"the app opens at {address or 'its published port'}", problems, ok)
        finally:
            remove(name)
    return problems


def test(args) -> None:
    need_docker()
    if docker("image", "inspect", args.image, capture=True, check=False).returncode != 0:
        sys.exit(f"No image called {args.image} yet. Run: python container.py build")
    problems = test_image(args.image, port_check=not args.no_port_check)
    if problems:
        sys.exit(f"{len(problems)} problem{'s' if len(problems) != 1 else ''}: don't publish this image yet.")
    print("The image works. Next: python container.py publish")


# ---------------------------------------------------------------------------
# Trying it, and publishing it
# ---------------------------------------------------------------------------

def run_command(image: str, real: bool = False, port: int = PORT) -> list[str]:
    command = ["run", "--rm", "--name", "market-agent", "--publish", f"127.0.0.1:{port}:{PORT}"]
    if real:  # keys are passed through from this terminal's settings (never written down), data stays in a volume
        command += ["--env", "MODE=real", "--env", "ANTHROPIC_API_KEY", "--env", "SEC_CONTACT", "--env", "VOYAGE_API_KEY",
                    "--env", "DISCORD_WEBHOOK_URL", "--env", "SCHEDULE", "--volume", "market-agent-data:/data"]
    return [*command, image]


def run(args) -> None:
    need_docker()
    print(f"Starting {args.image} at http://localhost:{args.port} (Ctrl+C to stop)")
    sys.exit(docker(*run_command(args.image, args.real, args.port), check=False).returncode)


def visitor_commands(image: str) -> str:
    return (f"  The demo (no account, no key, works offline once downloaded):\n"
            f"    docker run --rm -p 127.0.0.1:{PORT}:{PORT} {image}\n"
            f"  Then open http://localhost:{PORT}\n"
            f"  To get a newer version later:\n"
            f"    docker pull {image}")


def publish(args) -> None:
    need_docker()
    remote = origin_remote()
    image = choose_image(args.image, remote)
    context = make_context(args)
    version, source = version_in(context), repo_page(remote)
    if not args.skip_test:
        print(f"Building {LOCAL_IMAGE} to test it first...")
        docker(*build_command(context, LOCAL_IMAGE, version, source, extra_flags()))
        problems = test_image(LOCAL_IMAGE, port_check=not args.no_port_check)
        if problems:
            sys.exit(f"{len(problems)} problem{'s' if len(problems) != 1 else ''}: nothing was published.")
    ensure_builder(args.builder)
    print(f"Building for {args.platforms} and publishing {image}:latest and {image}:{version} (this takes a few minutes)...")
    result = docker(*publish_command(context, image, version, source, args.platforms, args.builder, extra_flags()), check=False)
    if result.returncode != 0:
        sys.exit("Publishing failed (see above). The usual causes:\n"
                 "  - not signed in to the registry: docker login ghcr.io -u YOUR-GITHUB-NAME (the password is a "
                 "personal access token (classic) with the write:packages scope)\n"
                 "  - the image name isn't under your own GitHub name: use --image ghcr.io/YOUR-GITHUB-NAME/market-agent\n"
                 "  - this Docker can't build for other processors: try --platforms linux/amd64 (or your own) for now")
    print(f"Published {image}:latest and {image}:{version}.")
    print("If this is the first time, make the package public on GitHub (the guide, section 6), then anyone can run:")
    print(visitor_commands(image))


def context(args) -> None:
    out = make_context(args)
    for name in list_files(out):
        print(f"  {name}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build, test and publish the market analyst app as a Docker image.")
    commands = parser.add_subparsers(dest="command", required=True)

    def content(p):
        p.add_argument("--tickers", help="the image's watchlist, comma-separated (default: AAPL,MSFT,NVDA,AMZN,JPM). "
                                         "Your own watchlist.txt is never copied")
        p.add_argument("--version", help="the version shown in the app and used as the image's tag (default: today's date)")

    content(commands.add_parser("context", help="make the clean copy the image is built from, and check it"))
    content(commands.add_parser("build", help=f"build {LOCAL_IMAGE} for this computer"))
    t = commands.add_parser("test", help="run the image's checks")
    t.add_argument("--image", default=LOCAL_IMAGE)
    t.add_argument("--no-port-check", action="store_true", help="skip opening the app from this computer")
    r = commands.add_parser("run", help="try the image at http://localhost:8100")
    r.add_argument("--image", default=LOCAL_IMAGE)
    r.add_argument("--port", type=int, default=PORT)
    r.add_argument("--real", action="store_true", help="real mode, with this terminal's ANTHROPIC_API_KEY and a data volume")
    p = commands.add_parser("publish", help="build, test and publish to a registry")
    content(p)
    p.add_argument("--image", help="where to publish (default: ghcr.io/OWNER/REPOSITORY, from market-agent's GitHub address)")
    p.add_argument("--platforms", default=PLATFORMS, help=f"default: {PLATFORMS}")
    p.add_argument("--builder", default=BUILDER, help="the buildx builder to use ('default' for Docker's own)")
    p.add_argument("--skip-test", action="store_true", help="publish without testing first (not recommended)")
    p.add_argument("--no-port-check", action="store_true", help="skip opening the app from this computer")
    args = parser.parse_args()
    {"context": context, "build": build, "test": test, "run": run, "publish": publish}[args.command](args)


if __name__ == "__main__":
    main()
```

### demo-banner.js

```javascript
/* The banner on the container's demo. `start.py prepare` adds it to a copy of the built app when the
   image is made; the app itself is unchanged, and in real mode this file isn't loaded at all.

   Unlike the GitHub Pages demo, nothing here stands in for the API: the container runs the real API,
   which the test environment points at simulated data. */
(function () {
  'use strict'

  const VERSION = '__VERSION__' // filled in by `start.py prepare`

  function addBanner() {
    if (document.querySelector('.demo-banner')) return
    const style = document.createElement('style')
    style.textContent = `
      .demo-banner { padding: 8px 16px; text-align: center; font-size: 0.875rem; line-height: 1.45;
        background: var(--live-bg, #fef3c7); color: var(--text, #1c2430); border-bottom: 1px solid var(--border, #e2e6eb); }
      .demo-banner .demo-version { color: var(--muted, #5b6675); white-space: nowrap; }`
    document.head.appendChild(style)
    const bar = document.createElement('div')
    bar.className = 'demo-banner'
    bar.setAttribute('role', 'note')
    const strong = document.createElement('strong')
    strong.textContent = 'Demo with sample data.'
    bar.append(
      strong,
      ' Prices, news, company filings, runs and answers are simulated, and no AI is called. Everything starts again when the container restarts.',
    )
    if (VERSION && !VERSION.startsWith('__')) {
      const version = document.createElement('span')
      version.className = 'demo-version'
      version.textContent = ` Version ${VERSION}`
      bar.append(version)
    }
    document.body.prepend(bar)
  }

  if (document.body) addBanner()
  else document.addEventListener('DOMContentLoaded', addBanner)
})()
```

### test_container.py

```python
"""Checks for the container: the clean copy the image is built from, the start program (demo mode, real
mode, the schedule, the self-test) and the commands that build and publish it.

Run from this folder:  pytest -v   (no Docker, internet, npm, GitHub account or keys needed)

To also check an image you have built (python container.py build), name it:
    CONTAINER_TEST_IMAGE=market-agent:local pytest -v
"""

import glob
import hashlib
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import container  # noqa: E402  (turns off __pycache__ folders before anything else loads)
import start  # noqa: E402

ET = ZoneInfo("America/New_York")
END = date(2026, 11, 6)  # a Friday
SKIP = {".venv", "node_modules", ".git", "__pycache__", ".pytest_cache", "data", "frontend-dist", "dist"}
SETTINGS = ("MODE", "PORT", "HOST", "ALLOWED_HOSTS", "SCHEDULE", "RUN_TIMES", "CALENDAR_TIMES", "FILINGS_TIMES",
            "AUTO_CLOSE_RUN", "CONTAINER_IMAGE", "CONTAINER_BUILD_FLAGS", *start.KEYS)
KEPT = ("REPORTS_DB", "SEARCH_DB", "WATCHLIST_FILE", "HOME", "MARKET_AGENT_DIR")


def snapshot(folder: Path) -> dict:
    """Every file in a folder (except installed packages, databases and build output), with its contents' hash."""
    found = {}
    for path in sorted(folder.rglob("*")):
        rel = path.relative_to(folder)
        if SKIP & set(rel.parts) or path.name.startswith(("reports.db", "search.db")):
            continue
        found[str(rel)] = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else "folder"
    return found


MAIN_BEFORE, TESTENV_BEFORE = snapshot(start.MAIN), snapshot(start.TESTENV)


@pytest.fixture(autouse=True)
def clean_settings(monkeypatch):
    """Each check starts without container settings or keys, and leaves the environment as it found it."""
    for name in SETTINGS:
        monkeypatch.delenv(name, raising=False)
    before = {name: os.environ.get(name) for name in KEPT}
    yield
    for name, value in before.items():
        if value is None:
            os.environ.pop(name, None)
        else:
            os.environ[name] = value


def write(path: Path, text: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    return path


@pytest.fixture
def projects(tmp_path, monkeypatch):
    """Two small stand-in project folders with everything a real one collects: code, plus keys, databases,
    logs, tests, installed packages and a personal watchlist that must all stay out of the image."""
    main, testenv = tmp_path / "market-agent", tmp_path / "market-agent-testenv"
    for name in ("api.py", "run_brief.py", "reports_db.py", "new_feature.py"):
        write(main / name, f"# {name}\n")
    write(main / "market_tools.py", 'import os\nWATCHLIST_FILE = os.environ.get("WATCHLIST_FILE") or "watchlist.txt"\n')
    write(main / "analyst_prompt.md", "You are an analyst.\n")
    write(main / "requirements.txt", "starlette\nuvicorn\n")
    write(main / "watchlist.txt", "TSLA\nPLTR  # my private pick\n")
    write(main / ".env", "ANTHROPIC_API_KEY=not-in-the-image\n")
    for name in ("reports.db", "reports.db-wal", "search.db", "run.log", "alerts_outbox.jsonl", "backup.zip", "README.md",
                 "market-agent-alerts.md", "test-case-reporting.md", "report.md", "test_local.py", "tests/test_api.py", "tests/conftest.py", "__pycache__/api.cpython-312.pyc", ".git/config"):
        write(main / name, "KEEP-OUT\n")
    frontend = main / "frontend"
    write(frontend / "package.json", '{"scripts": {"build": "vite build"}}\n')
    write(frontend / "package-lock.json", "{}\n")
    write(frontend / "index.html", '<!doctype html><html><head><title>Market Analyst</title></head><body><div id="root"></div></body></html>\n')
    write(frontend / "vite.config.js", "export default {}\n")
    write(frontend / ".npmrc", "//registry.npmjs.org/:_authToken=KEEP-OUT\n")
    write(frontend / "src" / "main.jsx", "import './App.jsx'\n")
    write(frontend / "src" / "components" / "NewTab.jsx", "export default function NewTab() {}\n")
    write(frontend / "src" / ".DS_Store", "junk")
    write(frontend / "src" / ".cache" / "deps.js", "// KEEP-OUT\n")
    write(frontend / "public" / "logo.svg", "<svg/>\n")
    write(frontend / "node_modules" / "react" / "index.js", "module.exports = 'KEEP-OUT'\n")
    write(frontend / "dist" / "index.html", "<html>an old build: KEEP-OUT</html>\n")
    write(testenv / "testenv.py", "# testenv\n")
    write(testenv / "sample_market.py", "# sample market\n")
    write(testenv / "test_testenv.py", "KEEP-OUT\n")
    write(testenv / "data" / "reports.db", "KEEP-OUT\n")
    write(testenv / "data" / "watchlist.txt", "TSLA\n")
    write(testenv / "frontend-dist" / "index.html", "<html>a build: KEEP-OUT</html>\n")
    monkeypatch.setattr(container, "MAIN", main)
    monkeypatch.setattr(container, "TESTENV", testenv)
    return main, testenv


# ---------------------------------------------------------------------------
# The clean copy the image is built from
# ---------------------------------------------------------------------------

def test_the_copy_holds_the_code_and_nothing_personal(projects, tmp_path):
    files = container.assemble(tmp_path / "build", version="2026.11.06")
    assert files == sorted([
        "Dockerfile", "VERSION", "demo-banner.js", "start.py",
        "app/market-agent/analyst_prompt.md", "app/market-agent/api.py", "app/market-agent/market_tools.py",
        "app/market-agent/new_feature.py", "app/market-agent/reports_db.py", "app/market-agent/requirements.txt",
        "app/market-agent/run_brief.py", "app/market-agent/watchlist.txt",
        "app/market-agent-testenv/sample_market.py", "app/market-agent-testenv/testenv.py",
        "frontend/index.html", "frontend/package-lock.json", "frontend/package.json", "frontend/vite.config.js",
        "frontend/public/logo.svg", "frontend/src/components/NewTab.jsx", "frontend/src/main.jsx"])
    assert (tmp_path / "build" / "VERSION").read_text() == "2026.11.06\n"
    assert container.check_context(tmp_path / "build") == []
    everything = "".join(p.read_text(errors="ignore") for p in (tmp_path / "build").rglob("*") if p.is_file())
    assert "KEEP-OUT" not in everything and "not-in-the-image" not in everything and "TSLA" not in everything


def test_a_new_features_files_come_along_without_changing_anything(projects, tmp_path):
    main, testenv = projects
    write(main / "portfolio.py", "# a feature added next month\n")
    write(main / "portfolio_prompt.md", "prompt\n")
    write(main / "frontend" / "src" / "components" / "PortfolioTab.jsx", "export default 1\n")
    write(testenv / "sample_portfolio.py", "# its simulated data\n")
    files = container.assemble(tmp_path / "build")
    assert {"app/market-agent/portfolio.py", "app/market-agent/portfolio_prompt.md",
            "frontend/src/components/PortfolioTab.jsx", "app/market-agent-testenv/sample_portfolio.py"} <= set(files)


def test_your_own_watchlist_never_goes_in(projects, tmp_path):
    out = tmp_path / "build"
    container.assemble(out)
    assert (out / "app/market-agent/watchlist.txt").read_text().split() == ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]
    container.assemble(out, tickers=["KO", "PEP"])
    assert (out / "app/market-agent/watchlist.txt").read_text() == "KO\nPEP\n"
    assert not any("PLTR" in p.read_text(errors="ignore") for p in out.rglob("*") if p.is_file())


def test_the_tickers_option_is_checked():
    assert container.read_tickers(None) == container.read_tickers("") == ["AAPL", "MSFT", "NVDA", "AMZN", "JPM"]
    assert container.read_tickers(" aapl, brk-b ,msft ") == ["AAPL", "BRK-B", "MSFT"]
    for bad in ("AAPL;rm -rf", "AAPL,AAPL", "A B", ",".join(f"T{i}" for i in range(26)), "*AAPL", "../x"):
        with pytest.raises(SystemExit) as stopped:
            container.read_tickers(bad)
        assert "--tickers takes up to 25 different tickers" in str(stopped.value)


def test_the_version_can_only_be_plain_characters(projects, tmp_path):
    for good in ("1.4", "2026.11.12", "v2-beta_1"):
        container.assemble(tmp_path / "build", version=good)
        assert (tmp_path / "build" / "VERSION").read_text() == good + "\n"
    for bad in ("1.4 final", "'; alert(1); '", "latest/../x", "", "-rc1", "x" * 61):
        if bad == "":
            continue  # (nothing given means today's date)
        with pytest.raises(SystemExit) as stopped:
            container.assemble(tmp_path / "build", version=bad)
        assert "--version can only have letters, digits, dots, dashes and underscores" in str(stopped.value)
    assert (tmp_path / "build" / "VERSION").read_text() == "v2-beta_1\n"  # a refused version changes nothing


def test_a_symlink_is_not_followed_out_of_the_project(projects, tmp_path):
    if not hasattr(os, "symlink") or sys.platform == "win32":
        pytest.skip("needs symlinks")
    main, _ = projects
    secret = write(tmp_path / "elsewhere" / "secrets.py", "TOKEN = 'outside the project'\n")
    os.symlink(secret, main / "linked.py")
    os.symlink(secret, main / "frontend" / "src" / "linked.js")
    files = container.assemble(tmp_path / "build")
    assert not any("linked" in f for f in files)


@pytest.mark.parametrize("secret", ["sk-ant-api03-abcdefgh12345678", "https://discord.com/api/webhooks/123456789/abcDEF",
                                    "pa-abcdefghijklmnopqrstuvwx", "ghp_abcdefghijklmnopqrstuvwxyz0123",
                                    "github_pat_11ABCDEFG0abcdefghijkl_mnop"])
def test_anything_that_looks_like_a_key_stops_the_build(projects, tmp_path, secret, monkeypatch):
    main, _ = projects
    write(main / "new_feature.py", f'KEY = "{secret}"  # pasted in while testing\n')
    out = tmp_path / "build"
    container.assemble(out)
    problems = container.check_context(out)
    assert len(problems) == 1 and problems[0].startswith("app/market-agent/new_feature.py contains something that looks like a key")
    monkeypatch.setattr(container, "CONTEXT", out)
    with pytest.raises(SystemExit) as stopped:
        container.make_context(type("Args", (), {"tickers": None, "version": None}))
    assert "Not building" in str(stopped.value) and secret not in str(stopped.value)


def test_a_folder_on_your_computer_named_in_the_code_is_flagged(projects, tmp_path):
    main, _ = projects
    write(main / "new_feature.py", f'LOG = r"{main}/run.log"\n')
    container.assemble(tmp_path / "build")
    assert any("mentions a folder on your computer" in p for p in container.check_context(tmp_path / "build"))


def test_missing_pieces_are_named(projects, tmp_path, monkeypatch):
    main, testenv = projects
    (main / "frontend" / "package.json").unlink()
    container.assemble(tmp_path / "build")
    assert container.check_context(tmp_path / "build") == [
        "frontend/package.json is missing: set up the frontend first (market-agent-frontend.md, section 5)"]
    (testenv / "testenv.py").unlink()
    with pytest.raises(SystemExit) as stopped:
        container.assemble(tmp_path / "build")
    assert "Can't find the test environment" in str(stopped.value)
    monkeypatch.setattr(container, "MAIN", tmp_path / "nowhere")
    with pytest.raises(SystemExit) as stopped:
        container.assemble(tmp_path / "build")
    assert "Can't find the main project" in str(stopped.value)
    assert "is missing" in "\n".join(container.check_context(tmp_path / "never-made"))


def test_an_app_without_the_watchlist_setting_is_caught(projects, tmp_path):
    main, _ = projects
    write(main / "market_tools.py", 'WATCHLIST_FILE = "watchlist.txt"\n')  # as it was before the container guide
    container.assemble(tmp_path / "build")
    assert any("market_tools.py doesn't read the WATCHLIST_FILE setting" in p for p in container.check_context(tmp_path / "build"))


def test_the_copy_is_made_fresh_and_only_replaces_its_own_folder(projects, tmp_path):
    main, _ = projects
    out = tmp_path / "build"
    container.assemble(out)
    write(out / "app" / "market-agent" / "removed_feature.py", "# left over from an earlier build\n")
    (main / "new_feature.py").unlink()
    files = container.assemble(out)
    assert "app/market-agent/removed_feature.py" not in files and "app/market-agent/new_feature.py" not in files

    theirs = tmp_path / "documents"
    write(theirs / "thesis.txt", "years of work\n")
    with pytest.raises(SystemExit) as stopped:
        container.assemble(theirs)
    assert "didn't make" in str(stopped.value) and (theirs / "thesis.txt").read_text() == "years of work\n"
    for inside in (main / "build", main, main.parent):
        with pytest.raises(SystemExit) as stopped:
            container.assemble(inside)
        assert "can't be inside" in str(stopped.value) or "didn't make" in str(stopped.value)
    assert (main / "api.py").is_file()


def test_your_real_projects_make_a_clean_copy(tmp_path):
    files = container.assemble(tmp_path / "build")
    code = sorted(p.name for p in container.MAIN.glob("*.py") if not p.name.startswith("test_"))
    assert code and all(f"app/market-agent/{name}" in files for name in code)
    assert {"app/market-agent-testenv/testenv.py", "app/market-agent-testenv/sample_market.py", "start.py", "Dockerfile"} <= set(files)
    assert not any("/tests/" in f or "/test_" in f or f.endswith((".db", ".env", ".log")) for f in files)
    assert (tmp_path / "build" / "app/market-agent/watchlist.txt").read_text() == "AAPL\nMSFT\nNVDA\nAMZN\nJPM\n"
    # (frontend/package.json is only there once the frontend is set up with npm, as its guide describes)
    assert [p for p in container.check_context(tmp_path / "build") if "frontend/package" not in p] == []


# ---------------------------------------------------------------------------
# The Dockerfile
# ---------------------------------------------------------------------------

def dockerfile() -> str:
    return (HERE / "Dockerfile").read_text()


def instructions() -> list[str]:
    """The Dockerfile's instructions, with continued lines joined and comments dropped."""
    text = re.sub(r"\\\n", " ", "\n".join(ln for ln in dockerfile().splitlines() if not ln.lstrip().startswith("#")))
    return [" ".join(line.split()) for line in text.splitlines() if line.strip()]


def test_everything_the_dockerfile_copies_is_in_the_copy(projects, tmp_path):
    out = tmp_path / "build"
    container.assemble(out)
    copies = [i.split()[1:] for i in instructions() if i.startswith("COPY ") and "--from=" not in i]
    assert len(copies) >= 5
    for *sources, _target in copies:
        for source in sources:
            assert glob.glob(str(out / source)), f"the Dockerfile copies {source}, which the clean copy doesn't have"
    assert not any(i.startswith("ADD ") for i in instructions())


def test_the_image_runs_as_an_ordinary_user_with_a_health_check():
    lines = instructions()
    users = [i for i in lines if i.startswith("USER ")]
    assert users == ["USER app"] and lines.index("USER app") > max(i for i, ln in enumerate(lines) if ln.startswith("RUN "))
    assert any(i.startswith("HEALTHCHECK") and '"/app/start.py", "healthcheck"' in i for i in lines)
    assert 'ENTRYPOINT ["tini", "--", "python", "/app/start.py"]' in lines
    assert f"EXPOSE {container.PORT}" in lines and container.PORT == start.DEFAULT_PORT == 8100
    assert any("chown app:app /data" in i for i in lines)  # so a new volume there belongs to the app's user


def test_the_dockerfile_holds_no_keys_and_pins_its_base_images():
    text = dockerfile()
    assert not any(name in text for name in start.KEYS)
    bases = dict(re.findall(r"ARG (NODE_IMAGE|PYTHON_IMAGE)=(\S+)", text))
    assert set(bases) == {"NODE_IMAGE", "PYTHON_IMAGE"} and not any(tag.endswith((":latest", "/")) or ":" not in tag for tag in bases.values())
    froms = [i for i in instructions() if i.startswith("FROM ")]
    assert froms == ["FROM --platform=$BUILDPLATFORM ${NODE_IMAGE} AS frontend", "FROM ${PYTHON_IMAGE}"]
    assert "requirements.txt" in text and "npm run build" in text and "python start.py prepare" in text


# ---------------------------------------------------------------------------
# Where it is published, and the commands that do it
# ---------------------------------------------------------------------------

def test_the_image_name_comes_from_the_github_address():
    assert container.image_for("https://github.com/Someone/Market-Agent.git") == "ghcr.io/someone/market-agent"
    assert container.image_for("git@github.com:someone/market-agent.git\n") == "ghcr.io/someone/market-agent"
    assert container.image_for("https://gitlab.com/someone/market-agent.git") == container.image_for("") == ""
    assert container.repo_page("git@github.com:Someone/market-agent.git") == "https://github.com/Someone/market-agent"
    assert container.choose_image(None, "https://github.com/Someone/market-agent") == "ghcr.io/someone/market-agent"
    assert container.choose_image("ghcr.io/team/analyst", "https://github.com/Someone/market-agent") == "ghcr.io/team/analyst"
    assert container.choose_image("registry.example.com:5000/team/analyst", "") == "registry.example.com:5000/team/analyst"


def test_a_missing_or_malformed_image_name_is_explained(monkeypatch):
    with pytest.raises(SystemExit) as stopped:
        container.choose_image(None, "")
    assert "--image ghcr.io/YOUR-GITHUB-NAME/market-agent" in str(stopped.value)
    for bad in ("ghcr.io/Someone/market-agent", "ghcr.io/someone/market-agent:latest", "market agent", "ghcr.io/", "https://ghcr.io/a/b"):
        with pytest.raises(SystemExit) as stopped:
            container.choose_image(bad, "")
        assert "isn't an image name" in str(stopped.value)
    monkeypatch.setenv("CONTAINER_IMAGE", "ghcr.io/from-settings/analyst")
    assert container.choose_image(None, "") == "ghcr.io/from-settings/analyst"


def test_the_build_and_publish_commands(tmp_path, monkeypatch):
    build = container.build_command(tmp_path, "market-agent:local", "2026.11.06", "https://github.com/someone/market-agent")
    assert build == ["build", "--tag", "market-agent:local", "--build-arg", "VERSION=2026.11.06",
                     "--build-arg", "SOURCE=https://github.com/someone/market-agent", str(tmp_path)]
    publish = container.publish_command(tmp_path, "ghcr.io/someone/market-agent", "2026.11.06")
    assert publish[:4] == ["buildx", "build", "--builder", "market-agent-builder"]
    assert publish[publish.index("--platform") + 1] == "linux/amd64,linux/arm64"
    assert [publish[i + 1] for i, word in enumerate(publish) if word == "--tag"] == [
        "ghcr.io/someone/market-agent:latest", "ghcr.io/someone/market-agent:2026.11.06"]
    assert publish[-2:] == ["--push", str(tmp_path)]
    assert "--builder" not in container.publish_command(tmp_path, "ghcr.io/someone/market-agent", "1", builder="default")
    monkeypatch.setenv("CONTAINER_BUILD_FLAGS", '--build-arg "PYTHON_IMAGE=python:3.13-slim" --no-cache')
    assert container.extra_flags() == ["--build-arg", "PYTHON_IMAGE=python:3.13-slim", "--no-cache"]
    assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}", container.default_version())


def test_trying_it_keeps_the_app_on_this_computer_and_keys_out_of_the_command():
    demo = container.run_command("market-agent:local")
    assert demo == ["run", "--rm", "--name", "market-agent", "--publish", "127.0.0.1:8100:8100", "market-agent:local"]
    real = container.run_command("market-agent:local", real=True, port=9000)
    assert "127.0.0.1:9000:8100" in real and "market-agent-data:/data" in real and "MODE=real" in real
    passed = [real[i + 1] for i, word in enumerate(real) if word == "--env"]
    assert "ANTHROPIC_API_KEY" in passed and all("=" not in name for name in passed if name != "MODE=real")  # names only
    assert "docker run --rm -p 127.0.0.1:8100:8100 ghcr.io/someone/market-agent" in container.visitor_commands("ghcr.io/someone/market-agent")
    assert "--pull always" not in container.visitor_commands("x/y")  # the demo must also start with no internet


class FakeDocker:
    """Stands in for the docker command: answers from a script, and remembers what it was asked."""

    def __init__(self, answers=None):
        self.calls, self.answers = [], answers or {}

    def __call__(self, *args, capture=False, check=True):
        self.calls.append(args)
        for start_of, (code, out) in self.answers.items():
            if args[:len(start_of)] == start_of:
                return subprocess.CompletedProcess(args, code, out, "")
        return subprocess.CompletedProcess(args, 0, "", "")


def test_the_builder_is_created_once_and_your_default_is_left_alone(monkeypatch):
    fake = FakeDocker({("buildx", "inspect"): (1, "")})
    monkeypatch.setattr(container, "docker", fake)
    container.ensure_builder()
    assert fake.calls[-1] == ("buildx", "create", "--name", "market-agent-builder", "--driver", "docker-container")
    assert "--use" not in fake.calls[-1]
    fake = FakeDocker({("buildx", "inspect"): (0, "")})
    monkeypatch.setattr(container, "docker", fake)
    container.ensure_builder()
    container.ensure_builder("default")
    assert [c[:2] for c in fake.calls] == [("buildx", "inspect")]


def healthy_docker(changes: dict | None = None):
    answers = {("inspect", "--format", "{{.State.Running}}"): (0, "true\n"),
               ("inspect", "--format", "{{.State.ExitCode}}"): (0, "143\n"),
               ("exec", "NAME", "id", "-u"): (0, "10001\n"),
               ("exec", "NAME", "cat", "/data/watchlist.txt"): (0, "AAPL\nMSFT\n"),
               ("logs", "NAME"): (0, "No ANTHROPIC_API_KEY: the app opens...\n"),
               ("port",): (0, "127.0.0.1:49999\n")}
    answers.update(changes or {})
    name = f"market-agent-test-{os.getpid()}"
    return FakeDocker({tuple(name if part == "NAME" else part for part in key): value for key, value in answers.items()})


def test_testing_an_image_runs_it_offline_in_both_modes(monkeypatch):
    fake = healthy_docker()
    monkeypatch.setattr(container, "docker", fake)
    monkeypatch.setattr(container.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(container, "fetch", lambda url: 200)
    assert container.test_image("market-agent:local") == []
    runs = [c for c in fake.calls if c[0] == "run"]
    assert len(runs) == 3 and all("--detach" in r and r[-1] == "market-agent:local" for r in runs)
    assert [("--network", "none") == r[4:6] for r in runs] == [True, True, False]   # the first two can't reach anything
    assert "MODE=real" in runs[1] and "MODE=real" not in runs[0]
    assert not any(name in " ".join(r) for r in runs for name in start.KEYS)       # no key is ever given to a test
    assert "127.0.0.1::8100" in runs[2]                                             # this computer only, any free port
    assert sum(c[:2] == ("rm", "--force") for c in fake.calls) >= 3                 # every test container is removed
    fake.calls.clear()
    assert container.test_image("market-agent:local", port_check=False) == []
    assert len([c for c in fake.calls if c[0] == "run"]) == 2


def test_an_image_that_fails_is_not_fit_to_publish(monkeypatch, capsys):
    monkeypatch.setattr(container.time, "sleep", lambda seconds: None)
    monkeypatch.setattr(container, "fetch", lambda url: 200)
    name = f"market-agent-test-{os.getpid()}"

    fake = healthy_docker({("exec", "NAME", "python", "/app/start.py", "selftest"): (1, "  FAIL  GET /api/portfolio: answered 500\n")})
    monkeypatch.setattr(container, "docker", fake)
    problems = container.test_image("market-agent:local", port_check=False)
    assert problems == ["the demo passes its self-test offline", "real mode passes its (read-only) self-test"]
    assert "FAIL  GET /api/portfolio" in capsys.readouterr().out

    fake = healthy_docker({("exec", "NAME", "id", "-u"): (0, "0\n"), ("inspect", "--format", "{{.State.ExitCode}}"): (0, "137\n")})
    monkeypatch.setattr(container, "docker", fake)
    problems = container.test_image("market-agent:local", port_check=False)
    assert any("not as root" in p for p in problems) and any("docker stop ends it promptly" in p for p in problems)

    fake = healthy_docker({("inspect", "--format", "{{.State.Running}}"): (0, "false\n")})  # it stopped straight away
    monkeypatch.setattr(container, "docker", fake)
    assert container.test_image("market-agent:local", port_check=False) == ["the demo starts", "real mode starts without a key"]
    assert not any(c[:2] == ("exec", name) for c in fake.calls)

    fake = healthy_docker()
    monkeypatch.setattr(container, "docker", fake)
    monkeypatch.setattr(container, "fetch", lambda url: 0)  # nothing answers at the published port
    assert container.test_image("market-agent:local")[-1].startswith("the app opens at http://localhost:49999")


def test_publishing_stops_before_anything_is_sent_if_the_test_fails(projects, tmp_path, monkeypatch):
    fake = healthy_docker({("exec", "NAME", "python", "/app/start.py", "selftest"): (1, "")})
    monkeypatch.setattr(container, "docker", fake)
    monkeypatch.setattr(container, "need_docker", lambda: None)
    monkeypatch.setattr(container, "origin_remote", lambda: "git@github.com:Someone/market-agent.git")
    monkeypatch.setattr(container, "CONTEXT", tmp_path / "build")
    monkeypatch.setattr(container.time, "sleep", lambda seconds: None)
    args = type("Args", (), {"image": None, "tickers": None, "version": "2026.11.06", "skip_test": False,
                             "no_port_check": True, "builder": "market-agent-builder", "platforms": container.PLATFORMS})
    with pytest.raises(SystemExit) as stopped:
        container.publish(args)
    assert "nothing was published" in str(stopped.value)
    assert not any(c[0] == "buildx" for c in fake.calls)

    fake = healthy_docker()
    monkeypatch.setattr(container, "docker", fake)
    container.publish(args)
    pushed = [c for c in fake.calls if c[:2] == ("buildx", "build")]
    assert len(pushed) == 1 and "--push" in pushed[0] and "ghcr.io/someone/market-agent:2026.11.06" in pushed[0]
    assert "SOURCE=https://github.com/Someone/market-agent" in pushed[0]
    built = [c for c in fake.calls if c[0] == "build"]
    assert len(built) == 1 and fake.calls.index(built[0]) < fake.calls.index(pushed[0])  # tested before it is published


# ---------------------------------------------------------------------------
# start.py: settings
# ---------------------------------------------------------------------------

def test_mode_and_port_settings():
    assert start.read_mode({}) == start.read_mode({"MODE": ""}) == "demo"
    assert start.read_mode({"MODE": " Real "}) == "real"
    with pytest.raises(SystemExit) as stopped:
        start.read_mode({"MODE": "production"})
    assert "MODE must be demo or real" in str(stopped.value)
    assert start.read_port({}) == 8100 and start.read_port({"PORT": "9000"}) == 9000
    for bad in ("0", "70000", "eighty", "-1"):
        with pytest.raises(SystemExit):
            start.read_port({"PORT": bad})


def test_quotes_from_a_settings_file_are_taken_off():
    env = {"MODE": '"real"', "ANTHROPIC_API_KEY": "'sk-ant-quoted'", "SEC_CONTACT": '"someone@firm.test"',
           "RUN_TIMES": "08:15,12:30", "DISCORD_WEBHOOK_URL": '"', "UNRELATED": '"left alone"', "SCHEDULE": '"on\''}
    assert start.unquote_settings(env) == ["MODE", "ANTHROPIC_API_KEY", "SEC_CONTACT"]
    assert env == {"MODE": "real", "ANTHROPIC_API_KEY": "sk-ant-quoted", "SEC_CONTACT": "someone@firm.test",
                   "RUN_TIMES": "08:15,12:30", "DISCORD_WEBHOOK_URL": '"', "UNRELATED": '"left alone"', "SCHEDULE": '"on\''}
    assert start.unquote_settings(env) == [] and start.read_mode(env) == "real"


def test_a_user_without_a_home_folder_gets_one(tmp_path):
    env = {"HOME": str(tmp_path)}
    assert start.writable_home(env) == str(tmp_path)
    for env in ({}, {"HOME": str(tmp_path / "missing")}):
        home = start.writable_home(env)
        assert env["HOME"] == home and os.access(home, os.W_OK) and home != str(tmp_path / "missing")


# ---------------------------------------------------------------------------
# start.py: the demo's sample
# ---------------------------------------------------------------------------

def test_the_samples_today_is_the_latest_trading_day():
    assert start.sample_day(date(2026, 11, 6)) == date(2026, 11, 6)      # a Friday
    assert start.sample_day(date(2026, 11, 7)) == date(2026, 11, 6)      # Saturday
    assert start.sample_day(date(2026, 11, 8)) == date(2026, 11, 6)      # Sunday
    assert start.sample_day(date(2026, 11, 26)) == date(2026, 11, 25)    # Thanksgiving
    assert start.sample_day(date(2027, 1, 1)) == date(2026, 12, 31)      # New Year's Day


def latest_report(folder: Path) -> tuple:
    import sqlite3
    from contextlib import closing
    with closing(sqlite3.connect(folder / "reports.db")) as conn:
        return conn.execute("SELECT session_date, status FROM reports ORDER BY session_date DESC LIMIT 1").fetchone()


def test_the_sample_is_made_once_a_day_and_starts_clean(tmp_path):
    folder = tmp_path / "demo"
    assert start.make_sample(folder, END) is True
    assert latest_report(folder) == ("2026-11-06", "intraday")           # a day in progress: Run update now has work to do
    made_at = (folder / "reports.db").stat().st_mtime_ns
    (folder / "watchlist.txt").write_text("GME\n")                        # a visitor changed the demo's stocks
    assert start.make_sample(folder, END) is False                        # the same day (the container restarted): kept
    assert (folder / "reports.db").stat().st_mtime_ns == made_at and (folder / "watchlist.txt").read_text() == "GME\n"
    assert start.make_sample(folder, date(2026, 11, 9)) is True           # the next trading day: a fresh one
    assert latest_report(folder) == ("2026-11-09", "intraday")
    assert "GME" not in (folder / "watchlist.txt").read_text()
    assert start.sample_is_ready(folder, date(2026, 11, 9)) and not start.sample_is_ready(folder, END)


def test_a_half_made_sample_is_made_again(tmp_path):
    folder = tmp_path / "demo"
    start.make_sample(folder, END)
    (folder / "ready").unlink()                                           # as if the container was stopped mid-way
    (folder / "reports.db").write_bytes(b"half a database")
    assert start.make_sample(folder, END) is True
    assert latest_report(folder) == ("2026-11-06", "intraday")


def test_the_demo_wont_replace_files_that_arent_a_sample(tmp_path):
    folder = tmp_path / "my-data"
    write(folder / "reports.db", "real reports")
    write(folder / "watchlist.txt", "TSLA\n")
    with pytest.raises(SystemExit) as stopped:
        start.make_sample(folder, END)
    assert "aren't a demo sample" in str(stopped.value)
    assert (folder / "reports.db").read_text() == "real reports" and (folder / "watchlist.txt").read_text() == "TSLA\n"
    assert start.make_sample(tmp_path / "empty", END) is True             # an empty or missing folder is fine


def test_the_demo_drops_real_keys_before_anything_runs(tmp_path, monkeypatch):
    for name in start.KEYS:
        monkeypatch.setenv(name, "a-real-looking-value")
    app, info = start.demo_app(tmp_path / "demo", today=date(2026, 11, 7), frontend=tmp_path / "no-frontend")  # a Saturday
    assert info["ignored"] == list(start.KEYS) and not any(name in os.environ for name in start.KEYS)
    assert info["day"] == END and info["made"] is True
    from starlette.testclient import TestClient
    with TestClient(app) as client:
        assert client.get("/api/health").json() == {"status": "ok", "reports": 44}
        latest = client.get("/api/reports/latest").json()
        assert (latest["session_date"], latest["status"]) == ("2026-11-06", "intraday")
        assert "prices and news are simulated" in latest["body_md"]
    app, info = start.demo_app(tmp_path / "demo", today=date(2026, 11, 8), frontend=tmp_path / "no-frontend")  # Sunday
    assert info["made"] is False and info["ignored"] == []


# ---------------------------------------------------------------------------
# start.py: real mode's settings
# ---------------------------------------------------------------------------

def test_real_mode_points_the_app_and_its_jobs_at_the_data_folder(tmp_path, monkeypatch):
    monkeypatch.setenv("SEARCH_DB", str(tmp_path / "elsewhere.db"))
    data = tmp_path / "data"
    app, notes = start.real_app(data, frontend=tmp_path / "no-frontend")
    # In the environment, because scheduled jobs and the agent's tools are programs of their own
    assert os.environ["REPORTS_DB"] == str(data / "reports.db") and os.environ["WATCHLIST_FILE"] == str(data / "watchlist.txt")
    assert "SEARCH_DB" not in os.environ  # so the search index sits in the data folder too
    import market_tools
    import reports_db
    assert market_tools.WATCHLIST_FILE == data / "watchlist.txt" and reports_db.DB_PATH == data / "reports.db"
    assert [note.split(": ")[0] for note in notes] == ["No ANTHROPIC_API_KEY", "No SEC_CONTACT", f"{data} isn't a volume"]
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    monkeypatch.setenv("SEC_CONTACT", "someone@firm.test")
    monkeypatch.setattr(start, "is_mounted", lambda folder: True)
    assert start.real_app(data, frontend=tmp_path / "no-frontend")[1] == []


def test_the_projects_own_key_name_works_too(tmp_path, monkeypatch):
    """A .env passed with --env-file names the key MARKET_AGENT_ANTHROPIC_KEY (run_brief.py's name for it)."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")  # (so the test puts it back as it was)
    monkeypatch.setenv("MARKET_AGENT_ANTHROPIC_KEY", "sk-project")
    _, notes = start.real_app(tmp_path / "data", frontend=tmp_path / "no-frontend")
    assert os.environ["ANTHROPIC_API_KEY"] == "sk-project" and not any("ANTHROPIC_API_KEY" in note for note in notes)
    assert "MARKET_AGENT_ANTHROPIC_KEY" in start.KEYS  # so the demo drops it, like the other keys


def test_the_key_reaches_the_agent_and_the_schedule(tmp_path):
    """This project's run_brief.py takes ANTHROPIC_API_KEY out of the environment and gives the agent
    MARKET_AGENT_ANTHROPIC_KEY instead. The key given to docker run must still reach the agent, and the
    start-up checks and the schedule must still see it. (A program of its own, as in the container.)"""
    show = (f"import os, sys; sys.path.insert(0, {str(HERE)!r}); import start; from pathlib import Path; "
            f"app, notes = start.real_app(Path({str(tmp_path / 'data')!r}), frontend=Path({str(tmp_path / 'none')!r})); "
            "import run_brief; print(run_brief.AGENT_ENV.get('ANTHROPIC_API_KEY')); print(os.environ.get('ANTHROPIC_API_KEY')); "
            "print(start.plan_schedule({**os.environ, 'SCHEDULE': 'on'})[1][0]); print(notes)")
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS}
    env["ANTHROPIC_API_KEY"] = "sk-given-to-docker-run"
    result = subprocess.run([sys.executable, "-c", show], cwd=tmp_path, env=env, capture_output=True, text=True, timeout=120)
    assert result.returncode == 0, result.stderr
    agent, environment, schedule, notes = result.stdout.splitlines()[-4:]
    assert agent == environment == "sk-given-to-docker-run"
    assert schedule.startswith("Schedule: on") and "brief 08:15" in schedule and "No ANTHROPIC_API_KEY" not in notes


def test_the_apps_after_close_run_belongs_to_the_schedule(tmp_path, monkeypatch):
    """This app runs a final report after the close by itself (api.AUTO_CLOSE). In a container that
    would spend money nobody asked for, so it is on only with SCHEDULE=on and a key."""
    assert start.after_close_wanted({}) is False
    assert start.after_close_wanted({"ANTHROPIC_API_KEY": "sk-test"}) is False      # no schedule: nothing runs by itself
    assert start.after_close_wanted({"SCHEDULE": "on"}) is False                    # nothing to run it with
    assert start.after_close_wanted(KEYED) is True
    assert start.after_close_wanted({"SCHEDULE": "on", "MARKET_AGENT_ANTHROPIC_KEY": "sk-test"}) is True
    assert start.after_close_wanted({**KEYED, "AUTO_CLOSE_RUN": "0"}) is False
    start.real_app(tmp_path / "data", frontend=tmp_path / "no-frontend")
    import api
    monkeypatch.setattr(api, "AUTO_CLOSE", api.AUTO_CLOSE)  # (put back afterwards)
    assert api.AUTO_CLOSE is False
    monkeypatch.setenv("SCHEDULE", "on")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    start.real_app(tmp_path / "data", frontend=tmp_path / "no-frontend")
    assert api.AUTO_CLOSE is True


def test_a_projects_env_file_is_never_read(tmp_path):
    """The image has no .env, and on your own computer the project's .env (real keys, a real webhook) must
    not reach the demo, the tests or anything they start."""
    assert os.environ["PYTHON_DOTENV_DISABLED"] == "1"
    write(tmp_path / ".env", "CONTAINER_TEST_FROM_ENV_FILE=leaked\n")
    show = (f"import os, sys; sys.path.insert(0, {str(HERE)!r}); import start; from dotenv import load_dotenv; "
            "load_dotenv(); print(os.environ.get('CONTAINER_TEST_FROM_ENV_FILE'))")
    env = {k: v for k, v in os.environ.items() if k not in ("PYTHON_DOTENV_DISABLED", "CONTAINER_TEST_FROM_ENV_FILE")}
    result = subprocess.run([sys.executable, "-c", show], cwd=tmp_path, env=env, capture_output=True, text=True)
    assert result.returncode == 0 and result.stdout.strip() == "None", result.stderr
    without = subprocess.run([sys.executable, "-c", show.replace("import start; ", "")], cwd=tmp_path, env=env,
                             capture_output=True, text=True)
    assert without.stdout.strip() == "leaked"  # (proof the check above would have seen it)


# ---------------------------------------------------------------------------
# start.py: the demo's banner
# ---------------------------------------------------------------------------

BUILT = ('<!doctype html>\n<html lang="en">\n  <head>\n    <title>Market Analyst</title>\n'
         '    <link rel="stylesheet" href="/assets/app.css">\n  </head>\n  <body>\n    <div id="root"></div>\n'
         '    <script type="module" src="/assets/app.js"></script>\n  </body>\n</html>\n')


def built_app(folder: Path) -> Path:
    write(folder / "index.html", BUILT)
    write(folder / "assets" / "app.js", "document.getElementById('root').textContent = 'app'\n")
    write(folder / "assets" / "app.css", "body { margin: 0 }\n")
    return folder


def test_the_banner_is_added_once():
    page = start.add_banner(BUILT)
    assert page.count('<script src="/demo-banner.js" defer></script>') == 1
    assert page.index("demo-banner.js") < page.index("</head>") and "<title>Market Analyst · demo</title>" in page
    assert start.add_banner(page) == page
    with pytest.raises(ValueError):
        start.add_banner("<p>not the built app</p>")


def test_the_demo_gets_a_copy_and_the_real_app_is_left_alone(tmp_path, monkeypatch):
    dist, target = built_app(tmp_path / "dist"), tmp_path / "frontend-demo"
    before = snapshot(dist)
    write(target / "assets" / "old.js", "left over from an earlier build")
    monkeypatch.setattr(start, "version", lambda: "2026.11.06")
    assert start.prepare(dist, target) == target
    assert snapshot(dist) == before and "demo-banner.js" not in (dist / "index.html").read_text()
    assert "demo-banner.js" in (target / "index.html").read_text()
    banner = (target / "demo-banner.js").read_text()
    assert "const VERSION = '2026.11.06'" in banner and "__VERSION__" not in banner and "no AI is called" in banner
    assert (target / "assets" / "app.js").is_file() and not (target / "assets" / "old.js").exists()
    monkeypatch.setattr(start, "version", lambda: "1.4'; alert(1); '")  # a VERSION file edited by hand
    start.prepare(dist, target)
    assert "const VERSION = '1.4alert1'" in (target / "demo-banner.js").read_text()
    for missing in (tmp_path / "no-build", write(tmp_path / "empty" / "readme.txt").parent):
        with pytest.raises(SystemExit) as stopped:
            start.prepare(missing, tmp_path / "x")
        assert "Build the frontend first" in str(stopped.value)


# ---------------------------------------------------------------------------
# start.py: only this computer's names are answered
# ---------------------------------------------------------------------------

def test_host_names_are_read_without_their_port():
    assert start.host_name("LocalHost:8100") == "localhost" and start.host_name("127.0.0.1") == "127.0.0.1"
    assert start.host_name("[::1]:8100") == "[::1]" and start.host_name("localhost.:80") == "localhost"
    assert start.host_name("") == "" and start.host_name("[::1") == ""
    assert start.allowed_hosts("") == {"localhost", "127.0.0.1", "[::1]"}
    assert start.allowed_hosts(" My-PC , 192.168.1.20 ,") == {"my-pc", "192.168.1.20"}


def test_requests_sent_to_another_name_are_refused():
    from starlette.applications import Starlette
    from starlette.responses import PlainTextResponse
    from starlette.routing import Route
    from starlette.testclient import TestClient
    from contextlib import asynccontextmanager
    events = []

    @asynccontextmanager
    async def lifespan(app):
        events.append("started")
        yield
        events.append("stopped")

    inner = Starlette(routes=[Route("/", lambda request: PlainTextResponse("the app"))], lifespan=lifespan)
    with TestClient(start.only_hosts(inner, start.allowed_hosts(""))) as client:
        for host in ("localhost:8100", "LOCALHOST", "127.0.0.1:9000", "[::1]:8100"):
            assert client.get("/", headers={"Host": host}).text == "the app"
        for host in ("evil.example", "localhost.evil.example:8100", "127.0.0.1.evil.example", "192.168.1.20:8100", ""):
            answer = client.get("/", headers={"Host": host})
            assert answer.status_code == 403 and "only answers at" in answer.text and "the app" not in answer.text
        assert "<script>" not in client.get("/", headers={"Host": "<script>alert(1)</script>"}).text
    assert events == ["started", "stopped"]  # the app's own start and stop still happen
    with TestClient(start.only_hosts(inner, start.allowed_hosts("localhost, my-pc"))) as client:
        assert client.get("/", headers={"Host": "my-pc:8100"}).status_code == 200
        assert client.get("/", headers={"Host": "127.0.0.1:8100"}).status_code == 403
    assert start.only_hosts(inner, start.allowed_hosts("*")) is inner


# ---------------------------------------------------------------------------
# start.py: the built-in schedule
# ---------------------------------------------------------------------------

from datetime import time as at  # noqa: E402

KEYED = {"SCHEDULE": "on", "ANTHROPIC_API_KEY": "sk-test", "SEC_CONTACT": "someone@firm.test"}


def test_the_schedule_is_off_unless_asked_for():
    for env in ({}, {"SCHEDULE": "off"}, {"SCHEDULE": ""}, {"ANTHROPIC_API_KEY": "sk-test"}):
        slots, notes = start.plan_schedule(env)
        assert slots == [] and notes[0].startswith("Schedule: off.") and "SCHEDULE=on" in notes[0]


def test_the_default_schedule_matches_the_guides():
    slots, notes = start.plan_schedule(KEYED)
    assert [(name, f"{when:%H:%M}", command) for name, when, command in slots] == [
        ("filings", "08:00", ["filings.py", "check"]), ("brief", "08:15", ["run_brief.py"]),
        ("calendar", "09:35", ["events.py", "scan", "--only-if-open"]), ("brief", "12:30", ["run_brief.py"]),
        ("filings", "16:35", ["filings.py", "check"])]
    assert notes == ["Schedule: on, weekdays, New York time: filings 08:00, brief 08:15, calendar 09:35, brief 12:30, filings 16:35."]
    for _, _, command in slots:
        assert (start.MAIN / command[0]).is_file()  # each job is a program the main project really has


def test_jobs_that_lack_their_key_are_left_out_and_times_can_be_changed():
    slots, notes = start.plan_schedule({"SCHEDULE": "on", "SEC_CONTACT": "someone@firm.test"})
    assert {name for name, _, _ in slots} == {"filings"}
    assert "Schedule: brief is off, because ANTHROPIC_API_KEY isn't set." in notes
    slots, notes = start.plan_schedule({"SCHEDULE": "on", "ANTHROPIC_API_KEY": "sk-test"})
    assert {name for name, _, _ in slots} == {"brief", "calendar"} and any("filings is off, because SEC_CONTACT" in n for n in notes)
    slots, notes = start.plan_schedule({"SCHEDULE": "on"})
    assert slots == [] and notes[-1] == "Schedule: on, but nothing can run yet."
    slots, _ = start.plan_schedule({**KEYED, "RUN_TIMES": "7:05, 16:10,7:05", "CALENDAR_TIMES": "", "FILINGS_TIMES": " "})
    assert [(name, f"{when:%H:%M}") for name, when, _ in slots] == [("brief", "07:05"), ("brief", "16:10")]
    for bad in ("8.15", "25:00", "08:60", "noon", "08:15;12:30"):
        with pytest.raises(SystemExit) as stopped:
            start.plan_schedule({**KEYED, "RUN_TIMES": bad})
        assert "RUN_TIMES must be times like 08:15,12:30" in str(stopped.value)


def ny(day: str, clock: str) -> datetime:
    return datetime.fromisoformat(f"{day}T{clock}").replace(tzinfo=ET)


SLOTS = [("filings", at(8, 0), ["filings.py", "check"]), ("brief", at(8, 15), ["run_brief.py"]),
         ("brief", at(12, 30), ["run_brief.py"])]
EARLY = ny("2026-11-02", "00:00")  # the container has been up since before the week began


def names(jobs) -> list[str]:
    return [name for _, name, _ in jobs]


def test_a_job_is_due_at_its_time_on_weekdays():
    assert names(start.due(SLOTS, ny("2026-11-06", "08:14"), EARLY, set())) == ["filings"]
    assert names(start.due(SLOTS, ny("2026-11-06", "08:15"), EARLY, set())) == ["filings", "brief"]   # earliest first
    assert names(start.due(SLOTS, ny("2026-11-06", "07:59"), EARLY, set())) == []
    assert names(start.due(SLOTS, ny("2026-11-07", "08:15"), EARLY, set())) == []                      # Saturday
    assert names(start.due(SLOTS, ny("2026-11-08", "12:30"), EARLY, set())) == []                      # Sunday
    in_utc = ny("2026-11-06", "12:30").astimezone(timezone.utc)                                        # 17:30 UTC
    assert names(start.due(SLOTS, in_utc, EARLY, set())) == ["brief"]


def test_a_job_missed_while_the_computer_slept_runs_up_to_two_hours_late():
    assert names(start.due(SLOTS, ny("2026-11-06", "10:15"), EARLY, set())) == ["brief"]   # 8:15's, exactly 2 hours late
    assert names(start.due(SLOTS, ny("2026-11-06", "10:16"), EARLY, set())) == []           # too late: wait for 12:30
    assert names(start.due(SLOTS, ny("2026-11-06", "13:00"), EARLY, set())) == ["brief"]   # asleep all morning: only 12:30's


def test_jobs_from_before_the_container_started_dont_run_and_none_runs_twice():
    started = ny("2026-11-06", "08:16")
    assert names(start.due(SLOTS, ny("2026-11-06", "08:17"), started, set())) == []         # restarted a minute after 8:15
    assert names(start.due(SLOTS, ny("2026-11-06", "12:30"), started, set())) == ["brief"]
    done = set()
    assert start.tick(SLOTS, ny("2026-11-06", "08:15"), EARLY, done, lambda name, command: 0) == ["filings", "brief"]
    assert start.tick(SLOTS, ny("2026-11-06", "08:15"), EARLY, done, lambda name, command: 0) == []
    assert start.tick(SLOTS, ny("2026-11-06", "09:00"), EARLY, done, lambda name, command: 0) == []
    assert start.tick(SLOTS, ny("2026-11-06", "12:31"), EARLY, done, lambda name, command: 0) == ["brief"]
    assert start.tick(SLOTS, ny("2026-11-09", "08:15"), EARLY, done, lambda name, command: 0) == ["filings", "brief"]  # Monday


def test_a_job_that_fails_is_not_tried_again_and_again():
    done, tries = set(), []

    def broken(name, command):
        tries.append(name)
        raise RuntimeError("the job crashed")

    with pytest.raises(RuntimeError):
        start.tick(SLOTS, ny("2026-11-06", "08:15"), EARLY, done, broken)
    assert tries == ["filings"]
    assert start.tick(SLOTS, ny("2026-11-06", "08:15"), EARLY, done, lambda name, command: 1) == ["brief"]  # the rest still run
    assert start.tick(SLOTS, ny("2026-11-06", "08:16"), EARLY, done, lambda name, command: 1) == []


def test_late_evening_jobs_and_clock_changes():
    late = [("filings", at(23, 30), ["filings.py", "check"])]
    assert names(start.due(late, ny("2026-11-07", "00:10"), EARLY, set())) == ["filings"]   # Friday's, just after midnight
    assert names(start.due(late, ny("2026-11-09", "00:10"), EARLY, set())) == []            # Sunday has no jobs
    # The clocks went forward on Sunday 14 March 2027: 8:15 in New York is 12:15 UTC, not 13:15
    spring = datetime(2027, 3, 15, 12, 15, tzinfo=timezone.utc)
    assert names(start.due(SLOTS, spring, ny("2027-03-01", "00:00"), set())) == ["filings", "brief"]
    assert names(start.due(SLOTS, spring - timedelta(minutes=16), ny("2027-03-01", "00:00"), set())) == []
    winter = datetime(2026, 11, 6, 13, 15, tzinfo=timezone.utc)                             # after the clocks went back
    assert names(start.due(SLOTS, winter, EARLY, set())) == ["filings", "brief"]


def test_a_scheduled_job_runs_as_its_own_program_in_the_main_project(monkeypatch, capsys):
    seen = {}

    def fake_run(command, cwd=None, timeout=None, **more):
        seen.update(command=command, cwd=cwd, timeout=timeout, more=more)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(start.subprocess, "run", fake_run)
    assert start.run_job("brief", ["run_brief.py"]) == 0
    assert seen["command"] == [sys.executable, "run_brief.py"] and seen["cwd"] == start.MAIN and seen["timeout"] == 1800
    assert "env" not in seen["more"]  # it inherits this program's settings: the data folder, the watchlist, the keys
    assert "[schedule] brief: finished" in capsys.readouterr().out

    def too_slow(command, **more):
        raise subprocess.TimeoutExpired(command, 1800)

    monkeypatch.setattr(start.subprocess, "run", too_slow)
    assert start.run_job("brief", ["run_brief.py"]) == -1
    out = capsys.readouterr().out
    assert "stopped after 30 minutes" in out and "failed (exit code -1)" in out
    monkeypatch.setattr(start.subprocess, "run", lambda command, **more: subprocess.CompletedProcess(command, 3))
    assert start.run_job("calendar", ["events.py", "scan"]) == 3 and "failed (exit code 3)" in capsys.readouterr().out


def test_real_mode_knows_whether_a_volume_is_attached(tmp_path):
    mounts = write(tmp_path / "mountinfo", "\n".join([
        "2049 1730 0:96 / / rw,relatime master:412 - overlay overlay rw",
        f"2060 2049 254:1 /docker/volumes/market-agent-data/_data {tmp_path / 'data'} rw,relatime - ext4 /dev/vda1 rw",
        "short line"]) + "\n")
    assert start.is_mounted(tmp_path / "data", mounts) is True
    assert start.is_mounted(tmp_path / "other", mounts) is False
    assert start.is_mounted(tmp_path, tmp_path / "no-such-file") is False  # not Linux: falls back to the usual check


# ---------------------------------------------------------------------------
# The app itself, started the way the container starts it (as its own program)
# ---------------------------------------------------------------------------

def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def launch(tmp: Path, settings: dict, wait: bool = True):
    """Start start.py as the container does, with a small built app standing in for the React build."""
    dist = built_app(tmp / "dist")
    demo_frontend = start.prepare(dist, tmp / "frontend-demo")
    port = free_port()
    code = ("import functools, sys; from pathlib import Path; "
            f"sys.path.insert(0, {str(HERE)!r}); import start; "
            f"start.DEMO_FRONTEND = Path({str(demo_frontend)!r}); "
            f"start.real_app = functools.partial(start.real_app, frontend=Path({str(dist)!r})); start.serve()")
    env = {k: v for k, v in os.environ.items() if k not in SETTINGS}
    env.update({"PORT": str(port), "HOST": "127.0.0.1", "PYTHONUNBUFFERED": "1", "DEMO_DIR": str(tmp / "demo"),
                "DATA_DIR": str(tmp / "data"), "RUN_COOLDOWN_SECONDS": "0", "FILINGS_CHECK_COOLDOWN_SECONDS": "0", **settings})
    log = open(tmp / "log.txt", "w")
    process = subprocess.Popen([sys.executable, "-c", code], cwd=tmp, env=env, stdout=log, stderr=subprocess.STDOUT)
    if wait:
        for _ in range(240):
            if start.healthcheck(port) == 0 or process.poll() is not None:
                break
            time.sleep(0.25)
        assert process.poll() is None and start.healthcheck(port) == 0, (tmp / "log.txt").read_text()
    return process, f"http://127.0.0.1:{port}", tmp / "log.txt"


def stop(process) -> None:
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(15)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    tmp = tmp_path_factory.mktemp("demo-run")
    process, url, log = launch(tmp, {"ANTHROPIC_API_KEY": "sk-not-a-real-key", "DISCORD_WEBHOOK_URL": "https://example.invalid/hook"})
    yield url, log, tmp
    stop(process)


@pytest.fixture
def real(tmp_path):
    started = []

    def begin(settings=None, **more):
        process, url, log = launch(tmp_path, {"MODE": "real", **(settings or {})}, **more)
        started.append(process)
        return process, url, log

    yield begin
    for process in started:
        stop(process)


def test_the_demo_starts_says_what_it_is_and_ignores_keys(demo):
    url, log, tmp = demo
    text = log.read_text()
    assert "demo mode" in text and "Sample data made: two months of reports up to" in text
    assert "no AI is called and nothing is sent anywhere" in text
    assert "Ignored in demo mode: ANTHROPIC_API_KEY, DISCORD_WEBHOOK_URL. Add -e MODE=real" in text
    assert "sk-not-a-real-key" not in text
    assert (tmp / "demo" / "ready").is_file() and not (tmp / "data").exists()
    assert start.healthcheck(int(url.rsplit(":", 1)[1])) == 0
    assert start.healthcheck(free_port()) == 1  # nothing listening there


def test_the_self_test_passes_on_the_demo(demo):
    url, _, _ = demo
    lines = []
    assert start.selftest(url, "demo", out=lines.append) == 0, "\n".join(lines)
    report = "\n".join(lines)
    routes = start.api_routes()
    assert len(routes) >= 18 and {"/api/health", "/api/filings", "/api/tickers/{ticker}/prices", "/api/events"} <= set(routes)
    for route in routes:  # every GET address the API has was tried, with real values filled in
        address = re.sub(r"\\{\w+\\}", "[^/ ]+", re.escape(route))
        assert re.search(rf"  ok    GET {address}(\s|$)", report), route
    for line in ("ok    the page opens", "ok    the page's file /demo-banner.js", "ok    the page's file /assets/app.js",
                 "ok    a request sent to another name is refused", "ok    another website can't start a run",
                 "ok    Run update now (simulated): ", "ok    Ask (simulated): answered in", "ok    Filings: Check now (simulated SEC)"):
        assert line in report, line
    assert "FAIL" not in report and re.search(r"All \d+ checks passed\.", lines[-1])


def test_the_self_test_names_what_is_broken(demo, monkeypatch):
    url, _, _ = demo
    lines = []
    failed = start.selftest(url, "demo", routes=["/api/health", "/api/portfolio", "/api/portfolio/{holding}", "/api/search"],
                            out=lines.append)
    report = "\n".join(lines)
    assert failed == 2
    assert "FAIL  GET /api/portfolio: answered 404" in report
    assert "FAIL  GET /api/portfolio/{holding}: the self-test has no sample value for 'holding'" in report
    assert "ok    GET /api/search" in report and re.search(r"\d+ checks passed, 2 failed\.", lines[-1])
    monkeypatch.setattr(start, "QUERY_SAMPLES", {})
    lines.clear()
    assert start.selftest(url, "demo", routes=["/api/search"], out=lines.append) == 1
    assert "FAIL  GET /api/search: it needs something in its address: q is required. Add a sample to QUERY_SAMPLES" in "\n".join(lines)
    lines.clear()
    assert start.selftest(f"http://127.0.0.1:{free_port()}", "demo", routes=[], out=lines.append) == 1
    assert "nothing is listening" in "\n".join(lines)


def test_a_real_app_page_with_the_demo_banner_would_be_caught(demo):
    url, _, _ = demo
    lines = []
    assert start.selftest(url, "real", routes=[], out=lines.append) == 1  # (the demo's page, checked as if it were real mode's)
    assert "FAIL  no demo banner in real mode" in "\n".join(lines)


def test_a_demo_without_its_banner_or_its_guard_is_caught():
    """A stand-in server that answers like the app, but serves the plain page, answers to any name, and
    (second time round) accepts every job and then fails it."""
    import http.server
    import json
    import threading

    class Plain(http.server.BaseHTTPRequestHandler):
        jobs_fail = False

        def answer(self, status, body, kind="application/json"):
            body = body if isinstance(body, bytes) else json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", kind)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/api/health":
                self.answer(200, {"status": "ok", "reports": 1})
            elif self.jobs_fail and self.path == "/api/runs/current":
                self.answer(200, {"run": {"state": "failed", "result": None, "error": "the agent crashed"}})
            elif self.jobs_fail and self.path == "/api/filings":
                self.answer(200, {"check": {"state": "failed", "error": "the SEC was unreachable"}})
            else:
                self.answer(200, BUILT.encode(), "text/html")

        def do_POST(self):
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            if not self.jobs_fail:
                self.answer(404, {"error": "not found"})
            elif self.path == "/api/ask":
                self.answer(200, b'{"type": "delta", "text": "I "}\n{"type": "error", "error": "the answer broke off"}\n', "application/x-ndjson")
            else:
                self.answer(202, {})

        def log_message(self, *args):
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Plain)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        lines = []
        failed = start.selftest(url, "demo", routes=[], out=lines.append)
        report = "\n".join(lines)
        assert "FAIL  the demo's banner: the page doesn't load demo-banner.js" in report
        assert "FAIL  a request sent to another name is refused: answered 200" in report
        assert "FAIL  another website can't start a run" in report and "FAIL  Run update now: answered 404" in report
        assert "FAIL  Ask" in report and "FAIL  Filings: Check now: answered 404" in report
        assert failed == 6

        Plain.jobs_fail = True
        lines.clear()
        failed = start.selftest(url, "demo", routes=[], out=lines.append)
        report = "\n".join(lines)
        assert "FAIL  Run update now: the agent crashed" in report
        assert "FAIL  Ask: the answer broke off" in report
        assert "FAIL  Filings: Check now: the SEC was unreachable" in report
        assert failed == 6
    finally:
        server.shutdown()
        server.server_close()


@pytest.mark.skipif(sys.platform == "win32", reason="signals work differently on Windows")
def test_stopping_doesnt_wait_for_open_browser_tabs(tmp_path):
    process, url, _ = launch(tmp_path, {})
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    tab = opener.open(url + "/api/events", timeout=30)  # what an open tab holds: the live-updates stream
    try:
        assert tab.status == 200 and tab.readline().startswith(b"retry")
        began = time.monotonic()
        process.send_signal(signal.SIGTERM)  # docker stop
        process.wait(12)
        assert time.monotonic() - began < 8  # Docker waits 10 seconds, then kills
    finally:
        tab.close()
        stop(process)


def test_real_mode_starts_without_keys_and_explains_what_is_missing(real):
    process, url, log = real({"MODE": '"real"'})  # written with quotes, as people do in a settings file
    text = log.read_text()
    assert "Removed the quotes around MODE (a settings file needs none)." in text
    assert "real mode" in text and "Your reports, search index and watchlist are in" in text
    assert "No ANTHROPIC_API_KEY: the app opens, but runs, questions and first takes won't work." in text
    assert "No SEC_CONTACT: company filings stay off" in text
    assert "isn't a volume: your reports live inside this container and are deleted with it." in text
    assert "Schedule: off." in text and "[schedule]" not in text and "Sample data" not in text
    assert "after the close" not in text


def test_real_mode_says_when_the_after_close_run_is_on(real):
    # (no job times, so nothing can start while the test runs; the key isn't real either)
    process, url, log = real({"SCHEDULE": "on", "ANTHROPIC_API_KEY": "sk-not-a-real-key", "RUN_TIMES": "",
                              "CALENDAR_TIMES": "", "FILINGS_TIMES": ""})
    text = log.read_text()
    assert "Schedule: the day's final report is also written after the close, at 16:15 New York time" in text
    assert "sk-not-a-real-key" not in text


def test_real_mode_keeps_everything_in_its_data_folder(real, tmp_path):
    process, url, _ = real()
    data = tmp_path / "data"
    starter = start.MAIN / "watchlist.txt"
    assert (data / "watchlist.txt").read_text() == starter.read_text()   # begins as a copy of the image's list
    status, _, body = start.request("GET", url + "/api/watchlist")
    first = start._json(body)["stocks"][0]
    status, _, body = start.request("POST", f"{url}/api/watchlist/{first['ticker']}", {"main": not first["main"]})
    assert status == 200, body
    assert (data / "watchlist.txt").read_text() != starter.read_text()   # the Stocks tab edits the copy in the data folder
    assert start.request("GET", url + "/api/health")[0] == 200 and (data / "reports.db").is_file()
    assert not (tmp_path / "demo").exists()                               # no sample data is made in real mode


def test_an_existing_watchlist_and_reports_are_kept(real, tmp_path):
    write(tmp_path / "data" / "watchlist.txt", "*TSLA\nKO  XLP  # mine\n")
    process, url, _ = real()
    assert (tmp_path / "data" / "watchlist.txt").read_text() == "*TSLA\nKO  XLP  # mine\n"
    stocks = start._json(start.request("GET", url + "/api/watchlist")[2])["stocks"]
    assert [s["ticker"] for s in stocks] == ["TSLA", "KO"]


def program(folder: Path, answer: str = "", error: str = "", code: int = 0) -> str:
    """A small stand-in for Claude Code: a program that answers --version (a shell script, or on Windows
    a batch file)."""
    if sys.platform == "win32":
        lines = ["@echo off", *([f"echo {answer}"] if answer else []), *([f"echo {error} 1>&2"] if error else []),
                 f"exit /b {code}"]
        return str(write(folder / "claude.cmd", "\r\n".join(lines) + "\r\n"))
    lines = ["#!/bin/sh", *([f'echo "{answer}"'] if answer else []), *([f"echo '{error}' >&2"] if error else []),
             f"exit {code}"]
    path = write(folder / "claude", "\n".join(lines) + "\n")
    path.chmod(0o755)
    return str(path)


def test_real_modes_self_test_only_reads(real, monkeypatch, tmp_path):
    process, url, _ = real({"ANTHROPIC_API_KEY": "sk-not-a-real-key"})
    monkeypatch.setattr(start, "claude_code", lambda: program(tmp_path, answer="9.9.9 (Claude Code)"))
    asked, original = [], start.request

    def recording(method, address, body=None, **more):
        asked.append((method, address, body))
        return original(method, address, body, **more)

    monkeypatch.setattr(start, "request", recording)
    lines = []
    assert start.selftest(url, "real", out=lines.append) == 0, "\n".join(lines)
    assert len(asked) > 20 and all(method == "GET" and body is None for method, _, body in asked)  # nothing that could cost money
    report = "\n".join(lines)
    assert "skip  GET /api/reports/latest: nothing saved yet" in report and "Run update now" not in report
    assert "ok    the page opens" in report and "demo-banner" not in report
    assert "ok    the agent's program (Claude Code) starts: 9.9.9 (Claude Code)" in report


def test_an_image_whose_agent_cant_start_is_caught(tmp_path, monkeypatch):
    what = "the agent's program (Claude Code)"
    for found, expected in ((None, f"FAIL  {what}: it isn't here, so runs, questions and first takes would fail"),
                            (program(tmp_path / "wrong-processor", error="cannot execute binary file", code=126),
                             f"FAIL  {what}: it is here but didn't start"),
                            (str(tmp_path / "not-a-program"), f"FAIL  {what}: it is here but didn't start"),
                            (program(tmp_path / "silent"), f"FAIL  {what}: it is here but didn't start (no answer)"),
                            (program(tmp_path / "working", answer="2.1.0 (Claude Code)"), f"ok    {what} starts: 2.1.0 (Claude Code)")):
        monkeypatch.setattr(start, "claude_code", lambda found=found: found)
        lines = []
        checks = start.Checks(lines.append)
        start._agent_check(checks)
        assert expected in lines[0] and len(checks.failed) == (0 if expected.startswith("ok") else 1)
    # In the demo it isn't asked for at all: the demo never starts it
    monkeypatch.setattr(start, "claude_code", lambda: pytest.fail("the demo's self-test looked for Claude Code"))
    lines = []
    start.selftest(f"http://127.0.0.1:{free_port()}", "demo", routes=[], out=lines.append)


def test_claude_code_is_looked_for_where_the_sdk_keeps_it(tmp_path, monkeypatch):
    import types
    package = tmp_path / "claude_agent_sdk"
    write(package / "__init__.py")
    monkeypatch.setitem(sys.modules, "claude_agent_sdk", types.SimpleNamespace(__file__=str(package / "__init__.py")))
    monkeypatch.setattr(start.shutil, "which", lambda name: "/somewhere/on/the/path/claude" if name == "claude" else None)
    assert start.claude_code() == "/somewhere/on/the/path/claude"          # not in the package: the PATH
    name = "claude.exe" if os.name == "nt" else "claude"
    write(package / "_bundled" / name, "the program")
    assert start.claude_code() == str(package / "_bundled" / name)         # in the package: that one first
    monkeypatch.setattr(start.shutil, "which", lambda name: None)
    (package / "_bundled" / name).unlink()
    assert start.claude_code() is None


def test_a_data_folder_that_cant_be_written_is_explained(real, tmp_path):
    blocked = write(tmp_path / "a-file", "not a folder")
    process, _, log = real({"DATA_DIR": str(blocked / "data")}, wait=False)
    assert process.wait(30) == 1
    text = log.read_text()
    assert "Can't write to" in text and "-v market-agent-data:/data" in text and "Traceback" not in text


def test_a_wrong_mode_stops_with_a_plain_message(real, tmp_path):
    process, _, log = real({"MODE": "production"}, wait=False)
    assert process.wait(30) == 1 and log.read_text().strip() == "MODE must be demo or real, not 'production'."


def test_the_agents_tools_follow_the_watchlist_setting(tmp_path):
    """The agent starts market_tools.py as its own program, so the setting has to reach it through the environment."""
    mine = write(tmp_path / "data" / "watchlist.txt", "*TSLA\nKO  XLP\n")
    show = "import market_tools; print(market_tools.WATCHLIST_FILE); print(market_tools.load_watchlist())"
    env = {k: v for k, v in os.environ.items() if k != "WATCHLIST_FILE"}

    def ask(**settings) -> list[str]:
        result = subprocess.run([sys.executable, "-c", show], cwd=start.MAIN, env={**env, **settings}, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        return result.stdout.splitlines()

    assert ask(WATCHLIST_FILE=str(mine)) == [str(mine), "['TSLA', 'KO']"]
    for unset in (ask(), ask(WATCHLIST_FILE="")):  # not set, or set to nothing: next to the code, as before
        assert Path(unset[0]).resolve() == (start.MAIN / "watchlist.txt").resolve()


# ---------------------------------------------------------------------------
# A real image, if you have built one
# ---------------------------------------------------------------------------

def test_the_built_image_passes_its_checks():
    image = os.environ.get("CONTAINER_TEST_IMAGE")
    if not image:
        pytest.skip("set CONTAINER_TEST_IMAGE=market-agent:local to test an image you built")
    if not shutil.which("docker") or subprocess.run(["docker", "image", "inspect", image], capture_output=True).returncode != 0:
        pytest.skip(f"Docker isn't running here, or there is no image called {image}")
    assert container.test_image(image, port_check=os.environ.get("CONTAINER_PORT_CHECK", "1") != "0") == []


# ---------------------------------------------------------------------------
# Isolation (keep this last)
# ---------------------------------------------------------------------------

def test_the_other_folders_were_not_touched():
    assert snapshot(start.MAIN) == MAIN_BEFORE
    assert snapshot(start.TESTENV) == TESTENV_BEFORE
    assert not (HERE / ".build").exists() or (HERE / ".build" / container.MARKER).is_file()
```

## Appendix B: the changed file in market-agent

*This project:* this is this project's `market_tools.py`, with its own fixes (BUG-01 and BUG-03 in `test-case-reporting.md`). Don't replace yours with the guide's original: only add the `import os` line and change the `WATCHLIST_FILE` line, as section 4.2 shows.

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
briefs can say what's coming up. past_moves reads the follow-through of earlier flagged
moves (followups.py), so briefs can say how similar moves played out. recent_filings reads
what companies have filed with the SEC (filings.py), so a move can be explained from the
company's own announcement.

Every flagged move also comes with sector and market context: how the ticker did
against its sector ETF and the S&P 500, and whether that gap was unusual. That
tells the agent whether a move was about the company, its sector, or the market.

Test it on its own:  npx @modelcontextprotocol/inspector python market_tools.py
"""

import os
from contextlib import closing
from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer

import reports_db

# WATCHLIST_FILE moves the list somewhere else (the container keeps it with its data). It is an environment
# setting, not an argument, because the agent starts this file as a program of its own.
WATCHLIST_FILE = Path(os.environ.get("WATCHLIST_FILE") or Path(__file__).parent / "watchlist.txt")
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


def read_watchlist_text() -> str:
    """watchlist.txt as text. The app saves it as UTF-8. A byte-order mark (which some Windows
    editors add) is skipped, and a file saved in the older Windows encoding still reads.
    Never rely on Python's default encoding here: on Windows it isn't UTF-8."""
    data = WATCHLIST_FILE.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _watchlist_entries() -> list[list[str]]:
    """Each line: a ticker, optionally followed by the benchmark to compare it with.
    A * before the ticker marks a main stock for the dashboard (see watchlist.py); the
    agent tracks every ticker either way. Anything after a # is a comment."""
    entries = []
    for line in read_watchlist_text().splitlines():
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
    daily = yf.Ticker(ticker).history(period="3mo").dropna(subset=["Close"])  # a day without a price is a missing day
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
    bars = yf.Ticker(ticker).history(period="1mo", interval="5m").dropna(subset=["Close"])  # e.g. a bar not filled in yet
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


@mcp.tool()
def past_moves(tickers: list[str], kinds: list[str] | None = None) -> dict:
    """How earlier flagged moves played out a week later (held, faded or reversed), for the
    "Worth watching" line. Give it the flagged tickers, and each one's `context.read` as `kinds`
    in the same order. For each ticker: its own past flagged moves, moves of the same kind across
    the watchlist, the latest story update, and `summary`, a ready-made sentence to use only when
    `worth_mentioning` is true.
    """
    import followups  # imported here, not at the top, because followups.py imports this module
    kinds = list(kinds or [])
    wanted = [t.strip().upper() for t in tickers if t.strip()][:30]
    try:
        with closing(reports_db.connect(readonly=True)) as conn:
            found = {t: followups.past_for(conn, t, kinds[i] if i < len(kinds) else None) for i, t in enumerate(wanted)}
            known = followups.last_update(conn)
    except Exception as e:  # no database yet, or it's busy: the brief just goes without
        return {"moves": {}, "note": f"Past moves aren't available ({e})."}
    result = {"horizon_days": followups.SURPRISE_HORIZON, "moves": found}
    if not known:
        result["note"] = "Follow-through hasn't been worked out yet, so there's nothing to compare with."
    return result


@mcp.tool()
def recent_filings(tickers: list[str], days: int = 3) -> dict:
    """What companies have filed with the SEC in the last few days: results announcements, other
    announcements and reports. Give it the flagged tickers. A filing that has been read has a
    `first_take` (headline, key points, figures and guidance, all checked against the filing in
    code): use it for "Likely why", cited with the filing's `url`. `expected` lists results the
    calendar expected in the last few days that hadn't been filed yet.
    """
    import filings  # imported here, not at the top, because filings.py imports this module
    days = max(1, min(int(days), 14))
    wanted = [t.strip().upper() for t in tickers if t.strip()][:30]
    try:
        with closing(reports_db.connect(readonly=True)) as conn:
            found = {t: filings.recent_for(conn, t, filings._days_ago(days)) for t in wanted}
            checked = filings.last_check(conn)
            waiting = [e for e in filings.expected(conn, now_et().date()) if e["ticker"] in wanted]
    except Exception as e:  # no database yet, or it's busy: the brief just goes without
        return {"filings": {}, "note": f"Filings aren't available ({e})."}
    result = {"days": days, "filings": {t: f for t, f in found.items() if f}, "expected": waiting,
              "checked": checked["finished_at"] if checked else None}
    if not checked:
        result["note"] = "Filings haven't been checked yet, so nothing is known about them."
    return result


if __name__ == "__main__":
    mcp.run()  # speaks MCP over stdio; the agent starts this as a subprocess
```
