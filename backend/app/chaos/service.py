"""Probe requests are evidence of responses, never proof of a workflow outcome."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select

from app.chaos.models import ChaosSession, ChaosTarget, ProbeAttempt
from app.integrations.n8n import IntegrationError
from app.investigation.evidence import fingerprint
from app.monitoring.models import Workflow
from app.monitoring.normalize import timestamp
from app.monitoring.service import event, utc
from app.repairs.models import Repair
from app.repairs.patches import inactive

PROBE_URL = (
    "={{ 'http://127.0.0.1:8000/api/v1/chaos/probe?workflow_id=' + $workflow.id "
    "+ '&execution_id=' + $execution.id }}"
)


def target_index(workflow, settings):
    if str(workflow.get("id")) not in settings.chaos_targets & settings.repair_targets:
        raise IntegrationError("Workflow needs both chaos and repair designation in configuration")
    inactive(workflow)
    nodes = [
        (i, n)
        for i, n in enumerate(workflow["nodes"])
        if n.get("type") != "n8n-nodes-base.stickyNote"
    ]
    if len(nodes) != 2 or nodes[0][1].get("type") != "n8n-nodes-base.manualTrigger":
        raise IntegrationError("Chaos requires exactly a manual trigger and a local probe node")
    index, node = nodes[1]
    params = node.get("parameters") or {}
    if (
        node.get("type") != "n8n-nodes-base.httpRequest"
        or params.get("method", "GET") != "GET"
        or params.get("url") != PROBE_URL
        or params.get("authentication") != "genericCredentialType"
        or params.get("genericAuthType") != "httpHeaderAuth"
        or set(node.get("credentials") or {}) != {"httpHeaderAuth"}
        or node.get("disabled")
        or nodes[0][1].get("disabled")
        or node.get("continueOnFail")
        or node.get("onError", "stopWorkflow") != "stopWorkflow"
        or any(params.get(k) for k in ("sendBody", "sendHeaders", "sendQuery"))
        or set(params.get("options") or {}) - {"timeout"}
        or type(node.get("maxTries", 3)) is not int
        or not 2 <= node.get("maxTries", 3) <= 5
        or type(node.get("waitBetweenTries", 1000)) is not int
        or not 1000 <= node.get("waitBetweenTries", 1000) <= 5000
        or workflow["connections"]
        != {nodes[0][1]["name"]: {"main": [[{"node": node["name"], "type": "main", "index": 0}]]}}
    ):
        raise IntegrationError("Use the exact documented authenticated local Chaos probe template")
    return index


def no_active_repair(session, workflow_id):
    if session.scalar(select(Repair.id).where(Repair.active_workflow_id == workflow_id)):
        raise IntegrationError("Finish the active repair before changing fault conditions")


def response_code(mode, attempt, expired=False):
    if expired:
        return 410  # Never turn an expired fault into apparent recovery.
    return 503 if mode == "persistent" or (mode == "transient" and attempt == 1) else 200


async def collect_chaos_context(sessions, settings, source, current, bundle):
    try:
        index = target_index(current, settings)
    except IntegrationError:
        return
    if (
        not bundle["revision_matches"]
        or source.get("mode") != "manual"
        or bundle["facts"][0]["value"].get("http_status") != 503
        or (source.get("data") or {}).get("startData")
        or (source.get("workflowData") or {}).get("pinData")
    ):
        return
    with sessions() as session:
        attempt = session.scalar(
            select(ProbeAttempt)
            .where(
                ProbeAttempt.workflow_id == str(source.get("workflowId")),
                ProbeAttempt.execution_id == str(source.get("id")),
                ProbeAttempt.http_status == 503,
                ProbeAttempt.session_id.is_not(None),
            )
            .order_by(ProbeAttempt.id)
            .limit(1)
        )
        if attempt is None:
            return
        fault = session.get(ChaosSession, attempt.session_id)
        start, stop = timestamp(source.get("startedAt")), timestamp(source.get("stoppedAt"))
        if (
            not fault
            or fault.revision != bundle["execution_revision"]
            or not start
            or not stop
            or not start <= utc(attempt.created_at) <= stop
            or bundle["facts"][0]["value"].get("affected_node") != f"node_{index}"
        ):
            return
        bundle["facts"].append(
            {
                "id": "controlled_fault",
                "kind": "persisted_local_probe_response",
                "value": {
                    "session_id": fault.id,
                    "mode": fault.mode,
                    "affected_node": f"node_{index}",
                    "response": 503,
                    "attempt": attempt.attempt,
                    "behavior": (
                        "Transient: first request per execution returns 503; later requests "
                        "return backend liveness. Persistent: every request returns 503. "
                        "No business writes."
                    ),
                    "desired_behavior": (
                        "Recover within the same full execution in transient mode; persistent "
                        "failures must stay visible after finite attempts. Never suppress errors."
                    ),
                    "limits": (
                        "Probe request IDs are authenticated caller claims, correlated with "
                        "the saved n8n trace and execution interval. This is not repair approval "
                        "or proof of future recovery. Healthy comparisons do not prove retries."
                    ),
                },
            }
        )


async def arm(request, workflow_id, mode, baseline):
    state = request.app.state
    if not state.settings.monitoring_enabled:
        raise IntegrationError("Enable monitoring before arming a fault")
    current = await state.n8n.workflow(workflow_id)
    index = target_index(current, state.settings)
    saved = await state.n8n.execution(baseline)
    data = saved.get("data") or {}
    trace = (data.get("resultData") or {}).get("runData") or {}
    node = current["nodes"][index]
    runs = trace.get(node["name"]) or []
    started = timestamp(saved.get("startedAt"))
    if (
        saved.get("status") != "success"
        or saved.get("mode") != "manual"
        or str(saved.get("workflowId")) != workflow_id
        or fingerprint(saved.get("workflowData") or {}) != fingerprint(current)
        or (saved.get("workflowData") or {}).get("pinData")
        or not started
        or datetime.now(UTC) - started > timedelta(hours=24)
        or not runs
        or any(r.get("error") for r in runs)
        or data.get("startData")
        or data.get("pinData")
        or (data.get("resultData") or {}).get("pinData")
        or saved.get("retryOf")
        or not timestamp(saved.get("stoppedAt"))
        or started > datetime.now(UTC)
    ):
        raise IntegrationError(
            "A recent full successful baseline of this exact saved workflow is required"
        )
    if mode == "transient" and node.get("retryOnFail", False):
        raise IntegrationError(
            "Retry is already enabled; this scenario would not demonstrate a broken run"
        )
    with state.sessions() as session:
        target = session.get(ChaosTarget, workflow_id)
        workflow = session.get(Workflow, workflow_id)
        if not workflow or not workflow.enabled or not workflow.available:
            raise IntegrationError("Target must remain available and monitored")
        if not target:
            raise IntegrationError("Designate this workflow in Chaos Mode first")
        no_active_repair(session, workflow_id)
        if target.session_id:
            raise IntegrationError("Stop the previous fault session first")
        proof = session.scalar(
            select(ProbeAttempt.id).where(
                ProbeAttempt.workflow_id == workflow_id,
                ProbeAttempt.execution_id == baseline,
                ProbeAttempt.session_id.is_(None),
                ProbeAttempt.http_status == 200,
                ProbeAttempt.created_at >= started,
                ProbeAttempt.created_at <= timestamp(saved.get("stoppedAt")),
            )
        )
        if not proof:
            raise IntegrationError("Baseline must include an actual healthy Chaos probe response")
        row = ChaosSession(
            workflow_id=workflow_id,
            mode=mode,
            revision=fingerprint(current),
            baseline_execution=baseline,
            expires_at=datetime.now(UTC) + timedelta(minutes=30),
        )
        session.add(row)
        session.flush()
        target.session_id = row.id
        event(
            session,
            "chaos.armed",
            f"Controlled {mode} fault armed; manual execution required.",
            workflow_id,
        )
        session.commit()
    return {"status": "armed"}


def record_probe(state, workflow_id, execution_id):
    with state.sessions() as session:
        target = session.get(ChaosTarget, workflow_id)
        if not target:
            raise IntegrationError("Workflow has not been designated")
        fault = session.get(ChaosSession, target.session_id) if target.session_id else None
        count = session.scalar(
            select(func.count())
            .select_from(ProbeAttempt)
            .where(
                ProbeAttempt.workflow_id == workflow_id, ProbeAttempt.execution_id == execution_id
            )
        )
        recent = session.scalar(
            select(func.count())
            .select_from(ProbeAttempt)
            .where(ProbeAttempt.created_at >= datetime.now(UTC) - timedelta(minutes=1))
        )
        if count >= 20 or recent >= 120:
            raise IntegrationError("Probe request budget exhausted")
        code = response_code(
            fault.mode if fault else "healthy",
            count + 1,
            bool(fault and utc(fault.expires_at) <= datetime.now(UTC)),
        )
        session.add(
            ProbeAttempt(
                workflow_id=workflow_id,
                execution_id=execution_id,
                session_id=target.session_id,
                attempt=count + 1,
                http_status=code,
            )
        )
        event(
            session,
            "chaos.probe",
            f"Execution {execution_id}, attempt {count + 1}, HTTP {code}.",
            workflow_id,
        )
        session.commit()
        return code
