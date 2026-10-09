# Controlled HTTP test target — Phase 4 acceptance support

NEW FILE: `scripts/repair_test_target.py`
NEW FILE: `docs/PHASE_4_TEST_TARGET.md`
NEW FILE: `docs/PHASE_4_TEST_TARGET_MANIFEST.md`
No existing files are replaced. No extra n8n workflow JSON is created.

This is an opt-in local fault-injection helper for the designated test workflow, not a
production endpoint or the Phase 5 Chaos Mode UI. It never writes incidents, AI responses,
approvals, repair state or n8n configuration. All application results must be generated
from real executions and the actual inference pipeline.

## Start (keep the API and console running)

From a new Windows PowerShell terminal:

```powershell
cd D:\AgentSentinel
.\backend\.venv\Scripts\python.exe .\scripts\repair_test_target.py --workflow-id 3Zn4KGcN90F5fb9z
```

Default binding: 127.0.0.1:9002. It probes the actual AgentSentinel /health/live endpoint on
127.0.0.1:8000. No dependencies beyond Python's standard library, credentials or .env edits.
Keep KILL_SWITCH=true until a genuine eligible repair proposal has been reviewed.

## Test node (do this after the helper starts)

Only in AgentSentinel Repair Test, keep Method GET, Authentication None, Retry On Fail OFF.
Set the HTTP Request URL to Expression mode and paste the expression below. The editor may
show the expression without the leading `=`; use its Expression control rather than inserting
an expression as fixed text.

```javascript
{{ 'http://127.0.0.1:9002/probe?workflow_id=' + $workflow.id + '&execution_id=' + $execution.id }}
```

Save, keep unpublished, and execute the full workflow once. The first request for each actual
execution ID intentionally receives HTTP 503. A retry within the SAME execution reaches the
real backend liveness endpoint; HTTP 200 is returned only if that actual check succeeds.
Executing again without retries creates a new execution ID and fails again. Do not manually
turn retries on to manufacture a healed result. The approved AgentSentinel patch must do that.

Wait for real monitoring/analysis. Inspect the observed HTTP status and all five agent results.
A legitimate blocked/no_safe_fix outcome must remain blocked; do not fabricate eligibility.
After a supported repair is prepared and approved through the existing controls, run the
saved patched workflow fully twice for its real verification window.

## Fault controls and cleanup

Type a command in the helper terminal and press Enter:

- `transient`: first request of each execution fails; retries reach real backend health.
- `persistent`: every valid probe fails with a deliberate real 503, for rollback verification.
- `healthy`: each valid probe forwards the actual backend health check.

Ctrl+C stops only this helper. Keep it running throughout a repair verification window.
No state is written to disk. Request counters are bounded to the 4,096 most recently used IDs.
Do not manually send probes with the workflow's execution IDs: that changes actual attempt
counts and would contaminate the test evidence.

Workflow ID matching is a routing guard, not authentication. Keep this loopback-only and use
it solely for the dedicated local workflow. It does not verify the supplied execution ID with
n8n; AgentSentinel independently obtains genuine execution evidence from n8n's public API.
Backend liveness success by itself never marks an incident healed.

Docker-based n8n cannot reach a Windows loopback listener through its own 127.0.0.1. These steps
are for the already verified local n8n-to-127.0.0.1 setup; do not expose this helper publicly.

## Verification completed

Ruff passed. Tested this exact helper with real n8n 2.15.1 and the actual FastAPI liveness
endpoint: execution 1 failed, retry-patched executions 2/3 succeeded, persistent-fault
execution 4 failed, and execution 5 failed after restoring the original retry configuration.
These are isolated test runs, not the user's executions or a completed AI-approved repair.
