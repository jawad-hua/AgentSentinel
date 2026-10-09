"""Explicit data minimization: node aliases, typed configuration and output counts only."""

import copy
import hashlib
import json
import re

from app.integrations.n8n import IntegrationError
from app.monitoring.normalize import safe_label

FIELDS = {"retryOnFail": False, "maxTries": 3, "waitBetweenTries": 1000}
FACT_KEYS = {
    "sample_count",
    "median_ms",
    "observed_ms",
    "item_count",
    "http_status",
    "error_type",
    "execution_status",
    "duration_ms",
    "baseline_count",
    "baseline_median_ms",
    "threshold_ms",
    "output_items",
    "reason",
    "kind",
}
ERROR_TYPES = {
    "NodeApiError",
    "NodeOperationError",
    "SyntaxError",
    "TypeError",
    "WorkflowOperationError",
    "OutputParserException",
    "Error",
}


def error_handling(node: dict) -> dict:
    """Expose explicit settings/defaults, never infer successful runtime behavior."""
    result = {}
    for field in ("disabled", "continueOnFail"):
        value = node.get(field, False)
        result[field] = value if type(value) is bool else "unknown"
    mode = node.get("onError", "stopWorkflow")
    result["onError"] = (
        mode
        if mode in ("stopWorkflow", "continueRegularOutput", "continueErrorOutput")
        else "unknown"
    )
    result["source"] = "Saved execution node settings; absent fields use n8n defaults"
    return result


def fingerprint(workflow: dict) -> str:
    # Hash only here; the repair service separately encrypts restorable workflow snapshots.
    parts = copy.deepcopy({key: workflow.get(key) for key in ("nodes", "connections", "settings")})
    # n8n 2.15.1 expands these defaults in saved executions. Strip only exact known
    # defaults from both sides; never discard unknown configuration or secrets from the hash.
    defaults = {
        "n8n-nodes-base.manualTrigger": {"notice": ""},
        "n8n-nodes-base.httpRequest": {
            "curlImport": "",
            "method": "GET",
            "authentication": "none",
            "provideSslCertificates": False,
            "sendQuery": False,
            "sendHeaders": False,
            "sendBody": False,
            "infoMessage": "",
        },
    }
    # Public API PUT materializes these documented defaults in n8n 2.15.1.
    # Non-default values must remain in the hash (they affect security/behavior).
    settings = parts.get("settings") or {}
    for key, default in {"callerPolicy": "workflowsFromSameOwner", "availableInMCP": False}.items():
        if type(settings.get(key)) is type(default) and settings.get(key) == default:
            settings.pop(key, None)
    for node in parts.get("nodes") or []:
        params = node.get("parameters", {})
        for key, default in defaults.get(node.get("type"), {}).items():
            if type(params.get(key)) is type(default) and params.get(key) == default:
                params.pop(key, None)
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def observed_facts(evidence: dict) -> dict:
    result = {}
    for key in FACT_KEYS:
        value = evidence.get(key)
        if type(value) in (int, float, bool):
            result[key] = value
        elif key == "error_type" and value in ERROR_TYPES:
            result[key] = value
        elif key == "execution_status" and value in {"success", "error", "crashed", "canceled"}:
            result[key] = value
    return result


def collect(
    detail: dict,
    current: dict,
    incident,
    occurrence: dict,
    history: list[dict],
    affected_node: str | None = None,
    secrets: tuple = (),
) -> dict:
    if str(detail.get("id")) != incident.execution_id:
        raise IntegrationError("Execution identity does not match the investigation")
    recorded = detail.get("workflowData")
    if not isinstance(recorded, dict) or not isinstance(recorded.get("nodes"), list):
        raise IntegrationError("Saved execution has no workflow configuration; analysis blocked")
    if str(detail.get("workflowId", recorded.get("id"))) != str(current.get("id")):
        raise IntegrationError("Workflow identity mismatch; analysis blocked")
    nodes = recorded["nodes"]
    if len(nodes) > 200:
        raise IntegrationError("Workflow exceeds the 200-node investigation limit")
    result_data = detail.get("data", {}).get("resultData", {})
    run_data = result_data.get("runData", {})
    if not isinstance(run_data, dict) or not run_data:
        raise IntegrationError("Execution trace is unavailable")
    facts = [{"id": "execution", "kind": "observed_failure", "value": observed_facts(occurrence)}]
    aliases = {node.get("name"): f"node_{i}" for i, node in enumerate(nodes)}
    affected_alias = next(
        (
            alias
            for name, alias in aliases.items()
            if affected_node and safe_label(name, secrets) == affected_node
        ),
        None,
    )
    if affected_alias:
        facts[0]["value"]["affected_node"] = affected_alias
    summaries = []
    for index, node in enumerate(nodes):
        alias = f"node_{index}"
        node_type = node.get("type", "")
        if not re.fullmatch(
            r"(?:n8n-nodes-base|@n8n/n8n-nodes-langchain)\.[a-zA-Z0-9]+", node_type
        ):
            node_type = "unreviewed_node_type"
        params = node.get("parameters", {})
        config = {key: node.get(key, default) for key, default in FIELDS.items()}
        config = {k: v for k, v in config.items() if type(v) in (bool, int)}
        method = params.get("method", "GET")
        if node_type == "n8n-nodes-base.httpRequest" and method in {
            "GET",
            "HEAD",
            "POST",
            "PUT",
            "PATCH",
            "DELETE",
            "OPTIONS",
        }:
            config["method"] = method
        runs = run_data.get(node.get("name"), [])
        summary = {"node": alias, "type": node_type, "config": config, "executed": bool(runs)}
        summary["error_handling"] = error_handling(node)
        if runs:
            summary["error_observed"] = any(bool(run.get("error")) for run in runs)
            summary["output_items"] = sum(
                len(items)
                for run in runs
                for items in run.get("data", {}).get("main", [])
                if isinstance(items, list)
            )
        summaries.append(summary)
        # Sticky notes do not execute; their repeated defaults waste scarce inference tokens.
        # Preserve original node indices in aliases and in the configuration fingerprint.
        if node_type != "n8n-nodes-base.stickyNote":
            facts.append({"id": alias, "kind": "execution_node", "value": summary})
    edges = []
    for source, kinds in recorded.get("connections", {}).items():
        for channels in kinds.values():
            for outputs in channels:
                for edge in outputs:
                    if source in aliases and edge.get("node") in aliases:
                        edges.append([aliases[source], aliases[edge["node"]]])
                        if len(edges) > 500:
                            raise IntegrationError("Workflow exceeds the connection evidence limit")
    facts.append({"id": "topology", "kind": "connections", "value": {"edges": edges}})
    if history:
        facts.append({"id": "history", "kind": "related_incidents", "value": {"items": history}})
    return {
        "facts": facts,
        "nodes": summaries,
        "execution_revision": fingerprint(recorded),
        "current_revision": fingerprint(current),
        "revision_matches": fingerprint(recorded) == fingerprint(current),
        "limits": [
            "No raw error text, URLs, credentials, code or payload values shared.",
            "Output counts do not establish payload correctness.",
            "Current configuration may differ from the failed execution.",
        ],
    }
