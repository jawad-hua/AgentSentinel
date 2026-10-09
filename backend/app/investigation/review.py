"""Explicit read-only operator review of a triage stop; never a repair override."""

from app.integrations.n8n import IntegrationError
from app.investigation.schemas import Triage


def triage_review_eligible(run, incident, agents) -> bool:
    return bool(
        run.status == "escalated"
        and run.stage == "triage"
        and run.trigger != "operator_review"
        and run.execution_id == incident.last_execution_id
        and run.policy is None
        and run.evidence
        and run.evidence.get("revision_matches") is True
        and run.evidence.get("execution_revision")
        and len(agents) == 1
        and agents[0].stage == "triage"
        and agents[0].status == "completed"
        and agents[0].output
        and agents[0].output.get("investigate") is False
    )


def reviewed_triage(source, incident, agents, bundle) -> dict:
    if not triage_review_eligible(source, incident, agents):
        raise IntegrationError("Source is not an eligible triage-only escalation")
    if (
        not bundle["revision_matches"]
        or bundle["execution_revision"] != source.evidence["execution_revision"]
    ):
        raise IntegrationError("Workflow revision changed; operator assessment cannot continue")
    return Triage.model_validate(agents[0].output).model_dump()
