# Market Analyst Agent: Discord Alerts

The agent posts to a Discord channel when a ticker is newly flagged during the day, and posts a short summary once the day's final report is saved. You hear about a big move without opening the app, and alerts reach your phone through the Discord app.

This builds on `market-agent-sector-context.md`. Do that guide first: alerts include its verdicts, and this guide's files include its changes.

---

## Contents

1. [What you'll get](#1-what-youll-get)
2. [How it works](#2-how-it-works)
3. [Before you start](#3-before-you-start)
4. [Step 1: Create a Discord webhook](#4-step-1-create-a-discord-webhook)
5. [Step 2: Set the webhook address](#5-step-2-set-the-webhook-address)
6. [Step 3: Add the alerts module](#6-step-3-add-the-alerts-module)
7. [Step 4: Send alerts after each run](#7-step-4-send-alerts-after-each-run)
8. [Step 5: Show alert status in the app](#8-step-5-show-alert-status-in-the-app)
9. [Step 6: Add the tests](#9-step-6-add-the-tests)
10. [Step 7: Try it](#10-step-7-try-it)
11. [Test it](#11-test-it)
12. [Getting phone notifications](#12-getting-phone-notifications)
13. [Settings and timing](#13-settings-and-timing)
14. [Commands and API reference](#14-commands-and-api-reference)
15. [Privacy and security](#15-privacy-and-security)
16. [Troubleshooting](#16-troubleshooting)
17. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What you'll get

**A flag alert** while the market is open. Each ticker gets its own card, with a green or red stripe for up or down. These examples came from the test environment, so the prices and news are simulated:

```
Market Analyst
1 new flag in the intraday update as of 12:45 ET
┃ MSFT +4.96% so far today
┃ z-score 2.98 · volume 1.68x normal for this time of day
┃ Vs. sector and market: MSFT rose 4.96% so far today; its sector (Technology, XLK) fell 0.13% and the
┃ S&P 500 fell 0.33%. That is 5.09 points better than its sector, an unusual gap for MSFT (z-score 4.1),
┃ so the move looks specific to MSFT.
┃ Likely why: A new product announcement drew buyers. Demo Markets Daily
┃ As of 2026-11-06 12:45 ET · research, not investment advice
```

**An end-of-day summary** after the final report:

```
Market Analyst
Daily summary: 1 flagged move
┃ Watchlist brief: 2026-11-06
┃ Market: The S&P 500 fell 0.47% (z-score -0.4). Strongest sector: Utilities (XLU) +1.29%;
┃ weakest: Financials (XLF) -1.64%.
┃ MSFT +7.02% (z-score 3.01) · stock-specific
┃ A new product announcement drew buyers. Demo Markets Daily
┃ Quiet: AAPL -0.18%, AMZN +0.51%, JPM +0.52%, NVDA +0.44%
┃ End-of-day summary · research, not investment advice
```

In Discord, the publisher names are links to the articles.

**When alerts are sent:**

| Situation | What's sent |
|---|---|
| A run while the market is open flags tickers not alerted yet today | One message, with a card for each newly flagged ticker (up to 10) |
| A later run flags the same ticker again | Nothing, unless its z-score has grown by 1.5 or more ("Bigger move") or it has reversed direction past ±2 ("Reversal") |
| A run saves the day's final report | One end-of-day summary |
| A later run finds the final report already saved | Nothing, unless that day's summary failed to send earlier; then it's sent now |
| Sending fails (Discord down, no internet) | Logged as failed, and the next run tries again. The run itself still succeeds, with a warning |
| No webhook is set | Nothing is sent or logged. Everything else works as before |

After the close there are no flag alerts, only the summary, which covers every flagged ticker.

---

## 2. How it works

```
run_brief.py (scheduled, or "Run update now")
   1. the agent writes the report → saved to reports.db       (as before)
   2. the search index is updated                              (as before)
   3. alerts.notify(day):
        compare the saved report with the alerts log (in reports.db)
        → decide what's new, and claim it in the log           (one database transaction)
        → post to the Discord webhook
        → mark each one sent or failed
```

- **The saved report is the source.** The "Likely why" text is the agent's own words from the brief. The "Vs. sector and market" sentence and figures come from the stored comparison. Alerts never call Claude, so they add no cost.
- **Each alert is logged** in a new `alerts` table in `reports.db`: what was sent, when, and any error. A failed alert isn't counted as sent, so the next run tries again.
- **No double alerts from runs at the same moment.** If a scheduled run and "Run update now" finish together, the first to claim a ticker sends it. If a run crashes mid-send, its claim expires after 2 minutes.
- **Discord's limits are respected.** A message is limited to 10 cards and 6,000 characters. Long text is shortened, and links are turned into plain text before anything is cut, so a link is never broken. If Discord asks for a pause (rate limit), the send waits and retries once.
- **Alerts never break a run.** Any problem is shown as a warning, in the terminal and in the app's run log.

---

## 3. Before you start

- [ ] You've done `market-agent-sector-context.md`, and `pytest` shows `125 passed, 1 skipped`.
- [ ] You have a Discord account and a server where you can manage webhooks. Your own server works: in Discord, use the **+** button (Add a Server) to create a free one.

No new Python packages are needed. Sending uses Python's standard library.

---

## 4. Step 1: Create a Discord webhook

A webhook is a private address that lets a program post to one channel.

1. In Discord, create a channel for alerts (for example `#market-alerts`). A private channel is best.
2. Open your server's **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**. You can also start from the channel itself: **Edit Channel** → **Integrations** → **Webhooks**. You need the **Manage Webhooks** permission; a server's owner has it.
3. Choose your alerts channel. The name and avatar don't matter: each message is posted as "Market Analyst".
4. Click **Copy Webhook URL**. It looks like `https://discord.com/api/webhooks/1234.../AbCd...`.

**Treat this address like a password.** Anyone who has it can post in your channel. Don't put it in code or commit it to git. If it leaks, delete the webhook (**Integrations** → **Webhooks** → **Delete Webhook**) and create a new one.

Discord's menus change from time to time. If a label differs, look for the webhooks option under the server's or channel's integrations.

---

## 5. Step 2: Set the webhook address

Set `DISCORD_WEBHOOK_URL` the same way as your other keys:

```bash
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."   # macOS / Linux (add to ~/.zshrc or ~/.bashrc to keep it)
setx DISCORD_WEBHOOK_URL "https://discord.com/api/webhooks/..."     # Windows (then open a new terminal)
```

Alerts are sent by whatever runs the agent, so the address must be set in each place runs happen:

| Where runs happen | How to set it |
|---|---|
| `python run_brief.py` in a terminal | The command above |
| "Run update now" in the app | Set it in the terminal before starting `uvicorn api:app` |
| Scheduled runs with cron (macOS / Linux) | Add `DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...` to your crontab, next to `ANTHROPIC_API_KEY` (main guide, section 8) |
| Scheduled runs with Task Scheduler (Windows) | `setx` as above, then sign out and back in so Task Scheduler sees it |

**Optional:** set `ALERTS_APP_URL` (for example `http://localhost:8000`) to add a link to the app on each message. It only opens on the computer running the app.

---

## 6. Step 3: Add the alerts module

Create `alerts.py` from the [appendix](#alertspy).

It contains:

- **The rules:** what's new since the last alert.
- **The message building:** cards, summaries and Discord's limits.
- **The sending:** a JSON post to the webhook that pings nobody (mentions are switched off), with one retry if rate limited.
- **The alerts log.**
- **A small command line:** `test`, `preview`, `log` and `summary` (section 14).

---

## 7. Step 4: Send alerts after each run

Replace `run_brief.py` and `api.py` with the appendix versions.

- **`run_brief.py`**:
  - After saving a report and updating the search index, it calls `send_alerts()`.
  - It also calls `send_alerts()` when it skips because the final report is already saved, so a failed summary gets another try.
  - The terminal shows a line such as `Discord: sent flag alert: NVDA`.
- **`api.py`** adds `GET /api/alerts`. It reports whether this server's runs send alerts, plus the latest alerts from any run. It never includes the webhook address.

---

## 8. Step 5: Show alert status in the app

Replace these files in `frontend/src/` with the appendix versions:

| File | Change |
|---|---|
| `api.js` | `getAlerts()` |
| `format.js` | `formatDateTime()` |
| `components/RunPanel.jsx` | A status line under "Run update now" |
| `App.jsx` | Passes "a report was saved" to the run panel, so the line refreshes |
| `styles.css` | Two lines of styling |

Then rebuild if you serve the built app (`cd frontend && npm run build`).

The status line shows one of:

- **"Discord alerts on · last sent Nov 7, 3:48 PM (MSFT)"**
- **"Discord alerts off for runs started here"**: the API was started without `DISCORD_WEBHOOK_URL`. Scheduled runs may still send; the "last sent" part shows alerts from any run.
- **"· last alert failed: …"** in red, with the reason. The next run retries.

It refreshes after each run, when a report is saved, and once a minute.

---

## 9. Step 6: Add the tests

1. Add `tests/conftest.py` from the [appendix](#testsconftestpy). It makes sure tests can never post to your real Discord (or send text to Voyage), even when those variables are set in your terminal.
2. Add `tests/test_alerts.py`.
3. Run:

```bash
pytest -v
```

**Expected result:** `148 passed, 1 skipped`.

---

## 10. Step 7: Try it

1. **Send a test message:**

   ```bash
   python alerts.py test
   ```

   "Alerts are set up" should appear in your channel within a second or two.

2. **Preview** what the latest report would send now, without sending. This works before you set up a webhook:

   ```bash
   python alerts.py preview            # or: python alerts.py preview 2026-11-06
   ```

3. **During market hours**, run `python run_brief.py`. If anything is newly flagged, the terminal ends with `Discord: sent flag alert: ...` and the message arrives. Run it again: nothing repeats unless a move grew a lot.

4. **After the close**, run it again. The final report is saved and the summary arrives: `Discord: sent daily summary for ...`.

5. **See the log:**

   ```bash
   python alerts.py log
   ```

**Tip:** to experiment without filling your main channel, make a second webhook in a test channel and set that one in your terminal while testing.

---

## 11. Test it

### 11.1 Automated tests

| Test | Proves that |
|---|---|
| `test_no_webhook_means_nothing_is_sent` | Without a webhook, nothing is sent or logged |
| `test_webhook_must_be_a_discord_address` | Only Discord webhook addresses are accepted |
| `test_a_newly_flagged_ticker_alerts_once_per_day` | A ticker alerts once a day; a newly flagged ticker later in the day gets its own alert |
| `test_a_much_bigger_move_alerts_again` | A z-score that grows by 1.5 or more sends a "Bigger move" card showing the earlier figure |
| `test_a_reversal_alerts_again` | A move that reverses past ±2 sends a "Reversal" card |
| `test_volume_only_flag_alerts_once` | A volume-only flag doesn't re-alert as volume keeps rising |
| `test_flag_alert_shows_context_and_the_agents_explanation` | Cards carry the figures, the sector sentence, the agent's "Likely why" with its link, the right color and the "not investment advice" footer |
| `test_many_flags_fit_in_one_message_within_discords_limits` | 14 flags with very long text become one message within Discord's 10-card and 6,000-character limits, and all 14 count as alerted |
| `test_final_report_sends_one_summary` | The final report sends one summary (backdrop, flagged moves with verdicts and reasons, quiet tickers), never twice |
| `test_quiet_day_summary` | A day with no flags still gets a short summary |
| `test_final_report_sends_no_flag_alerts` | After the close, only the summary is sent |
| `test_a_failed_alert_is_logged_and_retried_next_run` | A failed send is logged with its reason, and the next run sends it |
| `test_an_alert_being_sent_by_another_run_is_not_doubled` | A ticker claimed by another run isn't sent twice; a claim left by a crashed run expires |
| `test_post_sends_safe_json_to_the_webhook` | The request goes to the webhook with `?wait=true`, a JSON body, the "Market Analyst" name, and mentions switched off |
| `test_post_waits_and_retries_once_when_rate_limited` | When Discord asks for a pause, the send waits that long and retries once |
| `test_post_errors_are_clear_and_never_show_the_webhook` (3 cases) | A deleted webhook, a rejected message and no connection each give a clear error, and the webhook's secret part never appears in it |
| `test_a_run_sends_alerts_after_saving` | A real run (with a fake agent) saves, then alerts, and shows it in the run log |
| `test_alert_problems_never_fail_a_run` | A send failure becomes a warning; the run still succeeds |
| `test_a_skipped_run_retries_a_summary_that_failed` | A run that skips Claude (final already saved) still sends a summary that failed earlier |
| `test_api_shows_alert_status` | `/api/alerts` works before any alert exists, then lists sent alerts |
| `test_preview_shows_messages_without_sending` | `alerts.py preview` prints the messages and sends and logs nothing |

**Check the tests catch real bugs.** Make one of these temporary changes in `alerts.py`, run `pytest tests/test_alerts.py`, then change it back. Each was tried:

| Temporary change | Tests that fail |
|---|---|
| `ESCALATE_Z = 1.5` → `ESCALATE_Z = 0.0` (every run re-alerts) | The once-per-day, volume-only and no-doubling tests |
| In `_already`, count failed alerts as sent: `status = 'sent'` → `status IN ('sent', 'failed')` | Both retry tests |
| In `post`, delete `"allowed_mentions": {"parse": []}, ` | `test_post_sends_safe_json_to_the_webhook` |

### 11.2 What was also tested

- **Real HTTP sending, against a local stand-in for Discord:**
  - The first reply was "429, retry after 0.2 seconds". The send waited and retried, and got the message id.
  - A "404 Unknown Webhook" gave the "doesn't exist" error.
  - The path, `?wait=true`, the headers and the JSON body were all checked.
- **The test environment** (`market-agent-test-enviro.md`). Its simulated alerts follow these exact rules, written to a file instead of Discord:
  - On two months of sample data, `update` alerted the newly flagged ticker once.
  - A second `update` didn't repeat it.
  - `finalize` sent one summary, and a skipped run sent nothing more.
- **In a real browser, against the test environment:**
  - The status line read "Discord alerts on".
  - "Run update now" showed "Discord: sent flag alert: MSFT".
  - The status line updated to "last sent … (MSFT)".
  - The message was in the outbox, and nothing was sent to Discord.
- **From the guides alone:** the project was rebuilt from the guides and all tests passed.

**Not tested here:** posting to real Discord, since these were built without access to it. Do the checks below once.

### 11.3 Checks with your real Discord

- [ ] `python alerts.py test` posts "Alerts are set up", from "Market Analyst"
- [ ] A flag alert has a green or red stripe, and its publisher link opens the article
- [ ] Running again within the day doesn't repeat it
- [ ] The summary arrives after the final report
- [ ] Your phone shows a notification (section 12)
- [ ] **Failure and recovery:**
  1. In a test channel, delete the webhook you set and run once. The run succeeds with the warning "Discord says this webhook doesn't exist", and `python alerts.py log` shows `failed`.
  2. Set a new webhook and run again. The alert is sent.

---

## 12. Getting phone notifications

1. Install the Discord app on your phone and sign in.
2. Webhook messages don't @mention anyone, so set the alerts channel to notify you for **all messages**. Open the channel's notification settings (right-click or long-press the channel) and choose **All Messages**.
3. Check that notifications for Discord are allowed in your phone's settings.

Muting the channel stops the notifications but keeps the messages, if you only want to read alerts sometimes.

---

## 13. Settings and timing

At the top of `alerts.py`:

| Setting | Default | What it does |
|---|---|---|
| `SEND_FLAG_ALERTS` | `True` | Alerts for newly flagged tickers while the market is open |
| `SEND_DAILY_SUMMARY` | `True` | One summary after each final report |
| `ESCALATE_Z` | `1.5` | How much a ticker's z-score must grow before it alerts again the same day |
| `PENDING_SECONDS` | `120` | How long another run's claim on an alert counts as "being sent" |
| `USERNAME` | `Market Analyst` | The name messages are posted under |
| `COLORS` | green / red / grey | Card stripe colors |

| Environment variable | What it does |
|---|---|
| `DISCORD_WEBHOOK_URL` | Turns alerts on |
| `ALERTS_APP_URL` | Optional: adds a link to the app on each message |

**How many alerts, and when.** Alerts can only arrive when a run happens:

- **Flag alerts:** with the main guide's schedule (8:15am and 12:30pm), the 12:30 run is the only one during market hours. So you get at most one flag message a day, at about 12:30. Add more intraday runs (for example 10:30am and 2:30pm) to hear sooner. Each run costs a Claude run.
- **The summary:** with that schedule, it arrives with the 8:15am run the next morning, since that run writes the final report. Add a run after the close (for example 4:30pm New York time) to get it the same evening.
- **The number of flags:** the flagging thresholds in `flag_events` decide how many tickers get flagged, so they decide alert volume too. If alerts are too noisy, raise them (testing guide, section 9).

---

## 14. Commands and API reference

```bash
python alerts.py test                      # send a test message
python alerts.py preview [DATE]            # print what would be sent now; sends and logs nothing
python alerts.py log                       # recent alerts: when, what, sent or failed, and why
python alerts.py summary DATE [--force]    # send a day's summary by hand (--force sends it again)
```

`GET /api/alerts?limit=10` returns:

```json
{
  "enabled": true,
  "alerts": [
    {"session_date": "2026-11-06", "kind": "flag", "ticker": "MSFT", "return_1d_pct": 4.96,
     "return_zscore": 2.98, "as_of": "2026-11-06 12:45 ET", "status": "sent", "error": null,
     "created_at": "2026-11-06T17:46:02Z", "sent_at": "2026-11-06T17:46:03Z"}
  ]
}
```

`enabled` is about runs started from this server ("Run update now"). `limit` can be 1 to 100. Summaries have `kind: "summary"` and no ticker.

**The `alerts` table** (in `reports.db`): `session_date`, `kind` (`flag` or `summary`), `ticker`, `return_1d_pct`, `return_zscore`, `as_of`, `status` (`pending`, `sent` or `failed`), `error`, `created_at` and `sent_at`.

---

## 15. Privacy and security

- **What goes to Discord:**
  - The flagged tickers on your watchlist, with their figures and sector sentences.
  - The agent's explanations, with news links.
  - In summaries, the quiet tickers' moves.

  Discord stores these like any message. Nothing else leaves your computer for alerts.
- **The webhook address is a secret:**
  - Error messages and logs never include it (a test checks this).
  - The API never returns it.
  - Only real Discord webhook addresses are accepted, so a typo can't send your data elsewhere.
- **No pings:** mentions are switched off on every message, so a headline containing "@everyone" can't notify your whole server.
- **The API can't send alerts by itself.** Only a run sends them. The app's "Run update now" button is protected as before.
- **Tests and the test environment never post to Discord**, even when `DISCORD_WEBHOOK_URL` is set:
  - The tests remove it (`tests/conftest.py`).
  - The test environment writes alerts to a file unless you choose `--live-alerts`.

---

## 16. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `Couldn't send: DISCORD_WEBHOOK_URL isn't set` | The variable isn't set in this terminal. Set it (step 2), or open a new terminal after `setx`. |
| `must be a Discord webhook URL` | You copied something else, such as a channel or invite link. Use **Copy Webhook URL** (step 1). |
| `Discord says this webhook doesn't exist` | The webhook was deleted. Create a new one and update the variable. |
| `Discord refused the message (403) ...` or `(401) ...` | The webhook address is incomplete (check you copied all of it), or a firewall or proxy is blocking Discord. The text after the code is Discord's reason. |
| `couldn't reach Discord (...)` | No internet, or Discord is blocked on this network. The next run retries automatically. |
| "Run update now" sends alerts, but scheduled runs don't | The scheduler doesn't have the variable (step 2: crontab line, or sign out and in after `setx`). Check `run.log`. |
| The app says "off for runs started here", but alerts arrive | The API was started without the variable; scheduled runs have it. Either is fine. Restart the API with it set if you want "Run update now" to send too. |
| A ticker was flagged but no alert came | It was alerted earlier that day (check `python alerts.py log`), or the report was a final one (only the summary is sent), or `SEND_FLAG_ALERTS` is `False`. |
| The summary arrives the next morning | That's when your final report is written. Add an after-close run (section 13). |
| An alert came twice | Two copies of the project, or two different databases (`REPORTS_DB`), each sending with the same webhook. The alert log is per database. |
| No phone notification | Set the channel to **All Messages** (section 12), and check Discord's notifications are allowed on your phone. |
| Test messages appear in your channel | `tests/conftest.py` is missing. Add it from the appendix. |

---

## Appendix: full source code

### alerts.py

```python
"""Discord alerts for the market analyst agent.

After each run saves a report, run_brief.py calls notify(), which compares the saved
report with the alerts already sent and posts whatever is new:
- While the market is open: one message for tickers flagged for the first time today.
  A ticker alerts once per day, unless its move later grows a lot (or reverses).
- After the final report: one end-of-day summary per day.
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
from datetime import datetime, timedelta, timezone

import reports_db

WEBHOOK_ENV = "DISCORD_WEBHOOK_URL"
APP_URL = os.environ.get("ALERTS_APP_URL", "").rstrip("/")  # e.g. http://localhost:8000: adds links to the app
SEND_FLAG_ALERTS = True      # newly flagged tickers while the market is open
SEND_DAILY_SUMMARY = True    # one summary after each final report
ESCALATE_Z = 1.5             # alert a ticker again the same day if its |z-score| grows by this much
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


def flag_embed(t: dict, report: dict, previous: dict | None = None) -> dict:
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
    return {
        "title": _shorten(title, MAX_TITLE),
        "description": _shorten("\n".join(lines), MAX_DESCRIPTION),
        "color": COLORS["up" if pct > 0 else "down" if pct < 0 else "neutral"],
        "footer": {"text": f"As of {report['as_of']} · research, not investment advice"},
        **_app_link("#/"),
    }


def flags_payload(report: dict, items: list[tuple[dict, dict | None]]) -> dict:
    new = sum(1 for _, previous in items if previous is None)
    bigger = len(items) - new
    parts = [f"{new} new flag{'s' if new != 1 else ''}"] if new else []
    if bigger:
        parts.append(f"{bigger} bigger move{'s' if bigger != 1 else ''}")
    content = f"**{' and '.join(parts).capitalize()}** in the intraday update as of {report['as_of'][11:]}"
    if len(items) > MAX_EMBEDS:
        content += f" (showing {MAX_EMBEDS}; the rest are in the app)"
    return {"content": content, "embeds": _fit([flag_embed(t, report, prev) for t, prev in items[:MAX_EMBEDS]])}


def summary_payload(report: dict) -> dict:
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
                messages.append((label, ids, flags_payload(report, todo["flags"])))
            if todo["summary"]:
                messages.append((f"daily summary for {session_date}", [_record(conn, session_date, "summary", report)],
                                 summary_payload(report)))
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
        if todo["report"] is None:
            sys.exit(f"No report for {day}.")
        payloads = []
        if todo["flags"]:
            payloads.append(flags_payload(todo["report"], todo["flags"]))
        if todo["summary"]:
            payloads.append(summary_payload(todo["report"]))
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
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules
(a run also logs the Discord alerts it sends).
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
from datetime import datetime, timezone
from pathlib import Path

from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Mount, Route
from starlette.staticfiles import StaticFiles

import alerts
import ask
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
            update_index_in_background()  # covers scheduled runs, which are separate programs


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

### frontend/src/App.jsx

```jsx
import { useCallback, useEffect, useRef, useState } from 'react'
import { getCurrentRun, getLatestReport } from './api'
import { ChartContext } from './chartContext'
import { useLiveEvents } from './useLiveEvents'
import { routes, useRoute } from './useRoute'
import AskPanel from './components/AskPanel'
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
    <ChartContext.Provider value={openChart}>
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
              <RunPanel run={run} onStarted={onRunStarted} lastSaved={lastSaved} />
              <AskPanel />
            </aside>
          </main>

          <PreviousDaysPreview latestDate={latest?.session_date} lastSaved={lastSaved} />
        </div>

        <div hidden={route.tab !== 'previous'}>
          <PreviousDaysTab latestDate={latest?.session_date} lastSaved={lastSaved} selectedDate={route.date} />
        </div>

        {chartTicker && <TickerChart ticker={chartTicker} latestDate={latest?.session_date} onClose={closeChart} />}
      </div>
    </ChartContext.Provider>
  )
}
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
```

### tests/conftest.py

```python
"""Shared test setup: tests never reach real services, whatever is set in your terminal.

Without this, running pytest in a terminal where DISCORD_WEBHOOK_URL is set would post
test alerts to your real Discord channel (and VOYAGE_API_KEY would send test text to Voyage).
Tests that need these set them themselves.
"""

import pytest


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    for name in ("DISCORD_WEBHOOK_URL", "VOYAGE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
```

### tests/test_alerts.py

```python
"""Offline tests for Discord alerts. Nothing is sent to Discord: sending is faked.

Run from the project folder:
    pytest -v tests/test_alerts.py
"""

import asyncio
import io
import json
import sys
import urllib.error
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

WEBHOOK = "https://discord.com/api/webhooks/123/secret-token"
DAY = "2026-11-06"


def ticker(symbol, pct=-4.2, z=-3.1, volume=2.5, read="stock-specific"):
    return {"ticker": symbol, "last_price": 150.0, "return_1d_pct": pct, "return_5d_pct": -5.0,
            "return_zscore": z, "volume_vs_avg": volume, "compared_to": "test",
            "context": {"benchmark": "XLK", "benchmark_return_pct": -1.0, "market_return_pct": -0.5,
                        "vs_benchmark_pct": pct + 1.0, "vs_benchmark_zscore": -2.6, "read": read,
                        "summary": f"{symbol} fell; its sector (Technology, XLK) fell 1.00%. Looks specific to {symbol}."}}


def brief(title, flagged):
    lines = [f"# {title}", "", "## Market backdrop", "",
             "The S&P 500 fell 0.50% (z-score -0.9). Strongest sector: Energy (XLE) +0.80%; "
             "weakest: Technology (XLK) -1.00%.", "", "## Notable moves", ""]
    for t in flagged:
        lines += [f"### {t['ticker']}: {t['return_1d_pct']}% (z-score {t['return_zscore']}, volume {t['volume_vs_avg']}x normal)",
                  "- **What happened:** it moved.",
                  "- **Vs. sector and market:** see context.",
                  f"- **Likely why:** An analyst downgrade weighed on {t['ticker']}. [Reuters](https://example.com/{t['ticker']})",
                  "- **Worth watching:** the next session.", ""]
    lines += ["## Quiet", "", "AAPL (+0.30%)"]
    return "\n".join(lines)


def save(*flagged, status="intraday", at="10:30"):
    as_of = DAY if status == "final" else f"{DAY} {at} ET"
    title = f"Watchlist brief: {DAY}" if status == "final" else f"Intraday update: {as_of}"
    scan = {"session": {"status": "complete" if status == "final" else "in_progress", "as_of": as_of},
            "flagged": list(flagged), "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.3}], "errors": []}
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=DAY, status=status, title=title,
                                      body_md=brief(title, flagged), as_of=as_of, scan=scan)


def logged():
    with closing(alerts.connect()) as conn:
        return alerts.recent(conn, 100)


@pytest.fixture
def sent(tmp_path, monkeypatch):
    """A temporary database, a webhook in the environment, and fake sending. Returns what was 'sent'."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    messages = []
    monkeypatch.setattr(alerts, "send", lambda payload: messages.append(payload) or "1")
    return messages


def titles(message):
    return [e["title"] for e in message["embeds"]]


# ---------------------------------------------------------------------------
# Turning alerts on
# ---------------------------------------------------------------------------

def test_no_webhook_means_nothing_is_sent(sent, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL")
    save(ticker("NVDA"))

    assert alerts.notify(DAY) == {"enabled": False, "sent": [], "failed": []}
    assert sent == []


def test_webhook_must_be_a_discord_address(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/collect")

    assert not alerts.enabled()
    with pytest.raises(ValueError, match="Discord webhook"):
        alerts.webhook_url()


# ---------------------------------------------------------------------------
# Flag alerts while the market is open
# ---------------------------------------------------------------------------

def test_a_newly_flagged_ticker_alerts_once_per_day(sent):
    save(ticker("NVDA"), at="10:30")
    first = alerts.notify(DAY)
    save(ticker("NVDA", z=-3.3), at="10:45")              # still flagged, a little bigger
    second = alerts.notify(DAY)
    save(ticker("NVDA", z=-3.4), ticker("JPM", pct=3.1, z=2.8), at="11:00")
    third = alerts.notify(DAY)

    assert first["sent"] == ["flag alert: NVDA"] and second["sent"] == [] and third["sent"] == ["flag alert: JPM"]
    assert [titles(m) for m in sent] == [["NVDA -4.20% so far today"], ["JPM +3.10% so far today"]]
    assert sent[0]["content"] == "**1 new flag** in the intraday update as of 10:30 ET"


def test_a_much_bigger_move_alerts_again(sent):
    save(ticker("NVDA", pct=-4.2, z=-3.0), at="10:30")
    alerts.notify(DAY)
    save(ticker("NVDA", pct=-6.9, z=-4.6), at="12:30")    # |z| grew by 1.6
    alerts.notify(DAY)

    assert titles(sent[1]) == ["Bigger move: NVDA -6.90% so far today"]
    assert "Was -4.20% at 10:30 ET" in sent[1]["embeds"][0]["description"]
    assert sent[1]["content"] == "**1 bigger move** in the intraday update as of 12:30 ET"


def test_a_reversal_alerts_again(sent):
    save(ticker("NVDA", pct=4.0, z=3.0), at="10:30")
    alerts.notify(DAY)
    save(ticker("NVDA", pct=-3.5, z=-2.6), at="14:00")
    alerts.notify(DAY)

    assert titles(sent[1]) == ["Reversal: NVDA -3.50% so far today"]


def test_volume_only_flag_alerts_once(sent):
    save(ticker("JPM", pct=0.2, z=0.4, volume=3.0, read="in line"), at="10:30")
    alerts.notify(DAY)
    save(ticker("JPM", pct=0.3, z=0.6, volume=4.5, read="in line"), at="11:30")
    alerts.notify(DAY)

    assert len(sent) == 1


def test_flag_alert_shows_context_and_the_agents_explanation(sent):
    save(ticker("NVDA"))
    alerts.notify(DAY)
    embed = sent[0]["embeds"][0]

    assert "z-score -3.1 · volume 2.5x normal for this time of day" in embed["description"]
    assert "**Vs. sector and market:** NVDA fell; its sector (Technology, XLK) fell 1.00%." in embed["description"]
    assert ("**Likely why:** An analyst downgrade weighed on NVDA. [Reuters](https://example.com/NVDA)"
            in embed["description"])
    assert embed["color"] == alerts.COLORS["down"]
    assert embed["footer"]["text"] == "As of 2026-11-06 10:30 ET · research, not investment advice"


def test_many_flags_fit_in_one_message_within_discords_limits(sent):
    many = [ticker(f"T{i:02d}") for i in range(14)]
    for t in many:
        t["context"]["summary"] = "x" * 1500
    save(*many)
    alerts.notify(DAY)
    message = sent[0]

    assert len(sent) == 1 and len(message["embeds"]) == alerts.MAX_EMBEDS
    assert "showing 10" in message["content"]
    total = sum(len(e["title"]) + len(e["description"]) + len(e["footer"]["text"]) for e in message["embeds"])
    assert total <= alerts.MAX_TOTAL
    assert all(len(e["description"]) <= alerts.MAX_DESCRIPTION for e in message["embeds"])
    assert len(logged()) == 14  # every flagged ticker counts as alerted


# ---------------------------------------------------------------------------
# The end-of-day summary
# ---------------------------------------------------------------------------

def test_final_report_sends_one_summary(sent):
    save(ticker("NVDA"), status="final")
    first = alerts.notify(DAY)
    again = alerts.notify(DAY)

    assert first["sent"] == [f"daily summary for {DAY}"] and again["sent"] == []
    embed = sent[0]["embeds"][0]
    assert sent[0]["content"] == "**Daily summary:** 1 flagged move"
    assert embed["title"] == f"Watchlist brief: {DAY}"
    assert embed["description"].startswith("**Market:** The S&P 500 fell 0.50%")
    assert "**NVDA** -4.20% (z-score -3.1) · stock-specific\nAn analyst downgrade weighed on NVDA." in embed["description"]
    assert "**Quiet:** AAPL +0.30%" in embed["description"]


def test_quiet_day_summary(sent):
    save(status="final")
    alerts.notify(DAY)

    assert sent[0]["content"] == "**Daily summary:** 0 flagged moves"
    assert "Nothing unusual today." in sent[0]["embeds"][0]["description"]


def test_final_report_sends_no_flag_alerts(sent):
    save(ticker("NVDA"), ticker("JPM", pct=3.0, z=2.9), status="final")
    alerts.notify(DAY)

    assert len(sent) == 1 and sent[0]["content"].startswith("**Daily summary:**")


# ---------------------------------------------------------------------------
# Failures and retries
# ---------------------------------------------------------------------------

def test_a_failed_alert_is_logged_and_retried_next_run(sent, monkeypatch):
    def broken(payload):
        raise alerts.SendError("couldn't reach Discord (timed out)")

    save(ticker("NVDA"))
    monkeypatch.setattr(alerts, "send", broken)
    failed = alerts.notify(DAY)
    monkeypatch.setattr(alerts, "send", lambda payload: sent.append(payload))
    retried = alerts.notify(DAY)

    assert failed["failed"] == ["flag alert: NVDA (couldn't reach Discord (timed out))"]
    assert retried["sent"] == ["flag alert: NVDA"]
    statuses = [(a["status"], a["error"]) for a in logged()]
    assert statuses == [("sent", None), ("failed", "couldn't reach Discord (timed out)")]


def test_an_alert_being_sent_by_another_run_is_not_doubled(sent, monkeypatch):
    save(ticker("NVDA"))
    with closing(alerts.connect()) as conn:  # another run has claimed NVDA, and is sending right now
        conn.execute("""INSERT INTO alerts (session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status,
                        created_at) VALUES (?, 'flag', 'NVDA', -4.2, -3.1, ?, 'pending', ?)""",
                     (DAY, f"{DAY} 10:30 ET", alerts._stamp(alerts._utc_now())))
    assert alerts.notify(DAY)["sent"] == []

    # A claim left behind by a run that crashed counts as unsent after a while
    later = alerts._utc_now() + timedelta(seconds=alerts.PENDING_SECONDS + 1)
    monkeypatch.setattr(alerts, "_utc_now", lambda: later)
    assert alerts.notify(DAY)["sent"] == ["flag alert: NVDA"]


# ---------------------------------------------------------------------------
# Sending to Discord (the network is faked)
# ---------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(code, body):
    return urllib.error.HTTPError(WEBHOOK, code, "error", {}, io.BytesIO(json.dumps(body).encode()))


def test_post_sends_safe_json_to_the_webhook(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse(b'{"id": "998877"}')

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)

    assert alerts.post({"content": "hello @everyone"}) == "998877"
    request = requests[0]
    body = json.loads(request.data)
    assert request.full_url == WEBHOOK + "?wait=true"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent") == "market-agent-alerts/1.0"
    assert body == {"username": "Market Analyst", "allowed_mentions": {"parse": []}, "content": "hello @everyone"}


def test_post_waits_and_retries_once_when_rate_limited(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    replies = [http_error(429, {"message": "You are being rate limited.", "retry_after": 0.25}),
               FakeResponse(b'{"id": "1"}')]
    waits = []

    def fake_urlopen(request, timeout):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(alerts.time, "sleep", waits.append)

    assert alerts.post({"content": "x"}) == "1"
    assert waits == [0.25]


@pytest.mark.parametrize("error, expected", [
    (http_error(404, {"message": "Unknown Webhook"}), "doesn't exist"),
    (http_error(400, {"message": "Invalid Form Body"}), "refused the message (400)"),
    (urllib.error.URLError("timed out"), "couldn't reach Discord"),
])
def test_post_errors_are_clear_and_never_show_the_webhook(monkeypatch, error, expected):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)

    def fake_urlopen(request, timeout):
        raise error

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(alerts.SendError) as caught:
        alerts.post({"content": "x"})

    assert expected in str(caught.value)
    assert "secret-token" not in str(caught.value)


# ---------------------------------------------------------------------------
# Runs, the API and the command line
# ---------------------------------------------------------------------------

def fake_agent(monkeypatch, session, flagged):
    monkeypatch.setattr(run_brief, "market_session", lambda: session)
    scan = {"session": session, "flagged": flagged, "quiet": [], "errors": []}
    title = f"Intraday update: {session['as_of']}" if session["status"] == "in_progress" else f"Watchlist brief: {DAY}"

    async def query(*, prompt, options):
        yield AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})], model="m")
        yield UserMessage(content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": json.dumps(scan)}])])
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
                            session_id="s", total_cost_usd=0.01, result=brief(title, flagged))

    monkeypatch.setattr(run_brief, "query", query)


def test_a_run_sends_alerts_after_saving(sent, monkeypatch):
    fake_agent(monkeypatch, {"status": "in_progress", "as_of": f"{DAY} 10:30 ET"}, [ticker("NVDA")])
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "saved"
    assert {"type": "alert", "message": "Discord: sent flag alert: NVDA"} in events
    assert titles(sent[0]) == ["NVDA -4.20% so far today"]


def test_alert_problems_never_fail_a_run(sent, monkeypatch):
    fake_agent(monkeypatch, {"status": "in_progress", "as_of": f"{DAY} 10:30 ET"}, [ticker("NVDA")])

    def broken(payload):
        raise alerts.SendError("Discord refused the message (400): bad")

    monkeypatch.setattr(alerts, "send", broken)
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "saved"
    assert any(e["type"] == "warning" and "Discord alert failed" in e["message"] for e in events)


def test_a_skipped_run_retries_a_summary_that_failed(sent, monkeypatch):
    save(ticker("NVDA"), status="final")
    with closing(alerts.connect()) as conn:
        conn.execute("""INSERT INTO alerts (session_date, kind, status, error, created_at)
                        VALUES (?, 'summary', 'failed', 'timed out', '2026-11-06T21:31:00Z')""", (DAY,))
    fake_agent(monkeypatch, {"status": "complete", "as_of": DAY}, [ticker("NVDA")])
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "skipped"  # Claude isn't called again...
    assert {"type": "alert", "message": f"Discord: sent daily summary for {DAY}"} in events  # ...but the summary goes out


def test_api_shows_alert_status(sent):
    with TestClient(api.app) as client:
        empty = client.get("/api/alerts").json()   # before any alert has been sent
        save(ticker("NVDA"))
        alerts.notify(DAY)
        after = client.get("/api/alerts").json()

    assert empty == {"enabled": True, "alerts": []}
    assert after["alerts"][0]["ticker"] == "NVDA" and after["alerts"][0]["status"] == "sent"


def test_preview_shows_messages_without_sending(sent, monkeypatch, capsys):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL")  # works before alerts are set up
    save(ticker("NVDA"))
    monkeypatch.setattr(sys, "argv", ["alerts.py", "preview"])

    alerts.main()

    preview = json.loads(capsys.readouterr().out)
    assert titles(preview[0]) == ["NVDA -4.20% so far today"]
    assert sent == [] and logged() == []
```
