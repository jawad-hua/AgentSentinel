import json
import re
from typing import Protocol, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.integrations.n8n import IntegrationError
from app.integrations.rate_limits import RateLimited, retry_delay

T = TypeVar("T", bound=BaseModel)


class StructuredProvider(Protocol):
    async def generate(self, instruction: str, evidence: dict, schema: type[T]) -> T: ...


class GroqProvider:
    def __init__(
        self,
        http: httpx.AsyncClient,
        api_key: str,
        model: str,
        timeout: int = 60,
        secrets: tuple[str, ...] = (),
    ):
        self.http, self.api_key, self.model = http, api_key, model
        self.timeout, self.secrets = timeout, (*secrets, api_key)

    async def check(self) -> None:
        if not self.api_key:
            raise IntegrationError("Groq API key is not configured")
        try:
            response = await self.http.get(
                "https://api.groq.com/openai/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            response.raise_for_status()
            ids = {item["id"] for item in response.json()["data"]}
            if self.model not in ids:
                raise IntegrationError("Configured Groq model is not available")
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            raise IntegrationError("Groq connection check failed") from None

    async def generate(self, instruction: str, evidence: dict, schema: type[T]) -> T:
        if not self.api_key:
            raise IntegrationError("Groq API key is not configured")
        # JSON mode is portable; Pydantic is the mandatory schema enforcement boundary.
        # No repair, tool execution, or automatic retry follows a malformed response.
        if len(json.dumps(self.clean(evidence), separators=(",", ":"))) > 100_000:
            raise IntegrationError("Minimized AI evidence exceeds its size limit")
        payload = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 4096,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": instruction
                    + " Return only JSON matching this schema: "
                    + json.dumps(schema.model_json_schema(), separators=(",", ":")),
                },
                {
                    "role": "user",
                    "content": json.dumps(self.clean(evidence), separators=(",", ":")),
                },
            ],
        }
        try:
            async with self.http.stream(
                "POST",
                "https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json=payload,
                timeout=self.timeout,
            ) as response:
                if response.status_code == 429:
                    raise RateLimited(retry_delay(response.headers))
                if response.status_code in {401, 403}:
                    raise IntegrationError("Groq denied inference access; check credentials")
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 256_000:
                        raise IntegrationError("Groq output exceeds its size limit")
            choice = json.loads(content)["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ValueError("Incomplete generation")
            result = schema.model_validate_json(choice["message"]["content"])
            return schema.model_validate(self.clean(result.model_dump()))
        except (httpx.HTTPError, ValueError, KeyError, IndexError, TypeError, ValidationError):
            raise IntegrationError(
                "Groq generation failed or returned invalid structured output"
            ) from None

    def clean(self, value):
        """Defense in depth on generated text; upstream bodies are never logged."""
        if isinstance(value, dict):
            return {key: self.clean(child) for key, child in value.items()}
        if isinstance(value, list):
            return [self.clean(child) for child in value]
        if isinstance(value, str):
            for secret in self.secrets:
                if secret:
                    value = value.replace(secret, "[REDACTED]")
            value = re.sub(r"https?://[^\s]+", "[URL OMITTED]", value)
            value = re.sub(
                r"(?i)(bearer\s+|(?:token|password|secret|api[_-]?key)\s*[:=]\s*)[^\s,;]+",
                "[REDACTED]",
                value,
            )
        return value
