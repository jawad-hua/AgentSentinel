"""Recovery requires complete, unpinned real execution evidence, never heartbeat receipts."""

from datetime import UTC, datetime

from app.investigation.evidence import fingerprint
from app.monitoring.normalize import TERMINAL, detect, timestamp


def utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def evaluate(detail: dict, expected: dict, workflow, applied_at: datetime, target: str) -> str:
    if str(detail.get("workflowId")) != str(workflow.id):
        return "unrelated"
    start = timestamp(detail.get("startedAt"))
    if start is None or start < utc(applied_at):
        return "older"
    if detail.get("status") not in TERMINAL:
        return "pending"
    recorded = detail.get("workflowData")
    if not isinstance(recorded, dict) or fingerprint(recorded) != fingerprint(expected):
        return "unproven"
    data = detail.get("data") or {}
    result = data.get("resultData") or {}
    if (
        recorded.get("pinData")
        or result.get("pinData")
        or data.get("pinData")
        or detail.get("retryOf")
    ):
        return "unproven"
    if data.get("startData"):
        return "unproven"
    findings, available = detect(detail, workflow)
    if findings or detail.get("status") != "success":
        return "failed"
    if not available or not timestamp(detail.get("stoppedAt")):
        return "unproven"
    index = int(target[5:])
    name = expected["nodes"][index]["name"]
    runs = (result.get("runData") or {}).get(name)
    if not isinstance(runs, list) or not runs or any(run.get("error") for run in runs):
        return "unproven"
    return "success"
