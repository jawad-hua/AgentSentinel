"""Opt-in real n8n + Groq inference, up to five calls; no workflow writes."""

import asyncio
import os

import httpx
import pytest
from sqlalchemy import select

from app.config import Settings
from app.db import Base, database
from app.integrations.llm import GroqProvider
from app.integrations.n8n import N8nClient
from app.investigation.models import AgentRun, Investigation
from app.investigation.service import Investigator
from app.monitoring.models import Incident
from app.monitoring.service import Monitor


@pytest.mark.skipif(
    os.getenv("AGENTSENTINEL_LIVE_ANALYSIS") != "1"
    or not os.getenv("AGENTSENTINEL_LIVE_EXECUTION_ID"),
    reason="Real execution ID and explicit inference opt-in required",
)
def test_real_investigation(tmp_path):
    config = Settings()
    engine, sessions = database(f"sqlite:///{tmp_path / 'analysis.db'}")
    Base.metadata.create_all(engine)

    async def run():
        async with httpx.AsyncClient(timeout=30, trust_env=False, follow_redirects=False) as http:
            n8n = N8nClient(http, config.n8n_base_url, config.n8n_api_key.get_secret_value())
            groq = GroqProvider(http, config.groq_api_key.get_secret_value(), config.groq_model)
            monitor = Monitor(sessions, n8n, config)
            await monitor.sync()
            detail = await n8n.execution(os.environ["AGENTSENTINEL_LIVE_EXECUTION_ID"])
            monitor.record(detail["workflowId"], detail)
            with sessions() as session:
                incident = session.scalar(select(Incident))
                assert incident, "Selected execution must contain an observed failure"
                incident_id = incident.id
            worker = Investigator(sessions, n8n, groq, config)
            run_id = worker.enqueue(incident_id)
            await worker.analyze(run_id)
            with sessions() as session:
                result = session.get(Investigation, run_id)
                assert result.status in {"blocked", "review_required", "escalated"}
                assert result.evidence["facts"]
                stages = list(session.scalars(select(AgentRun)))
                assert stages and all(stage.status == "completed" for stage in stages)
                assert not result.policy or result.policy["execution_allowed"] is False

    try:
        asyncio.run(run())
    finally:
        engine.dispose()
