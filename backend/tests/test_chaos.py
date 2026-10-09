"""Real local HTTP probe contracts; no simulated n8n/Groq responses or operational seeds."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.chaos.models import ChaosSession, ChaosTarget, ProbeAttempt
from app.chaos.service import PROBE_URL, response_code, target_index
from app.integrations.n8n import IntegrationError
from app.monitoring.models import Incident, Workflow
from tests.test_foundation import auth


def test_war_room_empty_is_truthful_and_private(client, settings):
    assert client.get("/api/v1/war-room").status_code == 401
    assert client.get("/api/v1/war-room", headers=auth(settings, "ingest")).status_code == 401
    data = client.get("/api/v1/war-room", headers=auth(settings)).json()
    assert data["focus"] is None
    assert data["metrics"]["healed"] == 0
    assert data["metrics"]["mean_repair_seconds"] is None
    assert data["metrics"]["mean_detection_seconds"] is None
    assert all(n["status"] == "idle" for n in data["graph"])


def test_chaos_gates_before_upstream_calls(client, settings):
    payload = {"action": "transient", "workflow_id": "local-contract", "acknowledged": True}
    assert client.post("/api/v1/chaos", json=payload).status_code == 401
    assert (
        client.post("/api/v1/chaos", json=payload, headers=auth(settings, "ingest")).status_code
        == 401
    )
    assert client.post("/api/v1/chaos", json=payload, headers=auth(settings)).status_code == 409
    payload["acknowledged"] = False
    assert client.post("/api/v1/chaos", json=payload, headers=auth(settings)).status_code == 422


@pytest.mark.parametrize(
    "mode,attempt,expired,code",
    [
        ("healthy", 1, False, 200),
        ("transient", 1, False, 503),
        ("transient", 2, False, 200),
        ("persistent", 5, False, 503),
        ("transient", 2, True, 410),
        ("persistent", 2, True, 410),
    ],
)
def test_fault_contract(mode, attempt, expired, code):
    assert response_code(mode, attempt, expired) == code


def test_actual_probe_responses_persist_without_fabricating_incidents(client, settings):
    settings.chaos_enabled = True
    settings.kill_switch = False
    settings.chaos_workflow_ids = settings.repair_workflow_ids = "local-contract"
    with client.app.state.sessions() as session:
        session.add(Workflow(id="local-contract", name="HTTP contract target"))
        session.flush()
        fault = ChaosSession(
            workflow_id="local-contract",
            mode="transient",
            revision="0" * 64,
            baseline_execution="contract-only",
            expires_at=datetime.now(UTC) + timedelta(minutes=1),
        )
        session.add(fault)
        session.flush()
        session.add(ChaosTarget(workflow_id="local-contract", session_id=fault.id))
        session.commit()
    url = "/api/v1/chaos/probe?workflow_id=local-contract&execution_id=contract-request"
    assert client.get(url).status_code == 401
    assert client.get(url, headers=auth(settings)).status_code == 401
    assert client.get(url, headers=auth(settings, "ingest")).status_code == 503
    assert client.get(url, headers=auth(settings, "ingest")).status_code == 200
    with client.app.state.sessions() as session:
        attempts = list(session.scalars(select(ProbeAttempt).order_by(ProbeAttempt.id)))
        assert [(a.attempt, a.http_status) for a in attempts] == [(1, 503), (2, 200)]
        assert session.scalar(select(func.count()).select_from(Incident)) == 0
        fault = session.get(ChaosSession, attempts[0].session_id)
        fault.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
    assert client.get(url, headers=auth(settings, "ingest")).status_code == 410
    assert (
        client.get(
            url.replace("local-contract", "arbitrary"), headers=auth(settings, "ingest")
        ).status_code
        == 403
    )


def template():
    return {
        "id": "local-contract",
        "active": False,
        "nodes": [
            {"id": "m", "name": "Manual", "type": "n8n-nodes-base.manualTrigger"},
            {
                "id": "p",
                "name": "Probe",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {
                    "url": PROBE_URL,
                    "authentication": "genericCredentialType",
                    "genericAuthType": "httpHeaderAuth",
                },
                "credentials": {"httpHeaderAuth": {"id": "credential-reference"}},
            },
        ],
        "connections": {"Manual": {"main": [[{"node": "Probe", "type": "main", "index": 0}]]}},
    }


@pytest.mark.parametrize("change", ["external", "published", "extra_node", "suppression", "proxy"])
def test_template_rejects_unsafe_targets(settings, change):
    settings.chaos_workflow_ids = settings.repair_workflow_ids = "local-contract"
    workflow = template()
    assert target_index(workflow, settings) == 1
    if change == "external":
        workflow["nodes"][1]["parameters"]["url"] = "https://example.org"
    elif change == "published":
        workflow["active"] = True
    elif change == "extra_node":
        workflow["nodes"].append({"id": "c", "name": "Code", "type": "n8n-nodes-base.code"})
    elif change == "suppression":
        workflow["nodes"][1]["onError"] = "continueRegularOutput"
    else:
        workflow["nodes"][1]["parameters"]["options"] = {"proxy": "https://example.org"}
    with pytest.raises(IntegrationError):
        target_index(workflow, settings)


def test_kill_switch_never_turns_probe_into_success(client, settings):
    settings.chaos_enabled = True
    settings.chaos_workflow_ids = settings.repair_workflow_ids = "local-contract"
    settings.kill_switch = True
    result = client.get(
        "/api/v1/chaos/probe?workflow_id=local-contract&execution_id=contract-request",
        headers=auth(settings, "ingest"),
    )
    assert result.status_code == 423
    with client.app.state.sessions() as session:
        assert session.scalar(select(func.count()).select_from(ProbeAttempt)) == 0
