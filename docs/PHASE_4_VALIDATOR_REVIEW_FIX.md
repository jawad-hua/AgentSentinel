# Validator review criteria correction

MODIFIED FILE: backend/app/investigation/prompts.py
NEW FILE: docs/PHASE_4_VALIDATOR_REVIEW_FIX.md
No deleted files.

The previous validator instruction required rejection for any regression hazard. This conflated bounded residual risk with a blocking safety concern and obscured the separate Risk and approval stages. The instruction now distinguishes them without requiring acceptance. Unsupported changes, material unaddressed safety uncertainties, stale configuration, no-safe-fix proposals and policy violations still require rejection. GET alone does not prove idempotency. Human approval and rollback are not substitutes for evidence.

All stages are explicitly instructed that a comparison is a separate execution, not an observed retry, and later success cannot confirm a transient root cause. These instructions reduce ambiguity; they cannot guarantee that an LLM follows them. Inspect the next result. Existing investigation records are preserved, including their unsupported wording.

No deterministic policy, approval, kill-switch, write or recovery gate changed. No observations or acceptance results are fabricated. No additional inference provider calls occur until an investigation is requested.

Apply: stop the API; merge the ZIP into D:\AgentSentinel, preserving any unrelated local edits; restart from the activated backend terminal:

```powershell
cd D:\AgentSentinel\backend
python -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

Keep KILL_SWITCH=true and the helper healthy. No migrations, dependency installation or frontend build. After restart, request one investigation to evaluate the revised criteria. Do not repeat requests to shop for acceptance. If it rejects for missing endpoint safety evidence, preserve that result and collect the specific evidence before another analysis.

Validation: Ruff passed; backend tests 69 passed, 2 skipped (existing Starlette/httpx warning). No real Groq run was performed for this prompt change in the isolated environment; behavior must be reviewed in the next real investigation. Phase 4 end-to-end acceptance remains incomplete.

prompts.py SHA-256: b197ffe039b882bef317a5e3bb22223e33a01c94687fa41e034102a741e6a952
