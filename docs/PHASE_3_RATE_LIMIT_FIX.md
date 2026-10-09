# Phase 3 — bounded Groq rate-limit retries

This incremental patch requires the existing Phase 3 installation (database revision 0003).
It does not change dependencies, environment files, migrations, frontend or n8n workflows.

## Apply on Windows

1. Stop the backend with Ctrl+C. Extract this ZIP into a temporary folder.
2. Copy its backend and docs folders into D:\AgentSentinel, merging folders and replacing
   only the files listed in PHASE_3_RATE_LIMIT_MANIFEST.md. Preserve any personal edits first.
3. In the existing activated backend PowerShell terminal:

```powershell
cd D:\AgentSentinel\backend
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:3000/incidents/1 (use your configured trusted console origin if different).
Request another analysis once. Previous failed investigations remain historical records;
this starts a new run, it does not resume #1 or #2. During a 429 wait, leave the service running.
The timeline should record the actual rate limit, wait duration and retry of the same stage.

## Behavior

Only HTTP 429 is retried, once per stage, at most three retries per investigation.
Provider cooldown hints are honored within a 120-second single-wait / 180-second total-wait
budget, with a one-second margin. Missing usable hints use a 60-second fallback.
Longer cooldowns or persistent 429 fail explicitly; this cannot override account quotas.
Completed stage outputs are retained within the active run. Cancellation/restart marks
active/waiting stages interrupted. No automatic workflow modification is introduced.

Compact JSON, relevant previous-stage context, and omission of non-executable sticky notes
reduce inference input. Evidence aliases and configuration fingerprints are preserved.

## Verification

- Ruff: passed.
- Backend pytest: 46 passed, 2 opt-in live integration tests skipped.
- New tests cover documented timing formats, exhausted daily request limits, fallback timing,
  per-stage retry limits, total call limits and cumulative wait limits.
- No mocked Groq responses or fabricated workflow executions were used for this hotfix.
- Real Groq 429 recovery must still be verified in the configured local installation.
- No frontend change; the existing persisted stage statuses and timeline render waiting/retry.

For this historical POST/404 incident, no_safe_fix or a blocked/escalated outcome can be
correct. Completing Validator and Risk matters; HEALED is not a Phase 3 outcome.
