"""Two-call diagnostic replay of saved Fix/Validator inputs. Never authorizes repair."""

import argparse
import asyncio
import hashlib
import json

import httpx
from app.integrations.llm import GroqProvider
from app.integrations.n8n import IntegrationError
from app.investigation.models import Investigation
from app.investigation.prompts import BASE, PROMPTS
from app.investigation.schemas import STAGES, validate_references
from evaluate_requirement import Settings, load
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

REVIEW = (
    "\nThe operator explicitly requested read-only "
    "repair assessment after a prior triage stop. "
    "The prior investigate=false decision remains "
    "unchanged. Evaluate unmet requirements "
    "against the fresh facts; do not assume a "
    "repair is needed. Historical triage is "
    "interpretation, not fresh evidence. "
    "No-safe-fix and rejection remain valid outcomes."
)


SCOPE_REVIEW = (
    "\nThe operator requested assessment of candidate configuration changes after a "
    "prior triage stop. This analysis is read-only: it cannot APPLY workflow changes. "
    "That execution restriction does not prohibit PROPOSING a candidate change for "
    "later independent validation, risk review and explicit approval. "
    "Evaluate the recorded operator objective against the observed facts. "
    "Historical triage is interpretation, not a binding replacement for that objective. "
    "A proposal is data, not authorization to write. Do not assume a repair is needed; "
    "no_safe_fix remains valid when justified by the evidence and allowed actions."
)


async def replay(incident_id: int, scope_check: bool = False):
    settings = Settings()
    run_id, model, facts, limitations, saved = load(incident_id, settings)
    if not all(s in saved for s in ("diagnosis", "fix", "validator")):
        raise ValueError("Saved stages incomplete")
    engine = create_engine(settings.database_url)
    try:
        with Session(engine) as session:
            if engine.dialect.name == "sqlite":
                session.connection().exec_driver_sql("PRAGMA query_only=ON")
            run = session.get(Investigation, run_id)
            kind = run.evidence["detection_kind"]
            revision_matches = run.evidence["revision_matches"]
            review = run.trigger == "operator_review"
    finally:
        engine.dispose()
    if scope_check and not review:
        raise ValueError("Scope comparison requires an operator-review investigation")
    secrets = tuple(
        getattr(settings, name).get_secret_value()
        for name in (
            "admin_api_token",
            "ingest_api_token",
            "n8n_api_key",
            "n8n_write_api_key",
            "snapshot_encryption_key",
        )
    )
    print(f"Source investigation: {run_id}; model: {model}")
    print(
        "Reconstructing inputs from saved state and currently installed prompts; not a wire capture."
    )
    if scope_check:
        print("One Fix call maximum. Only the appended operator-review instruction is changed.")
        print("Diagnostic scope clarification; production prompts and saved inputs are retained.")
    else:
        print("Two calls maximum. Validator uses the ORIGINAL saved Fix, not this replay's new Fix.")
    print(
        "No database/n8n writes. Results cannot enter the approval process.", flush=True
    )
    async with httpx.AsyncClient(timeout=60, trust_env=False) as http:
        provider = GroqProvider(
            http, settings.groq_api_key.get_secret_value(), model, secrets=secrets
        )
        stages = [("fix", ("diagnosis",))]
        if not scope_check:
            stages.append(("validator", ("diagnosis", "fix")))
        for stage, required in stages:
            review_instruction = SCOPE_REVIEW if scope_check else REVIEW
            instruction = BASE + PROMPTS[stage] + (review_instruction if review else "")
            inputs = {
                "facts": facts,
                "detection_kind": kind,
                "revision_matches": revision_matches,
                "limitations": limitations,
                "previous_stages": {k: saved[k] for k in required},
            }
            try:
                print(f"Running diagnostic stage: {stage}", flush=True)
                result = await provider.generate(instruction, inputs, STAGES[stage])
                validate_references(result, facts)
                if stage == "validator":
                    refs = result.supported_hypotheses
                    if len(refs) != len(set(refs)) or any(
                        i < 0 or i >= len(saved["diagnosis"]["hypotheses"])
                        for i in refs
                    ):
                        raise ValueError("Invalid hypothesis references")
                decision = "disposition" if stage == "fix" else "accepted"
                print(
                    json.dumps(
                        provider.clean(
                            {
                                "stage": stage,
                                "condition": "clarified_review_scope" if scope_check else "installed_review_scope",
                                "prompt_sha256": hashlib.sha256(
                                    instruction.encode()
                                ).hexdigest(),
                                "original_decision": saved[stage].get(decision),
                                "replay_decision": result.model_dump().get(decision),
                                "actual_replay_output": result.model_dump(),
                            }
                        ),
                        indent=2,
                    ),
                    flush=True,
                )
            except (IntegrationError, ValueError) as exc:
                print(
                    json.dumps(
                        {
                            "stage": stage,
                            "status": "not_evaluated",
                            "reason": str(exc)
                            if isinstance(exc, IntegrationError)
                            else "Output validation failed",
                        }
                    ),
                    flush=True,
                )
                break
    print(
        "Finished. No automatic retries. Replay agreement/disagreement is not repair validation."
    )
    print(
        "This diagnostic cannot prove model reliability or the cause of the original reasoning error."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--incident-id", required=True, type=int)
    parser.add_argument(
        "--scope-check", action="store_true",
        help="One Fix call with clarified proposal-versus-application review scope; no writes.",
    )
    args = parser.parse_args()
    try:
        asyncio.run(replay(args.incident_id, args.scope_check))
    except (SQLAlchemyError, ValueError, KeyError, TypeError, AttributeError):
        print(
            "Stopped: saved evidence/stages unavailable or configured model differs. No writes."
        )
        raise SystemExit(1) from None
