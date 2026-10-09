"""Historical repair observations, rechecked against n8n; never current authorization."""

import asyncio
import copy
from types import SimpleNamespace

from sqlalchemy import select

from app.integrations.n8n import IntegrationError
from app.investigation.evidence import FIELDS
from app.monitoring.normalize import timestamp
from app.repairs.models import Repair
from app.repairs.patches import Snapshots, patch, revision
from app.repairs.verification import evaluate, utc


def comparable_baseline(original: dict, current: dict, target: str) -> bool:
    """Ignore only target retry settings for historical comparison, never write guards."""
    if not target.startswith("node_") or not target[5:].isdigit():
        return False
    index = int(target[5:])
    copies = [copy.deepcopy(original), copy.deepcopy(current)]
    for workflow in copies:
        nodes = workflow.get("nodes")
        if not isinstance(nodes, list) or index >= len(nodes):
            return False
        node = nodes[index]
        if node.get("type") != "n8n-nodes-base.httpRequest":
            return False
        for field in FIELDS:
            node.pop(field, None)
    return revision(copies[0]) == revision(copies[1])


def historical_execution(detail, expected, workflow, repair, target, execution_id):
    if str(detail.get("id")) != execution_id:
        return None
    start, stop = timestamp(detail.get("startedAt")), timestamp(detail.get("stoppedAt"))
    if (
        start is None
        or stop is None
        or stop < start
        or stop > utc(repair.finished_at)
        or detail.get("mode") not in {"manual", "trigger", "webhook"}
    ):
        return None
    outcome = evaluate(detail, expected, workflow, repair.applied_at, target)
    if outcome not in {"success", "failed"}:
        return None
    return {
        "execution_id": execution_id,
        "started_at": start.isoformat(),
        "finished_at": stop.isoformat(),
        "observed_result": outcome,
        "saved_patched_configuration_matches": True,
        "scope": "Historical execution; not a test of the current proposal",
    }


async def collect_repair_history(n8n, sessions, settings, incident_id, workflow, current, bundle):
    """Three terminal records, six read-only detail requests, thirty-second total budget."""
    with sessions() as session:
        repairs = list(
            session.scalars(
                select(Repair)
                .where(
                    Repair.incident_id == incident_id,
                    Repair.workflow_id == workflow.id,
                    Repair.finished_at.is_not(None),
                    Repair.active_workflow_id.is_(None),
                )
                .order_by(Repair.id.desc())
                .limit(3)
            )
        )
    scope = {
        "record_limit": 3,
        "execution_limit": 6,
        "included": 0,
        "status": "complete",
        "complete_history": False,
    }
    bundle["repair_history_scope"] = scope
    if not repairs:
        return
    bundle["limits"].append(
        "Repair history is historical database state with separately rechecked n8n records. "
        "It does not prove helper mode, request attempt counts, causal attribution, "
        "persistent-failure behavior, present health or approval of a new repair. "
        "Missing records are unavailable evidence, never successful executions. "
        "Historical baseline comparison ignores only the affected node's retry fields; "
        "current revision checks and all repair policy gates remain unchanged."
    )
    snapshots = Snapshots(settings.snapshot_encryption_key.get_secret_value())
    requests = 0
    try:
        async with asyncio.timeout(30):
            for repair in repairs:
                value = {
                    "repair_id": repair.id,
                    "recorded_outcome": repair.status,
                    "finished_at": utc(repair.finished_at).isoformat(),
                    "source": "Persisted repair audit record",
                    "recheck": "unavailable",
                    "rechecked_executions": [],
                }
                scope["included"] += 1
                bundle["facts"].append(
                    {
                        "id": f"repair_history_{repair.id}",
                        "kind": "historical_repair",
                        "value": value,
                    }
                )
                try:
                    original = snapshots.open(repair.snapshot)
                    expected = patch(original, repair.changes)
                    if (
                        revision(original) != repair.before_hash
                        or revision(expected) != repair.after_hash
                    ):
                        value["recheck"] = "snapshot_revision_mismatch"
                        continue
                    target = repair.changes[0]["node"]
                    affected = bundle["facts"][0]["value"].get("affected_node")
                    if affected != target or not comparable_baseline(original, current, target):
                        value["recheck"] = "different_configuration_or_target"
                        continue
                    value["same_configuration_except_target_retry_fields"] = True
                    value["historical_changes"] = [
                        {k: change[k] for k in ("node", "field", "before", "after")}
                        for change in repair.changes
                    ]
                    node = expected["nodes"][int(target[5:])]
                    value["historical_retry_configuration"] = {
                        k: node.get(k, default) for k, default in FIELDS.items()
                    }
                    if repair.applied_at is None:
                        value["recheck"] = "no_recorded_application"
                        continue
                    verification = repair.verification or {}
                    contract = verification.get("contract") or {}
                    historical_workflow = SimpleNamespace(
                        id=workflow.id,
                        **{
                            k: contract.get(k)
                            for k in (
                                "require_output",
                                "expect_json",
                                "contract_node",
                                "json_field",
                            )
                        },
                    )
                    # Include failures first; do not select success-only evidence.
                    ids = list(
                        dict.fromkeys(
                            verification.get("failed_ids", []) + verification.get("success_ids", [])
                        )
                    )
                    value["recheck"] = "checked" if ids else "no_recorded_verification_executions"
                    for execution_id in ids:
                        if requests >= 6:
                            value["recheck"] = "partial_request_limit"
                            break
                        requests += 1
                        try:
                            detail = await n8n.execution(str(execution_id))
                            observed = historical_execution(
                                detail,
                                expected,
                                historical_workflow,
                                repair,
                                target,
                                str(execution_id),
                            )
                        except (IntegrationError, ValueError, TypeError, KeyError, AttributeError):
                            observed = None
                        if observed is None:
                            value["recheck"] = "partial_unavailable"
                        value["rechecked_executions"].append(
                            observed
                            or {"execution_id": str(execution_id), "observed_result": "unavailable"}
                        )
                except (
                    IntegrationError,
                    ValueError,
                    TypeError,
                    KeyError,
                    AttributeError,
                    IndexError,
                ):
                    value["recheck"] = "unavailable"
    except TimeoutError:
        scope["status"] = "incomplete_timeout"
        if repairs:
            value["recheck"] = "incomplete_timeout"
    scope["detail_requests"] = requests
