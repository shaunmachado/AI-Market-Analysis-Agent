"""Tracked stocks: find them, add and remove them, and choose the main ones for the dashboard.

watchlist.txt stays the one list everything reads (the agent, alerts, the calendar).
A * in front of a ticker marks a main stock, shown first on the Today tab:

    *AAPL
    *NVDA  SMH      # a benchmark and a comment, as before
    MSFT

If no ticker has a *, the first 10 count as main, so older watchlists work unchanged.

The app edits the file one line at a time, so your other lines, benchmarks and comments
are kept. Each edit replaces the file in one step, so a run starting at that moment
sees either the old list or the new one, never half of each.
"""

import os
import re
import tempfile
import threading
import time

import yfinance as yf

import events
import market_tools

MAX_TRACKED = int(os.environ.get("MAX_TRACKED", "25"))  # raise when you want to track more (see the guide)
MAX_MAIN = 10                                          # main stocks shown on the dashboard
ALLOWED_TYPES = {"EQUITY": "Stock", "ETF": "ETF"}       # what can be tracked (no funds, futures, crypto...)
SEARCH_CACHE_SECONDS = 600
TICKER = re.compile(r"[A-Z0-9][A-Z0-9\-]{0,9}")         # US tickers as Yahoo writes them, e.g. BRK-B

_lock = threading.Lock()  # one edit at a time within this program
_search_cache: dict[str, tuple[float, list[dict]]] = {}


class WatchlistError(ValueError):
    """A request that can't be done, with a message to show as it is.
    status is the matching HTTP status for the API: 400, 404 (not on the list) or 409 (conflicts)."""

    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------

def _path():
    return market_tools.WATCHLIST_FILE  # read each time, so tests and the test environment can point elsewhere


def _parse(line: str) -> dict | None:
    code = line.split("#", 1)[0]
    words = code.replace("*", " ").upper().split()
    if not words:
        return None
    return {"ticker": words[0], "benchmark": words[1] if len(words) > 1 else None, "starred": "*" in code}


def entries() -> list[dict]:
    """Every tracked stock in file order: ticker, benchmark, and whether it's a main stock."""
    found = [e for e in (_parse(line) for line in market_tools.read_watchlist_text().splitlines()) if e]
    any_star = any(e["starred"] for e in found)
    for i, e in enumerate(found):
        e["main"] = e["starred"] if any_star else i < MAX_MAIN
    return found


def main_tickers() -> list[str]:
    return [e["ticker"] for e in entries() if e["main"]]


# ---------------------------------------------------------------------------
# Editing
# ---------------------------------------------------------------------------

REPLACE_ATTEMPTS, REPLACE_WAIT_SECONDS = 40, 0.05  # up to about 2 seconds in all


def _replace(temp: str, path) -> None:
    """os.replace, tried again for a moment if it's refused. On Windows a file can't be replaced while
    anything else has it open: a run or the API reading the list at that instant, or a virus scanner
    looking at the new file. That passes in milliseconds, so the edit waits instead of failing."""
    for attempt in range(REPLACE_ATTEMPTS):
        try:
            os.replace(temp, path)
            return
        except PermissionError:
            if attempt == REPLACE_ATTEMPTS - 1:
                raise
            time.sleep(REPLACE_WAIT_SECONDS)


def _write(lines: list[str]) -> None:
    """Replace the file in one step (write a temporary file, then swap it in)."""
    path = _path()
    handle, temp = tempfile.mkstemp(dir=path.parent, prefix=".watchlist-", suffix=".tmp")
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
        try:
            os.chmod(temp, path.stat().st_mode & 0o777)  # keep the file's permissions
        except OSError:
            pass
        _replace(temp, path)
    except BaseException:
        if os.path.exists(temp):
            os.unlink(temp)
        raise


def _star(line: str, on: bool) -> str:
    """Add or remove the * in front of the ticker, keeping the rest of the line as it was."""
    code, sep, comment = line.partition("#")
    code = code.replace("*", "")
    if on:
        code = re.sub(r"^(\s*)(\S)", r"\1*\2", code, count=1)
    return code + sep + comment


def _edit(change) -> list[dict]:
    """Read the file, apply change(lines, rows, current) and write it back, all under the lock.
    rows maps each ticker to its line number; current is the list as entries() gives it."""
    with _lock:
        lines = market_tools.read_watchlist_text().splitlines()
        rows = {}
        for i, line in enumerate(lines):
            parsed = _parse(line)
            if parsed:
                rows[parsed["ticker"]] = i
        current = entries()
        if current and not any(e["starred"] for e in current):  # make the implicit main stocks explicit first,
            for e in current:                                     # so the edit can't change which ones are main
                if e["main"]:
                    lines[rows[e["ticker"]]] = _star(lines[rows[e["ticker"]]], True)
        change(lines, rows, current)
        _write(lines)
    return entries()


def _can_add(ticker: str, main: bool, current: list[dict]) -> None:
    if ticker in {e["ticker"] for e in current}:
        raise WatchlistError(f"You're already tracking {ticker}.", 409)
    if len(current) >= MAX_TRACKED:
        raise WatchlistError(f"You're tracking {MAX_TRACKED} stocks, the most allowed. Remove one first, "
                             "or raise MAX_TRACKED (see the guide).", 409)
    if main and sum(e["main"] for e in current) >= MAX_MAIN:
        raise WatchlistError(f"You already have {MAX_MAIN} main stocks. Add it as tracked, or unstar one first.", 409)


def add(ticker: str, main: bool = False) -> dict:
    """Start tracking a stock, after checking it with Yahoo Finance. Returns its details."""
    ticker = ticker.strip().upper()
    if not TICKER.fullmatch(ticker):
        raise WatchlistError("That isn't a US ticker (letters, numbers and - only, like AAPL or BRK-B).")
    _can_add(ticker, main, entries())  # quick checks before asking Yahoo...
    info = check_ticker(ticker)

    def change(lines, rows, current):
        _can_add(ticker, main, current)  # ...and again under the lock, in case the list changed meanwhile
        lines.append(f"{'*' if main else ''}{ticker}")

    _edit(change)
    return {**info, "main": main}


def remove(ticker: str) -> None:
    """Stop tracking a stock. Its past reports and calendar history stay."""
    ticker = ticker.strip().upper()

    def change(lines, rows, current):
        if ticker not in rows:
            raise WatchlistError(f"{ticker} isn't on your list.", 404)
        lines[:] = [line for line in lines if (_parse(line) or {}).get("ticker") != ticker]  # every copy, if added twice

    _edit(change)


def set_main(ticker: str, main: bool) -> None:
    """Star (main, on the dashboard) or unstar a tracked stock."""
    ticker = ticker.strip().upper()

    def change(lines, rows, current):
        by_ticker = {e["ticker"]: e for e in current}
        if ticker not in by_ticker:
            raise WatchlistError(f"{ticker} isn't on your list.", 404)
        if main and not by_ticker[ticker]["main"] and sum(e["main"] for e in current) >= MAX_MAIN:
            raise WatchlistError(f"You already have {MAX_MAIN} main stocks. Unstar one first.", 409)
        lines[rows[ticker]] = _star(lines[rows[ticker]], main)

    _edit(change)


# ---------------------------------------------------------------------------
# Finding stocks with Yahoo Finance
# ---------------------------------------------------------------------------

def search_yahoo(query: str) -> list[dict]:
    """Yahoo Finance's own search (yfinance's Search). Tests and the test environment replace this."""
    if not hasattr(yf, "Search"):
        raise WatchlistError("Searching needs a newer yfinance: run pip install -U yfinance")
    return yf.Search(query, max_results=15, news_count=0, lists_count=0).quotes or []


def search(query: str, limit: int = 8) -> list[dict]:
    """US-listed stocks and ETFs matching a name or ticker, best match first."""
    query = " ".join(query.split())[:60]
    if not query:
        return []
    key = query.lower()
    cached = _search_cache.get(key)
    if cached and time.monotonic() - cached[0] < SEARCH_CACHE_SECONDS:
        quotes = cached[1]
    else:
        try:
            quotes = search_yahoo(query)
        except WatchlistError:
            raise
        except Exception as e:
            raise WatchlistError(f"Yahoo Finance search isn't answering right now ({e}). Try again shortly.") from None
        _search_cache[key] = (time.monotonic(), quotes)
        if len(_search_cache) > 200:  # keep the cache small
            _search_cache.pop(next(iter(_search_cache)))
    tracked = {e["ticker"] for e in entries()}
    results = []
    for q in quotes:
        symbol = str(q.get("symbol") or "").upper()
        kind = q.get("quoteType") or str(q.get("typeDisp") or "").upper()
        if kind not in ALLOWED_TYPES or not TICKER.fullmatch(symbol):  # a "." means a listing outside the US
            continue
        name = q.get("longname") or q.get("shortname") or symbol
        events._names.setdefault(symbol, events.short_name(name))  # remembered for the Stocks tab
        results.append({"ticker": symbol, "name": name, "type": ALLOWED_TYPES[kind],
                        "exchange": q.get("exchDisp") or q.get("exchange") or "", "tracked": symbol in tracked})
    return results[:limit]


def check_ticker(ticker: str) -> dict:
    """Confirm Yahoo Finance knows the ticker and it's a stock or ETF. Returns its name and type."""
    try:
        info = yf.Ticker(ticker).info or {}
    except Exception as e:
        raise WatchlistError(f"Couldn't check {ticker} with Yahoo Finance right now ({e}). Try again shortly.") from None
    kind = info.get("quoteType")
    name = info.get("longName") or info.get("shortName")
    if not kind or not name:
        raise WatchlistError(f"Yahoo Finance doesn't know {ticker}. Check the spelling, or search by company name.")
    if kind not in ALLOWED_TYPES:
        raise WatchlistError(f"{ticker} is a {kind.lower().replace('_', ' ')}. Only stocks and ETFs can be tracked.")
    events._names[ticker] = events.short_name(name)
    return {"ticker": ticker, "name": name, "type": ALLOWED_TYPES[kind]}
