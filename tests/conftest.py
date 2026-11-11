"""Shared test setup: tests never reach real services, whatever is set in your terminal.

Without this, running pytest in a terminal where DISCORD_WEBHOOK_URL is set would post
test alerts to your real Discord channel (and VOYAGE_API_KEY would send test text to Voyage).
Tests that need these set them themselves.

A run that saves a final report also follows up on earlier flagged moves, which downloads
prices from Yahoo and can ask Claude about surprises. Tests skip that step, except the ones
in test_followups.py, which fake Yahoo and Claude themselves.
"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    for name in ("DISCORD_WEBHOOK_URL", "VOYAGE_API_KEY"):
        monkeypatch.delenv(name, raising=False)


@pytest.fixture(autouse=True)
def no_follow_up_after_runs(request, monkeypatch):
    if request.module.__name__.endswith("test_followups"):
        return
    import stories
    monkeypatch.setattr(stories, "after_final_report", lambda emit=None: {"followups": None, "checks": [], "problems": []})
