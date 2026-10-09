# Phase 4: explicit operator repair assessment

## Problem and behavior
An intentional fault can have a known cause while an operator's recovery requirement remains unmet. Triage could stop at that known cause, leaving the UI asking for operator review without an action to perform it.

The latest triage-only escalation now offers **Request repair assessment**. This creates an audited, explicitly operator-requested, read-only assessment. Original triage output remains unchanged, including investigate=false. The UI references that original stage; it does not fabricate a new triage completion. Real Diagnosis, Fix, Validator and Risk stages run against freshly collected execution and configuration evidence. No acceptance is guaranteed.

Eligibility requires a completed triage-only escalation for the latest failed execution, matching configuration fingerprints, and no prior policy result. A validator rejection is not eligible. Changed workflow revisions, newer failures, active repair claims, queue limits and investigation budgets remain enforced. Referenced triage provenance is rechecked before preparing repairs. Independent validation, deterministic action bounds, human approval, encrypted snapshots, verification and rollback requirements remain in force.

This patch makes no workflow writes, changes no incident records during installation, and needs no migration, new dependency or environment change. Previous repair history remains intact. Phase 4's live rollback acceptance remains pending.

## Apply on Windows
1. Stop the running backend and frontend with Ctrl+C in their respective terminals. Keep the helper and n8n running; do not edit or execute the test workflow during installation.
2. Extract this ZIP to a temporary directory. Copy its backend, frontend and docs contents into D:\AgentSentinel, replacing only matching files. Do not delete destination folders. Preserve .env, .env.local, database, encryption keys and all unrelated files.
3. In frontend PowerShell:

```powershell
cd D:\AgentSentinel\frontend
npm run build
```

If the build fails, stop here and share the error. If it succeeds, start the frontend:

```powershell
npm run start
```

4. In another PowerShell, start the backend:

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

5. Open http://127.0.0.1:3000/incidents/2 and refresh. If Investigation #11 remains the latest eligible triage-only escalation, click **Request repair assessment** once. Do not repeatedly click Request another analysis. Leave repair writes paused while reading the result. The new investigation will have its own real database ID; do not assume its number.
6. Inspect the actual result before any approval. A blocked result remains blocked. An eligible proposal still needs a newly prepared, revision-bound repair and explicit approval. This patch does not authorize or execute it.

## Verification performed
- Backend Ruff: passed.
- Backend pytest: 79 passed, 2 skipped.
- Frontend ESLint and Next.js production build with TypeScript: passed.
- Real isolated FastAPI and Next.js servers: homepage, proxy routing, origin rejection, input validation, disabled-analysis guard and authentication passed. No seeded operational records or provider calls.
- Tests cover triage eligibility, stale revisions, unchanged original output and authorization boundaries. Test vectors are not application data.
- Live Groq assessment and failed-repair rollback still need verification in the user's connected environment. These checks do not claim a new live repair or recovery.
