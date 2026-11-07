"""Offline tests for Discord alerts. Nothing is sent to Discord: sending is faked.

Run from the project folder:
    pytest -v tests/test_alerts.py
"""

import asyncio
import io
import json
import sys
import urllib.error
from contextlib import closing
from datetime import timedelta
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import alerts  # noqa: E402
import api  # noqa: E402
import reports_db  # noqa: E402
import run_brief  # noqa: E402
from claude_agent_sdk import AssistantMessage, ResultMessage, ToolResultBlock, ToolUseBlock, UserMessage  # noqa: E402
from starlette.testclient import TestClient  # noqa: E402

WEBHOOK = "https://discord.com/api/webhooks/123/secret-token"
DAY = "2026-11-06"


def ticker(symbol, pct=-4.2, z=-3.1, volume=2.5, read="stock-specific"):
    return {"ticker": symbol, "last_price": 150.0, "return_1d_pct": pct, "return_5d_pct": -5.0,
            "return_zscore": z, "volume_vs_avg": volume, "compared_to": "test",
            "context": {"benchmark": "XLK", "benchmark_return_pct": -1.0, "market_return_pct": -0.5,
                        "vs_benchmark_pct": pct + 1.0, "vs_benchmark_zscore": -2.6, "read": read,
                        "summary": f"{symbol} fell; its sector (Technology, XLK) fell 1.00%. Looks specific to {symbol}."}}


def brief(title, flagged):
    lines = [f"# {title}", "", "## Market backdrop", "",
             "The S&P 500 fell 0.50% (z-score -0.9). Strongest sector: Energy (XLE) +0.80%; "
             "weakest: Technology (XLK) -1.00%.", "", "## Notable moves", ""]
    for t in flagged:
        lines += [f"### {t['ticker']}: {t['return_1d_pct']}% (z-score {t['return_zscore']}, volume {t['volume_vs_avg']}x normal)",
                  "- **What happened:** it moved.",
                  "- **Vs. sector and market:** see context.",
                  f"- **Likely why:** An analyst downgrade weighed on {t['ticker']}. [Reuters](https://example.com/{t['ticker']})",
                  "- **Worth watching:** the next session.", ""]
    lines += ["## Quiet", "", "AAPL (+0.30%)"]
    return "\n".join(lines)


def save(*flagged, status="intraday", at="10:30"):
    as_of = DAY if status == "final" else f"{DAY} {at} ET"
    title = f"Watchlist brief: {DAY}" if status == "final" else f"Intraday update: {as_of}"
    scan = {"session": {"status": "complete" if status == "final" else "in_progress", "as_of": as_of},
            "flagged": list(flagged), "quiet": [{"ticker": "AAPL", "return_1d_pct": 0.3}], "errors": []}
    with closing(reports_db.connect()) as conn:
        return reports_db.save_report(conn, session_date=DAY, status=status, title=title,
                                      body_md=brief(title, flagged), as_of=as_of, scan=scan)


def logged():
    with closing(alerts.connect()) as conn:
        return alerts.recent(conn, 100)


@pytest.fixture
def sent(tmp_path, monkeypatch):
    """A temporary database, a webhook in the environment, and fake sending. Returns what was 'sent'."""
    monkeypatch.setattr(reports_db, "DB_PATH", tmp_path / "reports.db")
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    messages = []
    monkeypatch.setattr(alerts, "send", lambda payload: messages.append(payload) or "1")
    return messages


def titles(message):
    return [e["title"] for e in message["embeds"]]


# ---------------------------------------------------------------------------
# Turning alerts on
# ---------------------------------------------------------------------------

def test_no_webhook_means_nothing_is_sent(sent, monkeypatch):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL")
    save(ticker("NVDA"))

    assert alerts.notify(DAY) == {"enabled": False, "sent": [], "failed": []}
    assert sent == []


def test_webhook_must_be_a_discord_address(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", "https://example.com/collect")

    assert not alerts.enabled()
    with pytest.raises(ValueError, match="Discord webhook"):
        alerts.webhook_url()


# ---------------------------------------------------------------------------
# Flag alerts while the market is open
# ---------------------------------------------------------------------------

def test_a_newly_flagged_ticker_alerts_once_per_day(sent):
    save(ticker("NVDA"), at="10:30")
    first = alerts.notify(DAY)
    save(ticker("NVDA", z=-3.3), at="10:45")              # still flagged, a little bigger
    second = alerts.notify(DAY)
    save(ticker("NVDA", z=-3.4), ticker("JPM", pct=3.1, z=2.8), at="11:00")
    third = alerts.notify(DAY)

    assert first["sent"] == ["flag alert: NVDA"] and second["sent"] == [] and third["sent"] == ["flag alert: JPM"]
    assert [titles(m) for m in sent] == [["NVDA -4.20% so far today"], ["JPM +3.10% so far today"]]
    assert sent[0]["content"] == "**1 new flag** in the intraday update as of 10:30 ET"


def test_a_much_bigger_move_alerts_again(sent):
    save(ticker("NVDA", pct=-4.2, z=-3.0), at="10:30")
    alerts.notify(DAY)
    save(ticker("NVDA", pct=-6.9, z=-4.6), at="12:30")    # |z| grew by 1.6
    alerts.notify(DAY)

    assert titles(sent[1]) == ["Bigger move: NVDA -6.90% so far today"]
    assert "Was -4.20% at 10:30 ET" in sent[1]["embeds"][0]["description"]
    assert sent[1]["content"] == "**1 bigger move** in the intraday update as of 12:30 ET"


def test_a_reversal_alerts_again(sent):
    save(ticker("NVDA", pct=4.0, z=3.0), at="10:30")
    alerts.notify(DAY)
    save(ticker("NVDA", pct=-3.5, z=-2.6), at="14:00")
    alerts.notify(DAY)

    assert titles(sent[1]) == ["Reversal: NVDA -3.50% so far today"]


def test_volume_only_flag_alerts_once(sent):
    save(ticker("JPM", pct=0.2, z=0.4, volume=3.0, read="in line"), at="10:30")
    alerts.notify(DAY)
    save(ticker("JPM", pct=0.3, z=0.6, volume=4.5, read="in line"), at="11:30")
    alerts.notify(DAY)

    assert len(sent) == 1


def test_flag_alert_shows_context_and_the_agents_explanation(sent):
    save(ticker("NVDA"))
    alerts.notify(DAY)
    embed = sent[0]["embeds"][0]

    assert "z-score -3.1 · volume 2.5x normal for this time of day" in embed["description"]
    assert "**Vs. sector and market:** NVDA fell; its sector (Technology, XLK) fell 1.00%." in embed["description"]
    assert ("**Likely why:** An analyst downgrade weighed on NVDA. [Reuters](https://example.com/NVDA)"
            in embed["description"])
    assert embed["color"] == alerts.COLORS["down"]
    assert embed["footer"]["text"] == "As of 2026-11-06 10:30 ET · research, not investment advice"


def test_many_flags_fit_in_one_message_within_discords_limits(sent):
    many = [ticker(f"T{i:02d}") for i in range(14)]
    for t in many:
        t["context"]["summary"] = "x" * 1500
    save(*many)
    alerts.notify(DAY)
    message = sent[0]

    assert len(sent) == 1 and len(message["embeds"]) == alerts.MAX_EMBEDS
    assert "showing 10" in message["content"]
    total = sum(len(e["title"]) + len(e["description"]) + len(e["footer"]["text"]) for e in message["embeds"])
    assert total <= alerts.MAX_TOTAL
    assert all(len(e["description"]) <= alerts.MAX_DESCRIPTION for e in message["embeds"])
    assert len(logged()) == 14  # every flagged ticker counts as alerted


# ---------------------------------------------------------------------------
# The end-of-day summary
# ---------------------------------------------------------------------------

def test_final_report_sends_one_summary(sent):
    save(ticker("NVDA"), status="final")
    first = alerts.notify(DAY)
    again = alerts.notify(DAY)

    assert first["sent"] == [f"daily summary for {DAY}"] and again["sent"] == []
    embed = sent[0]["embeds"][0]
    assert sent[0]["content"] == "**Daily summary:** 1 flagged move"
    assert embed["title"] == f"Watchlist brief: {DAY}"
    assert embed["description"].startswith("**Market:** The S&P 500 fell 0.50%")
    assert "**NVDA** -4.20% (z-score -3.1) · stock-specific\nAn analyst downgrade weighed on NVDA." in embed["description"]
    assert "**Quiet:** AAPL +0.30%" in embed["description"]


def test_quiet_day_summary(sent):
    save(status="final")
    alerts.notify(DAY)

    assert sent[0]["content"] == "**Daily summary:** 0 flagged moves"
    assert "Nothing unusual today." in sent[0]["embeds"][0]["description"]


def test_final_report_sends_no_flag_alerts(sent):
    save(ticker("NVDA"), ticker("JPM", pct=3.0, z=2.9), status="final")
    alerts.notify(DAY)

    assert len(sent) == 1 and sent[0]["content"].startswith("**Daily summary:**")


# ---------------------------------------------------------------------------
# Failures and retries
# ---------------------------------------------------------------------------

def test_a_failed_alert_is_logged_and_retried_next_run(sent, monkeypatch):
    def broken(payload):
        raise alerts.SendError("couldn't reach Discord (timed out)")

    save(ticker("NVDA"))
    monkeypatch.setattr(alerts, "send", broken)
    failed = alerts.notify(DAY)
    monkeypatch.setattr(alerts, "send", lambda payload: sent.append(payload))
    retried = alerts.notify(DAY)

    assert failed["failed"] == ["flag alert: NVDA (couldn't reach Discord (timed out))"]
    assert retried["sent"] == ["flag alert: NVDA"]
    statuses = [(a["status"], a["error"]) for a in logged()]
    assert statuses == [("sent", None), ("failed", "couldn't reach Discord (timed out)")]


def test_an_alert_being_sent_by_another_run_is_not_doubled(sent, monkeypatch):
    save(ticker("NVDA"))
    with closing(alerts.connect()) as conn:  # another run has claimed NVDA, and is sending right now
        conn.execute("""INSERT INTO alerts (session_date, kind, ticker, return_1d_pct, return_zscore, as_of, status,
                        created_at) VALUES (?, 'flag', 'NVDA', -4.2, -3.1, ?, 'pending', ?)""",
                     (DAY, f"{DAY} 10:30 ET", alerts._stamp(alerts._utc_now())))
    assert alerts.notify(DAY)["sent"] == []

    # A claim left behind by a run that crashed counts as unsent after a while
    later = alerts._utc_now() + timedelta(seconds=alerts.PENDING_SECONDS + 1)
    monkeypatch.setattr(alerts, "_utc_now", lambda: later)
    assert alerts.notify(DAY)["sent"] == ["flag alert: NVDA"]


# ---------------------------------------------------------------------------
# Sending to Discord (the network is faked)
# ---------------------------------------------------------------------------

class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def http_error(code, body):
    return urllib.error.HTTPError(WEBHOOK, code, "error", {}, io.BytesIO(json.dumps(body).encode()))


def test_post_sends_safe_json_to_the_webhook(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse(b'{"id": "998877"}')

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)

    assert alerts.post({"content": "hello @everyone"}) == "998877"
    request = requests[0]
    body = json.loads(request.data)
    assert request.full_url == WEBHOOK + "?wait=true"
    assert request.get_header("Content-type") == "application/json"
    assert request.get_header("User-agent") == "market-agent-alerts/1.0"
    assert body == {"username": "Market Analyst", "allowed_mentions": {"parse": []}, "content": "hello @everyone"}


def test_post_waits_and_retries_once_when_rate_limited(monkeypatch):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)
    replies = [http_error(429, {"message": "You are being rate limited.", "retry_after": 0.25}),
               FakeResponse(b'{"id": "1"}')]
    waits = []

    def fake_urlopen(request, timeout):
        reply = replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return reply

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)
    monkeypatch.setattr(alerts.time, "sleep", waits.append)

    assert alerts.post({"content": "x"}) == "1"
    assert waits == [0.25]


@pytest.mark.parametrize("error, expected", [
    (http_error(404, {"message": "Unknown Webhook"}), "doesn't exist"),
    (http_error(400, {"message": "Invalid Form Body"}), "refused the message (400)"),
    (urllib.error.URLError("timed out"), "couldn't reach Discord"),
])
def test_post_errors_are_clear_and_never_show_the_webhook(monkeypatch, error, expected):
    monkeypatch.setenv("DISCORD_WEBHOOK_URL", WEBHOOK)

    def fake_urlopen(request, timeout):
        raise error

    monkeypatch.setattr(alerts.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(alerts.SendError) as caught:
        alerts.post({"content": "x"})

    assert expected in str(caught.value)
    assert "secret-token" not in str(caught.value)


# ---------------------------------------------------------------------------
# Runs, the API and the command line
# ---------------------------------------------------------------------------

def fake_agent(monkeypatch, session, flagged):
    monkeypatch.setattr(run_brief, "market_session", lambda: session)
    scan = {"session": session, "flagged": flagged, "quiet": [], "errors": []}
    title = f"Intraday update: {session['as_of']}" if session["status"] == "in_progress" else f"Watchlist brief: {DAY}"

    async def query(*, prompt, options):
        yield AssistantMessage(content=[ToolUseBlock(id="t1", name="mcp__market__flag_events", input={})], model="m")
        yield UserMessage(content=[ToolResultBlock(tool_use_id="t1", content=[{"type": "text", "text": json.dumps(scan)}])])
        yield ResultMessage(subtype="success", duration_ms=1, duration_api_ms=1, is_error=False, num_turns=2,
                            session_id="s", total_cost_usd=0.01, result=brief(title, flagged))

    monkeypatch.setattr(run_brief, "query", query)


def test_a_run_sends_alerts_after_saving(sent, monkeypatch):
    fake_agent(monkeypatch, {"status": "in_progress", "as_of": f"{DAY} 10:30 ET"}, [ticker("NVDA")])
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "saved"
    assert {"type": "alert", "message": "Discord: sent flag alert: NVDA"} in events
    assert titles(sent[0]) == ["NVDA -4.20% so far today"]


def test_alert_problems_never_fail_a_run(sent, monkeypatch):
    fake_agent(monkeypatch, {"status": "in_progress", "as_of": f"{DAY} 10:30 ET"}, [ticker("NVDA")])

    def broken(payload):
        raise alerts.SendError("Discord refused the message (400): bad")

    monkeypatch.setattr(alerts, "send", broken)
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "saved"
    assert any(e["type"] == "warning" and "Discord alert failed" in e["message"] for e in events)


def test_a_skipped_run_retries_a_summary_that_failed(sent, monkeypatch):
    save(ticker("NVDA"), status="final")
    with closing(alerts.connect()) as conn:
        conn.execute("""INSERT INTO alerts (session_date, kind, status, error, created_at)
                        VALUES (?, 'summary', 'failed', 'timed out', '2026-11-06T21:31:00Z')""", (DAY,))
    fake_agent(monkeypatch, {"status": "complete", "as_of": DAY}, [ticker("NVDA")])
    events = []

    result = asyncio.run(run_brief.run_once(events.append))

    assert result["type"] == "skipped"  # Claude isn't called again...
    assert {"type": "alert", "message": f"Discord: sent daily summary for {DAY}"} in events  # ...but the summary goes out


def test_api_shows_alert_status(sent):
    with TestClient(api.app) as client:
        empty = client.get("/api/alerts").json()   # before any alert has been sent
        save(ticker("NVDA"))
        alerts.notify(DAY)
        after = client.get("/api/alerts").json()

    assert empty == {"enabled": True, "alerts": []}
    assert after["alerts"][0]["ticker"] == "NVDA" and after["alerts"][0]["status"] == "sent"


def test_preview_shows_messages_without_sending(sent, monkeypatch, capsys):
    monkeypatch.delenv("DISCORD_WEBHOOK_URL")  # works before alerts are set up
    save(ticker("NVDA"))
    monkeypatch.setattr(sys, "argv", ["alerts.py", "preview"])

    alerts.main()

    preview = json.loads(capsys.readouterr().out)
    assert titles(preview[0]) == ["NVDA -4.20% so far today"]
    assert sent == [] and logged() == []
