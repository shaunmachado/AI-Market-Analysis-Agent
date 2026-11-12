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


def read_watchlist_text() -> str:
    """watchlist.txt as text. The app saves it as UTF-8. A byte-order mark (which some Windows
    editors add) is skipped, and a file saved in the older Windows encoding still reads.
    Never rely on Python's default encoding here: on Windows it isn't UTF-8."""
    data = WATCHLIST_FILE.read_bytes()
    try:
        return data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return data.decode("cp1252", errors="replace")


def _watchlist_entries() -> list[list[str]]:
    """Each line: a ticker, optionally followed by the benchmark to compare it with.
    A * before the ticker marks a main stock for the dashboard (see watchlist.py); the
    agent tracks every ticker either way. Anything after a # is a comment."""
    entries = []
    for line in read_watchlist_text().splitlines():
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
    daily = yf.Ticker(ticker).history(period="3mo").dropna(subset=["Close"])  # a day without a price is a missing day
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
    bars = yf.Ticker(ticker).history(period="1mo", interval="5m").dropna(subset=["Close"])  # e.g. a bar not filled in yet
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
