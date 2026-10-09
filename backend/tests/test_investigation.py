"""Adversarial contract vectors, not operational data or mocked provider calls."""

import pytest
from pydantic import ValidationError

from app.integrations.llm import GroqProvider
from app.investigation.evidence import observed_facts
from app.investigation.policy import assess
from app.investigation.schemas import Claim, Diagnosis, Fix, Risk, Validation, validate_references
from tests.test_foundation import auth


def test_analysis_scope_and_missing_incident(client, settings):
    path = "/api/v1/incidents/1/investigations"
    assert client.post(path).status_code == 401
    assert client.post(path, headers=auth(settings, "ingest")).status_code == 401
    assert client.get(path, headers=auth(settings, "ingest")).status_code == 401
    assert client.post(path, headers=auth(settings)).status_code == 404
    assert client.get(path, headers=auth(settings)).status_code == 404


@pytest.mark.parametrize(
    "field,value",
    [("url", "https://invalid.example"), ("jsCode", "return []"), ("retryOnFail", "true")],
)
def test_code_and_coercion_rejected(field, value):
    with pytest.raises(ValidationError):
        Fix(
            disposition="propose",
            rationale="Security contract input",
            evidence_ids=["e"],
            changes=[{"node": "node_0", "field": field, "value": value}],
            verification_plan=["Operator review required"],
        )


def test_citations_fail_closed():
    for refs in [["missing"], ["e", "e"]]:
        with pytest.raises(ValueError):
            validate_references(
                Claim(statement="Untrusted claim", evidence_ids=refs), [{"id": "e"}]
            )


def policy_input(method="GET", status=503, value=True):
    # Policy truth-table vectors; these are never stored as executions or agent output.
    return [
        {
            "revision_matches": True,
            "facts": [{"id": "e", "value": {"http_status": status}}],
            "nodes": [
                {
                    "node": "node_0",
                    "type": "n8n-nodes-base.httpRequest",
                    "executed": True,
                    "error_observed": True,
                    "config": {"method": method, "retryOnFail": False},
                }
            ],
        },
        Diagnosis(
            hypotheses=[Claim(statement="Contract hypothesis", evidence_ids=["e"])],
            missing_evidence=[],
            next_steps=["Review"],
        ),
        Fix(
            disposition="propose",
            rationale="Contract proposal",
            evidence_ids=["e"],
            changes=[{"node": "node_0", "field": "retryOnFail", "value": value}],
            verification_plan=["Review"],
        ),
        Validation(
            accepted=True,
            supported_hypotheses=[0],
            evidence_ids=["e"],
            rationale="Contract review",
            concerns=[],
        ),
        Risk(level="low", evidence_ids=["e"], rationale="Contract risk input", hazards=[]),
        "http_failure",
    ]


@pytest.mark.parametrize(
    "method,status,value",
    [
        ("POST", 503, True),
        ("DELETE", 503, True),
        ("GET", 404, True),
        ("GET", 401, True),
        ("GET", 503, 1),
        ("GET", 503, False),
    ],
)
def test_policy_overrides_model(method, status, value):
    result = assess(*policy_input(method, status, value))
    assert result["decision"] == "blocked"
    assert result["execution_allowed"] is False


def test_validator_and_staleness_block():
    inputs = policy_input()
    inputs[3].accepted = False
    assert assess(*inputs)["decision"] == "blocked"
    inputs[3].accepted = True
    inputs[0]["revision_matches"] = False
    assert assess(*inputs)["decision"] == "blocked"
    inputs[3].supported_hypotheses = [4]
    with pytest.raises(ValueError):
        assess(*inputs)


def test_allowlist_never_authorizes_execution():
    result = assess(*policy_input())
    assert result["decision"] == "human_review_required"
    assert result["risk_level"] == "medium"
    assert result["execution_allowed"] is False
    assert result["approval_status"] == "not_requested"
    assert result["confidence"]["supported_hypotheses"] == 1
    assert "Not probability" in result["confidence"]["meaning"]


def test_minimization():
    assert observed_facts(
        {"http_status": 404, "error_type": "NodeApiError", "reason": "private", "body": "private"}
    ) == {"http_status": 404, "error_type": "NodeApiError"}
    provider = GroqProvider(None, "private-provider-value", "model")
    clean = provider.clean(
        {"text": "private-provider-value https://private.invalid/path token=secret"}
    )
    assert "private" not in str(clean)
    assert "token=secret" not in str(clean)
