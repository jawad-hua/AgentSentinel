"""Revision-bound operator testimony for the shipped local test helper, not auto-approval."""

import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import select

from app.integrations.n8n import IntegrationError
from app.investigation.comparisons import comparison
from app.investigation.evidence import fingerprint
from app.monitoring.models import Event
from app.monitoring.normalize import detect, timestamp
from app.repairs.patches import inactive

HELPER_SHA = "5f4b9d25e89fa9d42ac57e5d9d13e1e404cdffb05afd2123f0829507031c99a2"
KIND = "test.operator_attestation"


class TestAttestation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: str = Field(pattern=r"^[a-f0-9]{64}$")
    failure: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    healthy: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    port: int = Field(ge=1024, le=65535)
    helper_sha: str = Field(pattern=r"^[a-f0-9]{64}$")
    objective: Literal["same_execution_recovery"] | None = None


def helper_matches() -> bool:
    path = Path(__file__).resolve().parents[3] / "scripts" / "repair_test_target.py"
    try:
        content = path.read_bytes().replace(b"\r\n", b"\n")
        return hashlib.sha256(content).hexdigest() == HELPER_SHA
    except OSError:
        return False


def target_node(workflow: dict, settings, port: int) -> int:
    if str(workflow.get("id")) not in settings.repair_targets:
        raise IntegrationError("Workflow is not explicitly designated for repairs")
    if urlsplit(settings.n8n_base_url).hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise IntegrationError("This helper attestation requires local n8n")
    inactive(workflow)
    if not helper_matches():
        raise IntegrationError("Installed test helper differs from the reviewed source")
    nodes = workflow["nodes"]
    executable = [
        (i, n) for i, n in enumerate(nodes) if n.get("type") != "n8n-nodes-base.stickyNote"
    ]
    if len(executable) != 2 or executable[0][1].get("type") != "n8n-nodes-base.manualTrigger":
        raise IntegrationError("Expected only a manual trigger and one HTTP test node")
    index, node = executable[1]
    params = node.get("parameters") or {}
    expected = (
        "={{ 'http://127.0.0.1:"
        + str(port)
        + "/probe?workflow_id=' + $workflow.id + '&execution_id=' + $execution.id }}"
    )
    if (
        node.get("type") != "n8n-nodes-base.httpRequest"
        or params.get("method", "GET") != "GET"
        or params.get("url") != expected
        or params.get("authentication", "none") != "none"
        or node.get("credentials")
        or any(
            params.get(k)
            for k in ("sendBody", "sendHeaders", "sendQuery", "provideSslCertificates")
        )
    ):
        raise IntegrationError("Workflow does not match the reviewed local probe configuration")
    return index


def validate_runs(workflow, current, source, healthy, bundle, settings, port):
    index = target_node(current, settings, port)
    if fingerprint(current) != bundle["execution_revision"]:
        raise IntegrationError("Execution and current workflow configurations differ")
    if bundle["facts"][0]["value"].get("affected_node") != f"node_{index}":
        raise IntegrationError("The observed failure is not at the controlled test node")
    failed = comparison(source, workflow, bundle, source, str(source.get("id")))
    success = comparison(healthy, workflow, bundle, source, str(healthy.get("id")))
    findings, available = detect(source, workflow)
    if (
        failed is None
        or success is None
        or not available
        or source.get("status") != "error"
        or not any(f.evidence.get("http_status") == 503 for f in findings)
        or not success["success_with_no_detected_findings"]
        or timestamp(healthy.get("startedAt")) <= timestamp(source.get("startedAt"))
    ):
        raise IntegrationError(
            "Actual full 503 failure and later same-configuration success required"
        )


async def collect_test_context(
    n8n, sessions, settings, incident_id, workflow, current, source, bundle
):
    with sessions() as session:
        record = session.scalar(
            select(Event)
            .where(
                Event.kind == KIND,
                Event.workflow_id == workflow.id,
                Event.incident_id == incident_id,
                Event.created_at >= datetime.now(UTC) - timedelta(hours=24),
            )
            .order_by(Event.id.desc())
            .limit(1)
        )
    if record is None:
        return
    try:
        attestation = TestAttestation.model_validate_json(record.message)
        if (
            attestation.failure != str(source.get("id"))
            or attestation.revision != bundle["execution_revision"]
            or attestation.helper_sha != HELPER_SHA
        ):
            raise IntegrationError("Test attestation no longer matches this execution")
        healthy = await n8n.execution(attestation.healthy)
        validate_runs(workflow, current, source, healthy, bundle, settings, attestation.port)
    except (IntegrationError, ValidationError, ValueError, TypeError, KeyError):
        bundle["limits"].append("Stored test testimony could not be revalidated; it was excluded.")
        return
    bundle["facts"].append(
        {
            "id": "test_operator_context",
            "kind": "operator_attestation_with_checked_configuration",
            "value": {
                "audit_event_id": record.id,
                "source": "Local operator testimony; actual n8n execution/configuration checks",
                "affected_node": bundle["facts"][0]["value"]["affected_node"],
                "failure_execution": attestation.failure,
                "healthy_execution": attestation.healthy,
                "operator_statement": (
                    "I ran the reviewed shipped helper. The failure occurred in transient mode; "
                    "I switched to healthy mode before the separate successful execution."
                ),
                "reviewed_helper_behavior": (
                    "Transient mode intentionally returns HTTP 503 on the first request per "
                    "execution; subsequent requests perform a loopback GET of backend liveness. "
                    "Effects are bounded in-memory attempt counters, logs and liveness reads; "
                    "the helper does not write workflows or business records. Persistent mode "
                    "always fails. Recovery still depends on real backend availability."
                ),
                "provenance_limits": (
                    "Installed helper source hash and saved target configuration checked. The "
                    "running process identity and historical helper mode are operator-attested, "
                    "not independently attested by n8n. Mode change explains the comparison; "
                    "it is not proof of transient network outage or successful automatic retry. "
                    "No proposed repair has been executed or validated by this testimony."
                ),
            },
        }
    )

    if attestation.objective == "same_execution_recovery":
        bundle["facts"].append(
            {
                "id": "test_operator_objective",
                "kind": "operator_declared_requirement",
                "value": {
                    "audit_event_id": record.id,
                    "affected_node": bundle["facts"][0]["value"]["affected_node"],
                    "desired_behavior": (
                        "Complete the same full workflow execution despite the helper's first "
                        "intentional 503, while the helper remains in transient mode and backend "
                        "liveness is available. Changing the helper to healthy or starting a "
                        "separate execution does not meet this requirement."
                    ),
                    "failure_behavior": (
                        "Persistent failures must remain visible after bounded attempts; never "
                        "suppress errors, fabricate output or retry without limit."
                    ),
                    "scope": (
                        "Operator-selected acceptance goal for this designated local test only. "
                        "This is desired behavior, not observed recovery or proof of safety. "
                        "It does not prescribe a patch or authorize any workflow write. All "
                        "existing action bounds, independent validation, risk review, explicit "
                        "approval, verification and rollback requirements still apply."
                    ),
                },
            }
        )
