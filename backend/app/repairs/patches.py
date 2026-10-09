"""Small retry patches only. Full configurations never leave the encrypted snapshot boundary."""

import copy
import hashlib
import json

from cryptography.fernet import Fernet, InvalidToken

from app.integrations.n8n import IntegrationError
from app.investigation.evidence import FIELDS, fingerprint


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()


def revision(workflow: dict) -> str:
    return digest(
        {
            "configuration": fingerprint(workflow),
            "name": workflow.get("name"),
            "staticData": workflow.get("staticData"),
            "pinData": workflow.get("pinData") or {},
        }
    )


def inactive(workflow: dict) -> None:
    if workflow.get("active") is not False or workflow.get("activeVersionId"):
        raise IntegrationError("Only unpublished, inactive workflows may be repaired")
    if workflow.get("isArchived") or workflow.get("pinData"):
        raise IntegrationError("Archived workflows and pinned execution data are blocked")
    if not workflow.get("nodes") or not isinstance(workflow.get("connections"), dict):
        raise IntegrationError("Workflow structure is unavailable")
    nodes = workflow["nodes"]
    names = [n.get("name") for n in nodes]
    ids = [n.get("id") for n in nodes]
    if len(nodes) > 200 or len(set(names)) != len(names) or len(set(ids)) != len(ids):
        raise IntegrationError("Workflow node identities are invalid")
    if any(not isinstance(x, str) or not x for x in names + ids):
        raise IntegrationError("Workflow node identities are missing")
    for source, kinds in workflow["connections"].items():
        if source not in names:
            raise IntegrationError("Connection source is missing")
        for outputs in kinds.values():
            for channel in outputs:
                if any(edge.get("node") not in names for edge in channel):
                    raise IntegrationError("Connection target is missing")


def patch(workflow: dict, changes: list[dict]) -> dict:
    inactive(workflow)
    if not 1 <= len(changes) <= 3 or len({c["node"] for c in changes}) != 1:
        raise IntegrationError("Only one bounded retry target is allowed")
    updated = copy.deepcopy(workflow)
    seen = set()
    for change in changes:
        alias, field, value = change["node"], change["field"], change["after"]
        if not alias.startswith("node_") or not alias[5:].isdigit():
            raise IntegrationError("Invalid node alias")
        index = int(alias[5:])
        if index >= len(updated["nodes"]) or field not in FIELDS or field in seen:
            raise IntegrationError("Invalid or duplicate patch target")
        seen.add(field)
        node = updated["nodes"][index]
        if node.get("type") != "n8n-nodes-base.httpRequest" or node.get("parameters", {}).get(
            "method", "GET"
        ) not in {"GET", "HEAD", "OPTIONS"}:
            raise IntegrationError("Only read-only HTTP retry settings may be changed")
        if (
            node.get("disabled")
            or node.get("continueOnFail")
            or node.get("onError", "stopWorkflow") != "stopWorkflow"
        ):
            raise IntegrationError("Disabled or error-suppressing nodes cannot be repaired")
        before = node.get(field, FIELDS[field])
        if (
            type(before) is not type(change["before"])
            or before != change["before"]
            or before == value
        ):
            raise IntegrationError("Patch precondition differs from the saved revision")
        valid = (
            field == "retryOnFail"
            and value is True
            or field == "maxTries"
            and type(value) is int
            and 2 <= value <= 5
            or field == "waitBetweenTries"
            and type(value) is int
            and 1000 <= value <= 5000
        )
        if not valid:
            raise IntegrationError("Retry value exceeds the action allowlist")
        node[field] = value
    if (
        node.get("retryOnFail") is not True
        or not 2 <= node.get("maxTries", 3) <= 5
        or not 1000 <= node.get("waitBetweenTries", 1000) <= 5000
    ):
        raise IntegrationError("Final retry configuration is outside the bounded policy")
    return updated


def payload(workflow: dict) -> dict:
    # Public API accepts writable fields only; activation and ownership are excluded.
    body = {
        key: copy.deepcopy(workflow[key])
        for key in ("name", "nodes", "connections", "settings", "staticData", "pinData")
        if key in workflow
    }
    # n8n 2.15.1 rejects binaryMode in public PUT but merges omitted settings from
    # the stored workflow. Keep it in snapshots and revision checks so any loss
    # during read-back escalates instead of falsely confirming the patch.
    if isinstance(body.get("settings"), dict):
        body["settings"].pop("binaryMode", None)
    return body


class Snapshots:
    def __init__(self, key: str):
        self.cipher = Fernet(key.encode()) if key else None

    def seal(self, workflow: dict) -> str:
        if not self.cipher:
            raise IntegrationError("Snapshot encryption key is not configured")
        return self.cipher.encrypt(json.dumps(workflow).encode()).decode()

    def open(self, encrypted: str) -> dict:
        if not self.cipher:
            raise IntegrationError("Snapshot encryption key is not configured")
        try:
            return json.loads(self.cipher.decrypt(encrypted.encode()))
        except (InvalidToken, ValueError):
            raise IntegrationError(
                "Snapshot cannot be decrypted; preserve the original key"
            ) from None
