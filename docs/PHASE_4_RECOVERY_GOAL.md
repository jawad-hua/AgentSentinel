# Explicit recovery goal for the designated local test

The earlier context patch recorded what happened, but not the desired resilience behavior.
This patch adds an optional typed operator requirement: complete the same full execution
while the helper remains in transient mode and backend liveness is available. Switching
modes or starting a new execution does not meet that goal. Persistent errors must remain
visible after bounded attempts.

The CLI displays the selected goal before ATTEST. The new audit event preserves the
historical testimony plus the explicit requirement. Older records remain unchanged and
receive no inferred goal. The evidence distinguishes desired behavior from observations.
The same actual n8n execution, source hash, target, revision, designation and 24-hour checks
apply. No arbitrary instructions are accepted in the objective field.

Prompts now evaluate the gap between observed and desired behavior. No patch is prescribed
by the requirement. Fix may still return no_safe_fix; Validator may reject. Deterministic
bounds, risk policy, approval and write controls are unchanged. No successful recovery is
claimed. No LLM call or n8n write occurs during registration.

## Apply and register

Requires the previously installed Phase 4 patches, including Test Context and n8n Write Fix.
Keep runtime writes paused. Stop the backend, merge this ZIP into D:\AgentSentinel and
replace only the manifest files. No migration, dependencies or frontend rebuild is needed.

From D:\AgentSentinel\backend:

```powershell
.\.venv\Scripts\python.exe ..\scripts\register_test_context.py --incident-id 2 --healthy-execution 50673 --objective same_execution_recovery
```

Read the statement. Type ATTEST only if the historical testimony is true and you select
this recovery goal for the designated test. Anything else cancels. These incident and
execution IDs are the actual operator-provided records, not seeded data.

Restart:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Request one analysis. Check test_operator_objective in evidence and review the result.
Do not repeat analysis solely to obtain acceptance. Keep writes paused until a new eligible
proposal and its exact diff are reviewed. The helper should remain transient during any
subsequent repair verification; preserve actual helper attempt logs for that check.

## Validation

Ruff passed. Backend tests: 69 passed, 2 skipped (existing httpx deprecation warning).
A real isolated n8n 2.15.1 instance and shipped helper verified saved failure/success,
registration, absence of a goal for older context, explicit goal inclusion, and exclusion
when the revision or designation mismatched. No AI success or approval was simulated.
Frontend files are unchanged, so frontend checks were not repeated.
The user's complete approved recovery and rollback acceptance remains pending.
