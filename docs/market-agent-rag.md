# Market Analyst Agent: RAG & Search

Adds **retrieval** across your whole report history, used in two places:

- **Ask gets smarter.** For each question, it finds the most relevant passages from *any* day, not just the 10 most recent reports, and Claude answers from them with dates cited.
- **A search box** on the Previous days tab. Type "analyst downgrade" or "regulatory" and see the matching passages, grouped by day, with your words highlighted. Click a day to open its report.

Search works two ways, blended into one ranking: **by keywords** (built into SQLite, free and offline) and **by meaning** (Voyage AI embeddings). So "rating cut" also finds "An analyst downgrade weighed on the shares."

This builds on `market-agent-frontend.md` (the version with charts). Finish that guide first.

---

## Contents

1. [How it works](#1-how-it-works)
2. [Before you start](#2-before-you-start)
3. [Step 1: Get a Voyage AI key](#3-step-1-get-a-voyage-ai-key)
4. [Step 2: Install and set the key](#4-step-2-install-and-set-the-key)
5. [Step 3: Add the search index](#5-step-3-add-the-search-index)
6. [Step 4: Update Ask, runs and the API](#6-step-4-update-ask-runs-and-the-api)
7. [Step 5: Add the search box](#7-step-5-add-the-search-box)
8. [Step 6: Build the index and try it](#8-step-6-build-the-index-and-try-it)
9. [Test it](#9-test-it)
10. [Using search and Ask](#10-using-search-and-ask)
11. [Settings and tuning](#11-settings-and-tuning)
12. [API additions reference](#12-api-additions-reference)
13. [Costs and privacy](#13-costs-and-privacy)
14. [Maintenance](#14-maintenance)
15. [Troubleshooting](#15-troubleshooting)
16. [Appendix: full source code](#appendix-full-source-code)

---

## 1. How it works

```
 reports.db ──(read only)──▶ search_index.py ──▶ search.db  (the index: rebuildable, never your reports)
                                  │
                                  ├── splits each report into passages:
                                  │     one per flagged ticker, plus an overview
                                  ├── keyword index: SQLite full-text search (FTS5)
                                  └── meaning index: Voyage AI embeddings (one vector per passage)

 A search ──▶ keyword ranking ─┐
          └─▶ meaning ranking ─┴─▶ blended (reciprocal rank fusion) ──▶ best passages, labelled
                                                                        "keywords", "meaning" or both
```

**Passages.** Each report is split into an **overview** (title, quiet tickers, data issues) and **one passage per flagged ticker** (what happened, likely why, and the news headlines the agent read). Every passage starts with its report's title, so it always carries its date. Link addresses are left out, so every keyword match is visible text.

**Two searches, one ranking.**

| | Keywords | Meaning |
|---|---|---|
| Finds | The words you typed, including variations ("downgraded" finds "downgrade") | Passages about the same thing in different words ("profit" finds "quarterly results") |
| Runs on | SQLite's built-in full-text search: free, offline | Voyage AI embeddings: needs `VOYAGE_API_KEY` |
| Without a key | Works | Switched off; search falls back to keywords only |

The two rankings are combined, so passages that match both ways come first. Meaning matches only count if they're close to the best one, which keeps loosely related passages out (section 11).

**The index is a separate file.** `search.db` sits next to `reports.db`, is built *from* it, and only ever *reads* it. You can delete `search.db` at any time and rebuild it. Your reports and their protections are untouched.

**Keeping it current.** The index updates itself:

| When | What happens |
|---|---|
| A run saves a report (scheduled or Run now) | `run_brief.py` updates the index straight after saving. If that fails, the report is still saved and the index catches up later |
| The API starts | It catches up on anything saved while it was off |
| The API spots a new save (every ~2 seconds) | It indexes and embeds it in the background |
| Someone searches | New reports are made searchable by keyword first, so nothing is ever missing from results |

**How Ask uses it (the RAG part).** For each question, Ask gathers, within its size limit:

1. Figures across days for any watchlist ticker named in the question (as before)
2. **New:** the 8 passages that best match the question, from any day, labelled with their report's date
3. The 10 most recent reports in full, plus recent reports where a named ticker was flagged (as before)

Claude answers only from that material and cites dates, so a question like "Have there been any regulatory issues?" can now draw on a report from two months ago.

---

## 2. Before you start

- [ ] Your program is at the latest version of `market-agent-frontend.md` (with charts), and `pytest -v` shows `81 passed, 1 skipped`
- [ ] You can create a free Voyage AI account (next step)

**Files in this guide:**

| File | Status |
|---|---|
| `search_index.py` | **New:** passages, keyword and meaning search, the index |
| `tests/test_search.py` | **New:** 25 offline tests |
| `ask.py`, `run_brief.py`, `api.py` | **Changed** (replace the frontend guide's versions) |
| `requirements.txt` | **Changed:** adds `voyageai` |
| `frontend/src/components/SearchPanel.jsx` | **New:** the search box |
| `frontend/src/api.js`, `frontend/src/components/PreviousDaysTab.jsx`, `frontend/src/styles.css` | **Changed** |

Everything else stays as it is.

---

## 3. Step 1: Get a Voyage AI key

1. Create an account at [dash.voyageai.com](https://dash.voyageai.com).
2. Create an API key and copy it.
3. Optional: add a payment method. Voyage's standard rate limits apply once one is added. The free token allowance (section 13) easily covers this project either way.

---

## 4. Step 2: Install and set the key

Replace `requirements.txt` with the version in the [appendix](#requirementstxt), then install:

```bash
pip install -r requirements.txt
```

Set the key wherever the API and scheduled runs run, the same way as `ANTHROPIC_API_KEY`:

```bash
export VOYAGE_API_KEY=pa-...                 # macOS / Linux (add to ~/.zshrc or ~/.bashrc to keep it)
setx VOYAGE_API_KEY "pa-..."                 # Windows (then open a new terminal)
```

For cron, add `VOYAGE_API_KEY=pa-...` to the crontab next to `ANTHROPIC_API_KEY` (main guide, section 8).

Without the key, everything still works with keyword search only. You can add the key later and the index fills in its embeddings automatically.

---

## 5. Step 3: Add the search index

Create `search_index.py` in `market-agent/` with the code from the [appendix](#search_indexpy).

| Part | What it does |
|---|---|
| `chunk_report()` | Splits a report into passages: an overview, plus one per flagged ticker with its news headlines |
| `sync()` | Brings the index up to date: indexes new reports, re-indexes changed ones (a newer intraday update, or a day being finalized), removes deleted ones, then embeds anything without a vector |
| `embed()` | The one call to Voyage AI: `input_type="document"` for passages, `"query"` for searches |
| `search()` | Runs both searches, blends them, and returns the best passages with what they matched by |
| Command line | `sync`, `rebuild`, `status`, `search` (section 8) |

---

## 6. Step 4: Update Ask, runs and the API

Replace these three files with the versions in the appendix:

- **[`ask.py`](#askpy):** adds the retrieval step, `find_passages()`, and gathers the material in a background thread so a search doesn't hold up the server.
- **[`run_brief.py`](#run_briefpy):** after saving, updates the index. If that fails, it adds a warning line to the run's progress instead of failing the run.
- **[`api.py`](#apipy):** adds `GET /api/search` and `GET /api/search/status`, and updates the index in the background when it starts and whenever a report is saved.

**The API now writes one file:** `search.db`, the index. It still never writes `reports.db`. Report endpoints use a read-only connection exactly as before.

---

## 7. Step 5: Add the search box

In `frontend/src/`:

- **Add** [`components/SearchPanel.jsx`](#frontendsrccomponentssearchpaneljsx): the search box, example searches, results grouped by day, highlighted words, and "matched by" labels
- **Replace** [`components/PreviousDaysTab.jsx`](#frontendsrccomponentspreviousdaystabjsx), which puts the search box above the list of days; [`api.js`](#frontendsrcapijs), which adds `searchReports()`; and [`styles.css`](#frontendsrcstylescss), which adds the search styles

If you serve the built app from the API, run `npm run build` again afterwards.

Add the index to `.gitignore` (it's rebuilt from your reports, so there's no need to commit it):

```
search.db
search.db-wal
search.db-shm
```

---

## 8. Step 6: Build the index and try it

```bash
python search_index.py rebuild      # index every report you have (and embed them, if the key is set)
python search_index.py status
```

`status` shows something like:

```json
{
  "reports_total": 44,
  "reports_indexed": 44,
  "passages": 73,
  "passages_embedded": 73,
  "model": "voyage-4",
  "meaning_search": true,
  "index": ".../market-agent/search.db"
}
```

Try a search from the terminal:

```bash
python search_index.py search "analyst downgrade"
```

```
2026-10-01  NVDA: +4.20% (z-score 3.1, volume 2.5x normal) matched by keywords + meaning
```

Then restart the API (`uvicorn api:app --port 8000`), open the app, and go to the **Previous days** tab. The search box is at the top.

---

## 9. Test it

### 9.1 Automated tests

Create `tests/test_search.py` with the code from the [appendix](#teststest_searchpy), then run:

```bash
pytest -v
```

**Expected result:** `106 passed, 1 skipped` (81 from before, plus 25 new). No Voyage key or internet is needed. Voyage is replaced by a small stand-in that maps phrases to topics ("downgrade", "rating cut" and "lowered its rating" are all the same topic), so meaning-based matches behave realistically.

| Test | Proves that |
|---|---|
| `test_reports_are_split_into_passages` | Reports become an overview plus one passage per flagged ticker, each carrying its date and news headlines, with link addresses removed |
| `test_link_addresses_are_not_searchable` | Keyword matches are always visible text (so they can be highlighted) |
| `test_sync_indexes_new_changed_and_removed_reports` | New reports are indexed, a newer intraday update replaces the old text, and a removed report disappears from search |
| `test_reports_database_is_only_read` | Indexing and searching leave `reports.db` byte-for-byte unchanged, and the index sits next to it |
| `test_embeddings_are_made_in_batches_and_reused` | Passages are sent to Voyage in batches as "document"s, never sent twice, and re-embedded only if you change model |
| `test_without_a_key_nothing_is_sent_to_voyage` | With no key, nothing leaves your computer and keyword search still works |
| `test_keyword_search_matches_word_variations` | "downgraded" finds "downgrade"; results show the passage itself |
| `test_search_filters_by_ticker_and_dates` | Ticker and date filters work |
| `test_search_text_is_never_read_as_search_syntax` (4 cases) | Quotes, brackets, `OR`, `*` and the like can't break a search |
| `test_meaning_search_finds_passages_without_the_same_words` | "rating cut" finds the downgrade passage by meaning alone, and queries are sent as "query" |
| `test_matches_on_both_keywords_and_meaning_rank_first` | Passages matching both ways rank highest |
| `test_loosely_related_passages_are_left_out` | Only clearly relevant meaning matches are shown, and lowering the cutoff lets partial matches in |
| `test_search_falls_back_to_keywords_if_voyage_fails` | If Voyage is unreachable, you get keyword results and a note saying so |
| `test_api_search_returns_passages_including_brand_new_reports` | `/api/search` works, and a report saved a moment ago is already searchable |
| `test_api_search_rejects_bad_requests` (6 cases) | Empty or too-long searches, bad dates or tickers, and bad limits get a 400 |
| `test_ask_retrieves_passages_from_older_reports` | Ask brings in a relevant passage from a report older than the recent 10 |
| `test_runs_keep_the_search_index_current` | A run updates the index; if updating fails, the report is still saved and a warning is shown |

**Checking that the tests catch real problems.** Each of these was broken on purpose, and a test failed every time: Ask ignoring retrieved passages, no word-variation matching, removed reports left in the index, and meaning search switched off.

### 9.2 What was also tested in a real browser

Using the test environment (`market-agent-test-enviro.md`) with two months of sample reports, everything below worked in Chromium with no browser errors. The test environment uses a topic-based stand-in for Voyage, not the real service.

1. The Previous days tab shows the search box with example searches.
2. "earnings" finds all five earnings days. The reports say "quarterly results", so this works through meaning.
3. "quarterly" matches by keyword, and the word is highlighted in each passage.
4. "profit", a word no report uses, still finds the earnings passages, all matched by meaning.
5. Clicking a result opens that day's report below and scrolls to it.
6. A search with no matches says so, and Clear resets the box.
7. Pressing Enter searches. Results for the latest day link to the Today tab.
8. Ask's (offline) answer lists the passages it retrieved.
9. A report saved by another program is searchable straight away.
10. At phone width there's no sideways scrolling, and dark mode renders correctly.

The chart and whole-app browser checks from earlier guides were rerun on this version and still pass.

An early version of the browser test caught two real issues, both now fixed:

- **Link addresses were being matched.** "earnings" matched the word inside a link's URL, which wasn't visible text. Link addresses are no longer indexed.
- **Loosely related passages came through.** Similar-sounding passages slipped in, because every brief uses the same template. Meaning matches now have to be close to the best one.

### 9.3 Manual checks with real Voyage

These are the parts that can only be checked with your key:

- [ ] `python search_index.py rebuild` finishes, and `status` shows `passages_embedded` equal to `passages` and `"meaning_search": true`
- [ ] In the app, the search box says **By meaning and keywords**
- [ ] A search in different words from the reports, such as "rating cut" when the reports say "downgrade", finds the right passages, labelled "matched by meaning"
- [ ] Unrelated passages don't crowd the results. If they do, raise `MEANING_CUTOFF`; if relevant ones are missing, lower it (section 11)
- [ ] An Ask question about something older than your 10 most recent reports gets an answer citing the older date
- [ ] After a scheduled run, `status` shows the new report indexed and embedded

---

## 10. Using search and Ask

**The search box (Previous days tab)**

- Type a few words, or click an example, then press **Search** or Enter.
- Results are grouped by day, best match first. Each passage shows the ticker (or "Overview") and how it matched:
  - **matched by keywords:** your words appear (highlighted)
  - **matched by meaning:** about the same thing in other words
  - **matched by keywords and meaning:** the strongest matches
- Click a day to open its report below (or on the Today tab, for the latest day).
- The top right says **By meaning and keywords**, or **By keywords** if meaning search is off.

**Good searches:** topics ("guidance cut", "regulatory", "product launch"), events ("earnings miss", "market sell-off"), tickers with a topic ("NVDA downgrade"), or "no clear catalyst" to find unexplained moves.

**Ask** works as before; answers just reach further back. Questions that benefit most:

- "Have there been any regulatory issues this quarter?"
- "When did AMZN last report earnings, and how did it move?"
- "Which tickers moved on analyst rating changes?"

The line under each answer shows how many reports it drew on, including any older ones found by search.

---

## 11. Settings and tuning

At the top of `search_index.py`:

| Setting | Default | Effect |
|---|---|---|
| `EMBED_MODEL` | `voyage-4` (or the `VOYAGE_MODEL` environment variable) | Which Voyage model makes the vectors. `voyage-finance-2` is tuned for finance; `voyage-4-large` is the highest quality; `voyage-4-lite` is cheapest |
| `MEANING_CUTOFF` | `0.85` | Meaning matches must be at least 85% as similar as the best one. Lower it to see more loosely related passages, raise it for fewer |
| `MIN_SIMILARITY` | `0.25` | Meaning matches weaker than this never show |
| `RRF_K` | `60` | How keyword and meaning rankings are blended (the standard value; rarely worth changing) |
| `EMBED_BATCH` | `128` | Passages per Voyage request |

In `ask.py`: `PASSAGES` (default 8) is how many retrieved passages each question gets.

**Changing the model:** set `VOYAGE_MODEL` (or edit `EMBED_MODEL`) and restart. The next update re-embeds every passage with the new model automatically, since vectors from different models can't be compared. That's a one-off cost of a few hundred thousand tokens a year at most.

**Tuning with your own data:** the test environment with `--live-embeddings` runs real Voyage over two months of sample reports, a safe place to try `MEANING_CUTOFF` values.

---

## 12. API additions reference

### `GET /api/search`

| Parameter | Required | Values |
|---|---|---|
| `q` | yes | What to search for (up to 500 characters) |
| `limit` | no | 1–50 passages (default 12) |
| `ticker` | no | Only passages about this ticker |
| `since`, `until` | no | `YYYY-MM-DD`: only reports in this range |

```json
{
  "query": "rating cut",
  "mode": "hybrid",
  "note": null,
  "terms": ["rating", "cut"],
  "results": [
    {
      "session_date": "2026-10-01",
      "status": "final",
      "ticker": "NVDA",
      "heading": "NVDA: +4.20% (z-score 3.1, volume 2.5x normal)",
      "text": "### NVDA: +4.20% ...\n- **Likely why:** An analyst downgrade weighed on the shares. Sample Wire\nNews: ...",
      "score": 0.01639,
      "matched_by": ["meaning"]
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `mode` | `hybrid` (keywords and meaning) or `keyword` (meaning search off or unavailable) |
| `note` | Set when meaning search was expected but couldn't run (for example, Voyage unreachable) |
| `terms` | The words searched for, which the app highlights |
| `results[].text` | The passage, in markdown, without its title line |
| `results[].matched_by` | `keywords`, `meaning`, or both |
| `results[].score` | The blended rank score (higher is better; only useful for ordering) |

Errors: `400` with `{"error": "..."}` for an empty or too-long `q`, or a bad `ticker`, date or `limit`.

### `GET /api/search/status`

```json
{"reports_total": 44, "reports_indexed": 44, "passages": 73, "passages_embedded": 73,
 "model": "voyage-4", "meaning_search": true, "index": ".../search.db"}
```

---

## 13. Costs and privacy

**Costs.** At the time of writing, Voyage's pricing page lists `voyage-4` at $0.06 per million tokens, with the first 200 million tokens free for every account (50 million for `voyage-finance-2`). Check [Voyage's pricing page](https://docs.voyageai.com/docs/pricing) for current figures. For scale:

| | Tokens (approx.) |
|---|---|
| One report (about 2 passages) | 300–1,000 |
| A year of reports | under 250,000 |
| One search or Ask question | under 50 |

So in practice this stays within the free allowance for a long time. Charts, keyword search and reading reports cost nothing.

**Privacy.** With a key set, report passages (including the news headlines the agent read) and your search and Ask text are sent to Voyage AI to make vectors. Without a key, nothing leaves your computer, and search works by keywords only. To stop sending data, remove `VOYAGE_API_KEY` and restart; existing vectors stay in `search.db` but are no longer used.

---

## 14. Maintenance

| Task | How |
|---|---|
| See what's indexed | `python search_index.py status` |
| Index anything missed | `python search_index.py sync` (also happens automatically) |
| Start the index again | `python search_index.py rebuild`. Safe at any time: your reports aren't touched |
| Back it up | No need. It's rebuilt from `reports.db`, which is what you back up (database guide, section 12) |
| Change the search layout | Edit `chunk_report()`, then `python search_index.py rebuild` |
| Remove search entirely | Delete `search.db` and restore the frontend guide's versions of the changed files |

After the database guide's procedure for removing a final report, the index drops that report on its next update.

---

## 15. Troubleshooting

| Problem | Cause and fix |
|---|---|
| The search box says **By keywords** | `VOYAGE_API_KEY` isn't set where the API runs. Set it and restart the API. Embeddings fill in automatically |
| **Meaning-based search is unavailable right now (…)** | Voyage couldn't be reached (network, rate limit, or an invalid key). You still get keyword results. The message gives the reason |
| **The search index is still being embedded** | New passages haven't been embedded yet. Wait a few seconds, or run `python search_index.py sync` |
| `ModuleNotFoundError: voyageai` | Run `pip install -r requirements.txt` in the virtual environment |
| `no such module: fts5` | Your Python's SQLite lacks full-text search (rare; python.org and Homebrew builds include it). Install Python from python.org |
| A new report doesn't show up in search | Check `python search_index.py status`. If `reports_indexed` is behind, run `python search_index.py sync` and look at the error it prints |
| A run shows **Saved, but the search index wasn't updated** | The report is safe. The index will catch up on the next run or API start, or run `python search_index.py sync` |
| Results include passages that seem unrelated | Raise `MEANING_CUTOFF` (for example to 0.9). They'll be labelled "matched by meaning" |
| A relevant passage is missing | Try other words, or lower `MEANING_CUTOFF` (for example to 0.75) |
| `database is locked` from search | Two updates at once. They queue for up to 10 seconds; retry |
| Ask's answers don't mention older reports | Check `status` shows the index is complete. Ask only uses passages that relate to the question, so try asking about a specific topic |

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
voyageai
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

### ask.py

Replaces the version in the frontend guide.

```python
"""Answer questions about saved reports with Claude, using retrieval (RAG).

For each question it gathers, within a size limit:
1. Figures across days for any watchlist ticker named in the question.
2. The passages from any report that best match the question, found by
   search_index.py (keywords plus meaning), so older reports are reachable.
3. The 10 most recent reports in full, plus recent reports where a named ticker was flagged.
Claude is told to answer from that material alone and to cite report dates.
"""

import asyncio
import re
from contextlib import closing

from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, StreamEvent, query

import reports_db
import search_index

SYSTEM_PROMPT = """You answer questions about the user's saved stock watchlist reports.

Rules:
- Use only the reports, passages and figures provided. If they don't contain the answer, say so plainly.
- Cite the report date for every claim, like (2026-11-05). Passages carry the date of the report they came from.
- Every number must come from the provided material. Never estimate or calculate new figures.
- Intraday reports describe moves "so far" that day, and those figures may have changed since.
- This is research, not investment advice. Never recommend buying or selling.
- Keep answers short: a few sentences or a short list, in markdown."""

MAX_QUESTION_CHARS = 500
RECENT_REPORTS = 10              # always included in full
FLAGGED_REPORTS_PER_TICKER = 10  # recent reports for each ticker named in the question
PASSAGES = 8                     # best-matching passages from any report (the retrieval step)
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
                 "date | status | category | return % | z-score | volume vs normal"]
        lines += [f"{h['session_date']} | {h['status']} | {h['category']} | {h['return_1d_pct']} | "
                  f"{h['return_zscore']} | {h['volume_vs_avg']}"
                  for h in reports_db.ticker_history(conn, ticker, limit=60)]
        add("\n".join(lines))

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

### run_brief.py

Replaces the version in the frontend guide.

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

    # Keep the search index current. The report is already saved, so a problem here isn't fatal:
    # the index catches up next time (or run `python search_index.py sync`).
    try:
        await asyncio.to_thread(search_index.sync)
    except Exception as e:
        emit({"type": "warning", "message": f"Saved, but the search index wasn't updated ({e}). It will catch up later."})
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

Replaces the version in the frontend guide.

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
    GET  /api/events            live updates (Server-Sent Events)
    GET  /api/runs/current      the on-demand run in progress, or the last one
    POST /api/runs              write a fresh report now
    POST /api/ask               ask Claude about saved reports (streams the answer)

Reports are only read here, through a read-only database connection. The one
thing that writes reports is a run, through run_brief.py's normal storage rules.
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

### tests/test_search.py

```python
"""Offline tests for search and retrieval (RAG): search_index.py, /api/search, and how
Ask and runs use it. Voyage AI is replaced by a small stand-in that maps phrases to topics.

Run from the project folder:
    pytest -v tests/test_search.py
"""

import asyncio
import hashlib
import json
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
import search_index  # noqa: E402
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# A stand-in for Voyage: each vector says which topics a text mentions, in any wording
TOPICS = {
    "rating down": ["downgrade", "cut its rating", "lowered its rating", "rating cut"],
    "earnings": ["quarterly results", "earnings", "profit"],
    "regulation": ["regulatory", "regulator", "investigation", "probe"],
}


def fake_embed(texts, input_type):
    fake_embed.calls.append((len(texts), input_type))
    return [[float(sum(p in t.lower() for p in phrases)) for phrases in TOPICS.values()] + [0.1] for t in texts]


def brief(day, ticker, why, status="final"):
    title = f"Watchlist brief: {day}" if status == "final" else f"Intraday update: {day} 12:30 ET"
    return title, f"""# {title}

## Notable moves

### {ticker}: +4.20% (z-score 3.1, volume 2.5x normal)
- **What happened:** {ticker} moved +4.20% on heavy volume.
- **Likely why:** {why} [Sample Wire](https://news.example.com/{day})

## Quiet

AAPL (+0.10%)
"""


def save(day, ticker, why, status="final"):
    title, body = brief(day, ticker, why, status)
    scan = {"flagged": [{"ticker": ticker, "last_close": 100.0, "return_1d_pct": 4.2, "return_zscore": 3.1,
                         "volume_vs_avg": 2.5}], "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.1}], "errors": []}
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=day, status=status, title=title, body_md=body,
                                      as_of=day if status == "final" else f"{day} 12:30 ET", scan=scan,
                                      sources=[{"ticker": ticker, "title": f"{ticker} headline", "publisher": "Sample Wire"}])


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    """A temporary database with four reports; no Voyage key unless a test adds one."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.delenv("SEARCH_DB", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    fake_embed.calls = []
    monkeypatch.setattr(search_index, "embed", fake_embed)
    save("2026-10-01", "NVDA", "An analyst downgrade weighed on the shares.")
    save("2026-10-02", "AAPL", "Quarterly results beat expectations.")
    save("2026-10-05", "JPM", "Regulatory concerns were reported.")
    save("2026-10-06", "MSFT", "No clear catalyst found.", status="intraday")


@pytest.fixture
def voyage(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")


def search(q, **filters):
    return search_index.search(q, **filters)


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------

def test_reports_are_split_into_passages():
    with closing(reports_db.connect(readonly=True)) as conn:
        passages = search_index.chunk_report(reports_db.get_report(conn, "2026-10-01"))

    assert [p["ticker"] for p in passages] == [None, "NVDA"]  # an overview, then one per flagged ticker
    overview, nvda = passages
    assert overview["heading"] == "Overview" and "AAPL (+0.10%)" in overview["text"]
    assert nvda["heading"].startswith("NVDA: +4.20%")
    assert nvda["text"].startswith("Watchlist brief: 2026-10-01 (final)\n")  # every passage carries its date
    assert "News: NVDA headline (Sample Wire)" in nvda["text"]
    assert "[Sample Wire](" not in nvda["text"] and "Sample Wire" in nvda["text"]  # link text kept, URL dropped


def test_link_addresses_are_not_searchable():
    """A keyword match should always be something a reader can see (and the app can highlight)."""
    search_index.sync()
    assert search("news.example.com")["results"] == []


def test_sync_indexes_new_changed_and_removed_reports():
    assert search_index.sync()["reports_indexed"] == 4
    assert search_index.sync()["reports_indexed"] == 0  # nothing changed

    title, body = brief("2026-10-06", "MSFT", "A regulator opened an investigation.", "intraday")
    with closing(reports_db.connect()) as conn:  # a newer intraday update for the same day
        reports_db.save_report(conn, session_date="2026-10-06", status="intraday", title=title, body_md=body,
                               as_of="2026-10-06 13:00 ET", scan={})
    assert search_index.sync()["reports_indexed"] == 1
    assert search("investigation")["results"][0]["session_date"] == "2026-10-06"
    assert search("catalyst")["results"] == []  # the old version's text is gone

    with closing(reports_db.connect()) as conn:  # the documented procedure for removing a final report
        for trigger in ("final_reports_no_delete", "report_tickers_final_no_delete", "report_sources_final_no_delete"):
            conn.execute(f"DROP TRIGGER {trigger}")
        for table in ("report_sources", "report_tickers", "reports"):
            conn.execute(f"DELETE FROM {table} WHERE session_date = '2026-10-01'")
    assert search_index.sync()["reports_removed"] == 1
    assert search("downgrade")["results"] == []


def test_reports_database_is_only_read():
    before = hashlib.sha256(Path(reports_db.DB_PATH).read_bytes()).hexdigest()
    search_index.sync()
    search("downgrade")
    assert hashlib.sha256(Path(reports_db.DB_PATH).read_bytes()).hexdigest() == before
    assert search_index.index_path() == Path(reports_db.DB_PATH).with_name("search.db")


def test_embeddings_are_made_in_batches_and_reused(voyage, monkeypatch):
    monkeypatch.setattr(search_index, "EMBED_BATCH", 3)
    assert search_index.sync()["passages_embedded"] == 8  # 4 reports x (overview + 1 ticker)
    assert all(size <= 3 and kind == "document" for size, kind in fake_embed.calls)

    fake_embed.calls = []
    search_index.sync()
    assert fake_embed.calls == []  # already embedded: nothing sent again

    monkeypatch.setattr(search_index, "EMBED_MODEL", "voyage-finance-2")
    assert search_index.sync()["passages_embedded"] == 8  # a new model re-embeds everything
    assert search_index.status()["passages_embedded"] == 8


def test_without_a_key_nothing_is_sent_to_voyage():
    search_index.sync()
    result = search("downgrade")
    assert fake_embed.calls == []
    assert result["mode"] == "keyword" and result["results"]
    assert search_index.status()["meaning_search"] is False


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def test_keyword_search_matches_word_variations():
    search_index.sync()
    result = search("downgraded")  # stemming: matches "downgrade"
    top = result["results"][0]
    assert (top["session_date"], top["ticker"], top["matched_by"]) == ("2026-10-01", "NVDA", ["keywords"])
    assert top["text"].startswith("### NVDA")  # the passage itself, without the title line
    assert result["terms"] == ["downgraded"]


def test_search_filters_by_ticker_and_dates():
    search_index.sync()
    assert {r["session_date"] for r in search("shares OR results OR concerns")["results"]} >= {"2026-10-01", "2026-10-02", "2026-10-05"}
    assert [r["ticker"] for r in search("results", ticker="aapl")["results"]] == ["AAPL"]
    assert search("downgrade", since="2026-10-02")["results"] == []
    assert {r["session_date"] for r in search("AAPL", until="2026-10-02")["results"]} == {"2026-10-01", "2026-10-02"}


@pytest.mark.parametrize("query", ['NVDA\'s "earnings" (Q3) OR * -', "AND", "?!", "NEAR(a b)"])
def test_search_text_is_never_read_as_search_syntax(query):
    search_index.sync()
    search(query)  # no error


def test_meaning_search_finds_passages_without_the_same_words(voyage):
    search_index.sync()
    result = search("rating cut")  # shares no words with "An analyst downgrade weighed on the shares"
    top = result["results"][0]
    assert result["mode"] == "hybrid"
    assert (top["session_date"], top["matched_by"]) == ("2026-10-01", ["meaning"])  # no shared keywords
    assert fake_embed.calls[-1] == (1, "query")


def test_matches_on_both_keywords_and_meaning_rank_first(voyage):
    search_index.sync()
    top = search("regulatory probe")["results"][0]
    assert (top["ticker"], sorted(top["matched_by"])) == ("JPM", ["keywords", "meaning"])


def test_loosely_related_passages_are_left_out(voyage, monkeypatch):
    save("2026-10-07", "AMZN", "Earnings beat, though a regulator is watching.")  # only partly about regulation
    search_index.sync()

    def days_for(query):
        return [r["session_date"] for r in search(query)["results"] if "meaning" in r["matched_by"]]

    assert days_for("probe") == ["2026-10-05"]  # the clearly relevant passage only
    monkeypatch.setattr(search_index, "MEANING_CUTOFF", 0.5)
    assert set(days_for("probe")) == {"2026-10-05", "2026-10-07"}  # a lower cutoff lets the partial match in


def test_search_falls_back_to_keywords_if_voyage_fails(voyage, monkeypatch):
    search_index.sync()

    def unreachable(texts, input_type):
        raise ConnectionError("Voyage unreachable")

    monkeypatch.setattr(search_index, "embed", unreachable)
    result = search("downgrade")
    assert result["mode"] == "keyword" and "unavailable" in result["note"]
    assert result["results"][0]["session_date"] == "2026-10-01"


# ---------------------------------------------------------------------------
# The API, Ask and runs
# ---------------------------------------------------------------------------

def test_api_search_returns_passages_including_brand_new_reports():
    client = TestClient(api.app)
    data = client.get("/api/search?q=downgrade").json()
    assert data["results"][0]["session_date"] == "2026-10-01" and data["mode"] == "keyword"

    save("2026-10-07", "AMZN", "Reports of a large contract win.")
    assert client.get("/api/search?q=contract").json()["results"][0]["session_date"] == "2026-10-07"
    status = client.get("/api/search/status").json()
    assert status["reports_indexed"] == status["reports_total"] == 5


@pytest.mark.parametrize("query", ["", "?q=", "?q=x&since=yesterday", "?q=x&ticker=not%20one", "?q=x&limit=0",
                                   "?q=" + "x" * 501])
def test_api_search_rejects_bad_requests(query):
    response = TestClient(api.app).get("/api/search" + query)
    assert response.status_code == 400 and "error" in response.json()


def test_ask_retrieves_passages_from_older_reports():
    for day in range(8, 20):  # twelve newer reports push 1-5 October out of the "recent 10"
        save(f"2026-10-{day:02d}", "MSFT", "No clear catalyst found.")

    context, used = ask.gather("Were there any regulatory issues?")

    assert "2026-10-05" in used
    assert "## Passage from the report of 2026-10-05 (final): JPM" in context
    assert "Regulatory concerns were reported." in context


def test_runs_keep_the_search_index_current(monkeypatch):
    scan = {"session": {"status": "complete", "as_of": "2026-10-07"},
            "flagged": [{"ticker": "AMZN", "last_close": 180.0, "return_1d_pct": 3.0, "return_zscore": 2.4}],
            "quiet": [], "errors": []}
    title, body = brief("2026-10-07", "AMZN", "Reports of a large contract win.")
    messages = [AssistantMessage(content=[ToolUseBlock(id="t", name="mcp__market__flag_events", input={})], model="m"),
                UserMessage(content=[ToolResultBlock(tool_use_id="t", content=[{"type": "text", "text": json.dumps(scan)}])]),
                ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
                              session_id="s", total_cost_usd=0.03, result=body)]

    async def fake_query(*, prompt, options):
        for m in messages:
            yield m

    monkeypatch.setattr(run_brief, "market_session", lambda: scan["session"])
    monkeypatch.setattr(run_brief, "query", fake_query)
    events = []
    asyncio.run(run_brief.run_once(events.append))
    assert search("contract")["results"][0]["session_date"] == "2026-10-07"

    def broken_sync(**kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(search_index, "sync", broken_sync)
    monkeypatch.setattr(run_brief, "market_session", lambda: {"status": "in_progress", "as_of": "2026-10-08 11:00 ET"})
    scan["session"] = {"status": "in_progress", "as_of": "2026-10-08 11:00 ET"}
    messages[1] = UserMessage(content=[ToolResultBlock(tool_use_id="t", content=[{"type": "text", "text": json.dumps(scan)}])])
    events = []
    asyncio.run(run_brief.run_once(events.append))
    assert events[-1]["type"] == "warning" and "disk full" in events[-1]["message"]
    with closing(reports_db.connect(readonly=True)) as conn:
        assert reports_db.get_report(conn, "2026-10-08") is not None  # the report was still saved
```

### frontend/src/api.js

Replaces the version in the frontend guide.

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

export const getPrices = (ticker, range) =>
  request(`/api/tickers/${encodeURIComponent(ticker)}/prices?range=${range}`).then((body) => body.prices)

export const searchReports = (q, limit = 12) =>
  request(`/api/search?q=${encodeURIComponent(q)}&limit=${limit}`)

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

### frontend/src/components/SearchPanel.jsx

```jsx
import { useState } from 'react'
import { searchReports } from '../api'
import { formatDate } from '../format'
import { routes } from '../useRoute'
import StatusBadge from './StatusBadge'

const EXAMPLES = ['analyst downgrade', 'earnings', 'regulatory', 'no clear catalyst']

// A short plain-text preview of a markdown passage
const plain = (md) =>
  md
    .replace(/^#+\s*/gm, '')
    .replace(/\*\*/g, '')
    .replace(/\[([^\]]+)\]\([^)]*\)/g, '$1')
    .replace(/^- /gm, '')
    .trim()

// Marks the searched words by splitting the text, so no HTML is ever built from report text
function Highlight({ text, terms }) {
  const words = terms.filter((t) => t.length > 1).map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'))
  if (!words.length) return text
  return text.split(new RegExp(`\\b(${words.join('|')})`, 'gi')).map((part, i) => (i % 2 ? <mark key={i}>{part}</mark> : part))
}

// Search every saved report: by keywords, and by meaning when the API has a Voyage key.
// Results are grouped by day; clicking a day opens its report.
export default function SearchPanel({ latestDate }) {
  const [query, setQuery] = useState('')
  const [data, setData] = useState(null)
  const [error, setError] = useState(null)
  const [busy, setBusy] = useState(false)

  const run = async (q) => {
    if (!q.trim()) return
    setBusy(true)
    setError(null)
    try {
      setData(await searchReports(q))
    } catch (e) {
      setError(e.message)
    } finally {
      setBusy(false)
    }
  }

  const clear = () => {
    setQuery('')
    setData(null)
    setError(null)
  }

  // An older day opens in the report viewer below; bring it into view
  const openDay = (day) => {
    if (day !== latestDate) {
      setTimeout(() => document.getElementById('day-report')?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 50)
    }
  }

  const days = []
  for (const r of data?.results || []) {
    let day = days.find((d) => d.date === r.session_date)
    if (!day) days.push((day = { date: r.session_date, status: r.status, passages: [] }))
    day.passages.push(r)
  }

  return (
    <section className="panel search" aria-label="Search reports">
      <div className="section-head">
        <h2>Search reports</h2>
        {data && <span className="muted small">{data.mode === 'hybrid' ? 'By meaning and keywords' : 'By keywords'}</span>}
      </div>

      <form
        className="search-row"
        role="search"
        onSubmit={(e) => {
          e.preventDefault()
          run(query)
        }}
      >
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="e.g. analyst downgrade, earnings, regulatory"
          aria-label="Search all reports"
          maxLength={500}
        />
        <button className="primary" disabled={busy || !query.trim()}>{busy ? 'Searching…' : 'Search'}</button>
        {data && <button type="button" className="link" onClick={clear}>Clear</button>}
      </form>

      {!data && (
        <div className="examples">
          {EXAMPLES.map((q) => (
            <button
              key={q}
              type="button"
              className="chip"
              onClick={() => {
                setQuery(q)
                run(q)
              }}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {error && <p className="error">{error}</p>}
      {data?.note && <p className="muted small">{data.note}</p>}
      {data?.mode === 'keyword' && !data.note && (
        <p className="muted small">Searching by keywords only: meaning-based search is off because the API has no Voyage API key.</p>
      )}

      {data && (
        <div className={busy ? 'refreshing' : ''} aria-live="polite">
          <p className="muted small">
            {data.results.length === 0
              ? 'No matching passages.'
              : `${data.results.length} passage${data.results.length === 1 ? '' : 's'} from ${days.length} day${days.length === 1 ? '' : 's'}, best match first`}
          </p>
          <ol className="search-results">
            {days.map((day) => (
              <li key={day.date}>
                <a
                  className="result-day"
                  href={day.date === latestDate ? routes.today : routes.previous(day.date)}
                  onClick={() => openDay(day.date)}
                >
                  <span className="day-date">{formatDate(day.date)}</span>
                  <StatusBadge status={day.status} current={day.date === latestDate} />
                </a>
                {day.passages.map((p, i) => (
                  <div key={i} className="passage">
                    <div className="passage-head">
                      <strong>{p.ticker || 'Overview'}</strong>
                      <span className="muted small">matched by {p.matched_by.join(' and ')}</span>
                    </div>
                    <p className="passage-text">
                      <Highlight text={plain(p.text)} terms={data.terms} />
                    </p>
                  </div>
                ))}
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
```

### frontend/src/components/PreviousDaysTab.jsx

Replaces the version in the frontend guide.

```jsx
import { useEffect, useRef, useState } from 'react'
import { getReport, listReports } from '../api'
import { formatDate, formatMonth } from '../format'
import { routes } from '../useRoute'
import ReportView from './ReportView'
import SearchPanel from './SearchPanel'
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
    <>
      <SearchPanel latestDate={latestDate} />
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
            <div className="day-report" id="day-report" ref={reportRef}>
              {report ? <ReportView report={report} /> : <p className="muted">Loading…</p>}
            </div>
          </div>
        )}
      </section>
    </>
  )
}
```

### frontend/src/styles.css

Replaces the version in the frontend guide.

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
