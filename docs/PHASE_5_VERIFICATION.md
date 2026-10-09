# Phase 5 verification

## Implemented

- Database migration 0005: explicit Chaos target designation, fault sessions and actual HTTP probe
  attempts. No operational records are seeded by migrations or packaging.
- War Room with workflow freshness, selected incident, real stage graph, persisted events,
  repair outcomes and documented SQL-derived metrics. Unavailable and empty states are distinct.
- Authenticated, allowlisted loopback probe: healthy liveness, first-attempt transient 503,
  persistent 503, explicit stop and 30-minute expiry. Expiry returns 410, never false success.
- Baseline checks use the actual saved n8n execution, exact workflow configuration, full manual
  trace and a correlated real healthy probe response. No n8n/Groq response is simulated.
- Controlled response evidence is correlated with saved failed executions before AI analysis.
  One automatic investigation per armed session supports deduplicated existing incidents.
- Normal triage, independent validation, risk classification, policy, snapshot and approval remain.
  Fault conditions cannot be changed while a repair holds the workflow. Approval rejects stopped
  or expired experiment context. Configured kill switch blocks the probe and fault injection.
- Existing incident detail contains evidence, interpretation, confidence coverage, diff and timeline.
  Rolled-back records now explicitly say that restoration is not a healed outcome.

## Checks run in the build environment

- Ruff: backend and new setup script passed.
- Pytest: **112 passed, 2 skipped**. Live provider checks require user credentials.
- Migration upgrade/downgrade/schema-drift checks included in the backend suite.
- Real local HTTP probe contract: 503 then 200 persisted; expiry 410; wrong authentication rejected;
  no fabricated incident from probe requests; kill switch produces no successful response.
- Configuration vectors reject external URL, published workflows, executable extra nodes,
  error suppression and proxy options. These test vectors are not operational n8n records.
- Frontend ESLint and production Next.js/TypeScript build passed.
- Actual FastAPI + production Next.js smoke: empty migrated database, readiness, authenticated
  API, same-origin proxy, rejected foreign origin, invalid target input, disabled Chaos guard,
  and no server tokens in rendered HTML.
- Chromium desktop (1440 px) and mobile (390 px): inspected real empty state; SSE connected;
  all graph nodes idle; Operations navigation worked; no page errors or horizontal overflow.
- Exactly one workflow JSON, no embedded credentials; static workflow structure check passed.

An existing Starlette/httpx deprecation warning remains. It is not suppressed. No new runtime
package was added. The build uses one Next.js worker; Windows RAM behavior remains a user-side check.

## Prior live evidence retained (Phase 4)

The operator supplied actual persisted records and n8n logs:
- Repair 2 healed, successful saved patched executions 66491 and 66561, 2026-10-07.
- Repair 3 rolled back after failed execution 83654 (three real 503 attempts), restored configuration
  confirmed by read-back at 2026-10-08 04:30:12 UTC.
These are historical acceptance evidence, not verification of the new Phase 5 probe or a new repair.

## Still required on the user's machine

- Apply migration 0005 and build/start the new console.
- Opt in and assign the ingest credential to the dedicated test node; verify the updated n8n
  template/configuration in the user's installed n8n version.
- Execute a healthy baseline and a real transient experiment through monitoring, actual Groq
  analysis, independent validation, explicit approval and full execution verification.
- Observe the red-to-green state and correlated requests/events in the War Room.
- Confirm responsive UI with the user's real history and real running agent stages.

Phase 5 is not declared accepted solely from local tests. Phase 6 has not begun.
The new flow intentionally retains manual n8n execution and human approval; no unsupported
public-API execution endpoint or hidden replay is used.
