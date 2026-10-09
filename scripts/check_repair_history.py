"""Read-only historical repair evidence check. No AI calls, approvals or workflow writes."""

import argparse
import asyncio
import json
from types import SimpleNamespace

import httpx
from app.config import Settings
from app.db import database
from app.integrations.n8n import IntegrationError, N8nClient
from app.investigation.evidence import collect
from app.investigation.repair_history import collect_repair_history
from app.monitoring.models import Incident, Occurrence, Workflow
from sqlalchemy.exc import SQLAlchemyError


async def run(incident_id: int):
    settings = Settings()
    engine, sessions = database(settings.database_url)
    try:
        with sessions() as session:
            incident = session.get(Incident, incident_id)
            if incident is None:
                raise IntegrationError("Incident not found")
            workflow = session.get(Workflow, incident.workflow_id)
            occurrence = session.get(
                Occurrence, (incident.id, incident.last_execution_id)
            )
            if workflow is None or occurrence is None:
                raise IntegrationError("Persisted incident evidence unavailable")
        async with httpx.AsyncClient(timeout=15, trust_env=False) as http:
            n8n = N8nClient(
                http, settings.n8n_base_url, settings.n8n_api_key.get_secret_value()
            )
            source = await n8n.execution(incident.last_execution_id)
            current = await n8n.workflow(incident.workflow_id)
            bundle = collect(
                source,
                current,
                SimpleNamespace(execution_id=incident.last_execution_id),
                occurrence.evidence,
                [],
                incident.node,
            )
            await collect_repair_history(
                n8n,
                sessions,
                settings,
                incident.id,
                workflow,
                current,
                bundle,
            )
        print(
            json.dumps(
                {
                    "scope": bundle["repair_history_scope"],
                    "history": [
                        f["value"]
                        for f in bundle["facts"]
                        if f["kind"] == "historical_repair"
                    ],
                },
                indent=2,
            )
        )
        print("Read-only check complete. No AI calls, approvals or workflow changes.")
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", required=True, type=int)
    args = parser.parse_args()
    try:
        asyncio.run(run(args.incident_id))
    except IntegrationError as exc:
        print(str(exc))
        raise SystemExit(1) from None
    except (SQLAlchemyError, ValueError, TypeError, KeyError, AttributeError):
        print("History check failed; verify configuration and database readiness.")
        raise SystemExit(1) from None
