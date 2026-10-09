"""Database-derived operations view. No inferred green state from heartbeats."""

from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, select

from app.investigation.models import AgentRun, Investigation
from app.monitoring.models import Event, Execution, Incident, Workflow
from app.monitoring.routes import event_dict, incident_dict, iso
from app.monitoring.service import utc
from app.repairs.models import Repair
from app.security import admin

router = APIRouter(prefix="/api/v1", dependencies=[Depends(admin)])


def graph(session, incident):
    nodes = [
        {"id": k, "status": "idle"}
        for k in (
            "monitor",
            "triage",
            "diagnosis",
            "fix",
            "validator",
            "risk",
            "approval",
            "executor",
            "verification",
        )
    ]
    states = {n["id"]: n for n in nodes}
    if not incident:
        return nodes
    states["monitor"]["status"] = "completed"
    run = session.scalar(
        select(Investigation)
        .where(Investigation.incident_id == incident.id)
        .order_by(Investigation.id.desc())
        .limit(1)
    )
    if run:
        for a in session.scalars(select(AgentRun).where(AgentRun.investigation_id == run.id)):
            if a.stage in states:
                states[a.stage]["status"] = a.status
        if run.trigger == "operator_review":
            states["triage"]["status"] = "referenced"
        repair = session.scalar(select(Repair).where(Repair.investigation_id == run.id))
        if repair:
            states["approval"]["status"] = repair.approval
            states["executor"]["status"] = (
                "running"
                if repair.status in {"applying", "rolling_back"}
                else "completed"
                if repair.applied_at
                else "idle"
            )
            states["verification"]["status"] = (
                "running"
                if repair.status == "verifying"
                else repair.status
                if repair.finished_at
                else "idle"
            )
    return nodes


@router.get("/war-room")
def war_room(request: Request):
    with request.app.state.sessions() as session:

        def count(model, *conditions):
            return session.scalar(select(func.count()).select_from(model).where(*conditions))

        selected = session.scalar(
            select(Incident).order_by(Incident.last_seen_at.desc(), Incident.id.desc()).limit(1)
        )
        active = session.scalar(
            select(Investigation)
            .where(Investigation.active_incident_id.is_not(None))
            .order_by(Investigation.id.desc())
            .limit(1)
        )
        repair = session.scalar(
            select(Repair)
            .where(Repair.active_workflow_id.is_not(None))
            .order_by(Repair.id.desc())
            .limit(1)
        )
        if active:
            selected = session.get(Incident, active.incident_id)
        if repair:
            selected = session.get(Incident, repair.incident_id)
        finished = list(
            session.scalars(
                select(Repair)
                .where(Repair.status == "healed", Repair.finished_at.is_not(None))
                .order_by(Repair.id.desc())
                .limit(100)
            )
        )
        durations = [
            (utc(r.finished_at) - utc(r.applied_at)).total_seconds()
            for r in finished
            if r.applied_at
        ]
        detection = list(
            session.execute(
                select(Incident.detected_at, Execution.stopped_at)
                .join(Execution, Incident.first_execution_id == Execution.id)
                .where(Execution.stopped_at.is_not(None))
                .order_by(Incident.id.desc())
                .limit(100)
            )
        )
        delays = [(utc(d) - utc(s)).total_seconds() for d, s in detection if utc(d) >= utc(s)]
        workflows = count(Workflow, Workflow.enabled.is_(True))
        return {
            "at": datetime.now(UTC).isoformat(),
            "writes_paused": request.app.state.repairer.paused(),
            "configured_kill_switch": request.app.state.settings.kill_switch,
            "monitoring_enabled": request.app.state.settings.monitoring_enabled,
            "metrics": {
                "monitored_workflows": workflows,
                "incidents": count(Incident),
                "open_incidents": count(Incident, Incident.status != "healed"),
                "diagnoses": count(
                    AgentRun, AgentRun.stage == "diagnosis", AgentRun.status == "completed"
                ),
                "repair_attempts": count(Repair, Repair.applied_at.is_not(None)),
                "healed": count(Repair, Repair.status == "healed"),
                "failed_repairs": count(Repair, Repair.status.in_(["failed", "rolled_back"])),
                "rollbacks": count(Repair, Repair.status == "rolled_back"),
                "mean_detection_seconds": round(sum(delays) / len(delays), 1) if delays else None,
                "mean_repair_seconds": round(sum(durations) / len(durations), 1)
                if durations
                else None,
                "detection_samples": len(delays),
                "repair_samples": len(durations),
            },
            "focus": incident_dict(selected, session.get(Workflow, selected.workflow_id).name)
            if selected
            else None,
            "graph": graph(session, selected),
            "events": [
                event_dict(e)
                for e in session.scalars(
                    select(Event)
                    .where(Event.kind != "monitor.polled")
                    .order_by(Event.id.desc())
                    .limit(30)
                )
            ],
            "recent_repairs": [
                {
                    "id": r.id,
                    "incident_id": r.incident_id,
                    "status": r.status,
                    "finished_at": iso(r.finished_at),
                }
                for r in session.scalars(select(Repair).order_by(Repair.id.desc()).limit(6))
            ],
        }
