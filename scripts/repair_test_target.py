"""Loopback-only controlled HTTP fault for a designated Phase 4 test workflow.

Never writes to n8n or AgentSentinel. Successful probes forward the real backend
liveness response; the application must independently observe actual n8n executions.
"""

import argparse
import http.client
import json
import re
import threading
from collections import OrderedDict
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit


class FaultState:
    def __init__(self, workflow_id: str, mode: str, health_port: int):
        self.workflow_id, self.mode, self.health_port = workflow_id, mode, health_port
        self.attempts: OrderedDict[str, int] = OrderedDict()
        self.lock = threading.Lock()

    def attempt(self, execution_id: str) -> tuple[int, str]:
        with self.lock:
            count = self.attempts.get(execution_id, 0) + 1
            self.attempts[execution_id] = count
            self.attempts.move_to_end(execution_id)
            if len(self.attempts) > 4096:
                self.attempts.popitem(last=False)
            return count, self.mode


class Handler(BaseHTTPRequestHandler):
    server_version = "AgentSentinelControlledTarget/1"

    def log_message(self, *_args):
        pass

    def reply(self, status: int, body: bytes):
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):
        state: FaultState = self.server.fault_state
        url = urlsplit(self.path)
        query = parse_qs(url.query)
        workflow = query.get("workflow_id", [])
        execution = query.get("execution_id", [])
        if (
            len(self.path) > 1024
            or url.path != "/probe"
            or workflow != [state.workflow_id]
            or len(execution) != 1
            or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", execution[0])
            or set(query) != {"workflow_id", "execution_id"}
        ):
            self.reply(
                403, b'{"error":"Use the designated workflow and execution IDs"}'
            )
            return
        count, mode = state.attempt(execution[0])
        if mode == "persistent" or (mode == "transient" and count == 1):
            status = 503
            body = json.dumps(
                {
                    "error": "Intentional controlled HTTP fault",
                    "mode": mode,
                    "attempt": count,
                }
            ).encode()
        else:
            connection = http.client.HTTPConnection(
                "127.0.0.1", state.health_port, timeout=5
            )
            try:
                connection.request("GET", "/health/live")
                response = connection.getresponse()
                body = response.read(4097)
                if (
                    len(body) > 4096
                    or response.status != 200
                    or json.loads(body).get("status") != "alive"
                ):
                    raise ValueError("Backend liveness was not confirmed")
                status = 200
            except (OSError, http.client.HTTPException, ValueError, AttributeError):
                status, body = 502, b'{"error":"Actual backend liveness check failed"}'
            finally:
                connection.close()
        print(
            f"{datetime.now(UTC).isoformat()} execution={execution[0]} "
            f"attempt={count} mode={mode} HTTP={status}",
            flush=True,
        )
        self.reply(status, body)


def commands(state: FaultState):
    while True:
        try:
            command = input().strip().lower()
        except EOFError:
            return
        if command in {"transient", "persistent", "healthy"}:
            with state.lock:
                state.mode = command
            print(f"Controlled target mode: {command}", flush=True)
        else:
            print(
                "Commands: transient, persistent, healthy. Ctrl+C stops the target.",
                flush=True,
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workflow-id", required=True)
    parser.add_argument(
        "--mode", choices=("transient", "persistent", "healthy"), default="transient"
    )
    parser.add_argument("--port", type=int, default=9002)
    parser.add_argument("--health-port", type=int, default=8000)
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", args.workflow_id):
        parser.error("Invalid workflow ID")
    if not all(1024 <= port <= 65535 for port in (args.port, args.health_port)):
        parser.error("Ports must be between 1024 and 65535")
    state = FaultState(args.workflow_id, args.mode, args.health_port)
    try:
        server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    except OSError:
        raise SystemExit(
            "Cannot bind the loopback port; check whether it is already in use."
        ) from None
    server.fault_state = state
    print(
        f"Controlled test target listening on http://127.0.0.1:{args.port}/probe",
        flush=True,
    )
    print(f"Designated workflow: {args.workflow_id}; mode: {args.mode}", flush=True)
    print(
        "Commands: transient, persistent, healthy. Keep this terminal running.",
        flush=True,
    )
    threading.Thread(target=commands, args=(state,), daemon=True).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
