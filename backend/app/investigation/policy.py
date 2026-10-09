"""Deterministic proposal boundary. Never authorizes an n8n write."""

from app.investigation.schemas import Diagnosis, Fix, Risk, Validation


def assess(
    bundle: dict,
    diagnosis: Diagnosis,
    fix: Fix,
    validation: Validation,
    risk: Risk,
    incident_kind: str,
) -> dict:
    reasons: list[str] = []
    supported = set(validation.supported_hypotheses)
    if any(type(i) is not int or i < 0 or i >= len(diagnosis.hypotheses) for i in supported):
        raise ValueError("Validator referenced an unknown hypothesis")
    if len(supported) != len(validation.supported_hypotheses):
        raise ValueError("Duplicate hypothesis references")
    if not validation.accepted:
        reasons.append("Independent validator rejected the proposal.")
    if not supported:
        reasons.append("No hypothesis was supported by the validator.")
    if not bundle["revision_matches"]:
        reasons.append(
            "Workflow changed since the failed execution; re-investigate current behavior."
        )
    if risk.level == "blocked":
        reasons.append("Risk agent requested a block.")
    nodes = {n["node"]: n for n in bundle["nodes"]}
    changes = []
    seen = set()
    for change in fix.changes:
        key = (change.node, change.field)
        if key in seen:
            reasons.append("Duplicate patch target.")
        seen.add(key)
        node = nodes.get(change.node)
        if node is None:
            reasons.append("Patch targets an unknown node.")
            continue
        if not node.get("executed") or not node.get("error_observed"):
            reasons.append("Patch must target a node with an observed execution error.")
        # Even retry can duplicate side effects. V1 proposal scope is read-only HTTP methods.
        if node["type"] != "n8n-nodes-base.httpRequest" or node["config"].get("method") not in {
            "GET",
            "HEAD",
            "OPTIONS",
        }:
            reasons.append("Retry proposal is restricted to read-only HTTP request methods.")
        if incident_kind not in {"timeout", "http_failure"}:
            reasons.append("Retry does not address this observed failure category.")
        status = bundle["facts"][0]["value"].get("http_status")
        if incident_kind == "http_failure" and status not in {408, 429, 500, 502, 503, 504}:
            reasons.append("Retry is not permitted for this HTTP status.")
        value = change.value
        valid = (
            change.field == "retryOnFail"
            and value is True
            or change.field == "maxTries"
            and type(value) is int
            and 2 <= value <= 5
            or change.field == "waitBetweenTries"
            and type(value) is int
            and 1000 <= value <= 5000
        )
        if not valid:
            reasons.append("Patch value is outside the deterministic retry limits.")
        before = node["config"].get(change.field)
        if before == value:
            reasons.append("Patch contains a no-op.")
        changes.append(
            {"node": change.node, "field": change.field, "before": before, "after": value}
        )
    if len({c.node for c in fix.changes}) > 1:
        reasons.append("Only one node may be changed in a proposal.")
    if fix.changes:
        target = nodes.get(fix.changes[0].node, {})
        final_config = dict(target.get("config", {}))
        final_config.update({c.field: c.value for c in fix.changes})
        if final_config.get("retryOnFail") is not True:
            reasons.append("Proposed retry settings would not enable retries.")
    if fix.disposition == "no_safe_fix":
        reasons.append("Fix agent found no supported allowlisted repair.")
    blocked = bool(reasons)
    return {
        "decision": "blocked" if blocked else "human_review_required",
        "risk_level": "blocked" if blocked else ("high" if risk.level == "high" else "medium"),
        "reasons": list(dict.fromkeys(reasons)) or ["Every retry proposal requires human review."],
        "changes": changes,
        "execution_allowed": False,
        "approval_status": "not_requested",
        "validation_scope": "Static review only; no replay or recovery verification performed.",
        "confidence": {
            "label": "Evidence-limited hypothesis" if blocked else "Reviewed hypothesis",
            "supported_hypotheses": len(supported),
            "total_hypotheses": len(diagnosis.hypotheses),
            "evidence_coverage_percent": round(100 * len(supported) / len(diagnosis.hypotheses)),
            "meaning": (
                "Validator-supported hypotheses / total hypotheses. Not probability of correctness."
            ),
        },
    }
