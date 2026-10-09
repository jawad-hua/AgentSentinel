import secrets

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def settings(tmp_path, monkeypatch):
    values = {
        "DATABASE_URL": f"sqlite:///{tmp_path / 'test.db'}",
        "ADMIN_API_TOKEN": secrets.token_urlsafe(48),
        "INGEST_API_TOKEN": secrets.token_urlsafe(48),
        "N8N_API_KEY": "",
        "GROQ_API_KEY": "",
        "KILL_SWITCH": "true",
        "ALLOWED_HOSTS": "testserver,127.0.0.1,localhost",
    }
    for name, value in values.items():
        monkeypatch.setenv(name, value)
    command.upgrade(Config("alembic.ini"), "head")
    return Settings(_env_file=None)


@pytest.fixture
def client(settings):
    with TestClient(create_app(settings)) as client:
        yield client
