"""MCP server with the market tools the analyst agent can call.

Every number the agent reports comes from these functions, computed in code.
The agent never does math itself.

Works at any time of day:
- Market closed (evenings, weekends, holidays, pre-market): measures the last
  completed session against the previous 3 months of daily moves.
- Market open: measures today's move *so far* against the same time of day in
  recent sessions, so a partial day is never treated as a full one.

Test it on its own:  npx @modelcontextprotocol/inspector python market_tools.py
"""

from datetime import date, datetime, time, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf
from mcp.server.mcpserver import MCPServer

WATCHLIST_FILE = Path(__file__).parent / "watchlist.txt"
ET = ZoneInfo("America/New_York")
MARKET_CLOSE = time(16, 0)
REFERENCE_TICKER = "SPY"             # used to tell whether the market is open
STALE_AFTER = timedelta(minutes=30)  # no new bar for this long means trading has stopped (early close)
MIN_INTRADAY_DAYS = 10               # past sessions needed for a same-time-of-day comparison

mcp = MCPServer("market-tools")


def now_et() -> datetime:
    return datetime.now(ET)


def _to_et(index: pd.DatetimeIndex) -> pd.DatetimeIndex:
    return index.tz_localize(ET) if index.tz is None else index.tz_convert(ET)


def load_watchlist() -> list[str]:
    lines = WATCHLIST_FILE.read_text().splitlines()
    return [ln.strip().upper() for ln in lines if ln.strip() and not ln.startswith("#")]


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


def _moves(ticker: str, session: dict) -> dict:
    """Core calculation shared by the tools below."""
    daily = yf.Ticker(ticker).history(period="3mo")
    if len(daily) < 25:
        return {"ticker": ticker, "error": "not enough price history"}
    daily.index = _to_et(daily.index)
    if session["status"] == "in_progress":
        return _intraday_moves(ticker, daily, session)
    return _completed_session_moves(ticker, daily, session)


def _completed_session_moves(ticker: str, daily: pd.DataFrame, session: dict) -> dict:
    """Last completed session vs. the previous 3 months of daily moves."""
    last_session = date.fromisoformat(session["as_of"])
    daily = daily[daily.index.date <= last_session]  # ignore any row for a session that hasn't finished
    if len(daily) < 25:
        return {"ticker": ticker, "error": "not enough price history"}

    close, volume = daily["Close"], daily["Volume"]
    returns = close.pct_change().dropna()
    today = returns.iloc[-1]
    baseline = returns.iloc[:-1]  # history before the session, so it doesn't skew its own baseline
    std = baseline.std()
    avg_volume = volume.iloc[-21:-1].mean()  # prior 20 sessions

    return {
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


def _intraday_moves(ticker: str, daily: pd.DataFrame, session: dict) -> dict:
    """Today's move so far vs. the same time of day in recent sessions."""
    bars = yf.Ticker(ticker).history(period="1mo", interval="5m")
    if bars.empty:
        return {"ticker": ticker, "error": "no intraday data"}
    bars.index = _to_et(bars.index)

    today = datetime.strptime(session["as_of"], "%Y-%m-%d %H:%M ET").date()
    today_bars = bars[bars.index.date == today]
    if today_bars.empty:
        return {"ticker": ticker, "error": "no trades yet today"}
    cutoff = today_bars.index[-1].time()  # compare every past session up to this same time

    closes = pd.Series(daily["Close"].to_numpy(), index=daily.index.date)

    def prev_close(day: date) -> float | None:
        earlier = closes[closes.index < day]
        return float(earlier.iloc[-1]) if len(earlier) else None

    past_bars = bars[bars.index.date < today]
    past_returns, past_volumes = [], []
    for day, day_bars in past_bars.groupby(past_bars.index.date):
        if day_bars.index[-1].time() < cutoff:  # session closed early, before this time of day
            continue
        upto = day_bars[day_bars.index.time <= cutoff]
        start = prev_close(day)
        if upto.empty or start is None:
            continue
        past_returns.append(upto["Close"].iloc[-1] / start - 1)
        past_volumes.append(upto["Volume"].sum())

    start_today = prev_close(today)
    if len(past_returns) < MIN_INTRADAY_DAYS or start_today is None:
        return {"ticker": ticker, "error": "not enough intraday history"}

    price = float(today_bars["Close"].iloc[-1])
    move = price / start_today - 1
    past = pd.Series(past_returns)
    std = past.std()
    avg_volume = sum(past_volumes) / len(past_volumes)
    earlier_closes = closes[closes.index < today]

    return {
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


@mcp.tool()
def flag_events(z_threshold: float = 2.0, volume_threshold: float = 2.0) -> dict:
    """Scan the whole watchlist and return only the tickers with unusual moves.

    A ticker is flagged if its return z-score is beyond +/- z_threshold, or its volume
    is at least volume_threshold times normal. Works whether or not the market is open:
    `session.status` is "complete" for the last finished session, or "in_progress" when
    the market is open, in which case moves are measured so far today and compared with
    the same time of day in recent sessions. Call this first when writing a brief.
    """
    session = market_session()
    flagged, quiet, errors = [], [], []
    for ticker in load_watchlist():
        try:
            m = _moves(ticker, session)
        except Exception as e:  # one bad ticker shouldn't sink the whole scan
            errors.append({"ticker": ticker, "error": str(e)})
            continue
        if "error" in m:
            errors.append(m)
        elif abs(m["return_zscore"]) >= z_threshold or (m["volume_vs_avg"] or 0) >= volume_threshold:
            flagged.append(m)
        else:
            quiet.append({"ticker": ticker, "return_1d_pct": m["return_1d_pct"]})
    return {"session": session, "flagged": flagged, "quiet": quiet, "errors": errors}


@mcp.tool()
def compute_moves(ticker: str) -> dict:
    """Price and volume stats for one ticker: price, return since the previous close,
    5-day return, return z-score and volume vs. normal. When the market is open these
    are so far today, compared with the same time of day in recent sessions.
    Use this for any figure you report; never estimate numbers yourself.
    """
    return _moves(ticker.strip().upper(), market_session())


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
