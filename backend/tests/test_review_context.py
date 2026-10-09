"""Boundary tests for minimized configuration and unchanged policy; no provider simulation."""

import pytest

from app.investigation.evidence import error_handling
from app.investigation.policy import assess
from tests.test_investigation import policy_input


def test_saved_error_handling_is_minimized_and_defaults_are_labeled():
    result = error_handling({"credentials": "private", "parameters": {"url": "private"}})
    assert result["onError"] == "stopWorkflow"
    assert result["continueOnFail"] is False
    assert "defaults" in result["source"]
    assert "private" not in str(result)
    for mode in ("continueRegularOutput", "continueErrorOutput"):
        assert error_handling({"onError": mode})["onError"] == mode
    assert error_handling({"continueOnFail": True})["continueOnFail"] is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("onError", "private-unknown-value"),
        ("onError", None),
        ("continueOnFail", "false"),
        ("disabled", 0),
    ],
)
def test_unknown_error_handling_is_not_coerced_or_exposed(field, value):
    assert error_handling({field: value})[field] == "unknown"


def test_risk_block_still_wins_even_with_stop_on_error():
    inputs = policy_input()
    inputs[0]["nodes"][0]["error_handling"] = error_handling({})
    inputs[4].level = "blocked"
    result = assess(*inputs)
    assert result["decision"] == "blocked"
    assert result["execution_allowed"] is False
    assert "Risk agent requested a block." in result["reasons"]


def test_nonblocked_preapproval_review_never_authorizes_execution():
    inputs = policy_input()
    inputs[0]["nodes"][0]["error_handling"] = error_handling({})
    result = assess(*inputs)
    assert result["decision"] == "human_review_required"
    assert result["approval_status"] == "not_requested"
    assert result["execution_allowed"] is False
