"""Offline tests for follow-through (the price after each flagged move) and story updates (the
news since). Yahoo Finance and Claude are faked.

Run from the project folder:
    pytest -v tests/test_followups.py
"""

import asyncio
import json
import sys
import time
from contextlib import closing
from datetime import date, timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import api  # noqa: E402
import ask  # noqa: E402
import events  # noqa: E402
import followups  # noqa: E402
import market_tools  # noqa: E402
import prices  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
import stories  # noqa: E402
from claude_agent_sdk import ResultMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

# Trading days (weekdays) from September to December 2026
DAYS = [date(2026, 9, 1) + timedelta(days=i) for i in range(120) if (date(2026, 9, 1) + timedelta(days=i)).weekday() < 5]
D0 = date(2026, 10, 1)  # the flagged day
I0 = DAYS.index(D0)
PRICES = {}             # ticker -> {day: close}
CLAUDE = []             # every prompt the fake Claude was sent
NEWS = {}               # ticker -> headlines the fake Yahoo returns


def path(ticker, base, moves):
    """Closes: `base` until the flagged day, then the given closes from D0 onwards."""
    closes = {d: base for d in DAYS[:I0]}
    closes.update({DAYS[I0 + i]: c for i, c in enumerate(moves)})
    last = moves[-1]
    closes.update({d: last for d in DAYS[I0 + len(moves):]})
    PRICES[ticker] = closes


def body(*sections):
    lines = ["# Watchlist brief", "", "## Notable moves", ""]
    for ticker, why in sections:
        lines += [f"### {ticker}: +1.00% (z-score 3, volume 2x normal)", "- **What happened:** it moved.",
                  f"- **Likely why:** {why}", "- **Worth watching:** more.", ""]
    return "\n".join(lines + ["## Quiet", "", "AAPL (+0.10%)"])


def save(day, status, flagged, why=None, sources=()):
    """A report for `day` with these flagged moves: [(ticker, move %, kind)]."""
    scan = {"session": {"status": "complete", "as_of": day.isoformat()},
            "flagged": [{"ticker": t, "last_close": 100.0, "return_1d_pct": m, "return_zscore": 3.0, "volume_vs_avg": 2.0,
                         "context": {"read": k, "benchmark": "XLK", "summary": "..."}} for t, m, k in flagged],
            "quiet": [{"ticker": "AAPL", "last_close": 190.0, "return_1d_pct": 0.1}], "errors": []}
    with closing(reports_db.connect()) as conn:
        reports_db.save_report(conn, session_date=day.isoformat(), status=status, title="Brief",
                               body_md=body(*[(t, (why or {}).get(t, "No clear catalyst found.")) for t, _, _ in flagged]),
                               as_of=day.isoformat(), scan=scan, sources=list(sources))


def fake_claude(reply):
    def ask_claude(prompt):
        CLAUDE.append(prompt)
        if isinstance(reply, Exception):
            raise reply
        return (reply if isinstance(reply, str) else json.dumps(reply)), 0.012
    return ask_claude


@pytest.fixture
def db(tmp_path, monkeypatch):
    """A temporary database, a fixed 'latest close', fake Yahoo prices and news, and fake Claude."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    PRICES.clear()
    CLAUDE.clear()
    NEWS.clear()
    path("NVDA", 100.0, [110.0, 111.0, 109.0, 106.0, 105.0, 104.5] + [100.0] * 20)  # +10%, then faded, then reversed
    path("MSFT", 200.0, [190.0, 189.0, 186.0, 184.0, 182.0, 180.0])                # -5%, then kept going down
    clock = {"last": DAYS[I0 + 25]}
    monkeypatch.setattr(followups, "last_complete_session", lambda: clock["last"])
    monkeypatch.setattr(prices, "fetch_prices", lambda t, period: [
        {"date": d.isoformat(), "close": c, "volume": 1000} for d, c in sorted(PRICES[t].items())])
    monkeypatch.setattr(stories, "fetch_news", lambda t: NEWS.get(t, []))
    monkeypatch.setattr(stories, "ask_claude", fake_claude({"verdict": "developed", "update": "On Oct 5 it said more.",
                                                             "sources": [1]}))
    monkeypatch.setattr(events, "company_name", lambda t: {"NVDA": "NVIDIA", "MSFT": "Microsoft"}.get(t, t))
    reports_db.connect().close()
    return clock


def rows(conn=None):
    with closing(reports_db.connect(readonly=True)) as c:
        return {r["ticker"]: dict(r) for r in c.execute("SELECT * FROM followups WHERE session_date = ?", (D0.isoformat(),))}


# ---------------------------------------------------------------------------
# Judging a move
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("move, after, expected", [
    (10, 3.0, "held"),        # kept going
    (10, -2.0, "held"),       # gave back 22% of the move
    (10, -5.0, "faded"),      # gave back 55%
    (10, -9.1, "reversed"),   # back below where it started
    (-10, 5.0, "faded"),
    (-10, 11.2, "reversed"),
    (4, None, None),          # not known yet
])
def test_judging_a_move(move, after, expected):
    assert followups.outcome(move, after) == expected


def test_surprises_are_reversals_or_doubling_within_a_week():
    assert followups.is_surprise(10, -9.1) and followups.surprise_kind(10, -9.1) == "reversed within a week"
    assert followups.is_surprise(-5, -5.3)  # down 5%, then as much again
    assert followups.surprise_kind(-5, -5.3) == "kept going: as much again within a week"
    assert not followups.is_surprise(10, -5.0) and not followups.is_surprise(10, None)
    assert followups.follow(-5, -5.3) == 5.3  # counted in the move's direction


# ---------------------------------------------------------------------------
# Finding the moves and filling in prices
# ---------------------------------------------------------------------------

def test_follow_ups_come_from_final_reports_only(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")],
         why={"NVDA": "Quarterly results beat estimates. [Reuters](https://x.example)"})
    save(DAYS[I0 + 26], "intraday", [("NVDA", 4.0, "stock-specific")])  # today's flags aren't followed up yet

    result = followups.update()

    found = rows()
    assert result["added"] == 2 and set(found) == {"NVDA", "MSFT"}
    assert found["NVDA"]["reason"] == "earnings" and found["NVDA"]["why"] == "Quarterly results beat estimates. Reuters"
    assert found["MSFT"]["reason"] == "none" and found["MSFT"]["move_read"] == "market-wide"
    with closing(reports_db.connect(readonly=True)) as conn:
        assert conn.execute("SELECT COUNT(*) FROM followups").fetchone()[0] == 2


def test_earnings_on_the_calendar_count_as_the_reason(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")], why={"NVDA": "No clear catalyst found."})
    with closing(events.connect()) as conn:
        conn.execute("""INSERT INTO events (event_date, ticker, company, kind, title, first_seen, last_seen)
                        VALUES (?, 'NVDA', 'NVIDIA', 'earnings', 'Earnings report', '2026-09-01', '2026-09-01')""",
                     ((D0 - timedelta(days=1)).isoformat(),))
    followups.update()
    assert rows()["NVDA"]["reason"] == "earnings"  # reported the evening before


def test_prices_fill_in_as_days_pass(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    db["last"] = DAYS[I0 + 3]  # three closes since the move

    followups.update()
    first = rows()["NVDA"]
    db["last"] = DAYS[I0 + 25]
    second = followups.update()
    settled = rows()["NVDA"]
    again = followups.update()

    assert first["after_1d"] == 0.91 and first["after_5d"] is None and first["after_20d"] is None
    assert settled["after_5d"] == -5.0 and settled["after_20d"] == -9.09
    assert followups.outcome(10, settled["after_5d"]) == "faded" and followups.outcome(10, settled["after_20d"]) == "reversed"
    assert second["updated"] == 1 and again["updated"] == 0  # settled moves aren't downloaded again


def test_todays_unfinished_price_is_never_used(monkeypatch):
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "in_progress", "as_of": "2026-11-06 11:30 ET"})
    assert followups.last_complete_session() == date(2026, 11, 5)
    monkeypatch.setattr(market_tools, "market_session", lambda: {"status": "complete", "as_of": "2026-11-06"})
    assert followups.last_complete_session() == date(2026, 11, 6)


def test_a_price_problem_for_one_stock_doesnt_stop_the_rest(db, monkeypatch):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")])
    real = prices.fetch_prices
    monkeypatch.setattr(prices, "fetch_prices", lambda t, p: (_ for _ in ()).throw(ConnectionError("rate limited"))
                        if t == "NVDA" else real(t, p))
    result = followups.update()
    assert result["status"] == "partial" and "NVDA: rate limited" in result["message"]
    assert rows()["MSFT"]["after_5d"] == -5.26 and rows()["NVDA"]["after_5d"] is None


def test_a_broken_price_for_one_stock_doesnt_stop_the_rest(db, monkeypatch):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")])
    PRICES["MSFT"][D0] = 0.0  # Yahoo sometimes has a 0 close
    result = followups.update()
    assert result["status"] == "ok" and result["updated"] == 1
    assert rows()["NVDA"]["after_1d"] is not None and rows()["MSFT"]["note"] == "no Yahoo price for that day"

    real = followups.is_surprise

    def fails_for_drops(move, after):
        if move < 0:
            raise RuntimeError("boom")
        return real(move, after)
    monkeypatch.setattr(followups, "is_surprise", fails_for_drops)
    PRICES["MSFT"][D0] = 190.0
    result = followups.update()
    assert result["status"] == "partial" and "MSFT: boom" in result["message"]  # contained, and the update is logged


def test_patterns_group_the_moves(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    followups.update()
    with closing(reports_db.connect(readonly=True)) as conn:
        result = followups.patterns(followups.moves(conn), 5)
    assert result["all"]["judged"] == 2 and (result["all"]["held"], result["all"]["faded"]) == (1, 1)
    assert [g["label"] for g in result["by_kind"]] == ["Stock-specific"]
    assert [g["label"] for g in result["by_direction"]] == ["Up moves", "Down moves"]
    assert not result["all"]["enough"]  # 2 moves: too few to tell
    assert followups.describe_group(result["all"], 5) == \
        "All flagged moves: 1 of 2 held a week later, 1 faded, 0 reversed (too few to tell)"


def test_past_moves_tool_for_the_brief(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    followups.update()

    result = market_tools.past_moves(["nvda"], ["stock-specific"])

    nvda = result["moves"]["NVDA"]
    assert result["horizon_days"] == 5 and nvda["this_stock"]["judged"] == 1
    assert nvda["same_kind"]["judged"] == 2 and nvda["last_move"]["outcome"] == "faded"
    assert nvda["summary"].startswith("NVDA's flagged moves: 0 of 1 held a week later, 1 faded")
    assert nvda["worth_mentioning"] is False  # too few to mention in a brief


def test_past_moves_without_any_history(db):
    assert market_tools.past_moves(["NVDA"])["note"].startswith("Follow-through hasn't been worked out yet")


# ---------------------------------------------------------------------------
# Story updates
# ---------------------------------------------------------------------------

def test_no_newer_headlines_means_no_claude_and_no_cost(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    followups.update()
    NEWS["NVDA"] = [{"title": "On the day", "publisher": "Wire", "published": f"{D0}T13:00:00Z", "url": "https://a.example"}]

    check = stories.check(D0.isoformat(), "NVDA")

    assert check["status"] == "no_news" and check["cost_usd"] == 0 and CLAUDE == []
    assert check["update_text"] == "No newer headlines about NVIDIA since 2026-10-01."


def test_a_check_reads_only_newer_headlines(db):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")], why={"NVDA": "A product launch."},
         sources=[{"ticker": "NVDA", "title": "NVIDIA unveils chip", "publisher": "Wire", "url": "https://a.example"}])
    followups.update()
    NEWS["NVDA"] = [
        {"title": "Chip reviews arrive", "publisher": "Daily", "published": "2026-10-05T12:00:00Z", "url": "https://b.example"},
        {"title": "Same-day story", "publisher": "Wire", "published": f"{D0}T15:00:00Z", "url": "https://c.example"},
        {"title": "Older story", "publisher": "Wire", "published": 1790000000, "url": "https://d.example"},  # Sep 2026, as seconds
    ]

    check = stories.check(D0.isoformat(), "nvda", emit=lambda e: None)

    assert check["status"] == "ok" and check["verdict"] == "developed" and check["cost_usd"] == 0.012
    assert check["sources"] == [{"title": "Chip reviews arrive", "publisher": "Daily", "url": "https://b.example",
                                 "published": "2026-10-05T12:00:00Z"}]
    prompt = CLAUDE[0]
    assert "EXPLANATION AT THE TIME: A product launch." in prompt and "- NVIDIA unveils chip (Wire)" in prompt
    assert "PRICE SINCE: next day: +0.91%, after a week: -5.00%, after a month: -9.09%" in prompt
    assert "Chip reviews arrive" in prompt and "Same-day story" not in prompt and "Older story" not in prompt


@pytest.mark.parametrize("reply, error", [
    ("Sorry, I can't.", "no JSON"),
    ({"verdict": "maybe", "update": "x", "sources": [1]}, "unknown verdict"),
    ({"verdict": "developed", "update": "x", "sources": [7]}, "cited none of the newer headlines"),
    ({"verdict": "developed", "update": "x", "sources": [True]}, "cited none of the newer headlines"),
    (RuntimeError("error_max_budget_usd"), "error_max_budget_usd"),
])
def test_a_bad_reply_is_saved_as_a_failed_check(db, monkeypatch, reply, error):
    save(D0, "final", [("NVDA", 10.0, "stock-specific")])
    followups.update()
    NEWS["NVDA"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    monkeypatch.setattr(stories, "ask_claude", fake_claude(reply))
    check = stories.check(D0.isoformat(), "NVDA")
    assert check["status"] == "failed" and error in check["error"]


def test_only_flagged_moves_can_be_checked(db):
    with pytest.raises(stories.StoryError, match="wasn't flagged") as missing:
        stories.check("2026-10-02", "NVDA")
    assert missing.value.status == 404


def test_surprises_are_checked_once_after_a_final_report(db):
    db["last"] = DAYS[I0 + 10]  # two weeks after the move
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    progress = []

    first = stories.after_final_report(progress.append)
    second = stories.after_final_report(progress.append)

    assert first["followups"]["new_surprises"] == 1  # MSFT fell as much again within a week
    assert [(c["ticker"], c["trigger"], c["status"]) for c in first["checks"]] == [("MSFT", "surprise", "ok")]
    assert second["checks"] == []  # checked once only
    messages = [e["message"] for e in progress]
    assert "Follow-through: 2 new moves, 2 updated, 1 new surprise" in messages
    assert "Story updates: checked 1 surprise · $0.012" in messages


def test_older_surprises_are_left_to_check_by_hand(db):
    save(D0, "final", [("MSFT", -5.0, "stock-specific")])  # 5 weeks before the latest close
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]

    result = stories.after_final_report()

    assert result["followups"]["new_surprises"] == 1 and result["checks"] == []
    assert CLAUDE == []  # no money spent on old news
    assert stories.check(D0.isoformat(), "MSFT")["status"] == "ok"  # it can still be checked on request
    assert stories.check_surprises(within_days=60)[0]["trigger"] == "surprise"


def test_after_final_report_never_breaks_the_run(db, monkeypatch):
    monkeypatch.setattr(followups, "update", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("disk full")))
    progress = []
    result = stories.after_final_report(progress.append)
    assert result["problems"] == ["follow-through: disk full"]
    assert progress[-1]["type"] == "warning" and "disk full" in progress[-1]["message"]


def test_a_final_run_follows_up_and_an_intraday_run_doesnt(db, monkeypatch):
    calls = []
    monkeypatch.setattr(stories, "after_final_report", lambda emit=None: calls.append(1))
    monkeypatch.setattr(run_brief, "send_alerts", lambda *a, **k: asyncio.sleep(0))
    monkeypatch.setattr(run_brief.search_index, "sync", lambda *a, **k: None)
    scan = {"flagged": [], "quiet": [{"ticker": "AAPL", "last_close": 1.0, "return_1d_pct": 0.1}], "errors": []}

    async def fake_query(*, prompt, options):
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=1,
                            session_id="s", total_cost_usd=0.01, result="# Brief\n\nNothing unusual.")

    monkeypatch.setattr(run_brief, "query", fake_query)
    for session in ({"status": "in_progress", "as_of": "2026-11-06 11:30 ET"}, {"status": "complete", "as_of": "2026-11-06"}):
        monkeypatch.setattr(run_brief, "market_session", lambda s=session: s)
        monkeypatch.setattr(run_brief, "flag_events", lambda s=session: {**scan, "session": s})
        asyncio.run(run_brief.run_once())
    assert calls == [1]  # once, after the final report


# ---------------------------------------------------------------------------
# Ask
# ---------------------------------------------------------------------------

def test_ask_sees_follow_through_and_story_updates(db):
    db["last"] = DAYS[I0 + 10]
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    stories.after_final_report()

    with closing(reports_db.connect(readonly=True)) as conn:
        named = ask.followup_section(conn, ["MSFT"])
        general = ask.followup_section(conn, [])
        context, _ = ask.build_context(conn, "What happened after MSFT dropped?")

    assert named in context  # Claude is actually given it

    assert "## Follow-through for MSFT" in named and "2026-10-01 | -5.00 | Stock-specific | No clear reason |" in named
    assert "| held" in named
    assert "## Story updates for MSFT" in named and "Developed. On Oct 5 it said more. Sources: Daily: Later" in named
    assert "All flagged moves: 1 of 2 held a week later" in general
    assert "(follow-through)" in ask.SYSTEM_PROMPT and "(story update" in ask.SYSTEM_PROMPT


# ---------------------------------------------------------------------------
# The API
# ---------------------------------------------------------------------------

@pytest.fixture
def client(db, monkeypatch):
    monkeypatch.setattr(api, "hub", api.EventHub())
    monkeypatch.setattr(api, "followup_refreshes", api.BackgroundJob(
        "followups_refresh", lambda: 60, "busy", "Prices were just refreshed. Try again in {}."))
    monkeypatch.setattr(api, "story_checks", api.BackgroundJob(
        "story_check", lambda: 60, "busy", "A story was just checked. Try again in {}."))
    monkeypatch.setattr(events, "today_et", lambda: D0 + timedelta(days=20))  # moves of the last 30 days can be checked
    save(D0, "final", [("NVDA", 10.0, "stock-specific"), ("MSFT", -5.0, "market-wide")])
    with TestClient(api.app) as test_client:
        yield test_client


def wait_for(check, timeout=5.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if value := check():
            return value
        time.sleep(0.05)
    raise AssertionError("timed out waiting")


def test_api_refresh_and_follow_through(client):
    assert client.get("/api/followups").json()["moves"] == []  # nothing worked out yet

    started = client.post("/api/followups/refresh", json={})
    assert started.status_code == 202 and started.json()["refresh"]["state"] == "running"
    wait_for(lambda: client.get("/api/followups").json()["refresh"]["state"] == "finished")
    assert client.post("/api/followups/refresh", json={}).status_code == 429  # cooldown

    view = client.get("/api/followups?horizon=20").json()
    assert view["horizon"] == 20 and view["horizons"] == [1, 5, 20] and view["tickers"] == ["MSFT", "NVDA"]
    nvda = next(m for m in view["moves"] if m["ticker"] == "NVDA")
    assert nvda["outcomes"] == {"1": "held", "5": "faded", "20": "reversed"} and nvda["settled"]
    assert view["patterns"]["horizon"] == 20 and view["updated"]["trigger"] == "manual"
    only = client.get("/api/followups?ticker=msft").json()
    assert [m["ticker"] for m in only["moves"]] == ["MSFT"] and only["patterns"]["all"]["moves"] == 2
    assert client.get("/api/followups?horizon=7").status_code == 400


def test_api_story_check(client):
    followups.update()
    NEWS["NVDA"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]
    queue = api.hub.subscribe()
    before = client.get("/api/stories").json()
    assert [m["ticker"] for m in before["unchecked"]] == ["MSFT", "NVDA"] and before["max_cost_usd"] == 0.1

    started = client.post("/api/stories/check", json={"session_date": D0.isoformat(), "ticker": "nvda"})
    assert started.status_code == 202 and started.json()["check"]["target"] == {"session_date": "2026-10-01", "ticker": "NVDA"}
    done = wait_for(lambda: (c := client.get("/api/stories").json())["check"]["state"] == "finished" and c)

    assert done["checks"][0]["ticker"] == "NVDA" and done["checks"][0]["verdict_label"] == "Developed"
    assert done["checks"][0]["move"]["outcomes"]["5"] == "faded"
    assert [m["ticker"] for m in done["unchecked"]] == ["MSFT"]
    assert next(m for m in client.get("/api/followups").json()["moves"] if m["ticker"] == "NVDA")["story"]["verdict"] == "developed"
    kinds = []
    while not queue.empty():
        kinds.append(queue.get_nowait()["type"])
    assert kinds.count("story_check") >= 2  # started, progress, finished
    assert client.post("/api/stories/check", json={"session_date": D0.isoformat(), "ticker": "MSFT"}).status_code == 429


@pytest.mark.parametrize("body, status, message", [
    ({"session_date": "2026-10-02", "ticker": "NVDA"}, 404, "wasn't flagged"),
    ({"session_date": "Oct 1", "ticker": "NVDA"}, 400, "send JSON like"),
    ({"ticker": "NVDA"}, 400, "send JSON like"),
])
def test_api_story_check_explains_what_went_wrong(client, body, status, message):
    followups.update()
    response = client.post("/api/stories/check", json=body)
    assert response.status_code == status and message in response.json()["error"]


def test_other_websites_cannot_start_checks(client):
    for path, body in (("/api/followups/refresh", {}), ("/api/stories/check", {"session_date": "2026-10-01", "ticker": "NVDA"})):
        assert client.post(path, json=body, headers={"Origin": "https://evil.example"}).status_code == 403
    assert CLAUDE == []


def test_updates_from_scheduled_runs_reach_open_pages(db, monkeypatch):
    monkeypatch.setattr(api, "POLL_SECONDS", 0.05)
    monkeypatch.setattr(api, "hub", api.EventHub())
    db["last"] = DAYS[I0 + 10]
    save(D0, "final", [("MSFT", -5.0, "stock-specific")])
    NEWS["MSFT"] = [{"title": "Later", "publisher": "Daily", "published": "2026-10-05", "url": "https://b.example"}]

    async def scenario():
        queue = api.hub.subscribe()
        watcher = asyncio.create_task(api.watch_reports())
        await asyncio.sleep(0.3)
        await asyncio.to_thread(stories.after_final_report)  # what another program (a scheduled run) does
        seen = set()
        deadline = time.monotonic() + 3
        while not {"followups_updated", "story_checked"} <= seen and time.monotonic() < deadline:
            try:
                seen.add((await asyncio.wait_for(queue.get(), 0.5))["type"])
            except asyncio.TimeoutError:
                pass
        watcher.cancel()
        return seen

    assert {"followups_updated", "story_checked"} <= asyncio.run(scenario())
