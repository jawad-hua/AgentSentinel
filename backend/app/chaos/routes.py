from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select

from app.chaos.models import ChaosSession, ChaosTarget, ProbeAttempt
from app.chaos.service import arm, no_active_repair, record_probe, target_index
from app.integrations.n8n import IntegrationError
from app.monitoring.models import Occurrence, Workflow
from app.monitoring.routes import iso
from app.monitoring.service import event
from app.security import admin, ingest

router = APIRouter(prefix="/api/v1/chaos")


class Action(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["designate", "transient", "persistent", "stop"]
    workflow_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,128}$")
    baseline_execution: str = Field(default="", max_length=128, pattern=r"^[A-Za-z0-9_-]*$")
    acknowledged: bool


@router.get("", dependencies=[Depends(admin)])
def overview(request: Request):
    config = request.app.state.settings
    with request.app.state.sessions() as session:
        targets = []
        for workflow in session.scalars(
            select(Workflow).where(Workflow.id.in_(config.chaos_targets & config.repair_targets))
        ):
            target = session.get(ChaosTarget, workflow.id)
            fault = (
                session.get(ChaosSession, target.session_id)
                if target and target.session_id
                else None
            )
            targets.append(
                {
                    "id": workflow.id,
                    "name": workflow.name,
                    "designated": bool(target),
                    "session_id": fault.id if fault else None,
                    "mode": fault.mode if fault else "healthy",
                    "expires_at": iso(fault.expires_at) if fault else None,
                }
            )
        history = []
        for row in session.scalars(select(ChaosSession).order_by(ChaosSession.id.desc()).limit(10)):
            attempts = list(
                session.scalars(
                    select(ProbeAttempt)
                    .where(ProbeAttempt.session_id == row.id)
                    .order_by(ProbeAttempt.id.desc())
                    .limit(30)
                )
            )
            incidents = list(
                session.scalars(
                    select(Occurrence.incident_id)
                    .where(Occurrence.execution_id.in_([a.execution_id for a in attempts]))
                    .distinct()
                )
            )
            history.append(
                {
                    "id": row.id,
                    "workflow_id": row.workflow_id,
                    "mode": row.mode,
                    "created_at": iso(row.created_at),
                    "expires_at": iso(row.expires_at),
                    "stopped_at": iso(row.stopped_at),
                    "incident_ids": incidents,
                    "attempts": [
                        {
                            "execution_id": a.execution_id,
                            "attempt": a.attempt,
                            "http_status": a.http_status,
                            "at": iso(a.created_at),
                        }
                        for a in attempts
                    ],
                }
            )
        return {"enabled": config.chaos_enabled, "targets": targets, "sessions": history}


@router.post("", dependencies=[Depends(admin)])
async def action(body: Action, request: Request):
    state = request.app.state
    if not body.acknowledged:
        raise HTTPException(422, "Explicit test-only acknowledgment required")
    if body.action != "stop" and not state.settings.chaos_enabled:
        raise HTTPException(409, "Chaos Mode is disabled in configuration")
    try:
        # Shared repair lock prevents changing fault conditions during approval/application.
        async with state.repairer.lock:
            if body.action == "stop":
                with state.sessions() as session:
                    no_active_repair(session, body.workflow_id)
                    target = session.get(ChaosTarget, body.workflow_id)
                    if target and target.session_id:
                        session.get(ChaosSession, target.session_id).stopped_at = datetime.now(UTC)
                        target.session_id = None
                        event(
                            session,
                            "chaos.stopped",
                            "Fault stopped by operator; health not inferred.",
                            body.workflow_id,
                        )
                        session.commit()
                return {"status": "stopped"}
            if state.settings.kill_switch:
                raise IntegrationError("Configured kill switch blocks fault setup and injection")
            if body.action in {"transient", "persistent"}:
                return await arm(request, body.workflow_id, body.action, body.baseline_execution)
            current = await state.n8n.workflow(body.workflow_id)
            target_index(current, state.settings)
            with state.sessions() as session:
                no_active_repair(session, body.workflow_id)
                workflow = session.get(Workflow, body.workflow_id)
                if not workflow or not workflow.enabled:
                    raise IntegrationError("Sync and enable monitoring before designation")
                if not session.get(ChaosTarget, body.workflow_id):
                    session.add(ChaosTarget(workflow_id=body.workflow_id))
                    event(
                        session,
                        "chaos.designated",
                        "Operator designated the local test workflow.",
                        body.workflow_id,
                    )
                    session.commit()
            return {"status": "designated"}
    except IntegrationError as exc:
        raise HTTPException(409, str(exc)) from None


@router.get("/probe", dependencies=[Depends(ingest)])
async def probe(
    request: Request,
    workflow_id: str = Query(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
    execution_id: str = Query(pattern=r"^[A-Za-z0-9_-]{1,128}$"),
):
    state = request.app.state
    if (
        not state.settings.chaos_enabled
        or workflow_id not in state.settings.chaos_targets & state.settings.repair_targets
    ):
        raise HTTPException(403, "Probe target disabled or not allowlisted")
    if state.settings.kill_switch:
        raise HTTPException(423, "Configured kill switch pauses the Chaos probe")
    try:
        async with state.chaos_lock:
            code = record_probe(state, workflow_id, execution_id)
    except IntegrationError as exc:
        raise HTTPException(409, str(exc)) from None
    return JSONResponse(
        status_code=code,
        content={
            "status": "alive"
            if code == 200
            else "controlled_fault"
            if code == 503
            else "fault_expired",
        },
    )
