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
