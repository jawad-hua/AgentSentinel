import json
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from pydantic import ValidationError

from app.config import Settings
from app.security import redact


def auth(settings, kind="admin"):
    return {"Authorization": "Bearer " + getattr(settings, f"{kind}_api_token").get_secret_value()}


def test_service_and_empty_database(client, settings):
    assert client.get("/health/live").json() == {"status": "alive"}
    assert client.get("/health/ready").status_code == 200
    response = client.get("/api/v1/status", headers=auth(settings))
    data = response.json()
    assert data["heartbeat_count"] == 0
    assert data["last_heartbeat"] is None
    assert data["kill_switch"] is True
    assert data["monitoring_enabled"] is False
    assert data["repairs_enabled"] is False
    assert settings.admin_api_token.get_secret_value() not in response.text
    assert response.headers["cache-control"] == "no-store"


def test_scoped_auth(client, settings):
    assert client.get("/api/v1/status").status_code == 401
    assert client.get("/api/v1/status", headers=auth(settings, "ingest")).status_code == 401
    assert client.post("/api/v1/heartbeat", headers=auth(settings), json={}).status_code == 401
    assert (
        client.post("/api/v1/integrations/n8n/check", headers=auth(settings, "ingest")).status_code
        == 401
    )


def test_actual_http_delivery_persistence_and_dedup(client, settings):
    # This is a direct HTTP contract test, NOT an n8n execution or an incident fixture.
    # Isolated temporary DB is destroyed by pytest; nothing is seeded into the application.
    payload = {"workflow_id": "contract-test", "execution_id": "request-1"}
    first = client.post("/api/v1/heartbeat", headers=auth(settings, "ingest"), json=payload)
    assert first.json()["status"] == "recorded"
    second = client.post("/api/v1/heartbeat", headers=auth(settings, "ingest"), json=payload)
    assert second.json()["status"] == "already_received"
    data = client.get("/api/v1/status", headers=auth(settings)).json()
    assert data["heartbeat_count"] == 1
    assert data["last_heartbeat"] is not None


def test_invalid_payload_is_not_echoed(client, settings):
    response = client.post(
        "/api/v1/heartbeat",
        headers=auth(settings, "ingest"),
        json={"workflow_id": "", "execution_id": "x", "token": "secret-input"},
    )
    assert response.status_code == 422
    assert "secret-input" not in response.text


def test_unconfigured_connections_fail_truthfully(client, settings):
    for provider in ("n8n", "groq"):
        result = client.post(f"/api/v1/integrations/{provider}/check", headers=auth(settings))
        assert result.status_code == 502
        assert "not configured" in result.json()["detail"]
    assert (
        client.post("/api/v1/integrations/unknown/check", headers=auth(settings)).status_code == 404
    )


def test_no_mutation_endpoints(client, settings):
    assert (
        client.patch("/api/v1/workflows/1/repair", headers=auth(settings), json={}).status_code
        == 404
    )


def test_migration_round_trip(settings):
    config = Config("alembic.ini")
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    command.check(config)


def test_config_rejects_weak_or_shared_secrets(settings):
    values = settings.model_dump()
    values["admin_api_token"] = "short"
    with pytest.raises(ValidationError):
        Settings(**values, _env_file=None)
    values["admin_api_token"] = settings.ingest_api_token
    with pytest.raises(ValidationError):
        Settings(**values, _env_file=None)


def test_redaction_excludes_secrets_and_unreviewed_free_text():
    evidence = {
        "authorization": "private",
        "node": {"apiKey": "private", "message": "token"},
        "status_code": 500,
        "rows": [{"password": "private"}],
    }
    clean = redact(evidence)
    assert "private" not in json.dumps(clean)
    assert clean["status_code"] == 500
    assert clean["node"]["message"] == "[TEXT OMITTED]"


def test_single_workflow_structure_and_no_embedded_credentials():
    paths = list((Path(__file__).parents[2] / "n8n").glob("*.json"))
    assert len(paths) == 1
    workflow = json.loads(paths[0].read_text())
    assert workflow["active"] is False
    assert workflow["pinData"] == {}
    names = {node["name"] for node in workflow["nodes"]}
    for node in workflow["nodes"]:
        assert "credentials" not in node
    for source, kinds in workflow["connections"].items():
        assert source in names
        for outputs in kinds.values():
            for output in outputs:
                assert all(edge["node"] in names for edge in output)
