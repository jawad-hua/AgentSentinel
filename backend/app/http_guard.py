"""Bound resource use before parsing bodies; one process, no external cache required."""

import asyncio
import time
from collections import deque

from starlette.responses import JSONResponse


class HttpGuard:
    def __init__(self, app):
        self.app = app
        self.requests = deque()
        self.streams = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def deny(code, detail):
            response = JSONResponse(
                {"detail": detail},
                status_code=code,
                headers={"Cache-Control": "no-store", "Retry-After": "60"}
                if code == 429
                else {"Cache-Control": "no-store"},
            )
            await response(scope, receive, send)

        now = time.monotonic()
        while self.requests and self.requests[0] <= now - 60:
            self.requests.popleft()
        # Global rather than IP-keyed: forwarded headers cannot evade this bounded budget.
        if len(self.requests) >= 600:
            return await deny(429, "Request budget exceeded; retry later")
        self.requests.append(now)
        if scope["method"] in {"POST", "PUT", "PATCH"}:
            headers = dict(scope["headers"])
            try:
                length = int(headers.get(b"content-length", b"0"))
            except ValueError:
                return await deny(400, "Invalid content length")
            if length < 0 or length > 65536:
                return await deny(413, "Request too large")
            body = bytearray()
            deadline = time.monotonic() + 10
            try:
                while True:
                    message = await asyncio.wait_for(receive(), max(0, deadline - time.monotonic()))
                    if message["type"] == "http.disconnect":
                        return
                    body.extend(message.get("body", b""))
                    if len(body) > 65536:
                        return await deny(413, "Request too large")
                    if not message.get("more_body", False):
                        break
            except TimeoutError:
                return await deny(408, "Request body timed out")
            original_receive = receive
            delivered = False

            async def bounded_receive():
                nonlocal delivered
                if not delivered:
                    delivered = True
                    return {"type": "http.request", "body": bytes(body), "more_body": False}
                return await original_receive()

            receive = bounded_receive
        streaming = scope["path"] == "/api/v1/events"
        if streaming and self.streams >= 8:
            return await deny(429, "Too many event streams")
        if streaming:
            self.streams += 1
        try:
            await self.app(scope, receive, send)
        finally:
            if streaming:
                self.streams -= 1
