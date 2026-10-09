# Controlled test context

This incremental patch records a truthful local operator attestation about the shipped
repair test helper. It separates deliberate test faults and mode changes from observed
n8n facts. A later success after switching to healthy mode does not prove automatic
retry recovery or a transient external outage.

Registration performs GET-only checks of the actual saved failed execution, later
successful execution and current workflow. It requires the designated, inactive,
unpublished two-node manual/HTTP workflow and exact local probe configuration, matching
revision, actual HTTP 503 failure, full comparable success and reviewed helper source.
Running process identity and historical mode remain operator testimony, not independently
verified facts. No credentials or raw payloads are added to AI evidence.

The attestation is stored in the existing audit event table, expires after 24 hours,
and is revalidated for each investigation. Revision or designation mismatch excludes it.
It never approves a repair, overrides a validator, rewrites previous investigations,
changes the kill switch, or writes to n8n. No migration or new dependency is required.

## Apply

Keep repair writes paused. Stop the backend with Ctrl+C. Extract the ZIP into
D:\AgentSentinel, merging the backend, scripts and docs folders. Replace only the
listed files. Preserve .env, database, snapshots and unrelated work.

From D:\AgentSentinel\backend, register the user's observed test:

```powershell
.\.venv\Scripts\python.exe ..\scripts\register_test_context.py --incident-id 2 --healthy-execution 50673
```

Type ATTEST only if you actually ran the unmodified shipped helper, the failed run
was in transient mode, and you switched to healthy before that successful execution.
Anything else cancels without recording testimony. The IDs above refer to the actual
operator-reported incident and execution; they are not seeded examples.

Restart the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Request one new analysis on the incident and inspect test_operator_context in its
evidence. The validator can still reject a proposal. Keep writes paused until a new
eligible proposal has been reviewed. Do not repeatedly rerun analysis to obtain approval.

## Verification performed

Ruff passed; existing backend suite: 69 passed, 2 skipped. Actual isolated n8n 2.15.1
and the real shipped helper verified registration and inclusion against real saved
executions, plus exclusion without registration or with revision/designation mismatch.
The same live run checked the binaryMode write compatibility fix, two patched successful
executions, persistent failure, restore/readback and drift protection.

These are engineering checks, not a claim that the user's repair healed. The user's
complete Groq-to-approval-to-recovery/rollback acceptance remains pending. No frontend
files changed; frontend checks were not repeated for this patch.
