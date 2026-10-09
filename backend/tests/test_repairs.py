"""Pure configuration/security contract vectors. Never seed operational incidents or AI results."""

import copy

import pytest
from cryptography.fernet import Fernet

from app.integrations.n8n import IntegrationError
from app.repairs.patches import Snapshots, patch, payload, revision
from tests.test_foundation import auth


def specification():
    # A minimal configuration input to the patch validator, not an executed workflow.
    return {
        "name": "Configuration contract",
        "id": "contract",
        "active": False,
        "nodes": [
            {
                "id": "http",
                "name": "HTTP",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"method": "GET"},
            }
        ],
        "connections": {},
        "settings": {},
    }


def changes():
    return [{"node": "node_0", "field": "retryOnFail", "before": False, "after": True}]


def test_patch_changes_only_authorized_field_and_is_reversible():
    original = specification()
    saved = copy.deepcopy(original)
    updated = patch(original, changes())
    assert original == saved
    assert revision(updated) != revision(original)
    del updated["nodes"][0]["retryOnFail"]
    assert updated == original
    assert "active" not in payload(original)
    assert "id" not in payload(original)


@pytest.mark.parametrize("method", ["POST", "PUT", "DELETE", "PATCH", "={{ $json.method }}"])
def test_non_read_only_methods_cannot_be_approved(method):
    original = specification()
    original["nodes"][0]["parameters"]["method"] = method
    with pytest.raises(IntegrationError):
        patch(original, changes())


@pytest.mark.parametrize(
    "mutate",
    [
        lambda w: w.update(active=True),
        lambda w: w.update(activeVersionId="published"),
        lambda w: w.update(pinData={"HTTP": []}),
        lambda w: w["nodes"][0].update(disabled=True),
        lambda w: w["nodes"][0].update(onError="continueRegularOutput"),
        lambda w: w["nodes"][0].update(maxTries=10),
        lambda w: w["nodes"][0].update(retryOnFail=True),
    ],
)
def test_unsafe_workflow_boundaries(mutate):
    original = specification()
    mutate(original)
    with pytest.raises(IntegrationError):
        patch(original, changes())


def test_credentials_round_trip_only_inside_encrypted_snapshot():
    original = specification()
    original["nodes"][0]["credentials"] = {"httpHeaderAuth": {"id": "credential-reference"}}
    snapshots = Snapshots(Fernet.generate_key().decode())
    sealed = snapshots.seal(original)
    assert "credential-reference" not in sealed
    assert snapshots.open(sealed) == original
    with pytest.raises(IntegrationError):
        Snapshots(Fernet.generate_key().decode()).open(sealed)


def test_repair_auth_and_invalid_input_fail_closed(client, settings):
    for path in (
        "/api/v1/repairs",
        "/api/v1/repairs/1/decision",
        "/api/v1/repair-safety",
        "/api/v1/repairs/1/reconcile",
    ):
        assert client.post(path, json={}).status_code == 401
        assert client.post(path, headers=auth(settings, "ingest"), json={}).status_code == 401
    assert (
        client.post(
            "/api/v1/repairs", headers=auth(settings), json={"investigation_id": 1}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/repairs", headers=auth(settings), json={"investigation_id": 1, "patch": {}}
        ).status_code
        == 422
    )
    assert client.get("/api/v1/incidents/1/repairs", headers=auth(settings)).status_code == 404


def test_persisted_runtime_kill_switch_cannot_override_configuration(client, settings):
    for paused in (True, False):
        result = client.post(
            "/api/v1/repair-safety", headers=auth(settings), json={"paused": paused}
        )
        assert result.status_code == 200
        assert result.json()["paused"] is True


def test_only_documented_equivalent_n8n_defaults_are_canonicalized():
    original = specification()
    materialized = copy.deepcopy(original)
    materialized["settings"] = {"callerPolicy": "workflowsFromSameOwner", "availableInMCP": False}
    assert revision(original) == revision(materialized)
    materialized["settings"]["availableInMCP"] = True
    assert revision(original) != revision(materialized)
    materialized["settings"] = {"callerPolicy": "any"}
    assert revision(original) != revision(materialized)


def test_unknown_recovery_claim_cannot_be_cleared(client, settings):
    response = client.post("/api/v1/repairs/1/reconcile", headers=auth(settings))
    assert response.status_code == 409


@pytest.mark.parametrize(
    "field,value",
    [("maxTries", 100), ("waitBetweenTries", 0), ("retryOnFail", 1), ("credentials", True)],
)
def test_patch_rejects_unbounded_or_unallowlisted_values(field, value):
    original = specification()
    change = {"node": "node_0", "field": field, "before": False, "after": value}
    with pytest.raises(IntegrationError):
        patch(original, [change])
