"""Read-only diagnosis of persisted analysis; no provider calls or application changes."""

import argparse
import hashlib
import json
from pathlib import Path

from app.config import Settings
from app.integrations.llm import GroqProvider
from app.investigation import evidence, prompts, service
from app.investigation.models import AgentRun, Investigation
from app.investigation.policy import assess
from app.investigation.schemas import Diagnosis, Fix, Risk, Validation
from sqlalchemy import create_engine, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

# Release fingerprints, not incident data or expected AI decisions.
EXPECTED = {
    "evidence": "05ac18c2276ff647c21b5bc523399d9d2e1ec3eaafa7fc88cac4bc6630a45461",
    "prompts": "e68438d8768208e636756d48e74b08daf2c664e960492e8b9524cc2a2963af3c",
    "service": "2c8c287159522d01c09b310482e8dd521e92dc5374fb9fbeb1d4e008f1c18d48",
}


def diagnose(incident_id: int) -> dict:
    settings = Settings()
    url = make_url(settings.database_url)
    if url.get_backend_name() == "sqlite" and (
        not url.database
        or url.database == ":memory:"
        or not Path(url.database).is_file()
    ):
        raise ValueError("Configured database file is missing; nothing was created")
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as session:
            if url.get_backend_name() == "sqlite":
                session.connection().exec_driver_sql("PRAGMA query_only=ON")
            run = session.scalar(
                select(Investigation)
                .where(Investigation.incident_id == incident_id)
                .order_by(Investigation.id.desc())
                .limit(1)
            )
            if run is None:
                raise ValueError("No persisted investigation exists for this incident")
            agents = list(
                session.scalars(
                    select(AgentRun)
                    .where(AgentRun.investigation_id == run.id)
                    .order_by(AgentRun.id)
                )
            )
            bundle = run.evidence or {}
            facts = {
                f.get("id"): f for f in bundle.get("facts", []) if isinstance(f, dict)
            }
            objective = facts.get("test_operator_objective", {}).get("value", {})
            affected = facts.get("execution", {}).get("value", {}).get("affected_node")
            node = facts.get(affected, {}).get("value", {})
            output = {
                "investigation_id": run.id,
                "incident_id": run.incident_id,
                "execution_id": run.execution_id,
                "status": run.status,
                "model": run.model,
                "trigger": run.trigger,
                "source_triage": bundle.get("operator_review_of"),
                "objective_present": bool(objective),
                "recorded_requirement": {
                    k: str(objective[k])[:2000]
                    for k in ("desired_behavior", "failure_behavior")
                    if k in objective
                },
                "saved_node_settings": {
                    "config": node.get("config"),
                    "error_handling": node.get("error_handling"),
                },
                "recorded_policy": run.policy,
                "stage_decisions": [
                    {
                        "stage": a.stage,
                        "status": a.status,
                        "decision": {
                            k: a.output[k]
                            for k in (
                                "disposition",
                                "accepted",
                                "level",
                                "evidence_ids",
                            )
                            if k in (a.output or {})
                        },
                    }
                    for a in agents
                ],
                "loaded_source_checks": {},
                "limits": [
                    "Source hashes check this diagnostic process, not the running server memory.",
                    "Saved evidence is not a wire capture of the prior Groq request.",
                    "Policy replay validates decision rules, not the truth of AI interpretations.",
                    "No LLM calls, n8n calls, approvals, workflow writes or database updates.",
                ],
            }
            for name, module in (
                ("evidence", evidence),
                ("prompts", prompts),
                ("service", service),
            ):
                actual = hashlib.sha256(
                    Path(module.__file__).read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest()
                output["loaded_source_checks"][name] = {
                    "matches_delivered_version": actual == EXPECTED.get(name),
                    "sha256": actual,
                }
            by_stage = {a.stage: a.output for a in agents if a.status == "completed"}
            if all(
                name in by_stage for name in ("diagnosis", "fix", "validator", "risk")
            ):
                replay = assess(
                    bundle,
                    Diagnosis.model_validate(by_stage["diagnosis"]),
                    Fix.model_validate(by_stage["fix"]),
                    Validation.model_validate(by_stage["validator"]),
                    Risk.model_validate(by_stage["risk"]),
                    bundle["detection_kind"],
                )
                output["policy_replay_matches_record"] = all(
                    replay.get(k) == (run.policy or {}).get(k)
                    for k in ("decision", "reasons")
                )
            else:
                output["policy_replay_matches_record"] = (
                    "Not evaluated: stages incomplete"
                )
            secrets = tuple(
                getattr(settings, k).get_secret_value()
                for k in (
                    "admin_api_token",
                    "ingest_api_token",
                    "n8n_api_key",
                    "n8n_write_api_key",
                    "groq_api_key",
                    "snapshot_encryption_key",
                )
            )
            return GroqProvider(None, "", "", secrets=secrets).clean(output)
    finally:
        engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", required=True, type=int)
    args = parser.parse_args()
    try:
        print(json.dumps(diagnose(args.incident_id), indent=2))
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError, OSError):
        print(
            "Diagnostic could not read or validate local state. No provider calls or writes made."
        )
        raise SystemExit(1) from None
