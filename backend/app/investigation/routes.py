from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select

from app.integrations.n8n import IntegrationError
from app.investigation.models import AgentRun, Investigation
from app.investigation.review import triage_review_eligible
from app.monitoring.models import Incident
from app.monitoring.routes import iso
from app.security import admin

router = APIRouter(prefix="/api/v1/incidents", dependencies=[Depends(admin)])


@router.post("/{incident_id}/investigations", status_code=202)
async def request_analysis(incident_id: int, request: Request):
    with request.app.state.sessions() as session:
        if session.get(Incident, incident_id) is None:
            raise HTTPException(404, "Incident not found")
    try:
        run_id = request.app.state.investigator.enqueue(incident_id)
    except IntegrationError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"investigation_id": run_id, "status": "requested"}


@router.post("/{incident_id}/investigations/{source_id}/assessment", status_code=202)
async def request_assessment(incident_id: int, source_id: int, request: Request):
    try:
        run_id = request.app.state.investigator.enqueue(incident_id, review_of=source_id)
    except IntegrationError as exc:
        raise HTTPException(409, str(exc)) from None
    return {"investigation_id": run_id, "status": "requested"}


@router.get("/{incident_id}/investigations")
def investigations(incident_id: int, request: Request):
    config = request.app.state.settings
    with request.app.state.sessions() as session:
        incident = session.get(Incident, incident_id)
        if incident is None:
            raise HTTPException(404, "Incident not found")
        items = []
        for row in session.scalars(
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .order_by(Investigation.id.desc())
            .limit(10)
        ):
            agents = list(
                session.scalars(
                    select(AgentRun)
                    .where(AgentRun.investigation_id == row.id)
                    .order_by(AgentRun.id)
                )
            )
            stages = [
                {
                    "id": agent.id,
                    "stage": agent.stage,
                    "status": agent.status,
                    "started_at": iso(agent.started_at),
                    "finished_at": iso(agent.finished_at),
                    "output": agent.output,
                }
                for agent in agents
            ]
            items.append(
                {
                    "id": row.id,
                    "can_request_assessment": not items
                    and triage_review_eligible(row, incident, agents),
                    "execution_id": row.execution_id,
                    "status": row.status,
                    "stage": row.stage,
                    "trigger": row.trigger,
                    "model": row.model,
                    "created_at": iso(row.created_at),
                    "finished_at": iso(row.finished_at),
                    "review_of": (row.evidence or {}).get("operator_review_of"),
                    "evidence": row.evidence if row.evidence and "facts" in row.evidence else None,
                    "policy": row.policy,
                    "error": row.error,
                    "stages": stages,
                    "newer_failure_observed": row.execution_id != incident.last_execution_id,
                }
            )
    return {
        "items": items,
        "enabled": config.analysis_enabled,
        "configured": bool(config.groq_api_key.get_secret_value()),
        "automatic_new_incidents": config.analysis_auto_new,
        "daily_limit": config.analysis_daily_limit,
        "history_limit": 10,
    }
