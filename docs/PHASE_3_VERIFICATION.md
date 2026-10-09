# Phase 3 verification — October 6, 2026

## Completed checks

- Backend Ruff: passed.
- Backend pytest: 32 passed, 2 skipped (explicit live n8n/inference opt-ins).
- Alembic upgrade/downgrade/upgrade and schema drift check: passed in temporary database.
- Frontend ESLint, TypeScript and Next.js production build: passed.
- Actual isolated n8n Community 2.15.1 workflow execution: success → real HTTP 503 → success.
- Read-only collection of the real failed execution, node error flags and configuration: passed.
- Exact known default normalization and actual changed-URL fingerprint detection: passed.
- Secret marker, endpoint URL and raw node name exclusion from collected evidence: passed.
- Missing Groq configuration rejects the API action; no successful inference is fabricated.
- Direct pipeline failure-path check using the real n8n evidence: collection/start/failure events
  persisted, real unconfigured provider refused inference, agent output remained null and claim released.
- Browser against actual FastAPI + Next.js + n8n observations: incident detail, SSE connected,
  evidence expansion, disabled unconfigured analysis control, cross-origin 403 rejection,
  desktop/mobile layout and zero uncaught page errors passed. Screenshots reviewed.
- Adversarial schema/policy checks cover forbidden fields/code, string-to-boolean coercion,
  invalid evidence citations, HTTP 404/401 retry blocks, POST/DELETE retry blocks, validator
  rejection, stale configuration, invalid hypothesis references and no execution authorization.

Tests use isolated databases. Policy truth-table inputs are contract validation vectors,
not synthetic operational records or mocked provider responses. Real n8n QA data and all
QA credentials remain outside the shipped repository/ZIP. No operational seed data exists.

## Pending live acceptance

No Groq credential is available in this development environment. Successful real inference,
all five stage outputs, schema compliance for the user's selected model and human assessment
of diagnosis quality MUST be verified on the user's configured laptop. No provider response
has been mocked and no generated diagnosis is claimed here.

The explicit `tests/test_live_investigation.py` test consumes actual Groq calls only when
both opt-in environment variables are set (see PHASE_3_SETUP.md). It never modifies n8n.
Frontend rendering of successful AI stage contents and proposal diffs awaits those real
outputs; failure/empty/observed-evidence rendering has been verified without inventing data.
Windows migration/build/start and peak memory on the 4 GB laptop also remain user checks.

## Existing limitations

The earlier development-only braces/ESLint dependency advisory remains unresolved; no
lockfiles or dependencies were changed in this patch. Do not use npm audit fix --force.
Starlette's existing httpx test-client deprecation warning remains visible; tests pass.
This is a loopback-only, single-operator, single-process release, not an internet-ready
multi-user service. AI has no tools or write access. The available proposal class is narrow:
bounded retries on eligible read-only HTTP nodes. Unsupported fixes explicitly escalate.

## Phase 2 user acceptance recorded

On the user's Windows instance, schema 0002 and frontend build passed, 22 real workflows
synced, Master execution 33597 succeeded, deliberately changed test URL produced execution
33966 with NodeApiError / HTTP 404, and one persisted incident/occurrence appeared with live
updates and timeline. The user restored the URL and confirmed success, then authorized
Phase 3. These user records are not bundled in the patch.

Phase 3 is implementation-ready, not acceptance-complete until the real inference gate passes.
