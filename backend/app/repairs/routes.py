from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.integrations.n8n import IntegrationError
from app.monitoring.models import Incident
from app.monitoring.routes import iso
from app.repairs.models import Repair
from app.security import admin

router = APIRouter(prefix="/api/v1", dependencies=[Depends(admin)])


class Prepare(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    investigation_id: int = Field(gt=0)


class Decision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    action: Literal["approve", "reject"]
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    maintenance_acknowledged: bool = False


class Safety(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    paused: bool


@router.post("/repairs", status_code=201)
async def prepare(body: Prepare, request: Request):
    try:
        rid = await request.app.state.repairer.prepare(body.investigation_id)
    except (IntegrationError, IntegrityError, ValueError) as exc:
        message = (
            str(exc) if isinstance(exc, IntegrationError) else "Repair could not be prepared safely"
        )
        raise HTTPException(409, message) from None
    return {"repair_id": rid}


@router.post("/repairs/{repair_id}/decision")
async def decision(repair_id: int, body: Decision, request: Request):
    try:
        await request.app.state.repairer.decide(
            repair_id, body.action, body.digest, body.maintenance_acknowledged
        )
    except (IntegrationError, ValueError) as exc:
        raise HTTPException(
            409, str(exc) if isinstance(exc, IntegrationError) else "Approval validation failed"
        ) from None
    return {"status": body.action}


@router.post("/repair-safety")
async def safety(body: Safety, request: Request):
    await request.app.state.repairer.safety(body.paused)
    return {"paused": request.app.state.repairer.paused()}


@router.get("/incidents/{incident_id}/repairs")
def repairs(incident_id: int, request: Request):
    worker = request.app.state.repairer
    with request.app.state.sessions() as session:
        incident = session.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(404, "Incident not found")
        rows = list(
            session.scalars(
                select(Repair)
                .where(Repair.incident_id == incident_id)
                .order_by(Repair.id.desc())
                .limit(10)
            )
        )
        items = [
            {
                "id": row.id,
                "investigation_id": row.investigation_id,
                "status": row.status,
                "approval": row.approval,
                "created_at": iso(row.created_at),
                "expires_at": iso(row.expires_at),
                "decided_at": iso(row.decided_at),
                "applied_at": iso(row.applied_at),
                "deadline": iso(row.deadline),
                "finished_at": iso(row.finished_at),
                "before_hash": row.before_hash,
                "after_hash": row.after_hash,
                "digest": row.approval_digest,
                "changes": row.changes,
                "message": row.message,
                "snapshot_saved": bool(row.snapshot),
                "holds_workflow": bool(row.active_workflow_id),
                "verification": {k: v for k, v in row.verification.items() if k != "contract"},
            }
            for row in rows
        ]
    return {
        "items": items,
        "enabled": worker.settings.repairs_enabled,
        "designated": incident.workflow_id in worker.settings.repair_targets,
        "paused": worker.paused(),
        "configured_kill_switch": worker.settings.kill_switch,
        "configured": bool(
            worker.snapshots.cipher and worker.settings.n8n_write_api_key.get_secret_value()
        ),
    }


@router.post("/repairs/{repair_id}/reconcile")
async def reconcile(repair_id: int, request: Request):
    try:
        await request.app.state.repairer.recover(repair_id)
    except IntegrationError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"status": "reconciled"}
