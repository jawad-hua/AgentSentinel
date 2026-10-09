# Phase 4 verification — October 6, 2026

## Checks completed in the isolated development environment

| Check | Result |
| --- | --- |
| Ruff | Passed |
| Backend pytest | 68 passed, 2 opt-in live tests skipped |
| Alembic upgrade/downgrade/upgrade and schema drift | Passed in temporary databases |
| Encryption round-trip and wrong-key rejection | Passed |
| Retry field/value/method/structure gates | Passed contract tests |
| Inactive/unpublished, pinned-data, disabled/error-suppressing node gates | Passed contract tests |
| Admin/ingest separation, invalid submission, unknown repair/recovery denial | Passed |
| Runtime pause cannot override configured kill switch | Passed |
| Frontend ESLint and TypeScript | Passed |
| Next.js 16.3.8 production build | Passed |
| Real API + console desktop/mobile browser | Passed, 1440/390 px, no horizontal overflow |
| Real repair empty state; blocked/missing proposal cannot prepare | Passed |
| Same-origin safety action; foreign-origin rejection | Passed |
| Browser uncaught errors | Zero in smoke check |
| Single master workflow, no credential material in JSON | Passed |

Contract inputs are configuration/security vectors in temporary tests. They are not saved
as incidents, workflow executions, AI decisions or dashboard history. No mocked n8n/Groq
responses or operational seeds were used.

## Actual n8n 2.15.1 mutation boundary check

Started an isolated real n8n instance with a fresh database and a dedicated temporary workflow
derived in memory from the single master file. A local controlled HTTP dependency genuinely
returned alternating 503/200 responses, then persistent 503. Actual executions were saved by n8n.

- Execution 1: real HTTP 503 failure; monitor persisted the actual incident.
- Saved the actual original workflow through encrypted snapshot round-trip.
- Applied only `retryOnFail=true` using public API PUT and verified the subsequent GET.
- Executions 2 and 3: real successful runs of the patched workflow; affected node executed.
- Execution 4: genuine persistent failure with retries enabled; verifier classified failure.
- Restored the original snapshot through PUT and confirmed read-back matched it.
- Execution 5: failure with original retry configuration restored.
- A real operator configuration change produced a different revision guard.

The check revealed that public PUT inserts documented defaults `callerPolicy` and
`availableInMCP`. Canonicalization now treats only their exact verified defaults as equivalent;
non-default changes still invalidate the fingerprint. Re-ran mutation checks successfully.

This is a direct deterministic mutation-boundary test, **not an AI-approved end-to-end repair**.
The test did not invent five successful agents, persisted approvals or a HEALED incident.
Browser screenshots show only the actual monitored failures and honest repair empty state.

## Required configured-machine acceptance

No Groq key was available in the isolated environment. The user has verified all five real
Phase 3 agents on a blocked historical POST/404 incident. For Phase 4, still verify:

1. A new eligible actual GET/HEAD/OPTIONS failure and all five real Groq stage outputs.
2. Prepare encrypted snapshot, inspect actual diff, approve/reject and verify persisted decisions.
3. Approve on an explicitly designated inactive workflow under exclusive maintenance.
4. Worker patch + two real executions + observation window → HEALED with actual execution IDs.
5. A failed verification → safe worker rollback/escalation, including kill switch pause and restart
   reconciliation on the dedicated test workflow. Do not test crash/concurrent-edit behavior in production.

Restart-intent and rollback-worker paths are implemented and reviewed, but this report does
not claim live crash-injection or complete AI-to-approval-to-worker acceptance. No public-hosting,
Windows process, PostgreSQL, 4 GB peak-memory or other n8n-version validation is claimed.

One existing upstream Starlette TestClient/httpx deprecation warning remains; tests pass and
no warning was suppressed. Phase 5 is not started. Keep writes disabled until local setup and
explicit controlled-workflow acceptance steps are ready.
