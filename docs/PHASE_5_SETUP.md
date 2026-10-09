# War Room and controlled Chaos

This update preserves existing incidents, approvals, encrypted snapshots and audit events.
It adds a local, manually executed Chaos probe and an operations console using actual data.
No local LLM, additional queue service, Docker or new runtime dependency is required.

## Install in small checkpoints (Windows)

1. Stop the backend with Ctrl+C. Back up the backend database **and** `.env` securely together;
   the snapshot encryption key is needed to recover retained workflow versions. With the service
   stopped, include any SQLite WAL/SHM companions if they remain. Do not upload this backup.
2. Extract the incremental ZIP into `D:\AgentSentinel`, preserving directories; replace files.
3. In `D:\AgentSentinel\backend` run:
   ```powershell
   .\.venv\Scripts\python.exe -m alembic upgrade head
   .\.venv\Scripts\python.exe -m alembic current
   ```
   Expected schema: `0005 (head)`. Stop and resolve migration errors before starting services.
4. Start the backend:
   ```powershell
   .\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
   ```
5. Stop the existing frontend server. In `D:\AgentSentinel\frontend`:
   ```powershell
   npm run build
   npm run start
   ```
   No npm install is required. Build once, use the production server on the 4 GB laptop.
6. Visit `http://127.0.0.1:3000`. The War Room uses the existing database. Operations and connection
   controls remain at `/operations`. A disconnected API renders unavailable state, not zero KPIs.

## Opt in to the dedicated test target

Do this only after the War Room loads successfully. No approved repair may be in progress.
The previous port-9002 helper can be stopped; its historical evidence remains in the database.

1. Run `..\scripts\setup_chaos.py` with the backend venv. This only adds missing disabled settings.
2. In backend `.env`, set `CHAOS_ENABLED=true` and `CHAOS_WORKFLOW_IDS` to the exact dedicated test
   workflow ID. That ID must also already be in `REPAIR_WORKFLOW_IDS`. Keep existing encryption
   and API keys unchanged. `KILL_SWITCH=true` blocks setup/injection. Change it only deliberately
   for this controlled local test; runtime repair pause is independently available.
3. In the existing dedicated **AgentSentinel Repair Test** workflow, while inactive/unpublished
   and exclusively under maintenance, change only the HTTP Request target and authentication:
   - GET URL in expression mode (the saved expression must match):
     ```text
     ={{ 'http://127.0.0.1:8000/api/v1/chaos/probe?workflow_id=' + $workflow.id + '&execution_id=' + $execution.id }}
     ```
   - Authentication: Generic Credential Type → Header Auth.
   - Select the n8n credential whose header is `Authorization` and value is
     `Bearer <INGEST_API_TOKEN>`. Use the existing ingest credential; never the admin/write key.
   - Only Manual Trigger → HTTP Request, with optional sticky notes. No pinned data, proxy,
     custom query/body/headers, batching, response overrides or additional executable nodes.
   - Stop on error. Finite retries: maxTries 3, waitBetweenTries 1000; Retry On Fail off for the
     initial transient repair scenario. Save before designation; do not edit during repair.
4. Restart the backend to load the opt-in configuration. Sync/enable this workflow in Operations.
5. In Chaos Mode select the workflow, read the test-only acknowledgment, then **Designate test
   workflow**. Run the entire saved workflow in n8n once. It should return the live backend's
   `alive` response; copy the actual successful execution ID into the healthy baseline field.

`n8n/AgentSentinel_Master.json` remains the **only** importable workflow JSON. Its updated template
is the two-node authenticated Chaos probe, with named sticky sections for the lifecycle. An import
is optional if adapting the existing dedicated test workflow above. Do not overwrite a production
workflow or import another copy unnecessarily. Imported credentials must be assigned in n8n.
Old imported heartbeat workflows are not automatically changed; the heartbeat API still exists.
The probe URL intentionally supports the same-machine loopback deployment only.

## Real transient red-to-green demo

1. With a real healthy baseline and Retry On Fail off, click **Arm transient fault**. This creates
   a persisted 30-minute experiment, not an incident or repair. Execute the full workflow in n8n.
2. Its first probe returns a real 503. Normal monitoring retrieves the actual saved failed execution,
   deduplicates the incident and records evidence. With automatic analysis enabled, one investigation
   is queued per experiment, even for an existing incident. There are no synthetic agent outputs.
3. Open the linked incident. Triage may require an explicit **Request repair assessment**; this is
   retained as an operator decision, never silently overridden. Validator/Risk can reject repairs.
4. For an eligible proposal, release runtime repair pause as appropriate, prepare the encrypted
   snapshot, inspect the exact diff, and explicitly approve application and conditional rollback.
5. When the repair says **verifying**, reload the saved workflow and run two full executions while
   the experiment stays in transient mode. Each should show its own first 503 followed by a real
   successful response if bounded retries work. Verification needs both full saved executions and
   at least 60 seconds of observation before the persisted repair can become healed.
6. After the terminal repair outcome, stop the fault. The incident outcome is not changed by stop.
   Pause repair writes after the experiment. Repeating a repair demonstration requires an intentional
   maintenance reset and a new baseline; Chaos never silently disables a working retry setting.

Automatic replay is deliberately disabled: full n8n runs remain explicit operator actions.
The UI does not promise healing, validator acceptance or a successful demo before actual evidence.

## Persistent fault and recovery boundaries

Persistent mode always returns 503. It supports observing bounded failure and, when a repair was
independently proposed and approved, failed verification and conditional rollback. A permanently
failing endpoint does not guarantee a repair proposal; no policy is relaxed to obtain one.

Fault modes cannot change while an active repair holds the workflow. An expired experiment
returns HTTP 410; it never becomes a healthy response during verification. The configured kill
switch returns HTTP 423 from the probe, rather than a successful response. Stop it explicitly
once the repair is terminal. Disabling Chaos also does not produce successful probe responses.
A successful probe alone does not create an incident, trigger a healed state or prove workflow health.

Probe requests require the ingest token, configured allowlists and persisted designation. Records
retain caller-supplied workflow/execution IDs, attempt counts, HTTP statuses and timestamps only.
AI context is included only after matching saved n8n trace/configuration and execution timing.
That correlation is evidence, not independent attestation of caller identity beyond the credential.

## What the War Room measures

- Counts come from persisted workflow, incident, stage and repair records.
- Mean detection delay: first incident detection minus its failed execution's stop time, for up to
  the latest 100 available nonnegative samples. Null means unavailable, never zero by assumption.
- Mean repair duration: applied-to-healed elapsed time, up to the latest 100 healed records.
- A completed diagnosis means a validated structured output, not a proven root cause.
- A healed repair proves its observation window, not perpetual health of that workflow.
- The graph selects an active repair/investigation, otherwise the latest observed incident;
  each node reflects persisted stage state. Only running stages animate. Reduced motion is honored.
- The global feed shows the last 30 events; incident details retain their bounded audit timeline.

## Remaining release gate

Phase 5 implementation checks are local. User-side n8n import/configuration, Groq analysis, approval,
real transient recovery and War Room timeline correlation must be verified before accepting Phase 5.
Phase 6 (public deployment hardening and production release) has not started.
