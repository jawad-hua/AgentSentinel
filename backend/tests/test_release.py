import asyncio
import importlib.util
import sqlite3
from pathlib import Path

import pytest

from app.http_guard import HttpGuard
from app.worker_lock import worker_lock
from tests.test_foundation import auth


def test_host_body_and_auth_guards(client, settings):
    assert client.get("/health/live", headers={"Host": "attacker.invalid"}).status_code == 400
    response = client.post("/api/v1/heartbeat", content=b"x" * 65537, headers=auth(settings))
    assert response.status_code == 413
    assert "x" * 20 not in response.text
    # Size gate must not break actual small authenticated deliveries.
    assert (
        client.post(
            "/api/v1/heartbeat",
            headers=auth(settings, "ingest"),
            json={"workflow_id": "release-contract", "execution_id": "direct-http-receipt"},
        ).status_code
        == 200
    )


def test_rate_budget_is_bounded_and_not_forwarded_ip_dependent(client):
    statuses = [
        client.get("/health/live", headers={"X-Forwarded-For": str(i)}).status_code
        for i in range(601)
    ]
    assert statuses[-1] == 429


def test_chunked_body_size_enforced_before_handler():
    async def scenario():
        reached = False
        sent = []

        async def app(scope, receive, send):
            nonlocal reached
            reached = True

        async def receive():
            return {"type": "http.request", "body": b"a" * 40000, "more_body": True}

        async def send(message):
            sent.append(message)

        await HttpGuard(app)(
            {"type": "http", "method": "POST", "path": "/", "headers": []}, receive, send
        )
        assert not reached
        assert sent[0]["status"] == 413

    asyncio.run(scenario())


def test_worker_lock_rejects_second_worker_and_releases(tmp_path):
    url = f"sqlite:///{tmp_path / 'db.sqlite'}"
    with worker_lock(url):
        with pytest.raises(RuntimeError, match="Another"):
            with worker_lock(url):
                pass
    with worker_lock(url):
        pass


def test_stream_budget_released_after_cancellation():
    async def scenario():
        started = 0
        ready = asyncio.Event()
        blocked = asyncio.Event()
        sent = []

        async def app(scope, receive, send):
            nonlocal started
            started += 1
            if started == 8:
                ready.set()
            await blocked.wait()

        async def receive():
            return {"type": "http.disconnect"}

        async def send(message):
            sent.append(message)

        guard = HttpGuard(app)
        scope = {"type": "http", "method": "GET", "path": "/api/v1/events"}
        tasks = [asyncio.create_task(guard(scope, receive, send)) for _ in range(8)]
        await ready.wait()
        await guard(scope, receive, send)
        assert sent[0]["status"] == 429
        for task in tasks:
            task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        assert guard.streams == 0
    asyncio.run(scenario())


def test_backup_restores_real_persisted_receipt(client, settings, tmp_path):
    client.post(
        "/api/v1/heartbeat",
        headers=auth(settings, "ingest"),
        json={"workflow_id": "backup-contract", "execution_id": "direct-http-receipt"},
    )
    spec = importlib.util.spec_from_file_location(
        "backup", Path(__file__).parents[2] / "scripts/backup_database.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    output = tmp_path / "backup.sqlite"
    with pytest.raises(RuntimeError):
        module.backup(settings.database_url, output)
    assert not output.exists()
    # A separate real SQLite database tests byte-independent backup/restore.
    source = tmp_path / "offline.sqlite"
    with sqlite3.connect(source) as connection:
        connection.execute("CREATE TABLE receipts (value TEXT)")
        connection.execute("INSERT INTO receipts VALUES (?)", ("actual test write",))
    module.backup(f"sqlite:///{source}", output)
    with sqlite3.connect(output) as restored:
        assert restored.execute("SELECT value FROM receipts").fetchone()[0] == "actual test write"
    with pytest.raises(FileExistsError):
        module.backup(f"sqlite:///{source}", output)
