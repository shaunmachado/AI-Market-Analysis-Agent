# Market Analyst Agent: Build & Run Guide

A Python agent that writes a morning brief on your stock watchlist. Code computes every number; Claude investigates the unusual moves and writes up what happened and why.

---

## Contents

1. [How it works](#1-how-it-works)
2. [Prerequisites](#2-prerequisites)
3. [Project files](#3-project-files)
4. [Setup](#4-setup)
5. [Test it](#5-test-it)
6. [Run the agent](#6-run-the-agent)
7. [Tune it for a week](#7-tune-it-for-a-week)
8. [Schedule it](#8-schedule-it)
9. [Customize and extend](#9-customize-and-extend)
10. [Costs and guardrails](#10-costs-and-guardrails)
11. [Troubleshooting](#11-troubleshooting)
12. [Known limitations](#12-known-limitations)
13. [Roadmap](#13-roadmap)
14. [Appendix: full source code](#appendix-full-source-code)

---

## 1. How it works

**Design rule: code does the numbers, the agent does the reasoning.** The model never estimates or calculates figures. It decides which tools to call, interprets what they return and writes the brief.

```
run_brief.py  (the agent, built on the Claude Agent SDK)
     │
     │  starts and connects over MCP
     ▼
market_tools.py  (MCP server, your code)
     ├── flag_events    scan the watchlist, return only unusual movers
     ├── compute_moves  detailed stats for one ticker
     └── get_news       recent headlines for one ticker
              │
              ▼
         yfinance  (free Yahoo Finance data)
```

**What happens on each run:**

1. `run_brief.py` starts `market_tools.py` as a background process and connects to it over MCP.
2. Claude calls `flag_events`. Code compares each ticker's latest daily return against its last 3 months and flags it if:
   - the return is more than 2 standard deviations from normal (z-score ≥ 2), **or**
   - volume is at least 2× its 20-day average.
3. For each flagged ticker, Claude calls `get_news` to find the likely catalyst.
4. Claude writes the brief in your template, with sources. The script saves it to `briefs/YYYY-MM-DD.md` and prints the cost.

**What Claude can and can't do:** it can only call those three tools. Built-in tools (shell, file access, web) are switched off, and there is a hard cost cap per run.

---

## 2. Prerequisites

| Requirement | Notes |
|---|---|
| Python 3.10 or newer | Check with `python --version` |
| An Anthropic API key | Create one at [console.anthropic.com](https://console.anthropic.com). You pay per use. |
| Node.js (optional) | Only needed for the MCP Inspector testing tool (see the testing guide) |

No market data subscription is needed for the basic version. yfinance is free.

---

## 3. Project files

```
market-agent/
├── market_tools.py      MCP server with the three tools
├── run_brief.py         the agent: connects, runs, saves the brief
├── analyst_prompt.md    Claude's instructions and output template
├── watchlist.txt        your tickers, one per line
├── requirements.txt     Python dependencies
├── tests/
│   └── test_market_tools.py   offline tests for the tools
└── briefs/              created on first run; one .md file per day
```

| File | When you'll edit it |
|---|---|
| `watchlist.txt` | Whenever your watchlist changes |
| `analyst_prompt.md` | Most often: this is where you tune tone, format and rules |
| `market_tools.py` | To change thresholds or add new tools |
| `run_brief.py` | To change the model, cost cap or connect more MCP servers |

Full source for every file is in the [appendix](#appendix-full-source-code).

---

## 4. Setup

### 4.1 Create the project files

1. Create a folder named `market-agent`.
2. Inside it, create these five files and paste in the code from the [appendix](#appendix-full-source-code):
   - `requirements.txt`
   - `watchlist.txt`
   - `market_tools.py`
   - `run_brief.py`
   - `analyst_prompt.md`
3. Open a terminal in the `market-agent` folder.

Use a code editor such as VS Code, not a word processor, so the code isn't reformatted. File names must match exactly. The test file is covered in `market-agent-testing.md`.

### 4.2 Create a virtual environment and install dependencies

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows (PowerShell)**

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

The Claude Agent SDK includes everything it needs; there's nothing else to install.

### 4.3 Set your API key

**macOS / Linux** (current terminal only)

```bash
export ANTHROPIC_API_KEY=sk-ant-...
```

To make it permanent, add that line to `~/.zshrc` (macOS) or `~/.bashrc` (Linux).

**Windows (PowerShell)**

```powershell
$env:ANTHROPIC_API_KEY = "sk-ant-..."          # current window only
setx ANTHROPIC_API_KEY "sk-ant-..."            # permanent; open a new window afterwards
```

Never put the key in a code file or commit it to git.

### 4.4 Add your tickers

Edit `watchlist.txt`, one ticker per line. Lines starting with `#` are ignored. Use Yahoo's ticker format (for example, `BRK-B`, not `BRK.B`). Start with 5–30 tickers.

---

## 5. Test it

Full testing steps are in the companion file **`market-agent-testing.md`**. In short, test in layers:

| Layer | What it checks | Testing guide step |
|---|---|---|
| Offline tests | The math and error handling in your tools | 2–3 |
| Live data check | yfinance is returning real data | 4 |
| MCP Inspector | The tools work the way Claude will see them | 5 |
| Agent test runs | Claude writes a good brief from the tools | 6 |
| Schedule test | The scheduled job actually runs | 7 |
| Quality log | The briefs are useful over the first week | 8 |

At minimum, run the offline tests and the live data check before your first agent run.

---

## 6. Run the agent

```bash
python run_brief.py
```

You'll see each tool call as it happens, then a summary line:

```
-> mcp__market__flag_events {}
-> mcp__market__get_news {'ticker': 'NVDA'}
Saved briefs/2026-11-03.md (6 turns, $0.0xx)
```

Open the file in `briefs/` to read the brief.

**Note on timing:** run it before the market opens or after it closes. The brief then covers the most recent completed trading session (on a Monday morning, that's Friday). During trading hours, yfinance includes the current partial day, so returns are incomplete and volume looks low. Each ticker's `as_of` date shows which session was used.

---

## 7. Tune it for a week

Most of the quality comes from tuning, not code. Run it daily for a week and keep notes on each brief:

| If you see this | Change this |
|---|---|
| Too many tickers flagged / noisy | Raise `z_threshold` and `volume_threshold` defaults in `flag_events` (try 2.5 and 2.5) |
| Missing moves you cared about | Lower the thresholds (try 1.5) |
| Explanations are vague or speculative | Tighten the rules in `analyst_prompt.md` (for example: "only state a catalyst if a headline directly mentions it") |
| Format isn't what you want | Edit the output template in `analyst_prompt.md` |
| Wrong or stale explanations | Check the `get_news` output in the Inspector; the data may be the issue, not the prompt |

Change one thing at a time so you know what helped.

---

## 8. Schedule it

The scheduled run uses absolute paths, so it works from any folder. **Your computer must be on and awake at the scheduled time.**

### macOS / Linux (cron)

Run `crontab -e` and add these lines (replace the paths and key):

```
ANTHROPIC_API_KEY=sk-ant-...
15 8 * * 1-5  /path/to/market-agent/.venv/bin/python /path/to/market-agent/run_brief.py >> /path/to/market-agent/run.log 2>&1
```

This runs at 8:15am, Monday to Friday. Cron doesn't load your shell profile, which is why the key goes in the crontab. Check `run.log` if a brief is missing.

### Windows (Task Scheduler)

Make sure you've set the key permanently with `setx` (step 4.3), then run:

```powershell
schtasks /create /tn "MarketBrief" /sc weekly /d MON,TUE,WED,THU,FRI /st 08:15 /tr "C:\path\to\market-agent\.venv\Scripts\python.exe C:\path\to\market-agent\run_brief.py"
```

### Later: run it in the cloud

To run without your computer, use GitHub Actions or a small cloud function on a schedule, with the API key stored as a secret.

---

## 9. Customize and extend

### 9.1 Choose the model

Add a `model` line to `ClaudeAgentOptions` in `run_brief.py`, using a model ID from Anthropic's models page:

```python
options = ClaudeAgentOptions(
    model="<model-id>",
    ...
)
```

### 9.2 Add a tool

Four steps:

1. Write a function in `market_tools.py` with the `@mcp.tool()` decorator. The docstring is what Claude reads to decide when to use the tool, so write it clearly.
2. Add it to `allowed_tools` in `run_brief.py` as `mcp__market__<function_name>`.
3. Mention it in the Process section of `analyst_prompt.md`.
4. Add a test for it (testing guide, step 9).

Example, an upcoming-earnings tool (tested with fake data only; check it with live data in the Inspector before relying on it):

```python
@mcp.tool()
def get_earnings_date(ticker: str) -> dict:
    """Next scheduled earnings date for one ticker, if known.
    Use this for the 'Worth watching' line of a brief.
    """
    cal = yf.Ticker(ticker.strip().upper()).calendar or {}
    dates = cal.get("Earnings Date") or []
    return {"ticker": ticker.strip().upper(), "next_earnings": [str(d) for d in dates]}
```

```python
allowed_tools=[
    "mcp__market__flag_events",
    "mcp__market__compute_moves",
    "mcp__market__get_news",
    "mcp__market__get_earnings_date",
],
```

### 9.3 Connect a ready-made MCP server

Data providers such as FMP, Alpha Vantage and Bigdata.com publish their own MCP servers. To add one:

1. Get the server URL and API key from the provider's docs.
2. Add it to `mcp_servers` in `run_brief.py`:

```python
mcp_servers={
    "market": {"type": "stdio", "command": sys.executable, "args": [str(HERE / "market_tools.py")]},
    "fmp": {"type": "http", "url": os.environ["FMP_MCP_URL"]},
},
```

(Add `import os` at the top of the file.)

3. Find the tool names in the provider's docs or with the MCP Inspector, then add only the ones you need to `allowed_tools`, as `mcp__fmp__<tool_name>`. Some servers expose 100+ tools; allowing just a few keeps Claude focused and costs down.

### Tips for writing good tools

- **Return small, pre-computed results.** Return a z-score, not 60 rows of prices.
- **Make one tool do one clear job,** with a docstring that says when to use it.
- **Handle errors inside the tool** and return them as data, so one bad ticker doesn't stop the run.
- **Keep every tool read-only.** Never add tools that can place trades or move money.

---

## 10. Costs and guardrails

| Setting (in `run_brief.py`) | What it does | Default |
|---|---|---|
| `max_budget_usd` | Hard stop if a run costs more than this | `1.00` |
| `max_turns` | Stops the run after this many steps | `25` |
| `tools=[]` | Turns off built-in tools (shell, files, web) | on |
| `strict_mcp_config=True` | Uses only the MCP servers listed in the script | on |
| `allowed_tools` | The only tools Claude can call | 3 tools |

The script prints the cost of each run. Watch it for the first few days, then set `max_budget_usd` a little above your typical run. Cost grows with watchlist size and the number of flagged tickers.

**The output is research, not investment advice.** The prompt forbids buy/sell recommendations; keep it that way.

---

## 11. Troubleshooting

| Problem | Cause and fix |
|---|---|
| `ModuleNotFoundError: No module named 'mcp.server.mcpserver'` | You have MCP version 1. Run `pip install -U "mcp>=2"`. |
| `No module named 'mcp.server.fastmcp'` | You're using older example code. In MCP v2, `FastMCP` was renamed: use `from mcp.server.mcpserver import MCPServer`. |
| Authentication / invalid API key error | The key isn't set in this terminal. Re-run the step 4.3 command and check with `echo $ANTHROPIC_API_KEY` (macOS/Linux) or `echo $env:ANTHROPIC_API_KEY` (PowerShell). |
| A ticker shows `not enough price history` | Wrong symbol format (use `BRK-B`, not `BRK.B`), a delisted ticker, or a very recent IPO. |
| Many tickers erroring at once | Yahoo is rate-limiting or yfinance is temporarily broken. Wait and retry, or run `pip install -U yfinance`. |
| `Run failed: error_max_budget_usd` | The run hit the cost cap. Raise `max_budget_usd` or shorten the watchlist. |
| `Run failed: error_max_turns` | Too many steps. Raise `max_turns` (common with long watchlists). |
| `get_news` returns an empty list | Yahoo has no recent headlines for that ticker. The brief should say "No clear catalyst found." |
| Scheduled run didn't happen | The computer was asleep, a path is wrong, or the key isn't available to the scheduler. Check `run.log`. |

---

## 12. Known limitations

- **yfinance is unofficial.** It scrapes Yahoo Finance and can break or be rate-limited. It's fine for a prototype; switch to a paid provider for anything you rely on.
- **News is headlines only.** There are no SEC filings, earnings call transcripts or analyst data yet.
- **No memory.** Each brief starts fresh, with no comparison to earlier briefs.
- **Daily data only.** Moves are measured close-to-close, not intraday. Run it outside market hours (see section 6).
- **Testing status:** the offline test suite passes (testing guide, step 3), including the tools working through a real MCP client. The live data check (step 4) and a full agent run (step 6) still need to be confirmed on your machine.

---

## 13. Roadmap

| Phase | What you add | Why |
|---|---|---|
| 1. Proof of concept (optional) | Run the brief as a no-code scheduled task in Claude, with a market data connector | Test the brief's usefulness before writing code |
| 2. Basic version (this guide) | Watchlist scan, news, daily brief | A working agent you control |
| 3. Reliability | Paid data via a provider's MCP server; earnings dates; SEC filings from EDGAR (free) | Trustworthy data and better "why" explanations |
| 4. Memory | Save each brief, plus a `get_past_briefs(ticker, days)` tool | "Is this move part of a trend?" and tracking your thesis on each stock |
| 5. RAG | Search over many filings and transcripts | Questions like "how has management's language on margins changed over 12 quarters?" |

Start memory with simple lookups by ticker and date. Add vector search (RAG) only when that stops being enough.

---

## Appendix: full source code

The test file, `tests/test_market_tools.py`, and its instructions are in `market-agent-testing.md`.

### requirements.txt

```
claude-agent-sdk>=0.2
mcp>=2.0
yfinance
pandas
```

### watchlist.txt

```
# One ticker per line. Lines starting with # are ignored.
AAPL
MSFT
NVDA
AMZN
JPM
```

### market_tools.py

```python
"""MCP server with the market tools the analyst agent can call.

Every number the agent reports comes from these functions, computed in code.
The agent never does math itself.

Test it on its own:  npx @modelcontextprotocol/inspector python market_tools.py
"""

from pathlib import Path

import yfinance as yf
from mcp.server.mcpserver import MCPServer

WATCHLIST_FILE = Path(__file__).parent / "watchlist.txt"

mcp = MCPServer("market-tools")


def load_watchlist() -> list[str]:
    lines = WATCHLIST_FILE.read_text().splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


def _moves(ticker: str) -> dict:
    """Core calculation shared by the tools below."""
    df = yf.Ticker(ticker).history(period="3mo")
    if len(df) < 25:
        return {"ticker": ticker, "error": "not enough price history"}

    close, volume = df["Close"], df["Volume"]
    returns = close.pct_change().dropna()
    today = returns.iloc[-1]
    baseline = returns.iloc[:-1]  # history before today, so today doesn't skew its own baseline
    std = baseline.std()
    avg_volume = volume.iloc[-21:-1].mean()  # prior 20 sessions

    return {
        "ticker": ticker,
        "as_of": df.index[-1].date().isoformat(),
        "last_close": round(float(close.iloc[-1]), 2),
        "return_1d_pct": round(float(today) * 100, 2),
        "return_5d_pct": round(float(close.iloc[-1] / close.iloc[-6] - 1) * 100, 2),
        "return_zscore": round(float((today - baseline.mean()) / std), 2) if std > 0 else 0.0,
        "volume_vs_avg": round(float(volume.iloc[-1] / avg_volume), 2) if avg_volume > 0 else None,
    }


@mcp.tool()
def flag_events(z_threshold: float = 2.0, volume_threshold: float = 2.0) -> dict:
    """Scan the whole watchlist and return only the tickers with unusual moves.

    A ticker is flagged if its 1-day return z-score is beyond +/- z_threshold, or its
    volume is at least volume_threshold times its 20-day average. Quiet tickers come
    back with just their 1-day return. Call this first when writing a brief.
    """
    flagged, quiet, errors = [], [], []
    for ticker in load_watchlist():
        try:
            m = _moves(ticker)
        except Exception as e:  # one bad ticker shouldn't sink the whole scan
            errors.append({"ticker": ticker, "error": str(e)})
            continue
        if "error" in m:
            errors.append(m)
        elif abs(m["return_zscore"]) >= z_threshold or (m["volume_vs_avg"] or 0) >= volume_threshold:
            flagged.append(m)
        else:
            quiet.append({"ticker": ticker, "return_1d_pct": m["return_1d_pct"]})
    return {"flagged": flagged, "quiet": quiet, "errors": errors}


@mcp.tool()
def compute_moves(ticker: str) -> dict:
    """Price and volume stats for one ticker: last close, 1-day and 5-day return,
    1-day return z-score vs. the last 3 months, and volume vs. its 20-day average.
    Use this for any figure you report; never estimate numbers yourself.
    """
    return _moves(ticker.strip().upper())


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


if __name__ == "__main__":
    mcp.run()  # speaks MCP over stdio; the agent starts this as a subprocess
```

### run_brief.py

```python
"""Run the analyst agent once and save today's brief to briefs/YYYY-MM-DD.md.

Usage:
    export ANTHROPIC_API_KEY=sk-ant-...
    python run_brief.py
"""

import asyncio
import sys
from datetime import date
from pathlib import Path

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolUseBlock,
    query,
)

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


async def main() -> None:
    today = date.today().isoformat()
    prompt = f"Today is {today}. Write the watchlist brief."

    async for message in query(prompt=prompt, options=options):
        # Log every tool call so you can audit where each claim came from
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    print(f"-> {block.name} {block.input}")

        if isinstance(message, ResultMessage):
            if message.is_error or not message.result:
                sys.exit(f"Run failed: {message.subtype}")
            out = HERE / "briefs" / f"{today}.md"
            out.parent.mkdir(exist_ok=True)
            out.write_text(message.result)
            cost = message.total_cost_usd or 0
            print(f"Saved {out} ({message.num_turns} turns, ${cost:.3f})")


if __name__ == "__main__":
    asyncio.run(main())
```

### analyst_prompt.md

```markdown
You are an equity research analyst writing a short morning brief on the user's watchlist.

## Process

1. Call `flag_events` first. It returns the tickers with unusual moves, plus the quiet ones.
2. For each flagged ticker, call `get_news` to find the likely reason. Call `compute_moves` if you need more detail on a ticker.
3. Write the brief.

## Rules

- Every number must come from a tool result. Never estimate or calculate figures yourself.
- Cite a source (publisher and link) for every explanation.
- Keep facts separate from interpretation. If the news doesn't clearly explain a move, write "No clear catalyst found."
- If nothing was flagged, say so in one line. Don't invent significance.
- If a tool returned errors for some tickers, list them at the end.
- This is research, not investment advice. Never recommend buying or selling.

## Output

Respond with only the brief, in this markdown format:

# Watchlist brief: {date}

## Notable moves

### {TICKER}: {return_1d_pct}% (z-score {return_zscore}, volume {volume_vs_avg}x average)
- **What happened:** one or two factual sentences.
- **Likely why:** the catalyst, with [publisher](url). Or "No clear catalyst found."
- **Worth watching:** one line on what to check next.

## Quiet today

{TICKER} ({return_1d_pct}%), ...

## Data issues

Only include this section if any tickers returned errors.
```
