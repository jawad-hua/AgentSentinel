"""Pure detectors: observations, not AI diagnoses. No payloads are persisted here."""

import hashlib
import json
import re
from datetime import UTC, datetime
from statistics import median

from pydantic import BaseModel, ConfigDict

TERMINAL = {"success", "error", "crashed", "canceled"}
STATUSES = TERMINAL | {"new", "running", "waiting", "unknown"}


def timestamp(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(UTC) if result.tzinfo else result.replace(tzinfo=UTC)
    except ValueError:
        return None


def safe_label(value, secrets=()) -> str:
    text = str(value or "")
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    text = re.sub(
        r"(?i)(bearer\s+|(?:api[_-]?key|token|password|secret)\s*[:=]\s*)[^\s,;]+",
        "[REDACTED]",
        text,
    )
    text = re.sub(r"https?://\S+", "[URL OMITTED]", text)
    return re.sub(r"[\x00-\x1f]", " ", text)[:256]


class Finding(BaseModel):
    model_config = ConfigDict(extra="forbid")
    kind: str
    node: str | None = None
    severity: str = "high"
    summary: str
    evidence: dict
    signature: str = ""

    def fingerprint(self, workflow_id: str) -> str:
        values = [workflow_id, self.kind, self.node, self.signature]
        return hashlib.sha256(json.dumps(values, sort_keys=True).encode()).hexdigest()


def error_finding(error: dict, node: str | None, secrets=()) -> Finding:
    # Examine raw error only in memory. Never store arbitrary error text/stack/input.
    name = str(error.get("name", ""))
    message = str(error.get("message", ""))
    description = str(error.get("description", ""))
    messages = error.get("messages")
    extra = (
        " ".join(item for item in messages if isinstance(item, str))
        if isinstance(messages, list)
        else ""
    )
    text = (name + " " + message + " " + description + " " + extra).lower()
    status = error.get("httpCode", error.get("statusCode"))
    try:
        status = int(status)
    except (ValueError, TypeError):
        status = None
    kind = "node_exception"
    if "etimedout" in text or "timed out" in text or "timeout" in text:
        kind = "timeout"
    elif "outputparser" in text or "structured output" in text or "output doesn't fit" in text:
        kind = "structured_output_failure"
    elif "json" in text and any(
        term in text for term in ("invalid", "parse", "unexpected", "valid", "syntax")
    ):
        kind = "invalid_json"
    elif status and 400 <= status <= 599:
        kind = "http_failure"
    # Stable redacted signature groups equivalent errors without retaining raw messages.
    signature = safe_label(message + " " + description + " " + extra, secrets)
    signature = re.sub(r"\b\d+\b", "#", signature)
    signature = hashlib.sha256((name + signature + str(status)).encode()).hexdigest()
    evidence = {"source": "n8n execution error", "raw_error": "omitted for privacy"}
    if status and 400 <= status <= 599:
        evidence["http_status"] = status
    if name in {
        "NodeOperationError",
        "NodeApiError",
        "SyntaxError",
        "TypeError",
        "WorkflowOperationError",
        "OutputParserException",
        "Error",
    }:
        evidence["error_type"] = name
    return Finding(
        kind=kind,
        node=node,
        summary=f"n8n reported {kind.replace('_', ' ')}.",
        evidence=evidence,
        signature=signature,
    )


def items_from_run(run: dict) -> list[dict] | None:
    main = (run.get("data") or {}).get("main")
    if not isinstance(main, list):
        return None
    return [
        item
        for branch in main
        if isinstance(branch, list)
        for item in branch
        if isinstance(item, dict)
    ]


def find_field(value, path: str):
    for part in path.split("."):
        if not isinstance(value, dict) or part not in value:
            return None
        value = value[part]
    return value


def detect(detail: dict, workflow, secrets=()) -> tuple[list[Finding], bool]:
    result = (detail.get("data") or {}).get("resultData") or {}
    runs = result.get("runData")
    available = isinstance(runs, dict)
    findings: list[Finding] = []
    root_error = result.get("error")
    types = {
        node.get("name"): node
        for node in (detail.get("workflowData") or {}).get("nodes", [])
        if isinstance(node, dict)
    }
    if available:
        for name, executions in runs.items():
            if not isinstance(executions, list):
                continue
            for run in executions:
                if not isinstance(run, dict):
                    continue
                node = safe_label(name, secrets)
                if isinstance(run.get("error"), dict):
                    findings.append(error_finding(run["error"], node, secrets))
                items = items_from_run(run)
                config = types.get(name, {})
                response_options = ((config.get("parameters") or {}).get("options") or {}).get(
                    "response"
                ) or {}
                full_response = (response_options.get("response") or {}).get("fullResponse") is True
                if config.get("type") == "n8n-nodes-base.httpRequest" and full_response and items:
                    for item in items:
                        status = (item.get("json") or {}).get("statusCode")
                        if isinstance(status, int) and 400 <= status <= 599:
                            findings.append(
                                Finding(
                                    kind="http_failure",
                                    node=node,
                                    summary="HTTP Request output contains a failed HTTP status.",
                                    evidence={
                                        "source": "HTTP Request output statusCode",
                                        "http_status": status,
                                    },
                                    signature=str(status),
                                )
                            )
                # A skipped/unrecorded node is not proof of empty output.
                if name != workflow.contract_node or items is None or run.get("error"):
                    continue
                if workflow.require_output and (
                    not items or all(not i.get("json") and not i.get("binary") for i in items)
                ):
                    findings.append(
                        Finding(
                            kind="empty_output",
                            node=node,
                            summary="Executed node returned no required output.",
                            evidence={
                                "source": "operator output contract",
                                "item_count": len(items),
                            },
                        )
                    )
                if workflow.expect_json and workflow.json_field:
                    for item in items:
                        value = find_field(item.get("json"), workflow.json_field)
                        valid = isinstance(value, (dict, list))
                        if isinstance(value, str):
                            try:
                                valid = isinstance(json.loads(value), (dict, list))
                            except (ValueError, RecursionError):
                                valid = False
                        if not valid:
                            findings.append(
                                Finding(
                                    kind="invalid_json",
                                    node=node,
                                    summary=(
                                        "Configured output field is missing or is not "
                                        "a JSON object/array."
                                    ),
                                    evidence={
                                        "source": "operator JSON contract",
                                        "field": safe_label(workflow.json_field, secrets),
                                    },
                                    signature=workflow.json_field,
                                )
                            )
    if isinstance(root_error, dict) and not any(
        f.evidence.get("source") == "n8n execution error" for f in findings
    ):
        raw_node = root_error.get("node")
        node = (
            raw_node.get("name") if isinstance(raw_node, dict) else result.get("lastNodeExecuted")
        )
        findings.append(error_finding(root_error, safe_label(node, secrets) or None, secrets))
    if detail.get("status") in {"error", "crashed"} and not findings:
        findings.append(
            Finding(
                kind="execution_failure",
                summary="n8n reported a failed execution.",
                evidence={"source": "n8n execution status", "status": detail["status"]},
            )
        )
    unique = {(f.kind, f.node, f.signature): f for f in findings}
    return list(unique.values()), available


def latency_finding(duration: int | None, baseline: list[int]) -> Finding | None:
    if duration is None or len(baseline) < 20:
        return None
    center = median(baseline)
    mad = median(abs(value - center) for value in baseline)
    threshold = max(center * 3, center + max(1000, 6 * mad))
    if duration <= threshold:
        return None
    return Finding(
        kind="abnormal_latency",
        severity="medium",
        summary="Execution duration exceeded the historical threshold.",
        evidence={
            "source": "prior successful executions in the same workflow and mode",
            "sample_count": len(baseline),
            "median_ms": center,
            "threshold_ms": threshold,
            "observed_ms": duration,
        },
    )
