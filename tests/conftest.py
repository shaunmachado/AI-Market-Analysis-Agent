"""Shared test setup: tests never reach real services, whatever is set in your terminal.

Without this, running pytest in a terminal where DISCORD_WEBHOOK_URL is set would post
test alerts to your real Discord channel (and VOYAGE_API_KEY would send test text to Voyage).
Tests that need these set them themselves.
"""

import pytest


@pytest.fixture(autouse=True)
def no_real_services(monkeypatch):
    for name in ("DISCORD_WEBHOOK_URL", "VOYAGE_API_KEY"):
        monkeypatch.delenv(name, raising=False)
