"""Optional read-only verification against one actual saved n8n execution.

Set AGENTSENTINEL_LIVE_EXECUTION_ID explicitly. No workflows are changed or executed.
Credentials come from the local .env. All test records use a temporary SQLite database.
"""

import asyncio
import os

import httpx
import pytest
from sqlalchemy import select

from app.config import Settings
from app.db import Base, database
from app.integrations.n8n import N8nClient
from app.monitoring.models import Execution, Incident, Workflow
from app.monitoring.service import Monitor


@pytest.mark.skipif(
    not os.getenv("AGENTSENTINEL_LIVE_EXECUTION_ID"),
    reason="An actual n8n execution ID is required",
)
def test_real_execution_observation_and_rescan(tmp_path):
    config = Settings()
    engine, sessions = database(f"sqlite:///{tmp_path / 'live-test.db'}")
    Base.metadata.create_all(engine)

    async def verify():
        async with httpx.AsyncClient(timeout=30, follow_redirects=False, trust_env=False) as http:
            client = N8nClient(http, config.n8n_base_url, config.n8n_api_key.get_secret_value())
            detail = await client.execution(os.environ["AGENTSENTINEL_LIVE_EXECUTION_ID"])
            assert detail["status"] in {"success", "error", "crashed", "canceled"}
            monitor = Monitor(sessions, client, config)
            await monitor.sync()
            with sessions() as session:
                workflow = session.get(Workflow, detail["workflowId"])
                assert workflow is not None
                workflow.enabled = True
                session.commit()
            monitor.record(detail["workflowId"], detail)
            with sessions() as session:
                first = [(row.id, row.occurrences) for row in session.scalars(select(Incident))]
            monitor.record(detail["workflowId"], detail)
            with sessions() as session:
                second = [(row.id, row.occurrences) for row in session.scalars(select(Incident))]
                stored = session.get(Execution, detail["id"])
                assert stored.status == detail["status"]
                assert stored.inspected is True
                assert first == second
                if detail["status"] in {"error", "crashed"}:
                    assert first

    try:
        asyncio.run(verify())
    finally:
        engine.dispose()
