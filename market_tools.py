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
