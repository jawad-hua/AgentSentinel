# AgentSentinel engineering rules

Current checkpoint: Phase 6 release hardening, explicitly authorized October 9, 2026.
Phase 5 accepted: integrated Chaos experiment 1, incident 4, investigation 21, repair 4.
Actual executions 107039/107118 each returned 503 then 200; healed; experiment stopped.
Phase 4 rollback already verified using failed execution 83654 and restored read-back.
Preserve this evidence as historical acceptance, never as seeded application records.

- Read README.md, docs/ARCHITECTURE.md and docs/VERIFICATION.md before changes.
- Exactly six major phases. Implement only the authorized phase and necessary fixes.
- Never seed dummy operational data or simulate provider success in the application.
- Keep one primary workflow: n8n/AgentSentinel_Master.json. Do not add workflow JSON files.
- Preserve existing code; later ZIP deliveries contain only changed/new paths and a manifest.
- Keep provider secrets server-side. Models never authorize mutations.
- Default deny for repairs; snapshot, validate, bind approval to revision, verify and safely
  rollback before claiming healing in future phases.
- Never turn a heartbeat receipt into a workflow-health claim.
- No phase/backend/frontend labels in visible product UI.
- Resource target is a 4 GB Windows laptop; no required Docker, Redis or local models.
- Run Ruff, pytest, frontend lint/typecheck and relevant build/integration checks.
- Distinguish checks actually run from live n8n/Groq checks awaiting credentials.
- Report short, sequential Windows PowerShell instructions and stop progression on errors.
