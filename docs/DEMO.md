# Genuine red-to-green demo

Use the already recorded experiment 1 for a retrospective; do not reset records or invent activity.
Show its 503 execution 106588, minimized evidence, five completed agent stages, exact approved
retry diff, then probe attempts for 107039/107118 and the healed repair timeline. Say:

“AgentSentinel detected a broken automation, investigated the evidence, proposed a bounded retry,
and verified recovery after my approval.”

The existing implementation validates structure/policy before writing and verifies actual
executions afterward; do not describe it as sandbox replay or a pre-application execution test.

For a fresh live demo, follow PHASE_5_SETUP.md with a dedicated inactive two-node test workflow.
The current repaired node may already have retries enabled. Do not silently switch retries off:
any reset must be an explicit operator edit after all repairs are terminal and fault sessions stopped.
Save the reset before collecting a new healthy baseline. Old baseline IDs cannot stand in for
current saved configuration. Never touch unrelated production workflows.

1. Confirm monitoring, read/write n8n connections and Groq model access. Keep an inference budget.
2. Designate the exact authenticated local probe template. Run a full healthy saved execution.
3. Enter its actual ID and arm transient fault; the session expires after 30 minutes with HTTP 410.
4. Execute the full workflow once. Observe real 503 and its incident. Wait through bounded Groq
   rate-limit retries. If evidence is unavailable or validator rejects, show that result honestly.
5. Inspect evidence, diagnosis, diff and medium risk. Release runtime pause only for controlled
   remediation. Prepare the review and explicitly approve the diff and conditional rollback.
6. Once verifying, reload n8n saved workflow and run it fully twice, at least 60 seconds apart,
   without pinned data or partial runs. Keep transient mode unchanged and writes available.
7. Show two actual 503-to-200 sequences and HEALED only when persisted verification confirms it.
8. Stop the fault and pause writes. This cleanup does not create healing; earlier executions did.

Persistent-mode rollback was already tested in Phase 4 with execution 83654. It is a separate
experiment, not a mode switch during an active repair. Do not claim the transient demo also tested
persistent rollback. Hide secrets, credential dialogs, .env files and authorization headers while
recording; preserve the real IDs and chronology. Older unresolved incidents remain honest history.
