import asyncio
import json
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, model_validator
from sqlalchemy import func, select

from app.integrations.n8n import IntegrationError
from app.monitoring.models import Event, Execution, Incident, Occurrence, Workflow
from app.monitoring.service import event, utc
from app.security import admin

router = APIRouter(prefix="/api/v1", dependencies=[Depends(admin)])


def iso(value):
    return utc(value).isoformat() if value else None


def incident_dict(row, workflow_name):
    return {
        "id": row.id,
        "workflow_id": row.workflow_id,
        "workflow_name": workflow_name,
        "kind": row.kind,
        "node": row.node,
        "severity": row.severity,
        "status": row.status,
        "summary": row.summary,
        "occurrences": row.occurrences,
        "first_execution_id": row.first_execution_id,
        "last_execution_id": row.last_execution_id,
        "detected_at": iso(row.detected_at),
        "last_seen_at": iso(row.last_seen_at),
        "evidence": row.evidence,
    }


def event_dict(row):
    return {
        "id": row.id,
        "kind": row.kind,
        "workflow_id": row.workflow_id,
        "incident_id": row.incident_id,
        "message": row.message,
        "created_at": iso(row.created_at),
    }


class WorkflowUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool
    require_output: bool = False
    expect_json: bool = False
    contract_node: str | None = Field(default=None, max_length=256)
    json_field: str | None = Field(default=None, max_length=256, pattern=r"^[A-Za-z0-9_.-]+$")

    @model_validator(mode="after")
    def contract(self):
        if (self.require_output or self.expect_json) and not (self.contract_node or "").strip():
            raise ValueError("An exact node name is required for output checks")
        if self.expect_json and not self.json_field:
            raise ValueError("A JSON output field is required")
        return self


@router.get("/workflows")
def workflows(request: Request):
    with request.app.state.sessions() as session:
        result = []
        for row in session.scalars(select(Workflow).order_by(Workflow.name)):
            latest = session.scalar(
                select(Execution)
                .where(Execution.workflow_id == row.id)
                .order_by(Execution.started_at.desc(), Execution.observed_at.desc())
                .limit(1)
            )
            count = session.scalar(
                select(func.count()).select_from(Incident).where(Incident.workflow_id == row.id)
            )
            stale = not row.last_polled_at or datetime.now(UTC) - utc(
                row.last_polled_at
            ) > timedelta(seconds=max(90, request.app.state.settings.poll_interval_seconds * 3))
            result.append(
                {
                    "id": row.id,
                    "name": row.name,
                    "active": row.active,
                    "available": row.available,
                    "enabled": row.enabled,
                    "require_output": row.require_output,
                    "expect_json": row.expect_json,
                    "contract_node": row.contract_node,
                    "json_field": row.json_field,
                    "monitor_since": iso(row.monitor_since),
                    "last_polled_at": iso(row.last_polled_at),
                    "last_error": row.last_error,
                    "stale": stale,
                    "incident_count": count,
                    "backfill_pending": bool(row.backfill_cursor),
                    "last_execution": {
                        "id": latest.id,
                        "status": latest.status,
                        "started_at": iso(latest.started_at),
                        "duration_ms": latest.duration_ms,
                        "has_findings": latest.has_findings,
                        "evidence_available": latest.evidence_available,
                    }
                    if latest
                    else None,
                }
            )
        return {
            "items": result,
            "monitoring_enabled": request.app.state.settings.monitoring_enabled,
            "poll_interval_seconds": request.app.state.settings.poll_interval_seconds,
        }


@router.post("/workflows/sync")
async def sync(request: Request):
    try:
        return await request.app.state.monitor.sync()
    except IntegrationError as exc:
        raise HTTPException(502, str(exc)) from None


@router.patch("/workflows/{workflow_id}")
def update(workflow_id: str, body: WorkflowUpdate, request: Request):
    with request.app.state.sessions() as session:
        row = session.get(Workflow, workflow_id)
        if row is None:
            raise HTTPException(404, "Workflow not found; sync the catalog first")
        if body.enabled and not row.available:
            raise HTTPException(409, "Workflow is not available in the n8n catalog")
        if body.enabled and not row.enabled:
            count = session.scalar(
                select(func.count()).select_from(Workflow).where(Workflow.enabled.is_(True))
            )
            if count >= 20:
                raise HTTPException(409, "Local monitoring is limited to 20 enabled workflows")
            if row.monitor_since is None:
                row.monitor_since = datetime.now(UTC) - timedelta(
                    hours=request.app.state.settings.monitoring_lookback_hours
                )
        for name, value in body.model_dump().items():
            setattr(row, name, value)
        event(
            session,
            "workflow.configured",
            "Monitoring configuration saved by the operator.",
            workflow_id,
        )
        session.commit()
    request.app.state.monitor.wake.set()
    return {"status": "saved"}


@router.post("/monitor/poll", status_code=202)
def poll(request: Request):
    if not request.app.state.settings.monitoring_enabled:
        raise HTTPException(409, "Monitoring is disabled in server configuration")
    with request.app.state.sessions() as session:
        event(session, "monitor.requested", "Operator requested an execution check.")
        session.commit()
    request.app.state.monitor.wake.set()
    return {"status": "requested"}


@router.get("/incidents")
def incidents(
    request: Request,
    before: int | None = Query(default=None, ge=1),
    limit: int = Query(default=30, ge=1, le=100),
):
    with request.app.state.sessions() as session:
        query = select(Incident, Workflow.name).join(Workflow).order_by(Incident.id.desc())
        if before:
            query = query.where(Incident.id < before)
        rows = list(session.execute(query.limit(limit + 1)))
        items = [incident_dict(row, name) for row, name in rows[:limit]]
        return {"items": items, "next_before": items[-1]["id"] if len(rows) > limit else None}


@router.get("/incidents/{incident_id}")
def incident(incident_id: int, request: Request):
    with request.app.state.sessions() as session:
        row = session.get(Incident, incident_id)
        if row is None:
            raise HTTPException(404, "Incident not found")
        name = session.get(Workflow, row.workflow_id).name
        data = incident_dict(row, name)
        data["timeline"] = [
            event_dict(e)
            for e in session.scalars(
                select(Event)
                .where(Event.incident_id == row.id)
                .order_by(Event.id.desc())
                .limit(100)
            )
        ][::-1]
        data["occurrences_recent"] = [
            {
                "execution_id": o.execution_id,
                "evidence": o.evidence,
                "observed_at": iso(o.observed_at),
            }
            for o in session.scalars(
                select(Occurrence)
                .where(Occurrence.incident_id == row.id)
                .order_by(Occurrence.observed_at.desc())
                .limit(20)
            )
        ]
        data["timeline_limit"] = 100
        return data


@router.get("/events")
async def events(request: Request):
    raw = request.headers.get("last-event-id", "")
    if raw and (not raw.isdigit() or len(raw) > 18):
        raise HTTPException(400, "Invalid event cursor")
    with request.app.state.sessions() as session:
        cursor = int(raw) if raw else session.scalar(select(func.max(Event.id))) or 0

    async def stream():
        nonlocal cursor
        yield "retry: 3000\nevent: ready\ndata: {}\n\n"
        keepalive = 0
        while not await request.is_disconnected():
            with request.app.state.sessions() as session:
                rows = list(
                    session.scalars(
                        select(Event).where(Event.id > cursor).order_by(Event.id).limit(100)
                    )
                )
                payloads = [(row.id, json.dumps(event_dict(row))) for row in rows]
            for event_id, payload in payloads:
                cursor = event_id
                yield f"id: {event_id}\ndata: {payload}\n\n"
            keepalive += 1
            if keepalive >= 15:
                yield ": keepalive\n\n"
                keepalive = 0
            await asyncio.sleep(1)

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
