# n8n public API write compatibility fix

## Cause and limits

The operator's workflow returned settings binaryMode=separate and executionOrder. In installed n8n 2.15.1, workflowSettings rejects additional properties and omits binaryMode from its public PUT schema. The previous serializer copied this field into PUT. A real isolated n8n 2.15.1 test reproduced HTTP 400 with this payload. The historical operator attempt did not retain its HTTP code; this is a reproduced compatibility defect, not recovered historical error evidence.

## Change

The serializer omits binaryMode from outgoing settings only. n8n 2.15.1 merges omitted settings from the saved workflow. Full encrypted snapshots, revision hashes and read-back checks still retain binaryMode, so loss or unexpected change cannot be reported as a successful repair. No unknown settings are silently dropped. Update and restore both use this serializer. Workflows remain restricted to inactive/unpublished exclusive maintenance.

HTTP update errors now retain status codes and record a repair.write_error audit event before read-back reconciliation. Bodies, URLs and credentials are never logged. Writes are not blindly retried. Existing historical repair records are not edited or reopened.

## Apply

Keep runtime writes paused. Stop the API, merge this archive into D:\AgentSentinel (preserve unrelated local edits), then restart in the activated backend PowerShell:

```powershell
cd D:\AgentSentinel\backend
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

No database migration, dependencies or frontend rebuild. Do not change binaryMode manually. This fix does not authorize a repair or bypass the latest blocked investigation. Resolve missing endpoint evidence before requesting another analysis. A later eligible proposal requires its own snapshot and explicit approval.

## Validation

- Ruff passed; pytest 69 passed, 2 skipped; existing Starlette/httpx deprecation warning.
- Real isolated n8n 2.15.1: original serializer reproduced HTTP 400; fixed PUT and read-back preserved binaryMode=separate; two patched successful full executions; persistent patched failure; snapshot restore and read-back; post-restore failure and drift guard passed.
- This was direct deterministic boundary testing, not an end-to-end Groq-approved repair. Phase 4 acceptance remains incomplete.
