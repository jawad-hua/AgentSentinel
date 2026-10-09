"""Contract boundaries use empty temporary databases, never operational seed incidents."""

from alembic import command
from alembic.config import Config
from sqlalchemy import func, select

from app.monitoring.models import Event
from app.monitoring.normalize import error_finding, safe_label
from tests.test_foundation import auth


def test_empty_monitoring_is_not_assumed_health(client, settings):
    workflows = client.get("/api/v1/workflows", headers=auth(settings)).json()
    assert workflows["items"] == []
    assert workflows["monitoring_enabled"] is True
    assert client.get("/api/v1/incidents", headers=auth(settings)).json()["items"] == []
    status = client.get("/api/v1/status", headers=auth(settings)).json()
    assert status["monitoring_enabled"] is False
    assert (
        status["monitored_workflows"] == status["execution_count"] == status["incident_count"] == 0
    )


def test_monitoring_read_and_write_require_admin(client, settings):
    for path in ["/api/v1/workflows", "/api/v1/incidents", "/api/v1/events"]:
        assert client.get(path).status_code == 401
        assert client.get(path, headers=auth(settings, "ingest")).status_code == 401
    for path in ["/api/v1/workflows/sync", "/api/v1/monitor/poll"]:
        assert client.post(path, headers=auth(settings, "ingest")).status_code == 401


def test_missing_incident_and_unsynced_workflow(client, settings):
    assert client.get("/api/v1/incidents/1", headers=auth(settings)).status_code == 404
    result = client.patch(
        "/api/v1/workflows/unknown", headers=auth(settings), json={"enabled": True}
    )
    assert result.status_code == 404


def test_contract_validation_and_event_cursor(client, settings):
    result = client.patch(
        "/api/v1/workflows/unknown",
        headers=auth(settings),
        json={"enabled": True, "expect_json": True},
    )
    assert result.status_code == 422
    result = client.get("/api/v1/events", headers={**auth(settings), "Last-Event-ID": "invalid"})
    assert result.status_code == 400


def test_operator_poll_request_is_an_actual_audited_action(client, settings):
    response = client.post("/api/v1/monitor/poll", headers=auth(settings))
    assert response.status_code == 202
    assert response.json()["status"] == "requested"
    with client.app.state.sessions() as session:
        count = session.scalar(
            select(func.count()).select_from(Event).where(Event.kind == "monitor.requested")
        )
        assert count == 1


def test_migration_retains_existing_heartbeat(client, settings):
    # This is an actual HTTP receipt contract test in an isolated DB, not an n8n execution.
    client.post(
        "/api/v1/heartbeat",
        headers=auth(settings, "ingest"),
        json={"workflow_id": "migration-contract", "execution_id": "receipt"},
    )
    command.downgrade(Config("alembic.ini"), "0001")
    command.upgrade(Config("alembic.ini"), "head")
    status = client.get("/api/v1/status", headers=auth(settings)).json()
    assert status["heartbeat_count"] == 1


def test_timeout_signal_from_actual_n8n_error_shape():
    # Recorded in the isolated real n8n 2.15.1 HTTP timeout validation run.
    # Only the non-sensitive error fields are retained; no API response is mocked.
    actual_error_fields = {
        "name": "NodeApiError",
        "message": "The connection was aborted, perhaps the server is offline",
        "messages": ["timeout of 100ms exceeded", "timeout of 100ms exceeded"],
    }
    result = error_finding(actual_error_fields, None)
    assert result.kind == "timeout"
    assert result.evidence["raw_error"] == "omitted for privacy"


def test_redaction_before_label_truncation(settings):
    key = settings.admin_api_token.get_secret_value()
    value = "x" * 230 + key
    assert key[:20] not in safe_label(value, (key,))
