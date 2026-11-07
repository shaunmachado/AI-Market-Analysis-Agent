"""Offline tests for search and retrieval (RAG): search_index.py, /api/search, and how
Ask and runs use it. Voyage AI is replaced by a small stand-in that maps phrases to topics.

Run from the project folder:
    pytest -v tests/test_search.py
"""

import asyncio
import hashlib
import json
import sys
from contextlib import closing
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
import search_index  # noqa: E402
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# A stand-in for Voyage: each vector says which topics a text mentions, in any wording
TOPICS = {
    "rating down": ["downgrade", "cut its rating", "lowered its rating", "rating cut"],
    "earnings": ["quarterly results", "earnings", "profit"],
    "regulation": ["regulatory", "regulator", "investigation", "probe"],
}


def fake_embed(texts, input_type):
    fake_embed.calls.append((len(texts), input_type))
    return [[float(sum(p in t.lower() for p in phrases)) for phrases in TOPICS.values()] + [0.1] for t in texts]


def brief(day, ticker, why, status="final"):
    title = f"Watchlist brief: {day}" if status == "final" else f"Intraday update: {day} 12:30 ET"
    return title, f"""# {title}

## Notable moves

### {ticker}: +4.20% (z-score 3.1, volume 2.5x normal)
- **What happened:** {ticker} moved +4.20% on heavy volume.
- **Likely why:** {why} [Sample Wire](https://news.example.com/{day})

## Quiet

AAPL (+0.10%)
"""


def save(day, ticker, why, status="final"):
    title, body = brief(day, ticker, why, status)
    scan = {"flagged": [{"ticker": ticker, "last_close": 100.0, "return_1d_pct": 4.2, "return_zscore": 3.1,
                         "volume_vs_avg": 2.5}], "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.1}], "errors": []}
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=day, status=status, title=title, body_md=body,
                                      as_of=day if status == "final" else f"{day} 12:30 ET", scan=scan,
                                      sources=[{"ticker": ticker, "title": f"{ticker} headline", "publisher": "Sample Wire"}])


@pytest.fixture(autouse=True)
def setup(tmp_path, monkeypatch):
    """A temporary database with four reports; no Voyage key unless a test adds one."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.delenv("SEARCH_DB", raising=False)
    monkeypatch.delenv("VOYAGE_API_KEY", raising=False)
    fake_embed.calls = []
    monkeypatch.setattr(search_index, "embed", fake_embed)
    save("2026-10-01", "NVDA", "An analyst downgrade weighed on the shares.")
    save("2026-10-02", "AAPL", "Quarterly results beat expectations.")
    save("2026-10-05", "JPM", "Regulatory concerns were reported.")
    save("2026-10-06", "MSFT", "No clear catalyst found.", status="intraday")


@pytest.fixture
def voyage(monkeypatch):
    monkeypatch.setenv("VOYAGE_API_KEY", "test-key")


def search(q, **filters):
    return search_index.search(q, **filters)


# ---------------------------------------------------------------------------
# Building the index
# ---------------------------------------------------------------------------

def test_reports_are_split_into_passages():
    with closing(reports_db.connect(readonly=True)) as conn:
        passages = search_index.chunk_report(reports_db.get_report(conn, "2026-10-01"))

    assert [p["ticker"] for p in passages] == [None, "NVDA"]  # an overview, then one per flagged ticker
    overview, nvda = passages
    assert overview["heading"] == "Overview" and "AAPL (+0.10%)" in overview["text"]
    assert nvda["heading"].startswith("NVDA: +4.20%")
    assert nvda["text"].startswith("Watchlist brief: 2026-10-01 (final)\n")  # every passage carries its date
    assert "News: NVDA headline (Sample Wire)" in nvda["text"]
    assert "[Sample Wire](" not in nvda["text"] and "Sample Wire" in nvda["text"]  # link text kept, URL dropped


def test_link_addresses_are_not_searchable():
    """A keyword match should always be something a reader can see (and the app can highlight)."""
    search_index.sync()
    assert search("news.example.com")["results"] == []


def test_sync_indexes_new_changed_and_removed_reports():
    assert search_index.sync()["reports_indexed"] == 4
    assert search_index.sync()["reports_indexed"] == 0  # nothing changed

    title, body = brief("2026-10-06", "MSFT", "A regulator opened an investigation.", "intraday")
    with closing(reports_db.connect()) as conn:  # a newer intraday update for the same day
        reports_db.save_report(conn, session_date="2026-10-06", status="intraday", title=title, body_md=body,
                               as_of="2026-10-06 13:00 ET", scan={})
    assert search_index.sync()["reports_indexed"] == 1
    assert search("investigation")["results"][0]["session_date"] == "2026-10-06"
    assert search("catalyst")["results"] == []  # the old version's text is gone

    with closing(reports_db.connect()) as conn:  # the documented procedure for removing a final report
        for trigger in ("final_reports_no_delete", "report_tickers_final_no_delete", "report_sources_final_no_delete"):
            conn.execute(f"DROP TRIGGER {trigger}")
        for table in ("report_sources", "report_tickers", "reports"):
            conn.execute(f"DELETE FROM {table} WHERE session_date = '2026-10-01'")
    assert search_index.sync()["reports_removed"] == 1
    assert search("downgrade")["results"] == []


def test_reports_database_is_only_read():
    before = hashlib.sha256(Path(reports_db.DB_PATH).read_bytes()).hexdigest()
    search_index.sync()
    search("downgrade")
    assert hashlib.sha256(Path(reports_db.DB_PATH).read_bytes()).hexdigest() == before
    assert search_index.index_path() == Path(reports_db.DB_PATH).with_name("search.db")


def test_embeddings_are_made_in_batches_and_reused(voyage, monkeypatch):
    monkeypatch.setattr(search_index, "EMBED_BATCH", 3)
    assert search_index.sync()["passages_embedded"] == 8  # 4 reports x (overview + 1 ticker)
    assert all(size <= 3 and kind == "document" for size, kind in fake_embed.calls)

    fake_embed.calls = []
    search_index.sync()
    assert fake_embed.calls == []  # already embedded: nothing sent again

    monkeypatch.setattr(search_index, "EMBED_MODEL", "voyage-finance-2")
    assert search_index.sync()["passages_embedded"] == 8  # a new model re-embeds everything
    assert search_index.status()["passages_embedded"] == 8


def test_without_a_key_nothing_is_sent_to_voyage():
    search_index.sync()
    result = search("downgrade")
    assert fake_embed.calls == []
    assert result["mode"] == "keyword" and result["results"]
    assert search_index.status()["meaning_search"] is False


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def test_keyword_search_matches_word_variations():
    search_index.sync()
    result = search("downgraded")  # stemming: matches "downgrade"
    top = result["results"][0]
    assert (top["session_date"], top["ticker"], top["matched_by"]) == ("2026-10-01", "NVDA", ["keywords"])
    assert top["text"].startswith("### NVDA")  # the passage itself, without the title line
    assert result["terms"] == ["downgraded"]


def test_search_filters_by_ticker_and_dates():
    search_index.sync()
    assert {r["session_date"] for r in search("shares OR results OR concerns")["results"]} >= {"2026-10-01", "2026-10-02", "2026-10-05"}
    assert [r["ticker"] for r in search("results", ticker="aapl")["results"]] == ["AAPL"]
    assert search("downgrade", since="2026-10-02")["results"] == []
    assert {r["session_date"] for r in search("AAPL", until="2026-10-02")["results"]} == {"2026-10-01", "2026-10-02"}


@pytest.mark.parametrize("query", ['NVDA\'s "earnings" (Q3) OR * -', "AND", "?!", "NEAR(a b)"])
def test_search_text_is_never_read_as_search_syntax(query):
    search_index.sync()
    search(query)  # no error


def test_meaning_search_finds_passages_without_the_same_words(voyage):
    search_index.sync()
    result = search("rating cut")  # shares no words with "An analyst downgrade weighed on the shares"
    top = result["results"][0]
    assert result["mode"] == "hybrid"
    assert (top["session_date"], top["matched_by"]) == ("2026-10-01", ["meaning"])  # no shared keywords
    assert fake_embed.calls[-1] == (1, "query")


def test_matches_on_both_keywords_and_meaning_rank_first(voyage):
    search_index.sync()
    top = search("regulatory probe")["results"][0]
    assert (top["ticker"], sorted(top["matched_by"])) == ("JPM", ["keywords", "meaning"])


def test_loosely_related_passages_are_left_out(voyage, monkeypatch):
    save("2026-10-07", "AMZN", "Earnings beat, though a regulator is watching.")  # only partly about regulation
    search_index.sync()

    def days_for(query):
        return [r["session_date"] for r in search(query)["results"] if "meaning" in r["matched_by"]]

    assert days_for("probe") == ["2026-10-05"]  # the clearly relevant passage only
    monkeypatch.setattr(search_index, "MEANING_CUTOFF", 0.5)
    assert set(days_for("probe")) == {"2026-10-05", "2026-10-07"}  # a lower cutoff lets the partial match in


def test_search_falls_back_to_keywords_if_voyage_fails(voyage, monkeypatch):
    search_index.sync()

    def unreachable(texts, input_type):
        raise ConnectionError("Voyage unreachable")

    monkeypatch.setattr(search_index, "embed", unreachable)
    result = search("downgrade")
    assert result["mode"] == "keyword" and "unavailable" in result["note"]
    assert result["results"][0]["session_date"] == "2026-10-01"


# ---------------------------------------------------------------------------
# The API, Ask and runs
# ---------------------------------------------------------------------------

def test_api_search_returns_passages_including_brand_new_reports():
    client = TestClient(api.app)
    data = client.get("/api/search?q=downgrade").json()
    assert data["results"][0]["session_date"] == "2026-10-01" and data["mode"] == "keyword"

    save("2026-10-07", "AMZN", "Reports of a large contract win.")
    assert client.get("/api/search?q=contract").json()["results"][0]["session_date"] == "2026-10-07"
    status = client.get("/api/search/status").json()
    assert status["reports_indexed"] == status["reports_total"] == 5


@pytest.mark.parametrize("query", ["", "?q=", "?q=x&since=yesterday", "?q=x&ticker=not%20one", "?q=x&limit=0",
                                   "?q=" + "x" * 501])
def test_api_search_rejects_bad_requests(query):
    response = TestClient(api.app).get("/api/search" + query)
    assert response.status_code == 400 and "error" in response.json()


def test_ask_retrieves_passages_from_older_reports():
    for day in range(8, 20):  # twelve newer reports push 1-5 October out of the "recent 10"
        save(f"2026-10-{day:02d}", "MSFT", "No clear catalyst found.")

    context, used = ask.gather("Were there any regulatory issues?")

    assert "2026-10-05" in used
    assert "## Passage from the report of 2026-10-05 (final): JPM" in context
    assert "Regulatory concerns were reported." in context


def test_runs_keep_the_search_index_current(monkeypatch):
    scan = {"session": {"status": "complete", "as_of": "2026-10-07"},
            "flagged": [{"ticker": "AMZN", "last_close": 180.0, "return_1d_pct": 3.0, "return_zscore": 2.4}],
            "quiet": [], "errors": []}
    title, body = brief("2026-10-07", "AMZN", "Reports of a large contract win.")
    messages = [AssistantMessage(content=[ToolUseBlock(id="t", name="mcp__market__flag_events", input={})], model="m"),
                UserMessage(content=[ToolResultBlock(tool_use_id="t", content=[{"type": "text", "text": json.dumps(scan)}])]),
                ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
                              session_id="s", total_cost_usd=0.03, result=body)]

    async def fake_query(*, prompt, options):
        for m in messages:
            yield m

    monkeypatch.setattr(run_brief, "market_session", lambda: scan["session"])
    monkeypatch.setattr(run_brief, "query", fake_query)
    events = []
    asyncio.run(run_brief.run_once(events.append))
    assert search("contract")["results"][0]["session_date"] == "2026-10-07"

    def broken_sync(**kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(search_index, "sync", broken_sync)
    monkeypatch.setattr(run_brief, "market_session", lambda: {"status": "in_progress", "as_of": "2026-10-08 11:00 ET"})
    scan["session"] = {"status": "in_progress", "as_of": "2026-10-08 11:00 ET"}
    messages[1] = UserMessage(content=[ToolResultBlock(tool_use_id="t", content=[{"type": "text", "text": json.dumps(scan)}])])
    events = []
    asyncio.run(run_brief.run_once(events.append))
    assert events[-1]["type"] == "warning" and "disk full" in events[-1]["message"]
    with closing(reports_db.connect(readonly=True)) as conn:
        assert reports_db.get_report(conn, "2026-10-08") is not None  # the report was still saved
