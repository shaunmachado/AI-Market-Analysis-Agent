"""Run the analyst agent once and save the report to the reports database.

Works at any time:
- Market open: writes an intraday update and saves it as today's report,
  replacing any earlier update from today.
- Market closed: writes the final report for the last session. Final reports
  are permanent; if it's already saved, this stops before calling Claude.

Auth: if MARKET_AGENT_ANTHROPIC_KEY is set (in .env or the environment), this
script bills that API key. Otherwise it uses your Claude Code login (subscription).
The key is handed only to the Claude process this script starts; a global
ANTHROPIC_API_KEY is ignored, so your own Claude Code sessions keep using Pro.

Usage:
    claude login   # once, if you're not using an API key
    python run_brief.py

The API's "Run update now" button calls run_once() from here too.
"""

import asyncio
import dataclasses
import json
import os
import sys
from contextlib import closing
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

# An ANTHROPIC_API_KEY in the environment overrides the subscription login,
# so drop any stray one and pass the project's key explicitly (below).
os.environ.pop("ANTHROPIC_API_KEY", None)
API_KEY = (os.environ.get("MARKET_AGENT_ANTHROPIC_KEY") or "").strip()
AGENT_ENV = {"ANTHROPIC_API_KEY": API_KEY} if API_KEY else {}

from claude_agent_sdk import (  # noqa: E402
    AssistantMessage,
    ClaudeAgentOptions,
    ResultMessage,
    ToolResultBlock,
    ToolUseBlock,
    UserMessage,
    query,
)

import alerts  # noqa: E402
import reports_db  # noqa: E402
import search_index  # noqa: E402
from market_tools import flag_events, load_watchlist, market_session, now_et  # noqa: E402

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
        "mcp__market__market_backdrop",
        "mcp__market__compute_moves",
        "mcp__market__get_news",
        "mcp__market__upcoming_events",
    ],
    max_turns=BASE_TURNS,    # each run uses turn_limit() instead (below)
    max_budget_usd=1.00,     # hard stop on cost per run
    env=AGENT_ENV,
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
