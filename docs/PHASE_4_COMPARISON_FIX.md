# Phase 4: real execution comparison evidence

The investigation collector now reads a bounded sample of actual n8n executions alongside the failed execution. Previously, a later successful execution was not available to the agents.

## Apply on Windows

1. Stop the AgentSentinel API with Ctrl+C. Preserve any local edits to the two modified Python files before merging this patch.
2. Extract this ZIP and merge its backend and docs folders into D:\AgentSentinel, replacing only the listed files. It contains no environment files, secrets, database, dependencies or migration.
3. In the existing activated backend PowerShell terminal:

```powershell
cd D:\AgentSentinel\backend
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Keep KILL_SWITCH=true and the controlled test target running in healthy mode. No frontend build is needed.

After startup, request another analysis of Incident #2 once. Inspect the new observed_execution_comparison facts: the collector must independently retrieve actual saved executions from n8n. Execution 50673 is eligible only if its saved details satisfy the checks and it is present in the bounded sample. A helper log alone is not imported as evidence. Existing investigation records remain unchanged.

## Evidence limits and safety

The collector reads one listing page (up to 50 records), at most five execution details from the last 24 hours, with a 30-second overall limit. It requires matching workflow ID, saved configuration fingerprint and execution mode, terminal timestamps, and actual execution of the affected node. Pinned, retried and partial executions are excluded. It applies the existing deterministic detector and configured output contract. API failures yield explicit incomplete evidence, never invented successes.

Only minimized facts are sent for analysis; URLs, payloads, credentials and raw node names are excluded. A successful comparison shows that the observed failure was not universal across the sampled executions. External conditions may have changed. It does not prove a root cause, successful repair or recovery.

Prompts now distinguish plausible explanations from supported causal hypotheses and ask for the smallest supported change. The validator may still reject the proposal. No policy, kill switch, approval or repair execution gate is bypassed. Do not repeatedly request analysis to obtain a preferred verdict.

## Validation

- Backend pytest: 69 passed, 2 skipped; existing Starlette/httpx deprecation warning.
- Backend Ruff passed.
- Real isolated n8n 2.15.1 test: saved same-configuration success collected; changed-configuration executions excluded; actual mutation/restore boundary checks passed.
- This patch has not completed the user's Groq-to-approval-to-healing acceptance test. Phase 4 remains in progress.
