# Deployment and operations

## Supported local topology

Use one API worker on loopback and the production Next.js server. Keep n8n unpublished for
repair tests. Python 3.11+ and Node 22+ are required; the supplied lockfiles capture the tested
versions. On a 4 GB machine stop frontend serving while building; do not build alongside
heavy n8n workflows. Actual peak memory on the operator laptop has not been instrumented.

From backend (Windows PowerShell):

```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:create_app --factory --host 127.0.0.1 --port 8000 --workers 1 --no-proxy-headers
```

From frontend:

```powershell
npm run start
```

Use the exact CONSOLE_ORIGIN URL (default http://127.0.0.1:3000) for mutation controls.
localhost is allowed for reading but does not change the configured Origin requirement.
Do not use --reload or additional workers in normal operation. An OS lock rejects another API
worker sharing this SQLite file; deleting its lock filename while a worker runs is unsafe.
The lock file remaining on disk after shutdown is normal; the OS lock itself is released.

## Configuration

Keep existing .env/.env.local unchanged when applying patches. Examples are templates only.
Backend ALLOWED_HOSTS defaults to 127.0.0.1,localhost,[::1]. It accepts explicit hosts, not URLs
or wildcard domains. A custom health checker must send an allowed Host. Authentication remains
mandatory for API data, including SSE; an ingest token cannot authorize admin mutations.

Optional console protection: set CONSOLE_USERNAME and CONSOLE_PASSWORD in frontend/.env.local.
Use a separate random password of at least 32 characters, not an existing API token. Restart
Next.js after changing these variables. Browser Basic authentication protects all pages, RSC,
assets and fixed proxy routes. To end cached Basic credentials close the browser profile;
for immediate revocation rotate the password and restart. There is no application logout/session
management. This gate does not create multiple operators or per-user authorization.

For remote access prefer a private authenticated tunnel/VPN to the loopback deployment.
Do not publish the API or n8n ports. A reverse-proxy deployment requires TLS termination,
exact Host preservation, bounded request sizes/timeouts, independent access/rate controls and
SSE buffering disabled. Non-loopback CONSOLE_ORIGIN requires https and console credentials;
that configuration check alone is not proof TLS is correctly deployed. A public deployment
requires its own acceptance/security review. No cloud URL is supplied by this release.

## Restart and emergency procedure

1. Before planned shutdown, finish active verification/rollback; stop fault sessions; pause writes.
2. Stop frontend/API. Back up database and retain matching environment/snapshot key securely.
3. Restart one API and one console. Check /health/ready and workflow poll freshness.
4. An unexpected crash does not erase write intent. Applying/rollback stages reconcile actual n8n
   revision on restart. Uncertain state retains the snapshot and workflow claim for operator review.
5. In an emergency pause writes or set KILL_SWITCH=true and restart. Pausing also stops rollback
   writes. An already in-flight HTTP write cannot be recalled. Inspect n8n actual state before
   releasing pause or using the existing reconciliation control. Never delete audit rows to unblock.

## Backups and restore

Stop the API first. From backend:

```powershell
.\.venv\Scripts\python.exe ..\scripts\backup_database.py --output ..\agentsentinel-backup.sqlite
```

The command refuses to overwrite a file, uses SQLite's backup API (including committed WAL state),
and checks integrity. If that filename exists choose a new dated name. Keep the backup on an
encrypted volume with access restricted to your account. Back up backend/.env and frontend/.env.local
separately in an encrypted location. Database snapshots are encrypted but audit metadata is not;
never commit a backup, .env or snapshot key. Losing the matching Fernet key prevents restoration
of encrypted workflow snapshots. Do not rotate that key without re-encrypting retained snapshots.

Restore drill: stop API; preserve current database and its WAL/SHM files together in a separate
recovery directory; copy a verified backup to the configured database path. Keep old WAL/SHM files
out of the restored directory. Restore the matching snapshot key. Set KILL_SWITCH=true before
startup; run alembic upgrade head and check readiness. Compare the real n8n workflow revision
before releasing writes: restoring the database does not restore remote workflows, and old
approvals must not be replayed blindly. Do not restore to an older application schema without
an independently tested recovery plan.

## Monitoring the monitor

/health/live only proves process liveness; /health/ready checks database/schema. Workflow poll
freshness and provider failures appear in Operations. Audit events persist in SQLite; War Room
omits routine monitor.polled rows only from its latest-30 view. Full rows remain stored.
Rate limits: 600 total API requests/minute/process, 8 concurrent event streams; probe additionally
has its own recorded-attempt budget. Mutation body limit 64 KiB and 10-second read deadline.
Console action bodies have tighter per-route limits. HTTP 429 is a real limit, not success.
Single-process limits reset on restart and do not substitute for an edge denial-of-service defense.
