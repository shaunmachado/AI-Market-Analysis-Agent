# Market Analysis Agent: Project Report

Date: 2026-11-07
Location: `C:\shaun\AI-Market-Analysis-Agent`

## 1. What the project is

A Python agent that writes a short research brief on a stock watchlist, stores every brief in a database, and shows them in a React web app. A person can read today's report, browse earlier days, view price charts, search the whole history, run an update on demand, and ask Claude questions about the saved reports.

**Design rule: code does the numbers, Claude does the reasoning.** The model never estimates or calculates figures. All numbers come from tool results, and the system prompt forbids anything else. Output is research only, never buy/sell advice.

Watchlist (`watchlist.txt`): AAPL, MSFT, NVDA, AMZN, JPM.

## 2. Architecture

```
run_brief.py  (agent, Claude Agent SDK)
   │  talks over MCP to
   ▼
market_tools.py  (MCP server: flag_events, compute_moves, get_news; data from yfinance)
   │
   ▼  result saved by
reports_db.py ──▶ reports.db (SQLite)
                     │   read-only                  ┌──▶ search_index.py ──▶ search.db (FTS5 + Voyage vectors)
                     ▼                              │
                  api.py  (Starlette, JSON + live events) ──▶ ask.py (Claude answers using retrieved passages)
                     │
                     ▼
             frontend/ (React + Vite): Today, Previous days, charts, search, Ask, Run now
```

## 3. Components

| File | Role |
|---|---|
| `analyst_prompt.md` | The agent's instructions: call `flag_events` first, `get_news` for each flagged ticker, then write the brief in a fixed markdown format. Different wording and title for market open vs. closed |
| `market_tools.py` | MCP server with three tools. Detects whether the US market is open (NYSE calendar, SPY as the reference, New York time). Closed: the last finished session is measured against the previous 3 months. Open: today's move so far is compared with the same time of day in recent sessions, using about 20 sessions of 5-minute data |
| `run_brief.py` | Runs the agent once and saves the result. Loads `.env`. Passes `MARKET_AGENT_ANTHROPIC_KEY` explicitly and drops any stray `ANTHROPIC_API_KEY`, so the subscription login isn't overridden. Built-in tools are off (no shell or file access). Hard stops: 25 turns and $1.00 per run. Streams progress events. Updates the search index after saving |
| `reports_db.py` | SQLite storage with enforced rules (section 4). Tables: `reports`, `report_tickers`, `report_sources` |
| `prices.py` | Daily closing prices for charts (ranges 1mo, 3mo, 6mo, 1y) |
| `api.py` | Starlette API. Endpoints: health, reports (list, latest, by date), ticker history, ticker prices, search, search status, live events (Server-Sent Events), runs (start, current), ask. Serves `frontend/dist` if built. Reports are read through a read-only connection. Run-now has a cooldown (default 60 s), and Ask allows at most 2 concurrent questions |
| `ask.py` | Answers questions with Claude, using only supplied text, citing report dates, no tools, $0.25 cap per question. Streams the answer |
| `search_index.py` | Splits reports into passages, builds the keyword and meaning indexes, runs blended search (section 5) |
| `frontend/` | React 19 + Vite. Components: Today table, Previous days tab, price charts, search panel, Ask panel, run panel, live updates |
| `tests/` | `test_market_tools.py`, `test_reports_db.py`, `test_frontend_api.py`, `test_charts.py`, `test_search.py` |
| Guides | `market-agent-guide.md` (main), `-testing.md`, `-database.md`, `-frontend.md`, `-rag.md`, `-test-enviro.md` |

## 4. Storage rules

1. One report per trading day.
2. While the market is open, the day's report is `intraday`. Each run replaces it with fresher text, figures and sources, and the revision number goes up. An older update can't overwrite a newer one.
3. Once the session is over, the next run while the market is closed saves the day's `final` report.
4. Final reports are permanent. Database triggers refuse to change or delete a final report, including its tickers and sources.
5. If the final report already exists, `run_brief.py` stops before calling Claude, so the run costs nothing.

## 5. Search and RAG

- **Passages:** each report becomes an overview plus one passage per flagged ticker, with its news headlines. Link URLs are stripped so keyword matches are visible text.
- **Keywords:** SQLite FTS5 with stemming. Free and offline.
- **Meaning:** Voyage AI embeddings (default model `voyage-4`). Needs `VOYAGE_API_KEY`.
- **Blending:** reciprocal rank fusion. Meaning matches must be at least 85% as similar as the best match (`MEANING_CUTOFF`) and above 0.25 (`MIN_SIMILARITY`).
- **Index:** a separate file, `search.db`. It's rebuilt from `reports.db`, only reads it, and can be deleted at any time.
- **Kept current:** after each saved run, at API startup, by a background check every ~2 s, and before each search.
- **Used by:** the Previous days search box (`GET /api/search`) and Ask, which adds the 8 best-matching passages from any date to the 10 most recent reports. This is the RAG part.
- **Without a Voyage key:** keyword search only, and everything still works.

## 6. Configuration and secrets

`C:\shaun\AI-Market-Analysis-Agent\.env` (git-ignored):

| Variable | Purpose |
|---|---|
| `MARKET_AGENT_ANTHROPIC_KEY` | Claude key for the agent. Named this way on purpose so Claude Code never picks it up. Leave blank to use the Claude Code login |
| `VOYAGE_API_KEY` | Search by meaning. Blank means keyword search only |

Optional environment variables: `REPORTS_DB`, `SEARCH_DB`, `VOYAGE_MODEL`, `FRONTEND_ORIGINS`, `RUN_COOLDOWN_SECONDS`, `REPORT_POLL_SECONDS`.

## 7. Current state

| Item | State |
|---|---|
| Automated tests | 113 passed, 1 skipped (project). 18 passed (test environment) |
| Real data | `reports.db` holds 1 report. The older `briefs/` folder holds 3 markdown briefs from before the database existed |
| Voyage account | Key is set, but no payment method, so it is limited to 3 requests per minute |
| Git | Last commit `aa289a9` (reports database, API, React frontend). Many changes since then are uncommitted: charts, search/RAG, `ask.py`, `prices.py`, `search_index.py`, new tests, doc updates, `.mcp.json` |
| Test environment | `C:\shaun\market-agent-testenv`: 44 simulated reports (two months, 73 passages), simulated prices and news, no real spending by default. Search tested there with real Voyage on 2026-11-07 |

## 8. Test environment

`testenv.py` seeds a separate database of simulated reports and serves the real app and API over it at http://localhost:8100. It does not touch the real `reports.db`. Commands: `seed`, `status`, `build-frontend`, `serve`, `update`, `finalize`, `reset`. Options `--live-ask`, `--live-runs` and `--live-embeddings` switch on real Claude or Voyage. The frontend must be rebuilt with `build-frontend` after any frontend change, otherwise the served app is stale. This caused a missing search box earlier today.

## 9. RAG evaluation on the sample data

Real Voyage results:

- "profit" finds the "quarterly results beat expectations" passages, though no report uses that word.
- "regulatory probe" finds the MSFT regulatory passage.
- "stock fell after analyst lowered its view" finds the analyst-downgrade passages, matched by both keywords and meaning.

Issues:

1. **Short queries return nothing by meaning.** "rating cut" scored about 0.225, just under `MIN_SIMILARITY` (0.25). Lowering it to about 0.15–0.2 would fix this but admits looser matches, because every brief shares a template.
2. **Rate limit.** At 3 requests per minute, rapid searches fall back to keywords, with a note in the response. Adding a payment method fixes this, and the free token allowance still applies.
3. **Value.** Keyword search covers most of what the templated reports need. The meaning half helps when wording differs. The main benefit is Ask reaching beyond the 10 most recent reports, and that grows with history. Not yet tested: Ask with a real Claude call.

## 10. Known limitations

- yfinance is unofficial and can break or be rate-limited.
- News is headlines only: no SEC filings, earnings transcripts or analyst data.
- US market hours only.
- Intraday z-scores are rougher (about 20 sessions of data), and the first 30–60 minutes after the open are the noisiest.
- Intraday data can lag by a few minutes.
- SQLite and a single-process API suit one user. Hosting for many users would need a database like PostgreSQL and authentication.
- There is no login on the API. CORS is limited to localhost origins by default.

## 11. Cost controls

| Action | Cost control |
|---|---|
| Agent run | `max_budget_usd=1.00`, `max_turns=25` |
| Ask question | `max_budget_usd=0.25`, 500-character limit, context capped at 60,000 characters |
| Run now | Cooldown between runs, skipped entirely if the final report exists |
| Voyage | About 300–1,000 tokens per report. A year of reports is under 250,000 tokens, well inside the free allowance |

## 12. How to run

```
# Real app (backend + built frontend)
cd frontend && npm run build && cd ..
uvicorn api:app --port 8000          # http://localhost:8000

# Write a report now
python run_brief.py

# Search index
python search_index.py status | sync | rebuild | search "analyst downgrade"

# Tests
pytest -v

# Test environment (sample data, real Voyage)
cd C:\shaun\market-agent-testenv
set MARKET_AGENT_DIR=C:\shaun\AI-Market-Analysis-Agent
python testenv.py build-frontend
python testenv.py serve --live-embeddings      # http://localhost:8100
```

For the test environment with real Voyage, `VOYAGE_API_KEY` must be set in that terminal. It doesn't read the project's `.env` itself.

## 13. Suggested next steps

1. Add a payment method to the Voyage account (removes the 3 requests per minute limit).
2. Decide on `MIN_SIMILARITY` (lower to about 0.15–0.2 for short queries).
3. Test Ask end to end with a real Claude call, and confirm the search box in a browser.
4. Commit the current uncommitted work.
5. Schedule runs (morning and midday) so real history builds up, then judge search quality on real briefs.
6. Longer term, per the main guide's roadmap: paid or more reliable market data, earnings dates, SEC filings, and then RAG over filings and transcripts.
