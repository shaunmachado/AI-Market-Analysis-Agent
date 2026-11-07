"""Offline tests for the chart data: prices.py and /api/tickers/{ticker}/prices.

Run from the project folder:
    pytest -v tests/test_charts.py
"""

import math
import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import prices  # noqa: E402
import reports_db  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402


@pytest.fixture(autouse=True)
def clean(tmp_path, monkeypatch):
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    prices._cache.clear()


@pytest.fixture
def fake_prices(monkeypatch):
    """Replace the download with three days of prices; returns a log of calls."""
    calls = []

    def fetch(ticker, period):
        calls.append((ticker, period))
        return [{"date": "2026-11-04", "close": 100.0, "volume": 1_000},
                {"date": "2026-11-05", "close": 110.0, "volume": 3_000},
                {"date": "2026-11-06", "close": 99.0, "volume": 2_000}]

    monkeypatch.setattr(prices, "fetch_prices", fetch)
    return calls


def test_prices_endpoint_returns_daily_closes_with_changes(fake_prices):
    data = TestClient(api.app).get("/api/tickers/nvda/prices?range=1mo").json()

    assert data["ticker"] == "NVDA" and data["range"] == "1mo"
    assert [p["close"] for p in data["prices"]] == [100.0, 110.0, 99.0]
    assert [p["change_pct"] for p in data["prices"]] == [None, 10.0, -10.0]
    assert fake_prices == [("NVDA", "1mo")]


def test_default_range_is_three_months(fake_prices):
    assert TestClient(api.app).get("/api/tickers/AAPL/prices").json()["range"] == "3mo"


def test_prices_are_cached_between_clicks(fake_prices):
    client = TestClient(api.app)
    client.get("/api/tickers/NVDA/prices?range=6mo")
    client.get("/api/tickers/nvda/prices?range=6mo")
    client.get("/api/tickers/NVDA/prices?range=1y")
    assert fake_prices == [("NVDA", "6mo"), ("NVDA", "1y")]  # the repeat came from the cache


@pytest.mark.parametrize("path", ["/api/tickers/not%20a%20ticker/prices", "/api/tickers/NVDA/prices?range=5y"])
def test_prices_reject_bad_requests(fake_prices, path):
    response = TestClient(api.app).get(path)
    assert response.status_code == 400 and "error" in response.json()


def test_prices_report_data_problems_clearly(monkeypatch):
    client = TestClient(api.app)

    def broken(ticker, period):
        raise ConnectionError("rate limited")

    monkeypatch.setattr(prices, "fetch_prices", broken)
    failed = client.get("/api/tickers/NVDA/prices")
    assert failed.status_code == 502 and "rate limited" in failed.json()["error"]

    monkeypatch.setattr(prices, "fetch_prices", lambda ticker, period: [])
    missing = client.get("/api/tickers/ZZZZ/prices")
    assert missing.status_code == 404 and "no price data" in missing.json()["error"]


def test_fetch_prices_reads_yfinance_data(monkeypatch):
    """Missing closes are skipped and missing volume counts as 0, as Yahoo sometimes has gaps."""
    index = pd.date_range("2026-11-02", periods=4, freq="B", tz="America/New_York")
    frame = pd.DataFrame({"Close": [100.123, math.nan, 101.0, 102.5], "Volume": [10.0, 20.0, math.nan, 40.0]},
                         index=index)

    class FakeTicker:
        def __init__(self, ticker):
            pass

        def history(self, period, interval):
            assert interval == "1d"
            return frame

    monkeypatch.setattr(prices.yf, "Ticker", FakeTicker)

    assert prices.fetch_prices("NVDA", "1mo") == [
        {"date": "2026-11-02", "close": 100.12, "volume": 10},
        {"date": "2026-11-04", "close": 101.0, "volume": 0},
        {"date": "2026-11-05", "close": 102.5, "volume": 40},
    ]
