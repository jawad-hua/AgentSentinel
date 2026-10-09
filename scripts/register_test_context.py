"""Register truthful operator testimony; GET-only n8n access, no LLM or repair writes."""

import argparse
import asyncio

import httpx
from app.config import Settings
from app.db import database
from app.integrations.n8n import IntegrationError, N8nClient
from app.investigation.evidence import collect
from app.investigation.test_context import (
    HELPER_SHA,
    KIND,
    TestAttestation,
    validate_runs,
)
from app.monitoring.models import Incident, Occurrence, Workflow
from app.monitoring.service import event
from app.repairs.models import Repair
from sqlalchemy import select


async def run(args):
    settings = Settings()
    engine, sessions = database(settings.database_url)
    try:
        with sessions() as session:
            incident = session.get(Incident, args.incident_id)
            if incident is None:
                raise IntegrationError("Incident not found")
            if session.scalar(
                select(Repair.id).where(
                    Repair.active_workflow_id == incident.workflow_id
                )
            ):
                raise IntegrationError(
                    "An active repair must finish before registering context"
                )
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
            healthy = await n8n.execution(args.healthy_execution)
            # collect expects the selected execution as execution_id; latest may differ from first.
            from types import SimpleNamespace

            selected = SimpleNamespace(execution_id=incident.last_execution_id)
            bundle = collect(
                source, current, selected, occurrence.evidence, [], incident.node
            )
            validate_runs(
                workflow, current, source, healthy, bundle, settings, args.port
            )
        print(
            "Actual n8n failure, later success and local probe configuration checked."
        )
        print("Confirm ONLY if you ran the unmodified shipped repair_test_target.py:")
        print(
            "Failure was in transient mode; you changed to healthy before the separate success."
        )
        print(
            "This records operator testimony, not independent proof or repair approval."
        )
        if args.objective:
            print(
                "Requested goal: recover within the SAME execution with helper still transient."
            )
            print(
                "Persistent failures must remain visible; no unlimited retries or error suppression."
            )
            print(
                "ATTEST also records this desired behavior, not a repair approval or success claim."
            )
        if (
            input("Type ATTEST to record, or anything else to cancel: ").strip()
            != "ATTEST"
        ):
            print("Cancelled; no testimony recorded.")
            return
        data = TestAttestation(
            revision=bundle["execution_revision"],
            failure=incident.last_execution_id,
            healthy=args.healthy_execution,
            port=args.port,
            helper_sha=HELPER_SHA,
            objective=args.objective,
        )
        message = data.model_dump_json()
        if len(message) > 512:
            raise IntegrationError("Test testimony exceeds audit record size")
        with sessions() as session:
            event(session, KIND, message, incident.workflow_id, incident.id)
            session.commit()
        print(
            "Operator testimony recorded. No n8n changes, AI calls or approvals performed."
        )
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", type=int, required=True)
    parser.add_argument("--healthy-execution", required=True)
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--objective", choices=["same_execution_recovery"])
    args = parser.parse_args()
    try:
        asyncio.run(run(args))
    except (IntegrationError, ValueError, EOFError) as exc:
        if isinstance(exc, IntegrationError):
            print(str(exc))
        else:
            print("Registration stopped; check input and saved execution availability.")
        raise SystemExit(1) from None
