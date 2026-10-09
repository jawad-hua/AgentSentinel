# Investigation and frontend diagnostics

## Investigation 16: confirmed immediate block
The supplied actual run completed all requested stages. Risk was low. The deterministic reasons were Validator rejection and Fix disposition no_safe_fix. Rate limits recovered and were not the final blocking condition.

Fix and Validator interpreted the declared requirement as stopping on the first intentional 503. The attested objective instead requires same-execution recovery from the helper's initial 503 while preserving visible failure after bounded attempts for persistent errors. This is an interpretation contradiction, not a missing operator approval in this run. Later stages receive preceding interpretations, so the same incorrect reading can propagate. Pydantic/schema and citation validation check output structure and evidence identifiers; they do not establish semantic correctness.

The new read-only diagnostic reads the latest persisted investigation, prints the stored objective and error-handling evidence, reports stage decisions, recomputes deterministic policy and checks locally imported file hashes against the previously delivered sources. It does not make AI or n8n calls, create incidents, alter records or authorize repairs. It also does not capture the old wire request or prove which code was loaded in an already-running server process. Those limits are printed. No prompt or safety-policy change is included here.

## Reproduced frontend warning
An isolated actual HTTP compression/stream test using the installed Next.js 16.3.8 code reproduced MaxListenersExceededWarning: 11 drain listeners added to Gzip. Stack: compiled/compression -> ServerResponse.once -> server/pipe-readable.js:177. The same stream test with compression disabled produced zero such warnings. These were byte-stream tests, not synthetic incidents or simulated provider responses.

The bundled compression middleware redirects drain subscriptions to the gzip stream, while the response streaming path repeatedly registers drain listeners during backpressure. Disabling built-in Next compression avoids this path in this loopback deployment. No listener limits are raised and no warnings are suppressed. Responses can be larger; compression policy should be reviewed separately before public deployment.

MODIFIED FILE frontend/next.config.ts sets compress:false. NEW FILE scripts/diagnose_investigation.py is the diagnostic. No package update, database migration or environment edit is required.

## Apply and collect results
1. Stop the frontend terminal with Ctrl+C; leave the backend running. Copy included frontend, scripts and docs folders into D:\AgentSentinel, replacing only matching files.
2. In a separate PowerShell:

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\python.exe ..\scripts\diagnose_investigation.py --incident-id 2
```

Share the minimized output. No secret values are printed. Source fingerprints are release hashes, not workflow secrets. Run this before another analysis or approval request.

3. Rebuild and restart the frontend after copying next.config.ts:

```powershell
cd D:\AgentSentinel\frontend
npm run build
npm run start
```

Do not run npm run start if the build fails. Keep writes paused and avoid changing helper/workflow settings while collecting diagnostics. No Phase 4 completion claim is made: prior recovery was verified, but failed-repair rollback acceptance remains pending.

## Checks performed
- Isolated compression reproduction: warning present with gzip, absent without gzip.
- Frontend production build including TypeScript and ESLint: passed.
- Actual isolated FastAPI and production Next integration: passed; gzip absent even when requested, page load and existing proxy/security checks passed.
- Diagnostic Python lint, imports/CLI parsing, safe missing-record handling and preservation of an actual empty migrated database: passed.
- Diagnostic against the user's persisted investigation: pending. No real Groq call was made here and no semantic fix is claimed.
