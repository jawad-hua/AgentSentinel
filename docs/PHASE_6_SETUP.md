# Phase 6 incremental installation — Windows

One existing security dependency is upgraded to cryptography 50.0.2 (64-bit Python required).
No schema migration or n8n import is required. The schema remains 0005.
Apply only the manifest files; never replace .env/.env.local or database with an example file.
The accepted Phase 5 experiment is stopped and writes are paused; retain that state.

## Checkpoint 1 — stop, copy, backup

Stop the API Uvicorn terminal and the frontend server with Ctrl+C. Copy/replace the ZIP's files
into D:\AgentSentinel. From a PowerShell terminal:

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\python.exe ..\scripts\backup_database.py --output ..\agentsentinel-before-phase6.sqlite
```

Keep the matching backend .env securely with your recovery plan. If the backup filename already
exists use a new name; do not overwrite it. Stop progression if backup fails.

## Checkpoint 2 — backend checks

```powershell
.\.venv\Scripts\python.exe -m pip install --only-binary=:all: cryptography==50.0.2
.\.venv\Scripts\python.exe -m pip install -e . --no-deps
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m pytest -q
```

Expected migration: 0005 (head). Credential-gated live tests skip unless explicitly opted in.
Tests use temporary databases and do not alter your incident records or call providers by default.

## Checkpoint 3 — frontend checks

```powershell
cd D:\AgentSentinel\frontend
npm run lint
npm run build
```

No npm ci is required because no dependency or package lock changes are included.
Do not run npm audit fix --force; see RELEASE.md for the remaining dev-tool advisory.

## Checkpoint 4 — start and inspect

Use the existing backend command, one process only:

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

In a separate terminal:

```powershell
cd D:\AgentSentinel\frontend
npm run start
```

Open http://127.0.0.1:3000. Confirm SSE connects; repair 4 remains healed; experiment 1 remains
stopped; writes remain paused; workflow freshness updates. Do not restart the Chaos test just to
prove an already accepted result. Report any startup/auth/host error before changing .env.
Optional console credentials are documented in DEPLOYMENT.md; local configuration works unchanged.
