"""Pure timing/policy contracts; no fabricated executions or API responses."""

import pytest

from app.integrations.n8n import IntegrationError
from app.integrations.rate_limits import RetryBudget, duration, retry_delay


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("7.66s", 7.66),
        ("2m59.56s", 179.56),
        ("100ms", 0.1),
        ("60", 60),
        ("0", 0),
        ("nan", None),
        ("inf", None),
        ("-1", None),
        ("bad", None),
        (None, None),
    ],
)
def test_duration_contract(value, expected):
    assert duration(value) == expected


def test_daily_reset_does_not_override_available_request_budget():
    assert (
        retry_delay(
            {
                "retry-after": "8",
                "x-ratelimit-reset-tokens": "7.66s",
                "x-ratelimit-reset-requests": "2h",
                "x-ratelimit-remaining-requests": "100",
            }
        )
        == 9
    )


def test_exhausted_daily_budget_and_missing_headers():
    assert (
        retry_delay(
            {
                "x-ratelimit-reset-requests": "2h",
                "x-ratelimit-remaining-requests": "0",
            }
        )
        == 7201
    )
    assert retry_delay({}) == 60


def test_retry_limits_are_enforced_without_consuming_denied_reservations():
    budget = RetryBudget()
    assert budget.reserve(60, False) == 60
    with pytest.raises(IntegrationError):
        budget.reserve(60, True)
    assert budget.retries == 1
    budget.reserve(60, False)
    budget.reserve(60, False)
    with pytest.raises(IntegrationError):
        budget.reserve(2, False)
    assert budget.waited == 180


def test_long_cooldowns_fail_closed():
    budget = RetryBudget()
    with pytest.raises(IntegrationError):
        budget.reserve(7201, False)
    assert budget.retries == 0
    budget.reserve(120, False)
    with pytest.raises(IntegrationError):
        budget.reserve(61, False)
