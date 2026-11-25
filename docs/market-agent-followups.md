# Market Analyst Agent: Follow-through and Story Updates

Every brief explains why a stock moved on the day. This guide adds what happened **afterwards**, in two separate tabs, so you can look at prices or news on their own:

| Tab | What it answers | Cost |
|---|---|---|
| **Follow-through (new)** | What did the price do 1, 5 and 20 trading days after each flagged move? Did the move **hold**, **fade** or **reverse**? And how did moves of each kind, reason and direction play out overall? | Free (Yahoo Finance prices) |
| **Story updates (new)** | What has the news said since? Each check reads the newer headlines and says whether the story **developed**, was **confirmed**, was **contradicted**, or had **no update** | A few cents a check (never more than $0.10). Free when there are no newer headlines |

Both run by themselves after each final report:

- **Follow-through** is filled in for every flagged move.
- **Surprises** get an automatic news check, once. A surprise is a move that reversed within a week, or kept going by as much again.
- **Any other move** can be checked with a button.

The **briefs** and **Ask** use it too:

- A brief's "Worth watching" line can say how the stock's earlier moves played out.
- Ask can answer "What happened after NVDA's drop?" from the follow-through and story updates.

It's history, never a forecast.

This builds on `market-agent-stocks.md`, and this guide's files include every earlier change.

---

## Contents

1. [What it looks like](#1-what-it-looks-like)
2. [How it works](#2-how-it-works)
3. [How a move is judged](#3-how-a-move-is-judged)
4. [Before you start](#4-before-you-start)
5. [Step 1: Add followups.py and stories.py](#5-step-1-add-followupspy-and-storiespy)
6. [Step 2: Connect them to the brief and to Ask](#6-step-2-connect-them-to-the-brief-and-to-ask)
7. [Step 3: Add the API endpoints](#7-step-3-add-the-api-endpoints)
8. [Step 4: Add the two tabs](#8-step-4-add-the-two-tabs)
9. [Step 5: Add the tests](#9-step-5-add-the-tests)
10. [Step 6: Try it](#10-step-6-try-it)
11. [Test it](#11-test-it)
12. [From the terminal](#12-from-the-terminal)
13. [Settings](#13-settings)
14. [Costs](#14-costs)
15. [Security](#15-security)
16. [Troubleshooting](#16-troubleshooting)
17. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it looks like

These examples are from the test environment, so the prices and headlines are simulated. Screenshots are in `followups-preview.png`.

**The Follow-through tab** (prices only):

```
HOW FLAGGED MOVES PLAYED OUT                              Prices updated Nov 9, 6:04 PM  [Refresh prices]
The price 1, 5 and 20 trading days after each move flagged in a final report, from Yahoo Finance.
Prices only: for what the news said since, see Story updates.

 [Next day]  [A week later]  [A month later]
 ■ Held gave back less than a quarter of the move   ■ Faded a quarter or more   ■ Reversed all of it, or more

All flagged moves
░░░░░░░░░░░░░░░░░░░░░░▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▓▓▓▓▓▓▓▓▓▓▓
12 held · 8 faded · 6 reversed · typically 1.06% back

BY KIND OF MOVE                 BY REASON                        BY DIRECTION
Stock-specific                  Earnings                         Up moves
5 held · 5 faded · 2 reversed   1 held · 4 faded · 0 reversed    7 held · 4 faded · 2 reversed
Sector-wide                     Other news                       Down moves
2 held · 1 faded · 0 reversed   7 held · 4 faded · 5 reversed    5 held · 4 faded · 4 reversed
  · too few to tell             No clear reason
…                               4 held · 0 faded · 1 reversed

History, not a forecast. Groups with fewer than 5 judged moves are marked "too few to tell".

FLAGGED MOVES                                                          Stock [All ▾]  ☐ Only surprises
Day     Ticker  Move     Kind            Reason           Next day  1 week   1 month  A week later
Nov 4   AMZN    +9.14%   Stock-specific  Earnings         -1.22%    …        …        not yet               Check news
Oct 29  AMZN    +4.78%   Sector-wide     Other news       +0.74%    +8.65%   …        held · surprise       No newer news
Oct 26  NVDA   -10.21%   Stock-specific  Other news       +5.40%    +9.23%   …        faded                 Check news
Oct 20  AAPL    -4.34%   Mixed           No clear reason  +2.03%    +7.51%   …        reversed · surprise   Story: no update
Oct 15  AMZN    -5.58%   Stock-specific  Other news       +1.11%    +9.70%   …        reversed · surprise   Story: developed
```

- **The buttons** at the top switch every bar and the last column between the next day, a week and a month.
- **Hover a bar** to see its counts as percentages ("Held: 12 of 26 (46%)").
- **"Typically 1.06% back"** is the middle price change since the move (the median): back toward where it started, or further in the move's direction.
- In the table:
  - a **day** opens that day's report
  - a **ticker** opens its chart
  - the last link opens the move on the Story updates tab

**The Story updates tab** (news only):

```
STORY UPDATES
What the news has said since a flagged move. Moves that turn out to be surprises are checked automatically
after the next final report. Any other move can be checked here: each check costs a few cents (at most $0.10),
and nothing if there are no newer headlines. For prices only, see Follow-through.

┌─ NVDA's move of Monday, October 26, 2026 ─────────────────────────────────────────────────────────┐
│ At the time: A senior executive departure was announced. Example Financial News                    │
│ Price since: +5.40% next day, +9.23% a week (faded after a week)                                   │
│ [Check for updates]                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────────────────────────┘
LATEST UPDATES
AMZN  move of Oct 15 · -5.58% · Other news                                                 [Developed]
At the time: An analyst downgrade weighed on the shares. Sample Wire
On 2026-10-17, Example Financial News reported: Amazon responds to last week's concerns.
  • AMZN: Amazon responds to last week's concerns   Example Financial News
Price since: +1.11% next day, +9.70% a week (reversed after a week) · Checked Nov 9, 6:04 PM ·
automatically: a surprise (reversed within a week)

MOVES YOU CAN CHECK                                         Flagged in the last 30 days, not checked yet
NVDA  move of Oct 26 · -10.21% · Other news                                       [Check for updates]
```

The card at the top appears when you arrive from a move's **Check news** link. While a check runs, the button shows its progress ("Reading NVIDIA's newest headlines", "Reading 3 newer headlines with Claude").

**In a brief,** a flagged stock's "Worth watching" line can end with how its earlier moves played out. This happens only when there are at least 5 earlier moves to go on:

```
- **Worth watching:** … Past moves: MSFT's flagged moves: 4 of 6 held a week later, 1 faded, 1 reversed;
  Stock-specific moves across the watchlist: 5 of 12 held a week later, 5 faded, 2 reversed.
```

**In Ask,** for example "What happened after AMZN's last flagged move?". Claude cites the new material as `(follow-through)` and `(story update, date checked)`:

```
After its move of 2026-10-29 (+4.78%), AMZN was 8.65% higher a week later, so the move held (follow-through).
No newer headlines about Amazon had appeared when it was last checked (story update, 2026-11-09).
```

---

## 2. How it works

```
A final report is saved (run_brief.py, after its alerts)
  └─▶ stories.after_final_report()
        1. followups.update()                                                        free
             each move flagged in a final report gets a row in the followups table
             Yahoo closes ─▶ after_1d, after_5d, after_20d (% from the move day's close)
             new surprises are noted
        2. stories.check_surprises()                              a few cents each, at most 5
             each new surprise from the last 30 days, once:
             Yahoo's newest headlines ─▶ keep those published after the move
                                         ├─ none: "No newer news" (no Claude call, $0)
                                         └─ some: Claude reads them ─▶ verdict, update, sources
                                                                        ─▶ story_checks table

Follow-through tab ── GET /api/followups ──── [Refresh prices]   ─▶ POST /api/followups/refresh
Story updates tab ─── GET /api/stories ────── [Check for updates] ─▶ POST /api/stories/check
The agent ─────────── past_moves tool ─────── "Worth watching" line
Ask ───────────────── follow-through and story updates for the stocks you name
```

- **Final reports only.** A move is followed up from its final report, using that day's close. Intraday flags can still change during the day, and today's unfinished price is never used.
- **Trading days.** "A week later" means 5 trading days after the move day's close, and "a month later" 20 trading days. Weekends and holidays don't count.
- **Settled moves aren't downloaded again.** Once a move has its 20-day figure, it's finished. Each update only downloads the stocks that still have moves to fill in.
- **Your reports are never changed.** Follow-ups live in three new tables in `reports.db`:
  - `followups`: one row per flagged move
  - `followup_updates`: one row per update
  - `story_checks`: one row per check

  Like your reports, you can read them yourself (section 12).
- **Your existing history counts.** The first update follows up every flagged move in your past final reports, at no cost, so the patterns start with what you already have.
- **Automatic checks are for recent surprises only.** Only moves from the last 30 days are checked automatically. That way the first run after adding this doesn't spend money checking months-old moves against today's headlines. Older moves can still be checked with the button.
- **Each surprise is checked automatically once.** A later check, by you, adds a newer update. Every check is kept.
- **A check never explains the move itself.** Claude only reports what the newer headlines say about the original story, and must cite them. A reply without a known verdict or a cited headline is saved as a failed check, with the reason.
- **Problems never spoil the run.** If Yahoo or Claude fails after a final report, the report and alerts are already saved. The run log ends with a warning, and the next final report catches up. A Yahoo problem with one stock doesn't stop the others (the update says `partial`).
- **Live.** When a scheduled run or the terminal adds follow-ups or checks, open pages update within a few seconds, as they do for new reports.

---

## 3. How a move is judged

**Gave back** means how much of the move's price change has been undone since.

Say a stock closes at $100, then jumps 10% to $110. A week later:

| Price a week later | Gave back | Judged |
|---|---|---|
| $115 | none: it kept going | **held** |
| $108 | $2 of the $10 move (20%) | **held** (less than a quarter) |
| $104 | $6 of $10 (60%) | **faded** (a quarter or more) |
| $99 | $11 of $10 (110%) | **reversed** (all of it, or more) |
| $120 or more | as much again | **held**, and a **surprise** |

The same applies to drops, the other way round.

**In the code** (`followups.give_back`), the follow-up figure is measured from the move day's close ($110), not the day before ($100), so the formula scales it back to the move:

```
gave back = −after × (1 + move) ÷ move          (as fractions: a 10% move is 0.10)
$104: after = −5.45%  →  0.0545 × 1.10 ÷ 0.10 = 0.60  →  faded
```

It's rounded to 2 decimal places, so a move given back exactly in full counts as reversed.

**A surprise** is judged a week later: the move **reversed** (gave back all of it or more), or **kept going by as much again**. These are the moves where the original story most likely missed something, so they get the automatic news check.

**Reason**, from the final report:

| Reason | When |
|---|---|
| Earnings | The calendar has the company's earnings on the move day or up to 3 days before, or the brief's "Likely why" line mentions earnings, results, quarterly figures, guidance, revenue, profit or EPS |
| Other news | The brief gave a reason that isn't earnings |
| No clear reason | The brief said "No clear catalyst" (and there was no earnings date) |

**Kind** is the sector verdict from the report: stock-specific, sector-wide, market-wide, mixed or in line.

**"Too few to tell":** groups with fewer than 5 judged moves still show, but are marked, and the brief doesn't mention them.

---

## 4. Before you start

- [ ] You've done `market-agent-stocks.md`, and `pytest` shows `241 passed, 3 skipped`.
- [ ] `ANTHROPIC_API_KEY` is set where your scheduled runs and the API run. It already is, for briefs and Ask; story checks use it too.

No new packages are needed: prices come from yfinance and checks use the Claude Agent SDK, as before.

If you use the test environment or the live demo, update them afterwards (section 10).

---

## 5. Step 1: Add followups.py and stories.py

1. Add `followups.py` from the [appendix](#followupspy). It works out the follow-through:

   | Function | What it does |
   |---|---|
   | `update(trigger)` | Adds new flagged moves from final reports and fills in their prices. Returns the counts and new surprises |
   | `outcome(move, after)` | `held`, `faded`, `reversed`, or `None` if not known yet |
   | `is_surprise(move, after_5d)` | Reversed, or kept going by as much again, within a week |
   | `moves(conn, ticker)` | The moves, newest first, with their outcomes and latest story update |
   | `patterns(moves, horizon)` | The counts for all moves, by kind, by reason and by direction |
   | `past_for(conn, ticker, kind)` | What the brief's `past_moves` tool returns for one stock |

2. Add `stories.py` from the [appendix](#storiespy). It does the news checks:

   | Function | What it does |
   |---|---|
   | `check(session_date, ticker)` | Checks one move's story now and saves the result |
   | `check_surprises()` | The automatic checks: recent surprises not checked yet, at most 5 |
   | `after_final_report(emit)` | Both steps, run after each final report. Never raises |
   | `latest(conn)` / `unchecked(conn, since)` | The newest checks; moves not checked yet |

   Problems the API should show as they are (such as "NVDA wasn't flagged in the final report of 2026-10-27.") raise `StoryError`.

**Try it** (free, needs internet):

```bash
python followups.py update
python followups.py patterns
```

The first prints a line per stock ("Following up on NVDA's flagged moves"), then something like `ok: 31 new moves, 31 updated, 4 new surprises`. The second prints the patterns. Your numbers depend on your history; with only a few reports, most groups say "too few to tell".

---

## 6. Step 2: Connect them to the brief and to Ask

Replace these files with the appendix versions:

| File | Change |
|---|---|
| `market_tools.py` | A sixth tool, `past_moves(tickers, kinds)`: for each flagged stock, how its earlier moves and moves of the same kind played out a week later, a one-line `summary`, and `worth_mentioning` (only with 5 or more judged moves) |
| `analyst_prompt.md` | The agent calls `past_moves` once when anything is flagged. It may add the summary to "Worth watching" as background, never as a forecast, and may mention the latest story update in one clause |
| `run_brief.py` | Allows the new tool. After a **final** report is saved and its alerts sent, it calls `stories.after_final_report`, and the run log shows "Follow-through: 3 new moves, 12 updated" and, if any, "Story updates: checked 1 surprise · $0.021". Intraday runs don't do this |
| `ask.py` | Questions naming a stock get its follow-through (the last 10 moves) and its latest 3 story updates. Other questions get the overall patterns. Claude cites them as `(follow-through)` and `(story update, date)` |

**The run log after a final report** (the run panel, or the terminal):

```
Saved (final) · $0.384
Discord: sent daily summary for 2026-11-06
Follow-through: 1 new move, 8 updated, 1 new surprise
Checking the news on AAPL's move of 2026-10-30 (a surprise)
Reading Apple's newest headlines
Reading 4 newer headlines with Claude
Story updates: checked 1 surprise · $0.018
```

---

## 7. Step 3: Add the API endpoints

Replace `api.py` with the appendix version. It adds:

| Endpoint | What it does |
|---|---|
| `GET /api/followups?horizon=5` | The flagged moves, newest first, and the patterns at that horizon (`1`, `5` or `20`), plus the stocks, the last update and whether a refresh is running. `&ticker=NVDA` lists one stock's moves; the patterns still cover all of them |
| `POST /api/followups/refresh` with `{}` | Fills in prices now (`202`), in the background |
| `GET /api/stories` | The latest checks (each with its move), the moves of the last 30 days not checked yet, whether a check is running, and the most a check can cost |
| `POST /api/stories/check` with `{"session_date": "2026-10-26", "ticker": "NVDA"}` | Checks that move's story now (`202`), in the background |

**What a move looks like in `GET /api/followups`:**

```json
{"session_date": "2026-10-29", "ticker": "AMZN", "move_pct": 4.78, "kind": "Sector-wide",
 "reason": "news", "reason_label": "Other news", "why": "A sector-wide rally in consumer discretionary stocks. …",
 "after_1d": 0.74, "after_5d": 8.65, "after_20d": null,
 "outcomes": {"1": "held", "5": "held", "20": null}, "follow": {"1": 0.74, "5": 8.65, "20": null},
 "surprise": true, "surprise_kind": "kept going: as much again within a week", "settled": false,
 "story": {"verdict": "no_update", "status": "no_news", "checked_at": "2026-11-09T23:10:41Z",
           "update": "No newer headlines about Amazon.com since 2026-10-29."}}
```

`follow` is the change in the move's direction (negative means back toward where it started). `settled` is true once the 20-day figure is in.

**When something can't be done,** the reply has an `error` message to show:

| Status | When |
|---|---|
| `400` | A horizon other than 1, 5 or 20, or a check request that isn't `{"session_date": "YYYY-MM-DD", "ticker": "…"}` |
| `404` | That stock wasn't flagged in that day's final report |
| `409` | A refresh or a check is already running ("A story is already being checked. Its progress is shown on the Story updates tab.") |
| `429` | Too soon after the last one: 60 seconds for refreshes, 30 for checks ("A story was just checked. Try again in 20 seconds.") |
| `403` / `415` | The request came from another website, or isn't JSON (section 15) |

**Live updates.** Open pages hear about refreshes and checks as they run (`followups_refresh` and `story_check` events, with progress). The background watcher also notices follow-ups and checks saved by other programs, such as a scheduled run, and sends `followups_updated` and `story_checked`.

**Try it** with the API running (`uvicorn api:app --port 8000`):

```bash
curl "http://127.0.0.1:8000/api/followups?horizon=5"
curl http://127.0.0.1:8000/api/stories
```

---

## 8. Step 4: Add the two tabs

Replace or add these files in `frontend/src/`:

| File | Change |
|---|---|
| `components/FollowThroughTab.jsx` | **New:** the patterns (a bar per group), the horizon buttons, **Refresh prices**, and the flagged moves table with its filters |
| `components/StoriesTab.jsx` | **New:** the picked move, the latest updates, and the moves you can check |
| `App.jsx` | The two tabs, and their live updates |
| `useRoute.js` | The `#/follow-through`, `#/stories` and `#/stories/2026-10-26/NVDA` addresses |
| `api.js` | `getFollowups`, `refreshFollowups`, `getStories`, `checkStory` |
| `components/RunPanel.jsx` | Names the agent's new step: "Checking how past moves played out" |
| `styles.css` | The bars, legend, tooltips and story cards. The tabs now wrap onto a second line on a phone instead of making the page scroll sideways |

**The colours** are one blue, from light (held) to dark (reversed), with their own shades for dark mode. They were checked for colour-blind readers. The counts are always written under each bar, so colour is never the only way to read it.

Then rebuild if you serve the built app (`cd frontend && npm run build`).

---

## 9. Step 5: Add the tests

1. Replace `tests/conftest.py` with the appendix version. Other tests save final reports too; this stops those from following up (which would download prices). Only `test_followups.py` does it, with fake Yahoo and Claude.
2. Add `tests/test_followups.py` from the [appendix](#teststest_followupspy).
3. Replace `tests/test_market_tools.py` with the version in `market-agent-testing.md`'s appendix. Its MCP check now expects six tools, including `past_moves`.
4. Run:

```bash
pytest -v
```

**Expected result:** `276 passed, 3 skipped`. The new file alone (`pytest -v tests/test_followups.py`) gives `35 passed`. They use a temporary database, fake prices, fake headlines and a fake Claude, so they're free and need no internet.

---

## 10. Step 6: Try it

Start the app as usual (frontend guide, section 6), then:

1. **Fill in your history:** `python followups.py update`, or **Refresh prices** on the Follow-through tab. It's free.
2. **The Follow-through tab:** the patterns and the moves table. Switch between **Next day**, **A week later** and **A month later**. Tick **Only surprises**.
3. **Check a story:** on a recent move, click **Check news**. The Story updates tab opens on that move; click **Check for updates**. It costs a few cents, or nothing if there are no newer headlines. The move's row on Follow-through now links to its update.
4. **After the next final report** (the scheduled run after the close, or `python run_brief.py` after 4pm), the run log shows the follow-through line. If a move became a surprise, its automatic check is shown too.
5. **The next brief** may mention past moves in "Worth watching", once a stock or its kind of move has 5 judged moves.
6. **Ask** "What happened after [a ticker]'s last flagged move?"

**To try it all for free first,** update the test environment (`market-agent-test-enviro.md`):

- Replace its three files, then run `python testenv.py seed --reset` and `python testenv.py build-frontend`.
- Its sample has two months of follow-through and story updates.
- **Refresh prices** and **Check for updates** work offline, at $0.

To show the new tabs in your live demo, build and publish it again (`market-agent-demo.md`, section 11).

---

## 11. Test it

### 11.1 Automated tests

*In `tests/test_followups.py`*

| Test | Proves that |
|---|---|
| `test_judging_a_move` (7 cases) | Kept going and a small give-back are held, 55% is faded, back past the start is reversed (up and down), and an unknown price is "not yet" |
| `test_surprises_are_reversals_or_doubling_within_a_week` | Both kinds of surprise are recognised and named; a fade isn't one |
| `test_follow_ups_come_from_final_reports_only` | Flagged moves in final reports are followed up; today's intraday flags aren't. The reason and the "Likely why" line (without its links) are kept |
| `test_earnings_on_the_calendar_count_as_the_reason` | Earnings the evening before the move make the reason "Earnings", even when the brief found no clear catalyst |
| `test_prices_fill_in_as_days_pass` | The next-day figure first, then the week and month as they come, matching hand-worked figures. Settled moves aren't downloaded again |
| `test_todays_unfinished_price_is_never_used` | While the market is open, the latest close used is yesterday's |
| `test_a_price_problem_for_one_stock_doesnt_stop_the_rest` | One stock failing gives `partial`, naming it, and the others are still filled in |
| `test_patterns_group_the_moves` | The counts by kind and direction, and "too few to tell" under 5 moves |
| `test_past_moves_tool_for_the_brief` | The agent's tool gives the stock's and the kind's history, the last move, a summary, and doesn't suggest mentioning too few moves |
| `test_past_moves_without_any_history` | With nothing worked out yet, the tool says so |
| `test_no_newer_headlines_means_no_claude_and_no_cost` | Only same-day headlines: "No newer headlines about NVIDIA since 2026-10-01.", $0, and Claude isn't asked |
| `test_a_check_reads_only_newer_headlines` | Claude gets the original explanation and sources, the price since, and only headlines published after the move day. The cited source is saved with its link |
| `test_a_bad_reply_is_saved_as_a_failed_check` (4 cases) | A reply that isn't JSON, has an unknown verdict, cites no given headline, or hits the cost cap is saved as a failed check with the reason |
| `test_only_flagged_moves_can_be_checked` | A move that wasn't flagged in a final report is refused (`404`) |
| `test_surprises_are_checked_once_after_a_final_report` | After a final report, the new surprise is checked automatically, once, and the run log gets both lines |
| `test_older_surprises_are_left_to_check_by_hand` | A surprise from more than 30 days ago isn't checked automatically (no Claude call), but can be checked on request |
| `test_after_final_report_never_breaks_the_run` | A failure is reported as a warning, never raised |
| `test_a_final_run_follows_up_and_an_intraday_run_doesnt` | `run_brief.py` follows up after a final report only |
| `test_ask_sees_follow_through_and_story_updates` | Ask's material has the stock's follow-through table and story updates, and the overall patterns for general questions. Claude is told how to cite them |
| `test_api_refresh_and_follow_through` | Refresh runs in the background, then the cooldown applies; each horizon, the stock filter, and a bad horizon (`400`) |
| `test_api_story_check` | A check through the API: progress events, the saved update, the move leaving "Moves you can check", the move's row linking to it, and the cooldown |
| `test_api_story_check_explains_what_went_wrong` (3 cases) | A move that wasn't flagged (`404`), a bad date and a missing date (`400`) |
| `test_other_websites_cannot_start_checks` | Refresh and check requests from another website are refused (`403`), and Claude isn't asked |
| `test_updates_from_scheduled_runs_reach_open_pages` | Follow-ups and checks saved by another program reach open pages |

**Check the tests catch real bugs.** Make one of these temporary changes, run `pytest tests/test_followups.py`, then change it back. Each was tried:

| Temporary change | Test that fails |
|---|---|
| `followups.py`: in `outcome`, `g >= 1` → `g > 1` | `test_judging_a_move` (the reversed cases) |
| `followups.py`: in `is_surprise`, `return g >= 1 or g <= -1` → `return g >= 1` | `test_surprises_are_reversals_or_doubling_within_a_week` |
| `followups.py`: in `_add_new`, delete `r.status = 'final' AND ` | `test_follow_ups_come_from_final_reports_only` |
| `followups.py`: in `_add_new`, `range(0, 4)` → `range(0, 1)` | `test_earnings_on_the_calendar_count_as_the_reason` |
| `followups.py`: in `update`, delete `if date.fromisoformat(d) <= last` | `test_prices_fill_in_as_days_pass` |
| `stories.py`: in `check`, `d.isoformat() > session_date` → `True` | `test_no_newer_headlines_means_no_claude_and_no_cost` |
| `stories.py`: in `check`, `if not later:` → `if False:` | `test_no_newer_headlines_means_no_claude_and_no_cost` |
| `stories.py`: in `check_surprises`, `f.session_date >= ?` → `? IS NOT NULL` (any age) | `test_older_surprises_are_left_to_check_by_hand` |
| `stories.py`: in `check_surprises`, `AND c.trigger = 'surprise'` → `AND 0` (earlier checks never found) | `test_surprises_are_checked_once_after_a_final_report` |
| `run_brief.py`: `if status == "final":  # once a day` → `if True:` | `test_a_final_run_follows_up_and_an_intraday_run_doesnt` |
| `api.py`: in `check_story`, delete the two `_post_guard` lines | `test_other_websites_cannot_start_checks` |
| `ask.py`: in `build_context`, `followed = followup_section(conn, tickers)` → `followed = ''` | `test_ask_sees_follow_through_and_story_updates` |

### 11.2 What was also tested

- **From the guides alone:** all three folders were rebuilt from the guides (this one included), and every test passed: 276 passed and 3 skipped in `market-agent/`, 33 in `market-agent-testenv/`, and 17 in `market-agent-demo/`.
- **In a real browser, against the test environment.** The 13 checks passed with no browser errors:
  1. Follow-through shows the patterns by kind, reason and direction and all 27 moves. The buttons switch between day, week and month.
  2. Hovering a bar segment shows its count ("Held: 12 of 26 (46%)").
  3. The table filters by stock and to surprises only.
  4. A ticker opens its chart.
  5. **Refresh prices** runs; pressing it again straight away explains the wait.
  6. **Check news** opens the move on Story updates; **Check for updates** gives its update.
  7. The new update leads the list; automatic checks are labelled; the move leaves "Moves you can check".
  8. The move's row on Follow-through now links to its update.
  9. **Run update now** shows "Checking how past moves played out", and the brief mentions past moves.
  10. Ask answers with how AMZN's last move played out, and its latest story update.
  11. A final report saved by another program adds its move without a reload.
  12. On a phone, both tabs fit with no sideways scrolling.
  13. Dark mode renders both tabs.

  The earlier Today, Previous days, chart, search, sector and alerts, calendar, Coming up and Stocks checks all still pass, and so do the live demo's 15 checks, which now include both tabs.
- **Found and fixed while testing:**
  - A move given back exactly in full (110 → 99.99…) counted as faded, from a rounding error. "Gave back" is now rounded to 2 places.
  - The Story updates tab failed to list moves before the first check ever ran (its table didn't exist yet).
  - With six tabs, the page scrolled sideways on a phone. The tabs now wrap.
  - Links in the new tabs were hard to read in dark mode.
  - The picked move's card repeated its own details under the update.
  - The first final report after adding this would have checked old surprises automatically, at a few cents each, against headlines that are no longer about them. Automatic checks are now for the last 30 days only.
  - `python stories.py check` printed a traceback for a move that wasn't flagged, instead of the message.

**Not tested here:** real Yahoo prices and headlines, and real Claude checks, because they couldn't be reached from where this guide was built. Run the checks below once.

### 11.3 Checks with real data

**Prices** (free):

- [ ] `python followups.py update` ends with `ok` (or `partial`, naming any stock Yahoo didn't answer for)
- [ ] For one move, compare with Yahoo Finance's historical prices: `after_5d` is the close 5 trading days after the move day, divided by the move day's close, minus 1. `python followups.py list --ticker NVDA` shows the figures
- [ ] During market hours, a move from yesterday has no next-day figure yet. After the close, an update fills it in

**A story check** (a few cents):

- [ ] `python stories.py check NVDA 2026-10-26`, using one of your recent flagged moves. It prints the steps, then the verdict, the update and the cost, then the sources with links
- [ ] Open the sources. Each was published after the move and says what the update says
- [ ] The cost is a few cents, and never more than $0.10
- [ ] The update reports news. It doesn't explain the price or predict anything

**Everything together:**

- [ ] After the next final report, the run log has the follow-through line, and the Follow-through tab shows that day's moves
- [ ] Within a week of a surprise, the Story updates tab has its automatic check, labelled "automatically: a surprise"
- [ ] Once a stock has 5 judged moves, its next flagged brief may say "Past moves: …" in "Worth watching"
- [ ] Ask "What happened after [ticker]'s last flagged move?": the answer cites (follow-through), and (story update, date) if it has one

---

## 12. From the terminal

```bash
python followups.py update                    # fill in follow-ups now (free)
python followups.py list                      # the latest moves and how they played out
python followups.py list --ticker NVDA        # one stock's
python followups.py patterns                  # how moves of each kind played out a week later
python followups.py patterns --days 20        # … a month later (1, 5 or 20)
python stories.py check NVDA 2026-10-26       # check one move's story now (a few cents)
python stories.py list                        # the latest story updates
```

**`list` and `patterns`** (from the test environment):

```
2026-10-26  NVDA    -10.21%  1d +5.40%  5d +9.23%  20d   …     faded     Other news
2026-10-12  NVDA     +8.13%  1d +2.37%  5d +10.53%  20d   …     held      No clear reason  SURPRISE
2026-09-15  NVDA    -13.81%  1d +0.00%  5d +4.43%  20d +14.14%  faded     Earnings
2026-09-09  NVDA     +5.76%  1d +3.76%  5d -10.46%  20d -9.69%  reversed  Other news  SURPRISE

All flagged moves: 12 of 26 held a week later, 8 faded, 6 reversed
Stock-specific: 5 of 12 held a week later, 5 faded, 2 reversed
Sector-wide: 2 of 3 held a week later, 1 faded, 0 reversed (too few to tell)
…
```

**Reading the tables yourself.** Like your reports, follow-ups are in `reports.db`, so any SQLite tool can read them (for example DB Browser for SQLite, or the `sqlite3` command):

```bash
sqlite3 reports.db "SELECT session_date, ticker, move_pct, after_1d, after_5d, after_20d, surprise FROM followups ORDER BY session_date DESC LIMIT 10"
sqlite3 reports.db "SELECT finished_at, ticker, session_date, verdict, update_text, cost_usd FROM story_checks ORDER BY id DESC LIMIT 10"
```

Read them, but don't edit them by hand. If you delete the `followups` table, the next update rebuilds it from your final reports. Story checks can't be rebuilt without checking again.

---

## 13. Settings

| Where | Setting | Default | What it does |
|---|---|---|---|
| `followups.py` | `HELD_UP_TO` | `0.25` | Giving back up to this share of the move still counts as held |
| `followups.py` | `MIN_FOR_PATTERN` | `5` | Fewer judged moves than this: "too few to tell", and not mentioned in briefs |
| `followups.py` | `EARNINGS_WORDS` | earnings, results, quarterly, guidance, revenue, profit, EPS | Words in "Likely why" that make the reason "Earnings" |
| `stories.py` | `MAX_AUTOMATIC` | `5` | Most automatic checks after one final report. `0` turns automatic checks off |
| `stories.py` | `AUTOMATIC_WITHIN_DAYS` | `30` | Only surprises this recent are checked automatically |
| `stories.py` | `CHECK_BUDGET_USD` | `0.10` | The most one check can cost |
| `stories.py` | `NEWS_PER_CHECK` | `10` | Newest headlines read per check |
| `api.py` | `FOLLOWUP_REFRESH_COOLDOWN_SECONDS` (environment) | `60` | Wait between **Refresh prices** presses |
| `api.py` | `STORY_CHECK_COOLDOWN_SECONDS` (environment) | `30` | Wait between story checks from the app |
| `api.py` | `STORY_DAYS` | `30` | How far back "Moves you can check" goes (older moves can be checked from Follow-through) |
| `ask.py` | `FOLLOWUP_MOVES`, `STORY_UPDATES` | `10`, `3` | How much of a stock's history Ask is given |

The horizons themselves (1, 5 and 20 days), and judging surprises after a week, are built into the tables and wording, so they're fixed.

---

## 14. Costs

- **Follow-through:** free. The prices come from Yahoo Finance: one download per stock that still has moves to fill in, after each final report and when you press **Refresh prices**.
- **Story checks:** one Claude request each, capped at $0.10, usually a few cents. A check with no newer headlines makes no request and costs nothing.
- **Automatic checks:** only surprises, only recent ones, and at most 5 per final report, so at most $0.50 a day. On most days there are none, or one.
- **Checks you start:** one at a time, at least 30 seconds apart.
- **Briefs:** when something is flagged, the agent makes one more tool call (`past_moves`) and reads a short result. This adds a little to each run, well under a cent. `max_budget_usd` still caps each run.
- **Ask:** a few more lines of material per question.

`python stories.py list` and the Story updates tab show each check's cost.

---

## 15. Security

- **Other websites can't start refreshes or checks.** **Refresh prices** and **Check for updates** use the same protection as Run now: requests from another website are refused (`403`), and only JSON is accepted.
- **Nothing runs up a bill.** Checks run one at a time with a cooldown, each has a hard cost cap, and the date and ticker must match a move flagged in a final report before anything is spent.
- **What Claude sees:** the move, the brief's explanation and its source headlines, the price since, and Yahoo's newer headlines. All of this is public news or your own report. No keys or other data are sent.
- **Headlines can't steer it.** A check has no tools and one turn, so text in a headline can't make Claude do anything. Its reply must be JSON with a known verdict, citing headlines by number. Anything else is saved as a failed check.
- **Links are Yahoo's, not Claude's.** Source links come from Yahoo's headlines, and the app only opens `http` and `https` links.
- **Who can use it:** anyone who can reach your API, the same as Run now. The API listens on your own computer only (`127.0.0.1`), as set up in the frontend guide.

---

## 16. Troubleshooting

| Problem | Cause and fix |
|---|---|
| Follow-through says nothing has been worked out yet | Press **Refresh prices** or run `python followups.py update`. If it still shows nothing, no final report has flagged anything yet. |
| "…" instead of a figure | Not enough trading days have passed. During market hours, today's price isn't used until the close. |
| `partial: NVDA: …` | Yahoo didn't answer for that stock (rate limiting or a network problem). The others were saved; the next update retries it. |
| A move has no prices, and its note says "no Yahoo price for that day" | Yahoo has no close for that day, usually because the ticker was renamed or delisted. |
| A group says "too few to tell" | Fewer than 5 judged moves. It fills in as more final reports come. |
| An old surprise wasn't checked automatically | By design: only the last 30 days (`AUTOMATIC_WITHIN_DAYS`). Click its **Check news** link on Follow-through, then **Check for updates**. |
| An older move isn't under "Moves you can check" | That list covers the last 30 days. Open the move from its row on Follow-through instead. |
| "No newer news" for a move you know had news | Yahoo had no headlines about the company dated after the move day among its newest 10. Try again in a few days, or raise `NEWS_PER_CHECK`. |
| A check says "Check failed" | The reason is shown: a reply without JSON or a cited headline (rare; check again), `error_max_budget_usd` (raise `CHECK_BUDGET_USD` a little), or Claude couldn't be reached (check `ANTHROPIC_API_KEY` where the API runs). |
| "A story is already being checked" / "Prices are already being refreshed" | One at a time. Its progress shows on the tab; try again when it finishes. |
| "A story was just checked. Try again in 20 seconds." | The cooldown (`STORY_CHECK_COOLDOWN_SECONDS`). |
| The run log ends "Saved, but follow-through: …" | The report and alerts were saved. Yahoo or the database had a problem afterwards; the next final report catches up, or run `python followups.py update`. |
| Briefs never mention past moves | They only do with 5 or more judged moves for that stock or kind, and the agent decides whether it's useful. Check with `python followups.py patterns`. |
| `ModuleNotFoundError: No module named 'followups'` (or `stories`) | Add both files from the appendix, in the `market-agent` folder. |
| Only `test_tools_work_through_mcp` fails | `tests/test_market_tools.py` is from before this guide. Replace it from the testing guide's appendix (step 5). |
| Many unrelated tests suddenly try to reach Yahoo | `tests/conftest.py` is from before this guide. Replace it (step 5). |

---

## Appendix: full source code

### followups.py

```python
"""Follow-through: what the price did after each flagged move, 1, 5 and 20 trading days later.

Every move flagged in a final report gets a follow-up. The prices come from Yahoo Finance
(free), so keeping follow-ups current costs nothing. They're filled in after each final
report is saved, and by "Refresh prices" on the Follow-through tab.

Each move is judged at each horizon by how much of it the price gave back:
- held:     gave back less than a quarter of the move (or kept going)
- faded:    gave back between a quarter and all of it
- reversed: gave back all of it or more (the price is back past where it started)

A move is a surprise if, a week (5 trading days) later, it had reversed, or kept going by as
much again. Surprises get an automatic news check (see stories.py).

From the terminal:
    python followups.py update        fill in follow-ups now
    python followups.py list          the latest moves and how they played out
    python followups.py patterns      how moves of each kind played out
"""

import argparse
import re
import statistics
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

import market_tools
import prices
import reports_db
from events import transaction

HORIZONS = (1, 5, 20)            # trading days after the move
SURPRISE_HORIZON = 5             # when a move is judged a surprise (and its news re-checked)
HELD_UP_TO = 0.25                # giving back up to this much of the move still counts as held
MIN_FOR_PATTERN = 5              # fewer settled moves than this: "too few to tell"
PERIODS = ((28, "1mo"), (88, "3mo"), (178, "6mo"), (360, "1y"), (725, "2y"), (1820, "5y"))  # Yahoo history to ask for
EARNINGS_WORDS = re.compile(r"\b(earnings|quarterly|results|guidance|revenue|profit|eps)\b", re.I)
MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]*\)")

KIND_LABELS = {"stock-specific": "Stock-specific", "sector-wide": "Sector-wide", "market-wide": "Market-wide",
               "mixed": "Mixed", "in line": "In line with its sector", None: "Not compared"}
REASON_LABELS = {"earnings": "Earnings", "news": "Other news", "none": "No clear reason"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS followups (
    session_date TEXT NOT NULL,         -- the day of the flagged move (from its final report)
    ticker       TEXT NOT NULL,
    move_pct     REAL NOT NULL,         -- that day's move
    move_read    TEXT,                  -- stock-specific, sector-wide, market-wide, mixed or in line
    reason       TEXT NOT NULL CHECK (reason IN ('earnings', 'news', 'none')),
    why          TEXT,                  -- the brief's "Likely why" line
    after_1d     REAL,                  -- % change from that day's close to the close N trading days later
    after_5d     REAL,
    after_20d    REAL,
    surprise     INTEGER NOT NULL DEFAULT 0,
    note         TEXT,                  -- why prices are missing, if they are
    updated_at   TEXT NOT NULL,
    PRIMARY KEY (session_date, ticker)
);
CREATE TABLE IF NOT EXISTS followup_updates (
    id           INTEGER PRIMARY KEY,
    finished_at  TEXT NOT NULL,
    trigger      TEXT NOT NULL,
    status       TEXT NOT NULL,         -- ok or partial
    added        INTEGER NOT NULL,
    updated      INTEGER NOT NULL,
    new_surprises INTEGER NOT NULL,
    message      TEXT
);
"""


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    """The reports database, with the follow-up tables added if they're missing."""
    conn = reports_db.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Judging a move
# ---------------------------------------------------------------------------

def give_back(move_pct: float, after_pct: float) -> float:
    """How much of the move the price gave back: 0 = none, 1 = all of it, below 0 = it kept going.
    Rounded to 2 places, so a price exactly back where it started counts as all of it."""
    m, a = move_pct / 100, after_pct / 100
    return round(-a * (1 + m) / m, 2) if m else 0.0


def outcome(move_pct: float, after_pct: float | None) -> str | None:
    """held, faded or reversed (None until that horizon's price is known)."""
    if after_pct is None:
        return None
    g = give_back(move_pct, after_pct)
    return "reversed" if g >= 1 else "faded" if g > HELD_UP_TO else "held"


def follow(move_pct: float, after_pct: float | None) -> float | None:
    """The price change after the move, counted in the move's direction (+ means it kept going)."""
    return None if after_pct is None else round(after_pct if move_pct >= 0 else -after_pct, 2)


def is_surprise(move_pct: float, after_5d: float | None) -> bool:
    """Reversed within a week, or kept going by as much again."""
    if after_5d is None:
        return False
    g = give_back(move_pct, after_5d)
    return g >= 1 or g <= -1


def surprise_kind(move_pct: float, after_5d: float | None) -> str | None:
    if not is_surprise(move_pct, after_5d):
        return None
    return "reversed within a week" if give_back(move_pct, after_5d) >= 1 else "kept going: as much again within a week"


# ---------------------------------------------------------------------------
# Finding the flagged moves
# ---------------------------------------------------------------------------

def likely_why(body_md: str, ticker: str) -> str | None:
    """The brief's "Likely why" line for a ticker, as plain text."""
    section = re.search(rf"(?ms)^### {re.escape(ticker)}\b.*?(?=^#{{1,3}} |\Z)", body_md or "")
    if not section:
        return None
    line = re.search(r"(?m)^- \*\*Likely why:\*\*\s*(.+)$", section.group(0))
    return MARKDOWN_LINK.sub(r"\1", line.group(1)).strip() if line else None


def reason_for(why: str | None, earnings_day: bool) -> str:
    if why and "no clear catalyst" in why.lower():
        return "earnings" if earnings_day else "none"
    if earnings_day or (why and EARNINGS_WORDS.search(why)):
        return "earnings"
    return "news" if why else "none"


def _earnings_days(conn) -> set[tuple[str, str]]:
    """(ticker, day) for each earnings date on the events calendar."""
    try:
        return {(r[0], r[1]) for r in conn.execute("SELECT ticker, event_date FROM events WHERE kind = 'earnings'")}
    except Exception:  # no calendar yet
        return set()


def _add_new(conn) -> int:
    """A follow-up for each move flagged in a final report that doesn't have one yet."""
    rows = conn.execute(
        """SELECT t.session_date, t.ticker, t.return_1d_pct, t.move_read, r.body_md
           FROM report_tickers t JOIN reports r ON r.session_date = t.session_date
           LEFT JOIN followups f ON f.session_date = t.session_date AND f.ticker = t.ticker
           WHERE r.status = 'final' AND t.category = 'flagged' AND t.return_1d_pct IS NOT NULL
             AND f.ticker IS NULL""").fetchall()
    earnings = _earnings_days(conn)
    now = _utc_now()
    for r in rows:
        day = date.fromisoformat(r["session_date"])
        near = {(r["ticker"], (day - timedelta(days=d)).isoformat()) for d in range(0, 4)}  # reported before or on the day
        why = likely_why(r["body_md"], r["ticker"])
        conn.execute("""INSERT INTO followups (session_date, ticker, move_pct, move_read, reason, why, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""",
                     (r["session_date"], r["ticker"], r["return_1d_pct"], r["move_read"],
                      reason_for(why, bool(near & earnings)), why, now))
    return len(rows)


# ---------------------------------------------------------------------------
# Filling in prices
# ---------------------------------------------------------------------------

def last_complete_session() -> date:
    """The latest trading day whose close is known. The test environment replaces this."""
    session = market_tools.market_session()
    if session["status"] == "complete":
        return date.fromisoformat(session["as_of"])
    return date.fromisoformat(session["as_of"][:10]) - timedelta(days=1)  # today's isn't finished


def fetch_closes(ticker: str, since: date, last: date) -> list[tuple[str, float]]:
    """(day, close) from Yahoo, oldest first, from at least `since` up to the latest close."""
    days = (last - since).days + 10
    period = next((p for limit, p in PERIODS if days <= limit), PERIODS[-1][1])
    return [(row["date"], row["close"]) for row in prices.fetch_prices(ticker, period)]


def update(trigger: str = "command line", emit=None) -> dict:
    """Add follow-ups for newly flagged moves and fill in prices that are now known. Free (Yahoo only).
    Returns a summary, including the moves that just became surprises."""
    emit = emit or (lambda event: None)
    last = last_complete_session()
    problems, updated, surprises = [], 0, []
    with closing(connect()) as conn:
        with transaction(conn):
            added = _add_new(conn)
        pending = conn.execute("SELECT * FROM followups WHERE after_20d IS NULL ORDER BY ticker, session_date").fetchall()
        by_ticker: dict[str, list] = {}
        for row in pending:
            by_ticker.setdefault(row["ticker"], []).append(row)
        for ticker, rows in by_ticker.items():
            emit({"type": "progress", "message": f"Following up on {ticker}'s flagged moves"})
            try:
                closes = [(d, c) for d, c in fetch_closes(ticker, date.fromisoformat(rows[0]["session_date"]), last)
                          if date.fromisoformat(d) <= last]
            except Exception as e:  # one ticker failing doesn't stop the rest
                problems.append(f"{ticker}: {e}")
                continue
            index = {d: i for i, (d, _) in enumerate(closes)}
            with transaction(conn):
                for row in rows:
                    i = index.get(row["session_date"])
                    if i is None:
                        conn.execute("UPDATE followups SET note = ? WHERE session_date = ? AND ticker = ?",
                                     ("no Yahoo price for that day", row["session_date"], ticker))
                        continue
                    base = closes[i][1]
                    after = {n: round((closes[i + n][1] / base - 1) * 100, 2) if i + n < len(closes) else None
                             for n in HORIZONS}
                    old = {n: row[f"after_{n}d"] for n in HORIZONS}
                    if after == old:
                        continue
                    surprise = is_surprise(row["move_pct"], after[SURPRISE_HORIZON])
                    if surprise and not row["surprise"]:
                        surprises.append({"session_date": row["session_date"], "ticker": ticker})
                    conn.execute(f"""UPDATE followups SET {', '.join(f'after_{n}d = ?' for n in HORIZONS)},
                                     surprise = ?, note = NULL, updated_at = ? WHERE session_date = ? AND ticker = ?""",
                                 (*after.values(), int(surprise), _utc_now(), row["session_date"], ticker))
                    updated += 1
        status = "partial" if problems else "ok"
        message = "; ".join(problems)[:1000] or None
        conn.execute("""INSERT INTO followup_updates (finished_at, trigger, status, added, updated, new_surprises, message)
                        VALUES (?, ?, ?, ?, ?, ?, ?)""", (_utc_now(), trigger, status, added, updated, len(surprises), message))
        summary = last_update(conn)
    summary["surprises"] = surprises
    return summary


# ---------------------------------------------------------------------------
# Reading (the API, Ask and the agent's past_moves tool)
# ---------------------------------------------------------------------------

def last_update(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM followup_updates ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:  # not set up yet
        return None
    return dict(row) if row else None


def _move(row, story=None) -> dict:
    m = dict(row)
    m["direction"] = "up" if m["move_pct"] >= 0 else "down"
    m["kind"] = KIND_LABELS.get(m["move_read"], m["move_read"])
    m["reason_label"] = REASON_LABELS[m["reason"]]
    m["outcomes"] = {str(n): outcome(m["move_pct"], m[f"after_{n}d"]) for n in HORIZONS}
    m["follow"] = {str(n): follow(m["move_pct"], m[f"after_{n}d"]) for n in HORIZONS}
    m["settled"] = m[f"after_{HORIZONS[-1]}d"] is not None
    m["surprise_kind"] = surprise_kind(m["move_pct"], m[f"after_{SURPRISE_HORIZON}d"])
    m["surprise"] = bool(m["surprise"])
    m["story"] = story
    return m


def moves(conn, ticker: str | None = None, since: str | None = None, limit: int = 500) -> list[dict]:
    """Flagged moves, newest first, with how they played out and their latest story update."""
    try:
        rows = conn.execute(
            f"""SELECT * FROM followups WHERE 1 = 1{' AND ticker = ?' if ticker else ''}{' AND session_date >= ?' if since else ''}
                ORDER BY session_date DESC, ticker LIMIT ?""",
            [p for p in (ticker and ticker.upper(), since) if p] + [limit]).fetchall()
    except Exception:  # not set up yet
        return []
    stories = _latest_stories(conn)
    return [_move(r, stories.get((r["session_date"], r["ticker"]))) for r in rows]


def _latest_stories(conn) -> dict:
    try:
        rows = conn.execute("""SELECT session_date, ticker, verdict, update_text, finished_at, status FROM story_checks
                               WHERE status IN ('ok', 'no_news') ORDER BY id""").fetchall()
    except Exception:  # no story checks yet
        return {}
    return {(r["session_date"], r["ticker"]): {"verdict": r["verdict"], "update": r["update_text"],
                                                 "checked_at": r["finished_at"], "status": r["status"]} for r in rows}


def _group(label: str, found: list[dict], horizon: int) -> dict:
    judged = [m for m in found if m["outcomes"][str(horizon)]]
    counts = {k: sum(m["outcomes"][str(horizon)] == k for m in judged) for k in ("held", "faded", "reversed")}
    follows = [m["follow"][str(horizon)] for m in judged]
    return {"label": label, "moves": len(found), "judged": len(judged), **counts,
            "median_follow_pct": round(statistics.median(follows), 2) if follows else None,
            "enough": len(judged) >= MIN_FOR_PATTERN}


def patterns(all_moves: list[dict], horizon: int) -> dict:
    """How flagged moves played out `horizon` trading days later, grouped three ways."""
    def by(key, labels):
        groups = {}
        for m in all_moves:
            groups.setdefault(m[key], []).append(m)
        order = list(labels)
        return [_group(labels.get(k, k), groups[k], horizon)
                for k in sorted(groups, key=lambda k: order.index(k) if k in order else len(order))]
    return {"horizon": horizon, "all": _group("All flagged moves", all_moves, horizon),
            "by_kind": by("move_read", KIND_LABELS), "by_reason": by("reason", REASON_LABELS),
            "by_direction": by("direction", {"up": "Up moves", "down": "Down moves"})}


def describe_group(g: dict, horizon: int) -> str:
    when = {1: "the next day", 5: "a week later", 20: "a month later"}.get(horizon, f"{horizon} trading days later")
    if not g["judged"]:
        return f"{g['label']}: no moves to judge yet"
    return (f"{g['label']}: {g['held']} of {g['judged']} held {when}, {g['faded']} faded, {g['reversed']} reversed"
            + ("" if g["enough"] else " (too few to tell)"))


def past_for(conn, ticker: str, move_read: str | None, horizon: int = SURPRISE_HORIZON) -> dict:
    """For the brief: how this stock's earlier flagged moves, and moves of the same kind, played out."""
    every = moves(conn)
    mine = [m for m in every if m["ticker"] == ticker.upper()]
    same = [m for m in every if m["move_read"] == move_read] if move_read else []
    mine_g = _group(f"{ticker.upper()}'s flagged moves", mine, horizon)
    same_g = _group(f"{KIND_LABELS.get(move_read, move_read)} moves across the watchlist", same, horizon)
    lines = [describe_group(g, horizon) for g in (mine_g, same_g) if g["judged"]]
    last = next((m for m in mine if m["outcomes"][str(horizon)]), None)
    result = {"ticker": ticker.upper(), "horizon_days": horizon, "this_stock": mine_g,
              "same_kind": same_g if move_read else None,
              "last_move": None if last is None else {
                  "date": last["session_date"], "move_pct": last["move_pct"],
                  f"after_{horizon}d_pct": last[f"after_{horizon}d"], "outcome": last["outcomes"][str(horizon)]},
              "latest_story": mine[0]["story"] if mine and mine[0]["story"] else None,
              "summary": "; ".join(lines) or None,
              "worth_mentioning": mine_g["enough"] or same_g["enough"]}
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Follow-through: what happened after each flagged move.")
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("update", help="fill in follow-ups now (Yahoo only, free)")
    show = commands.add_parser("list", help="the latest moves and how they played out")
    show.add_argument("--ticker")
    pat = commands.add_parser("patterns", help="how moves of each kind played out")
    pat.add_argument("--days", type=int, default=SURPRISE_HORIZON, choices=HORIZONS)
    args = parser.parse_args()
    if args.command == "update":
        result = update(emit=lambda e: print(e["message"]))
        print(f"{result['status']}: {result['added']} new moves, {result['updated']} updated, "
              f"{result['new_surprises']} new surprises" + (f" ({result['message']})" if result["message"] else ""))
        return
    with closing(reports_db.connect(readonly=True)) as conn:
        found = moves(conn, args.ticker if args.command == "list" else None)
    if args.command == "list":
        for m in found[:40]:
            after = "  ".join(f"{n}d {m[f'after_{n}d']:+.2f}%" if m[f"after_{n}d"] is not None else f"{n}d   …   "
                              for n in HORIZONS)
            print(f"{m['session_date']}  {m['ticker']:<6} {m['move_pct']:+7.2f}%  {after}  "
                  f"{m['outcomes'][str(SURPRISE_HORIZON)] or 'pending':<9} {m['reason_label']}"
                  + ("  SURPRISE" if m["surprise"] else ""))
    else:
        result = patterns(found, args.days)
        for g in [result["all"], *result["by_kind"], *result["by_reason"], *result["by_direction"]]:
            print(describe_group(g, args.days))


if __name__ == "__main__":
    main()
```

### stories.py

```python
"""Story updates: what the news has said since a flagged move.

A check reads the newest headlines about the company, keeps the ones published after the move,
and asks Claude what they add to the original story: the brief's "Likely why" line and its
sources. If there are no newer headlines, there's no Claude call and no cost.

- Automatic: moves that turn out to be surprises (see followups.py) are checked once, after the
  final report that settles their first week. Only moves from the last 30 days are checked
  automatically, so reports from before you added this don't run up costs on old news.
- On demand: any flagged move, from the Story updates tab ("Check for updates") or the terminal.

From the terminal:
    python stories.py check MSFT 2026-10-13     check one move now (a few cents)
    python stories.py list                      the latest updates
"""

import argparse
import asyncio
import json
from contextlib import closing
from datetime import datetime, timedelta, timezone

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import events
import followups
import market_tools
import reports_db
from events import transaction

NEWS_PER_CHECK = 10              # newest headlines read per check
CHECK_BUDGET_USD = 0.10          # hard stop on Claude's cost per check
MAX_AUTOMATIC = 5                # most automatic (surprise) checks after one final report
AUTOMATIC_WITHIN_DAYS = 30       # automatic checks only for moves this recent; older ones are checked by hand
VERDICTS = {"developed": "Developed", "confirmed": "Confirmed", "contradicted": "Contradicted",
            "no_update": "No update"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS story_checks (
    id           INTEGER PRIMARY KEY,
    session_date TEXT NOT NULL,          -- the flagged move's day
    ticker       TEXT NOT NULL,
    trigger      TEXT NOT NULL CHECK (trigger IN ('surprise', 'manual')),
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'no_news', 'failed')),
    verdict      TEXT,                   -- developed, confirmed, contradicted or no_update
    update_text  TEXT,                   -- one or two sentences on what's happened since
    sources      TEXT,                   -- JSON list of the articles it's based on
    articles     INTEGER NOT NULL DEFAULT 0,  -- newer headlines found
    cost_usd     REAL NOT NULL DEFAULT 0,
    error        TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_story_checks_move ON story_checks (session_date, ticker);
"""

SYSTEM_PROMPT = """You check what has happened since a stock's unusual move. You get the original story
(the move, the explanation written at the time, and its source headlines), what the price has done since,
and newer headlines about the company.

Reply with JSON only, in this shape:
{"verdict": "developed", "update": "One or two plain sentences.", "sources": [1, 3]}

- verdict: "developed" (new information about the same story), "confirmed" (later news supports the
  original explanation), "contradicted" (later news undercuts it), or "no_update" (nothing about this story).
- update: what has happened since, from the newer headlines only. Mention dates. If nothing is about this
  story, say so in one sentence.
- sources: the numbers of the newer headlines you used (none for no_update).
- Use only the headlines given. Never explain the price move yourself, predict anything, or give advice."""

options = ClaudeAgentOptions(
    system_prompt=SYSTEM_PROMPT,
    mcp_servers={},
    strict_mcp_config=True,
    tools=[],
    max_turns=1,
    max_budget_usd=CHECK_BUDGET_USD,
)


class StoryError(ValueError):
    """A check that can't be done, with a message to show as it is. status is the HTTP status."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def connect():
    """The reports database, with the follow-up and story tables added if they're missing."""
    conn = followups.connect()
    conn.executescript(SCHEMA)
    return conn


def fetch_news(ticker: str) -> list[dict]:
    """The company's newest headlines. Tests and the test environment replace this."""
    return market_tools.get_news(ticker, NEWS_PER_CHECK)


async def _ask_claude_async(prompt: str) -> tuple[str, float]:
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't check the story: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(prompt))


# ---------------------------------------------------------------------------
# One check
# ---------------------------------------------------------------------------

def build_prompt(move: dict, original: list[dict], later: list[dict]) -> str:
    when = {1: "next day", 5: "after a week", 20: "after a month"}
    since = [f"{when[n]}: {move[f'after_{n}d']:+.2f}%" for n in followups.HORIZONS if move[f"after_{n}d"] is not None]
    lines = [f"STOCK: {move['ticker']}",
             f"MOVE: {move['move_pct']:+.2f}% on {move['session_date']} ({move['kind']})",
             f"EXPLANATION AT THE TIME: {move['why'] or 'none given'}",
             f"PRICE SINCE: {', '.join(since) or 'not known yet'}", "", "Headlines at the time:"]
    lines += [f"- {a.get('title')} ({a.get('publisher') or 'unknown'})" for a in original] or ["- none"]
    lines += ["", "Newer headlines:"]
    for n, a in enumerate(later, 1):
        lines += [f"[{n}] {a.get('publisher') or 'unknown publisher'} | published {a.get('published') or 'unknown'}",
                  f"    {a.get('title') or ''}", f"    {(a.get('summary') or '').strip()}"]
    return "\n".join(lines)


def parse_reply(text: str, later: list[dict]) -> tuple[str, str, list[dict]]:
    """(verdict, update, sources) from Claude's reply, checked."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    verdict = str(data.get("verdict") or "").strip().lower()
    update = " ".join(str(data.get("update") or "").split())
    if verdict not in VERDICTS:
        raise ValueError(f"Claude's reply had an unknown verdict ({verdict or 'none'})")
    if not update:
        raise ValueError("Claude's reply had no update")
    refs = data.get("sources") if isinstance(data.get("sources"), list) else []
    picked = sorted({r for r in refs if isinstance(r, int) and 1 <= r <= len(later)})
    if verdict != "no_update" and not picked:
        raise ValueError("Claude's reply cited none of the newer headlines")
    keep = ("title", "publisher", "url", "published")
    return verdict, update[:600], [{k: later[r - 1].get(k) for k in keep} for r in picked]


def _the_move(conn, session_date: str, ticker: str) -> dict:
    row = conn.execute("SELECT * FROM followups WHERE session_date = ? AND ticker = ?", (session_date, ticker)).fetchone()
    if row is None:
        raise StoryError(f"{ticker} wasn't flagged in the final report of {session_date}.", 404)
    return followups._move(row)


def check(session_date: str, ticker: str, trigger: str = "manual", emit=None) -> dict:
    """Check one flagged move's story now. Returns the saved check."""
    emit = emit or (lambda event: None)
    ticker = ticker.strip().upper()
    with closing(connect()) as conn:
        move = _the_move(conn, session_date, ticker)
        with transaction(conn):
            check_id = conn.execute(
                "INSERT INTO story_checks (session_date, ticker, trigger, status, started_at) VALUES (?, ?, ?, 'running', ?)",
                (session_date, ticker, trigger, _utc_now())).lastrowid
        original = [dict(r) for r in conn.execute(
            "SELECT title, publisher FROM report_sources WHERE session_date = ? AND ticker = ?", (session_date, ticker))]
    company = events.company_name(ticker)
    fields = {"status": "failed", "verdict": None, "update_text": None, "sources": "[]", "articles": 0,
              "cost_usd": 0.0, "error": None}
    try:
        emit({"type": "progress", "message": f"Reading {company}'s newest headlines"})
        later = [a for a in fetch_news(ticker)
                 if (d := events._to_date(a.get("published"))) is not None and d.isoformat() > session_date]
        fields["articles"] = len(later)
        if not later:  # nothing newer: no Claude call, no cost
            fields.update(status="no_news", verdict="no_update",
                          update_text=f"No newer headlines about {company} since {session_date}.")
        else:
            emit({"type": "progress", "message": f"Reading {len(later)} newer headline{'s' if len(later) != 1 else ''} with Claude"})
            reply, cost = ask_claude(build_prompt(move, original, later))
            fields["cost_usd"] = round(cost, 4)
            verdict, update, sources = parse_reply(reply, later)
            fields.update(status="ok", verdict=verdict, update_text=update, sources=json.dumps(sources))
    except Exception as e:  # saved as a failed check, so the reason is visible
        fields["error"] = str(e)[:500] or type(e).__name__
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute(f"""UPDATE story_checks SET {', '.join(f'{k} = ?' for k in fields)}, finished_at = ?
                             WHERE id = ?""", (*fields.values(), _utc_now(), check_id))
        return get_check(conn, check_id)


def check_surprises(emit=None, limit: int = MAX_AUTOMATIC, within_days: int | None = None) -> list[dict]:
    """The automatic checks: each recent surprise move that hasn't had one yet (at most `limit` at a time).
    Recent means within `within_days` (AUTOMATIC_WITHIN_DAYS) of the latest close, so older surprises, such as
    those in reports from before follow-through was added, don't spend money on today's headlines."""
    emit = emit or (lambda event: None)
    within = AUTOMATIC_WITHIN_DAYS if within_days is None else within_days
    since = (followups.last_complete_session() - timedelta(days=within)).isoformat()
    with closing(connect()) as conn:
        due = conn.execute(
            """SELECT f.session_date, f.ticker FROM followups f
               WHERE f.surprise = 1 AND f.session_date >= ? AND NOT EXISTS (
                   SELECT 1 FROM story_checks c WHERE c.session_date = f.session_date AND c.ticker = f.ticker
                   AND c.trigger = 'surprise')
               ORDER BY f.session_date DESC, f.ticker LIMIT ?""", (since, limit)).fetchall()
    done = []
    for row in due:
        emit({"type": "progress", "message": f"Checking the news on {row['ticker']}'s move of {row['session_date']} (a surprise)"})
        done.append(check(row["session_date"], row["ticker"], "surprise", emit))
    return done


def after_final_report(emit=None, within_days: int | None = None) -> dict:
    """Run after each final report: fill in follow-ups (free), then check any new surprises.
    Problems here are reported, never raised, so they can't spoil the run that called this."""
    emit = emit or (lambda event: None)
    result = {"followups": None, "checks": [], "problems": []}
    try:
        result["followups"] = followups.update("after a final report")
        f = result["followups"]
        emit({"type": "followups", "message": f"Follow-through: {f['added']} new move{'s' if f['added'] != 1 else ''}, {f['updated']} updated"
              + (f", {f['new_surprises']} new surprise{'s' if f['new_surprises'] != 1 else ''}" if f["new_surprises"] else "")})
    except Exception as e:
        result["problems"].append(f"follow-through: {e}")
    try:
        result["checks"] = check_surprises(emit, within_days=within_days)
        cost = sum(c["cost_usd"] for c in result["checks"])
        if result["checks"]:
            emit({"type": "stories", "message": f"Story updates: checked {len(result['checks'])} surprise"
                  f"{'s' if len(result['checks']) != 1 else ''} · ${cost:.3f}"})
    except Exception as e:
        result["problems"].append(f"story updates: {e}")
    for problem in result["problems"]:
        emit({"type": "warning", "message": f"Saved, but {problem}. It will catch up after the next final report."})
    return result


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _check_row(row) -> dict:
    c = dict(row)
    c["sources"] = json.loads(c["sources"] or "[]")
    c["verdict_label"] = VERDICTS.get(c["verdict"]) if c["status"] != "no_news" else "No newer news"
    return c


def get_check(conn, check_id: int) -> dict:
    return _check_row(conn.execute("SELECT * FROM story_checks WHERE id = ?", (check_id,)).fetchone())


def latest(conn, ticker: str | None = None, limit: int = 100) -> list[dict]:
    """Finished checks, newest first, each with its move."""
    try:
        rows = conn.execute(
            f"""SELECT c.* FROM story_checks c WHERE c.status != 'running'{' AND c.ticker = ?' if ticker else ''}
                ORDER BY c.finished_at DESC, c.session_date DESC, c.id DESC LIMIT ?""",
            ([ticker.upper()] if ticker else []) + [limit]).fetchall()
        found = {(r["session_date"], r["ticker"]): r for r in conn.execute("SELECT * FROM followups")}
    except Exception:  # not set up yet
        return []
    checks = []
    for r in rows:
        c = _check_row(r)
        move = found.get((c["session_date"], c["ticker"]))
        c["move"] = followups._move(move) if move else None
        checks.append(c)
    return checks


def unchecked(conn, since: str, limit: int = 40) -> list[dict]:
    """Recent flagged moves with no finished check yet: the ones the tab offers to check."""
    recent = "SELECT f.* FROM followups f WHERE f.session_date >= ?"
    checked = """ AND NOT EXISTS (SELECT 1 FROM story_checks c WHERE c.session_date = f.session_date
                  AND c.ticker = f.ticker AND c.status IN ('ok', 'no_news'))"""
    order = " ORDER BY f.session_date DESC, f.ticker LIMIT ?"
    rows = []
    for sql in (recent + checked + order, recent + order):  # the second before any story has been checked
        try:
            rows = conn.execute(sql, (since, limit)).fetchall()
            break
        except Exception:  # no story_checks table yet (or no followups table: nothing to offer)
            continue
    return [followups._move(r) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser(description="Story updates: what the news has said since a flagged move.")
    commands = parser.add_subparsers(dest="command", required=True)
    one = commands.add_parser("check", help="check one flagged move's story now (a few cents)")
    one.add_argument("ticker")
    one.add_argument("date")
    commands.add_parser("list", help="the latest story updates")
    args = parser.parse_args()
    if args.command == "check":
        try:
            c = check(args.date, args.ticker, emit=lambda e: print(e["message"]))
        except StoryError as e:
            raise SystemExit(str(e))
        if c["status"] == "failed":
            raise SystemExit(f"failed: {c['error']}")
        print(f"{c['verdict_label']}: {c['update_text']}  (${c['cost_usd']:.3f})")
        for s in c["sources"]:
            print(f"  - {s['publisher']}: {s['title']} {s['url'] or ''}")
    else:
        with closing(reports_db.connect(readonly=True)) as conn:
            for c in latest(conn, limit=30):
                print(f"{c['finished_at']}  {c['ticker']:<6} move of {c['session_date']}  "
                      f"{c['verdict_label'] or c['status']:<14} {c['update_text'] or c['error'] or ''}")


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
briefs can say what's coming up. past_moves reads the follow-through of earlier flagged
moves (followups.py), so briefs can say how similar moves played out.

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
4. If anything was flagged, call `past_moves` once, with the flagged tickers and each one's `context.read` as `kinds`.
5. For each flagged ticker, read its `context` (see below), then call `get_news` to find the likely reason. Call `compute_moves` if you need more detail on a ticker.
6. Write the brief.

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

## Past moves

`past_moves` says how earlier flagged moves played out a week later: the same stock's, and moves of the same kind across the watchlist.

- If a ticker's `worth_mentioning` is true, you may add its `summary` to that ticker's "Worth watching" line, as written, as background ("Past stock-specific moves here mostly held a week later: ...").
- It's history, not a forecast. Never say a move will hold or reverse.
- If `latest_story` has an update from a recent move of the same stock, you may mention it in one short clause.

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

After saving, it sends any Discord alerts the report calls for (see alerts.py). After a final
report, it also fills in the follow-through of earlier flagged moves (followups.py) and checks
the news on any that turned out to be surprises (stories.py).

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
import stories
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
        "mcp__market__past_moves",
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
    if status == "final":  # once a day: what happened after earlier flagged moves (and news on any surprises)
        await asyncio.to_thread(stories.after_final_report, emit)
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
"""Answer questions about saved reports with Claude, using retrieval (RAG).

For each question it gathers, within a size limit:
1. Figures across days for any watchlist ticker named in the question.
2. The events calendar: everything in the next 30 days, plus the last 30 days for named tickers.
3. What happened after flagged moves (followups.py and stories.py): for named tickers, each
   move's follow-through and story updates; otherwise, how moves of each kind played out.
4. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
5. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import events
import followups
import reports_db
import search_index
import stories

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports, passages and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05). Passages carry the date of the report they came from.
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- Dated events come from the events calendar: cite them as (calendar), and say so when a date isn't confirmed.
- Follow-through figures say what a stock's price did after a flagged move: cite them as (follow-through).
  Story updates say what later news added: cite them as (story update, then the date it was checked).
  Both are history, never a forecast.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
CALENDAR_DAYS = 30               # events calendar: this far ahead (all tickers) and back (named tickers)
FOLLOWUP_MOVES = 10              # flagged moves' follow-through per named ticker
STORY_UPDATES = 3                # latest story updates per named ticker
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


def followup_section(conn, tickers: list[str]) -> str:
    """What happened after flagged moves: each named ticker's moves and story updates, or, with no
    ticker named, how moves of each kind played out a week later."""
    horizon = followups.SURPRISE_HORIZON
    if not tickers:
        found = followups.moves(conn)
        if not found:
            return ""
        result = followups.patterns(found, horizon)
        lines = ["## How flagged moves played out a week later (all stocks; cite as (follow-through))", ""]
        lines += [f"- {followups.describe_group(g, horizon)}" for g in
                  [result["all"], *result["by_kind"], *result["by_reason"], *result["by_direction"]]]
        return "\n".join(lines)
    parts = []
    for ticker in tickers:
        found = followups.moves(conn, ticker)[:FOLLOWUP_MOVES]
        if found:
            lines = [f"## Follow-through for {ticker}: the price after each flagged move (cite as (follow-through))",
                     "day of the move | move % | kind | reason | 1 day later % | 1 week later % | 1 month later % | after a week"]
            for m in found:
                after = " | ".join("" if m[f"after_{n}d"] is None else f"{m[f'after_{n}d']:+.2f}" for n in followups.HORIZONS)
                lines.append(f"{m['session_date']} | {m['move_pct']:+.2f} | {m['kind']} | {m['reason_label']} | {after} | "
                             f"{m['outcomes'][str(horizon)] or 'not known yet'}")
            parts.append("\n".join(lines))
        checks = [c for c in stories.latest(conn, ticker, STORY_UPDATES) if c["status"] in ("ok", "no_news")]
        if checks:
            lines = [f"## Story updates for {ticker} (cite as (story update, date checked))"]
            for c in checks:
                cited = "; ".join(f"{s['publisher']}: {s['title']}" for s in c["sources"])
                lines.append(f"- Move of {c['session_date']}, checked {c['finished_at'][:10]}: {c['verdict_label']}. "
                             f"{c['update_text']}" + (f" Sources: {cited}" if cited else ""))
            parts.append("\n".join(lines))
    return "\n\n".join(parts)


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
    followed = followup_section(conn, tickers)
    if followed:
        add(followed)

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
    GET  /api/followups?horizon=1|5|20&ticker=   flagged moves and what the price did after them
    POST /api/followups/refresh  fill in follow-through prices now (Yahoo only, free)
    GET  /api/stories?ticker=    story updates (what later news said), and recent moves to check
    POST /api/stories/check      re-check one move's news now: {"session_date": "2026-10-13", "ticker": "MSFT"}
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules
(a run also logs the Discord alerts it sends). The events calendar is written the same
way, by events.py's scan (daily at the market open, or "Update now"). The Stocks tab edits
watchlist.txt, through watchlist.py's safe edits. Follow-through and story updates are written
by followups.py and stories.py (after each final report, or "Refresh prices" and "Check for updates").
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
import followups
import market_tools
import prices
import reports_db
import run_brief
import search_index
import stories
import watchlist

log = logging.getLogger("uvicorn.error")

DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "300"))  # between on-demand runs
CALENDAR_SCAN_COOLDOWN_SECONDS = int(os.environ.get("CALENDAR_SCAN_COOLDOWN_SECONDS", "300"))
MAX_CALENDAR_DAYS = 100                                                   # longest date range one request returns
FOLLOWUP_REFRESH_COOLDOWN_SECONDS = int(os.environ.get("FOLLOWUP_REFRESH_COOLDOWN_SECONDS", "60"))
STORY_CHECK_COOLDOWN_SECONDS = int(os.environ.get("STORY_CHECK_COOLDOWN_SECONDS", "30"))  # each check can cost a few cents
STORY_DAYS = 30                                                           # recent moves offered for a news check
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


def _latest_followups() -> tuple:
    """The latest follow-through update and story check, from any program (scheduled runs included)."""
    with _db() as conn:
        try:
            update = conn.execute("SELECT MAX(id) FROM followup_updates").fetchone()[0]
        except Exception:  # not set up yet
            update = None
        try:
            checked = conn.execute("SELECT MAX(id) FROM story_checks WHERE finished_at IS NOT NULL").fetchone()[0]
        except Exception:
            checked = None
    return update, checked


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
        return _latest_change(), _latest_calendar_scan(), watchlist_stamp(), _latest_followups()

    last, last_scan, last_stamp, last_followed = await asyncio.to_thread(check)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current, scan, stamp, followed = await asyncio.to_thread(check)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if followed != last_followed:  # follow-through updated, or a story checked
            if followed[0] != last_followed[0]:
                hub.publish({"type": "followups_updated"})
            if followed[1] != last_followed[1]:
                hub.publish({"type": "story_checked"})
            last_followed = followed
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


# ---------------------------------------------------------------------------
# Follow-through (the price after flagged moves) and story updates (the news since)
# ---------------------------------------------------------------------------

class BackgroundJob:
    """One job of a kind at a time, run in a worker thread, with a cooldown: refreshing
    follow-through prices, and checking a story's news. Progress goes out as live updates."""

    def __init__(self, event_type: str, cooldown, busy: str, too_soon: str):
        self.event_type, self.cooldown, self.busy, self.too_soon = event_type, cooldown, busy, too_soon
        self.task, self.last_started = None, None
        self.state = {"state": "idle", "started_at": None, "finished_at": None, "message": None,
                      "target": None, "result": None, "error": None}

    def snapshot(self) -> dict:
        return dict(self.state)

    def start(self, work, target=None) -> dict:
        """work(emit) runs in a thread; what it returns becomes the job's result."""
        if self.task and not self.task.done():
            raise AlreadyRunning(self.busy)
        if self.last_started is not None:
            wait = self.cooldown() - (time.monotonic() - self.last_started)
            if wait > 0:
                seconds = int(wait) + 1
                raise TooSoon(self.too_soon.format(f"{seconds} second{'s' if seconds != 1 else ''}"))
        self.last_started = time.monotonic()
        self.state = {"state": "running", "started_at": _utc_now(), "finished_at": None, "message": "Starting…",
                      "target": target, "result": None, "error": None}
        hub.publish({"type": self.event_type, "job": self.snapshot()})
        self.task = asyncio.create_task(self._run(work))
        return self.snapshot()

    def _progress(self, event: dict) -> None:
        if event.get("type") == "progress":
            self.state["message"] = event["message"]
            hub.publish({"type": self.event_type, "job": self.snapshot()})

    async def _run(self, work) -> None:
        loop = asyncio.get_running_loop()
        emit = lambda event: loop.call_soon_threadsafe(self._progress, event)  # noqa: E731  (work runs in a thread)
        try:
            self.state.update(state="finished", result=await asyncio.to_thread(work, emit), message=None)
        except Exception as e:
            self.state.update(state="failed", error=str(e) or type(e).__name__, message=None)
        self.state["finished_at"] = _utc_now()
        hub.publish({"type": self.event_type, "job": self.snapshot()})


followup_refreshes = BackgroundJob("followups_refresh", lambda: FOLLOWUP_REFRESH_COOLDOWN_SECONDS,
                                   "Prices are already being refreshed.",
                                   "Prices were just refreshed. Try again in {}.")
story_checks = BackgroundJob("story_check", lambda: STORY_CHECK_COOLDOWN_SECONDS,
                             "A story is already being checked. Its progress is shown on the Story updates tab.",
                             "A story was just checked. Try again in {}.")


def _followups_view(horizon: int, ticker: str | None) -> dict:
    with _db() as conn:
        every = followups.moves(conn)
        updated = followups.last_update(conn)
    return {"horizon": horizon, "horizons": list(followups.HORIZONS),
            "moves": [m for m in every if not ticker or m["ticker"] == ticker.upper()],
            "tickers": sorted({m["ticker"] for m in every}), "patterns": followups.patterns(every, horizon),
            "updated": updated, "refresh": followup_refreshes.snapshot()}


async def followups_view(request):
    raw = request.query_params.get("horizon", str(followups.SURPRISE_HORIZON))
    ticker = request.query_params.get("ticker") or None
    if not raw.isdigit() or int(raw) not in followups.HORIZONS:
        return _error(400, f"horizon must be one of: {', '.join(map(str, followups.HORIZONS))}")
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_followups_view, int(raw), ticker))


async def refresh_followups(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        job = followup_refreshes.start(lambda emit: followups.update("manual", emit))
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"refresh": job}, status_code=202)


def _stories_view(ticker: str | None) -> dict:
    since = (upcoming.today_et() - timedelta(days=STORY_DAYS)).isoformat()
    with _db() as conn:
        found = stories.latest(conn, ticker)
        todo = stories.unchecked(conn, since)
    return {"checks": found, "unchecked": [m for m in todo if not ticker or m["ticker"] == ticker.upper()],
            "days": STORY_DAYS, "check": story_checks.snapshot(), "max_cost_usd": stories.CHECK_BUDGET_USD}


async def stories_view(request):
    ticker = request.query_params.get("ticker") or None
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_stories_view, ticker))


async def check_story(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"session_date": "2026-10-13", "ticker": "MSFT"}')
    day = body.get("session_date") if isinstance(body, dict) else None
    ticker = body.get("ticker") if isinstance(body, dict) else None
    if not isinstance(day, str) or not DATE.fullmatch(day) or not isinstance(ticker, str) or not TICKER.fullmatch(ticker):
        return _error(400, 'send JSON like {"session_date": "2026-10-13", "ticker": "MSFT"}')
    ticker = ticker.upper()
    with _db() as conn:  # a quick check first, so a wrong move is refused straight away
        try:
            known = conn.execute("SELECT 1 FROM followups WHERE session_date = ? AND ticker = ?", (day, ticker)).fetchone()
        except Exception:
            known = None
    if not known:
        return _error(404, f"{ticker} wasn't flagged in the final report of {day}.")
    try:
        job = story_checks.start(lambda emit: stories.check(day, ticker, "manual", emit),
                                 target={"session_date": day, "ticker": ticker})
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"check": job}, status_code=202)


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
        Route("/api/followups", followups_view, methods=["GET"]),
        Route("/api/followups/refresh", refresh_followups, methods=["POST"]),
        Route("/api/stories", stories_view, methods=["GET"]),
        Route("/api/stories/check", check_story, methods=["POST"]),
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

### frontend/src/components/FollowThroughTab.jsx

```jsx
import { useEffect, useState } from 'react'
import { getFollowups, refreshFollowups } from '../api'
import { useOpenChart } from '../chartContext'
import { formatDateTime, formatShortDate, percent } from '../format'
import { routes } from '../useRoute'

const HORIZONS = { 1: 'Next day', 5: 'A week later', 20: 'A month later' }
const OUTCOMES = [
  ['held', 'Held', 'gave back less than a quarter of the move'],
  ['faded', 'Faded', 'gave back a quarter or more'],
  ['reversed', 'Reversed', 'gave back all of it, or more'],
]

// The middle (median) price change since the move, in words: "typically 1.06% further" or "typically 2.10% back"
function typical(pct) {
  if (pct === 0) return 'typically flat since'
  return `typically ${Math.abs(pct).toFixed(2)}% ${pct > 0 ? 'further' : 'back'}`
}

// One row of the patterns: a 100% bar split into held, faded and reversed, with the counts in words
function PatternRow({ group }) {
  const { judged } = group
  return (
    <div className="pattern-row">
      <div className="pattern-label">{group.label}</div>
      {judged ? (
        <div className="outcome-bar" role="img" aria-label={`${group.label}: ${group.held} held, ${group.faded} faded, ${group.reversed} reversed`}>
          {OUTCOMES.filter(([key]) => group[key]).map(([key, label]) => (
            <span
              key={key}
              className={`seg ${key}`}
              style={{ flexGrow: group[key] }}
              data-tip={`${label}: ${group[key]} of ${judged} (${Math.round((group[key] / judged) * 100)}%)`}
            />
          ))}
        </div>
      ) : (
        <div className="outcome-bar empty" />
      )}
      <div className="pattern-text muted small">
        {judged ? (
          <>
            {group.held} held · {group.faded} faded · {group.reversed} reversed
            {group.median_follow_pct != null && <> · {typical(group.median_follow_pct)}</>}
            {!group.enough && <span className="too-few"> · too few to tell</span>}
          </>
        ) : (
          'No moves to judge yet'
        )}
      </div>
    </div>
  )
}

function Patterns({ title, groups }) {
  if (!groups?.length) return null
  return (
    <div className="patterns">
      <h3>{title}</h3>
      {groups.map((g) => (
        <PatternRow key={g.label} group={g} />
      ))}
    </div>
  )
}

function Outcome({ move, horizon }) {
  const result = move.outcomes[String(horizon)]
  if (!result) return <span className="muted">not yet</span>
  return (
    <span className="outcome">
      <span className={`swatch ${result}`} aria-hidden="true" />
      {result}
      {move.surprise && (
        <span className="surprise" title={move.surprise_kind}>
          {' '}
          · surprise
        </span>
      )}
    </span>
  )
}

function MoveRow({ move, horizon, latestDate }) {
  const openChart = useOpenChart()
  const day = move.session_date
  const after = (n) => {
    const value = move[`after_${n}d`]
    return (
      <td className={`num ${value > 0 ? 'up' : value < 0 ? 'down' : ''}`}>{value == null ? <span className="muted">…</span> : percent(value)}</td>
    )
  }
  return (
    <tr className={move.surprise ? 'surprise-row' : undefined}>
      <td>
        <a href={day === latestDate ? routes.today : routes.previous(day)}>{formatShortDate(day)}</a>
      </td>
      <td className="ticker">
        <button type="button" className="ticker-button" onClick={(e) => openChart(move.ticker, e.currentTarget)} aria-label={`Show ${move.ticker} chart`}>
          {move.ticker}
        </button>
      </td>
      <td className={`num ${move.move_pct > 0 ? 'up' : 'down'}`}>{percent(move.move_pct)}</td>
      <td>{move.kind}</td>
      <td title={move.why || undefined}>{move.reason_label}</td>
      {after(1)}
      {after(5)}
      {after(20)}
      <td>
        <Outcome move={move} horizon={horizon} />
      </td>
      <td>
        <a href={routes.stories(day, move.ticker)} className="story-link">
          {move.story ? move.story.status === 'no_news' ? 'No newer news' : `Story: ${move.story.verdict.replace('_', ' ')}` : 'Check news'}
        </a>
      </td>
    </tr>
  )
}

// What the price did after each flagged move: patterns first, then every move
export default function FollowThroughTab({ version, refresh, onRefreshStarted, latestDate }) {
  const [horizon, setHorizon] = useState(5)
  const [ticker, setTicker] = useState('')
  const [onlySurprises, setOnlySurprises] = useState(false)
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = refresh?.state === 'running'

  useEffect(() => {
    let current = true
    getFollowups(horizon, ticker)
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [horizon, ticker, version])

  const refreshNow = async () => {
    setStarting(true)
    setError(null)
    try {
      onRefreshStarted(await refreshFollowups())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const updated = data?.updated
  const status = running
    ? refresh.message || 'Refreshing…'
    : updated
      ? `Prices updated ${formatDateTime(updated.finished_at)}`
      : 'Not worked out yet'
  const shown = (data?.moves || []).filter((m) => !onlySurprises || m.surprise)
  const p = data?.patterns

  return (
    <>
      <section className="panel followthrough" aria-label="How flagged moves played out">
        <div className="section-head">
          <h2>How flagged moves played out</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={refreshNow} disabled={running || starting}>
              {running ? 'Refreshing…' : 'Refresh prices'}
            </button>
          </div>
        </div>
        <p className="muted small">
          The price 1, 5 and 20 trading days after each move flagged in a final report, from Yahoo Finance. Prices only:
          for what the news said since, see <a href={routes.stories()}>Story updates</a>.
        </p>
        {error && <p className="error">{error}</p>}
        {refresh?.state === 'failed' && <p className="error">The refresh didn't finish: {refresh.error}</p>}
        {!running && updated?.status === 'partial' && <p className="muted small">Some prices couldn't be read: {updated.message}</p>}

        <div className="horizon-picker" role="group" aria-label="How long after the move">
          {Object.entries(HORIZONS).map(([n, label]) => (
            <button key={n} type="button" className="chip" aria-pressed={horizon === Number(n)} onClick={() => setHorizon(Number(n))}>
              {label}
            </button>
          ))}
        </div>

        {p && p.all.moves === 0 ? (
          <p className="muted">No flagged moves in final reports yet. They're followed up after each final report.</p>
        ) : (
          p && (
            <>
              <ul className="outcome-legend" aria-label="Key">
                {OUTCOMES.map(([key, label, meaning]) => (
                  <li key={key}>
                    <span className={`swatch ${key}`} aria-hidden="true" />
                    <strong>{label}</strong> <span className="muted">{meaning}</span>
                  </li>
                ))}
              </ul>
              <div className="patterns-all">
                <PatternRow group={p.all} />
              </div>
              <div className="patterns-grid">
                <Patterns title="By kind of move" groups={p.by_kind} />
                <Patterns title="By reason" groups={p.by_reason} />
                <Patterns title="By direction" groups={p.by_direction} />
              </div>
              <p className="muted small">
                History, not a forecast. Groups with fewer than 5 judged moves are marked "too few to tell".
              </p>
            </>
          )
        )}
      </section>

      <section className="panel" aria-label="Flagged moves">
        <div className="section-head">
          <h2>Flagged moves</h2>
          <div className="moves-filters">
            <label className="small">
              Stock{' '}
              <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
                <option value="">All</option>
                {(data?.tickers || []).map((t) => (
                  <option key={t}>{t}</option>
                ))}
              </select>
            </label>
            <label className="small">
              <input type="checkbox" checked={onlySurprises} onChange={(e) => setOnlySurprises(e.target.checked)} /> Only surprises
            </label>
          </div>
        </div>
        {shown.length === 0 ? (
          <p className="muted">{data ? 'No flagged moves to show.' : 'Loading…'}</p>
        ) : (
          <div className="table-wrap">
            <table className="tickers moves">
              <thead>
                <tr>
                  <th>Day</th>
                  <th>Ticker</th>
                  <th className="num">Move</th>
                  <th>Kind</th>
                  <th>Reason</th>
                  <th className="num">Next day</th>
                  <th className="num">1 week</th>
                  <th className="num">1 month</th>
                  <th>{HORIZONS[horizon]}</th>
                  <th>
                    <span className="sr-only">News</span>
                  </th>
                </tr>
              </thead>
              <tbody>
                {shown.map((m) => (
                  <MoveRow key={`${m.session_date}-${m.ticker}`} move={m} horizon={horizon} latestDate={latestDate} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </>
  )
}
```

### frontend/src/components/StoriesTab.jsx

```jsx
import { useEffect, useRef, useState } from 'react'
import { checkStory, getStories } from '../api'
import { formatDateTime, formatFullDate, formatShortDate, percent, safeUrl } from '../format'
import { routes } from '../useRoute'

const AFTER = [
  [1, 'next day'],
  [5, 'a week'],
  [20, 'a month'],
]

// "+1.20% next day, -3.40% a week (reversed)": the price since, in one line
function sinceLine(move) {
  const parts = AFTER.filter(([n]) => move[`after_${n}d`] != null).map(([n, label]) => `${percent(move[`after_${n}d`])} ${label}`)
  if (!parts.length) return 'Price since: not known yet'
  const lastKnown = [...AFTER].reverse().find(([n]) => move.outcomes[String(n)])
  return `Price since: ${parts.join(', ')}${lastKnown ? ` (${move.outcomes[String(lastKnown[0])]} after ${lastKnown[1]})` : ''}`
}

function MoveHeading({ move, sessionDate, ticker }) {
  return (
    <div className="story-head">
      <strong>{ticker}</strong>
      <span>
        move of {formatShortDate(sessionDate)}
        {move && (
          <>
            {' · '}
            <span className={move.move_pct > 0 ? 'up' : 'down'}>{percent(move.move_pct)}</span> · {move.reason_label}
          </>
        )}
      </span>
    </div>
  )
}

// `inPicked`: shown under the picked move, which already says what happened at the time and since
function Check({ check, inPicked = false }) {
  const move = check.move
  return (
    <article className="story" aria-label={`${check.ticker}, move of ${check.session_date}`}>
      <header>
        <MoveHeading move={move} sessionDate={check.session_date} ticker={check.ticker} />
        <span className={`verdict ${check.status === 'failed' ? 'failed' : check.verdict}`}>
          {check.status === 'failed' ? 'Check failed' : check.verdict_label}
        </span>
      </header>
      {move?.why && !inPicked && <p className="muted small">At the time: {move.why}</p>}
      <p className="story-update">{check.status === 'failed' ? check.error : check.update_text}</p>
      {check.sources.length > 0 && (
        <ul className="story-sources">
          {check.sources.map((s, i) => (
            <li key={i}>
              <a href={safeUrl(s.url)} target="_blank" rel="noreferrer">
                {s.title}
              </a>{' '}
              <span className="muted small">{s.publisher}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted small">
        {move && !inPicked && <>{sinceLine(move)} · </>}
        Checked {formatDateTime(check.finished_at)} ·{' '}
        {check.trigger === 'surprise' ? `automatically: a surprise (${move?.surprise_kind || 'unexpected move'})` : 'on request'}
        {check.cost_usd > 0 && ` · $${check.cost_usd.toFixed(3)}`}
      </p>
    </article>
  )
}

function CheckButton({ sessionDate, ticker, job, onStarted, label = 'Check for updates' }) {
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = job?.state === 'running'
  const mine = job?.target?.session_date === sessionDate && job?.target?.ticker === ticker
  const start = async () => {
    setStarting(true)
    setError(null)
    try {
      onStarted(await checkStory(sessionDate, ticker))
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }
  return (
    <div className="check-action">
      <button className="primary" onClick={start} disabled={running || starting} aria-label={`${label}: ${ticker}, ${sessionDate}`}>
        {running && mine ? 'Checking…' : label}
      </button>
      {running && mine && (
        <span className="muted small" aria-live="polite">
          {job.message}
        </span>
      )}
      {mine && job?.state === 'failed' && <span className="error">The check didn't finish: {job.error}</span>}
      {error && <span className="error">{error}</span>}
    </div>
  )
}

// What the news has said since each flagged move. Automatic for surprises; any other move on request.
export default function StoriesTab({ version, job, onCheckStarted, picked }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const pickedRef = useRef(null)

  useEffect(() => {
    let current = true
    getStories()
      .then((body) => {
        if (!current) return
        setData(body)
        setError(null)
      })
      .catch((e) => current && setError(e.message))
    return () => {
      current = false
    }
  }, [version])

  useEffect(() => {
    if (!picked?.date) return
    const timer = setTimeout(() => pickedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [picked?.date, picked?.ticker])

  const checks = data?.checks || []
  const isPicked = (date, ticker) => picked?.date === date && picked?.ticker === ticker
  const pickedChecks = picked?.date ? checks.filter((c) => isPicked(c.session_date, c.ticker)) : []
  const pickedMove = picked?.date
    ? (data?.unchecked || []).find((m) => isPicked(m.session_date, m.ticker)) || pickedChecks[0]?.move || null
    : null
  const maxCost = data ? `$${data.max_cost_usd.toFixed(2)}` : '$0.10'

  return (
    <>
      <section className="panel stories" aria-label="Story updates">
        <div className="section-head">
          <h2>Story updates</h2>
        </div>
        <p className="muted small">
          What the news has said since a flagged move. Moves that turn out to be surprises (reversed within a week, or kept
          going by as much again) are checked automatically after the next final report. Any other move can be checked here: each
          check costs a few cents (at most {maxCost}), and nothing if there are no newer headlines. For prices only, see{' '}
          <a href={routes.followThrough}>Follow-through</a>.
        </p>
        {error && <p className="error">{error}</p>}

        {picked?.date && data && (
          <div className="picked-move" ref={pickedRef} aria-label="Picked move">
            <h3>
              {picked.ticker}'s move of {formatFullDate(picked.date)}
            </h3>
            {pickedMove ? (
              <>
                {pickedMove.why && <p className="muted small">At the time: {pickedMove.why}</p>}
                <p className="muted small">{sinceLine(pickedMove)}</p>
              </>
            ) : null}
            {pickedChecks.length > 0 && <p className="small">Latest update below. You can check again for anything newer.</p>}
            <CheckButton
              sessionDate={picked.date}
              ticker={picked.ticker}
              job={job}
              onStarted={onCheckStarted}
              label={pickedChecks.length ? 'Check again' : 'Check for updates'}
            />
            {pickedChecks.slice(0, 1).map((c) => (
              <Check key={c.id} check={c} inPicked />
            ))}
          </div>
        )}

        <h3 className="stories-subhead">Latest updates</h3>
        {checks.length === 0 ? (
          <p className="muted">{data ? 'No story updates yet.' : 'Loading…'}</p>
        ) : (
          <div className="story-list">
            {checks.slice(0, 30).map((c) => (
              <Check key={c.id} check={c} />
            ))}
          </div>
        )}
      </section>

      <section className="panel" aria-label="Moves you can check">
        <div className="section-head">
          <h2>Moves you can check</h2>
          <span className="muted small">Flagged in the last {data?.days ?? 30} days, not checked yet</span>
        </div>
        {(data?.unchecked || []).length === 0 ? (
          <p className="muted">{data ? 'Every recent flagged move has been checked.' : 'Loading…'}</p>
        ) : (
          <ul className="check-list">
            {data.unchecked.map((m) => (
              <li key={`${m.session_date}-${m.ticker}`}>
                <div>
                  <MoveHeading move={m} sessionDate={m.session_date} ticker={m.ticker} />
                  {m.why && <p className="muted small">{m.why}</p>}
                </div>
                <CheckButton sessionDate={m.session_date} ticker={m.ticker} job={job} onStarted={onCheckStarted} />
              </li>
            ))}
          </ul>
        )}
      </section>
    </>
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
import FollowThroughTab from './components/FollowThroughTab'
import PreviousDaysPreview from './components/PreviousDaysPreview'
import PreviousDaysTab from './components/PreviousDaysTab'
import ReportView from './components/ReportView'
import RunPanel from './components/RunPanel'
import StocksTab from './components/StocksTab'
import StoriesTab from './components/StoriesTab'
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
  const [followVersion, setFollowVersion] = useState(0) // tells the Follow-through tab to reload
  const [refreshJob, setRefreshJob] = useState(null) // "Refresh prices" on the Follow-through tab
  const [storiesVersion, setStoriesVersion] = useState(0) // tells the Story updates tab to reload
  const [storyJob, setStoryJob] = useState(null) // "Check for updates" on the Story updates tab
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
    } else if (event.type === 'followups_refresh') {
      setRefreshJob(event.job)
      if (event.job.state !== 'running') setFollowVersion((v) => v + 1)
    } else if (event.type === 'followups_updated') {
      setFollowVersion((v) => v + 1) // after a final report, "Refresh prices", or another program
    } else if (event.type === 'story_check') {
      setStoryJob(event.job)
      if (event.job.state !== 'running') {
        setStoriesVersion((v) => v + 1)
        setFollowVersion((v) => v + 1) // the moves table links to each move's latest story
      }
    } else if (event.type === 'story_checked') {
      setStoriesVersion((v) => v + 1)
      setFollowVersion((v) => v + 1)
    }
  })

  // The live stream may have already moved the run on by the time the button's response arrives
  const onRunStarted = (started) =>
    setRun((current) => (current && current.started_at === started.started_at ? current : started))
  const onCalendarScanStarted = (started) =>
    setCalendarScan((current) => (current && current.started_at === started.started_at ? current : started))
  const onRefreshStarted = (started) =>
    setRefreshJob((current) => (current && current.started_at === started.started_at ? current : started))
  const onStoryCheckStarted = (started) =>
    setStoryJob((current) => (current && current.started_at === started.started_at ? current : started))

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
            {tabLink('followthrough', routes.followThrough, 'Follow-through')}
            {tabLink('stories', routes.stories(), 'Story updates')}
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

        <div hidden={route.tab !== 'followthrough'}>
          <FollowThroughTab
            version={followVersion}
            refresh={refreshJob}
            onRefreshStarted={onRefreshStarted}
            latestDate={latest?.session_date}
          />
        </div>

        <div hidden={route.tab !== 'stories'}>
          <StoriesTab
            version={storiesVersion}
            job={storyJob}
            onCheckStarted={onStoryCheckStarted}
            picked={route.tab === 'stories' ? { date: route.date, ticker: route.ticker } : null}
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
//   #/stocks                Every tracked stock, and finding new ones
//   #/follow-through        What the price did after each flagged move
//   #/stories               Story updates: what the news has said since
//   #/stories/2026-10-13/MSFT   ...with that move picked, ready to check
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date, ticker] = hash.replace(/^#/, '').split('/')
  if (tab === 'stocks') return { tab: 'stocks', date: null }
  if (tab === 'follow-through') return { tab: 'followthrough', date: null }
  if (tab === 'stories') {
    const picked = /^\d{4}-\d{2}-\d{2}$/.test(date || '') && /^[A-Za-z0-9.\-^=]{1,15}$/.test(ticker || '')
    return { tab: 'stories', date: picked ? date : null, ticker: picked ? decodeURIComponent(ticker).toUpperCase() : null }
  }
  if (tab !== 'previous' && tab !== 'calendar') return { tab: 'today', date: null }
  return { tab, date: /^\d{4}-\d{2}-\d{2}$/.test(date || '') ? date : null }
}

export const routes = {
  today: '#/',
  previous: (date) => (date ? `#/previous/${date}` : '#/previous'),
  calendar: (date) => (date ? `#/calendar/${date}` : '#/calendar'),
  stocks: '#/stocks',
  followThrough: '#/follow-through',
  stories: (date, ticker) => (date && ticker ? `#/stories/${date}/${encodeURIComponent(ticker)}` : '#/stories'),
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

// Follow-through: what the price did 1, 5 or 20 trading days after each flagged move
export const getFollowups = (horizon, ticker) =>
  request(`/api/followups?horizon=${horizon}${ticker ? `&ticker=${encodeURIComponent(ticker)}` : ''}`)
export const refreshFollowups = () => post('/api/followups/refresh', {}).then((body) => body.refresh)

// Story updates: what the news has said since a flagged move
export const getStories = (ticker) => request(`/api/stories${ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''}`)
export const checkStory = (sessionDate, ticker) =>
  post('/api/stories/check', { session_date: sessionDate, ticker }).then((body) => body.check)

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
  past_moves: () => 'Checking how past moves played out',
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

.tabs { display: flex; flex-wrap: wrap; gap: 4px; } /* six tabs: they wrap onto a second line on narrow screens */
.tab {
  color: var(--muted); text-decoration: none; font-weight: 600; font-size: 0.95rem;
  padding: 6px 12px; border-radius: 8px; white-space: nowrap;
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
.table-note a { color: var(--accent); }
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


/* Follow-through: held, faded and reversed, as one blue ramp (more of the move given back = more ink).
   Checked for contrast and step gaps in light and dark mode. */
:root { --held: #86b6ef; --faded: #2a78d6; --reversed: #104281; }
@media (prefers-color-scheme: dark) {
  :root { --held: #184f95; --faded: #3987e5; --reversed: #9ec5f4; }
}
.horizon-picker { display: flex; flex-wrap: wrap; gap: 6px; margin: 12px 0; }
.chip[aria-pressed="true"] { background: var(--accent); color: var(--accent-text); border-color: var(--accent); }
.outcome-legend { display: flex; flex-wrap: wrap; gap: 6px 18px; list-style: none; padding: 0; margin: 0 0 8px; font-size: 0.85rem; }
.outcome-legend li { display: flex; align-items: center; gap: 6px; }
.swatch { display: inline-block; width: 10px; height: 10px; border-radius: 2px; flex: none; }
.swatch.held, .seg.held { background: var(--held); }
.swatch.faded, .seg.faded { background: var(--faded); }
.swatch.reversed, .seg.reversed { background: var(--reversed); }
.patterns-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 4px 28px; }
.patterns h3 { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 14px 0 6px; }
.pattern-row { display: grid; grid-template-columns: minmax(0, 1fr); gap: 3px; margin-bottom: 10px; }
.pattern-label { font-size: 0.9rem; }
.outcome-bar { display: flex; gap: 2px; height: 12px; }
.outcome-bar.empty { background: var(--grid); border-radius: 0 4px 4px 0; }
.seg { position: relative; min-width: 4px; }
.seg:last-child { border-radius: 0 4px 4px 0; }
.seg:hover::after { content: attr(data-tip); position: absolute; bottom: 18px; left: 0; z-index: 5; white-space: nowrap;
  background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: 4px 8px;
  font-size: 0.8rem; box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12); pointer-events: none; }
.too-few { font-style: italic; }
.patterns-all { max-width: 640px; margin-top: 4px; }
.patterns-all .pattern-label { font-weight: 600; }
.followthrough a, .moves a, .stories a { color: var(--accent); }
.moves-filters { display: flex; flex-wrap: wrap; gap: 8px 16px; align-items: center; }
.moves-filters select { margin-left: 4px; }
.outcome { display: inline-flex; align-items: center; gap: 6px; white-space: nowrap; }
.surprise { color: var(--live); font-weight: 600; }
.story-link { color: var(--accent); white-space: nowrap; }

/* Story updates */
.stories-subhead { font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); margin: 18px 0 8px; }
.story-list { display: grid; gap: 12px; }
.story { border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; background: var(--panel); }
.story header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px 12px; align-items: baseline; }
.story-head { display: flex; flex-wrap: wrap; gap: 4px 8px; align-items: baseline; }
.story-update { margin: 8px 0; }
.story-sources { margin: 0 0 8px; padding-left: 18px; font-size: 0.9rem; }
.story-sources a { color: var(--accent); }
.verdict { font-size: 0.78rem; font-weight: 600; padding: 2px 8px; border-radius: 999px; border: 1px solid var(--border); color: var(--text); white-space: nowrap; }
.verdict.failed { color: var(--down); }
.picked-move { border: 2px solid var(--accent); border-radius: var(--radius); padding: 12px 14px; margin: 12px 0 4px; scroll-margin-top: 12px; }
.picked-move h3 { margin: 0 0 6px; font-size: 1rem; }
.check-action { display: flex; flex-wrap: wrap; gap: 6px 12px; align-items: center; margin: 8px 0; }
.check-list { list-style: none; padding: 0; margin: 0; }
.check-list li { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 8px 16px; align-items: center;
  padding: 10px 0; border-bottom: 1px solid var(--border); }
.check-list li > div { min-width: 0; flex: 1 1 260px; }
.check-list p { margin: 4px 0 0; }
```

### tests/conftest.py

```python
"""Shared test setup: tests never reach real services, whatever is set in your terminal.

Without this, running pytest in a terminal where DISCORD_WEBHOOK_URL is set would post
test alerts to your real Discord channel (and VOYAGE_API_KEY would send test text to Voyage).
Tests that need these set them themselves.

A run that saves a final report also follows up on earlier flagged moves, which downloads
prices from Yahoo and can ask Claude about surprises. Tests skip that step, except the ones
in test_followups.py, which fake Yahoo and Claude themselves.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    for name in ("DISCORD_WEBHOOK_URL", "VOYAGE_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_follow_up_after_runs(request, monkeypatch):
    if request.module.__name__.endswith("test_followups"):
        return
    import stories
    monkeypatch.setattr(stories, "after_final_report", lambda emit=None: {"followups": None, "checks": [], "problems": []})
```

### tests/test_followups.py

```python
"""Offline tests for follow-through (the price after each flagged move) and story updates (the
news since). Yahoo Finance and Claude are faked.

Run from the project folder:
    pytest -v tests/test_followups.py
"""

import asyncio
import json
import sys
import time
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import events  # noqa: E402
import followups  # noqa: E402
import market_tools  # noqa: E402
import prices  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
import stories  # noqa: E402
from claude_agent_sdk import ResultMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# Trading days (weekdays) from September to December 2026
DAYS = [date(2026, 9, 1) + timedelta(days=i) for i in range(120) if (date(2026, 9, 1) + timedelta(days=i)).weekday() < 5]
D0 = date(2026, 10, 1)  # the flagged day
I0 = DAYS.index(D0)
PRICES = {}             # ticker -> {day: close}
CLAUDE = []             # every prompt the fake Claude was sent
NEWS = {}               # ticker -> headlines the fake Yahoo returns


def path(ticker, base, moves):
    """Closes: `base` until the flagged day, then the given closes from D0 onwards."""
    closes = {d: base for d in DAYS[:I0]}
    closes.update({DAYS[I0 + i]: c for i, c in enumerate(moves)})
    last = moves[-1]
    closes.update({d: last for d in DAYS[I0 + len(moves):]})
    PRICES[ticker] = closes


def body(*sections):
    lines = ["# Watchlist brief", "", "## Notable moves", ""]
    for ticker, why in sections:
        lines += [f"### {ticker}: +1.00% (z-score 3, volume 2x normal)", "- **What happened:** it moved.",
                  f"- **Likely why:** {why}", "- **Worth watching:** more.", ""]
    return "\n".join(lines + ["## Quiet", "", "AAPL (+0.10%)"])


def save(day, status, flagged, why=None, sources=()):
    """A report for `day` with these flagged moves: [(ticker, move %, kind)]."""
    scan = {"session": {"status": "complete", "as_of": day.isoformat()},
            "flagged": [{"ticker": t, "last_close": 100.0, "return_1d_pct": m, "return_zscore": 3.0, "volume_vs_avg": 2.0,
                         "context": {"read": k, "benchmark": "XLK", "summary": "..."}} for t, m, k in flagged],
            "quiet": [{"ticker": "AAPL", "last_close": 190.0, "return_1d_pct": 0.1}], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date=day.isoformat(), status=status, title="Brief",
                               body_md=body(*[(t, (why or {}).get(t, "No clear catalyst found.")) for t, _, _ in flagged]),
                               as_of=day.isoformat(), scan=scan, sources=list(sources))


def fake_claude(reply):
    def ask_claude(prompt):
        CLAUDE.append(prompt)
        if isinstance(reply, Exception):
            raise reply
        return (reply if isinstance(reply, str) else json.dumps(reply)), 0.012
    return ask_claude


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A temporary database, a fixed 'latest close', fake Yahoo prices and news, and fake Claude."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    PRICES.clear()
    CLAUDE.clear()
    NEWS.clear()
    path("NVDA", 100.0, [110.0, 111.0, 109.0, 106.0, 105.0, 104.5] + [100.0] * 20)  # +10%, then faded, then reversed
    path("MSFT", 200.0, [190.0, 189.0, 186.0, 184.0, 182.0, 180.0])                # -5%, then kept going down
    clock = {"last": DAYS[I0 + 25]}
    monkeypatch.setattr(followups, "last_complete_session", lambda: clock["last"])
    monkeypatch.setattr(prices, "fetch_prices", lambda t, period: [
        {"date": d.isoformat(), "close": c, "volume": 1000} for d, c in sorted(PRICES[t].items())])
    monkeypatch.setattr(stories, "fetch_news", lambda t: NEWS.get(t, []))
    monkeypatch.setattr(stories, "ask_claude", fake_claude({"verdict": "developed", "update": "On Oct 5 it said more.",
                                                             "sources": [1]}))
    monkeypatch.setattr(events, "company_name", lambda t: {"NVDA": "NVIDIA", "MSFT": "Microsoft"}.get(t, t))
    reports_db.connect().close()
    return clock


def rows(conn=None):
    with closing(reports_db.connect(readonly=True)) as c:
        return {r["ticker"]: dict(r) for r in c.execute("SELECT * FROM followups WHERE session_date = ?", (D0.isoformat(),))}


# ---------------------------------------------------------------------------
# Judging a move
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move, after, expected", [
    (10, 3.0, "held"),        # kept going
    (10, -2.0, "held"),       # gave back 22% of the move
    (10, -5.0, "faded"),      # gave back 55%
    (10, -9.1, "reversed"),   # back below where it started
    (-10, 5.0, "faded"),
    (-10, 11.2, "reversed"),
    (4, None, None),          # not known yet
])
def test_judging_a_move(move, after, expected):
    assert followups.outcome(move, after) == expected


def test_surprises_are_reversals_or_doubling_within_a_week():
    assert followups.is_surprise(10, -9.1) and followups.surprise_kind(10, -9.1) == "reversed within a week"
    assert followups.is_surprise(-5, -5.3)  # down 5%, then as much again
    assert followups.surprise_kind(-5, -5.3) == "kept going: as much again within a week"
    assert not followups.is_surprise(10, -5.0) and not followups.is_surprise(10, None)
    assert followups.follow(-5, -5.3) == 5.3  # counted in the move's direction


# ---------------------------------------------------------------------------
# Finding the moves and filling in prices
# ---------------------------------------------------------------------------

def test_follow_ups_come_from_final_reports_only(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")],
         why={"NVDA": "Quarterly results beat estimates. [Reuters](https://x.example)"})
    save(DAYS[I0 + 26], "intraday", [("NVDA", 4.0, "stock-specific")])  # today's flags aren't followed up yet

    result = followups.update()

    found = rows()
    assert result["added"] == 2 and set(found) == {"NVDA", "MSFT"}
    assert found["NVDA"]["reason"] == "earnings" and found["NVDA"]["why"] == "Quarterly results beat estimates. Reuters"
    assert found["MSFT"]["reason"] == "none" and found["MSFT"]["move_read"] == "market-wide"
    with closing(reports_db.connect(readonly=True)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM followups").fetchone()[0] == 2


def test_earnings_on_the_calendar_count_as_the_reason(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")], why={"NVDA": "No clear catalyst found."})
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, first_seen, last_seen)
                        VALUES (?, 'NVDA', 'NVIDIA', 'earnings', 'Earnings report', '2026-09-01', '2026-09-01')""",
                     ((D0 - timedelta(days=1)).isoformat(),))
    followups.update()
    assert rows()["NVDA"]["reason"] == "earnings"  # reported the evening before


def test_prices_fill_in_as_days_pass(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    db["last"] = DAYS[I0 + 3]  # three closes since the move

    followups.update()
    first = rows()["NVDA"]
    db["last"] = DAYS[I0 + 25]
    second = followups.update()
    settled = rows()["NVDA"]
    again = followups.update()

    assert first["after_1d"] == 0.91 and first["after_5d"] is None and first["after_20d"] is None
    assert settled["after_5d"] == -5.0 and settled["after_20d"] == -9.09
    assert followups.outcome(10, settled["after_5d"]) == "faded" and followups.outcome(10, settled["after_20d"]) == "reversed"
    assert second["updated"] == 1 and again["updated"] == 0  # settled moves aren't downloaded again


def test_todays_unfinished_price_is_never_used(monkeypatch):
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    assert followups.last_complete_session() == date(2026, 11, 5)
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "complete", "as_of": "2026-11-06"})
    assert followups.last_complete_session() == date(2026, 11, 6)


def test_a_price_problem_for_one_stock_doesnt_stop_the_rest(db, monkeypatch):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")])
    real = prices.fetch_prices
    monkeypatch.setattr(prices, "fetch_prices", lambda t, p: (_ for _ in ()).throw(ConnectionError("rate limited"))
                        if t == "NVDA" else real(t, p))
    result = followups.update()
    assert result["status"] == "partial" and "NVDA: rate limited" in result["message"]
    assert rows()["MSFT"]["after_5d"] == -5.26 and rows()["NVDA"]["after_5d"] is None


def test_patterns_group_the_moves(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    followups.update()
    with closing(reports_db.connect(readonly=True)) as conn:
        result = followups.patterns(followups.moves(conn), 5)
    assert result["all"]["judged"] == 2 and (result["all"]["held"], result["all"]["faded"]) == (1, 1)
    assert [g["label"] for g in result["by_kind"]] == ["Stock-specific"]
    assert [g["label"] for g in result["by_direction"]] == ["Up moves", "Down moves"]
    assert not result["all"]["enough"]  # 2 moves: too few to tell
    assert followups.describe_group(result["all"], 5) == \
        "All flagged moves: 1 of 2 held a week later, 1 faded, 0 reversed (too few to tell)"


def test_past_moves_tool_for_the_brief(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    followups.update()

    result = market_tools.past_moves(["nvda"], ["stock-specific"])

    nvda = result["moves"]["NVDA"]
    assert result["horizon_days"] == 5 and nvda["this_stock"]["judged"] == 1
    assert nvda["same_kind"]["judged"] == 2 and nvda["last_move"]["outcome"] == "faded"
    assert nvda["summary"].startswith("NVDA's flagged moves: 0 of 1 held a week later, 1 faded")
    assert nvda["worth_mentioning"] is False  # too few to mention in a brief


def test_past_moves_without_any_history(db):
    assert market_tools.past_moves(["NVDA"])["note"].startswith("Follow-through hasn't been worked out yet")


# ---------------------------------------------------------------------------
# Story updates
# ---------------------------------------------------------------------------

def test_no_newer_headlines_means_no_claude_and_no_cost(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    followups.update()
    NEWS["NVDA"] = [{"title": "On the day", "publisher": "Wire", "published": f"{D0}T13:00:00Z", "url": "https://a.example"}]

    check = stories.check(D0.isoformat(), "NVDA")

    assert check["status"] == "no_news" and check["cost_usd"] == 0 and CLAUDE == []
    assert check["update_text"] == "No newer headlines about NVIDIA since 2026-10-01."


def test_a_check_reads_only_newer_headlines(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")], why={"NVDA": "A product launch."},
         sources=[{"ticker": "NVDA", "title": "NVIDIA unveils chip", "publisher": "Wire", "url": "https://a.example"}])
    followups.update()
    NEWS["NVDA"] = [
        {"title": "Chip reviews arrive", "publisher": "Daily", "published": "2026-10-05T12:00:00Z", "url": "https://b.example"},
        {"title": "Same-day story", "publisher": "Wire", "published": f"{D0}T15:00:00Z", "url": "https://c.example"},
        {"title": "Older story", "publisher": "Wire", "published": 1790000000, "url": "https://d.example"},  # Sep 2026, as seconds
    ]

    check = stories.check(D0.isoformat(), "nvda", emit=lambda e: None)

    assert check["status"] == "ok" and check["verdict"] == "developed" and check["cost_usd"] == 0.012
    assert check["sources"] == [{"title": "Chip reviews arrive", "publisher": "Daily", "url": "https://b.example",
                                 "published": "2026-10-05T12:00:00Z"}]
    prompt = CLAUDE[0]
    assert "EXPLANATION AT THE TIME: A product launch." in prompt and "- NVIDIA unveils chip (Wire)" in prompt
    assert "PRICE SINCE: next day: +0.91%, after a week: -5.00%, after a month: -9.09%" in prompt
    assert "Chip reviews arrive" in prompt and "Same-day story" not in prompt and "Older story" not in prompt


@pytest.mark.parametrize("reply, error", [
    ("Sorry, I can't.", "no JSON"),
    ({"verdict": "maybe", "update": "x", "sources": [1]}, "unknown verdict"),
    ({"verdict": "developed", "update": "x", "sources": [7]}, "cited none of the newer headlines"),
    (RuntimeError("error_max_budget_usd"), "error_max_budget_usd"),
])
def test_a_bad_reply_is_saved_as_a_failed_check(db, monkeypatch, reply, error):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    followups.update()
    NEWS["NVDA"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    monkeypatch.setattr(stories, "ask_claude", fake_claude(reply))
    check = stories.check(D0.isoformat(), "NVDA")
    assert check["status"] == "failed" and error in check["error"]


def test_only_flagged_moves_can_be_checked(db):
    with pytest.raises(stories.StoryError, match="wasn't flagged") as missing:
        stories.check("2026-10-02", "NVDA")
    assert missing.value.status == 404


def test_surprises_are_checked_once_after_a_final_report(db):
    db["last"] = DAYS[I0 + 10]  # two weeks after the move
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    progress = []

    first = stories.after_final_report(progress.append)
    second = stories.after_final_report(progress.append)

    assert first["followups"]["new_surprises"] == 1  # MSFT fell as much again within a week
    assert [(c["ticker"], c["trigger"], c["status"]) for c in first["checks"]] == [("MSFT", "surprise", "ok")]
    assert second["checks"] == []  # checked once only
    messages = [e["message"] for e in progress]
    assert "Follow-through: 2 new moves, 2 updated, 1 new surprise" in messages
    assert "Story updates: checked 1 surprise · $0.012" in messages


def test_older_surprises_are_left_to_check_by_hand(db):
    save(D0, "final", [("MSFT", -5.0, "stock-specific")])  # 5 weeks before the latest close
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]

    result = stories.after_final_report()

    assert result["followups"]["new_surprises"] == 1 and result["checks"] == []
    assert CLAUDE == []  # no money spent on old news
    assert stories.check(D0.isoformat(), "MSFT")["status"] == "ok"  # it can still be checked on request
    assert stories.check_surprises(within_days=60)[0]["trigger"] == "surprise"


def test_after_final_report_never_breaks_the_run(db, monkeypatch):
    monkeypatch.setattr(followups, "update", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    progress = []
    result = stories.after_final_report(progress.append)
    assert result["problems"] == ["follow-through: disk full"]
    assert progress[-1]["type"] == "warning" and "disk full" in progress[-1]["message"]


def test_a_final_run_follows_up_and_an_intraday_run_doesnt(db, monkeypatch):
    calls = []
    monkeypatch.setattr(stories, "after_final_report", lambda emit=None: calls.append(1))
    monkeypatch.setattr(run_brief, "send_alerts", lambda *a, **k: asyncio.sleep(0))
    monkeypatch.setattr(run_brief.search_index, "sync", lambda *a, **k: None)
    scan = {"flagged": [], "quiet": [{"ticker": "AAPL", "last_close": 1.0, "return_1d_pct": 0.1}], "errors": []}

    async def fake_query(*, prompt, options):
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
                            session_id="s", total_cost_usd=0.01, result="# Brief\n\nNothing unusual.")

    monkeypatch.setattr(run_brief, "query", fake_query)
    for session in ({"status": "in_progress", "as_of": "2026-11-06 11:30 ET"}, {"status": "complete", "as_of": "2026-11-06"}):
        monkeypatch.setattr(run_brief, "market_session", lambda s=session: s)
        monkeypatch.setattr(run_brief, "flag_events", lambda s=session: {**scan, "session": s})
        asyncio.run(run_brief.run_once())
    assert calls == [1]  # once, after the final report


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

def test_ask_sees_follow_through_and_story_updates(db):
    db["last"] = DAYS[I0 + 10]
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    stories.after_final_report()

    with closing(reports_db.connect(readonly=True)) as conn:
        named = ask.followup_section(conn, ["MSFT"])
        general = ask.followup_section(conn, [])
        context, _ = ask.build_context(conn, "What happened after MSFT dropped?")

    assert named in context  # Claude is actually given it

    assert "## Follow-through for MSFT" in named and "2026-10-01 | -5.00 | Stock-specific | No clear reason |" in named
    assert "| held" in named
    assert "## Story updates for MSFT" in named and "Developed. On Oct 5 it said more. Sources: Daily: Later" in named
    assert "All flagged moves: 1 of 2 held a week later" in general
    assert "(follow-through)" in ask.SYSTEM_PROMPT and "(story update" in ask.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "followup_refreshes", api.BackgroundJob(
        "followups_refresh", lambda: 60, "busy", "Prices were just refreshed. Try again in {}."))
    monkeypatch.setattr(api, "story_checks", api.BackgroundJob(
        "story_check", lambda: 60, "busy", "A story was just checked. Try again in {}."))
    monkeypatch.setattr(events, "today_et", lambda: D0 + timedelta(days=20))  # moves of the last 30 days can be checked
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")])
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_refresh_and_follow_through(client):
    assert client.get("/api/followups").json()["moves"] == []  # nothing worked out yet

    started = client.post("/api/followups/refresh", json={})
    assert started.status_code == 202 and started.json()["refresh"]["state"] == "running"
    wait_for(lambda: client.get("/api/followups").json()["refresh"]["state"] == "finished")
    assert client.post("/api/followups/refresh", json={}).status_code == 429  # cooldown

    view = client.get("/api/followups?horizon=20").json()
    assert view["horizon"] == 20 and view["horizons"] == [1, 5, 20] and view["tickers"] == ["MSFT", "NVDA"]
    nvda = next(m for m in view["moves"] if m["ticker"] == "NVDA")
    assert nvda["outcomes"] == {"1": "held", "5": "faded", "20": "reversed"} and nvda["settled"]
    assert view["patterns"]["horizon"] == 20 and view["updated"]["trigger"] == "manual"
    only = client.get("/api/followups?ticker=msft").json()
    assert [m["ticker"] for m in only["moves"]] == ["MSFT"] and only["patterns"]["all"]["moves"] == 2
    assert client.get("/api/followups?horizon=7").status_code == 400


def test_api_story_check(client):
    followups.update()
    NEWS["NVDA"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    queue = api.hub.subscribe()
    before = client.get("/api/stories").json()
    assert [m["ticker"] for m in before["unchecked"]] == ["MSFT", "NVDA"] and before["max_cost_usd"] == 0.1

    started = client.post("/api/stories/check", json={"session_date": D0.isoformat(), "ticker": "nvda"})
    assert started.status_code == 202 and started.json()["check"]["target"] == {"session_date": "2026-10-01", "ticker": "NVDA"}
    done = wait_for(lambda: (c := client.get("/api/stories").json())["check"]["state"] == "finished" and c)

    assert done["checks"][0]["ticker"] == "NVDA" and done["checks"][0]["verdict_label"] == "Developed"
    assert done["checks"][0]["move"]["outcomes"]["5"] == "faded"
    assert [m["ticker"] for m in done["unchecked"]] == ["MSFT"]
    assert next(m for m in client.get("/api/followups").json()["moves"] if m["ticker"] == "NVDA")["story"]["verdict"] == "developed"
    kinds = []
    while not queue.empty():
        kinds.append(queue.get_nowait()["type"])
    assert kinds.count("story_check") >= 2  # started, progress, finished
    assert client.post("/api/stories/check", json={"session_date": D0.isoformat(), "ticker": "MSFT"}).status_code == 429


@pytest.mark.parametrize("body, status, message", [
    ({"session_date": "2026-10-02", "ticker": "NVDA"}, 404, "wasn't flagged"),
    ({"session_date": "Oct 1", "ticker": "NVDA"}, 400, "send JSON like"),
    ({"ticker": "NVDA"}, 400, "send JSON like"),
])
def test_api_story_check_explains_what_went_wrong(client, body, status, message):
    followups.update()
    response = client.post("/api/stories/check", json=body)
    assert response.status_code == status and message in response.json()["error"]


def test_other_websites_cannot_start_checks(client):
    for path, body in (("/api/followups/refresh", {}), ("/api/stories/check", {"session_date": "2026-10-01", "ticker": "NVDA"})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert CLAUDE == []


def test_updates_from_scheduled_runs_reach_open_pages(db, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())
    db["last"] = DAYS[I0 + 10]
    save(D0, "final", [("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        await asyncio.to_thread(stories.after_final_report)  # what another program (a scheduled run) does
        seen = set()
        deadline = time.monotonic() + 3
        while not {"followups_updated", "story_checked"} <= seen and time.monotonic() < deadline:
            try:
                seen.add((await asyncio.wait_for(queue.get(), 0.5))["type"])
            except asyncio.TimeoutError:
                pass
        watcher.cancel()
        return seen

    assert {"followups_updated", "story_checked"} <= asyncio.run(scenario())
```
