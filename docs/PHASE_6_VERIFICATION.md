# Release verification — October 9, 2026

## Executed in the build environment

| Check | Result |
| --- | --- |
| Backend Ruff | Passed |
| Backend pytest after cryptography upgrade | 118 passed, 2 credential-gated live tests skipped |
| Dependency consistency (pip check) | Passed |
| Python pinned requirements pip-audit | No known vulnerabilities after cryptography 50.0.2 upgrade |
| Historical format compatibility | Real Fernet token encrypted with 48.0.1 decrypted with 50.0.2 using unchanged key |
| Next ESLint, TypeScript and production webpack build | Passed |
| npm production dependency audit | 0 vulnerabilities reported |
| npm full dependency audit | 5 high dev dependency entries; one braces advisory chain, unresolved upstream |
| API integration | Real migrated temporary SQLite, readiness, scoped auth and honest empty state passed |
| HTTP hardening | Invalid Host rejected, oversized/chunked bodies rejected, rate limit enforced despite varied forwarded headers |
| Event streams | Eight-stream budget tested; cancellation releases all capacity |
| Worker exclusion | Second lock refused; lock reacquisition succeeds after release |
| Backup | Live-worker backup refused; real offline SQLite data copied and read back; overwrite refused |
| Console authenticated production server | Unauthenticated HTML, Operations, incident and API routes denied; valid credentials accepted |
| Console mutation protections | Cross-origin rejected; oversized action rejected; disabled Chaos honestly failed |
| Console normal local mode | Existing credential-free loopback configuration still works |
| Browser | Chromium desktop 1440 and mobile 390; real empty database, SSE connected, no fake running stages, no horizontal overflow or uncaught page errors |
| Existing repair boundaries | Full regression suite retained; no validator, risk, approval, revision or rollback gate removed |

Python audit used the pinned requirements with --no-deps --disable-pip; it checks listed versions
against the advisory service, not a complete security proof. The installed dependency graph also
passed pip check. npm and Python audits reflect the time of this check, not a permanent guarantee.

Tests use isolated temporary databases and direct HTTP contract inputs. They never ship incident
fixtures or simulate n8n/Groq success. The build environment did not use the user's credentials.

One upstream Starlette TestClient/httpx deprecation warning remains. The environment's npm proxy
configuration warning is external to the project. Neither warning was suppressed.

## Real system evidence reused, not rerun

Phase 5 acceptance: experiment 1, failure 106588, investigation 21, approved repair 4; actual full
executions 107039/107118 each observed 503 then 200; healed; fault stopped and writes paused.
Phase 4 persistent failure 83654 triggered read-back-confirmed rollback. See RELEASE.md.
These records came from the operator's live installation, not this environment's test database.

## Remaining acceptance and limitations

- Apply this incremental patch, take a backup, install the security dependency update and verify
  startup/build on the Windows laptop. The new Windows msvcrt lock branch was reviewed but only
  the Linux flock branch was executed here. CI is supplied but has not run on GitHub.
- No new live provider calls or n8n workflow modifications were needed for release hardening.
- No public deployment, independent penetration test, multi-user auth, multi-host locking or
  PostgreSQL production validation is claimed. Local topology is the supported V1 scope.
- Full dependency security clearance remains limited by the documented braces dev-tool advisory.
- No measured guarantee is made for peak RAM on a 4 GB laptop; no heavy service was added.
