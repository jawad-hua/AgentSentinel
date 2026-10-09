# Local operator security boundary

This release supports a trusted single operator on a local machine. Bind API and console to
loopback. Optional console Basic authentication protects every request using a separate secret;
non-loopback origins require HTTPS plus that credential. It is not multi-user RBAC or a session
service. Admin actions identify the operator role, not individual people. Public exposure has not
been accepted or penetration-tested. See DEPLOYMENT.md before any deployment change.

- Distinct random bearer tokens for administration and ingestion; no browser token storage.
- All browser mutation proxies enforce trusted Origin and Host. No arbitrary target/proxy route.
- A separate write credential is used only by the repair service. Keep least-privilege n8n
  read/list access for monitoring and workflow:update access for the writer where supported.
- No n8n publish/activation/credential mutation endpoints are called. No code evaluation or
  LLM tool execution. Default-disabled repairs plus workflow designation plus human approval.
- Models never override deterministic policy. Revalidate stored schemas, source evidence,
  revision and allowlisted changes at preparation/approval/execution boundaries.
- Full snapshots may contain embedded secrets and credential references: encrypt them with
  Fernet before persistence; never return or send them to the LLM. Back up the key and DB securely.
- Snapshot keys live in .env, outside the database. OS file permissions remain essential;
  encryption does not protect against compromise of both the database and .env.
- Provider clients do not follow redirects or inherit HTTP proxy credentials. Raw upstream
  errors, arbitrary workflow payloads and credentials are excluded from logs and model evidence.
- Generic safe errors and request validation do not echo submitted credentials.
- Kill switch is checked immediately before each repair/rollback write. Already in-flight HTTP
  requests cannot be canceled reliably. Runtime pause is durable and cannot override configured pause.
- No automatic replay: manually run only a workflow whose full side effects you have reviewed.
- n8n public PUT is not atomic compare-and-swap. Inactive workflow + exclusive maintenance is
  mandatory; post-write drift escalates rather than overwriting someone else's configuration.
- Ambiguous post-write outcomes keep a workflow claim and encrypted snapshot for manual recovery.
- Do not delete/rotate the snapshot encryption key while retained snapshots depend on it.

## Hardening reviewed in release 0.6

- Explicit backend Host allowlist and console Host validation (DNS rebinding protection).
- Constant-time comparison of console credential digests; missing/partial remote configuration fails
  closed. A bounded per-process failed-auth budget returns 429. Never pass API keys to the browser.
- Backend 64 KiB mutation body cap, 10-second body deadline, 600 requests/minute total budget and
  eight concurrent SSE streams, with stream capacity released on cancellation. Frontend action
  readers stop buffering at their smaller per-route limits.
- Same-origin mutation checks remain mandatory even with Basic credentials. No CORS bypass added.
- SQLite OS worker exclusion; atomic database repair claims; no automatic retry of uncertain writes.
- Offline backup creation refuses overwrite and checks integrity; no automatic destructive restore.
- Existing independent validator veto, narrow action allowlist and current-revision checks unchanged.

## Residual risks and scope

OS compromise can read .env and authorize changes; local rate limits cannot prevent network floods.
Basic credentials are browser-cached until the browser clears them; rotate/restart to revoke.
No multi-user identities, public session management, external security audit, HA or PostgreSQL
coordination are claimed. Application policy does not prove arbitrary GET endpoints have no side
effects; operator review and strict workflow designation remain required.

The build dependency advisory GHSA-vfj7-8cjw-p6xm remains open; see RELEASE.md. No forced dependency
downgrade or warning suppression was applied. Preserve original failure evidence; do not ask the
LLM repeatedly until it gives an approval. Safe refusal is a valid pipeline outcome.
