# AgentSentinel 0.6 — release scope

A working single-operator n8n reliability system, with human-approved repairs to designated,
unpublished workflows. This is not a multi-tenant SaaS or an arbitrary production-code repair tool.
The supported topology is one local API process, one Next.js process and one self-hosted n8n
instance. SQLite remains the supported database; PostgreSQL requires a replacement process-lock
strategy and a separately verified migration. No Redis, Docker or local model is required.

## Actual acceptance evidence

The following records were provided by the operator from the real Windows/n8n/Groq installation.
They are documentation only; no script seeds them into a database.

| Gate | Real result |
| --- | --- |
| Phase 4 recovery | Repair 2 healed; executions 66491 and 66561 each retried 503 to 200 |
| Phase 4 rollback | Repair 3 restored original revision; persistent execution 83654 failed all 3 attempts |
| Phase 5 baseline | Healthy saved execution 106275 |
| Phase 5 detection | Execution 106588 returned 503; incident 4 created |
| Phase 5 intelligence | Investigation 21 completed five Groq stages; validator accepted; medium risk |
| Controlled repair | Repair 4 explicitly approved; retryOnFail false to true; read-back matched |
| Recovery | Executions 107039 and 107118 each returned 503 then 200 within the same execution |
| Verification | Repair 4 healed 2026-10-09 02:09:04 UTC after two full patched runs and observation window |
| Cleanup | Experiment 1 stopped 02:14:24 UTC; repair writes paused 02:12:18 UTC |

A past healed outcome covers its recorded window, not future availability. There are no
claims of universal LLM accuracy. Independent validation can reject a plausible proposal.
Evidence coverage counts supported hypotheses; it is not a probability of correctness.

## Supported changes and release limits

- Only allowlisted bounded retry fields on eligible read-only HTTP nodes are executable.
- Every retry repair still requires explicit human review; no LLM-only approval.
- No automatic replay, workflow activation, credential editing or arbitrary code execution.
- Exclusively maintained inactive workflows only: n8n's tested public PUT has no usable atomic
  compare-and-swap. Read checks cannot prevent concurrent third-party edits.
- An OS lock now prevents two API workers sharing one local SQLite path. Network filesystems,
  multiple hosts and multiple database copies are not a supported coordination mechanism.
- UI authentication is an optional single-operator HTTP Basic gate on loopback. A configured
  non-loopback origin requires HTTPS and a separate strong credential. This is not SSO, sessions,
  per-user RBAC or remote-deployment certification; keep the supported local topology for V1.
- Fault injection remains opt-in and restricted to the documented exact local probe template.
- No auto-purging audit/snapshot data. Plan encrypted backups and disk monitoring. Raw n8n
  execution pruning can remove evidence; a 404 blocks analysis rather than inventing a result.

## Dependency review

The pinned cryptography dependency is upgraded from 48.0.1 to 50.0.2 following the Python audit.
Existing Fernet keys are retained; do not run key generation again. Use 64-bit Python on Windows.
The upstream change log is https://cryptography.io/en/50.0.2/changelog/.

## Remaining development dependency advisory

The October 9 npm audit reports 5 high-severity development dependency entries from one braces
advisory (GHSA-vfj7-8cjw-p6xm), through Next's ESLint configuration. The advisory reports no patched
braces release. Do not force-downgrade eslint-config-next to 14 under Next 16. Build/lint only
trusted source trees; runtime installs can omit dev dependencies after building. This is an
explicit unresolved build-tool risk, not a clean all-dependency security audit.
Reference: https://github.com/advisories/GHSA-vfj7-8cjw-p6xm

Production-dependency audit and execution checks are recorded in PHASE_6_VERIFICATION.md.
No public deployment or repository publication is performed by this delivery.
