import re
from secrets import compare_digest

from fastapi import HTTPException, Request

SENSITIVE = re.compile(r"password|secret|token|authorization|credential|api.?key|cookie", re.I)


def redact(value):
    if isinstance(value, dict):
        return {k: "[REDACTED]" if SENSITIVE.search(k) else redact(v) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, str):
        # Free text is excluded from AI evidence until an allowlisted evidence collector exists.
        return "[TEXT OMITTED]"
    return value


def authenticate(request: Request, token: str) -> None:
    supplied = request.headers.get("authorization", "")
    if not compare_digest(supplied.encode(), f"Bearer {token}".encode()):
        raise HTTPException(401, "Authentication required", headers={"WWW-Authenticate": "Bearer"})


def admin(request: Request) -> None:
    authenticate(request, request.app.state.settings.admin_api_token.get_secret_value())


def ingest(request: Request) -> None:
    authenticate(request, request.app.state.settings.ingest_api_token.get_secret_value())
