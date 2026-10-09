"""Parse only documented rate-limit timing headers; never retain provider error bodies."""

import math
import re
from collections.abc import Mapping

from app.integrations.n8n import IntegrationError


class RateLimited(IntegrationError):
    def __init__(self, seconds: int):
        super().__init__(f"Groq rate limit reached; suggested retry after {seconds} seconds", 429)
        self.retry_after_seconds = seconds


def duration(value: str | None) -> float | None:
    if not value or len(value) > 80:
        return None
    try:
        seconds = float(value)
    except ValueError:
        parts = re.findall(r"(\d+(?:\.\d+)?)(ms|s|m|h)", value)
        if not parts or "".join(n + unit for n, unit in parts) != value:
            return None
        seconds = sum(
            float(n) * {"ms": 0.001, "s": 1, "m": 60, "h": 3600}[unit] for n, unit in parts
        )
    return seconds if math.isfinite(seconds) and seconds >= 0 else None


def retry_delay(headers: Mapping[str, str]) -> int:
    direct = duration(headers.get("retry-after"))
    candidates = [direct] if direct is not None else []
    # Token reset can apply even when remaining tokens > 0 but below the next request's cost.
    token_reset = duration(headers.get("x-ratelimit-reset-tokens"))
    if token_reset is not None:
        candidates.append(token_reset)
    if headers.get("x-ratelimit-remaining-requests") == "0":
        request_reset = duration(headers.get("x-ratelimit-reset-requests"))
        if request_reset is not None:
            candidates.append(request_reset)
    # Provider supplied no usable hint: a conservative one-minute local fallback, not a quota claim.
    return max(2, math.ceil(max(candidates)) + 1) if candidates else 60


class RetryBudget:
    """At most three extra requests and 180 total waiting seconds per investigation."""

    def __init__(self):
        self.retries = 0
        self.waited = 0

    def reserve(self, seconds: int, stage_retried: bool) -> int:
        if stage_retried or self.retries >= 3:
            raise IntegrationError(
                "Groq rate limit persists; bounded retries exhausted. Check Groq limits."
            )
        if seconds > 120 or self.waited + seconds > 180:
            raise IntegrationError(
                f"Groq requests a {seconds}-second cooldown beyond this run's wait budget; "
                "check account limits before requesting another analysis."
            )
        self.retries += 1
        self.waited += seconds
        return seconds
