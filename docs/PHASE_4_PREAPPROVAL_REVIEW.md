# Pre-approval review context correction

## Findings from the supplied Investigation 14
All requested stages completed; triage was explicitly referenced from Investigation 13. One real 429 was retried successfully. Both historical repair records reached the agents. Fix proposed only retryOnFail=false to true and Validator accepted. Risk returned blocked; deterministic policy correctly retained that block and made no new repair eligible.

One stated risk reason was missing operator approval. This is a stage-contract error: this pipeline classifies a proposal before preparing a snapshot and requesting human approval. Absence of approval must prevent execution, but is expected at analysis time. It does not itself establish technical unsuitability for later human review. Other material uncertainties can still justify a block.

Risk also treated retrying as necessarily suppressing persistent errors. The minimized input had omitted node error-handling settings. The collector now supplies disabled, continueOnFail and onError from the saved execution, explicitly labeling defaults. Unknown/malformed settings are shown as unknown. Raw node text, credentials and payloads remain excluded. The local n8n execution-engine source was inspected: finite retries and continuing on error are separate controls. This inspection is not a live persistent-failure test.

The role instructions now distinguish pre-approval classification from authorization, and bounded retry from error suppression. They retain independent rejection and instruct agents to distinguish current evidence from history and testimony. Past success does not establish liveness at a different time. No model response is rewritten, and no rejected investigation is reopened or force-approved.

The displayed 100% evidence coverage is a ratio of Validator-supported hypotheses; it is not proof of root cause. In particular, later backend availability does not prove availability at the earlier failure. Investigation 14's interpretations must not be treated as independently verified facts. The old 'Investigation 13 requested' text is a request receipt; the latest investigation header is the actual current result.

## Exact changes
- MODIFIED FILE: backend/app/investigation/evidence.py — minimized saved error-handling settings.
- MODIFIED FILE: backend/app/investigation/prompts.py — stage responsibilities and evidence limitations.
- NEW FILE: backend/tests/test_review_context.py — minimization, unknown-setting handling and retained risk veto/pre-approval boundary checks.
- NEW FILE: this document and the accompanying manifest.

No policy override, database migration, credentials, approval changes, workflow JSON, dependency or frontend change is included. Previous patches remain installed. Existing audit records remain untouched. Repairs stay subject to human approval, current revision validation, safety gates and conditional rollback.

## Verification
Backend Ruff passed. Backend suite: 97 passed, 2 credential-dependent live tests skipped. Frontend lint passed. The existing production frontend and actual isolated FastAPI server passed page loading, fixed proxy routing, origin rejection, request validation and authentication checks. No operational data was seeded and no n8n/Groq responses were mocked.

These checks cannot establish how live Groq will reason with the corrected inputs. It may still block a proposal for material risks. Current live approval and failed-repair rollback acceptance remain pending. Do not claim Phase 4 complete or start Phase 5 on the basis of these checks.

## Windows installation and next observation
1. Stop only the backend terminal with Ctrl+C.
2. Copy the ZIP's backend and docs folders into D:\AgentSentinel, replacing only matching files. Preserve all other files and folders.
3. Restart from D:\AgentSentinel\backend:

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000
```

No frontend rebuild or package installation is needed. Keep repair writes paused and do not edit the workflow or change helper mode.

4. Refresh Incident 2 and request another analysis once to capture the added configuration facts. If the actual new result is a triage-only escalation, use Request repair assessment once for that new source. Do not repeatedly rerun unchanged evidence to obtain acceptance. Inspect the resulting policy before any further actions. Approval is never inferred from an agent message.
