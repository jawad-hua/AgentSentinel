"""Configuration boundary vectors and real empty-database checks; no provider responses."""

import asyncio
import copy
from types import SimpleNamespace

import pytest

from app.investigation.repair_history import collect_repair_history, comparable_baseline


def configuration():
    return {
        "nodes": [
            {
                "id": "contract-node",
                "name": "contract-node",
                "type": "n8n-nodes-base.httpRequest",
                "parameters": {"method": "GET", "url": "contract-value"},
            }
        ],
        "connections": {},
        "settings": {},
    }


def test_historical_comparison_allows_only_target_retry_difference():
    original = configuration()
    current = copy.deepcopy(original)
    current["nodes"][0].update(retryOnFail=True, maxTries=3, waitBetweenTries=1000)
    assert comparable_baseline(original, current, "node_0")
    assert "retryOnFail" not in original["nodes"][0]
    assert current["nodes"][0]["retryOnFail"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("parameters", {"method": "POST", "url": "contract-value"}),
        ("parameters", {"method": "GET", "url": "changed"}),
        ("credentials", {"contract": "changed"}),
        ("continueOnFail", True),
        ("disabled", True),
        ("id", "different-node"),
    ],
)
def test_historical_comparison_rejects_other_changes(field, value):
    original = configuration()
    current = copy.deepcopy(original)
    current["nodes"][0][field] = value
    assert not comparable_baseline(original, current, "node_0")


def test_historical_comparison_rejects_settings_and_other_node_drift():
    original = configuration()
    current = copy.deepcopy(original)
    current["settings"]["executionOrder"] = "changed"
    assert not comparable_baseline(original, current, "node_0")
    current = copy.deepcopy(original)
    original["nodes"].append(copy.deepcopy(original["nodes"][0]))
    current["nodes"].append(copy.deepcopy(original["nodes"][0]))
    current["nodes"][1]["retryOnFail"] = True
    assert not comparable_baseline(original, current, "node_0")
    assert not comparable_baseline(original, current, "node_9")


def test_empty_history_does_not_create_evidence_or_call_providers(client, settings):
    bundle = {"facts": [], "limits": []}
    asyncio.run(
        collect_repair_history(
            None,
            client.app.state.sessions,
            settings,
            1,
            SimpleNamespace(id="contract-workflow"),
            {},
            bundle,
        )
    )
    assert bundle["facts"] == []
    assert bundle["limits"] == []
    assert bundle["repair_history_scope"]["included"] == 0


@pytest.mark.parametrize(
    "field,value",
    [
        ("staticData", {"contract": "changed"}),
        ("pinData", {"contract": "changed"}),
    ],
)
def test_historical_comparison_rejects_state_drift(field, value):
    original = configuration()
    current = copy.deepcopy(original)
    current[field] = value
    assert not comparable_baseline(original, current, "node_0")
