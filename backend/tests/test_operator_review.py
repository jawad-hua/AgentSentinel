"""Policy boundary vectors only: no simulated providers or operational seed records."""

from types import SimpleNamespace

import pytest

from app.integrations.n8n import IntegrationError
from app.investigation.review import reviewed_triage, triage_review_eligible
from tests.test_foundation import auth


def vector():
    source = SimpleNamespace(
        status="escalated",
        stage="triage",
        trigger="operator",
        execution_id="contract",
        policy=None,
        evidence={"revision_matches": True, "execution_revision": "revision"},
    )
    incident = SimpleNamespace(last_execution_id="contract")
    agents = [
        SimpleNamespace(
            stage="triage",
            status="completed",
            output={
                "summary": "Contract input",
                "severity": "low",
                "affected_node": None,
                "evidence_ids": ["execution"],
                "investigate": False,
                "reason": "Contract input",
            },
        )
    ]
    return source, incident, agents


@pytest.mark.parametrize(
    "field,value",
    [
        ("status", "blocked"),
        ("status", "failed"),
        ("stage", "validator"),
        ("trigger", "operator_review"),
        ("policy", {"decision": "blocked"}),
        ("execution_id", "older"),
        ("evidence", None),
    ],
)
def test_review_cannot_reopen_other_decisions(field, value):
    source, incident, agents = vector()
    setattr(source, field, value)
    assert not triage_review_eligible(source, incident, agents)


def test_review_preserves_triage_and_checks_revision():
    source, incident, agents = vector()
    bundle = {"revision_matches": True, "execution_revision": "revision"}
    result = reviewed_triage(source, incident, agents, bundle)
    assert result == agents[0].output
    assert result["investigate"] is False
    for invalid in [
        {"revision_matches": False, "execution_revision": "revision"},
        {"revision_matches": True, "execution_revision": "changed"},
    ]:
        with pytest.raises(IntegrationError):
            reviewed_triage(source, incident, agents, invalid)
    assert source.status == "escalated"
    assert source.policy is None


def test_review_requires_only_completed_triage_stop():
    source, incident, agents = vector()
    assert triage_review_eligible(source, incident, agents)
    assert not triage_review_eligible(source, incident, [])
    assert not triage_review_eligible(source, incident, agents + agents)
    agents[0].output["investigate"] = True
    assert not triage_review_eligible(source, incident, agents)
    agents[0].output["investigate"] = False
    agents[0].status = "failed"
    assert not triage_review_eligible(source, incident, agents)


def test_review_endpoint_auth(client, settings):
    path = "/api/v1/incidents/1/investigations/1/assessment"
    assert client.post(path).status_code == 401
    assert client.post(path, headers=auth(settings, "ingest")).status_code == 401
    assert client.post(path, headers=auth(settings)).status_code == 409
