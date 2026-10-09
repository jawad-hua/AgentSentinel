# Phase 4 — small Windows checkpoints

Apply only to the existing Phase 3 project plus its rate-limit fix. No operational data,
.env files, credentials, database or installed dependencies are included in the ZIP.
Stop both application terminals before copying files. Back up your project and database with
the service stopped (include any SQLite -wal/-shm files). Preserve personal edits if any.

## 1. Copy

Merge the ZIP's folders into `D:\AgentSentinel`, replacing only matching manifest paths.
Do not delete existing folders. No frontend dependencies changed; `npm ci` is unnecessary.

## 2. Install the encryption dependency and migrate

In your activated backend PowerShell terminal, run one command at a time:

```powershell
cd D:\AgentSentinel\backend
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python ..\scripts\setup_repairs.py
python -m alembic upgrade head
python -m alembic current
```

Expected revision: `0004 (head)`. Setup preserves existing values and adds disabled repair
settings plus a generated snapshot key if absent. It never prints secrets. If an existing
`SNAPSHOT_ENCRYPTION_KEY` is blank, generate a valid key locally and set it securely; the
helper intentionally never overwrites existing keys. Do not paste .env or keys into chat.

## 3. Start and build

```powershell
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

In the frontend terminal:

```powershell
cd D:\AgentSentinel\frontend
npm run build
npm run start
```

For the 4 GB laptop, stop n8n while building if memory is tight, then start it again.
Open http://127.0.0.1:3000/incidents/1 (or your configured trusted console origin).
The historical blocked POST/404 incident must not offer an approvable repair.

## 4. Deliberate write enablement — only after startup checks

Do not enable writes merely to remove an empty state. First designate a dedicated, inactive,
unpublished workflow for maintenance, backed up in n8n. Keep it monitored. Keep execution
success/error data and manual executions saved in n8n. Avoid concurrent editors/pinned data.

Create a separate n8n API key for `workflow:update` (scope restrictions where your edition
supports them). Keep the existing read key for workflow/execution read/list. Store the new
key privately as `N8N_WRITE_API_KEY`. Set comma-separated exact IDs in `REPAIR_WORKFLOW_IDS`.
Set `REPAIRS_ENABLED=true` and, only when ready for controlled writes, `KILL_SWITCH=false`.
Retain `SNAPSHOT_ENCRYPTION_KEY` securely; losing it makes stored snapshots unreadable.
Restart the API after configuration changes. No browser control can enable a configured kill switch.

An eligible **new** real HTTP GET timeout/408/429/500/502/503/504 incident must complete all
five Groq agents, including independent validator acceptance. Never alter a saved AI result
or database row to manufacture eligibility. The Phase 3 POST/404 remains an honest blocked case.

Use **Prepare repair review**, inspect the actual diff and encryption/safety state, then
acknowledge exclusive maintenance and approve. Once status is verifying, reload the saved
workflow in n8n and execute it fully twice within 10 minutes. Leave AgentSentinel running.
A failure or missing confirmed recovery requests rollback; configuration drift escalates.
The original snapshot and timeline remain persisted. A rollback is not a healed result.

The master JSON only updates explanatory notes. Do not overwrite your imported workflow just
for those notes; its existing heartbeat branch remains unchanged. There is still one master file.

Stop at any error. Phase 5/Chaos Mode is not included in this patch.
