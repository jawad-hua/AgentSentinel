# Phase 3 — incremental installation (Windows PowerShell)

Stop the API and console with Ctrl+C. Keep your existing project backup.
Extract this patch **inside `D:\AgentSentinel`**, replacing matching files.
Do not replace `.env`, `.env.local`, databases or n8n credentials.
Dependencies are unchanged; no `npm ci` or pip download is needed.

## Checkpoint 1: database

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\Activate.ps1
python -m alembic upgrade head
python -m alembic current
```

Expected schema: `0003 (head)`. Existing incidents/heartbeats are preserved.

## Checkpoint 2: service

```powershell
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Use one process/worker. Keep this window open.

## Checkpoint 3: console (second PowerShell)

```powershell
cd D:\AgentSentinel\frontend
npm run build
npm start
```

On a 4 GB machine, stop n8n temporarily during the build if memory is tight;
start it again before investigation. The single n8n master remains compatible;
no reimport is required (only an explanatory note changed).

## Checkpoint 4: real inference acceptance

Open http://localhost:3000/incidents/1 and select **Investigate incident**.
This sends minimized evidence to your configured Groq model, five stage calls plus at most three bounded HTTP 429 retries (eight calls maximum).
No workflow is modified. Do not send API keys in chat.

The existing HTTP 404 execution was manually repaired during Phase 2 acceptance.
Analysis of that saved failure must not claim an automatic repair. Changed configuration
or lack of a supported repair may correctly end in `blocked` / `escalated`.
Inspect all completed stage outputs, evidence references, policy and timeline.
For successful complete pipeline acceptance, observe Triage, Diagnosis, Fix, Validator
and Risk outputs from your real provider. Triage may stop early if further investigation
is not justified; that is a real early exit, not a five-stage success.

If Groq returns a quota/auth/model/schema error, the run must show Failed with its event.
Fix the reported configuration issue, restart if `.env` changed, and request another analysis.
A connected models probe alone is not inference acceptance.

## Optional configuration (defaults require no edits)

Add only if you want to override defaults in `backend\.env`:

```dotenv
ANALYSIS_ENABLED=true
ANALYSIS_AUTO_NEW=true
ANALYSIS_DAILY_LIMIT=20
GROQ_TIMEOUT_SECONDS=60
```

Automatic analysis applies to new incidents detected while this service process is running,
for enabled workflows, once per incident. Historical incidents and failed runs require an
operator request. Disable `ANALYSIS_AUTO_NEW` for manual-only inference. Disable
`ANALYSIS_ENABLED` and restart to stop all analysis. Queue capacity is five, one run at a time.
The kill switch remains enabled; no repair executor exists in this delivery.

## Optional local checks

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\Activate.ps1
python -m pytest -q
python -m ruff check .
```

For an explicitly opted-in real inference integration test using execution 33966 (only if
still retained by your n8n instance):

```powershell
$env:AGENTSENTINEL_LIVE_EXECUTION_ID="33966"
$env:AGENTSENTINEL_LIVE_ANALYSIS="1"
python -m pytest -q tests/test_live_investigation.py
Remove-Item Env:AGENTSENTINEL_LIVE_EXECUTION_ID
Remove-Item Env:AGENTSENTINEL_LIVE_ANALYSIS
```

This test uses a temporary database and real external calls, never production workflow writes.
Phase 3 acceptance stays open until live inference is verified. Do not start Phase 4 yet.
