"""Missing-access contract test: no mocked API responses or operational records."""

import asyncio
from types import SimpleNamespace

import httpx

from app.integrations.n8n import N8nClient
from app.investigation.comparisons import collect_comparisons


def test_unconfigured_history_is_explicitly_incomplete_without_inventing_facts():
    async def check():
        async with httpx.AsyncClient(trust_env=False) as http:
            client = N8nClient(http, "http://127.0.0.1:5678", "")
            bundle = {"facts": [], "limits": []}
            await collect_comparisons(client, SimpleNamespace(id="contract"), bundle, {})
            assert bundle["facts"] == []
            assert bundle["comparison_scope"]["status"] == "incomplete"
            assert bundle["comparison_scope"]["included"] == 0
            assert bundle["comparison_scope"]["complete_history"] is False
            assert any("unavailable" in note for note in bundle["limits"])

    asyncio.run(check())
