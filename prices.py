"""Daily price history for the charts, from Yahoo Finance (yfinance).

Results are kept for a few minutes, so opening the same chart again doesn't
download it again. The test environment swaps fetch_prices() for simulated prices.
"""

import time

import yfinance as yf

RANGES = ("1mo", "3mo", "6mo", "1y")
CACHE_SECONDS = 300
_cache: dict[tuple[str, str], tuple[float, list[dict]]] = {}


def fetch_prices(ticker: str, period: str) -> list[dict]:
    """Daily closes and volume, oldest first. While the market is open, the last
    row is today's price so far."""
    df = yf.Ticker(ticker).history(period=period, interval="1d").dropna(subset=["Close"])
    return [{"date": ts.date().isoformat(), "close": round(float(close), 2), "volume": int(volume or 0)}
            for ts, close, volume in zip(df.index, df["Close"], df["Volume"].fillna(0))]


def get_prices(ticker: str, period: str) -> list[dict]:
    """fetch_prices(), cached, with each day's % change from the day before."""
    key = (ticker.upper(), period)
    cached = _cache.get(key)
    if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
        return cached[1]
    rows = fetch_prices(*key)
    for previous, row in zip([None] + rows, rows):
        row["change_pct"] = (round((row["close"] / previous["close"] - 1) * 100, 2)
                             if previous and previous["close"] else None)  # a zero close is bad data: no % change
    if rows:
        _cache[key] = (time.monotonic(), rows)
    return rows
