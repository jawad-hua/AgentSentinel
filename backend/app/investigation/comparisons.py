"""Bounded, minimized real execution comparisons; never infer recovery from a status alone."""

import asyncio
from datetime import UTC, datetime, timedelta

from app.integrations.n8n import IntegrationError
from app.investigation.evidence import fingerprint
from app.monitoring.normalize import detect, items_from_run, timestamp


def comparison(
    detail: dict, workflow, bundle: dict, source: dict, execution_id: str
) -> dict | None:
    if str(detail.get("id")) != execution_id or str(detail.get("workflowId")) != workflow.id:
        return None
    if detail.get("status") not in {"success", "error", "crashed", "canceled"}:
        return None
    start, stop = timestamp(detail.get("startedAt")), timestamp(detail.get("stoppedAt"))
    source_start = timestamp(source.get("startedAt"))
    if start is None or stop is None or source_start is None or stop < start:
        return None
    if detail.get("mode") != source.get("mode") or detail.get("retryOf"):
        return None
    recorded, data = detail.get("workflowData"), detail.get("data") or {}
    if not isinstance(recorded, dict) or fingerprint(recorded) != bundle["execution_revision"]:
        return None
    result = data.get("resultData") or {}
    if (
        recorded.get("pinData")
        or data.get("pinData")
        or result.get("pinData")
        or data.get("startData")
    ):
        return None
    alias = bundle["facts"][0]["value"].get("affected_node")
    if not alias or not alias.startswith("node_") or not alias[5:].isdigit():
        return None
    index = int(alias[5:])
    nodes = recorded.get("nodes") or []
    if index >= len(nodes):
        return None
    runs = (result.get("runData") or {}).get(nodes[index].get("name"))
    if not isinstance(runs, list) or not runs or any(not isinstance(run, dict) for run in runs):
        return None
    findings, available = detect(detail, workflow)
    if not available:
        return None
    outputs = [items_from_run(run) for run in runs]
    return {
        "execution_id": execution_id,
        "started_at": start.isoformat(),
        "relation_to_failed_execution": "after" if start > source_start else "before_or_same_time",
        "same_saved_configuration": True,
        "same_execution_mode": True,
        "execution_status": detail["status"],
        "affected_node": alias,
        "affected_node_executed": True,
        "affected_node_error_observed": any(bool(run.get("error")) for run in runs),
        "affected_node_output_items": sum(len(items) for items in outputs if items is not None),
        "detected_findings": len(findings),
        "success_with_no_detected_findings": detail["status"] == "success" and not findings,
    }


async def collect_comparisons(n8n, workflow, bundle: dict, source: dict) -> None:
    """One listing page, at most five detail GETs, 30 seconds total. No provider calls."""
    bundle["comparison_scope"] = {
        "listing_limit": 50,
        "detail_limit": 5,
        "window_hours": 24,
        "complete_history": False,
        "status": "collecting",
        "included": 0,
    }
    scope = bundle["comparison_scope"]
    bundle["limits"].append(
        "Comparison executions are a bounded sample, not a root-cause proof, error-rate "
        "estimate, repair test or recovery verification. External conditions may change."
    )
    try:
        async with asyncio.timeout(30):
            page = await n8n.executions(workflow_id=workflow.id)
            if not isinstance(page.get("data"), list):
                raise ValueError("Execution list unavailable")
            now = datetime.now(UTC)
            candidates = []
            for item in page["data"][:50]:
                started = timestamp(item.get("startedAt"))
                eid = str(item.get("id", ""))
                if (
                    eid
                    and eid != str(source.get("id"))
                    and item.get("status") in {"success", "error", "crashed", "canceled"}
                    and started is not None
                    and now - timedelta(hours=24) <= started <= now
                ):
                    candidates.append((started, eid))
            seen = set()
            for _, eid in sorted(candidates, reverse=True):
                if eid in seen:
                    continue
                seen.add(eid)
                if len(seen) > 5:
                    break
                detail = await n8n.execution(eid)
                fact = comparison(detail, workflow, bundle, source, eid)
                if fact is not None:
                    scope["included"] += 1
                    bundle["facts"].append(
                        {
                            "id": f"comparison_{scope['included']}",
                            "kind": "observed_execution_comparison",
                            "value": fact,
                        }
                    )
            scope["status"] = "sampled"
    except (IntegrationError, TimeoutError, ValueError, TypeError, KeyError, AttributeError):
        scope["status"] = "incomplete"
        bundle["limits"].append(
            "Some comparison evidence was unavailable; do not assume missing runs succeeded."
        )
