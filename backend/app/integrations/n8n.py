import json
from typing import Any
from urllib.parse import quote

import httpx


class IntegrationError(Exception):
    """Safe public error; upstream bodies and credentials are never attached."""

    def __init__(self, message: str, status_code: int | None = None):
        super().__init__(message)
        self.status_code = status_code


class N8nClient:
    """Bounded public API client; writes use a separately configured credential."""

    def __init__(self, http: httpx.AsyncClient, base_url: str, api_key: str):
        self.http, self.base_url, self.api_key = http, base_url, api_key

    async def get(self, path: str, params: dict | None = None) -> dict[str, Any]:
        if not self.api_key:
            raise IntegrationError("n8n API key is not configured")
        try:
            async with self.http.stream(
                "GET",
                f"{self.base_url}/api/v1/{path}",
                params=params,
                headers={"X-N8N-API-KEY": self.api_key},
            ) as response:
                response.raise_for_status()
                content = bytearray()
                async for chunk in response.aiter_bytes():
                    content.extend(chunk)
                    if len(content) > 8 * 1024 * 1024:
                        raise IntegrationError("n8n response exceeds the 8 MiB evidence limit")
                data = json.loads(content)
            if not isinstance(data, dict):
                raise ValueError("Expected object")
            return data
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            raise IntegrationError(
                f"n8n request failed (HTTP {code}); check access and service", code
            ) from None
        except (httpx.HTTPError, ValueError):
            raise IntegrationError(
                "n8n request failed; check URL, credentials and service"
            ) from None

    async def workflows(self, cursor: str | None = None) -> dict[str, Any]:
        return await self.get("workflows", {"limit": 100, **({"cursor": cursor} if cursor else {})})

    async def executions(
        self, cursor: str | None = None, workflow_id: str | None = None
    ) -> dict[str, Any]:
        return await self.get(
            "executions",
            {
                "limit": 50,
                "includeData": "false",
                **({"cursor": cursor} if cursor else {}),
                **({"workflowId": workflow_id} if workflow_id else {}),
            },
        )

    async def execution(self, execution_id: str) -> dict[str, Any]:
        return await self.get(f"executions/{quote(execution_id, safe='')}", {"includeData": "true"})

    async def workflow(self, workflow_id: str) -> dict[str, Any]:
        return await self.get(f"workflows/{quote(workflow_id, safe='')}")

    async def check(self) -> None:
        data = await self.get("workflows", {"limit": 1})
        if not isinstance(data.get("data"), list):
            raise IntegrationError("n8n returned an unexpected public API response")

    async def update_workflow(self, workflow_id: str, body: dict) -> None:
        if not self.api_key:
            raise IntegrationError("n8n write API key is not configured")
        try:
            async with self.http.stream(
                "PUT",
                f"{self.base_url}/api/v1/workflows/{quote(workflow_id, safe='')}",
                headers={"X-N8N-API-KEY": self.api_key},
                json=body,
            ) as response:
                response.raise_for_status()
                # Success is established by a separate GET, never this response body.
        except httpx.HTTPStatusError as exc:
            code = exc.response.status_code
            raise IntegrationError(
                f"n8n update returned HTTP {code}; read-back reconciliation required", code
            ) from None
        except httpx.HTTPError:
            raise IntegrationError("n8n write outcome requires read-back reconciliation") from None
