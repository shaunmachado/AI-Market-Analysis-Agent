# Market Analyst Agent: Company Filings and First Takes

Until now, every "why" in the app came from news headlines. This guide adds the companies' own words: what each tracked company files with the SEC, and a **first take** on it, minutes after it's filed.

| Part | What it does | Cost |
|---|---|---|
| **Filings tab (new)** | Lists each tracked company's results announcements, other announcements, and quarterly and annual reports. Serious ones (an executive leaving, a restatement, a late report) are marked "Worth a look" | Free (the SEC's EDGAR service) |
| **First takes** | Claude reads a filing and writes a headline, the key points, the reported figures, guidance, and what changed since the last announcement. Every point carries a quote that's checked against the filing in code | A few cents a filing (estimated, not measured here) |
| **Figures** | Each reported figure is compared with the quarter before and a year earlier, in code, from the SEC's structured data. When the quarterly report arrives, each figure is marked **confirmed** or **different** | Free |
| **Calendar** | An earnings date says "Reported" once the results are filed, with a link to the first take, even if Yahoo's date was a day or two out | Free |
| **Briefs, Ask, Discord** | A brief explains a flagged move from the company's own filing when there is one. Ask can answer from first takes. Discord gets a message for each results first take and each serious announcement | A little more per run and per question |

**What's automatic:** a new results announcement is read as soon as a check finds it. Every other filing is listed, with a **Read this filing** button.

**A correction to the plan.** Before building this, I said the figures would come from the SEC's structured data. That's true for earlier quarters, but the SEC only has structured figures for the *new* quarter once the quarterly report is filed, which can be days after the announcement. So:

1. Claude copies each new figure from the announcement, exactly as written, with the table row it came from.
2. Code checks the number is really in that row, and that the row is really in the filing.
3. Code works out every comparison from the SEC's data.
4. When the report arrives, code checks each figure against it.

This builds on `market-agent-followups.md`, and this guide's files include every earlier change.

---

## Contents

1. [What it looks like](#1-what-it-looks-like)
2. [How it works](#2-how-it-works)
3. [What Claude does, and what code checks](#3-what-claude-does-and-what-code-checks)
4. [Which filings are followed](#4-which-filings-are-followed)
5. [Before you start](#5-before-you-start)
6. [Step 1: Add edgar.py and filings.py](#6-step-1-add-edgarpy-and-filingspy)
7. [Step 2: Connect them to runs, briefs and Ask](#7-step-2-connect-them-to-runs-briefs-and-ask)
8. [Step 3: Add the API endpoints](#8-step-3-add-the-api-endpoints)
9. [Step 4: Add the Filings tab](#9-step-4-add-the-filings-tab)
10. [Step 5: Add the tests](#10-step-5-add-the-tests)
11. [Step 6: Try it](#11-step-6-try-it)
12. [Test it](#12-test-it)
13. [From the terminal](#13-from-the-terminal)
14. [Settings](#14-settings)
15. [Costs](#15-costs)
16. [Security and privacy](#16-security-and-privacy)
17. [What it doesn't do](#17-what-it-doesnt-do)
18. [Troubleshooting](#18-troubleshooting)
19. [Appendix: full source code](#appendix-full-source-code)

---

## 1. What it looks like

These examples are from the test environment, so the companies' figures and filings are simulated. Screenshots are in `filings-preview.png`.

**The Filings tab:**

```
COMPANY FILINGS                                                  Checked Nov 6, 12:31 PM  [Check now]
What your tracked companies file with the SEC: results, other announcements, and quarterly and annual
reports. Looking for filings is free. A new results announcement is read by Claude automatically; any
other filing has a "Read this filing" button (a few cents, at most $0.50). …

Stock [All ▾]   [All] [Results] [Announcements] [Reports]   ☐ Only with a first take

┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ AMZN  Results announcement                                                              [Results] │
│ Filed Nov 4, 7:05 AM · form 8-K · the filing on sec.gov                                           │
│ Amazon.com reported revenue of $46.2 billion, up 20% from the same quarter a year earlier.        │
│                                                                                                    │
│ Figures as announced · quarter to Sep 30                                                           │
│ Figure             Reported   Quarter before  Change   A year earlier  Change   Checked against…  │
│ Revenue             $46.19B          $43.33B   +6.6%          $38.39B  +20.3%   Not checked yet   │
│ Operating income    $12.10B          $10.83B  +11.7%           $9.60B  +26.1%   Not checked yet   │
│ Earnings per share    $0.41            $0.37  +10.8%            $0.33  +24.2%   Not checked yet   │
│ Gross margin 43.0% (43.0% a year earlier) · Operating margin 26.2% (25.0% a year earlier) · …     │
│                                                                                                    │
│ KEY POINTS                                                                                         │
│ • Revenue was $46.2 billion, up 20% from the same quarter a year earlier.                          │
│   ▸ From the filing                                                                                │
│ GUIDANCE                                                                                           │
│ • (Raised) The company raised its revenue outlook for the full year.                               │
│ WHAT CHANGED SINCE THE LAST ANNOUNCEMENT                                                           │
│ • The outlook changed: last quarter the company reaffirmed it, and this quarter it raised it.      │
│ First take by Claude, Nov 4, 5:00 PM · automatically · read from amzn-ex991.htm    [Read again]    │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
┌────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ NVDA  Directors or senior officers leaving or appointed          [Worth a look]  [Announcement]   │
│ Filed Oct 26, 8:00 AM · form 8-K · the filing on sec.gov                                          │
│ [Read this filing]                                                                                 │
└────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

- **From the filing** opens the exact words a point is based on. Hovering a figure's name shows the table row it was copied from.
- **Checked against the report** changes from "Not checked yet" to **✓ Confirmed** once the quarterly report is filed, or to **✗ The report says $X** if it differs.
- A **quarterly or annual report** has its own figures, straight from the SEC's data, folded under "Figures from the report".
- A **ticker** opens its chart. A filing's **title** gives a link to that filing, to bookmark or share (`#/filings/0001234567-26-000123`).
- If the calendar expected results in the last few days and nothing has been filed, a line at the top says so.

**The calendar,** on an earnings day. Here the company reported the evening before the date Yahoo gave:

```
JPMorgan Chase  JPM  (Earnings)
Earnings report
┌──────────────────────────────────────────────────────────────────────────────────────────────┐
│ Reported on Sep 16: JPMorgan Chase reported revenue of $29.9 billion, up 14% from the same   │
│ quarter a year earlier. First take                                                            │
└──────────────────────────────────────────────────────────────────────────────────────────────┘
```

The day it was actually filed (Sep 16) shows the company too. On the Today tab, the **Coming up** card says "Reported: first take ready" for an earnings event that's been filed, and links to it.

**In a brief,** when a flagged company has filed something:

```
- **Likely why:** A new product announcement drew buyers. [Sample Wire](…) The company also filed with
  the SEC: information shared with investors ([company filing](…)).
```

With a first take, the real agent leads with the company's own announcement, then adds how the news received it.

**The run log** now starts with the filings check:

```
Reading Microsoft's results announcement
First take on MSFT: Microsoft reported revenue of $43.1 billion, up 17% from the same quarter a year earlier.
Filings: 1 new: MSFT (results announcement)
Discord: sent MSFT results
Writing the final report for 2026-10-13
Checking company filings
…
```

**On Discord:**

```
MSFT reported results
Microsoft: results
Microsoft reported revenue of $43.1 billion, up 17% from the same quarter a year earlier.
• Revenue $43.09B (+17.5% vs a year ago)
• Gross profit $18.53B (+17.5% vs a year ago)
• Operating income $8.71B (+24.9% vs a year ago)
• Net income $7.05B (+24.9% vs a year ago)
• Earnings per share (diluted) $1.36 (+24.8% vs a year ago)
Guidance (raised): The company raised its revenue outlook for the full year.
The filing on sec.gov
From the company's SEC filing · research, not investment advice
```

---

## 2. How it works

```
Each run of run_brief.py (first thing), "Check now" on the Filings tab, or: python filings.py check
  └─▶ filings.check()
        1. The SEC's list of each tracked company's filings ─▶ new ones saved in the filings table      free
        2. Each new results announcement from the last 3 days ─▶ filings.read()       a few cents, at most 5
        3. Each recent quarterly or annual report ─▶ its figures from the SEC's structured data         free
             └─▶ the matching results announcement's figures: confirmed, or different
        4. Discord: one message per results first take, and per serious announcement

filings.read(one filing)
  the press release (results), the filing's own text (announcements), or management's discussion (reports)
    ─▶ plain text, at most 60,000 characters ─▶ one Claude request, no tools ─▶ JSON
    ─▶ every quote checked against the text; every figure's number checked against its quote
    ─▶ comparisons worked out in code ─▶ filing_reads table

Filings tab ─── GET /api/filings ─── [Check now] ─▶ POST /api/filings/check
                                      [Read this filing] ─▶ POST /api/filings/read
Calendar ────── GET /api/calendar now includes "reported": results filed, matched to earnings events
The agent ───── recent_filings tool ── "Likely why" from the company's own filing
Ask ─────────── filings and first takes for the stocks you name
```

- **Where filings come from.** The SEC's EDGAR service, directly: no key, no account and no charge. The SEC asks automated tools to say who they are, so you set `SEC_CONTACT` to your name and email (step 5). The app stays far under the SEC's limit of 10 requests a second.
- **A run checks first.** Every run of `run_brief.py` starts by looking for new filings, so the brief can use them. This happens even when the day's final report is already saved, because results often arrive after the close. It adds about one request per tracked company, a few seconds in all.
- **Only fresh results are read automatically.** A results announcement is read if it was filed in the last 3 days, and at most 5 are read per check. So the first check after you add this lists your companies' last four months of filings for free, without reading old ones.
- **Your reports are never changed.** Filings live in five new tables in `reports.db` (`filers`, `filings`, `filing_reads`, `filing_checks`, `filing_alerts`). Like your reports, you can read them yourself (section 13).
- **Two share classes are one company.** If you track both GOOG and GOOGL, the SEC is asked once, the announcement is read once, and it shows under both tickers.
- **Funds have no company filings.** An ETF such as SPY isn't on the SEC's company list. It's skipped, and the tab says so in one line.
- **Problems never stop a run.** If the SEC can't be reached, or `SEC_CONTACT` isn't set, the run log gets one warning and the run carries on. If the SEC is down, a check gives up after two companies in a row can't be reached, so a run isn't held up for long.
- **One company failing doesn't stop the rest.** The check says `partial` and names it.
- **Live.** New filings and first takes reach open pages within a few seconds, whichever program found them.

---

## 3. What Claude does, and what code checks

| Part | Who | How it's kept honest |
|---|---|---|
| Finding filings and naming them | Code | Straight from the SEC's lists |
| Headline, key points, guidance, what changed | Claude | Every point must quote the filing. Code looks for the quote in the filing's text; if it isn't there, the point is dropped and a note says how many were |
| The quarter's figures | Claude copies, code calculates | Claude gives the number as written ("77,673") and the scale ("millions"). Code checks the number is in the quoted row, checks the row is in the filing, and does the multiplication |
| "Vs. the quarter before" and "vs. a year earlier" | Code | From the SEC's structured data for those quarters. Claude never works out a percentage |
| Margins | Code | Profit divided by revenue, for each period |
| Confirmed or different | Code | When the quarterly or annual report is filed, its structured figure is compared with the announced one |

**Extra checks on figures:**

- **Wrong unit.** If a figure is more than 20 times, or less than a 20th of, the same figure in an earlier quarter, the unit was probably misread (thousands for millions). It's left out, with a note.
- **Earnings per share** is always in dollars, whatever scale Claude gives.
- **Standard figures only.** Claude is told to use the standard (GAAP) figure for the three months, not an "adjusted" one or the year to date. Code can't check that at the time. The later comparison with the report can, and a mismatch shows as "The report says…".
- **No percentage from a loss.** A change from a negative or zero figure is shown as "—", because the percentage would mislead.

**Fourth quarters.** Annual reports give the year, not the last quarter on its own. So a fourth quarter is worked out as the year minus the first nine months. These show with "≈" in the tab. Revenue and profit worked out this way are exact. Earnings per share isn't (the share count changes during the year), so a fourth-quarter EPS is marked "Can't be checked" instead of confirmed.

**Rounding.** Announcements round, to the million in a table or to a tenth of a billion in a sentence. A figure counts as confirmed if it's within 0.6% of the report's (or $600,000 for small figures). Earnings per share must match to the cent.

**If Claude's reply can't be trusted at all** (no JSON, no headline, or no point with a real quote), the read is saved as failed, with the reason and the cost, and nothing from it is shown.

---

## 4. Which filings are followed

| The SEC's form | Shown as | Read automatically? |
|---|---|---|
| 8-K with item 2.02 | **Results announcement** | Yes, if filed in the last 3 days |
| 8-K, other items | The items in plain words, for example "Directors or senior officers leaving or appointed" | No: button |
| 10-Q | Quarterly report | No: button. Its figures are fetched for free |
| 10-K | Annual report | No: button. Its figures are fetched for free |
| NT 10-Q, NT 10-K | "Says its quarterly (or annual) report will be late" | No: the title says it all |
| 6-K, 20-F, 40-F | Reports from companies based outside the US | No: button |
| Any of these with "/A" | "Amended: …" | No: button |

Other forms (insider trades, prospectuses, proxy statements and so on) aren't listed.

**"Worth a look"** marks an announcement with any of these, and each also gets a Discord message (without Claude):

- bankruptcy
- a serious cybersecurity incident
- an acquisition or sale completed
- a debt brought due early
- restructuring or closures
- a large write-down
- a warning about staying listed
- a change of auditor
- earlier financial statements that can no longer be relied on
- a change of control
- directors or senior officers leaving or appointed
- any notice that a report will be late

**What Claude is given:**

| Filing | Text read |
|---|---|
| Results | The press release attached to the filing (the first "EX-99" exhibit), plus the previous results announcement for comparison |
| Other announcements | The filing's own text, then its press release if it has one |
| Quarterly and annual reports | Management's discussion of the results (Item 2 of a 10-Q, Item 7 of a 10-K). If it can't be found, the start of the report, with a note |

At most 60,000 characters are read (about 15,000 tokens). A longer document is cut off, and the first take says so.

---

## 5. Before you start

- [ ] You've done `market-agent-followups.md`, and `pytest` shows `276 passed, 3 skipped`.
- [ ] `ANTHROPIC_API_KEY` is set where your scheduled runs and the API run, as before.
- [ ] **Set `SEC_CONTACT`** to your name and email, in the same places:

  ```bash
  export SEC_CONTACT="Your Name you@yourmail.com"          # macOS / Linux
  $env:SEC_CONTACT="Your Name you@yourmail.com"            # Windows PowerShell
  ```

  Add it wherever you set `ANTHROPIC_API_KEY` for scheduled runs (your cron line, service file or Task Scheduler task). The SEC sees this with each request, and nothing else about you (section 16).

No new packages are needed.

---

## 6. Step 1: Add edgar.py and filings.py

1. Add `edgar.py` from the [appendix](#edgarpy). It reads the SEC, with no Claude:

   | Function | What it does |
   |---|---|
   | `company_numbers()` | The SEC's number for each ticker |
   | `list_filings(cik)` | A company's latest filings, newest first |
   | `filing_documents(cik, accession)` | The documents in a filing, with the SEC's label for each ("8-K", "EX-99.1") |
   | `to_text(html)` | A filing as plain text: one line per paragraph or table row |
   | `discussion(text, annual)` | Management's discussion, from a report |
   | `periods(company_facts(cik))` | Quarterly and yearly figures from the SEC's structured data, with fourth quarters worked out |

2. Add `filings.py` from the [appendix](#filingspy). It decides what to do with them:

   | Function | What it does |
   |---|---|
   | `check(trigger)` | Finds new filings, reads new results, fetches reports' figures, confirms, and sends Discord messages |
   | `read(accession)` | Reads one filing with Claude now and saves the first take |
   | `check_before_run(emit)` | What a run calls first. Never raises |
   | `list_filings(conn)`, `get_filing(conn, accession)` | Filings with their latest first take |
   | `for_calendar(conn, events, start, end)` | Results filed, matched to the calendar's earnings events |
   | `expected(conn, today)` | Results the calendar expected that haven't been filed |

**Try it** (free, needs internet and `SEC_CONTACT`):

```bash
python filings.py figures AAPL
python filings.py check --no-read
python filings.py list
```

- The first prints Apple's last 8 quarters of revenue, profit and earnings per share from the SEC's data. Fourth quarters say "(worked out: the year minus the first nine months)".
- The second lists your companies' filings from the last four months without sending anything to Claude. It ends with something like `ok: 37 new filings from 5 companies, 0 read, $0.000`.
- The third shows them, newest first.

---

## 7. Step 2: Connect them to runs, briefs and Ask

Replace these files with the appendix versions:

| File | Change |
|---|---|
| `run_brief.py` | Calls `filings.check_before_run` at the start of every run, and allows the agent's new tool |
| `market_tools.py` | A seventh tool, `recent_filings(tickers, days=3)`: what each flagged company filed in the last few days, with its first take if it has one, and any results the calendar expected that haven't come |
| `analyst_prompt.md` | The agent calls `recent_filings` once when anything is flagged. A filing with a first take leads "Likely why", cited as `[company filing](url)`. It uses the first take's figures exactly as given, and never guesses at a filing that hasn't been read |
| `ask.py` | Questions naming a stock get its latest 8 filings and its latest 2 first takes in full. Other questions get the last week's filings. Claude cites them as `(filing, date filed)` |

---

## 8. Step 3: Add the API endpoints

Replace `api.py` with the appendix version. It adds:

| Endpoint | What it does |
|---|---|
| `GET /api/filings` | The latest 300 filings, newest first, each with its latest first take. Also: results expected but not filed, tickers with no company filings, the last check, and any check or read in progress. `?ticker=MSFT` lists one stock's |
| `POST /api/filings/check` with `{}` | Looks for new filings now (`202`), in the background |
| `POST /api/filings/read` with `{"accession": "0000789019-26-000123"}` | Reads that filing now (`202`), in the background |
| `GET /api/calendar` | As before, plus `reported`: results filed in those dates, each with the `event_id` of the earnings event it answers (or `null`) |

**When something can't be done,** the reply has an `error` message to show:

| Status | When |
|---|---|
| `400` | A read request that isn't `{"accession": "…"}` with the SEC's number format |
| `404` | That filing isn't listed |
| `409` | A check or a read is already running |
| `429` | Too soon after the last one: 60 seconds for checks, 30 for reads |
| `403` / `415` | The request came from another website, or isn't JSON (section 16) |

**Live updates.** Checks and reads send their progress (`filings_check` and `filing_read` events). The background watcher sends `filings_updated` when any program lists a filing or finishes a read.

**Try it** with the API running:

```bash
curl http://127.0.0.1:8000/api/filings
```

---

## 9. Step 4: Add the Filings tab

Replace or add these files in `frontend/src/`:

| File | Change |
|---|---|
| `components/FilingsTab.jsx` | **New:** the list, filters, first takes, figures tables, **Check now** and **Read this filing** |
| `components/CalendarTab.jsx` | "Reported" on earnings events, and results shown on the day they were filed |
| `components/ComingUp.jsx` | An earnings event that's been reported links to its first take |
| `components/RunPanel.jsx` | Names the agent's new step: "Checking company filings" |
| `App.jsx` | The Filings tab, and its live updates |
| `useRoute.js` | The `#/filings` and `#/filings/0000789019-26-000123` addresses |
| `api.js` | `getFilings`, `checkFilings`, `readFiling` |
| `styles.css` | Filing cards, figures tables and the calendar's "Reported" line |

Then rebuild if you serve the built app (`cd frontend && npm run build`).

---

## 10. Step 5: Add the tests

1. Replace `tests/conftest.py` with the appendix version. Every run now starts by looking for filings, so this stops other tests' runs from doing that. It also removes `SEC_CONTACT` during tests, so no test can reach the SEC even if it's set in your terminal.
2. Add `tests/test_filings.py` from the [appendix](#teststest_filingspy).
3. Replace `tests/test_market_tools.py` with the version in `market-agent-testing.md`'s appendix. Its MCP check now expects seven tools.
4. Run:

```bash
pytest -v
```

**Expected result:** `415 passed, 4 skipped`. The new skipped test is a live check of the SEC (section 12.5). The new file alone (`pytest -v tests/test_filings.py`) gives `139 passed, 1 skipped`. They use a fake SEC, a fake Claude and a fake Discord, so they're free and need no internet.

---

## 11. Step 6: Try it

Start the app as usual, with `SEC_CONTACT` set, then:

1. **Open the Filings tab** and press **Check now**. Your companies' filings from the last four months appear. This is free: nothing older than 3 days is read.
2. **Read one.** Pick a recent results announcement and press **Read this filing**. In a few seconds its first take appears. Open a point's **From the filing** and check it against the filing on sec.gov.
3. **Check the figures.** If that quarter's report is already filed, each figure says ✓ Confirmed after the next **Check now**.
4. **The calendar.** Open that company's last earnings date: it says "Reported", with a link back.
5. **The next results day.** After the company reports, the next run's log starts with "Reading …'s results announcement", and the brief's "Likely why" cites the company filing.

**When to check.** Results usually arrive just after 4pm or before 9:30am New York time. Every run checks, so if your runs already cover those times, there's nothing to add. If not, schedule two free checks on weekdays, the same way you scheduled `run_brief.py`:

```bash
# crontab, with the computer's clock on New York time
35 16 * * 1-5  cd /path/to/market-agent && .venv/bin/python filings.py check >> filings.log 2>&1
0  8  * * 1-5  cd /path/to/market-agent && .venv/bin/python filings.py check >> filings.log 2>&1
```

**To try it all for free first,** update the test environment (`market-agent-test-enviro.md`): replace its three files, then run `python testenv.py seed --reset` and `python testenv.py build-frontend`. Its sample has a simulated SEC with two months of filings, first takes and confirmed figures, and **Check now** and **Read this filing** work offline at $0.

To show the Filings tab in your live demo, build and publish it again (`market-agent-demo.md`, section 11).

---

## 12. Test it

### 12.1 Automated tests

*In `tests/test_filings.py`*

**Reading the SEC (`edgar.py`)**

| Test | Proves that |
|---|---|
| `test_a_filing_becomes_plain_text_with_one_line_per_table_row` | A press release becomes text with one line per table row. `$`, `(` and `)` in cells of their own join their numbers. Hidden parts are left out |
| `test_text_copes_with_nested_tables_hidden_parts_and_cut_off_html` | Nested tables, `display: none` and a download that stops mid-table still give sensible text |
| `test_managements_discussion_is_found_past_the_contents_page` | The discussion section is found in a 10-Q and a 10-K, not its entry in the contents list |
| `test_a_companys_filings_are_read_from_the_secs_lists` | The SEC's lists become filings, newest first, with New York times converted. A bad row and a short list are tolerated |
| `test_a_filings_documents_come_from_its_index_page` | Documents and their labels come from the filing's index page, without the bundle and data files |
| `test_without_an_index_page_documents_are_guessed_from_their_names` | With no index page, the folder listing is used |
| `test_requests_say_who_they_are_and_keep_their_distance` | Nothing is sent without a contact (or with the placeholder). Requests carry it, are spaced out, unpack gzip, never exceed the size asked for, and only go to sec.gov |
| `test_the_secs_refusals_are_explained` (4 cases) | 403, 429, 404 and 500 each give a clear message |
| `test_quarters_come_from_structured_data_and_the_fourth_is_worked_out` | With Microsoft's real figures: quarters are read, and April to June is the year minus nine months, for revenue and for earnings per share |
| `test_a_fourth_quarter_can_also_be_the_year_minus_three_quarters` | The other way to work it out; with a quarter missing, nothing is guessed |
| `test_a_restated_figure_replaces_the_original` | The most recently filed value wins |
| `test_the_name_with_the_newest_figures_is_used_for_every_period` | A company that changed how it labels revenue is read under its current label |
| `test_quarters_that_end_a_few_days_apart_still_match` | A 52/53-week year still finds its year-ago quarter, and never a different quarter |
| `test_numbers_are_read_as_written` (10 cases) | `94,930`, `$1.64`, `(1,234)` and so on; anything else is refused |

**Naming and quoting**

| Test | Proves that |
|---|---|
| `test_filings_are_named_in_plain_words` (14 cases) | Each form and item gets its kind, title and "worth a look" flag |
| `test_forms_that_arent_followed_are_ignored` (6 cases) | Insider trades, prospectuses and the like aren't listed |
| `test_a_quote_counts_only_if_its_in_the_filing` (12 cases) | Capitals, spacing, curly quotes, table separators and "…" are allowed. A changed number, words out of order, or a quote too short to prove anything aren't |

**Looking for filings**

| Test | Proves that |
|---|---|
| `test_a_check_lists_new_filings_once` | New filings are saved once; forms that aren't followed and filings older than four months aren't |
| `test_an_empty_watchlist_or_a_filing_without_a_time_is_no_trouble` | Neither breaks a check |
| `test_funds_and_unknown_tickers_are_skipped_quietly` | A fund is skipped, and asked about again only after a month |
| `test_two_share_classes_are_one_company_asked_and_read_once` | One request, one read and one Discord message for two tickers |
| `test_one_company_failing_doesnt_stop_the_rest` | The check says `partial`, and the others are saved |
| `test_being_limited_by_the_sec_stops_the_check` | After a 403, no more requests are made |
| `test_an_unreachable_sec_is_given_up_on_quickly` | After two companies in a row can't be reached, the check stops |
| `test_without_a_contact_nothing_is_asked_and_a_run_carries_on` | No request is made, the message says how to set `SEC_CONTACT`, and a run only gets a warning |
| `test_only_fresh_results_are_read_automatically` | Yesterday's results are read. Old results, other announcements and amended ones aren't. Nothing is read twice |
| `test_a_busy_day_reads_a_few_and_leaves_the_rest_for_the_next_check` | The limit per check holds, and the rest are read next time |

**Reading**

| Test | Proves that |
|---|---|
| `test_a_results_first_take` | The press release is read, not the cover page. Claude gets the previous announcement too. Figures are compared with the quarter before and a year earlier, with margins |
| `test_points_claude_cant_quote_are_dropped` | Invented points are removed, with a note saying how many |
| `test_a_take_with_nothing_quotable_fails_and_says_why` | Saved as failed, with the cost |
| `test_quotes_from_the_previous_announcement_dont_count` | A quote must be from the new filing |
| `test_a_figure_that_doesnt_check_out_is_left_out` (6 cases) | Wrong unit, a number that isn't in its quote, a quote that isn't in the filing, a number in words, an unknown scale, an unknown figure |
| `test_claude_never_sets_the_scale_of_earnings_per_share` | It's always dollars |
| `test_an_unclear_quarter_means_no_comparisons` (4 cases) | A quarter end in the future, too far back, in words or missing: figures are kept, comparisons aren't made |
| `test_a_loss_or_a_missing_quarter_gives_no_percentage` | No percentage from a loss, or without the earlier quarter |
| `test_a_bank_without_gross_profit_just_has_fewer_rows` | Figures a company doesn't report are simply absent |
| `test_earlier_quarters_being_unavailable_still_gives_a_take` | If the SEC's figures can't be fetched, the take is saved without comparisons, with a note |
| `test_a_first_results_announcement_has_nothing_to_compare_wording_with` | Noted, not an error |
| `test_a_long_document_is_cut_off_and_says_so` | The size limit holds, and the take says the document was cut |
| `test_with_several_exhibits_the_press_release_is_the_one_read` | Slides and contracts attached to the filing aren't sent |
| `test_results_that_come_with_other_news_are_one_filing_and_one_message` | Results plus an executive change: read as results, marked worth a look, one Discord message |
| `test_results_without_a_press_release_read_the_filing_itself` | With a note |
| `test_a_bad_reply_is_saved_as_a_failed_read` (4 cases) | No JSON, the wrong shape, no headline, the cost cap. Trying again works |
| `test_a_later_failure_doesnt_hide_a_good_first_take` | The earlier good take stays shown |
| `test_only_listed_filings_can_be_read_one_at_a_time` | An unknown filing is refused (`404`), a second read at once is refused (`409`), and a read that crashed doesn't block forever |
| `test_an_announcement_is_read_with_its_press_release` | The filing's text and its press release are both given |
| `test_a_filing_with_nothing_readable_fails_clearly` | A scan or a PDF fails with a clear message, and nothing is sent to Claude |
| `test_a_report_is_read_through_managements_discussion` | Only the discussion is sent; without one, the start of the report |
| `test_companies_outside_the_us_are_listed_and_read_on_request` | A 6-K is listed, never read automatically, and no US-style figures are looked for |

**The report confirms the announcement**

| Test | Proves that |
|---|---|
| `test_the_quarterly_report_confirms_the_announcements_figures` | Figures go from "not checked" to confirmed, without Claude. The report's own figures are saved |
| `test_a_figure_the_report_gives_differently_is_flagged` | A different figure is flagged, with the report's value |
| `test_rounding_is_allowed_but_real_differences_arent` (6 cases), `test_earnings_per_share_must_match_to_the_cent` | The rounding rules |
| `test_a_report_filed_the_same_day_confirms_straight_away` | A report filed minutes before the announcement confirms it at once |
| `test_figures_the_report_doesnt_give_stop_waiting` | "Can't be checked", and the large file isn't downloaded again |
| `test_a_report_whose_figures_never_appear_isnt_fetched_forever` | After 3 days it's settled |
| `test_a_fourth_quarter_is_checked_against_the_annual_report` | Revenue against the year minus nine months; EPS marked as not checkable; the annual report's own figures are for the year |
| `test_an_amended_report_doesnt_replace_the_checks` | Listed, and nothing else changes |
| `test_a_late_report_notice_is_flagged_without_claude` | Marked worth a look and sent to Discord, at no cost |

**The calendar, Discord, briefs, Ask and the API**

| Test | Proves that |
|---|---|
| `test_the_calendar_shows_what_was_reported` | Results are matched to their earnings event; "expected" lists it before, not after |
| `test_a_calendar_date_thats_a_little_out_still_matches` (5 cases) | Two days early or late matches; six days doesn't; an unconfirmed window does |
| `test_results_the_calendar_never_expected_still_show_on_their_day` | With no event, results still show on the day they were filed |
| `test_another_companys_results_never_answer_an_event` | Matching is per company |
| `test_discord_hears_about_results_and_serious_announcements_once` | One message each, with the headline, figures and guidance. Nothing for routine announcements or old results |
| `test_a_discord_message_that_fails_is_sent_by_the_next_check` | A failed message is retried |
| `test_no_discord_without_a_webhook_or_for_old_filings` | Setting up Discord later doesn't send old news |
| `test_the_agents_tool_gives_first_takes_for_flagged_tickers` | `recent_filings` gives first takes, unread filings and expected results |
| `test_a_run_checks_filings_first_even_when_the_report_is_already_saved` | The first take exists before the agent starts; a skipped run still checks |
| `test_a_problem_with_filings_never_stops_a_run` | One warning, and the run carries on |
| `test_ask_sees_filings_and_first_takes` | Ask's material has the filings list, the first take with its figures, and how to cite them |
| `test_api_check_then_the_filings_view`, `test_api_read_a_filing` | The endpoints, progress events, cooldowns and the calendar's `reported` |
| `test_api_read_explains_what_went_wrong` (4 cases) | Unknown filing (`404`), malformed requests (`400`) |
| `test_other_websites_cannot_start_checks_or_reads` | Refused (`403`, `415`), and nothing is spent |
| `test_filings_found_by_scheduled_runs_reach_open_pages` | Open pages are told |
| `test_live_filings` | Live only: the real SEC (section 12.5) |

### 12.2 Edge cases the tests cover

These are the unusual situations a filings reader meets in real use. Each has a test above.

| Situation | What happens |
|---|---|
| You track an ETF | Skipped quietly; the tab says funds don't file these forms |
| You track both share classes of one company | Asked once, read once, shown under both |
| A company based outside the US (6-K, 20-F) | Listed; read only on request; no US-style figures |
| A filing is amended (8-K/A, 10-Q/A) | Listed as "Amended: …"; never read automatically |
| A company says its report will be late (NT 10-Q) | Marked "Worth a look" and sent to Discord, without Claude |
| Results and an executive change in one filing | One filing, read as results, marked worth a look, one message |
| The quarterly report is filed before the announcement | Figures are confirmed in the same check |
| A fourth quarter | Worked out from the annual report; EPS isn't confirmed |
| A 52/53-week year | Quarters ending a few days apart still match |
| A company relabels its revenue | The current label is used for every period |
| A restated figure | The latest filed value is used |
| A bank (no gross profit or operating income) | Fewer rows, not an error |
| A loss in the earlier quarter | No percentage |
| Claude invents a point | Dropped, with a note |
| Claude misreads thousands as millions | The figure is left out, with a note |
| Claude quotes the previous announcement | Doesn't count |
| The press release is very long | Cut at 60,000 characters, with a note |
| The filing is a scan or a PDF | Fails clearly; nothing is sent to Claude |
| The filing has slides and contracts attached | Only the press release is read |
| Yahoo's earnings date is a day or two out | Still matched; the calendar says "Reported on …" |
| Results the calendar never listed | Shown on the day they were filed |
| The SEC limits requests (403/429) | The check stops and says to wait 10 minutes |
| The SEC can't be reached | The check gives up after two companies; the run carries on |
| `SEC_CONTACT` isn't set | Nothing is sent; one clear message |
| Five companies report on the same evening | 5 are read per check; the rest next time |
| You add this months after your first report | Old results are listed, not read; no old Discord messages |
| A read crashes halfway | It shows as failed after 10 minutes and can be tried again |
| A read fails after an earlier one worked | The good first take stays |

### 12.3 Check the tests catch real bugs

Make one of these temporary changes, run `pytest tests/test_filings.py`, then change it back. All 48 that were tried were caught; these are a sample:

| Temporary change | Test that fails |
|---|---|
| `edgar.py`: in `_split`, `if nine:` → `if False:` | `test_quarters_come_from_structured_data_and_the_fourth_is_worked_out` |
| `edgar.py`: in `_periods_of`, delete `or str(fact.get("filed") or "") >= best[key]["filed"]` | `test_a_restated_figure_replaces_the_original` |
| `edgar.py`: in `fetch`, `if wait > 0:` → `if False:` | `test_requests_say_who_they_are_and_keep_their_distance` |
| `filings.py`: in `quoted`, replace the first `if` and its `return False` with `return True` | `test_a_quote_counts_only_if_its_in_the_filing` |
| `filings.py`: in `check_reply`, `or written.replace(" ", "") not in quote.replace(" ", ""):` → `or False:` | `test_a_figure_that_doesnt_check_out_is_left_out` |
| `filings.py`: in `compare`, `and not 0.05 <= r["value"] / nearby["value"] <= 20:` → `and False:` | `test_a_figure_that_doesnt_check_out_is_left_out` |
| `filings.py`: in `agrees`, the last line → `return True` | `test_a_figure_the_report_gives_differently_is_flagged` |
| `filings.py`: in `confirm`, `if filed["derived"] and row["unit"] != "USD":` → `if False:` | `test_a_fourth_quarter_is_checked_against_the_annual_report` |
| `filings.py`: in `check`, `AND filed_at >= ?` → `AND ? IS NOT NULL` (in the automatic-reads query) | `test_only_fresh_results_are_read_automatically` |
| `filings.py`: in `check`, `if unreachable >= UNREACHABLE_LIMIT:` → `if False:` | `test_an_unreachable_sec_is_given_up_on_quickly` |
| `filings.py`: in `gather`, `if filing["kind"] == "results" and press:` → `if False:` | `test_a_results_first_take` |
| `filings.py`: in `gather`, `text, cut_off = _cut(text, MAX_CHARS)` → `text, cut_off = text, False` | `test_a_long_document_is_cut_off_and_says_so` |
| `filings.py`: in `_matches`, the last line → `return filing["ticker"] == event["ticker"] and -30 <= gap <= 30` | `test_a_calendar_date_thats_a_little_out_still_matches` |
| `filings.py`: in `notify`, delete the two lines starting `if filing["kind"] != "results" and not filing["serious"]:` | `test_discord_hears_about_results_and_serious_announcements_once` |
| `run_brief.py`: delete `await asyncio.to_thread(filings.check_before_run, emit)` | `test_a_run_checks_filings_first_even_when_the_report_is_already_saved` |
| `api.py`: in `read_filing`, delete the two `_post_guard` lines | `test_other_websites_cannot_start_checks_or_reads` |
| `ask.py`: `filed = filings_section(conn, tickers)` → `filed = ''` | `test_ask_sees_filings_and_first_takes` |

### 12.4 What was also tested

- **From the guides alone:** all three folders were rebuilt from the guides (this one included), and every test passed: 415 passed and 4 skipped in `market-agent/`, 40 in `market-agent-testenv/`, and 18 in `market-agent-demo/`.
- **In a real browser, against the test environment.** The 13 checks passed with no browser errors:
  1. The Filings tab lists the sample's 24 filings; the newest results have a first take with figures, margins and guidance.
  2. A point opens to the filing's own words; a figure shows the row it came from.
  3. Figures are confirmed where the quarterly report is in; a report has its own figures; a bank has 3 rows.
  4. The filters: kind, first takes only, and stock.
  5. **Read this filing** gives a first take; reading another straight away explains the wait.
  6. **Check now** runs; pressing again straight away explains the wait.
  7. **Run update now** finds a filing made minutes earlier, the brief links to it, and it tops the tab without a reload.
  8. A report found by another program confirms an announcement's figures without a reload.
  9. The calendar says "Reported on Sep 16" on an earnings date of Sep 17, and its link opens that filing, picked out.
  10. A ticker opens its chart, and Ask answers with the latest first take.
  11. On a phone the tab fits, and the figures table scrolls inside its own box.
  12. Dark mode renders the tab and the calendar's "Reported" line.
  13. On the Today tab, a reported earnings event links to its first take.

  The earlier Today, Previous days, chart, search, sector and alerts, calendar, Coming up, Stocks and Follow-through checks all still pass, and so do the live demo's 16 checks, which now include the Filings tab.
- **Against the SEC's real pages.** The formats this code reads were checked by reading the SEC's own pages for Microsoft on 10 November 2026: the company list, the dates in its filing list, one filing's folder and index page, and its structured revenue and earnings-per-share figures. Those real figures are the fixtures in the fourth-quarter test. That reading also found a real case the design now handles: an "EX-99.1" attachment isn't always a press release. One of Microsoft's was a 6 MB reissue of its annual report, which is why documents are size-limited and cut-offs are noted.
- **Found and fixed while testing:**
  - The discussion finder picked the contents-page entry instead of the section.
  - The download limit was applied before unpacking, so a "limited" download could still be far larger. It's now exact.
  - With the SEC unreachable, a check waited on every company in turn, which could hold a run up for minutes. It now gives up after two.
  - A report whose figures never appeared was looked up again on every check. It's now settled after 3 days.
  - In the live demo, the Filings tab didn't refresh after a replayed run.

**Not tested here:**

- Running this code itself against the SEC. The SEC's pages were read through a browsing tool, not through `edgar.py`, and three columns of the filing list (form, items and document name) were beyond what that tool could show.
- A real press release through `to_text`.
- Real Claude reads, and so their real cost.

Run the checks below once.

### 12.5 Checks with real data

**The live test** (free, needs internet and `SEC_CONTACT`):

```bash
LIVE_TESTS=1 pytest -v -s -k live_filings                  # macOS / Linux
$env:LIVE_TESTS=1; pytest -v -s -k live_filings            # Windows PowerShell
```

**Expected result:** `1 passed`. It prints Apple's latest followed filings, the documents in its latest results announcement, the start of the press release as text, and five quarters of revenue.

Check by eye:

- [ ] The filings and their dates match Apple's page on sec.gov (search "Apple" at sec.gov/edgar/search)
- [ ] The documents include one labelled `EX-99.1`
- [ ] The press release text starts with the headline, not with code or blank lines
- [ ] Quarterly revenue matches Apple's reports. The fourth quarter (to late September) says it was worked out

**Then, with real Claude** (a few cents each):

- [ ] `python filings.py read ACCESSION` on a recent results announcement (take the number from `python filings.py list`). The headline and points are right. Each quote is word for word in the press release
- [ ] The figures match the press release's income statement, and they're the standard (GAAP) figures, not "adjusted" ones
- [ ] The cost printed is a few cents. If it's much more, lower `MAX_CHARS`
- [ ] After that quarter's report is filed, `python filings.py check` then `python filings.py show ACCESSION` says "✓ confirmed by the report" on each figure
- [ ] On the Filings tab, "the filing on sec.gov" opens the right filing

**Edge cases to try by hand,** once it's running:

- [ ] Add an ETF (such as SPY) on the Stocks tab, then **Check now**: the tab says there are no company filings for it, and the check is still `ok`
- [ ] Track a bank (such as JPM): its first take has revenue, net income and earnings per share, without gross profit
- [ ] Track a company whose year doesn't end in December (such as MSFT, NVDA or AAPL): `python filings.py figures TICKER` shows its quarters on its own calendar, with one worked-out quarter a year
- [ ] Unset `SEC_CONTACT` in a terminal and run `python run_brief.py`: the run finishes, with one warning about filings
- [ ] Turn off your network and run `python filings.py check`: it stops after two companies, not after all of them
- [ ] Press **Read this filing** on an annual report: the first take is about management's discussion, and if the report was too large a note says the start was read instead
- [ ] On a results day, compare the brief's "Likely why" with the first take: the brief should lead with the company's filing and use the same figures

---

## 13. From the terminal

```bash
python filings.py check                          # look for new filings now; reads new results
python filings.py check --no-read                # only list them: nothing is sent to Claude
python filings.py list                           # the latest 40 filings
python filings.py list --ticker MSFT             # one stock's
python filings.py read 0000789019-26-000123      # read one filing now (a few cents)
python filings.py show 0000789019-26-000123      # a filing's first take
python filings.py figures MSFT                   # quarterly figures from the SEC's structured data (free)
```

**`list` and `show`** (from the test environment's simulated data):

```
2026-11-04  AMZN   8-K      0004760458-26-003080  Results announcement  [first take]
2026-10-26  NVDA   8-K      0005650435-26-002990  ! Directors or senior officers leaving or appointed
2026-10-22  AAPL   8-K      0001487304-26-002951  Results announcement  [first take]
2026-10-22  AAPL   10-Q     0001487304-26-002950  Quarterly report

JPM  Results announcement  (filed 2026-09-16, 8-K)

Figures as announced (quarter to 2026-06-30):
  Revenue $29.92B (+13.9% vs a year ago)  ✓ confirmed by the report
  Net income $8.08B (+14.0% vs a year ago)  ✓ confirmed by the report
  Earnings per share (diluted) $0.86 (+13.2% vs a year ago)  ✓ confirmed by the report

JPMorgan Chase reported revenue of $29.9 billion, up 14% from the same quarter a year earlier.  ($0.000)

Key points:
  - Revenue was $29.9 billion, up 14% from the same quarter a year earlier.
      "Revenue was $29.9 billion, up 14% from the same quarter a year earlier."
```

A `!` marks a filing that's worth a look.

**Reading the tables yourself.** Filings are in `reports.db`, so any SQLite tool can read them:

```bash
sqlite3 reports.db "SELECT filing_date, ticker, form, title FROM filings ORDER BY filed_at DESC LIMIT 10"
sqlite3 reports.db "SELECT finished_at, ticker, status, headline, cost_usd FROM filing_reads ORDER BY id DESC LIMIT 10"
```

Read them, but don't edit them by hand. If you delete the `filings` table, the next check lists the last four months again. First takes can't be rebuilt without reading again.

---

## 14. Settings

| Where | Setting | Default | What it does |
|---|---|---|---|
| Environment | `SEC_CONTACT` | none | Your name and email, sent to the SEC with each request. Required |
| `filings.py` | `AUTOMATIC_WITHIN_DAYS` | `3` | Only results this recent are read automatically, and only filings this recent go to Discord |
| `filings.py` | `MAX_AUTOMATIC` | `5` | Most automatic reads per check. `0` turns automatic reads off |
| `filings.py` | `MAX_CHARS` | `60_000` | The most of a filing Claude is given. This is what bounds a read's cost |
| `filings.py` | `PREVIOUS_CHARS` | `20_000` | The most of the previous announcement given for comparison. `0` leaves it out |
| `filings.py` | `READ_BUDGET_USD` | `0.50` | A backstop on one read's cost |
| `filings.py` | `LOOKBACK_DAYS` | `120` | How far back filings are listed |
| `filings.py` | `SERIOUS_ITEMS` | see section 4 | Which announcements are marked "Worth a look" |
| `filings.py` | `FORMS` | see section 4 | Which forms are followed |
| `edgar.py` | `MIN_GAP_SECONDS` | `0.2` | The gap between requests to the SEC (5 a second; the SEC allows 10) |
| `edgar.py` | `MAX_BYTES` | `12_000_000` | The most of one document that's downloaded |
| `edgar.py` | `METRICS` | 5 figures | The figures followed, and the names companies report them under |
| `api.py` | `FILINGS_CHECK_COOLDOWN_SECONDS` (environment) | `60` | Wait between **Check now** presses |
| `api.py` | `FILING_READ_COOLDOWN_SECONDS` (environment) | `30` | Wait between reads from the app |
| `ask.py` | `FILING_TAKES`, `FILINGS_LISTED` | `2`, `8` | How much of a stock's filings Ask is given |

---

## 15. Costs

- **Looking for filings, and all figures:** free. They're requests to the SEC.
- **A first take:** one Claude request. I haven't measured one with real Claude. A results announcement plus the previous one is about 15,000 to 20,000 tokens in, and under 1,000 out, so I estimate **5 to 20 cents** depending on the model your Agent SDK uses. `python filings.py read` prints the real cost, so check it once (section 12.5).
- **What bounds it:** the size limits (`MAX_CHARS` and `PREVIOUS_CHARS`), because a read is a single request. `READ_BUDGET_USD` is a backstop.
- **Automatic reads:** results only, about 4 a year per stock, at most 5 per check. With 25 stocks that's about 100 a year.
- **Reads you start:** one at a time, at least 30 seconds apart. A full quarterly or annual report's discussion is the longest thing read, so expect those at the top of the range.
- **Briefs:** when something is flagged, the agent makes one more tool call (`recent_filings`). This adds a little to each run.
- **Runs take a few seconds longer,** for the check: about one request per tracked company.
- **Ask:** a few more lines of material per question that names a stock.

The Filings tab shows each read's cost, and `filing_checks` in the database records each check's total.

---

## 16. Security and privacy

- **What the SEC sees:** your `SEC_CONTACT` (the name and email you chose) and your computer's internet address, with each request, and which companies' filings you ask for. That's all. It's how the SEC asks automated tools to behave, and it lets them contact you instead of blocking you if something goes wrong.
- **What Claude sees:** the text of public filings, and the company's name. No keys and nothing of yours.
- **Other websites can't start checks or reads.** **Check now** and **Read this filing** use the same protection as Run now.
- **Nothing runs up a bill.** Reads run one at a time with a cooldown, each has a size limit, and a filing must be listed before anything is spent on it.
- **A filing can't steer Claude.** A read has no tools and one turn. The reply must be JSON, and every point and figure is checked against the filing's text before it's shown.
- **Only the SEC is asked.** `edgar.py` refuses any address that isn't on sec.gov. Links shown in the app are built from the SEC's own paths.
- **Who can use it:** anyone who can reach your API, the same as Run now. It listens on your own computer only.

---

## 17. What it doesn't do

- **Beat or miss.** Analysts' consensus estimates aren't free, so figures are compared with the company's own earlier quarters, not with expectations.
- **Earnings calls.** Call transcripts aren't filed with the SEC by most companies.
- **Adjusted figures.** Only the five standard figures are followed: revenue, gross profit, operating income, net income and diluted earnings per share.
- **Segments, cash flow and the balance sheet.** Not in the figures tables. A first take's key points can mention them, with quotes.
- **Companies that don't file with the SEC.** A company listed only outside the US has no filings here.
- **Very large reports.** Only the first 12 MB of a document is downloaded. In a very large annual report, management's discussion can be past that point, and then the start of the report is read instead, with a note.
- **Search.** First takes aren't in the Previous days search. Ask sees them for stocks you name.
- **Filings before the last four months.** Not listed.

---

## 18. Troubleshooting

| Problem | Cause and fix |
|---|---|
| "Set SEC_CONTACT to your name and email first" | Set it where the program runs (step 5), then restart the API. For scheduled runs, add it where you set `ANTHROPIC_API_KEY`. |
| "The SEC refused the request… wait 10 minutes" | Either `SEC_CONTACT` isn't a real name and email, or too many requests came from your address. Wait 10 minutes. Don't run several checks at once. |
| "couldn't reach the SEC" | A network problem, or the SEC is down. The check stops early and the next one catches up. |
| A stock has no filings | It may be a fund (the tab says so), listed only outside the US, or tracked under a ticker the SEC writes differently. Check with `python filings.py figures TICKER`. |
| Results were filed but not read | They were more than 3 days old when first found (press **Read this filing**), or 5 were already read in that check (the next check reads the rest). |
| A first take says items were left out | Claude gave points or figures whose quotes aren't in the filing. That's the check working. Press **Read again** if too much is missing. |
| "The quarter's end date wasn't clear" | The announcement didn't state its quarter plainly. Figures are shown without comparisons. |
| A figure says "The report says $X" | The quarterly report's figure differs from the announcement's. Usually the announcement led with an adjusted figure, or was later corrected. Open both filings. |
| Figures stay "Not checked yet" | The quarterly report isn't filed yet, or no check has run since. Press **Check now**. |
| "Can't be checked" | The report doesn't give that figure for the quarter alone (a fourth-quarter EPS, or a figure the company doesn't label in the standard way). |
| A report's first take says the start was read instead | Its discussion section wasn't found, usually because the report is larger than `MAX_BYTES`. Raise `MAX_BYTES` in `edgar.py`. |
| "This filing's document has no text that can be read" | The filing is a scan or a PDF. Open it on sec.gov. |
| "Read failed: … error_max_budget_usd" | The read hit `READ_BUDGET_USD`. Lower `MAX_CHARS`, or raise the budget a little. |
| The calendar doesn't say "Reported" | The results were filed more than 3 days from the calendar's date (14 after an unconfirmed one). They still show on the day they were filed. |
| No Discord message for results | The webhook isn't set where the check ran, or the results were more than 3 days old when found. |
| Runs take a few seconds longer | The check adds about one request per tracked stock. Tracking fewer stocks is the only thing that shortens it. |
| `ModuleNotFoundError: No module named 'filings'` (or `edgar`) | Add both files from the appendix, in the `market-agent` folder. |
| Only `test_tools_work_through_mcp` fails | `tests/test_market_tools.py` is from before this guide. Replace it from the testing guide's appendix (step 10). |
| Many unrelated tests fail with "Set SEC_CONTACT" warnings in run logs | `tests/conftest.py` is from before this guide. Replace it (step 10). |

---

## Appendix: full source code

### edgar.py

```python
"""Reading the SEC's EDGAR service: which filings a company has made, the documents inside a
filing, and the figures companies report in structured form (XBRL).

It's free and needs no key or account. The SEC asks automated tools to say who they are and to
stay under 10 requests a second, so set SEC_CONTACT to your name and email:

    export SEC_CONTACT="Jane Doe jane@example.com"

Everything here is plain reading and arithmetic: no Claude. filings.py decides what to do with it.
Tests and the test environment replace get_json and get_text, so nothing else talks to the SEC.
"""

import json
import os
import re
import threading
import time
import urllib.error
import urllib.request
import zlib
from datetime import date, timedelta
from html.parser import HTMLParser

CONTACT_ENV = "SEC_CONTACT"
DATA = "https://data.sec.gov"
WWW = "https://www.sec.gov"
MIN_GAP_SECONDS = 0.2        # between requests: at most 5 a second (the SEC allows 10)
TIMEOUT_SECONDS = 20
MAX_BYTES = 12_000_000       # the most of one document that's downloaded
MAX_FACTS_BYTES = 80_000_000 # a company's structured figures come as one large file
READABLE = (".htm", ".html", ".txt")

SCALES = {"units": 1, "thousands": 1_000, "millions": 1_000_000, "billions": 1_000_000_000}

# The figures worked out for each company, and the XBRL names companies report them under.
# The first name a company has recent figures for is used for every period, so periods compare like with like.
METRICS = {
    "revenue": {"label": "Revenue", "unit": "USD", "tags": [
        "RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues", "SalesRevenueNet",
        "RevenueFromContractWithCustomerIncludingAssessedTax", "RevenuesNetOfInterestExpense"]},
    "gross_profit": {"label": "Gross profit", "unit": "USD", "tags": ["GrossProfit"]},
    "operating_income": {"label": "Operating income", "unit": "USD", "tags": ["OperatingIncomeLoss"]},
    "net_income": {"label": "Net income", "unit": "USD", "tags": [
        "NetIncomeLoss", "ProfitLoss", "NetIncomeLossAvailableToCommonStockholdersBasic"]},
    "eps_diluted": {"label": "Earnings per share (diluted)", "unit": "USD/shares", "tags": ["EarningsPerShareDiluted"]},
}
QUARTER_DAYS, NINE_MONTH_DAYS, YEAR_DAYS = (80, 100), (260, 290), (350, 380)


class EdgarError(Exception):
    """A problem reading from the SEC, with a message to show as it is."""

    def __init__(self, message: str, status: int | None = None):
        super().__init__(message)
        self.status = status


class ContactMissing(EdgarError):
    """SEC_CONTACT isn't set, so nothing can be asked of the SEC."""


# ---------------------------------------------------------------------------
# Requests
# ---------------------------------------------------------------------------

_lock = threading.Lock()
_last_request = 0.0


def contact() -> str:
    """Who we tell the SEC we are. Raises EdgarError if SEC_CONTACT isn't a name and an email."""
    value = " ".join(os.environ.get(CONTACT_ENV, "").split())
    if "@" not in value or len(value) < 6 or "example.com" in value.lower():
        raise ContactMissing(f'Set {CONTACT_ENV} to your name and email first, for example: '
                         f'export {CONTACT_ENV}="Jane Doe jane@yourmail.com". '
                         "The SEC asks automated tools to say who they are.")
    return value


def contact_set() -> bool:
    try:
        contact()
        return True
    except EdgarError:
        return False


def fetch(url: str, max_bytes: int = MAX_BYTES) -> bytes:
    """One request to the SEC, politely: identified, spaced out, and never more than max_bytes."""
    global _last_request
    if not url.startswith((DATA + "/", WWW + "/")):
        raise EdgarError("only sec.gov addresses are read")
    request = urllib.request.Request(url, headers={"User-Agent": contact(), "Accept-Encoding": "gzip"})
    with _lock:  # one at a time, with a gap, whichever thread asks
        wait = MIN_GAP_SECONDS - (time.monotonic() - _last_request)
        if wait > 0:
            time.sleep(wait)
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                unpack = zlib.decompressobj(47) if (response.headers.get("Content-Encoding") or "").lower() == "gzip" else None
                raw = bytearray()
                while len(raw) <= max_bytes:  # read (and unpack) only as much as is wanted
                    chunk = response.read(65536)
                    if not chunk:
                        break
                    raw += unpack.decompress(chunk, max_bytes + 1 - len(raw)) if unpack else chunk
        except urllib.error.HTTPError as e:
            if e.code == 404:
                raise EdgarError("the SEC doesn't have that page", 404) from None
            if e.code in (403, 429):
                raise EdgarError("The SEC refused the request. Check SEC_CONTACT is your name and email. If it is, "
                                 "the SEC is limiting requests from this computer: wait 10 minutes and try again.",
                                 e.code) from None
            raise EdgarError(f"the SEC answered with an error ({e.code})", e.code) from None
        except zlib.error:
            raise EdgarError("the SEC's answer wasn't readable") from None
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            raise EdgarError(f"couldn't reach the SEC ({getattr(e, 'reason', e)})") from None
        finally:
            _last_request = time.monotonic()
    return bytes(raw[:max_bytes])


def get_json(url: str, max_bytes: int = MAX_BYTES):
    try:
        return json.loads(fetch(url, max_bytes))
    except ValueError:
        raise EdgarError("the SEC's answer wasn't readable") from None


def get_text(url: str, max_bytes: int = MAX_BYTES) -> str:
    raw = fetch(url, max_bytes)
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("cp1252", errors="replace")


# ---------------------------------------------------------------------------
# Companies and their filings
# ---------------------------------------------------------------------------

def company_numbers() -> dict[str, dict]:
    """Every company the SEC lists with a ticker: {"AAPL": {"cik": 320193, "name": "Apple Inc."}}."""
    listed = get_json(f"{WWW}/files/company_tickers.json")
    found = {}
    for entry in (listed.values() if isinstance(listed, dict) else listed):
        try:
            found.setdefault(str(entry["ticker"]).upper(), {"cik": int(entry["cik_str"]), "name": str(entry.get("title") or "")})
        except (KeyError, TypeError, ValueError):
            continue
    return found


def folder(cik: int, accession: str) -> str:
    return f"{WWW}/Archives/edgar/data/{int(cik)}/{accession.replace('-', '')}/"


def index_url(cik: int, accession: str) -> str:
    """The filing's own page on sec.gov, listing its documents."""
    return f"{folder(cik, accession)}{accession}-index.htm"


def _stamp(value: str) -> str:
    """'2026-11-09T23:04:33.000Z' -> '2026-11-09T23:04:33Z' (UTC)."""
    value = str(value or "")
    return value[:19] + "Z" if len(value) >= 19 and value[10] == "T" else ""


def list_filings(cik: int) -> dict:
    """A company's latest filings, newest first:
    {"name", "filings": [{accession, form, items, filing_date, report_date, filed_at, primary_doc, description}]}"""
    data = get_json(f"{DATA}/submissions/CIK{int(cik):010d}.json")
    recent = (data.get("filings") or {}).get("recent") or {}
    numbers = recent.get("accessionNumber") or []

    def column(name):
        values = recent.get(name) or []
        return [values[i] if i < len(values) else "" for i in range(len(numbers))]

    columns = {name: column(name) for name in ("form", "items", "filingDate", "reportDate", "acceptanceDateTime",
                                               "primaryDocument", "primaryDocDescription")}
    filings = []
    for i, accession in enumerate(numbers):
        if not re.fullmatch(r"\d{10}-\d{2}-\d{6}", str(accession)):
            continue
        filings.append({
            "accession": accession, "form": str(columns["form"][i] or "").strip().upper(),
            "items": [code.strip() for code in str(columns["items"][i] or "").split(",") if code.strip()],
            "filing_date": str(columns["filingDate"][i] or "")[:10], "report_date": str(columns["reportDate"][i] or "")[:10],
            "filed_at": _stamp(columns["acceptanceDateTime"][i]),
            "primary_doc": str(columns["primaryDocument"][i] or ""),
            "description": str(columns["primaryDocDescription"][i] or "")})
    filings.sort(key=lambda f: (f["filed_at"] or f["filing_date"], f["accession"]), reverse=True)
    return {"name": str(data.get("name") or ""), "filings": filings}


class _Tables(HTMLParser):
    """Every table in a page as rows of cells: [{"text", "href"}]."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tables, self._row, self._cell = [], None, None

    def handle_starttag(self, tag, attrs):
        if tag == "table":
            self.tables.append([])
        elif tag == "tr":
            self._row = []
        elif tag in ("td", "th") and self._row is not None:
            self._cell = {"text": "", "href": None}
        elif tag == "a" and self._cell is not None and self._cell["href"] is None:
            self._cell["href"] = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cell is not None and self._row is not None:
            self._cell["text"] = " ".join(self._cell["text"].split())
            self._row.append(self._cell)
            self._cell = None
        elif tag == "tr" and self._row is not None:
            if self.tables and self._row:
                self.tables[-1].append(self._row)
            self._row = None

    def handle_data(self, data):
        if self._cell is not None:
            self._cell["text"] += data


def _guess_type(name: str, primary_doc: str, form: str) -> str:
    if name == primary_doc:
        return form
    match = re.search(r"ex[-_]?(\d{2})[-_.]?(\d{1,2})?", name, re.I)
    return f"EX-{match.group(1)}" + (f".{match.group(2)}" if match.group(2) else "") if match else ""


def filing_documents(cik: int, accession: str, primary_doc: str = "", form: str = "") -> list[dict]:
    """The readable documents in a filing, in order: [{name, type, description, size, url}].
    type is the SEC's own label: the form itself ("8-K") or an exhibit ("EX-99.1", a press release)."""
    base = folder(cik, accession)
    documents = []
    try:
        parser = _Tables()
        parser.feed(get_text(index_url(cik, accession), 2_000_000))
        for table in parser.tables:
            if not table:
                continue
            head = [c["text"].lower() for c in table[0]]
            if "document" not in head or "type" not in head:
                continue
            at = {name: head.index(name) for name in ("document", "type", "description", "size") if name in head}
            for row in table[1:]:
                if len(row) <= max(at.values()):
                    continue
                cell = row[at["document"]]
                # The link may go through the SEC's viewer (/ix?doc=/Archives/...): the file name is its last part either way
                name = ((cell["href"] or "").rsplit("/", 1)[-1] or cell["text"].split(" ")[0]).strip()
                kind = row[at["type"]]["text"].strip().upper()
                if not name or not kind or not name.lower().endswith(READABLE):
                    continue
                size = row[at["size"]]["text"] if "size" in at else ""
                documents.append({"name": name, "type": kind, "url": base + name,
                                  "description": row[at["description"]]["text"] if "description" in at else "",
                                  "size": int(size) if size.isdigit() else None})
    except EdgarError as e:
        if e.status != 404:
            raise
    if documents:
        return documents
    # No readable index page: fall back to the folder listing, guessing each file's type from its name
    listing = get_json(base + "index.json")
    for item in ((listing.get("directory") or {}).get("item") or []):
        name = str(item.get("name") or "")
        kind = _guess_type(name, primary_doc, form)
        if kind and name.lower().endswith(READABLE) and "index" not in name.lower():
            size = str(item.get("size") or "")
            documents.append({"name": name, "type": kind, "url": base + name, "description": "",
                              "size": int(size) if size.isdigit() else None})
    documents.sort(key=lambda d: d["name"] != primary_doc)
    return documents


# ---------------------------------------------------------------------------
# Documents as plain text
# ---------------------------------------------------------------------------

_BLOCKS = {"p", "div", "br", "li", "ul", "ol", "table", "hr", "h1", "h2", "h3", "h4", "h5", "h6", "section",
           "article", "center", "blockquote", "pre", "title"}
_SKIPPED = {"script", "style", "head", "noscript", "ix:header"}
_VOID = {"br", "hr", "img", "input", "meta", "link", "col", "area", "base", "wbr"}
_HIDDEN = re.compile(r"display\s*:\s*none", re.I)


def _join_row(cells: list[str]) -> str:
    """One table row as 'Label | 1,234 | (56)'. Filings often put $, ( and ) in cells of their own."""
    merged = []
    for cell in (" ".join(c.split()) for c in cells):
        if not cell:
            continue
        if merged and (cell in (")", "%", ")%") or merged[-1] in ("$", "(", "$(", "($")):
            merged[-1] += cell
        else:
            merged.append(cell)
    return " | ".join(merged)


class _Text(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.lines, self._line = [], []
        self._rows, self._cells = [], []     # stacks, because filings nest tables for layout
        self._skip_tag, self._skip_depth = None, 0

    def _write(self, text: str) -> None:
        (self._cells[-1] if self._cells else self._line).append(text)

    def _break(self) -> None:
        if self._cells:
            self._cells[-1].append(" ")
            return
        text = " ".join("".join(self._line).split())
        if text:
            self.lines.append(text)
        self._line = []

    def handle_starttag(self, tag, attrs):
        if self._skip_tag:
            self._skip_depth += tag == self._skip_tag
            return
        if tag in _SKIPPED or (tag not in _VOID and _HIDDEN.search(dict(attrs).get("style") or "")):
            self._skip_tag, self._skip_depth = tag, 1
            return
        if tag == "tr":
            self._break()
            self._rows.append([])
        elif tag in ("td", "th"):
            self._cells.append([])
        elif tag in _BLOCKS:
            self._break()

    def handle_endtag(self, tag):
        if self._skip_tag:
            if tag == self._skip_tag:
                self._skip_depth -= 1
                if self._skip_depth == 0:
                    self._skip_tag = None
            return
        if tag in ("td", "th") and self._cells:
            text = "".join(self._cells.pop())
            if self._rows:
                self._rows[-1].append(text)
            else:
                self._write(text)
        elif tag == "tr" and self._rows:
            row = _join_row(self._rows.pop())
            if self._cells:           # a table inside another table's cell
                self._cells[-1].append(" " + row + " ")
            elif row:
                self.lines.append(row)
        elif tag in _BLOCKS:
            self._break()

    def handle_data(self, data):
        if not self._skip_tag:
            self._write(data)

    def text(self) -> str:
        while self._cells:  # anything left open by cut-off or untidy HTML
            text = "".join(self._cells.pop())
            (self._rows[-1] if self._rows else self._line).append(text)
        while self._rows:
            row = _join_row(self._rows.pop())
            if row:
                self.lines.append(row)
        self._break()
        return "\n".join(self.lines)


def tidy(text: str) -> str:
    """Curly quotes, long dashes and odd spaces made plain, so quotes can be matched."""
    for old, new in (("‘", "'"), ("’", "'"), ("“", '"'), ("”", '"'), ("–", "-"),
                     ("—", "-"), ("−", "-"), (" ", " "), ("​", ""), ("­", "")):
        text = text.replace(old, new)
    return text


def to_text(html: str) -> str:
    """A filing's HTML as plain text: one line per paragraph or table row, cells separated by ' | '.
    Hidden parts (scripts, styles, inline-XBRL headers) are left out."""
    if "<" not in html:
        return tidy(html)
    parser = _Text()
    try:
        parser.feed(html)
        parser.close()
    except Exception:  # untidy or cut-off HTML: keep what was read
        pass
    return tidy(parser.text())


def discussion(text: str, annual: bool) -> str:
    """Management's discussion of the results from a quarterly (10-Q) or annual (10-K) report,
    or '' if it can't be found. The heading appears in the contents list too, so the longest match wins."""
    number, ends = ("7", r"7a|8") if annual else ("2", r"3|4")
    start = re.compile(rf"(?im)^\s*item\s*{number}\s*[.:\-]?\s*\|?\s*management'?s\s+discussion")
    end = re.compile(rf"(?im)^\s*item\s*(?:{ends})\s*[.:\-]?\s*\|?\s*[a-z]")
    best = ""
    for match in start.finditer(text):
        stop = end.search(text, match.end())
        body = text[match.start(): stop.start() if stop else len(text)]
        if len(body) > len(best):
            best = body
    return best.strip() if len(best) > 2000 else ""


# ---------------------------------------------------------------------------
# Figures (XBRL)
# ---------------------------------------------------------------------------

def company_facts(cik: int) -> dict:
    """Every figure a company has reported in structured form. Large: often several megabytes."""
    return get_json(f"{DATA}/api/xbrl/companyfacts/CIK{int(cik):010d}.json", MAX_FACTS_BYTES)


def _periods_of(facts: list) -> list[dict]:
    """Each period once, taking the most recently filed value (later reports restate earlier ones)."""
    best = {}
    for fact in facts or []:
        try:
            start, end, value = date.fromisoformat(fact["start"]), date.fromisoformat(fact["end"]), float(fact["val"])
        except (KeyError, TypeError, ValueError):
            continue  # a balance at a point in time, or something unreadable
        key = (start, end)
        if key not in best or str(fact.get("filed") or "") >= best[key]["filed"]:
            best[key] = {"start": start, "end": end, "value": value, "filed": str(fact.get("filed") or ""),
                         "accession": fact.get("accn"), "form": fact.get("form"), "derived": False}
    return list(best.values())


def _days(period: dict) -> int:
    return (period["end"] - period["start"]).days + 1


def _between(days: int, limits: tuple[int, int]) -> bool:
    return limits[0] <= days <= limits[1]


def _split(periods: list[dict]) -> tuple[dict, dict]:
    """(quarters, years) by end date. Annual reports don't give the fourth quarter on its own, so it's
    worked out: the year minus the first nine months (or minus the other three quarters)."""
    quarters = {p["end"]: p for p in periods if _between(_days(p), QUARTER_DAYS)}
    years = {p["end"]: p for p in periods if _between(_days(p), YEAR_DAYS)}
    for year in years.values():
        if any(abs((end - year["end"]).days) <= 5 for end in quarters):
            continue
        nine = [p for p in periods if _between(_days(p), NINE_MONTH_DAYS) and abs((p["start"] - year["start"]).days) <= 5
                and 75 <= (year["end"] - p["end"]).days <= 105]
        inside = [q for q in quarters.values()
                  if q["start"] >= year["start"] - timedelta(days=5) and q["end"] < year["end"] - timedelta(days=60)]
        if nine:
            first = max(nine, key=lambda p: p["end"])
            value, start = year["value"] - first["value"], first["end"] + timedelta(days=1)
        elif len(inside) == 3:
            value, start = year["value"] - sum(q["value"] for q in inside), max(q["end"] for q in inside) + timedelta(days=1)
        else:
            continue
        quarters[year["end"]] = {"start": start, "end": year["end"], "value": value, "filed": year["filed"],
                                 "accession": year["accession"], "form": year["form"], "derived": True}
    return quarters, years


def periods(facts: dict) -> dict:
    """Quarterly and yearly figures from a company's structured data:
    {metric: {"tag", "quarters": {end date: period}, "years": {end date: period}}}.
    A metric the company doesn't report (a bank has no gross profit) is left out."""
    reported = (facts.get("facts") or {}).get("us-gaap") or {}
    found = {}
    for metric, spec in METRICS.items():
        best = None
        for tag in spec["tags"]:
            quarters, years = _split(_periods_of(((reported.get(tag) or {}).get("units") or {}).get(spec["unit"])))
            if not quarters and not years:
                continue
            latest = max([*quarters, *years])
            if best is None or latest > best[0]:
                best = (latest, {"tag": tag, "quarters": quarters, "years": years})
        if best:
            found[metric] = best[1]
    return found


def nearest(by_end: dict, target: date, tolerance_days: int = 12) -> dict | None:
    """The period ending closest to a date (companies' quarters end a few days apart from year to year)."""
    close = [p for end, p in by_end.items() if abs((end - target).days) <= tolerance_days]
    return min(close, key=lambda p: abs((p["end"] - target).days)) if close else None


def parse_number(written: str) -> float | None:
    """A number as a filing writes it: '94,930', '$1.64', '(1,234)' (negative)."""
    text = written.replace("$", "").replace(" ", "").strip()
    negative = text.startswith("(") and text.endswith(")") or text.startswith("-")
    text = text.strip("()-")
    if not re.fullmatch(r"\d{1,3}(,\d{3})+(\.\d+)?|\d+(\.\d+)?", text):
        return None
    value = float(text.replace(",", ""))
    return -value if negative else value
```

### filings.py

```python
"""Company filings: what your tracked companies file with the SEC, and a first take on each.

check() asks the SEC (free, see edgar.py) for each tracked company's new filings: results
announcements, other announcements (8-K), quarterly and annual reports, and notices that a
report will be late. Listing them costs nothing.

read() gives one filing to Claude and saves a first take: a headline, the key points, and for
results the reported figures, guidance, and what changed since the last announcement. Every
point carries a quote, and the quote is checked against the filing in code: anything Claude
can't quote exactly is dropped. Figures are never worked out by Claude. It copies each number
as written; the comparisons with earlier quarters use the SEC's structured data, in code.

- Automatic: a results announcement is read when it's found (if filed in the last 3 days).
- On request: any other filing, from the Filings tab ("Read this filing") or the terminal.
- When the quarterly or annual report arrives, its structured figures are compared with the
  announcement's, and each one is marked confirmed or different. That part is free.

    python filings.py check                          look for new filings now
    python filings.py list [--ticker MSFT]           the latest filings
    python filings.py read 0000789019-26-000123      read one filing now (costs a few cents)
    python filings.py show 0000789019-26-000123      a filing's first take
    python filings.py figures MSFT                   quarterly figures from the SEC's structured data
"""

import argparse
import asyncio
import json
import re
from contextlib import closing
from datetime import date, datetime, timedelta, timezone

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query

import alerts
import edgar
import events
import market_tools
import reports_db
from events import transaction

LOOKBACK_DAYS = 120           # how far back filings are listed (far enough for last quarter's results)
AUTOMATIC_WITHIN_DAYS = 3     # only results this recent are read automatically, and only filings this recent go to Discord
MAX_AUTOMATIC = 5             # most automatic reads in one check
READ_BUDGET_USD = 0.50        # hard stop on Claude's cost per read
MAX_CHARS = 60_000            # the most of a filing Claude is given (about 15,000 tokens)
PREVIOUS_CHARS = 20_000       # ...and of the previous results announcement, for comparison
COVER_CHARS = 12_000          # ...and of an announcement's cover document, before its press release
MAX_POINTS = 6
MIN_QUOTE = 12                # a quote shorter than this proves nothing
FIGURES_WITHIN_DAYS = 45      # how long a report's structured figures are looked for after it's filed
FILER_RECHECK_DAYS = 30       # how often to ask again about a ticker the SEC didn't know
STUCK_AFTER = timedelta(minutes=10)  # a "running" read older than this is treated as crashed
UNREACHABLE_LIMIT = 2         # companies in a row that can't be reached before a check gives up

FORMS = {"8-K": "announcement", "10-Q": "quarterly", "10-K": "annual", "NT 10-Q": "late", "NT 10-K": "late",
         "6-K": "foreign", "20-F": "annual", "40-F": "annual"}
KIND_LABELS = {"results": "Results", "announcement": "Announcement", "quarterly": "Quarterly report",
               "annual": "Annual report", "late": "Late-report notice", "foreign": "Report from outside the US"}
# What each part ("item") of an announcement means, in plain words
ITEMS = {
    "1.01": "A major agreement signed", "1.02": "A major agreement ended", "1.03": "Bankruptcy or receivership",
    "1.05": "A serious cybersecurity incident", "2.01": "An acquisition or sale completed", "2.02": "Results announced",
    "2.03": "New debt or a similar obligation", "2.04": "An event that brings a debt due early",
    "2.05": "Restructuring or closures, with their costs", "2.06": "A large write-down of assets",
    "3.01": "A warning about staying listed on its exchange", "3.02": "Shares sold privately",
    "3.03": "Shareholders' rights changed", "4.01": "A change of auditor",
    "4.02": "Earlier financial statements can no longer be relied on", "5.01": "A change in who controls the company",
    "5.02": "Directors or senior officers leaving or appointed", "5.03": "Changes to its bylaws or financial year",
    "5.07": "Results of a shareholder vote", "7.01": "Information shared with investors", "8.01": "Other events",
    "9.01": "Financial statements and exhibits",
}
# Announcements worth a second look, highlighted in the list and sent to Discord (without Claude)
SERIOUS_ITEMS = {"1.03", "1.05", "2.01", "2.04", "2.05", "2.06", "3.01", "4.01", "4.02", "5.01", "5.02"}
DIRECTIONS = {"raised": "Raised", "lowered": "Lowered", "maintained": "Kept", "new": "New", "withdrawn": "Withdrawn"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS filers (
    ticker     TEXT PRIMARY KEY,
    cik        INTEGER,              -- the SEC's number for the company; NULL if it lists none (a fund, say)
    name       TEXT,
    checked_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS filings (
    ticker      TEXT NOT NULL,
    accession   TEXT NOT NULL,       -- the SEC's number for the filing, e.g. 0000789019-26-000123
    cik         INTEGER NOT NULL,
    form        TEXT NOT NULL,       -- 8-K, 10-Q, 10-K, NT 10-Q, 6-K... (with /A if amended)
    items       TEXT NOT NULL DEFAULT '',   -- an announcement's parts, e.g. "2.02,9.01"
    kind        TEXT NOT NULL CHECK (kind IN ('results', 'announcement', 'quarterly', 'annual', 'late', 'foreign')),
    title       TEXT NOT NULL,
    serious     INTEGER NOT NULL DEFAULT 0,
    amended     INTEGER NOT NULL DEFAULT 0,
    filed_at    TEXT NOT NULL,       -- when the SEC accepted it (UTC)
    filing_date TEXT NOT NULL,       -- the SEC's filing date (New York)
    report_date TEXT,                -- reports: the last day of the period they cover
    primary_doc TEXT,
    figures     TEXT,                -- reports: figures from the SEC's structured data (JSON)
    first_seen  TEXT NOT NULL,
    PRIMARY KEY (ticker, accession)
);
CREATE INDEX IF NOT EXISTS idx_filings_filed ON filings (filed_at);
CREATE TABLE IF NOT EXISTS filing_reads (
    id           INTEGER PRIMARY KEY,
    accession    TEXT NOT NULL,
    ticker       TEXT NOT NULL,
    trigger      TEXT NOT NULL CHECK (trigger IN ('automatic', 'manual')),
    status       TEXT NOT NULL CHECK (status IN ('running', 'ok', 'failed')),
    headline     TEXT,
    points       TEXT,               -- JSON: [{text, quote}]
    guidance     TEXT,               -- JSON: [{text, direction, quote}]
    changes      TEXT,               -- JSON: [{text, quote}]: what's new since the previous announcement
    figures      TEXT,               -- JSON: the reported figures, compared and checked in code
    notes        TEXT,               -- JSON: plain sentences about anything left out or cut short
    document     TEXT,               -- the document that was read
    document_url TEXT,
    chars        INTEGER NOT NULL DEFAULT 0,
    cut_off      INTEGER NOT NULL DEFAULT 0,
    cost_usd     REAL NOT NULL DEFAULT 0,
    error        TEXT,
    started_at   TEXT NOT NULL,
    finished_at  TEXT
);
CREATE INDEX IF NOT EXISTS idx_filing_reads ON filing_reads (accession);
CREATE TABLE IF NOT EXISTS filing_checks (
    id          INTEGER PRIMARY KEY,
    finished_at TEXT NOT NULL,
    trigger     TEXT NOT NULL,
    status      TEXT NOT NULL CHECK (status IN ('ok', 'partial', 'failed')),
    companies   INTEGER NOT NULL DEFAULT 0,
    new_filings INTEGER NOT NULL DEFAULT 0,
    reads       INTEGER NOT NULL DEFAULT 0,
    cost_usd    REAL NOT NULL DEFAULT 0,
    message     TEXT
);
CREATE TABLE IF NOT EXISTS filing_alerts (
    accession  TEXT PRIMARY KEY,
    what       TEXT NOT NULL,
    status     TEXT NOT NULL CHECK (status IN ('pending', 'sent', 'failed')),
    error      TEXT,
    created_at TEXT NOT NULL,
    sent_at    TEXT
);
"""

RULES = """
Rules:
- Reply with JSON only, in the shape shown.
- Every "quote" must be copied exactly from the FILING TEXT (one sentence, or one table row), so it can be
  checked. Anything you can't quote exactly, leave out.
- Use only the filing. Never add outside knowledge, explain the share price, predict anything or give advice.
- Write plainly, in short sentences."""

RESULTS_PROMPT = """You read a company's results announcement and write a first take for an analyst.

Reply in this shape:
{"headline": "One sentence: what the company reported.",
 "period_end": "2026-09-30",
 "figures": [{"metric": "revenue", "as_written": "77,673", "scale": "millions", "quote": "Total revenue | $77,673 | $65,585"}],
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}],
 "guidance": [{"text": "What the company said about the period ahead.", "direction": "raised", "quote": "..."}],
 "changes": [{"text": "Something new, or dropped, compared with the previous announcement.", "quote": "..."}]}

- period_end: the last day of the quarter reported.
- figures: only these metrics, when the filing gives them: revenue, gross_profit, operating_income, net_income,
  eps_diluted. Use the standard (GAAP) figure for the quarter alone: three months, not the year to date, and
  not an "adjusted" or "non-GAAP" figure. "as_written" is the number exactly as it appears in your quote.
  "scale" is units, thousands, millions or billions (tables usually say, e.g. "in millions"). eps_diluted is always units.
  Never work anything out: no growth rates, margins or totals of your own.
- points: 3 to 6, most important first.
- guidance: one entry per outlook the company gives. direction is raised, lowered, maintained, new or withdrawn,
  compared with what it said before. Use [] if it gives none.
- changes: only if a PREVIOUS ANNOUNCEMENT is given. Quote from the new filing, never from the previous one. Use [] otherwise.""" + RULES

ANNOUNCEMENT_PROMPT = """You read a company's announcement filed with the SEC and write a first take for an analyst.

Reply in this shape:
{"headline": "One sentence: what the company announced.",
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}]}

- points: 1 to 5, most important first: what happened, who and when, and any amounts the filing gives.""" + RULES

REPORT_PROMPT = """You read management's discussion from a company's quarterly or annual report and write a first take
for an analyst who has already seen the headline figures.

Reply in this shape:
{"headline": "One sentence: the most important thing the report adds.",
 "points": [{"text": "A key point.", "quote": "The exact words it's based on."}]}

- points: 3 to 6, most important first: what drove the results, costs, cash, risks, and anything management
  says has changed.""" + RULES


def _options(system_prompt: str) -> ClaudeAgentOptions:
    return ClaudeAgentOptions(system_prompt=system_prompt, mcp_servers={}, strict_mcp_config=True, tools=[],
                              max_turns=1, max_budget_usd=READ_BUDGET_USD)


class FilingError(ValueError):
    """Something that can't be done, with a message to show as it is. status is the HTTP status."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def now_utc() -> datetime:
    """Now, by the same clock as the rest of the program. The test environment replaces this with the sample's."""
    return market_tools.now_et().astimezone(timezone.utc)


def _stamp(moment: datetime) -> str:
    return moment.strftime("%Y-%m-%dT%H:%M:%SZ")


def _utc_now() -> str:
    return _stamp(now_utc())


def _days_ago(days: int) -> str:
    return _stamp(now_utc() - timedelta(days=days))


def connect():
    """The reports database, with the filings tables added if they're missing."""
    conn = events.connect()
    conn.executescript(SCHEMA)
    return conn


# ---------------------------------------------------------------------------
# Naming a filing
# ---------------------------------------------------------------------------

def describe(form: str, items: list[str]) -> dict | None:
    """What kind of filing this is, in plain words. None for forms that aren't followed."""
    form = " ".join(str(form).upper().split())
    amended = form.endswith("/A")
    base = form[:-2] if amended else form
    kind = FORMS.get(base)
    if kind is None:
        return None
    others = [ITEMS.get(i, f"Item {i}") for i in items if i not in ("2.02", "9.01")]
    if kind == "announcement" and "2.02" in items:
        kind, title = "results", "; ".join(["Results announcement", *others])
    elif kind == "announcement":
        title = "; ".join(others) or "Announcement"
    elif kind == "late":
        title = f"Says its {'annual' if base.endswith('10-K') else 'quarterly'} report will be late"
    else:
        title = {"quarterly": "Quarterly report", "annual": "Annual report",
                 "foreign": "Report from a company based outside the US"}[kind]
    return {"kind": kind, "amended": amended, "title": ("Amended: " if amended else "") + title,
            "serious": kind == "late" or bool(SERIOUS_ITEMS & set(items))}


def money(value: float | None, unit: str = "USD") -> str:
    """$77.67B, $420.5M, $3.72 a share."""
    if value is None:
        return "—"
    sign, size = ("-" if value < 0 else ""), abs(value)
    if unit != "USD":
        return f"{sign}${size:.2f}"
    if size >= 1e9:
        return f"{sign}${size / 1e9:.2f}B"
    if size >= 1e6:
        return f"{sign}${size / 1e6:.1f}M"
    return f"{sign}${size:,.0f}"


def _company(conn, ticker: str) -> str:
    """A short company name without asking Yahoo: the calendar's, else the SEC's."""
    if ticker in events._names:
        return events._names[ticker]
    try:
        row = conn.execute("SELECT company FROM events WHERE ticker = ? ORDER BY id DESC LIMIT 1", (ticker,)).fetchone()
        if row:
            return row[0]
    except Exception:
        pass
    try:
        row = conn.execute("SELECT name FROM filers WHERE ticker = ?", (ticker,)).fetchone()
    except Exception:
        row = None
    return events.short_name((row["name"] or "").title()) if row and row["name"] else ticker


# ---------------------------------------------------------------------------
# Figures: comparing and checking, all in code
# ---------------------------------------------------------------------------

def _change(now: float | None, then: float | None) -> float | None:
    """Percentage change, or None when it would mislead (from zero or from a loss)."""
    if now is None or then is None or then <= 0:
        return None
    return round((now - then) / then * 100, 1)


def _earlier(by_end: dict, period_end: date, days: int) -> dict | None:
    found = edgar.nearest(by_end, period_end - timedelta(days=days))
    return None if found is None else {"end": found["end"].isoformat(), "value": found["value"], "derived": found["derived"]}


def agrees(metric: str, announced: float, reported: float) -> bool:
    """Do an announcement's figure and the report's match? Announcements round (to the million, or to a
    tenth of a billion in a sentence), so a small gap is allowed."""
    if edgar.METRICS[metric]["unit"] != "USD":
        return abs(announced - reported) <= 0.011
    return abs(announced - reported) <= max(abs(reported) * 0.006, 600_000)


def _margins(rows: list[dict]) -> list[dict]:
    """Each profit line as a share of revenue, for this period and the ones it's compared with."""
    by_metric = {r["metric"]: r for r in rows}
    revenue = by_metric.get("revenue")
    margins = []
    for metric, label in (("gross_profit", "Gross margin"), ("operating_income", "Operating margin"), ("net_income", "Net margin")):
        row = by_metric.get(metric)
        if not revenue or not row:
            continue

        def share(part, whole):
            return round(part / whole * 100, 1) if part is not None and whole else None
        margins.append({"label": label, "value": share(row["value"], revenue["value"]),
                        "prior": share((row["prior"] or {}).get("value"), (revenue["prior"] or {}).get("value")),
                        "year_ago": share((row["year_ago"] or {}).get("value"), (revenue["year_ago"] or {}).get("value"))})
    return [m for m in margins if m["value"] is not None]


def compare(reported: list[dict], period_end: date | None, known: dict, notes: list[str]) -> dict:
    """An announcement's figures next to earlier quarters from the SEC's structured data, and checked
    against the quarterly report's own figure if that's already filed."""
    rows = []
    for r in reported:
        metric, spec = r["metric"], edgar.METRICS[r["metric"]]
        quarters = (known.get(metric) or {}).get("quarters") or {}
        row = {"metric": metric, "label": spec["label"], "unit": spec["unit"], "value": r["value"],
               "as_written": r["as_written"], "scale": r["scale"], "quote": r["quote"],
               "prior": None, "year_ago": None, "change_prior_pct": None, "change_year_pct": None,
               "check": "pending", "report_value": None}
        if period_end:
            row["prior"], row["year_ago"] = _earlier(quarters, period_end, 91), _earlier(quarters, period_end, 365)
            nearby = row["prior"] or row["year_ago"]
            if spec["unit"] == "USD" and nearby and nearby["value"] > 0 and r["value"] > 0 \
                    and not 0.05 <= r["value"] / nearby["value"] <= 20:
                notes.append(f"{spec['label']} was left out: {r['as_written']} {r['scale']} doesn't fit with "
                             f"{money(nearby['value'])} in the quarter to {nearby['end']}, so the unit is probably wrong.")
                continue
            row["change_prior_pct"] = _change(r["value"], (row["prior"] or {}).get("value"))
            row["change_year_pct"] = _change(r["value"], (row["year_ago"] or {}).get("value"))
        rows.append(row)
    result = {"basis": "quarter", "source": "announcement", "period_end": period_end.isoformat() if period_end else None,
              "rows": rows, "margins": _margins(rows)}
    if period_end:
        confirm(result, known)
    return result


def confirm(figures: dict, known: dict) -> bool:
    """Mark each announced figure confirmed or different, once the report's own figure is known.
    Returns True if anything changed."""
    if not figures or figures.get("source") != "announcement" or not figures.get("period_end"):
        return False
    period_end, changed = date.fromisoformat(figures["period_end"]), False
    for row in figures["rows"]:
        if row["check"] != "pending":
            continue
        filed = edgar.nearest((known.get(row["metric"]) or {}).get("quarters") or {}, period_end, 7)
        if filed is None:
            continue
        if filed["derived"] and row["unit"] != "USD":
            row["check"] = "not_checked"  # a fourth quarter's earnings per share can't be worked out exactly
        else:
            row["check"] = "confirmed" if agrees(row["metric"], row["value"], filed["value"]) else "differs"
            row["report_value"] = filed["value"]
        changed = True
    return changed


def report_figures(known: dict, period_end: date, annual: bool) -> dict | None:
    """A quarterly or annual report's own figures, with the periods before. None if they aren't published yet."""
    rows = []
    for metric, spec in edgar.METRICS.items():
        by_end = (known.get(metric) or {}).get("years" if annual else "quarters") or {}
        now = edgar.nearest(by_end, period_end, 7)
        if now is None or (now["derived"] and not annual):
            continue
        prior = None if annual else _earlier(by_end, period_end, 91)
        year_ago = _earlier(by_end, period_end, 365)
        rows.append({"metric": metric, "label": spec["label"], "unit": spec["unit"], "value": now["value"],
                     "prior": prior, "year_ago": year_ago, "change_prior_pct": _change(now["value"], (prior or {}).get("value")),
                     "change_year_pct": _change(now["value"], (year_ago or {}).get("value")), "check": "report"})
    if not rows:
        return None
    return {"basis": "year" if annual else "quarter", "source": "report", "period_end": period_end.isoformat(),
            "rows": rows, "margins": _margins(rows)}


# ---------------------------------------------------------------------------
# Checking Claude's reply against the filing
# ---------------------------------------------------------------------------

def _plain(text: str) -> str:
    return " ".join(edgar.tidy(str(text)).replace("|", " ").lower().split())


def quoted(quote, document: str) -> bool:
    """Is this quote really in the document? `document` is already _plain(). A quote may skip words
    with "...", as long as each piece is there, in order."""
    pieces = [p.strip(" .") for p in re.split(r"\.\.\.|…", _plain(quote or ""))]
    pieces = [p for p in pieces if p]
    if not pieces or sum(len(p) for p in pieces) < MIN_QUOTE:
        return False
    at = 0
    for piece in pieces:
        at = document.find(piece, at)
        if at < 0:
            return False
        at += len(piece)
    return True


def _json(text: str) -> dict:
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end < start:
        raise ValueError("Claude's reply had no JSON in it")
    data = json.loads(text[start:end + 1])
    if not isinstance(data, dict):
        raise ValueError("Claude's reply wasn't in the shape asked for")
    return data


def _entries(data: dict, key: str, document: str, dropped: list[str], extra=None) -> list[dict]:
    """A list of {text, quote} from Claude's reply, keeping only those whose quote is in the filing."""
    kept = []
    for entry in data.get(key) if isinstance(data.get(key), list) else []:
        if not isinstance(entry, dict):
            continue
        text, quote = " ".join(str(entry.get("text") or "").split()), " ".join(str(entry.get("quote") or "").split())
        if not text:
            continue
        if not quoted(quote, document):
            dropped.append(key)
            continue
        item = {"text": text[:500], "quote": quote[:600]}
        if extra:
            item.update(extra(entry))
        kept.append(item)
    return kept[:MAX_POINTS]


def check_reply(text: str, document: str, kind: str, filing_date: date) -> dict:
    """Claude's reply, checked: {headline, period_end, reported, points, guidance, changes, notes}.
    Raises ValueError if nothing in it can be trusted."""
    data, plain, dropped, notes = _json(text), _plain(document), [], []
    headline = " ".join(str(data.get("headline") or "").split())[:300]
    if not headline:
        raise ValueError("Claude's reply had no headline")
    points = _entries(data, "points", plain, dropped)
    if not points:
        raise ValueError("Claude's reply quoted nothing that's in the filing")
    result = {"headline": headline, "period_end": None, "reported": [], "points": points, "guidance": [],
              "changes": [], "notes": notes}
    if kind == "results":
        result["guidance"] = _entries(data, "guidance", plain, dropped, lambda e: {
            "direction": str(e.get("direction") or "").lower() if str(e.get("direction") or "").lower() in DIRECTIONS else "new"})
        result["changes"] = _entries(data, "changes", plain, dropped)
        try:
            period_end = date.fromisoformat(str(data.get("period_end"))[:10])
            if not filing_date - timedelta(days=200) <= period_end <= filing_date:
                raise ValueError
            result["period_end"] = period_end
        except ValueError:
            notes.append("The quarter's end date wasn't clear, so the figures aren't compared with earlier quarters.")
        seen = set()
        for entry in data.get("figures") if isinstance(data.get("figures"), list) else []:
            if not isinstance(entry, dict) or entry.get("metric") not in edgar.METRICS or entry.get("metric") in seen:
                continue
            metric, written = entry["metric"], str(entry.get("as_written") or "").strip()
            scale = "units" if edgar.METRICS[metric]["unit"] != "USD" else str(entry.get("scale") or "").lower()
            quote, number = " ".join(str(entry.get("quote") or "").split()), edgar.parse_number(written)
            if number is None or scale not in edgar.SCALES or not quoted(quote, plain) \
                    or written.replace(" ", "") not in quote.replace(" ", ""):
                dropped.append("figures")
                continue
            seen.add(metric)
            result["reported"].append({"metric": metric, "value": number * edgar.SCALES[scale], "as_written": written,
                                       "scale": scale, "quote": quote[:600]})
    if dropped:
        n = len(dropped)
        notes.append(f"{n} item{'s' if n != 1 else ''} from Claude {'were' if n != 1 else 'was'} left out, "
                     f"because {'their quotes aren' if n != 1 else 'its quote isn'}'t in the filing.")
    return result


# ---------------------------------------------------------------------------
# Finding filings
# ---------------------------------------------------------------------------

def _tracked() -> list[str]:
    try:
        return market_tools.load_watchlist()
    except OSError:
        return []


def _filers(conn, tickers: list[str]) -> dict[str, int | None]:
    """Each tracked ticker's SEC company number, asking the SEC only about tickers it hasn't seen
    (or didn't know a month ago)."""
    known = {r["ticker"]: r for r in conn.execute("SELECT * FROM filers")}
    again = _days_ago(FILER_RECHECK_DAYS)
    missing = [t for t in tickers if t not in known or (known[t]["cik"] is None and known[t]["checked_at"] < again)]
    if missing:
        listed = edgar.company_numbers()
        with transaction(conn):
            for t in missing:
                entry = listed.get(t.upper()) or listed.get(t.upper().replace(".", "-")) or {}
                conn.execute("INSERT OR REPLACE INTO filers (ticker, cik, name, checked_at) VALUES (?, ?, ?, ?)",
                             (t, entry.get("cik"), entry.get("name"), _utc_now()))
        known = {r["ticker"]: r for r in conn.execute("SELECT * FROM filers")}
    return {t: known[t]["cik"] for t in tickers if t in known}


def check(trigger: str = "command line", emit=None, read_new: bool = True) -> dict:
    """Look for new filings from every tracked company (free), read new results announcements
    (a few cents each), compare reports' figures with what was announced (free), and send any
    Discord messages. Returns the saved check. Raises EdgarError if the SEC can't be asked at all."""
    emit = emit or (lambda event: None)
    today = events.today_et()
    since = (today - timedelta(days=LOOKBACK_DAYS)).isoformat()
    problems, new, facts = [], [], {}
    with closing(connect()) as conn:
        try:
            numbers = _filers(conn, _tracked())
        except edgar.ContactMissing:
            raise
        except edgar.EdgarError as e:
            numbers = {r["ticker"]: r["cik"] for r in conn.execute("SELECT ticker, cik FROM filers")}
            problems.append(f"the SEC's company list: {e}")
        companies, unreachable = {}, 0
        for ticker, cik in numbers.items():
            if cik is not None:
                companies.setdefault(cik, []).append(ticker)  # two share classes are one company: asked once
        for cik, tickers in companies.items():
            emit({"type": "progress", "message": f"Checking {' and '.join(tickers)}'s filings"})
            try:
                listed = edgar.list_filings(cik)["filings"]
            except edgar.ContactMissing:
                raise
            except edgar.EdgarError as e:
                problems.append(f"{tickers[0]}: {e}")
                if e.status in (403, 429):  # being limited: asking for the rest would only make it worse
                    break
                unreachable = unreachable + 1 if e.status is None else 0
                if unreachable >= UNREACHABLE_LIMIT:  # the SEC is down or the network is: don't hold a run up for every company
                    problems.append("stopped there: the SEC can't be reached right now")
                    break
                continue
            unreachable = 0
            with transaction(conn):
                for f in listed:
                    about = describe(f["form"], f["items"])
                    if about is None or f["filing_date"] < since or not f["filed_at"]:
                        continue
                    for ticker in tickers:
                        added = conn.execute(
                            """INSERT OR IGNORE INTO filings (ticker, accession, cik, form, items, kind, title, serious,
                               amended, filed_at, filing_date, report_date, primary_doc, first_seen)
                               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (ticker, f["accession"], cik, f["form"], ",".join(f["items"]), about["kind"], about["title"],
                             int(about["serious"]), int(about["amended"]), f["filed_at"], f["filing_date"],
                             f["report_date"] or None, f["primary_doc"], _utc_now())).rowcount
                        if added:
                            new.append({"ticker": ticker, "accession": f["accession"], "title": about["title"]})
        recent = _days_ago(AUTOMATIC_WITHIN_DAYS)
        due = [] if not read_new else [r["accession"] for r in conn.execute(
            """SELECT accession, MAX(filed_at) AS filed FROM filings f
               WHERE kind = 'results' AND amended = 0 AND filed_at >= ?
                 AND NOT EXISTS (SELECT 1 FROM filing_reads r WHERE r.accession = f.accession)
               GROUP BY accession ORDER BY filed DESC LIMIT ?""", (recent, MAX_AUTOMATIC))]
    reads = []
    for accession in due:
        try:
            reads.append(read(accession, "automatic", emit, facts))
        except Exception as e:  # one filing failing doesn't stop the rest
            problems.append(f"{accession}: {e}")
    with closing(connect()) as conn:
        problems += _fill_figures(conn, today, facts, emit)
    try:
        sent = notify(recent)
    except Exception as e:
        sent = {"sent": [], "failed": [f"Discord ({e})"]}
    problems += [f"Discord: {label}" for label in sent["failed"]]
    cost = round(sum(r["cost_usd"] for r in reads), 4)
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute("""INSERT INTO filing_checks (finished_at, trigger, status, companies, new_filings, reads, cost_usd, message)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                         (_utc_now(), trigger, "partial" if problems else "ok", len(companies), len(new), len(reads), cost,
                          "; ".join(problems)[:1000] or None))
        summary = last_check(conn)
    summary.update(new=new, read=[{"ticker": r["ticker"], "accession": r["accession"], "status": r["status"],
                                   "headline": r["headline"], "error": r["error"]} for r in reads], alerts=sent["sent"])
    return summary


def _facts(cik: int, cache: dict) -> dict:
    """A company's quarterly and yearly figures, downloaded once per check."""
    if cik not in cache:
        cache[cik] = edgar.periods(edgar.company_facts(cik))
    return cache[cik]


def _fill_figures(conn, today: date, cache: dict, emit) -> list[str]:
    """For each recent quarterly or annual report: save its own figures, and use them to confirm
    (or contradict) the figures in that quarter's results announcement. No Claude."""
    problems = []
    since = (today - timedelta(days=FIGURES_WITHIN_DAYS)).isoformat()
    reports = conn.execute(
        """SELECT * FROM filings WHERE kind IN ('quarterly', 'annual') AND amended = 0 AND report_date IS NOT NULL
           AND filing_date >= ? ORDER BY filed_at""", (since,)).fetchall()
    for report in reports:
        period_end = date.fromisoformat(report["report_date"])
        waiting = [r for r in conn.execute(
            "SELECT id, figures FROM filing_reads WHERE ticker = ? AND status = 'ok' AND figures IS NOT NULL",
            (report["ticker"],)) if _pending(r["figures"], period_end)]
        if report["figures"] is not None and not waiting:
            continue
        if not report["form"].startswith("10-"):
            continue  # companies outside the US don't file figures in this form
        try:
            emit({"type": "progress", "message": f"Fetching the figures from {report['ticker']}'s report"})
            known = _facts(report["cik"], cache)
        except edgar.EdgarError as e:
            problems.append(f"{report['ticker']}'s figures: {e}")
            continue
        own = report_figures(known, period_end, annual=report["kind"] == "annual")
        settled = own is not None or report["filing_date"] < (today - timedelta(days=3)).isoformat()
        if own is None and settled:  # the SEC publishes figures within minutes: after days, there are none to wait for
            own = {"basis": "year" if report["kind"] == "annual" else "quarter", "source": "report",
                   "period_end": report["report_date"], "rows": [], "margins": []}
        with transaction(conn):
            if own is not None and report["figures"] is None:
                conn.execute("UPDATE filings SET figures = ? WHERE ticker = ? AND accession = ?",
                             (json.dumps(own), report["ticker"], report["accession"]))
            for row in waiting:
                figures = json.loads(row["figures"])
                changed = confirm(figures, known)
                if settled:  # the report is in, so a figure it doesn't give can't be checked
                    for r in figures["rows"]:
                        if r["check"] == "pending":
                            r["check"], changed = "not_checked", True
                if changed:
                    conn.execute("UPDATE filing_reads SET figures = ? WHERE id = ?", (json.dumps(figures), row["id"]))
    return problems


def _pending(figures_json: str, period_end: date) -> bool:
    try:
        figures = json.loads(figures_json)
        return bool(figures.get("period_end")) and abs((date.fromisoformat(figures["period_end"]) - period_end).days) <= 7 \
            and any(r["check"] == "pending" for r in figures["rows"])
    except (ValueError, KeyError, TypeError):
        return False


def check_before_run(emit=None) -> dict | None:
    """What a run does first, so the brief can use today's filings. Never raises: a problem here
    is shown as a warning, and the run carries on."""
    emit = emit or (lambda event: None)
    try:
        result = check("before a run", lambda event: emit(event) if event.get("type") != "progress"
                       or event["message"].startswith(("Reading", "First take")) else None)
    except Exception as e:
        emit({"type": "warning", "message": f"Filings weren't checked ({e}). The run carries on without them."})
        return None
    if result["new"]:
        names = ", ".join(f"{f['ticker']} ({f['title'].split(';')[0].lower()})" for f in result["new"][:4])
        more = f" and {len(result['new']) - 4} more" if len(result["new"]) > 4 else ""
        emit({"type": "filings", "message": f"Filings: {len(result['new'])} new: {names}{more}"})
    for label in result["alerts"]:
        emit({"type": "alert", "message": f"Discord: sent {label}"})
    if result["message"]:
        emit({"type": "warning", "message": f"Filings: {result['message']}"})
    return result


# ---------------------------------------------------------------------------
# Reading one filing
# ---------------------------------------------------------------------------

async def _ask_claude_async(system_prompt: str, prompt: str) -> tuple[str, float]:
    result = None
    async for message in query(prompt=prompt, options=_options(system_prompt)):
        if isinstance(message, ResultMessage):
            result = message
    if result is None or result.is_error or not result.result:
        raise RuntimeError(f"Claude couldn't read the filing: {result.subtype if result else 'no result'}")
    return result.result, result.total_cost_usd or 0.0


def ask_claude(system_prompt: str, prompt: str) -> tuple[str, float]:
    """Claude's reply (JSON text) and its cost. Tests and the test environment replace this."""
    return asyncio.run(_ask_claude_async(system_prompt, prompt))


def _cut(text: str, limit: int) -> tuple[str, bool]:
    if len(text) <= limit:
        return text, False
    return text[:limit].rsplit("\n", 1)[0], True


def _press_release(documents: list[dict]) -> dict | None:
    exhibits = sorted((d for d in documents if d["type"].startswith("EX-99")), key=lambda d: d["type"])
    return exhibits[0] if exhibits else None


def _main(documents: list[dict], filing: dict) -> dict | None:
    return next((d for d in documents if d["name"] == filing["primary_doc"]), None) or (documents[0] if documents else None)


def gather(filing: dict) -> dict:
    """The text to read from a filing: {text, name, url, cut_off, notes}.
    - Results: the press release (the first EX-99 exhibit).
    - Other announcements: the filing's own text, then its press release if it has one.
    - Quarterly and annual reports: management's discussion of the results."""
    documents = edgar.filing_documents(filing["cik"], filing["accession"], filing["primary_doc"] or "", filing["form"])
    notes, press, main = [], _press_release(documents), _main(documents, filing)
    if filing["kind"] == "results" and press:
        chosen, text = press, edgar.to_text(edgar.get_text(press["url"]))
    elif filing["kind"] in ("quarterly", "annual"):
        if main is None:
            raise FilingError("This filing has no document that can be read.", 422)
        chosen, whole = main, edgar.to_text(edgar.get_text(main["url"]))
        text = edgar.discussion(whole, annual=filing["kind"] == "annual")
        if not text:
            text = whole
            notes.append("Management's discussion couldn't be found in the report, so the start of the report was read instead.")
    else:
        if main is None and press is None:
            raise FilingError("This filing has no document that can be read.", 422)
        chosen = main or press
        text = edgar.to_text(edgar.get_text(chosen["url"]))
        if main and press:
            text, _ = _cut(text, COVER_CHARS)
            text += f"\n\n--- Attached press release ({press['type']}) ---\n" + edgar.to_text(edgar.get_text(press["url"]))
        if filing["kind"] == "results":
            notes.append("This results filing has no press release attached, so the filing's own text was read.")
    if len(text.strip()) < 200:
        raise FilingError("This filing's document has no text that can be read (it may be a scan or a PDF).", 422)
    text, cut_off = _cut(text, MAX_CHARS)
    if cut_off:
        notes.append(f"The document is long: the first {MAX_CHARS:,} characters were read.")
    return {"text": text, "name": chosen["name"], "url": chosen["url"], "cut_off": cut_off, "notes": notes}


def _previous_announcement(conn, filing: dict) -> tuple[str, str] | None:
    """(filing date, text) of the results announcement before this one, for 'what changed'."""
    row = conn.execute(
        """SELECT * FROM filings WHERE ticker = ? AND kind = 'results' AND amended = 0 AND filed_at < ?
           ORDER BY filed_at DESC LIMIT 1""", (filing["ticker"], filing["filed_at"])).fetchone()
    if row is None:
        return None
    try:
        press = _press_release(edgar.filing_documents(row["cik"], row["accession"], row["primary_doc"] or "", row["form"]))
        if press is None:
            return None
        return row["filing_date"], _cut(edgar.to_text(edgar.get_text(press["url"])), PREVIOUS_CHARS)[0]
    except edgar.EdgarError:
        return None  # the comparison is a bonus: the read goes ahead without it


def build_prompt(filing: dict, company: str, text: str, previous: tuple[str, str] | None = None) -> str:
    lines = [f"COMPANY: {company} ({filing['ticker']})",
             f"FILING: {filing['title']}, filed {filing['filing_date']} (form {filing['form']}"
             + (f", items {filing['items']}" if filing["items"] else "") + ")"]
    if previous:
        lines += ["", f"PREVIOUS ANNOUNCEMENT (filed {previous[0]}), for comparison only. Never quote from it:",
                  "<<<", previous[1], ">>>"]
    lines += ["", 'FILING TEXT (in tables, cells are separated by " | "):', "<<<", text, ">>>"]
    return "\n".join(lines)


def _the_filing(conn, accession: str) -> dict:
    row = conn.execute("SELECT * FROM filings WHERE accession = ? ORDER BY ticker LIMIT 1", (accession,)).fetchone()
    if row is None:
        raise FilingError(f"No filing {accession} is listed. Check for new filings first.", 404)
    return dict(row)


def read(accession: str, trigger: str = "manual", emit=None, facts: dict | None = None) -> dict:
    """Read one filing with Claude now and save the first take. Returns the saved read."""
    emit = emit or (lambda event: None)
    facts = {} if facts is None else facts
    with closing(connect()) as conn:
        filing = _the_filing(conn, accession)
        company = _company(conn, filing["ticker"])
        stuck = _stamp(now_utc() - STUCK_AFTER)
        with transaction(conn):
            if conn.execute("SELECT 1 FROM filing_reads WHERE accession = ? AND status = 'running' AND started_at >= ?",
                            (accession, stuck)).fetchone():
                raise FilingError("This filing is already being read.", 409)
            read_id = conn.execute(
                "INSERT INTO filing_reads (accession, ticker, trigger, status, started_at) VALUES (?, ?, ?, 'running', ?)",
                (accession, filing["ticker"], trigger, _utc_now())).lastrowid
        previous = _previous_announcement(conn, filing) if filing["kind"] == "results" else None
    fields = {"status": "failed", "headline": None, "points": "[]", "guidance": "[]", "changes": "[]", "figures": None,
              "notes": "[]", "document": None, "document_url": None, "chars": 0, "cut_off": 0, "cost_usd": 0.0, "error": None}
    try:
        emit({"type": "progress", "message": f"Reading {company}'s {filing['title'].split(';')[0].lower()}"})
        source = gather(filing)
        fields.update(document=source["name"], document_url=source["url"], chars=len(source["text"]),
                      cut_off=int(source["cut_off"]))
        system = {"results": RESULTS_PROMPT, "quarterly": REPORT_PROMPT, "annual": REPORT_PROMPT}.get(
            filing["kind"], ANNOUNCEMENT_PROMPT)
        reply, cost = ask_claude(system, build_prompt(filing, company, source["text"], previous))
        fields["cost_usd"] = round(cost, 4)
        take = check_reply(reply, source["text"], filing["kind"], date.fromisoformat(filing["filing_date"]))
        notes = source["notes"] + take["notes"]
        if filing["kind"] == "results":
            try:
                known = _facts(filing["cik"], facts) if take["reported"] else {}
            except edgar.EdgarError as e:
                known = {}
                notes.append(f"Earlier quarters couldn't be fetched for comparison ({e}).")
            fields["figures"] = json.dumps(compare(take["reported"], take["period_end"], known, notes))
            if previous is None:
                notes.append("There's no earlier results announcement on file to compare the wording with.")
        fields.update(status="ok", headline=take["headline"], points=json.dumps(take["points"]),
                      guidance=json.dumps(take["guidance"]), changes=json.dumps(take["changes"]), notes=json.dumps(notes))
        emit({"type": "progress", "message": f"First take on {filing['ticker']}: {take['headline']}"})
    except Exception as e:  # saved as a failed read, so the reason is visible
        fields["error"] = str(e)[:500] or type(e).__name__
    with closing(connect()) as conn:
        with transaction(conn):
            conn.execute(f"""UPDATE filing_reads SET {', '.join(f'{k} = ?' for k in fields)}, finished_at = ?
                             WHERE id = ?""", (*fields.values(), _utc_now(), read_id))
        return get_read(conn, read_id)


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def _figure_line(row: dict) -> str:
    change = row.get("change_year_pct")
    return f"{row['label']} {money(row['value'], row['unit'])}" + (f" ({change:+.1f}% vs a year ago)" if change is not None else "")


def alert_payload(filing: dict, take: dict | None, company: str) -> dict:
    """One Discord message for a filing: a results first take, or a serious announcement."""
    link = alerts._app_link(f"#/filings/{filing['accession']}") or {"url": filing["url"]}
    footer = {"text": "From the company's SEC filing · research, not investment advice"}
    if filing["kind"] == "results" and take and take["status"] == "ok":
        lines = [take["headline"], ""]
        lines += [f"• {_figure_line(r)}" for r in (take["figures"] or {}).get("rows", [])]
        lines += [f"**Guidance ({DIRECTIONS[g['direction']].lower()}):** {g['text']}" for g in take["guidance"][:2]]
        lines += ["", f"[The filing on sec.gov]({filing['url']})"]
        return {"content": f"**{filing['ticker']} reported results**",
                "embeds": alerts._fit([{"title": alerts._shorten(f"{company}: results", alerts.MAX_TITLE),
                                        "description": alerts._shorten("\n".join(lines), alerts.MAX_DESCRIPTION),
                                        "color": alerts.COLORS["neutral"], "footer": footer, **link}])}
    lines = [filing["title"] + ".", "Not read by Claude yet: open the Filings tab to read it.",
             "", f"[The filing on sec.gov]({filing['url']})"]
    return {"content": f"**{filing['ticker']} filed with the SEC**",
            "embeds": [{"title": alerts._shorten(f"{company}: {filing['title']}", alerts.MAX_TITLE),
                        "description": alerts._shorten("\n".join(lines), alerts.MAX_DESCRIPTION),
                        "color": alerts.COLORS["neutral"], "footer": footer, **link}]}


def notify(since: str) -> dict:
    """Send a Discord message for each recent filing that calls for one and hasn't had one: a results
    announcement (with its first take, once it's read) or a serious announcement. One that fails is
    tried again by the next check. Returns {"sent": [...], "failed": [...]}."""
    outcome = {"sent": [], "failed": []}
    if not alerts.enabled():
        return outcome
    with closing(connect()) as conn:
        conn.execute("BEGIN IMMEDIATE")  # decide and claim in one step, so two checks can't both send
        try:
            pending = alerts._stamp(alerts._utc_now() - timedelta(seconds=alerts.PENDING_SECONDS))
            todo = []
            for filing in list_filings(conn, since=since):
                if filing["kind"] != "results" and not filing["serious"]:
                    continue
                take = filing["read"]
                if filing["kind"] == "results" and not filing["amended"] and (take is None or take["status"] == "running"):
                    continue  # wait for its first take
                done = conn.execute("SELECT status, created_at FROM filing_alerts WHERE accession = ?",
                                    (filing["accession"],)).fetchone()
                if done and (done["status"] == "sent" or (done["status"] == "pending" and done["created_at"] >= pending)):
                    continue
                if any(t[0]["accession"] == filing["accession"] for t in todo):
                    continue  # the same filing under a second ticker
                what = "first take" if filing["kind"] == "results" and take and take["status"] == "ok" else "filed"
                conn.execute("""INSERT OR REPLACE INTO filing_alerts (accession, what, status, created_at)
                                VALUES (?, ?, 'pending', ?)""", (filing["accession"], what, _utc_now()))
                todo.append((filing, take, _company(conn, filing["ticker"])))
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        for filing, take, company in todo:
            label = f"{filing['ticker']} {'results' if filing['kind'] == 'results' else 'filing'}"
            try:
                alerts.send(alert_payload(filing, take, company))
                conn.execute("UPDATE filing_alerts SET status = 'sent', error = NULL, sent_at = ? WHERE accession = ?",
                             (_utc_now(), filing["accession"]))
                outcome["sent"].append(label)
            except Exception as e:
                conn.execute("UPDATE filing_alerts SET status = 'failed', error = ? WHERE accession = ?",
                             (str(e) or type(e).__name__, filing["accession"]))
                outcome["failed"].append(f"{label} ({e})")
    return outcome


# ---------------------------------------------------------------------------
# Reading (the API, the agent's tool, Ask and the command line)
# ---------------------------------------------------------------------------

def _read_row(row) -> dict:
    r = dict(row)
    for key in ("points", "guidance", "changes", "notes"):
        r[key] = json.loads(r[key] or "[]")
    r["figures"] = json.loads(r["figures"]) if r["figures"] else None
    return r


def get_read(conn, read_id: int) -> dict:
    return _read_row(conn.execute("SELECT * FROM filing_reads WHERE id = ?", (read_id,)).fetchone())


def _filing_row(row, reads: dict) -> dict:
    f = dict(row)
    f["items"] = [{"code": code, "label": ITEMS.get(code, f"Item {code}")} for code in f["items"].split(",") if code]
    f["serious"], f["amended"] = bool(f["serious"]), bool(f["amended"])
    f["kind_label"] = KIND_LABELS[f["kind"]]
    f["figures"] = json.loads(f["figures"]) if f["figures"] else None
    f["url"] = edgar.index_url(f["cik"], f["accession"])
    f["read"] = reads.get(f["accession"])
    return f


def list_filings(conn, ticker: str | None = None, since: str | None = None, limit: int = 300,
                 accession: str | None = None) -> list[dict]:
    """Filings, newest first, each with its latest read. Works on a read-only connection,
    even before the first check."""
    limit = min(limit, 900)
    stuck = _stamp(now_utc() - STUCK_AFTER)
    try:
        rows = conn.execute(
            """SELECT * FROM filings WHERE (? IS NULL OR ticker = ?) AND (? IS NULL OR filed_at >= ?)
               AND (? IS NULL OR accession = ?) ORDER BY filed_at DESC, accession DESC, ticker LIMIT ?""",
            (ticker, ticker and ticker.upper(), since, since, accession, accession, limit)).fetchall()
        wanted = sorted({r["accession"] for r in rows})
        reads = {}
        for r in conn.execute(f"SELECT * FROM filing_reads WHERE accession IN ({','.join('?' * len(wanted))}) ORDER BY id",
                              wanted):
            taken = _read_row(r)
            if taken["status"] == "running" and taken["started_at"] < stuck:
                taken.update(status="failed", error="This read was interrupted. Try again.")
            if taken["status"] == "failed" and reads.get(r["accession"], {}).get("status") == "ok":
                continue  # the latest read wins, unless it failed and an earlier one worked
            reads[r["accession"]] = taken
    except Exception:  # no filings tables yet
        return []
    return [_filing_row(r, reads) for r in rows]


def get_filing(conn, accession: str) -> dict | None:
    found = list_filings(conn, accession=accession)
    return found[0] if found else None


def last_check(conn) -> dict | None:
    try:
        row = conn.execute("SELECT * FROM filing_checks ORDER BY id DESC LIMIT 1").fetchone()
    except Exception:
        return None
    return dict(row) if row else None


def not_covered(conn) -> list[str]:
    """Tracked tickers the SEC lists no company for (funds, and some companies listed elsewhere)."""
    try:
        missing = {r[0] for r in conn.execute("SELECT ticker FROM filers WHERE cik IS NULL")}
    except Exception:
        return []
    return [t for t in _tracked() if t in missing]


def _matches(filing: dict, event: dict) -> bool:
    """Is this results filing the earnings report this calendar event expected? Yahoo's dates can be a
    day or two out, and an unconfirmed date is the start of a window."""
    gap = (date.fromisoformat(filing["filing_date"]) - date.fromisoformat(event["event_date"])).days
    return filing["ticker"] == event["ticker"] and (-3 <= gap <= 3 if events.confirmed(event) else -3 <= gap <= 14)


def for_calendar(conn, calendar_events: list[dict], start: str, end: str) -> list[dict]:
    """Results announcements for the Calendar tab: each with the earnings event it answers (event_id),
    if the calendar had one. Covers `start` to `end`, plus whatever the given events matched."""
    earnings = [e for e in calendar_events if e["kind"] == "earnings"]
    since = (date.fromisoformat(start) - timedelta(days=15)).isoformat()
    until = (date.fromisoformat(end) + timedelta(days=15)).isoformat()
    found, seen = [], set()
    for f in list_filings(conn, since=since + "T00:00:00Z"):
        if f["kind"] != "results" or f["amended"] or f["filing_date"] > until or (f["ticker"], f["accession"]) in seen:
            continue
        seen.add((f["ticker"], f["accession"]))
        match = min((e for e in earnings if _matches(f, e)), default=None,
                    key=lambda e: abs((date.fromisoformat(f["filing_date"]) - date.fromisoformat(e["event_date"])).days))
        if match is None and not start <= f["filing_date"] <= end:
            continue
        take = f["read"] if f["read"] and f["read"]["status"] == "ok" else None
        found.append({"ticker": f["ticker"], "company": _company(conn, f["ticker"]), "accession": f["accession"],
                      "filing_date": f["filing_date"], "filed_at": f["filed_at"], "url": f["url"],
                      "headline": take["headline"] if take else None, "event_id": match["id"] if match else None})
    return found


def expected(conn, today: date) -> list[dict]:
    """Earnings the calendar expected in the last few days (or today) with no results announcement yet."""
    start = today - timedelta(days=3)
    due = [e for e in events.upcoming(conn, start, 3, _tracked() or None) if e["kind"] == "earnings"]
    reported = for_calendar(conn, due, start.isoformat(), today.isoformat())
    answered = {r["event_id"] for r in reported}
    return [{"ticker": e["ticker"], "company": e["company"], "event_date": e["event_date"],
             "confirmed": events.confirmed(e)} for e in due if e["id"] not in answered]


def recent_for(conn, ticker: str, since: str) -> list[dict]:
    """A ticker's recent filings, compact, for the brief's recent_filings tool."""
    found = []
    for f in list_filings(conn, ticker, since):
        take = f["read"] if f["read"] and f["read"]["status"] == "ok" else None
        entry = {"filed": f["filing_date"], "kind": f["kind_label"], "title": f["title"], "serious": f["serious"],
                 "url": f["url"], "first_take": None}
        if take:
            figures = take["figures"] or {}
            entry["first_take"] = {
                "headline": take["headline"], "points": [p["text"] for p in take["points"]],
                "guidance": [f"{DIRECTIONS[g['direction']]}: {g['text']}" for g in take["guidance"]],
                "figures": [_figure_line(r) + (f", {r['change_prior_pct']:+.1f}% vs the quarter before"
                                                if r.get("change_prior_pct") is not None else "")
                            for r in figures.get("rows", [])]}
        found.append(entry)
    return found


# ---------------------------------------------------------------------------
# Command line
# ---------------------------------------------------------------------------

def _print_take(filing: dict) -> None:
    take = filing["read"]
    print(f"{filing['ticker']}  {filing['title']}  (filed {filing['filing_date']}, {filing['form']})\n{filing['url']}")
    for label, figures in (("Figures from the report", filing["figures"]), ("Figures as announced", take and take["figures"])):
        if figures and figures["rows"]:
            print(f"\n{label} ({figures['basis']} to {figures['period_end']}):")
            for r in figures["rows"]:
                checked = {"confirmed": "  ✓ confirmed by the report", "differs": f"  ✗ the report says {money(r.get('report_value'), r['unit'])}"}
                print(f"  {_figure_line(r)}{checked.get(r['check'], '')}")
    if take is None:
        print("\nNot read yet: python filings.py read", filing["accession"])
        return
    if take["status"] != "ok":
        print(f"\nRead {take['status']}: {take['error'] or ''}")
        return
    print(f"\n{take['headline']}  (${take['cost_usd']:.3f})")
    for title, entries in (("Key points", take["points"]), ("Guidance", take["guidance"]), ("What changed", take["changes"])):
        if entries:
            print(f"\n{title}:")
            for e in entries:
                print(f"  - {e['text']}\n      \"{e['quote']}\"")
    for note in take["notes"]:
        print(f"\nNote: {note}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Company filings from the SEC, and first takes on them.")
    commands = parser.add_subparsers(dest="command", required=True)
    look = commands.add_parser("check", help="look for new filings now (free; reads new results announcements)")
    look.add_argument("--no-read", action="store_true", help="only list them: nothing is sent to Claude")
    show_list = commands.add_parser("list", help="the latest filings")
    show_list.add_argument("--ticker")
    for name, text in (("read", "read one filing with Claude now (costs a few cents)"), ("show", "a filing's first take")):
        commands.add_parser(name, help=text).add_argument("accession")
    commands.add_parser("figures", help="a company's quarterly figures from the SEC's structured data").add_argument("ticker")
    args = parser.parse_args()
    try:
        if args.command == "check":
            result = check(emit=lambda e: print(e["message"]), read_new=not args.no_read)
            print(f"{result['status']}: {result['new_filings']} new filing{'s' if result['new_filings'] != 1 else ''} from "
                  f"{result['companies']} companies, {result['reads']} read, ${result['cost_usd']:.3f}"
                  + (f" ({result['message']})" if result["message"] else ""))
        elif args.command == "list":
            with closing(reports_db.connect(readonly=True)) as conn:
                for f in list_filings(conn, args.ticker, limit=40):
                    state = "" if f["read"] is None else f"  [{'first take' if f['read']['status'] == 'ok' else f['read']['status']}]"
                    print(f"{f['filing_date']}  {f['ticker']:<6} {f['form']:<8} {f['accession']}  "
                          f"{'! ' if f['serious'] else ''}{f['title']}{state}")
        elif args.command == "read":
            taken = read(args.accession, emit=lambda e: print(e["message"]))
            if taken["status"] == "failed":
                raise SystemExit(f"failed: {taken['error']}")
            with closing(reports_db.connect(readonly=True)) as conn:
                _print_take(get_filing(conn, args.accession))
        elif args.command == "show":
            with closing(reports_db.connect(readonly=True)) as conn:
                filing = get_filing(conn, args.accession)
            if filing is None:
                raise SystemExit(f"No filing {args.accession} is listed.")
            _print_take(filing)
        else:
            ticker = args.ticker.upper()
            cik = (edgar.company_numbers().get(ticker) or {}).get("cik")
            if cik is None:
                raise SystemExit(f"The SEC lists no company under {ticker}.")
            for metric, found in edgar.periods(edgar.company_facts(cik)).items():
                print(f"\n{edgar.METRICS[metric]['label']} ({found['tag']})")
                for end in sorted(found["quarters"], reverse=True)[:8]:
                    q = found["quarters"][end]
                    print(f"  quarter to {end}  {money(q['value'], edgar.METRICS[metric]['unit']):>12}"
                          + ("  (worked out: the year minus the first nine months)" if q["derived"] else ""))
    except (FilingError, edgar.EdgarError) as e:
        raise SystemExit(str(e))


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
moves (followups.py), so briefs can say how similar moves played out. recent_filings reads
what companies have filed with the SEC (filings.py), so a move can be explained from the
company's own announcement.

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

### analyst_prompt.md

```markdown
You are an equity research analyst writing a short brief on the user's watchlist.

## Process

1. Call `flag_events` first. It returns the session status, the tickers with unusual moves, and the quiet ones.
2. Call `market_backdrop` once, for how the S&P 500 and each sector moved.
3. Call `upcoming_events` once, for what's coming up (see below).
4. If anything was flagged, call `past_moves` once, with the flagged tickers and each one's `context.read` as `kinds`. Then call `recent_filings` once, with the flagged tickers.
5. For each flagged ticker, read its `context` (see below) and any filings (see below), then call `get_news` to find the likely reason. Call `compute_moves` if you need more detail on a ticker.
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

## Company filings

`recent_filings` lists what each flagged company has filed with the SEC in the last few days: results announcements, other announcements and reports. A filing that has been read has a `first_take`: a headline, key points, figures and guidance, all checked against the filing.

- The company's own filing is the best source for "Likely why". If a flagged ticker has a filing with a `first_take`, lead with it, cited as [company filing](url) with the filing's `url`. Then add what the news says about how it was received.
- Use the first take's figures and guidance exactly as given. Never restate them from a news article instead.
- If a filing has no `first_take`, say what was filed (its `title`) and link it. Don't guess what it says.
- A filing marked `serious` is worth a mention in "Worth watching" even when the news explains the move another way.
- If the ticker is in `expected`, its results were due but hadn't been filed when you looked: say so in "Worth watching".
- `context.read` still comes first: a filing doesn't make a sector-wide or market-wide move company news.

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

Before writing, it looks for new company filings (filings.py), so the brief can explain a move
from the company's own announcement. After saving, it sends any Discord alerts the report calls
for (see alerts.py). After a final report, it also fills in the follow-through of earlier flagged
moves (followups.py) and checks the news on any that turned out to be surprises (stories.py).

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
import filings
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
        "mcp__market__recent_filings",
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
    # New filings first (free; a results announcement is read by Claude), so the brief can use them.
    # This runs even when the report is already saved: results often arrive after the close.
    await asyncio.to_thread(filings.check_before_run, emit)

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
4. Company filings (filings.py): for named tickers, their latest filings and first takes;
   otherwise, what was filed in the last week.
5. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
6. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing
from datetime import timedelta

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import events
import filings
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
- Company filings are what a company itself filed with the SEC: cite them as (filing, then the date it was filed).
  A first take's figures were checked against the filing: use them exactly as given. "Confirmed" means the
  quarterly report later gave the same figure. If a filing has no first take, say only that it was filed.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
CALENDAR_DAYS = 30               # events calendar: this far ahead (all tickers) and back (named tickers)
FOLLOWUP_MOVES = 10              # flagged moves' follow-through per named ticker
STORY_UPDATES = 3                # latest story updates per named ticker
FILING_TAKES = 2                 # latest first takes on filings, in full, per named ticker
FILINGS_LISTED = 8               # latest filings listed per named ticker
FILINGS_DAYS = 7                 # with no ticker named: filings from this many days back
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


def _take_lines(f: dict) -> list[str]:
    """One filing's first take as lines of text."""
    take = f["read"]
    lines = [f"### {f['ticker']}: {f['title']}, filed {f['filing_date']} (cite as (filing, {f['filing_date']}))",
             take["headline"]]
    figures = take["figures"] or {}
    for r in figures.get("rows", []):
        parts = [f"{r['label']}: {filings.money(r['value'], r['unit'])}"]
        if r["change_prior_pct"] is not None:
            parts.append(f"{r['change_prior_pct']:+.1f}% vs the quarter before")
        if r["change_year_pct"] is not None:
            parts.append(f"{r['change_year_pct']:+.1f}% vs a year earlier")
        if r["check"] == "confirmed":
            parts.append("confirmed by the quarterly report")
        elif r["check"] == "differs":
            parts.append(f"but the quarterly report says {filings.money(r['report_value'], r['unit'])}")
        lines.append("- " + ", ".join(parts))
    lines += [f"- {m['label']}: {m['value']}%" for m in figures.get("margins", [])]
    lines += [f"- {p['text']}" for p in take["points"]]
    lines += [f"- Guidance ({filings.DIRECTIONS[g['direction']].lower()}): {g['text']}" for g in take["guidance"]]
    lines += [f"- Changed since the last announcement: {c['text']}" for c in take["changes"]]
    return lines


def filings_section(conn, tickers: list[str]) -> str:
    """What companies filed with the SEC: each named ticker's latest filings and first takes, or,
    with no ticker named, everything filed in the last week."""
    def has_take(f):
        return f["read"] is not None and f["read"]["status"] == "ok"

    if not tickers:
        found = filings.list_filings(conn, since=filings._days_ago(FILINGS_DAYS), limit=40)
        if not found:
            return ""
        lines = [f"## Company filings in the last {FILINGS_DAYS} days (cite as (filing, date filed))", ""]
        lines += [f"- {f['filing_date']} {f['ticker']}: {f['title']}" + (f". {f['read']['headline']}" if has_take(f) else "")
                  for f in found]
        return "\n".join(lines)
    parts = []
    for ticker in tickers:
        found = filings.list_filings(conn, ticker, limit=60)
        if not found:
            continue
        lines = [f"## Company filings for {ticker} (cite as (filing, date filed))", ""]
        lines += [f"- {f['filing_date']}: {f['title']}" + ("" if has_take(f) else " (not read)") for f in found[:FILINGS_LISTED]]
        for f in [f for f in found if has_take(f)][:FILING_TAKES]:
            lines += ["", *_take_lines(f)]
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
    filed = filings_section(conn, tickers)
    if filed:
        add(filed)

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
    GET  /api/filings?ticker=    company filings from the SEC, with first takes, and results expected but not filed
    POST /api/filings/check      look for new filings now (free; new results announcements are read)
    POST /api/filings/read       read one filing with Claude now: {"accession": "0000789019-26-000123"}
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
Filings and first takes are written by filings.py (before each run, or "Check now" and "Read this filing").
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
import edgar
import events as upcoming  # events.py ("events" here is the live-updates endpoint)
import filings
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
ACCESSION = re.compile(r"\d{10}-\d{2}-\d{6}")                              # the SEC's number for a filing
TICKER = re.compile(r"[A-Za-z0-9.\-^=]{1,15}")
FRONTEND_ORIGINS = [o.strip() for o in os.environ.get(
    "FRONTEND_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",") if o.strip()]
RUN_COOLDOWN_SECONDS = int(os.environ.get("RUN_COOLDOWN_SECONDS", "300"))  # between on-demand runs
CALENDAR_SCAN_COOLDOWN_SECONDS = int(os.environ.get("CALENDAR_SCAN_COOLDOWN_SECONDS", "300"))
MAX_CALENDAR_DAYS = 100                                                   # longest date range one request returns
FOLLOWUP_REFRESH_COOLDOWN_SECONDS = int(os.environ.get("FOLLOWUP_REFRESH_COOLDOWN_SECONDS", "60"))
STORY_CHECK_COOLDOWN_SECONDS = int(os.environ.get("STORY_CHECK_COOLDOWN_SECONDS", "30"))  # each check can cost a few cents
STORY_DAYS = 30                                                           # recent moves offered for a news check
FILINGS_CHECK_COOLDOWN_SECONDS = int(os.environ.get("FILINGS_CHECK_COOLDOWN_SECONDS", "60"))
FILING_READ_COOLDOWN_SECONDS = int(os.environ.get("FILING_READ_COOLDOWN_SECONDS", "30"))  # each read costs a few cents
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
        reported = filings.for_calendar(conn, found, first.isoformat(), last.isoformat())  # results actually filed
    return JSONResponse({"today": today.isoformat(), "start": first.isoformat(), "end": last.isoformat(),
                         "events": found, "reported": reported, "last_scan": scanned, "scan": calendar_scans.snapshot()})


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


def _latest_filings() -> tuple:
    """Changes whenever any program lists a new filing, finishes a read, or confirms figures."""
    with _db() as conn:
        try:
            return (conn.execute("SELECT MAX(id) FROM filing_checks").fetchone()[0],
                    conn.execute("SELECT MAX(id) FROM filing_reads WHERE finished_at IS NOT NULL").fetchone()[0],
                    conn.execute("SELECT COUNT(*) FROM filings").fetchone()[0])
        except Exception:  # not set up yet
            return (None, None, None)


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
        return _latest_change(), _latest_calendar_scan(), watchlist_stamp(), _latest_followups(), _latest_filings()

    last, last_scan, last_stamp, last_followed, last_filed = await asyncio.to_thread(check)
    while True:
        await asyncio.sleep(POLL_SECONDS)
        try:
            current, scan, stamp, followed, filed = await asyncio.to_thread(check)
        except Exception:  # e.g. the database is briefly locked; try again next time
            continue
        if filed != last_filed:  # a new filing, a first take, or figures confirmed (by any program)
            last_filed = filed
            hub.publish({"type": "filings_updated"})
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


# ---------------------------------------------------------------------------
# Company filings (the Filings tab)
# ---------------------------------------------------------------------------

filing_checks = BackgroundJob("filings_check", lambda: FILINGS_CHECK_COOLDOWN_SECONDS,
                              "Filings are already being checked.", "Filings were just checked. Try again in {}.")
filing_reads = BackgroundJob("filing_read", lambda: FILING_READ_COOLDOWN_SECONDS,
                             "A filing is already being read. Its progress is shown on the Filings tab.",
                             "A filing was just read. Try again in {}.")


def _filings_view(ticker: str | None) -> dict:
    with _db() as conn:
        every = filings.list_filings(conn)
        return {"filings": [f for f in every if not ticker or f["ticker"] == ticker.upper()],
                "tickers": sorted({f["ticker"] for f in every}),
                "expected": filings.expected(conn, upcoming.today_et()), "not_covered": filings.not_covered(conn),
                "checked": filings.last_check(conn), "check": filing_checks.snapshot(), "read": filing_reads.snapshot(),
                "max_cost_usd": filings.READ_BUDGET_USD, "automatic_days": filings.AUTOMATIC_WITHIN_DAYS,
                "contact_set": edgar.contact_set()}


async def filings_view(request):
    ticker = request.query_params.get("ticker") or None
    if ticker and not TICKER.fullmatch(ticker):
        return _error(400, "invalid ticker")
    return JSONResponse(await asyncio.to_thread(_filings_view, ticker))


async def check_filings(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        job = filing_checks.start(lambda emit: filings.check("manual", emit))
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"check": job}, status_code=202)


async def read_filing(request):
    if blocked := _post_guard(request):
        return blocked
    try:
        body = await request.json()
    except ValueError:
        return _error(400, 'send JSON like {"accession": "0000789019-26-000123"}')
    accession = body.get("accession") if isinstance(body, dict) else None
    if not isinstance(accession, str) or not ACCESSION.fullmatch(accession):
        return _error(400, 'send JSON like {"accession": "0000789019-26-000123"}')
    with _db() as conn:  # a quick check first, so a wrong number is refused straight away
        known = filings.get_filing(conn, accession)
    if not known:
        return _error(404, f"No filing {accession} is listed. Check for new filings first.")
    try:
        job = filing_reads.start(lambda emit: filings.read(accession, "manual", emit),
                                 target={"accession": accession, "ticker": known["ticker"]})
    except AlreadyRunning as e:
        return _error(409, str(e))
    except TooSoon as e:
        return _error(429, str(e))
    return JSONResponse({"read": job}, status_code=202)


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
        Route("/api/filings", filings_view, methods=["GET"]),
        Route("/api/filings/check", check_filings, methods=["POST"]),
        Route("/api/filings/read", read_filing, methods=["POST"]),
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

### frontend/src/components/FilingsTab.jsx

```jsx
import { useEffect, useRef, useState } from 'react'
import { checkFilings, getFilings, readFiling } from '../api'
import { useOpenChart } from '../chartContext'
import { formatDateTime, formatShortDate, safeUrl } from '../format'
import { routes } from '../useRoute'

const KINDS = [
  ['all', 'All'],
  ['results', 'Results'],
  ['announcement', 'Announcements'],
  ['report', 'Reports'],
]
const inKind = (filing, kind) =>
  kind === 'all' ||
  (kind === 'report'
    ? ['quarterly', 'annual'].includes(filing.kind)
    : kind === 'announcement'
      ? ['announcement', 'late', 'foreign'].includes(filing.kind)
      : filing.kind === kind)

// $77.67B, $420.5M, $3.72: the same wording as the Discord messages
function money(value, unit) {
  if (value == null) return '—'
  const sign = value < 0 ? '-' : ''
  const size = Math.abs(value)
  if (unit !== 'USD') return `${sign}$${size.toFixed(2)}`
  if (size >= 1e9) return `${sign}$${(size / 1e9).toFixed(2)}B`
  if (size >= 1e6) return `${sign}$${(size / 1e6).toFixed(1)}M`
  return `${sign}$${Math.round(size).toLocaleString()}`
}

const change = (pct) => (pct == null ? '—' : `${pct > 0 ? '+' : ''}${pct.toFixed(1)}%`)
const direction = (pct) => (pct == null || pct === 0 ? '' : pct > 0 ? 'up' : 'down')

const CHECKS = {
  confirmed: ['ok', '✓ Confirmed', 'The quarterly report gives the same figure.'],
  pending: ['wait', 'Not checked yet', 'It will be compared with the quarterly report when that is filed.'],
  not_checked: ['wait', 'Can’t be checked', 'The report doesn’t give this figure for the quarter on its own.'],
}

function Earlier({ period, unit }) {
  if (!period) return <span className="muted">—</span>
  return (
    <span title={`Quarter to ${period.end}${period.derived ? ': worked out as the year minus the first nine months' : ''}`}>
      {period.derived && '≈ '}
      {money(period.value, unit)}
    </span>
  )
}

// Reported figures next to the periods before. Every comparison is worked out in code from the SEC's data.
function Figures({ figures, caption }) {
  if (!figures || figures.rows.length === 0) return null
  const year = figures.basis === 'year'
  const announced = figures.source === 'announcement'
  return (
    <div className="filing-figures">
      <div className="table-wrap">
        <table className="tickers figures">
          <caption>
            {caption} · {year ? 'year' : 'quarter'} to {figures.period_end ? formatShortDate(figures.period_end) : 'an unknown date'}
          </caption>
          <thead>
            <tr>
              <th scope="col">Figure</th>
              <th scope="col" className="num">{announced ? 'Reported' : 'In the report'}</th>
              {!year && <th scope="col" className="num">Quarter before</th>}
              {!year && <th scope="col" className="num">Change</th>}
              <th scope="col" className="num">A year earlier</th>
              <th scope="col" className="num">Change</th>
              {announced && <th scope="col">Checked against the report</th>}
            </tr>
          </thead>
          <tbody>
            {figures.rows.map((r) => {
              const [tone, label, tip] =
                r.check === 'differs'
                  ? ['bad', `✗ The report says ${money(r.report_value, r.unit)}`, 'The quarterly report gives a different figure.']
                  : CHECKS[r.check] || []
              return (
                <tr key={r.metric}>
                  <th scope="row" title={r.quote ? `From the filing: “${r.quote}”` : undefined}>{r.label}</th>
                  <td className="num">{money(r.value, r.unit)}</td>
                  {!year && <td className="num"><Earlier period={r.prior} unit={r.unit} /></td>}
                  {!year && <td className={`num ${direction(r.change_prior_pct)}`}>{change(r.change_prior_pct)}</td>}
                  <td className="num"><Earlier period={r.year_ago} unit={r.unit} /></td>
                  <td className={`num ${direction(r.change_year_pct)}`}>{change(r.change_year_pct)}</td>
                  {announced && <td className={`figure-check ${tone}`} title={tip}>{label}</td>}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
      {figures.margins.length > 0 && (
        <p className="muted small">
          {figures.margins
            .map((m) => `${m.label} ${m.value.toFixed(1)}%${m.year_ago != null ? ` (${m.year_ago.toFixed(1)}% a year earlier)` : ''}`)
            .join(' · ')}
        </p>
      )}
    </div>
  )
}

function Entries({ title, entries, badge }) {
  if (!entries || entries.length === 0) return null
  return (
    <div className="take-part">
      <h4>{title}</h4>
      <ul>
        {entries.map((e, i) => (
          <li key={i}>
            {badge && <span className={`guidance ${e.direction}`}>{badge(e)}</span>} {e.text}
            <details>
              <summary>From the filing</summary>
              <blockquote>{e.quote}</blockquote>
            </details>
          </li>
        ))}
      </ul>
    </div>
  )
}

const DIRECTIONS = { raised: 'Raised', lowered: 'Lowered', maintained: 'Kept', new: 'New', withdrawn: 'Withdrawn' }

function ReadButton({ filing, job, onStarted, label }) {
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const running = job?.state === 'running'
  const mine = job?.target?.accession === filing.accession
  const start = async () => {
    setStarting(true)
    setError(null)
    try {
      onStarted(await readFiling(filing.accession))
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }
  return (
    <div className="check-action">
      <button
        className={label === 'Read this filing' ? 'primary' : 'chip'}
        onClick={start}
        disabled={running || starting}
        aria-label={`${label}: ${filing.ticker}, ${filing.title}, filed ${filing.filing_date}`}
      >
        {running && mine ? 'Reading…' : label}
      </button>
      {running && mine && (
        <span className="muted small" aria-live="polite">
          {job.message}
        </span>
      )}
      {mine && job?.state === 'failed' && <span className="error">The read didn't finish: {job.error}</span>}
      {error && <span className="error">{error}</span>}
    </div>
  )
}

function Filing({ filing, picked, job, onReadStarted, cardRef }) {
  const openChart = useOpenChart()
  const take = filing.read
  const read = take?.status === 'ok'
  return (
    <article
      className={`filing ${picked ? 'picked' : ''} ${read ? 'read' : ''}`}
      ref={cardRef}
      aria-label={`${filing.ticker}: ${filing.title}, filed ${filing.filing_date}`}
    >
      <header>
        <div className="story-head">
          <button type="button" className="ticker-button" onClick={(e) => openChart(filing.ticker, e.currentTarget)} aria-label={`Show ${filing.ticker} chart`}>
            {filing.ticker}
          </button>
          <a className="filing-title" href={routes.filings(filing.accession)}>
            {filing.title}
          </a>
        </div>
        <div className="filing-tags">
          {filing.serious && <span className="verdict serious">Worth a look</span>}
          <span className="verdict">{filing.kind_label}</span>
        </div>
      </header>
      <p className="muted small">
        Filed {formatDateTime(filing.filed_at)} · form {filing.form}
        {filing.report_date && ['quarterly', 'annual'].includes(filing.kind) && ` · period to ${formatShortDate(filing.report_date)}`} ·{' '}
        <a href={safeUrl(filing.url)} target="_blank" rel="noopener noreferrer">
          the filing on sec.gov
        </a>
      </p>

      {filing.figures?.rows.length > 0 && (
        <details className="report-figures">
          <summary>Figures from the report ({filing.figures.rows.length}), from the SEC’s own data</summary>
          <Figures figures={filing.figures} caption="As filed" />
        </details>
      )}

      {read && (
        <>
          <p className="take-headline">{take.headline}</p>
          <Figures figures={take.figures} caption="Figures as announced" />
          <Entries title="Key points" entries={take.points} />
          <Entries title="Guidance" entries={take.guidance} badge={(g) => DIRECTIONS[g.direction] || 'New'} />
          <Entries title="What changed since the last announcement" entries={take.changes} />
          {take.notes.map((note, i) => (
            <p key={i} className="muted small take-note">
              Note: {note}
            </p>
          ))}
          <p className="muted small">
            First take by Claude, {formatDateTime(take.finished_at)} · {take.trigger === 'automatic' ? 'automatically' : 'on request'}
            {take.cost_usd > 0 && ` · $${take.cost_usd.toFixed(3)}`} · read from{' '}
            <a href={safeUrl(take.document_url)} target="_blank" rel="noopener noreferrer">
              {take.document}
            </a>
          </p>
        </>
      )}
      {take?.status === 'failed' && <p className="error">The last read failed: {take.error}</p>}
      {take?.status === 'running' ? (
        <p className="muted small">Being read…</p>
      ) : (
        <ReadButton filing={filing} job={job} onStarted={onReadStarted} label={read ? 'Read again' : 'Read this filing'} />
      )}
    </article>
  )
}

// What tracked companies have filed with the SEC, with Claude's first take on each one that's been read.
export default function FilingsTab({ version, checkJob, readJob, onCheckStarted, onReadStarted, picked }) {
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [starting, setStarting] = useState(false)
  const [ticker, setTicker] = useState('')
  const [kind, setKind] = useState('all')
  const [onlyRead, setOnlyRead] = useState(false)
  const pickedRef = useRef(null)

  useEffect(() => {
    let current = true
    getFilings()
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

  const loaded = Boolean(data)
  useEffect(() => {
    if (!picked || !loaded) return
    const timer = setTimeout(() => pickedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 0)
    return () => clearTimeout(timer)
  }, [picked, loaded])

  const check = async () => {
    setStarting(true)
    setError(null)
    try {
      onCheckStarted(await checkFilings())
    } catch (e) {
      setError(e.message)
    } finally {
      setStarting(false)
    }
  }

  const job = checkJob || data?.check
  const reading = readJob || data?.read
  const running = job?.state === 'running'
  const last = data?.checked
  const status = running
    ? job.message || 'Checking…'
    : last
      ? `Checked ${formatDateTime(last.finished_at)}`
      : loaded
        ? 'Not checked yet'
        : ''
  const all = data?.filings || []
  // A filing picked by its link is always shown, whatever the filters say
  const shown = all.filter(
    (f) =>
      f.accession === picked ||
      ((!ticker || f.ticker === ticker) && inKind(f, kind) && (!onlyRead || f.read?.status === 'ok')),
  )
  const maxCost = data ? `$${data.max_cost_usd.toFixed(2)}` : '$0.50'

  return (
    <>
      <section className="panel filings" aria-label="Company filings">
        <div className="section-head">
          <h2>Company filings</h2>
          <div className="cal-update">
            <span className="muted small" aria-live="polite">{status}</span>
            <button className="primary" onClick={check} disabled={running || starting}>
              {running ? 'Checking…' : 'Check now'}
            </button>
          </div>
        </div>
        <p className="muted small">
          What your tracked companies file with the SEC: results, other announcements, and quarterly and annual reports. Looking
          for filings is free. A new results announcement is read by Claude automatically; any other filing has a “Read this
          filing” button (a few cents, at most {maxCost}). Every point is checked against the filing’s own words, and every
          comparison is worked out in code from the SEC’s figures.
        </p>
        {error && <p className="error">{error}</p>}
        {job?.state === 'failed' && <p className="error">The check didn't finish: {job.error}</p>}
        {!running && last?.status === 'partial' && <p className="muted small">Checked, with problems: {last.message}</p>}
        {data && !data.contact_set && !last && (
          <p className="notice-box">
            To look for filings, set <code>SEC_CONTACT</code> to your name and email where the API runs, then restart it. The SEC
            asks automated tools to say who they are.
          </p>
        )}

        {data?.expected.length > 0 && (
          <ul className="expected" aria-label="Results expected">
            {data.expected.map((e) => (
              <li key={`${e.ticker}-${e.event_date}`}>
                <strong>{e.company}</strong> ({e.ticker}) was due to report on{' '}
                <a href={routes.calendar(e.event_date)}>{formatShortDate(e.event_date)}</a>
                {!e.confirmed && ' (date not confirmed)'}: nothing filed yet.
              </li>
            ))}
          </ul>
        )}

        <div className="moves-filters filings-filters">
          <label>
            Stock
            <select value={ticker} onChange={(e) => setTicker(e.target.value)}>
              <option value="">All</option>
              {(data?.tickers || []).map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </label>
          <div className="horizon-picker" role="group" aria-label="Kind of filing">
            {KINDS.map(([key, label]) => (
              <button key={key} type="button" className="chip" aria-pressed={kind === key} onClick={() => setKind(key)}>
                {label}
              </button>
            ))}
          </div>
          <label>
            <input type="checkbox" checked={onlyRead} onChange={(e) => setOnlyRead(e.target.checked)} /> Only with a first take
          </label>
        </div>

        {shown.length === 0 ? (
          <p className="muted">
            {!loaded ? 'Loading…' : all.length === 0 ? 'No filings listed yet. Press “Check now” to look for them.' : 'No filings match.'}
          </p>
        ) : (
          <div className="filing-list">
            {shown.slice(0, 80).map((f) => (
              <Filing
                key={`${f.ticker}-${f.accession}`}
                filing={f}
                picked={f.accession === picked}
                job={reading}
                onReadStarted={onReadStarted}
                cardRef={f.accession === picked ? pickedRef : undefined}
              />
            ))}
          </div>
        )}
        {shown.length > 80 && <p className="muted small">Showing the latest 80 of {shown.length}. Pick a stock to see its older filings.</p>}
        {data?.not_covered.length > 0 && (
          <p className="muted small">
            No company filings for {data.not_covered.join(', ')}: funds and some companies listed elsewhere don’t file these forms.
          </p>
        )}
      </section>
    </>
  )
}
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

// "Reported Oct 28: headline" under an earnings event, or on the day results were filed
function Reported({ filing, eventDate }) {
  return (
    <p className="cal-reported">
      <strong>Reported{filing.filing_date !== eventDate ? ` on ${formatShortDate(filing.filing_date)}` : ''}:</strong>{' '}
      {filing.headline || 'Results were filed with the SEC.'}{' '}
      <a href={routes.filings(filing.accession)}>{filing.headline ? 'First take' : 'See the filing'}</a>
    </p>
  )
}

function EventCard({ event, reported }) {
  return (
    <article className="cal-event">
      <div className="cal-event-head">
        <strong>{event.company}</strong>
        <span className="muted small">{event.ticker}</span>
        <span className={`kind kind-${event.kind}`}>{KINDS[event.kind]}</span>
      </div>
      <h3>{event.title}</h3>
      {event.date_note && <p className="muted small">{event.date_note}</p>}
      {reported && <Reported filing={reported} eventDate={event.event_date} />}
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
  const [dayReported, setDayReported] = useState([])
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
      .then((body) => {
        if (!current) return
        setDayEvents(body.events)
        setDayReported(body.reported || [])
      })
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
  // Results show on the day they were actually filed too, in case the calendar's date was out (or missing)
  for (const r of data?.reported || []) (byDay[r.filing_date] ||= []).push({ ticker: r.ticker, company: r.company })
  const reportedFor = new Map(dayReported.filter((r) => r.event_id != null).map((r) => [r.event_id, r]))
  const dayIds = new Set((dayEvents || []).map((e) => e.id))
  const filedToday = dayReported.filter((r) => r.filing_date === selectedDate && !dayIds.has(r.event_id))
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
          link to its source. The calendar updates every trading day when the market opens. Once a company files its
          results with the SEC, its day says “Reported”, with a link to the filing.
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
          ) : dayEvents.length === 0 && filedToday.length === 0 ? (
            <p className="muted">Nothing on the calendar for this day.</p>
          ) : (
            <>
              {dayEvents.map((e) => (
                <EventCard key={e.id} event={e} reported={reportedFor.get(e.id)} />
              ))}
              {filedToday.map((r) => (
                <article key={r.accession} className="cal-event">
                  <div className="cal-event-head">
                    <strong>{r.company}</strong>
                    <span className="muted small">{r.ticker}</span>
                    <span className="kind kind-earnings">Reported</span>
                  </div>
                  <h3>Results announced</h3>
                  <Reported filing={r} eventDate={selectedDate} />
                </article>
              ))}
            </>
          )}
        </section>
      )}
    </>
  )
}
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
  // Results that have since been filed: the event links to its filing instead
  const reported = new Map((data.reported || []).filter((r) => r.event_id != null).map((r) => [r.event_id, r]))

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
          {soon.slice(0, MAX_SHOWN).map((e) => {
            const filed = reported.get(e.id)
            return (
              <li key={e.id}>
                <a href={filed ? routes.filings(filed.accession) : routes.calendar(e.event_date)}>
                  <span className="cu-date">{e.event_date === data.today ? 'Today' : formatWeekdayDate(e.event_date)}</span>
                  <span className="cu-what">
                    <strong>{e.company}</strong>{' '}
                    <span className="muted">{filed ? (filed.headline ? 'Reported: first take ready' : 'Reported: results filed') : e.title}</span>
                  </span>
                </a>
              </li>
            )
          })}
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
  recent_filings: () => 'Checking company filings',
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
import FilingsTab from './components/FilingsTab'
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
  const [filingsVersion, setFilingsVersion] = useState(0) // tells the Filings tab to reload
  const [filingsCheck, setFilingsCheck] = useState(null) // "Check now" on the Filings tab
  const [filingRead, setFilingRead] = useState(null) // "Read this filing"
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
    } else if (event.type === 'filings_check') {
      setFilingsCheck(event.job)
      if (event.job.state !== 'running') setFilingsVersion((v) => v + 1)
    } else if (event.type === 'filing_read') {
      setFilingRead(event.job)
      if (event.job.state !== 'running') setFilingsVersion((v) => v + 1)
    } else if (event.type === 'filings_updated') {
      setFilingsVersion((v) => v + 1) // a new filing or first take, from "Check now", a run, or another program
      setCalendarVersion((v) => v + 1) // the calendar shows what was reported
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
  const onFilingsCheckStarted = (started) =>
    setFilingsCheck((current) => (current && current.started_at === started.started_at ? current : started))
  const onFilingReadStarted = (started) =>
    setFilingRead((current) => (current && current.started_at === started.started_at ? current : started))

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
            {tabLink('filings', routes.filings(), 'Filings')}
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

        <div hidden={route.tab !== 'filings'}>
          <FilingsTab
            version={filingsVersion}
            checkJob={filingsCheck}
            readJob={filingRead}
            onCheckStarted={onFilingsCheckStarted}
            onReadStarted={onFilingReadStarted}
            picked={route.tab === 'filings' ? route.accession : null}
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
//   #/filings               Company filings from the SEC, with first takes
//   #/filings/0000789019-26-000123   ...with that filing picked
// So tabs and days can be bookmarked, and the browser's Back button works.

function parse(hash) {
  const [, tab, date, ticker] = hash.replace(/^#/, '').split('/')
  if (tab === 'stocks') return { tab: 'stocks', date: null }
  if (tab === 'follow-through') return { tab: 'followthrough', date: null }
  if (tab === 'filings') return { tab: 'filings', date: null, accession: /^\d{10}-\d{2}-\d{6}$/.test(date || '') ? date : null }
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
  filings: (accession) => (accession ? `#/filings/${accession}` : '#/filings'),
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

// Company filings from the SEC, and Claude's first take on them
export const getFilings = (ticker) => request(`/api/filings${ticker ? `?ticker=${encodeURIComponent(ticker)}` : ''}`)
export const checkFilings = () => post('/api/filings/check', {}).then((body) => body.check)
export const readFiling = (accession) => post('/api/filings/read', { accession }).then((body) => body.read)

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

/* Filings */
.filings a, .cal-reported a { color: var(--accent); }
.filing-list { display: grid; gap: 12px; margin-top: 12px; }
.filing { border: 1px solid var(--border); border-radius: var(--radius); padding: 12px 14px; background: var(--panel); min-width: 0; scroll-margin-top: 12px; }
.filing.picked { border: 2px solid var(--accent); }
.filing header { display: flex; flex-wrap: wrap; justify-content: space-between; gap: 6px 12px; align-items: baseline; }
.filing p { margin: 6px 0; }
.filing-title { font-weight: 600; color: var(--text) !important; text-decoration: none; overflow-wrap: anywhere; }
.filing-title:hover { text-decoration: underline; }
.filing-tags { display: flex; gap: 6px; flex-wrap: wrap; }
.verdict.serious { color: var(--live); border-color: var(--live); }
.take-headline { font-size: 1.02rem; font-weight: 600; }
.filing-figures { margin: 10px 0; }
.figures caption { caption-side: top; text-align: left; font-size: 0.8rem; color: var(--muted); padding: 0 8px 4px; }
.figures tbody th { color: var(--text); font-size: 0.9rem; font-weight: 400; }
.figure-check { font-size: 0.85rem; }
.figure-check.ok { color: var(--final); font-weight: 600; }
.figure-check.bad { color: var(--down); font-weight: 600; }
.figure-check.wait { color: var(--muted); }
.take-part h4 { margin: 12px 0 4px; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--muted); }
.take-part ul { margin: 0; padding-left: 18px; display: grid; gap: 6px; }
.take-part details { font-size: 0.85rem; color: var(--muted); }
.take-part summary { cursor: pointer; width: fit-content; }
.take-part blockquote { margin: 4px 0 0; padding: 4px 10px; border-left: 3px solid var(--border); overflow-wrap: anywhere; }
.guidance { font-size: 0.75rem; font-weight: 600; padding: 1px 7px; border-radius: 999px; border: 1px solid var(--border); white-space: nowrap; }
.guidance.raised { color: var(--up); border-color: var(--up); }
.guidance.lowered, .guidance.withdrawn { color: var(--down); border-color: var(--down); }
.take-note { font-style: italic; }
.expected { list-style: none; margin: 12px 0; padding: 10px 12px; background: var(--live-bg); color: var(--text); border-radius: 8px; display: grid; gap: 4px; font-size: 0.9rem; }
.notice-box { padding: 10px 12px; border: 1px solid var(--border); border-radius: 8px; background: var(--bg); font-size: 0.9rem; }
.filings-filters { margin-top: 12px; }
.filings-filters .horizon-picker { margin: 0; }
.cal-reported { padding: 8px 10px; background: var(--final-bg); border-radius: 8px; }
.filings-filters label { font-size: 0.9rem; }
.report-figures { margin: 8px 0; font-size: 0.9rem; }
.report-figures summary { cursor: pointer; width: fit-content; color: var(--accent); }
```

### tests/conftest.py

```python
"""Shared test setup: tests never reach real services, whatever is set in your terminal.

Without this, running pytest in a terminal where DISCORD_WEBHOOK_URL is set would post
test alerts to your real Discord channel (and VOYAGE_API_KEY would send test text to Voyage,
and SEC_CONTACT would let tests ask the SEC for filings). Tests that need these set them themselves.

A run that saves a final report also follows up on earlier flagged moves, which downloads
prices from Yahoo and can ask Claude about surprises. Tests skip that step, except the ones
in test_followups.py, which fake Yahoo and Claude themselves.

Every run also starts by looking for new company filings, which asks the SEC and can ask Claude
to read a results announcement. Tests skip that step too, except the ones in test_filings.py,
which fake the SEC and Claude themselves.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    for name in ("DISCORD_WEBHOOK_URL", "VOYAGE_API_KEY", "SEC_CONTACT"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_follow_up_after_runs(request, monkeypatch):
    if request.module.__name__.endswith("test_followups"):
        return
    import stories
    monkeypatch.setattr(stories, "after_final_report", lambda emit=None: {"followups": None, "checks": [], "problems": []})


@pytest.fixture(autouse=True)
def no_filing_checks_before_runs(request, monkeypatch):
    if request.module.__name__.endswith("test_filings"):
        return
    import filings
    monkeypatch.setattr(filings, "check_before_run", lambda emit=None: None)
```

### tests/test_filings.py

```python
"""Offline tests for company filings: reading the SEC (edgar.py) and first takes (filings.py).
The SEC, Claude and Discord are faked, so these are free and need no internet.

Run from the project folder:
    pytest -v tests/test_filings.py

Live check of the SEC's real data (free, needs internet and your SEC_CONTACT):
    LIVE_TESTS=1 pytest -v -s -k live_filings
"""

import asyncio
import io
import json
import os
import sys
import time
import urllib.error
import zlib
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import ask  # noqa: E402
import edgar  # noqa: E402
import events  # noqa: E402
import filings  # noqa: E402
import market_tools  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import ResultMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

LIVE_CONTACT = os.environ.get("SEC_CONTACT")  # kept for the live test: conftest.py removes it for every test
ET = market_tools.ET
CLOCK = {"now": datetime(2026, 10, 29, 9, 0, tzinfo=ET)}  # a Thursday morning in New York
SEC = {}      # address -> what the fake SEC answers: JSON (a dict), text, or an error to raise
FILED = {}    # company number -> its filings, as the SEC lists them
ASKED = []    # every address the code asked for
CLAUDE = []   # every (system prompt, prompt) the fake Claude was sent
SENT = []     # Discord messages "sent"
REPLY = {}    # what the fake Claude answers: {"value": a dict, text or an error}

NWND = 1111   # Northwind, the company most tests use
RESULTS, PREVIOUS = "0000001111-26-000090", "0000001111-26-000050"
REPORT = "0000001111-26-000095"


# ---------------------------------------------------------------------------
# A fake SEC
# ---------------------------------------------------------------------------

def fake_sec(url, max_bytes=None):
    ASKED.append(url)
    if url not in SEC:
        raise edgar.EdgarError("the SEC doesn't have that page", 404)
    if isinstance(SEC[url], Exception):
        raise SEC[url]
    return SEC[url] if max_bytes is None or not isinstance(SEC[url], str) else SEC[url][:max_bytes]


def companies(*listed):
    """The SEC's list of companies: (ticker, number, name)."""
    SEC[f"{edgar.WWW}/files/company_tickers.json"] = {
        str(i): {"cik_str": cik, "ticker": ticker, "title": name} for i, (ticker, cik, name) in enumerate(listed)}


def filing(cik, accession, form, filed, items="", report_date="", docs=(), index=True):
    """Add a filing to a company's list, with its index page and documents.
    filed is New York time ('2026-10-28 16:05'). docs are (file name, type, html)."""
    when = datetime.strptime(filed, "%Y-%m-%d %H:%M").replace(tzinfo=ET)
    FILED.setdefault(cik, []).append({
        "accessionNumber": accession, "filingDate": filed[:10], "reportDate": report_date,
        "acceptanceDateTime": when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z"), "form": form,
        "items": items, "primaryDocument": docs[0][0] if docs else "", "primaryDocDescription": form})
    rows = sorted(FILED[cik], key=lambda r: r["acceptanceDateTime"], reverse=True)
    SEC[f"{edgar.DATA}/submissions/CIK{cik:010d}.json"] = {
        "cik": str(cik), "name": "A COMPANY INC", "filings": {"recent": {k: [r[k] for r in rows] for k in rows[0]}, "files": []}}
    base = edgar.folder(cik, accession)
    path = base.replace(edgar.WWW, "")
    table = "".join(
        f'<tr><td scope="row">{n}</td><td scope="row">{kind}</td><td scope="row">'
        + (f'<a href="/ix?doc={path}{name}">{name}</a> <span>iXBRL</span>' if n == 1 else f'<a href="{path}{name}">{name}</a>')
        + f'</td><td scope="row">{kind}</td><td scope="row">{len(html)}</td></tr>'
        for n, (name, kind, html) in enumerate(docs, 1))
    if index:
        SEC[edgar.index_url(cik, accession)] = (
            '<html><body><div class="formGrouping"><div class="infoHead">Filing Date</div></div>'
            '<table class="tableFile" summary="Document Format Files"><tr><th scope="col">Seq</th>'
            '<th scope="col">Description</th><th scope="col">Document</th><th scope="col">Type</th><th scope="col">Size</th></tr>'
            f'{table}<tr><td scope="row">&nbsp;</td><td scope="row">Complete submission text file</td><td scope="row">'
            f'<a href="{path}{accession}.txt">{accession}.txt</a></td><td scope="row">&nbsp;</td><td scope="row">99</td></tr></table>'
            '<table class="tableFile" summary="Data Files"><tr><th>Seq</th><th>Description</th><th>Document</th><th>Type</th>'
            f'<th>Size</th></tr><tr><td>9</td><td>XBRL</td><td><a href="{path}data.xml">data.xml</a></td><td>XML</td><td>5</td></tr>'
            '</table></body></html>')
    SEC[base + "index.json"] = {"directory": {"name": path, "parent-dir": path, "item": [
        {"last-modified": "2026-10-28 16:05:00", "name": name, "type": "text.gif", "size": str(len(html))} for name, _, html in docs]}}
    for name, _, html in docs:
        SEC[base + name] = html


def press_release(quarter="third", ended="September 30, 2026", revenue=12_400, gross=8_100, operating=4_000, net=3_200,
                  eps="2.67", year_ago=(10_000, 6_500, 3_000, 2_400, "2.00"), extra=""):
    return f"""<html><head><title>EX-99.1</title><style>p {{}}</style></head><body>
<ix:header><ix:hidden>0001111 false 2026-09-30</ix:hidden></ix:header>
<p>Northwind Reports {quarter.title()} Quarter Results</p>
<p>REDMOND, Wash. &#8212; Northwind Corp. today announced results for the quarter ended {ended}.</p>
<p>Revenue was ${revenue / 1000:.1f} billion and increased from a year earlier.</p>
<p>Cloud revenue grew 30% on demand for AI services.</p>
<p>&#8220;Customers are choosing Northwind for their most important workloads,&#8221; said the chief executive.</p>
<p>Business outlook: The company expects fourth-quarter revenue of $12.8 billion to $13.2 billion.</p>
{extra}
<table><tr><td>(In millions, except per share amounts)</td><td></td><td>Three Months Ended</td></tr>
<tr><td>Total revenue</td><td>$</td><td>{revenue:,}</td><td></td><td>$</td><td>{year_ago[0]:,}</td></tr>
<tr><td>Gross margin</td><td></td><td>{gross:,}</td><td></td><td></td><td>{year_ago[1]:,}</td></tr>
<tr><td>Operating income</td><td></td><td>{operating:,}</td><td></td><td></td><td>{year_ago[2]:,}</td></tr>
<tr><td>Other expense, net</td><td>(</td><td>120</td><td>)</td><td>(</td><td>90</td><td>)</td></tr>
<tr><td>Net income</td><td>$</td><td>{net:,}</td><td></td><td>$</td><td>{year_ago[3]:,}</td></tr>
<tr><td>Diluted earnings per share</td><td>$</td><td>{eps}</td><td></td><td>$</td><td>{year_ago[4]}</td></tr></table>
</body></html>"""


COVER = """<html><body><p>UNITED STATES SECURITIES AND EXCHANGE COMMISSION</p><p>FORM 8-K</p>
<p>Item 2.02 Results of Operations and Financial Condition.</p>
<p>On October 28, 2026, Northwind Corp. issued a press release announcing its results. A copy is attached as Exhibit 99.1.</p>
</body></html>"""


def fact(start, end, value, form="10-Q", filed=None):
    return {"start": start, "end": end, "val": value, "accn": "0000001111-26-000001", "fy": int(end[:4]), "fp": "Q",
            "form": form, "filed": filed or (date.fromisoformat(end) + timedelta(days=28)).isoformat()}


M = 1_000_000
# (revenue, gross profit, operating income, net income, earnings per share) for each quarter, in $ millions
HISTORY = {("2025-07-01", "2025-09-30"): (10_000, 6_500, 3_000, 2_400, 2.00),
           ("2026-04-01", "2026-06-30"): (11_800, 7_700, 3_700, 2_950, 2.46)}
THIRD_QUARTER = {("2026-07-01", "2026-09-30"): (12_400, 8_100, 4_000, 3_200, 2.67)}


def set_facts(cik, quarters, revenue_tag="Revenues", leave_out=()):
    """The company's structured figures, as the SEC publishes them."""
    tags = {revenue_tag: 0, "GrossProfit": 1, "OperatingIncomeLoss": 2, "NetIncomeLoss": 3}
    reported = {tag: {"label": tag, "units": {"USD": [fact(s, e, values[i] * M) for (s, e), values in quarters.items()]}}
                for tag, i in tags.items() if tag not in leave_out}
    if "EarningsPerShareDiluted" not in leave_out:
        reported["EarningsPerShareDiluted"] = {"units": {"USD/shares": [fact(s, e, v[4]) for (s, e), v in quarters.items()]}}
    SEC[f"{edgar.DATA}/api/xbrl/companyfacts/CIK{cik:010d}.json"] = {"cik": cik, "entityName": "x", "facts": {
        "dei": {"EntityCommonStockSharesOutstanding": {"units": {"shares": [{"end": "2026-10-20", "val": 1}]}}},
        "us-gaap": reported}}


def results_reply(**changes):
    """What a careful Claude would say about press_release()."""
    reply = {
        "headline": "Northwind reported third-quarter revenue of $12.4 billion, up from a year earlier.",
        "period_end": "2026-09-30",
        "figures": [
            {"metric": "revenue", "as_written": "12,400", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"},
            {"metric": "gross_profit", "as_written": "8,100", "scale": "millions", "quote": "Gross margin | 8,100 | 6,500"},
            {"metric": "operating_income", "as_written": "4,000", "scale": "millions", "quote": "Operating income | 4,000 | 3,000"},
            {"metric": "net_income", "as_written": "3,200", "scale": "millions", "quote": "Net income | $3,200 | $2,400"},
            {"metric": "eps_diluted", "as_written": "2.67", "scale": "units", "quote": "Diluted earnings per share | $2.67 | $2.00"}],
        "points": [
            {"text": "Cloud revenue grew 30%, driven by AI services.", "quote": "Cloud revenue grew 30% on demand for AI services."},
            {"text": "Management says customers are moving key workloads to it.",
             "quote": "“Customers are choosing Northwind for their most important workloads,” said the chief executive."}],
        "guidance": [{"text": "It expects fourth-quarter revenue of $12.8 billion to $13.2 billion.", "direction": "raised",
                      "quote": "The company expects fourth-quarter revenue of $12.8 billion to $13.2 billion."}],
        "changes": []}
    reply.update(changes)
    return reply


def fake_claude(system_prompt, prompt):
    CLAUDE.append((system_prompt, prompt))
    reply = REPLY["value"]
    if isinstance(reply, Exception):
        raise reply
    return (reply if isinstance(reply, str) else json.dumps(reply)), 0.08


def northwind():
    """Northwind's last two results announcements, and its figures up to the quarter before."""
    companies(("NWND", NWND, "NORTHWIND CORP"))
    filing(NWND, PREVIOUS, "8-K", "2026-07-29 16:05", "2.02,9.01", "2026-07-29", docs=[
        ("nwnd-8k.htm", "8-K", COVER),
        ("nwnd-ex991.htm", "EX-99.1", press_release("second", "June 30, 2026", 11_800, 7_700, 3_700, 2_950, "2.46",
                                                    extra="<p>Supply constraints limited growth in the quarter.</p>"))])
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", "2026-10-28", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    set_facts(NWND, HISTORY)


@pytest.fixture
def sec(tmp_path, monkeypatch):
    """A temporary watchlist and database, a fixed clock, and a fake SEC, Claude and Discord.
    Returns the watchlist file."""
    for store in (SEC, FILED, ASKED, CLAUDE, SENT):
        store.clear()
    CLOCK["now"] = datetime(2026, 10, 29, 9, 0, tzinfo=ET)
    REPLY["value"] = results_reply()
    path = tmp_path / "watchlist.txt"
    path.write_text("NWND\n")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", path)
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setattr(market_tools, "now_et", lambda: CLOCK["now"])
    monkeypatch.setattr(edgar, "get_json", fake_sec)
    monkeypatch.setattr(edgar, "get_text", fake_sec)
    monkeypatch.setattr(filings, "ask_claude", fake_claude)
    monkeypatch.setattr(events, "_names", {"NWND": "Northwind"})
    monkeypatch.setattr(alerts, "send", SENT.append)
    reports_db.connect().close()
    northwind()
    return path


def listed(ticker=None):
    with closing(reports_db.connect(readonly=True)) as conn:
        return filings.list_filings(conn, ticker)


def the(accession):
    with closing(reports_db.connect(readonly=True)) as conn:
        return filings.get_filing(conn, accession)


def figures_of(accession=RESULTS):
    return {r["metric"]: r for r in the(accession)["read"]["figures"]["rows"]}


# ---------------------------------------------------------------------------
# edgar.py: documents as text
# ---------------------------------------------------------------------------

def test_a_filing_becomes_plain_text_with_one_line_per_table_row():
    text = edgar.to_text(press_release())
    assert "Northwind Reports Third Quarter Results" in text.splitlines()[0]
    assert "Total revenue | $12,400 | $10,000" in text      # the $ joins its number, empty cells go
    assert "Other expense, net | (120) | (90)" in text      # ( and ) in cells of their own
    assert 'REDMOND, Wash. - Northwind' in text and '"Customers are choosing' in text  # dashes and quotes made plain
    assert "0001111 false" not in text and "p {}" not in text and "EX-99.1" not in text  # hidden parts left out


def test_text_copes_with_nested_tables_hidden_parts_and_cut_off_html():
    html = ('<div style="display: none">secret <div>nested</div> still secret</div><p>Shown</p>'
            '<table><tr><td><table><tr><td>inner</td><td>cell</td></tr></table></td><td>outer</td></tr>'
            '<tr><td>Revenue</td><td>1,234')  # the download stopped here
    assert edgar.to_text(html).splitlines() == ["Shown", "inner | cell | outer", "Revenue | 1,234"]
    assert edgar.to_text("Plain text, no tags — as some old filings are.") == "Plain text, no tags - as some old filings are."


def test_managements_discussion_is_found_past_the_contents_page():
    body = "We sell software. " * 200
    report = "\n".join(["Table of contents", "Item 1. Financial Statements 3",
                        "Item 2. Management's Discussion and Analysis of Financial Condition 20",
                        "Item 3. Quantitative and Qualitative Disclosures 40", "Item 1. Financial Statements", "numbers " * 50,
                        "Item 2. | Management’s Discussion and Analysis of Financial Condition and Results of Operations",
                        body, "Item 3. Quantitative and Qualitative Disclosures About Market Risk", "risk " * 50])
    found = edgar.discussion(edgar.tidy(report), annual=False)
    assert found.startswith("Item 2. | Management's Discussion") and found.rstrip().endswith("We sell software.")
    assert "risk risk" not in found and "Table of contents" not in found
    annual = report.replace("Item 2.", "Item 7.").replace("Item 3.", "Item 7A.")
    assert edgar.discussion(edgar.tidy(annual), annual=True).startswith("Item 7.")
    assert edgar.discussion("A report with no such heading. " * 200, annual=False) == ""


# ---------------------------------------------------------------------------
# edgar.py: filings and documents
# ---------------------------------------------------------------------------

def test_a_companys_filings_are_read_from_the_secs_lists(sec):
    filing(NWND, "0000001111-26-000091", "4", "2026-10-28 18:00")
    FILED[NWND].append({"accessionNumber": "not-a-number", "filingDate": "2026-10-28", "form": "8-K"})  # a row to skip
    rows = FILED[NWND]
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"]["filings"]["recent"] = {
        "accessionNumber": [r["accessionNumber"] for r in rows], "filingDate": [r["filingDate"] for r in rows],
        "form": [r["form"] for r in rows], "items": [r.get("items", "") for r in rows][:3],  # a list that's too short
        "acceptanceDateTime": [r.get("acceptanceDateTime", "") for r in rows]}

    found = edgar.list_filings(NWND)["filings"]

    assert [f["accession"] for f in found] == ["0000001111-26-000091", RESULTS, PREVIOUS]  # newest first
    assert found[1]["items"] == ["2.02", "9.01"] and found[1]["filed_at"] == "2026-10-28T20:05:00Z"  # 4:05pm New York
    assert found[1]["filing_date"] == "2026-10-28" and found[0]["form"] == "4" and found[0]["primary_doc"] == ""


def test_a_filings_documents_come_from_its_index_page(sec):
    documents = edgar.filing_documents(NWND, RESULTS)
    assert [(d["name"], d["type"]) for d in documents] == [("nwnd-8k.htm", "8-K"), ("nwnd-ex991.htm", "EX-99.1")]
    assert documents[0]["url"] == f"{edgar.WWW}/Archives/edgar/data/1111/000000111126000090/nwnd-8k.htm"  # not the /ix?doc= viewer
    assert documents[1]["size"] == len(press_release())  # the .txt bundle and data files are left out


def test_without_an_index_page_documents_are_guessed_from_their_names(sec):
    filing(NWND, "0000001111-26-000092", "8-K", "2026-10-28 17:00", "5.02,9.01", index=False, docs=[
        ("d123d8k.htm", "8-K", COVER), ("d123dex991.htm", "EX-99.1", "<p>x</p>"), ("pic.jpg", "GRAPHIC", "")])
    documents = edgar.filing_documents(NWND, "0000001111-26-000092", "d123d8k.htm", "8-K")
    assert [(d["name"], d["type"]) for d in documents] == [("d123d8k.htm", "8-K"), ("d123dex991.htm", "EX-99.1")]


def test_requests_say_who_they_are_and_keep_their_distance(monkeypatch):
    sent, waits = [], []

    class Response:
        headers = {"Content-Encoding": "gzip"}

        def __init__(self):
            packer = zlib.compressobj(wbits=31)  # gzip, as the SEC sends it
            self.read = io.BytesIO(packer.compress(b'{"ok": true}' + b" " * 200_000) + packer.flush()).read

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr(edgar.urllib.request, "urlopen", lambda request, timeout: sent.append(request) or Response())
    monkeypatch.setattr(edgar.time, "sleep", waits.append)
    monkeypatch.setattr(edgar, "_last_request", time.monotonic())

    with pytest.raises(edgar.ContactMissing, match="Set SEC_CONTACT"):
        edgar.fetch(f"{edgar.DATA}/submissions/CIK0000001111.json")       # nothing is sent without a contact
    monkeypatch.setenv("SEC_CONTACT", "Jane Doe jane@example.com")
    with pytest.raises(edgar.ContactMissing):
        edgar.fetch(f"{edgar.DATA}/x")                                     # the guide's placeholder doesn't count
    assert sent == []
    monkeypatch.setenv("SEC_CONTACT", "  Test Runner   test@tests.invalid ")

    assert edgar.get_json(f"{edgar.DATA}/submissions/CIK0000001111.json") == {"ok": True}  # unpacked
    assert sent[0].get_header("User-agent") == "Test Runner test@tests.invalid"
    assert waits and 0 < waits[0] <= edgar.MIN_GAP_SECONDS                  # it waited before asking again
    assert edgar.fetch(f"{edgar.WWW}/big", max_bytes=5) == b'{"ok"'         # never more than asked for
    with pytest.raises(edgar.EdgarError, match="only sec.gov"):
        edgar.fetch("https://example.org/Archives/x")


@pytest.mark.parametrize("code, message, status", [
    (403, "wait 10 minutes", 403), (429, "wait 10 minutes", 429), (404, "doesn't have that page", 404), (500, "an error \\(500\\)", 500)])
def test_the_secs_refusals_are_explained(monkeypatch, code, message, status):
    def refuse(request, timeout):
        raise urllib.error.HTTPError(request.full_url, code, "no", {}, io.BytesIO(b""))

    monkeypatch.setenv("SEC_CONTACT", "Test Runner test@tests.invalid")
    monkeypatch.setattr(edgar.urllib.request, "urlopen", refuse)
    monkeypatch.setattr(edgar.time, "sleep", lambda s: None)
    with pytest.raises(edgar.EdgarError, match=message) as refused:
        edgar.fetch(f"{edgar.DATA}/submissions/CIK0000001111.json")
    assert refused.value.status == status


# ---------------------------------------------------------------------------
# edgar.py: figures
# ---------------------------------------------------------------------------

# Microsoft's real revenue and earnings-per-share facts, as the SEC published them (November 2026)
MSFT_REVENUE = [
    ("2024-07-01", "2025-03-31", 205283, "10-Q", "2025-04-30"), ("2025-01-01", "2025-03-31", 70066, "10-Q", "2025-04-30"),
    ("2025-01-01", "2025-03-31", 70066, "10-Q", "2026-04-29"), ("2024-07-01", "2025-06-30", 281724, "10-K", "2025-07-30"),
    ("2025-07-01", "2025-09-30", 77673, "10-Q", "2025-10-29"), ("2025-07-01", "2025-09-30", 77673, "10-Q", "2026-10-28"),
    ("2025-07-01", "2025-12-31", 158946, "10-Q", "2026-01-28"), ("2025-10-01", "2025-12-31", 81273, "10-Q", "2026-01-28"),
    ("2025-07-01", "2026-03-31", 241832, "10-Q", "2026-04-29"), ("2026-01-01", "2026-03-31", 82886, "10-Q", "2026-04-29"),
    ("2025-07-01", "2026-06-30", 331839, "10-K", "2026-07-29"), ("2026-07-01", "2026-09-30", 92279, "10-Q", "2026-10-28")]
MSFT_EPS = [("2025-07-01", "2025-09-30", 3.72, "10-Q", "2025-10-29"), ("2025-07-01", "2025-12-31", 8.87, "10-Q", "2026-01-28"),
            ("2025-10-01", "2025-12-31", 5.16, "10-Q", "2026-01-28"), ("2025-07-01", "2026-03-31", 13.14, "10-Q", "2026-04-29"),
            ("2026-01-01", "2026-03-31", 4.27, "10-Q", "2026-04-29"), ("2025-07-01", "2026-06-30", 17.95, "10-K", "2026-07-29")]


def company_facts(**tags):
    return {"facts": {"us-gaap": {tag: {"units": {("USD/shares" if "PerShare" in tag else "USD"): [
        fact(s, e, v * (1 if "PerShare" in tag else M), form, filed) for s, e, v, form, filed in rows]}}
        for tag, rows in tags.items()}}}


def test_quarters_come_from_structured_data_and_the_fourth_is_worked_out():
    known = edgar.periods(company_facts(RevenueFromContractWithCustomerExcludingAssessedTax=MSFT_REVENUE,
                                        EarningsPerShareDiluted=MSFT_EPS))
    revenue, eps = known["revenue"], known["eps_diluted"]

    assert revenue["tag"] == "RevenueFromContractWithCustomerExcludingAssessedTax"
    assert {str(end): q["value"] / M for end, q in revenue["quarters"].items() if not q["derived"]} == {
        "2025-03-31": 70066, "2025-09-30": 77673, "2025-12-31": 81273, "2026-03-31": 82886, "2026-09-30": 92279}
    # The annual report gives only the year: April to June is the year minus the first nine months
    fourth = revenue["quarters"][date(2026, 6, 30)]
    assert fourth["derived"] and fourth["value"] / M == 331839 - 241832 and fourth["start"] == date(2026, 4, 1)
    assert revenue["quarters"][date(2025, 6, 30)]["value"] / M == 281724 - 205283
    assert {str(end): y["value"] / M for end, y in revenue["years"].items()} == {"2025-06-30": 281724, "2026-06-30": 331839}
    assert round(eps["quarters"][date(2026, 6, 30)]["value"], 2) == 4.81 and eps["quarters"][date(2026, 6, 30)]["derived"]
    assert set(known) == {"revenue", "eps_diluted"}  # nothing is invented for figures the company doesn't report


def test_a_fourth_quarter_can_also_be_the_year_minus_three_quarters():
    rows = [("2025-01-01", "2025-03-31", 100, "10-Q", "2025-04-30"), ("2025-04-01", "2025-06-30", 110, "10-Q", "2025-07-30"),
            ("2025-07-01", "2025-09-30", 120, "10-Q", "2025-10-30"), ("2025-01-01", "2025-12-31", 460, "10-K", "2026-02-10")]
    quarters = edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"]
    assert quarters[date(2025, 12, 31)]["value"] / M == 130 and quarters[date(2025, 12, 31)]["derived"]
    two = edgar.periods(company_facts(Revenues=[rows[0], rows[1], rows[3]]))["revenue"]["quarters"]
    assert date(2025, 12, 31) not in two  # with a quarter missing, nothing is guessed


def test_a_restated_figure_replaces_the_original():
    rows = [("2025-07-01", "2025-09-30", 100, "10-Q", "2025-10-30"), ("2025-07-01", "2025-09-30", 97, "10-Q", "2026-10-30")]
    assert edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"][date(2025, 9, 30)]["value"] / M == 97


def test_the_name_with_the_newest_figures_is_used_for_every_period():
    old = [("2019-01-01", "2019-03-31", 50, "10-Q", "2019-04-30")]
    new = [("2025-07-01", "2025-09-30", 100, "10-Q", "2025-10-30"), ("2026-07-01", "2026-09-30", 120, "10-Q", "2026-10-30")]
    known = edgar.periods(company_facts(SalesRevenueNet=old, RevenuesNetOfInterestExpense=new))
    assert known["revenue"]["tag"] == "RevenuesNetOfInterestExpense" and len(known["revenue"]["quarters"]) == 2


def test_quarters_that_end_a_few_days_apart_still_match():
    # A 52/53-week year: quarters end on the last Saturday of the month, not the same date each year
    rows = [("2025-06-29", "2025-09-27", 100, "10-Q", "2025-10-30"), ("2026-06-28", "2026-09-26", 120, "10-Q", "2026-10-30")]
    quarters = edgar.periods(company_facts(Revenues=rows))["revenue"]["quarters"]
    assert edgar.nearest(quarters, date(2026, 9, 26) - timedelta(days=365))["value"] / M == 100
    assert edgar.nearest(quarters, date(2026, 3, 28)) is None  # a different quarter is never used instead


@pytest.mark.parametrize("written, value", [
    ("94,930", 94930), ("$1.64", 1.64), ("(1,234)", -1234), ("-5.2", -5.2), ("$ 77,673", 77673), ("12.4", 12.4),
    ("1,23", None), ("about 5", None), ("", None), ("12,400 million", None)])
def test_numbers_are_read_as_written(written, value):
    assert edgar.parse_number(written) == value


# ---------------------------------------------------------------------------
# Naming filings
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("form, items, kind, title, serious", [
    ("8-K", ["2.02", "9.01"], "results", "Results announcement", False),
    ("8-K", ["2.02", "5.02", "9.01"], "results", "Results announcement; Directors or senior officers leaving or appointed", True),
    ("8-K", ["5.02", "9.01"], "announcement", "Directors or senior officers leaving or appointed", True),
    ("8-K", ["7.01", "9.01"], "announcement", "Information shared with investors", False),
    ("8-K", ["4.02"], "announcement", "Earlier financial statements can no longer be relied on", True),
    ("8-K", ["6.66"], "announcement", "Item 6.66", False),
    ("8-K", [], "announcement", "Announcement", False),
    ("8-K/A", ["2.02", "9.01"], "results", "Amended: Results announcement", False),
    ("10-Q", [], "quarterly", "Quarterly report", False),
    ("10-K/A", [], "annual", "Amended: Annual report", False),
    ("NT 10-Q", [], "late", "Says its quarterly report will be late", True),
    ("NT 10-K", [], "late", "Says its annual report will be late", True),
    ("6-K", [], "foreign", "Report from a company based outside the US", False),
    ("20-F", [], "annual", "Annual report", False),
])
def test_filings_are_named_in_plain_words(form, items, kind, title, serious):
    about = filings.describe(form, items)
    assert (about["kind"], about["title"], about["serious"], about["amended"]) == (kind, title, serious, form.endswith("/A"))


@pytest.mark.parametrize("form", ["4", "SC 13G", "424B2", "S-8", "DEF 14A", "144"])
def test_forms_that_arent_followed_are_ignored(form):
    assert filings.describe(form, []) is None


# ---------------------------------------------------------------------------
# Quotes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("quote, found", [
    ("Cloud revenue grew 30% on demand for AI services.", True),
    ("cloud revenue grew 30%  on demand", True),                                   # capitals and spacing don't matter
    ("Total revenue | $12,400 | $10,000", True),                                  # a table row
    ("Total revenue $12,400 $10,000", True),                                      # ...without the separators
    ("“Customers are choosing Northwind for their most important workloads,”", True),  # curly quotes
    ("Northwind Corp. today announced ... the quarter ended September 30, 2026", True),          # words skipped with ...
    ("the quarter ended September 30, 2026 ... Northwind Corp. today announced", False),         # ...but not out of order
    ("Cloud revenue grew 35% on demand for AI services.", False),                 # a changed number
    ("Revenue grew strongly across all segments.", False),                        # not in the filing
    ("Revenue was", False), ("", False), (None, False),                           # too short to prove anything
])
def test_a_quote_counts_only_if_its_in_the_filing(quote, found):
    assert filings.quoted(quote, filings._plain(edgar.to_text(press_release()))) is found


# ---------------------------------------------------------------------------
# Looking for filings
# ---------------------------------------------------------------------------

def test_a_check_lists_new_filings_once(sec):
    filing(NWND, "0000001111-26-000091", "4", "2026-10-28 18:00")                           # an insider trade: not followed
    filing(NWND, "0000001111-26-000010", "10-Q", "2026-04-29 16:10", report_date="2026-03-31")  # older than the lookback

    first = filings.check(read_new=False)
    second = filings.check(read_new=False)

    assert first["status"] == "ok" and first["new_filings"] == 2 and first["companies"] == 1 and first["reads"] == 0
    assert [f["accession"] for f in listed()] == [RESULTS, PREVIOUS]
    assert second["new_filings"] == 0 and second["new"] == []
    newest = listed()[0]
    assert (newest["kind"], newest["kind_label"], newest["title"]) == ("results", "Results", "Results announcement")
    assert newest["items"][0] == {"code": "2.02", "label": "Results announced"} and newest["read"] is None
    assert newest["url"].endswith("/000000111126000090/0000001111-26-000090-index.htm")
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 1 and CLAUDE == []  # the company list is asked for once


def test_an_empty_watchlist_or_a_filing_without_a_time_is_no_trouble(sec):
    FILED[NWND].append({"accessionNumber": "0000001111-26-000091", "filingDate": "2026-10-28", "reportDate": "", "form": "8-K",
                        "acceptanceDateTime": "", "items": "8.01", "primaryDocument": "x.htm", "primaryDocDescription": "8-K"})
    filing(NWND, "0000001111-26-000092", "8-K", "2026-10-28 18:00", "8.01", docs=[("y.htm", "8-K", COVER)])  # rebuilds the list
    assert filings.check(read_new=False)["new_filings"] == 3  # the one with no acceptance time is left out
    assert "0000001111-26-000091" not in [f["accession"] for f in listed()]
    sec.write_text("# nothing tracked yet\n")
    result = filings.check()
    assert (result["status"], result["companies"], result["new_filings"]) == ("ok", 0, 0)


def test_funds_and_unknown_tickers_are_skipped_quietly(sec):
    sec.write_text("NWND\nSPY\n")  # the SEC's company list has no SPY: funds don't file these forms

    result = filings.check(read_new=False)
    filings.check(read_new=False)

    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.not_covered(conn) == ["SPY"]
    assert result["status"] == "ok" and result["companies"] == 1
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 1  # not asked again the next time...
    with closing(filings.connect()) as conn:
        conn.execute("UPDATE filers SET checked_at = '2026-01-01T00:00:00Z' WHERE ticker = 'SPY'")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("SPY", 884394, "SPDR S&P 500 ETF TRUST"))
    filings.check(read_new=False)
    assert ASKED.count(f"{edgar.WWW}/files/company_tickers.json") == 2  # ...but again after a month, in case it's listed now


def test_two_share_classes_are_one_company_asked_and_read_once(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    sec.write_text("CNTA\nCNTB\n")
    companies(("CNTA", 3333, "CONTOSO INC"), ("CNTB", 3333, "CONTOSO INC"))
    filing(3333, "0000003333-26-000007", "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("c-8k.htm", "8-K", COVER), ("c-ex991.htm", "EX-99.1", press_release())])
    set_facts(3333, HISTORY)

    result = filings.check()

    assert ASKED.count(f"{edgar.DATA}/submissions/CIK0000003333.json") == 1
    assert sorted(f["ticker"] for f in listed()) == ["CNTA", "CNTB"] and result["new_filings"] == 2
    assert result["reads"] == 1 and len(CLAUDE) == 1                    # one first take, shown under both tickers
    assert all(f["read"]["status"] == "ok" for f in listed())
    assert len(SENT) == 1                                               # and one Discord message


def test_one_company_failing_doesnt_stop_the_rest(sec):
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    filing(2222, "0000002222-26-000004", "8-K", "2026-10-27 08:00", "7.01,9.01", docs=[("t-8k.htm", "8-K", COVER)])
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")

    result = filings.check(read_new=False)

    assert result["status"] == "partial" and "NWND: couldn't reach the SEC" in result["message"]
    assert [f["ticker"] for f in listed()] == ["TSPN"]


def test_being_limited_by_the_sec_stops_the_check(sec):
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    SEC[f"{edgar.DATA}/submissions/CIK{NWND:010d}.json"] = edgar.EdgarError("The SEC refused the request... wait 10 minutes", 403)

    result = filings.check(read_new=False)

    assert result["status"] == "partial" and "wait 10 minutes" in result["message"]
    assert f"{edgar.DATA}/submissions/CIK0000002222.json" not in ASKED  # asking for more would only make it worse


def test_an_unreachable_sec_is_given_up_on_quickly(sec):
    names = [f"CO{n}" for n in range(5)]
    sec.write_text("\n".join(names) + "\n")
    companies(*[(name, 4000 + n, f"COMPANY {n}") for n, name in enumerate(names)])
    filing(4000, "0000004000-26-000001", "8-K", "2026-10-28 16:00", "7.01", docs=[("c-8k.htm", "8-K", COVER)])
    for n in (1, 2, 3, 4):
        SEC[f"{edgar.DATA}/submissions/CIK{4000 + n:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")

    result = filings.check(read_new=False)

    asked = [url for url in ASKED if "/submissions/" in url]
    assert len(asked) == 3 and "stopped there: the SEC can't be reached right now" in result["message"]  # not all five
    assert result["status"] == "partial" and [f["ticker"] for f in listed()] == ["CO0"]  # what was found is kept


def test_without_a_contact_nothing_is_asked_and_a_run_carries_on(sec, monkeypatch):
    monkeypatch.undo()  # the real edgar.get_json again (conftest.py has removed SEC_CONTACT)
    monkeypatch.setattr(reports_db, "DB_PATH", sec.parent / "reports.db")
    monkeypatch.setattr(market_tools, "WATCHLIST_FILE", sec)
    monkeypatch.delenv("SEC_CONTACT", raising=False)
    monkeypatch.setattr(edgar.urllib.request, "urlopen", lambda *a, **k: pytest.fail("a request was made"))

    with pytest.raises(edgar.ContactMissing, match="Set SEC_CONTACT to your name and email"):
        filings.check()
    seen = []
    assert filings.check_before_run(seen.append) is None  # a run isn't stopped by it
    assert seen[0]["type"] == "warning" and "Set SEC_CONTACT" in seen[0]["message"]


def test_only_fresh_results_are_read_automatically(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", COVER)])
    filing(NWND, "0000001111-26-000094", "8-K/A", "2026-10-28 18:00", "2.02,9.01", docs=[
        ("n-8ka.htm", "8-K/A", COVER), ("n-ex991.htm", "EX-99.1", press_release())])

    result = filings.check()

    read = {f["accession"]: f["read"] and f["read"]["status"] for f in listed()}
    assert read == {RESULTS: "ok",                     # yesterday's results: read
                    PREVIOUS: None,                    # July's results: three months old, so listed only
                    "0000001111-26-000093": None,      # another announcement: a button, not automatic
                    "0000001111-26-000094": None}      # an amended announcement: a button too
    assert result["reads"] == 1 and result["cost_usd"] == 0.08 and len(CLAUDE) == 1
    assert the(RESULTS)["read"]["trigger"] == "automatic"
    assert filings.check()["reads"] == 0 and len(CLAUDE) == 1  # and never twice


def test_a_busy_day_reads_a_few_and_leaves_the_rest_for_the_next_check(sec, monkeypatch):
    monkeypatch.setattr(filings, "MAX_AUTOMATIC", 2)
    names = [f"CO{n}" for n in range(4)]
    sec.write_text("\n".join(names) + "\n")
    companies(*[(name, 4000 + n, f"COMPANY {n}") for n, name in enumerate(names)])
    for n in range(4):
        filing(4000 + n, f"000000400{n}-26-000001", "8-K", f"2026-10-28 16:0{n}", "2.02,9.01", docs=[
            ("c-8k.htm", "8-K", COVER), ("c-ex991.htm", "EX-99.1", press_release())])
        set_facts(4000 + n, HISTORY)

    assert filings.check()["reads"] == 2 and filings.check()["reads"] == 2 and filings.check()["reads"] == 0
    assert all(f["read"]["status"] == "ok" for f in listed())


# ---------------------------------------------------------------------------
# Reading a results announcement
# ---------------------------------------------------------------------------

def test_a_results_first_take(sec):
    REPLY["value"] = results_reply(changes=[{"text": "It no longer mentions supply constraints.",
                                             "quote": "Revenue was $12.4 billion and increased from a year earlier."}])
    filings.check(read_new=False)
    seen = []

    take = filings.read(RESULTS, emit=seen.append)

    assert take["status"] == "ok" and take["trigger"] == "manual" and take["cost_usd"] == 0.08
    assert take["document"] == "nwnd-ex991.htm" and take["document_url"].endswith("/000000111126000090/nwnd-ex991.htm")
    assert take["headline"].startswith("Northwind reported third-quarter revenue of $12.4 billion")
    assert [p["text"] for p in take["points"]] == ["Cloud revenue grew 30%, driven by AI services.",
                                                   "Management says customers are moving key workloads to it."]
    assert take["guidance"][0]["direction"] == "raised" and take["changes"][0]["text"].startswith("It no longer mentions")
    assert [e["message"] for e in seen] == ["Reading Northwind's results announcement",
                                           "First take on NWND: " + take["headline"]]

    system, prompt = CLAUDE[0]
    assert system == filings.RESULTS_PROMPT and "COMPANY: Northwind (NWND)" in prompt
    assert "FILING: Results announcement, filed 2026-10-28 (form 8-K, items 2.02,9.01)" in prompt
    assert "Total revenue | $12,400 | $10,000" in prompt and "UNITED STATES SECURITIES" not in prompt  # the press release, not the cover
    assert "PREVIOUS ANNOUNCEMENT (filed 2026-07-29)" in prompt and "Supply constraints limited growth" in prompt

    figures = take["figures"]
    rows = {r["metric"]: r for r in figures["rows"]}
    assert figures["period_end"] == "2026-09-30" and figures["basis"] == "quarter" and figures["source"] == "announcement"
    assert list(rows) == ["revenue", "gross_profit", "operating_income", "net_income", "eps_diluted"]
    revenue = rows["revenue"]
    assert revenue["value"] == 12_400 * M and revenue["as_written"] == "12,400" and revenue["quote"] == "Total revenue | $12,400 | $10,000"
    assert revenue["prior"] == {"end": "2026-06-30", "value": 11_800 * M, "derived": False}
    assert revenue["year_ago"] == {"end": "2025-09-30", "value": 10_000 * M, "derived": False}
    assert (revenue["change_prior_pct"], revenue["change_year_pct"]) == (5.1, 24.0)  # worked out in code: 12,400 vs 11,800 and 10,000
    assert rows["eps_diluted"]["value"] == 2.67 and rows["eps_diluted"]["change_year_pct"] == 33.5
    assert all(r["check"] == "pending" for r in figures["rows"])  # no quarterly report yet to check them against
    assert figures["margins"][1] == {"label": "Operating margin", "value": 32.3, "prior": 31.4, "year_ago": 30.0}
    assert take["notes"] == []


def test_points_claude_cant_quote_are_dropped(sec):
    reply = results_reply()
    reply["points"].append({"text": "Margins will keep expanding next year.", "quote": "We expect margins to keep expanding."})
    reply["guidance"].append({"text": "It will buy back $10 billion of shares.", "direction": "new", "quote": "a $10 billion buyback"})
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]

    assert len(take["points"]) == 2 and len(take["guidance"]) == 1  # the two invented ones are gone
    assert take["notes"] == ["2 items from Claude were left out, because their quotes aren't in the filing."]


def test_a_take_with_nothing_quotable_fails_and_says_why(sec):
    REPLY["value"] = results_reply(points=[{"text": "A strong quarter.", "quote": "It was a strong quarter overall."}])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "failed" and take["error"] == "Claude's reply quoted nothing that's in the filing"
    assert take["cost_usd"] == 0.08  # the cost is still recorded


def test_quotes_from_the_previous_announcement_dont_count(sec):
    REPLY["value"] = results_reply(changes=[{"text": "Supply is constrained.",
                                             "quote": "Supply constraints limited growth in the quarter."}])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["changes"] == []  # that sentence is in July's announcement, not this one
    assert "1 item from Claude was left out" in take["notes"][0]


@pytest.mark.parametrize("figure, why", [
    ({"metric": "revenue", "as_written": "12,400", "scale": "thousands", "quote": "Total revenue | $12,400 | $10,000"}, "unit"),
    ({"metric": "revenue", "as_written": "12,900", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"}, "number"),
    ({"metric": "revenue", "as_written": "12,400", "scale": "millions", "quote": "Total revenue was 12,400 this quarter"}, "quote"),
    ({"metric": "revenue", "as_written": "twelve billion", "scale": "millions", "quote": "Total revenue | $12,400 | $10,000"}, "number"),
    ({"metric": "revenue", "as_written": "12,400", "scale": "lots", "quote": "Total revenue | $12,400 | $10,000"}, "scale"),
    ({"metric": "free_cash_flow", "as_written": "4,000", "scale": "millions", "quote": "Operating income | 4,000 | 3,000"}, "metric"),
])
def test_a_figure_that_doesnt_check_out_is_left_out(sec, figure, why):
    reply = results_reply()
    reply["figures"][0] = figure
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]

    assert take["status"] == "ok" and "revenue" not in figures_of() and "net_income" in figures_of()
    if why == "unit":  # $12.4 million of revenue after $11.8 billion: the unit must be wrong
        assert take["notes"] == ["Revenue was left out: 12,400 thousands doesn't fit with $11.80B in the quarter to "
                                 "2026-06-30, so the unit is probably wrong."]
    elif why != "metric":
        assert "left out" in take["notes"][0]
    assert all(m["label"] != "Operating margin" for m in take["figures"]["margins"])  # no revenue, so no margins


def test_claude_never_sets_the_scale_of_earnings_per_share(sec):
    reply = results_reply()
    reply["figures"][4]["scale"] = "millions"
    REPLY["value"] = reply
    filings.check()
    assert figures_of()["eps_diluted"]["value"] == 2.67


@pytest.mark.parametrize("period_end", ["2026-12-31", "2025-09-30", "third quarter", None])
def test_an_unclear_quarter_means_no_comparisons(sec, period_end):
    REPLY["value"] = results_reply(period_end=period_end)
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["figures"]["period_end"] is None
    assert figures_of()["revenue"]["value"] == 12_400 * M and figures_of()["revenue"]["prior"] is None
    assert take["notes"] == ["The quarter's end date wasn't clear, so the figures aren't compared with earlier quarters."]


def test_a_loss_or_a_missing_quarter_gives_no_percentage(sec):
    history = dict(HISTORY)
    history[("2026-04-01", "2026-06-30")] = (11_800, 7_700, -300, -450, -0.38)  # a loss the quarter before
    del history[("2025-07-01", "2025-09-30")]                                    # and no figures from a year ago
    set_facts(NWND, history)
    filings.check()
    rows = figures_of()
    assert rows["net_income"]["prior"]["value"] == -450 * M and rows["net_income"]["change_prior_pct"] is None
    assert rows["revenue"]["change_prior_pct"] == 5.1 and rows["revenue"]["year_ago"] is None
    assert rows["revenue"]["change_year_pct"] is None


def test_a_bank_without_gross_profit_just_has_fewer_rows(sec):
    reply = results_reply()
    del reply["figures"][1:3]  # no gross profit or operating income in a bank's announcement
    REPLY["value"] = reply
    set_facts(NWND, HISTORY, revenue_tag="RevenuesNetOfInterestExpense", leave_out=("GrossProfit", "OperatingIncomeLoss"))
    filings.check()
    assert list(figures_of()) == ["revenue", "net_income", "eps_diluted"] and figures_of()["revenue"]["change_year_pct"] == 24.0
    assert [m["label"] for m in the(RESULTS)["read"]["figures"]["margins"]] == ["Net margin"]


def test_earlier_quarters_being_unavailable_still_gives_a_take(sec):
    SEC[f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"] = edgar.EdgarError("couldn't reach the SEC (timed out)")
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and figures_of()["revenue"]["value"] == 12_400 * M and figures_of()["revenue"]["prior"] is None
    assert take["notes"] == ["Earlier quarters couldn't be fetched for comparison (couldn't reach the SEC (timed out))."]


def test_a_first_results_announcement_has_nothing_to_compare_wording_with(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    filings.check()
    assert "PREVIOUS ANNOUNCEMENT" not in CLAUDE[0][1]
    assert the(RESULTS)["read"]["notes"] == ["There's no earlier results announcement on file to compare the wording with."]


def test_a_long_document_is_cut_off_and_says_so(sec, monkeypatch):
    monkeypatch.setattr(filings, "MAX_CHARS", 3_000)
    monkeypatch.setattr(filings, "PREVIOUS_CHARS", 500)
    padding = "".join(f"<p>Segment note {n}: nothing unusual happened in this business line.</p>" for n in range(400))
    SEC[edgar.folder(NWND, RESULTS) + "nwnd-ex991.htm"] = press_release(extra=padding)
    reply = results_reply()
    reply["figures"] = []  # the figures table is past the cut
    REPLY["value"] = reply
    filings.check()

    take = the(RESULTS)["read"]
    prompt = CLAUDE[0][1]

    assert take["status"] == "ok" and take["cut_off"] == 1 and take["chars"] <= 3_000
    assert "Segment note 5:" in prompt and "Segment note 399:" not in prompt and "Total revenue | $12,400" not in prompt
    assert len(prompt) < 3_000 + 500 + 600 and take["notes"][0] == "The document is long: the first 3,000 characters were read."
    assert take["figures"]["rows"] == []


def test_with_several_exhibits_the_press_release_is_the_one_read(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex992.htm", "EX-99.2", "<p>Slides for the earnings call.</p>" * 30),
        ("nwnd-ex991.htm", "EX-99.1", press_release()), ("nwnd-ex101.htm", "EX-10.1", "<p>A contract.</p>" * 30)])
    filings.check()
    assert the(RESULTS)["read"]["document"] == "nwnd-ex991.htm" and "Slides for the earnings call" not in CLAUDE[0][1]


def test_results_that_come_with_other_news_are_one_filing_and_one_message(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,5.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release())])
    result = filings.check()
    found = the(RESULTS)
    assert (found["kind"], found["serious"]) == ("results", True) and found["read"]["status"] == "ok"  # read as results
    assert found["title"] == "Results announcement; Directors or senior officers leaving or appointed"
    assert result["alerts"] == ["NWND results"] and len(SENT) == 1  # not a second "filed" message


def test_results_without_a_press_release_read_the_filing_itself(sec):
    FILED[NWND].clear()
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02", docs=[("nwnd-8k.htm", "8-K", press_release())])
    filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "ok" and take["document"] == "nwnd-8k.htm"
    assert "This results filing has no press release attached, so the filing's own text was read." in take["notes"]


@pytest.mark.parametrize("reply, error", [
    ("I'm sorry, I can't summarise this.", "no JSON"),
    ("[1, 2]", "no JSON"),
    ({"points": [{"text": "x", "quote": "Cloud revenue grew 30% on demand for AI services."}]}, "no headline"),
    (RuntimeError("Claude couldn't read the filing: error_max_budget_usd"), "error_max_budget_usd"),
])
def test_a_bad_reply_is_saved_as_a_failed_read(sec, reply, error):
    REPLY["value"] = reply
    result = filings.check()
    take = the(RESULTS)["read"]
    assert take["status"] == "failed" and error in take["error"] and take["finished_at"]
    assert result["read"][0]["status"] == "failed" and result["status"] == "ok"  # the check itself went fine
    REPLY["value"] = results_reply()
    assert filings.read(RESULTS)["status"] == "ok" and the(RESULTS)["read"]["status"] == "ok"  # trying again works


def test_a_later_failure_doesnt_hide_a_good_first_take(sec):
    filings.check()
    REPLY["value"] = "nonsense"
    assert filings.read(RESULTS)["status"] == "failed"
    assert the(RESULTS)["read"]["status"] == "ok"


def test_only_listed_filings_can_be_read_one_at_a_time(sec):
    with pytest.raises(filings.FilingError, match="No filing 0000009999-26-000001 is listed") as missing:
        filings.read("0000009999-26-000001")
    assert missing.value.status == 404
    filings.check(read_new=False)
    with closing(filings.connect()) as conn:
        conn.execute("INSERT INTO filing_reads (accession, ticker, trigger, status, started_at) VALUES (?, 'NWND', 'manual', 'running', ?)",
                     (RESULTS, filings._utc_now()))
    with pytest.raises(filings.FilingError, match="already being read") as busy:
        filings.read(RESULTS)
    assert busy.value.status == 409 and CLAUDE == []
    with closing(filings.connect()) as conn:  # a read that crashed long ago doesn't block a new one
        conn.execute("UPDATE filing_reads SET started_at = '2026-10-28T00:00:00Z'")
    assert the(RESULTS)["read"]["status"] == "failed" and "interrupted" in the(RESULTS)["read"]["error"]
    assert filings.read(RESULTS)["status"] == "ok"


# ---------------------------------------------------------------------------
# Reading other filings
# ---------------------------------------------------------------------------

DEPARTURE = """<html><body><p>FORM 8-K</p><p>Item 5.02 Departure of Directors or Certain Officers.</p>
<p>On October 27, 2026, Jordan Lee notified Northwind Corp. of the decision to resign as Chief Financial Officer, effective December 31, 2026.</p>
<p>The resignation was not the result of any disagreement with the company.</p></body></html>"""
ANNOUNCEMENT_REPLY = {"headline": "Northwind's chief financial officer is resigning at the end of the year.",
                      "points": [{"text": "Jordan Lee resigns as CFO, effective December 31, 2026.",
                                  "quote": "Jordan Lee notified Northwind Corp. of the decision to resign as Chief Financial Officer"},
                                 {"text": "A successor has been named.", "quote": "Avery Kim will become Chief Financial Officer"}]}


def test_an_announcement_is_read_with_its_press_release(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[
        ("n-8k.htm", "8-K", DEPARTURE), ("n-ex991.htm", "EX-99.1", "<p>Northwind names Avery Kim. Avery Kim will become Chief "
                                                                  "Financial Officer on January 1, 2027.</p>" + "<p>About Northwind.</p>" * 20)])
    REPLY["value"] = ANNOUNCEMENT_REPLY
    filings.check(read_new=False)

    take = filings.read("0000001111-26-000093")

    system, prompt = CLAUDE[0]
    assert system == filings.ANNOUNCEMENT_PROMPT and "PREVIOUS ANNOUNCEMENT" not in prompt
    assert "decision to resign as Chief Financial Officer" in prompt and "--- Attached press release (EX-99.1) ---" in prompt
    assert take["status"] == "ok" and len(take["points"]) == 2 and take["figures"] is None and take["guidance"] == []
    assert the("0000001111-26-000093")["serious"] is True


def test_a_filing_with_nothing_readable_fails_clearly(sec):
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "8.01", docs=[("scan.htm", "8-K", "<p>See attached.</p>")])
    filing(NWND, "0000001111-26-000096", "8-K", "2026-10-28 17:30", "8.01", docs=[("slides.pdf", "8-K", "%PDF")])
    filings.check(read_new=False)
    assert "no text that can be read (it may be a scan or a PDF)" in filings.read("0000001111-26-000093")["error"]
    assert "no document that can be read" in filings.read("0000001111-26-000096")["error"]
    assert CLAUDE == []  # nothing was sent to Claude, so nothing was spent


def test_a_report_is_read_through_managements_discussion(sec):
    body = "<p>Revenue increased 24% driven by cloud services. Operating expenses increased 12% as we hired engineers.</p>" * 40
    report = ("<html><body><p>Item 1. Financial Statements</p>" + "<p>Balance sheet line.</p>" * 30
              + "<p>Item 2. Management's Discussion and Analysis of Financial Condition and Results of Operations</p>" + body
              + "<p>Item 3. Quantitative and Qualitative Disclosures About Market Risk</p><p>Risk text.</p></body></html>")
    filing(NWND, REPORT, "10-Q", "2026-10-30 07:00", report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", report)])
    filing(NWND, "0000001111-26-000097", "10-Q", "2026-10-30 08:00", report_date="2026-09-30", docs=[
        ("odd-10q.htm", "10-Q", "<p>A report laid out in its own way, with no standard headings.</p>" * 20)])
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)
    REPLY["value"] = {"headline": "Growth came from cloud services, while hiring pushed costs up.",
                      "points": [{"text": "Costs rose 12% on hiring.", "quote": "Operating expenses increased 12% as we hired engineers."}]}
    filings.check(read_new=False)

    take = filings.read(REPORT)
    odd = filings.read("0000001111-26-000097")

    system, prompt = CLAUDE[0]
    assert system == filings.REPORT_PROMPT and take["status"] == "ok" and take["figures"] is None
    assert "Operating expenses increased 12%" in prompt and "Balance sheet line." not in prompt and "Risk text." not in prompt
    assert odd["status"] == "failed"  # its text has no such sentence, so the quote check fails...
    assert "A report laid out in its own way" in CLAUDE[1][1]  # ...but the start of the report was what Claude was given


def test_companies_outside_the_us_are_listed_and_read_on_request(sec):
    sec.write_text("LTWR\n")
    companies(("LTWR", 5555, "LITWARE NV"))
    filing(5555, "0000005555-26-000003", "6-K", "2026-10-28 06:30", docs=[("ltwr-6k.htm", "6-K", DEPARTURE)])
    filing(5555, "0000005555-26-000001", "20-F", "2026-09-15 06:30", report_date="2026-06-30", docs=[("ltwr-20f.htm", "20-F", "x")])
    REPLY["value"] = ANNOUNCEMENT_REPLY | {"points": ANNOUNCEMENT_REPLY["points"][:1]}

    result = filings.check()

    assert [(f["form"], f["kind"], f["figures"]) for f in listed()] == [("6-K", "foreign", None), ("20-F", "annual", None)]
    assert result["reads"] == 0 and CLAUDE == []                      # a 6-K is never read automatically
    assert f"{edgar.DATA}/api/xbrl/companyfacts/CIK0000005555.json" not in ASKED  # and no US-style figures are looked for
    assert filings.read("0000005555-26-000003")["status"] == "ok" and CLAUDE[0][0] == filings.ANNOUNCEMENT_PROMPT


# ---------------------------------------------------------------------------
# The report confirms the announcement
# ---------------------------------------------------------------------------

def file_report(when="2026-10-30 07:00", quarters=None, **facts_options):
    filing(NWND, REPORT, "10-Q", when, report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", "<p>x</p>")])
    set_facts(NWND, {**HISTORY, **(quarters or THIRD_QUARTER)}, **facts_options)


def test_the_quarterly_report_confirms_the_announcements_figures(sec):
    filings.check()
    assert all(r["check"] == "pending" for r in figures_of().values())
    file_report()
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)

    result = filings.check()

    assert result["new_filings"] == 1 and result["reads"] == 0 and len(CLAUDE) == 1  # confirming needs no Claude
    assert {m: r["check"] for m, r in figures_of().items()} == dict.fromkeys(
        ["revenue", "gross_profit", "operating_income", "net_income", "eps_diluted"], "confirmed")
    assert figures_of()["revenue"]["report_value"] == 12_400 * M
    own = the(REPORT)["figures"]  # the report's own figures are saved too, with the same comparisons
    assert own["source"] == "report" and own["period_end"] == "2026-09-30" and own["basis"] == "quarter"
    assert own["rows"][0]["value"] == 12_400 * M and own["rows"][0]["change_year_pct"] == 24.0
    assert own["margins"][1]["value"] == 32.3


def test_a_figure_the_report_gives_differently_is_flagged(sec):
    filings.check()
    file_report(quarters={("2026-07-01", "2026-09-30"): (12_400, 8_100, 4_000, 2_900, 2.42)})  # net income restated lower
    filings.check()
    rows = figures_of()
    assert rows["net_income"]["check"] == "differs" and rows["net_income"]["report_value"] == 2_900 * M
    assert rows["eps_diluted"]["check"] == "differs" and rows["eps_diluted"]["report_value"] == 2.42
    assert rows["revenue"]["check"] == "confirmed"


@pytest.mark.parametrize("announced, reported, same", [
    (12_400 * M, 12_400.4 * M, True),     # tables round to the million
    (12.4e9, 12.449e9, True),             # sentences round to a tenth of a billion
    (12.4e9, 12.6e9, False),
    (-450 * M, -450.3 * M, True), (450 * M, -450 * M, False),
    (3 * M, 3.5 * M, True),               # tiny figures: within the rounding of a table in millions
])
def test_rounding_is_allowed_but_real_differences_arent(announced, reported, same):
    assert filings.agrees("revenue", announced, reported) is same


def test_earnings_per_share_must_match_to_the_cent():
    assert filings.agrees("eps_diluted", 2.67, 2.674) and not filings.agrees("eps_diluted", 2.67, 2.70)


def test_a_report_filed_the_same_day_confirms_straight_away(sec):
    file_report(when="2026-10-28 16:01")  # some companies file the report minutes before the announcement
    result = filings.check()
    assert result["reads"] == 1 and all(r["check"] == "confirmed" for r in figures_of().values())
    assert figures_of()["revenue"]["prior"]["end"] == "2026-06-30"  # still compared with the quarter before, not with itself


def test_figures_the_report_doesnt_give_stop_waiting(sec):
    filings.check()
    file_report(leave_out=("GrossProfit",))
    address = f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"
    filings.check()
    asked = ASKED.count(address)
    assert figures_of()["gross_profit"]["check"] == "not_checked" and figures_of()["revenue"]["check"] == "confirmed"
    filings.check()
    assert ASKED.count(address) == asked  # nothing left to wait for, so the large file isn't downloaded again


def test_a_report_whose_figures_never_appear_isnt_fetched_forever(sec):
    filing(NWND, REPORT, "10-Q", "2026-10-30 07:00", report_date="2026-09-30", docs=[("nwnd-10q.htm", "10-Q", "<p>x</p>")])
    address = f"{edgar.DATA}/api/xbrl/companyfacts/CIK{NWND:010d}.json"
    CLOCK["now"] = datetime(2026, 10, 30, 9, 0, tzinfo=ET)
    filings.check(read_new=False)
    assert the(REPORT)["figures"] is None and ASKED.count(address) == 1  # not published yet: it will look again
    CLOCK["now"] = datetime(2026, 11, 5, 9, 0, tzinfo=ET)
    filings.check(read_new=False)
    assert the(REPORT)["figures"]["rows"] == [] and ASKED.count(address) == 2  # days later: settled as "none"
    filings.check(read_new=False)
    assert ASKED.count(address) == 2


def test_a_fourth_quarter_is_checked_against_the_annual_report(sec):
    """The annual report gives the year, not the quarter: revenue is checked against the year minus nine
    months, but earnings per share can't be worked out that way exactly, so it's marked as not checked."""
    FILED[NWND].clear()
    year, nine = ("2025-10-01", "2026-09-30"), ("2025-10-01", "2026-06-30")
    filing(NWND, RESULTS, "8-K", "2026-10-28 16:05", "2.02,9.01", docs=[
        ("nwnd-8k.htm", "8-K", COVER), ("nwnd-ex991.htm", "EX-99.1", press_release("fourth"))])
    filing(NWND, REPORT, "10-K", "2026-10-28 16:30", report_date="2026-09-30", docs=[("nwnd-10k.htm", "10-K", "<p>x</p>")])
    set_facts(NWND, {**HISTORY, year: (46_000, 30_000, 14_500, 11_600, 9.70), nine: (33_600, 21_900, 10_500, 8_400, 7.02),
                     ("2024-10-01", "2025-09-30"): (38_000, 24_000, 11_000, 8_800, 7.30)})

    filings.check()

    rows = figures_of()
    assert rows["revenue"]["check"] == "confirmed" and rows["revenue"]["report_value"] == (46_000 - 33_600) * M
    assert rows["eps_diluted"]["check"] == "not_checked" and rows["eps_diluted"]["report_value"] is None
    own = the(REPORT)["figures"]  # the annual report's own figures are for the year, against the year before
    assert own["basis"] == "year" and own["rows"][0]["value"] == 46_000 * M and own["rows"][0]["prior"] is None
    assert own["rows"][0]["year_ago"]["value"] == 38_000 * M and own["rows"][0]["change_year_pct"] == 21.1


def test_an_amended_report_doesnt_replace_the_checks(sec):
    filings.check()
    file_report()
    filing(NWND, "0000001111-26-000099", "10-Q/A", "2026-10-31 07:00", report_date="2026-09-30", docs=[("a.htm", "10-Q/A", "x")])
    CLOCK["now"] = datetime(2026, 11, 2, 9, 0, tzinfo=ET)
    filings.check()
    assert the("0000001111-26-000099")["title"] == "Amended: Quarterly report" and the("0000001111-26-000099")["figures"] is None
    assert figures_of()["revenue"]["check"] == "confirmed"


def test_a_late_report_notice_is_flagged_without_claude(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    filing(NWND, "0000001111-26-000098", "NT 10-Q", "2026-10-28 17:10", docs=[("nt.htm", "NT 10-Q", "<p>x</p>")])
    filings.check(read_new=False)
    late = the("0000001111-26-000098")
    assert (late["kind"], late["serious"], late["title"]) == ("late", True, "Says its quarterly report will be late")
    assert SENT[0]["content"] == "**NWND filed with the SEC**" and "will be late" in SENT[0]["embeds"][0]["title"]
    assert CLAUDE == []


# ---------------------------------------------------------------------------
# The calendar
# ---------------------------------------------------------------------------

def add_event(ticker, day, title="Earnings report", note=None, kind="earnings"):
    with closing(events.connect()) as conn:
        return conn.execute(
            """INSERT INTO events (event_date, ticker, company, kind, title, date_note, first_seen, last_seen)
               VALUES (?, ?, 'Northwind', ?, ?, ?, '2026-10-01', '2026-10-01')""", (day, ticker, kind, title, note)).lastrowid


def reported(start="2026-10-01", end="2026-11-15"):
    with closing(reports_db.connect(readonly=True)) as conn:
        found = events.events_between(conn, start, end)
        return filings.for_calendar(conn, found, start, end)


def test_the_calendar_shows_what_was_reported(sec):
    event = add_event("NWND", "2026-10-28")
    add_event("NWND", "2026-10-28", "Ex-dividend date", kind="dividend")
    with closing(reports_db.connect(readonly=True)) as conn:
        assert [e["ticker"] for e in filings.expected(conn, date(2026, 10, 29))] == ["NWND"]  # due yesterday, nothing filed yet
        assert filings.for_calendar(conn, events.events_between(conn, "2026-10-01", "2026-11-15"), "2026-10-01", "2026-11-15") == []

    filings.check()

    found = reported()
    assert len(found) == 1 and found[0]["event_id"] == event and found[0]["accession"] == RESULTS  # July's is out of range
    assert found[0]["headline"].startswith("Northwind reported third-quarter revenue") and found[0]["company"] == "Northwind"
    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.expected(conn, date(2026, 10, 29)) == []


@pytest.mark.parametrize("event_day, note, matched", [
    ("2026-10-26", None, True),                        # Yahoo had it two days early
    ("2026-10-30", None, True),                        # ...or two days late
    ("2026-10-22", None, False),                       # six days out: a different event
    ("2026-10-16", "Estimated: Yahoo Finance shows a window of Oct 16 to Oct 30.", True),   # an unconfirmed window
    ("2026-11-06", "Estimated: Yahoo Finance shows a window of Nov 6 to Nov 12.", False),   # a window that starts later
])
def test_a_calendar_date_thats_a_little_out_still_matches(sec, event_day, note, matched):
    event = add_event("NWND", event_day, note=note)
    filings.check(read_new=False)
    found = reported()
    assert found[0]["filing_date"] == "2026-10-28" and found[0]["event_id"] == (event if matched else None)
    assert found[0]["headline"] is None  # listed, not read


def test_results_the_calendar_never_expected_still_show_on_their_day(sec):
    filings.check(read_new=False)
    assert [(r["filing_date"], r["event_id"]) for r in reported("2026-10-01", "2026-10-31")] == [("2026-10-28", None)]
    assert reported("2026-11-01", "2026-11-30") == []
    assert [r["filing_date"] for r in reported("2026-07-01", "2026-07-31")] == ["2026-07-29"]


def test_another_companys_results_never_answer_an_event(sec):
    add_event("TSPN", "2026-10-28")
    filings.check(read_new=False)
    assert reported()[0]["event_id"] is None
    with closing(reports_db.connect(readonly=True)) as conn:
        assert filings.expected(conn, date(2026, 10, 29)) == []  # Tailspin isn't tracked, so it isn't waited for


# ---------------------------------------------------------------------------
# Discord
# ---------------------------------------------------------------------------

def test_discord_hears_about_results_and_serious_announcements_once(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 17:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", DEPARTURE)])
    filing(NWND, "0000001111-26-000096", "8-K", "2026-10-28 17:30", "7.01,9.01", docs=[("n2-8k.htm", "8-K", COVER)])

    result = filings.check()

    assert result["alerts"] == ["NWND filing", "NWND results"] and len(SENT) == 2  # not the routine 7.01, not July's results
    results = next(m for m in SENT if m["content"] == "**NWND reported results**")["embeds"][0]
    assert results["title"] == "Northwind: results" and results["url"].endswith("0000001111-26-000090-index.htm")
    assert "Northwind reported third-quarter revenue of $12.4 billion" in results["description"]
    assert "• Revenue $12.40B (+24.0% vs a year ago)" in results["description"]
    assert "• Earnings per share (diluted) $2.67 (+33.5% vs a year ago)" in results["description"]
    assert "**Guidance (raised):** It expects fourth-quarter revenue" in results["description"]
    assert "research, not investment advice" in results["footer"]["text"]
    serious = next(m for m in SENT if m["content"] == "**NWND filed with the SEC**")["embeds"][0]
    assert serious["title"] == "Northwind: Directors or senior officers leaving or appointed"
    assert "Not read by Claude yet" in serious["description"]
    assert filings.check()["alerts"] == [] and len(SENT) == 2  # once each


def test_a_discord_message_that_fails_is_sent_by_the_next_check(sec, monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    monkeypatch.setattr(alerts, "send", lambda payload: (_ for _ in ()).throw(alerts.SendError("couldn't reach Discord")))
    first = filings.check()
    assert first["status"] == "partial" and "Discord: NWND results (couldn't reach Discord)" in first["message"]
    monkeypatch.setattr(alerts, "send", SENT.append)
    assert filings.check()["alerts"] == ["NWND results"] and len(SENT) == 1


def test_no_discord_without_a_webhook_or_for_old_filings(sec, monkeypatch):
    assert filings.check()["alerts"] == [] and SENT == []  # no webhook set
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://discord.com/api/webhooks/1/x")
    CLOCK["now"] = datetime(2026, 11, 10, 9, 0, tzinfo=ET)
    assert filings.check()["alerts"] == [] and SENT == []  # set up two weeks later: old news isn't sent


# ---------------------------------------------------------------------------
# Briefs, runs and Ask
# ---------------------------------------------------------------------------

def test_the_agents_tool_gives_first_takes_for_flagged_tickers(sec):
    assert market_tools.recent_filings(["NWND"])["note"].startswith("Filings haven't been checked yet")
    add_event("TSPN", "2026-10-28")
    sec.write_text("NWND\nTSPN\n")
    companies(("NWND", NWND, "NORTHWIND CORP"), ("TSPN", 2222, "TAILSPIN INC"))
    filing(2222, "0000002222-26-000004", "8-K", "2026-10-27 08:00", "5.02,9.01", docs=[("t-8k.htm", "8-K", DEPARTURE)])
    filings.check()

    result = market_tools.recent_filings([" nwnd ", "TSPN", "AAPL"])

    assert set(result["filings"]) == {"NWND", "TSPN"} and "note" not in result and result["checked"]
    nwnd = result["filings"]["NWND"][0]  # July's announcement is too old to be listed here
    assert len(result["filings"]["NWND"]) == 1 and nwnd["kind"] == "Results" and nwnd["url"].endswith("-index.htm")
    take = nwnd["first_take"]
    assert take["headline"].startswith("Northwind reported") and take["guidance"] == [
        "Raised: It expects fourth-quarter revenue of $12.8 billion to $13.2 billion."]
    assert take["figures"][0] == "Revenue $12.40B (+24.0% vs a year ago), +5.1% vs the quarter before"
    tspn = result["filings"]["TSPN"][0]
    assert tspn["first_take"] is None and tspn["serious"] and tspn["title"].startswith("Directors or senior officers")
    assert [e["ticker"] for e in result["expected"]] == ["TSPN"]  # the calendar expected results that haven't come


def test_a_run_checks_filings_first_even_when_the_report_is_already_saved(sec, monkeypatch):
    order = []
    monkeypatch.setattr(run_brief, "send_alerts", lambda *a, **k: asyncio.sleep(0))
    monkeypatch.setattr(run_brief.search_index, "sync", lambda *a, **k: None)
    monkeypatch.setattr(run_brief.stories, "after_final_report", lambda emit=None: None)
    session = {"status": "complete", "as_of": "2026-10-28"}
    monkeypatch.setattr(run_brief, "market_session", lambda: session)
    monkeypatch.setattr(run_brief, "flag_events", lambda: {
        "session": session, "flagged": [], "quiet": [{"ticker": "NWND", "last_close": 1.0, "return_1d_pct": 0.1}], "errors": []})

    async def fake_query(*, prompt, options):
        order.append(("agent", the(RESULTS)["read"]["status"]))  # the first take is there before the agent starts
        assert "mcp__market__recent_filings" in options.allowed_tools
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
                            session_id="s", total_cost_usd=0.01, result="# Brief\n\nNothing unusual.")

    monkeypatch.setattr(run_brief, "query", fake_query)
    seen = []

    asyncio.run(run_brief.run_once(seen.append))

    assert order == [("agent", "ok")]
    messages = [e.get("message") for e in seen]
    assert "Reading Northwind's results announcement" in messages
    assert "Filings: 2 new: NWND (results announcement), NWND (results announcement)" in messages
    assert [e["type"] for e in seen][-1] == "saved"

    filing(NWND, "0000001111-26-000093", "8-K", "2026-10-28 19:00", "5.02,9.01", docs=[("n-8k.htm", "8-K", DEPARTURE)])
    seen.clear()
    asyncio.run(run_brief.run_once(seen.append))  # the report is final already: the run is skipped, filings still checked
    assert [e["type"] for e in seen] == ["filings", "skipped"] and "NWND (directors or senior officers" in seen[0]["message"]


def test_a_problem_with_filings_never_stops_a_run(sec, monkeypatch):
    monkeypatch.setattr(filings, "check", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("database is locked")))
    seen = []
    assert filings.check_before_run(seen.append) is None
    assert seen == [{"type": "warning", "message": "Filings weren't checked (database is locked). The run carries on without them."}]


def test_ask_sees_filings_and_first_takes(sec):
    file_report(when="2026-10-28 16:30")
    filings.check()

    with closing(reports_db.connect(readonly=True)) as conn:
        named = ask.filings_section(conn, ["NWND"])
        general = ask.filings_section(conn, [])
        reports_db.save_report(reports_db.connect(), session_date="2026-10-28", status="final", title="Brief", body_md="# Brief",
                               as_of="2026-10-28", scan={"session": {"status": "complete", "as_of": "2026-10-28"}, "flagged": [],
                                                         "quiet": [{"ticker": "NWND", "last_close": 1.0, "return_1d_pct": 0.1}],
                                                         "errors": []}, sources=[])
        context, _ = ask.build_context(conn, "What did NWND say about its outlook?")

    assert named in context  # Claude is actually given it
    assert "## Company filings for NWND (cite as (filing, date filed))" in named
    assert "- 2026-10-28: Quarterly report (not read)" in named and "- 2026-07-29: Results announcement (not read)" in named
    assert "### NWND: Results announcement, filed 2026-10-28 (cite as (filing, 2026-10-28))" in named
    assert "- Revenue: $12.40B, +5.1% vs the quarter before, +24.0% vs a year earlier, confirmed by the quarterly report" in named
    assert "- Operating margin: 32.3%" in named and "- Cloud revenue grew 30%, driven by AI services." in named
    assert "- Guidance (raised): It expects fourth-quarter revenue of $12.8 billion to $13.2 billion." in named
    assert "## Company filings in the last 7 days" in general
    assert "- 2026-10-28 NWND: Results announcement. Northwind reported third-quarter revenue" in general
    assert "2026-07-29" not in general
    assert "(filing, then the date it was filed)" in ask.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(sec, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "filing_checks", api.BackgroundJob(
        "filings_check", lambda: 60, "busy", "Filings were just checked. Try again in {}."))
    monkeypatch.setattr(api, "filing_reads", api.BackgroundJob(
        "filing_read", lambda: 60, "busy", "A filing was just read. Try again in {}."))
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_check_then_the_filings_view(client, sec):
    sec.write_text("NWND\nSPY\n")
    add_event("NWND", "2026-10-29", "Earnings report")
    empty = client.get("/api/filings").json()
    assert client.get("/api/calendar?start=2026-10-01&end=2026-10-31").json()["reported"] == []  # before any check
    assert empty["filings"] == [] and empty["checked"] is None and empty["contact_set"] is False
    assert [e["ticker"] for e in empty["expected"]] == ["NWND"] and empty["max_cost_usd"] == 0.5

    started = client.post("/api/filings/check", json={})
    assert started.status_code == 202 and started.json()["check"]["state"] == "running"
    done = wait_for(lambda: (v := client.get("/api/filings").json())["check"]["state"] == "finished" and v)
    assert client.post("/api/filings/check", json={}).status_code == 429  # cooldown

    assert [f["accession"] for f in done["filings"]] == [RESULTS, PREVIOUS] and done["tickers"] == ["NWND"]
    assert done["filings"][0]["read"]["headline"].startswith("Northwind reported") and done["not_covered"] == ["SPY"]
    assert done["checked"]["trigger"] == "manual" and done["check"]["result"]["reads"] == 1
    assert done["expected"] == []  # the event was a day out, and still counts as answered
    assert client.get("/api/filings?ticker=tspn").json()["filings"] == []
    assert client.get("/api/filings?ticker=nwnd").json()["filings"][0]["ticker"] == "NWND"
    assert client.get("/api/filings?ticker=N W").status_code == 400
    calendar = client.get("/api/calendar?start=2026-10-01&end=2026-10-31").json()
    assert calendar["reported"][0]["accession"] == RESULTS and calendar["reported"][0]["event_id"] == calendar["events"][0]["id"]


def test_api_read_a_filing(client):
    filings.check(read_new=False)
    queue = api.hub.subscribe()

    started = client.post("/api/filings/read", json={"accession": RESULTS})
    assert started.status_code == 202 and started.json()["read"]["target"] == {"accession": RESULTS, "ticker": "NWND"}
    done = wait_for(lambda: (v := client.get("/api/filings").json())["read"]["state"] == "finished" and v)

    assert done["filings"][0]["read"]["status"] == "ok" and done["read"]["result"]["headline"].startswith("Northwind")
    progress = []
    while not queue.empty():
        event = queue.get_nowait()
        if event["type"] == "filing_read":
            progress.append(event["job"]["message"])
    assert "Reading Northwind's results announcement" in progress
    assert client.post("/api/filings/read", json={"accession": PREVIOUS}).status_code == 429


@pytest.mark.parametrize("body, status, message", [
    ({"accession": "0000009999-26-000001"}, 404, "No filing 0000009999-26-000001 is listed"),
    ({"accession": "123"}, 400, "send JSON like"),
    ({"ticker": "NWND"}, 400, "send JSON like"),
    ([RESULTS], 400, "send JSON like"),
])
def test_api_read_explains_what_went_wrong(client, body, status, message):
    filings.check(read_new=False)
    response = client.post("/api/filings/read", json=body)
    assert response.status_code == status and message in response.json()["error"] and CLAUDE == []


def test_other_websites_cannot_start_checks_or_reads(client):
    filings.check(read_new=False)
    for path, body in (("/api/filings/check", {}), ("/api/filings/read", {"accession": RESULTS})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
        assert client.post(path, content="x", headers={"Content-Type": "text/plain"}).status_code == 415
    assert CLAUDE == [] and the(RESULTS)["read"] is None


def test_filings_found_by_scheduled_runs_reach_open_pages(sec, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        await asyncio.to_thread(filings.check)  # what another program (a scheduled run) does
        seen = []
        deadline = time.monotonic() + 3
        while "filings_updated" not in seen and time.monotonic() < deadline:
            try:
                seen.append((await asyncio.wait_for(queue.get(), 0.5))["type"])
            except asyncio.TimeoutError:
                pass
        watcher.cancel()
        return seen

    assert "filings_updated" in asyncio.run(scenario())


# ---------------------------------------------------------------------------
# Live
# ---------------------------------------------------------------------------

@pytest.mark.skipif(not os.getenv("LIVE_TESTS"), reason="set LIVE_TESTS=1 (and SEC_CONTACT) to ask the SEC")
def test_live_filings(monkeypatch):
    if not LIVE_CONTACT:
        pytest.skip('set SEC_CONTACT to your name and email first, e.g. export SEC_CONTACT="Jane Doe jane@yourmail.com"')
    monkeypatch.setenv("SEC_CONTACT", LIVE_CONTACT)

    apple = edgar.company_numbers()["AAPL"]
    found = edgar.list_filings(apple["cik"])["filings"]
    followed = [(f, filings.describe(f["form"], f["items"])) for f in found]
    followed = [(f, about) for f, about in followed if about]
    print(f"\nApple is company {apple['cik']} ({apple['name']}). Its latest filings that are followed:")
    for f, about in followed[:8]:
        print(f"  {f['filing_date']}  {f['form']:<6} {f['accession']}  {about['title']}")
    results = next(f for f, about in followed if about["kind"] == "results")
    documents = edgar.filing_documents(apple["cik"], results["accession"], results["primary_doc"], results["form"])
    print(f"Documents in the results announcement of {results['filing_date']}:", [(d["name"], d["type"]) for d in documents])
    press = filings._press_release(documents)
    text = edgar.to_text(edgar.get_text(press["url"]))
    print(f"Its press release is {len(text):,} characters. It starts:\n  " + "\n  ".join(text.splitlines()[:4]))
    known = edgar.periods(edgar.company_facts(apple["cik"]))
    print("Quarterly revenue from the SEC's structured data:")
    for end in sorted(known["revenue"]["quarters"], reverse=True)[:5]:
        q = known["revenue"]["quarters"][end]
        print(f"  quarter to {end}: {filings.money(q['value'])}" + ("  (worked out from the annual report)" if q["derived"] else ""))

    assert apple["cik"] == 320193 and results["filed_at"].endswith("Z") and "2.02" in results["items"]
    assert press is not None and press["type"].startswith("EX-99") and len(text) > 2000
    assert {"revenue", "net_income", "eps_diluted"} <= set(known) and len(known["revenue"]["quarters"]) >= 8
    assert any(q["derived"] for q in known["revenue"]["quarters"].values())  # a fourth quarter, worked out
```
