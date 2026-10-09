# Phase 2 incremental update — Windows PowerShell

This patch changes only the paths listed in PHASE_2_MANIFEST.md. It contains no .env,
.env.local, database, node_modules or replacement dependency lockfiles. Your Groq model
selection, API keys, local heartbeat and n8n credentials are preserved.

## Checkpoint 1 — stop and apply

1. In the AgentSentinel backend PowerShell, press Ctrl+C.
2. In the AgentSentinel frontend PowerShell, press Ctrl+C. Leave n8n running.
3. Make a backup copy of `D:\AgentSentinel` (at minimum backend/data and both environment
   files). The database must be copied while the service is stopped.
4. Extract the patch **inside `D:\AgentSentinel`** and allow listed files to replace.
   The ZIP begins with backend/, frontend/, n8n/, docs/ and root documentation.
   Do not create a second nested AgentSentinel folder.

## Checkpoint 2 — migrate and start

In backend PowerShell (activate .venv if this is a new window):

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\Activate.ps1
alembic upgrade head
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

`/health/ready` should report ready. Run **one worker**. No --workers option is needed.
This migration adds tables and preserves the existing heartbeat table and records.
The read-only monitor uses the existing N8N_BASE_URL and N8N_API_KEY.
Keep KILL_SWITCH=true: read-only monitoring does not require disabling it.

In frontend PowerShell:

```powershell
cd D:\AgentSentinel\frontend
npm run build
npm start
```

No npm ci/reinstall is needed because frontend dependencies have not changed.
Open http://127.0.0.1:3000. Do not run `npm audit fix --force`; the previously reported
ESLint/braces development advisory is not resolved by this patch. Your earlier production
`npm audit --omit=dev` reported zero; that result is not a permanent security guarantee.

## Checkpoint 3 — opt in

1. Press **Sync from n8n**. This imports workflow metadata only; it does not execute anything.
2. On AgentSentinel Master, press **Enable monitoring**.
3. Execute the existing master workflow manually in n8n.
4. Press **Check executions**, or allow the background cycle to run. The dashboard updates
   through real persisted events. Confirm the actual execution ID/status appears.

No workflow re-import is required. The bundled master JSON only updates explanatory notes;
its manual heartbeat behavior is unchanged. Re-importing needlessly could create another
workflow or require selecting credentials again.

Monitoring initially includes retained executions started in the prior 24 hours. Pausing
and resuming preserves the original coverage boundary and resumes retained history.
Monitor only selected workflows: maximum 20 enabled in this lightweight local release.
Inactive in n8n does not mean unmonitorable: manually executed workflows can be watched.

## Checkpoint 4 — validate failure detection safely

Watch an existing genuine failed execution in a designated non-production test workflow.
Never break an arbitrary production workflow merely to populate the console. If no such
failure exists, leave the incident empty state: success does not require invented incidents.
We can walk through one isolated real failure together before Phase 2 acceptance.

Confirm the incident shows the actual workflow/execution, evidence category, occurrence
count and persisted timeline. Repeated checks must not increment occurrences. A genuinely
new execution with the same failure signature increments that incident's count.

## Optional output expectations

Set these only when a workflow has a real contract:
- Exact node name: the node whose saved output should be inspected.
- Require non-empty output: flags a recorded empty node output, not a skipped node.
- Require a JSON object or array: checks the configured dot-separated field inside each
  item.json. It accepts an actual object/array or a string that parses to one.

Expectations apply to newly inspected executions. They do not rewrite existing incidents
or retroactively re-evaluate already inspected executions. Credentials/raw inputs/outputs
are never sent to an LLM in Phase 2. Arbitrary JSON Schema validation is not implemented.

## Configuration and limits

Defaults require no .env changes:

```env
MONITORING_ENABLED=true
POLL_INTERVAL_SECONDS=30
MONITORING_LOOKBACK_HOURS=24
```

Poll interval range: 10–300 seconds. Initial lookback: 1–168 hours. Interval is the pause
between cycles; heavy histories/network failures can make a cycle longer. Freshness and
check errors remain visible. Each workflow has a 45-second check budget and reads at most
two 50-row list pages per cycle, plus up to 10 pending executions. Each fetched response
is capped at 8 MiB and processed individually. Oversized/unavailable evidence reports a
check error; it is never called healthy. Background history cursor progress is persisted.

Enable saving successful, failed and manual executions in your n8n instance if you need
all those records. Deleted/pruned/unsaved traces cannot be reconstructed by AgentSentinel.
Use one n8n instance per AgentSentinel database; use a separate DB for another instance.

## Small verification commands

From activated backend:

```powershell
ruff check .
pytest -q
alembic check
```

From frontend:

```powershell
npm run lint
npm run typecheck
```

If an error appears, stop and share its text. Never share .env or credential screenshots.
After your actual execution and incident checks pass, confirm **Phase 2 complete**.
Phase 3 begins only after that confirmation.

## Optional live read-only pytest check

Once you have a real saved execution ID, set `AGENTSENTINEL_LIVE_EXECUTION_ID` in the
current PowerShell session and run `pytest -q tests/test_live_n8n.py`. This fetches the real
execution using your existing local n8n credentials, verifies persistence/deduplication
in a temporary database, and neither executes nor changes the workflow. It is skipped
by default so normal tests never assume that n8n is connected.
