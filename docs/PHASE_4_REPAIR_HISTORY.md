# Historical repair evidence

## Change
Same-configuration comparison evidence excluded successful executions of an older patched revision. This update separately collects the latest three terminal repair records for the same incident and workflow. It does not reinterpret them as executions of the current configuration.

The collector decrypts the retained original snapshot locally, reconstructs its allowlisted patch and validates both recorded revision hashes. It compares the historical baseline with the current configuration while ignoring only the affected node's retry settings. Other node configuration, credentials, topology, settings, static data and pinned data differences prevent inclusion as a comparable baseline. This special historical comparison is never used to authorize workflow writes or replace current revision checks.

Up to six execution records explicitly referenced by historical verification are fetched through the read API, with recorded failures considered before successes. Identity, saved patched configuration, timing, full execution and historical output-contract checks are repeated. Missing, mismatched or inaccessible records are unavailable evidence. The collector has a thirty-second asynchronous budget; incomplete collections are labeled.

Only minimized observations enter the existing evidence UI and provider input. Snapshots, credentials, raw error text and payloads are not included. An old successful execution does not prove helper mode, actual retry-attempt counts, current health, persistent-error behavior or suitability of another repair. Independent Validator, Risk and deterministic policy decisions remain unchanged. Existing blocked investigations and approvals are not modified.

## Install and first check
Requires the previously installed Operator Assessment patch. No migration, dependency update, environment edit or frontend rebuild is needed.

1. Stop only the backend with Ctrl+C. Copy the included backend, scripts and docs contents into D:\AgentSentinel, replacing only matching files. Preserve the database and .env.
2. From PowerShell, run:

```powershell
cd D:\AgentSentinel\backend
.\.venv\Scripts\python.exe ..\scripts\check_repair_history.py --incident-id 2
```

This command reads the actual incident, encrypted repair snapshots and n8n records. It prints minimized history only, performs no AI calls and changes no workflow or approval. Inspect its output before requesting another analysis. A missing original execution or snapshot key is an honest failure, not a reason to fabricate history.

3. Once the read check is reviewed, restart the backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

New investigations collect this history automatically. Existing investigation evidence is immutable. A fresh investigation still may stop or block; no successful decision is promised. Keep repair writes paused during evidence review.

## Verification
Backend Ruff passed. Backend tests: 90 passed, 2 credential-dependent live tests skipped. Frontend lint passed; its existing production build was used for a real FastAPI/Next.js smoke check, which passed page loading, proxy routing, origin checks, input validation and authentication. No frontend source or output schema required a change.

New checks cover historical configuration isolation, state drift and actual empty-database behavior. No fake provider responses or seeded application records were used. Live collection of the user's repair history, Groq review with this additional evidence, and failed-repair rollback acceptance remain to be checked in the connected Windows environment.
