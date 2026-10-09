<div align="center">

# AgentSentinel

### AI-powered reliability for n8n automations

Detect failures. Investigate evidence. Approve repairs. Verify recovery.

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=flat-square&logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-000000?style=flat-square&logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)
![n8n](https://img.shields.io/badge/n8n-EA4B71?style=flat-square&logo=n8n&logoColor=white)

[Overview](#overview) · [Recovery in action](#recovery-in-action) · [Architecture](#architecture) · [Getting started](#getting-started)

</div>

---

## Overview

A failed automation needs more than an alert. It needs an explanation,
a controlled response, and evidence that the response worked.

**AgentSentinel** brings that lifecycle to n8n workflows. It monitors real
executions, investigates failures through five bounded AI stages, and proposes
targeted configuration changes. Approved repairs are applied with encrypted
snapshots, execution-based verification, and conditional rollback.

The **Agent War Room** makes the process visible—from the first observed failure
to the final recovery decision.

> Every incident, agent event and operational metric comes from persisted system
> activity. Empty installations display empty states.

## Recovery in action

The controlled recovery test exercised the complete pipeline:

| Step | Observed behavior |
| --- | --- |
| Failure | A designated test endpoint returned HTTP 503 on the first request |
| Detection | AgentSentinel recorded the failed n8n execution as an incident |
| Investigation | AI stages examined execution evidence and node configuration |
| Proposal | A minimal change enabled `retryOnFail` on the affected node |
| Approval | The operator reviewed and approved the exact revision-bound diff |
| Application | AgentSentinel applied the change and confirmed it through n8n read-back |
| Verification | Two full executions each returned 503 on attempt one and 200 on attempt two |
| Outcome | The repair was marked **HEALED** after the required observation window |

The transient fault remained active during verification.

A separate persistent-failure test exhausted the bounded retries and triggered
a verified restoration of the original configuration.

**These results came from real n8n executions against an intentionally controlled
test endpoint.**

## Core capabilities

### Execution monitoring
Watch selected workflows, inspect actual execution records, detect supported
failure conditions, and persist incidents with deduplication.

### Bounded AI investigation
Triage, Diagnosis, Fix, Validator and Risk stages exchange validated structured
outputs. Evidence and AI interpretation remain distinguishable.

### Controlled remediation
Review a minimal diff, approve a specific workflow revision, and preserve an
encrypted snapshot before application. Deterministic policies constrain what
the system can change.

### Recovery verification
Evaluate actual executions of the patched workflow. Record successful recovery
or conditionally roll back when verification fails.

### Agent War Room
Follow live investigation stages, workflow status, approval decisions, repair
outcomes and a persisted incident timeline.

### Controlled Chaos Mode
Introduce transient or persistent HTTP failures into explicitly designated
test workflows and observe the normal detection-to-recovery pipeline.

## Architecture

```mermaid
flowchart TD
&#x20;   N["n8n executions"] --> M["Monitor · Normalize · Detect"]
&#x20;   M --> I["Incident and execution evidence"]
&#x20;   I --> A["Triage → Diagnosis → Fix"]
&#x20;   A --> V["Independent Validator and Risk review"]
&#x20;   V --> P{"Deterministic policy"}
&#x20;   P -->|Blocked| E["Escalate for operator review"]
&#x20;   P -->|Eligible| H["Human approval"]
&#x20;   H --> S["Encrypted snapshot and targeted patch"]
&#x20;   S --> R{"Actual execution verification"}
&#x20;   R -->|Passed| G["HEALED"]
&#x20;   R -->|Failed| B["Conditional rollback"]
```

The backend owns monitoring, investigation, policy enforcement and remediation.
The console receives live updates through Server-Sent Events. Groq supplies
external inference, so a local language model is not required.

## Safety by design

- **Evidence first:** proposals reference observed execution facts.
- **Limited actions:** executable changes must pass an explicit allowlist.
- **Independent review:** the Validator can reject the Fix stage's proposal.
- **Human authorization:** the model cannot approve its own workflow writes.
- **Revision checks:** approval is bound to the reviewed workflow configuration.
- **Recoverable changes:** encrypted snapshots preserve the previous configuration.
- **Auditability:** important decisions and actions are persisted.
- **Credential isolation:** secrets stay server-side; AI receives minimized evidence.
- **Operator control:** a kill switch and runtime pause constrain mutation writes.

## Current repair scope

V1 supports bounded changes to `retryOnFail`, `maxTries` and
`waitBetweenTries` on eligible GET, HEAD and OPTIONS HTTP Request nodes.

The verified operating model is a single operator managing allowlisted,
unpublished workflows under exclusive maintenance. Full verification runs are
started by the operator.

Detection coverage is broader than repair coverage. Arbitrary code changes,
credential repair, general URL correction and public multi-tenant deployment
are outside the verified scope.

A **HEALED** outcome describes recovery during the recorded verification window;
it does not guarantee future availability.

## Technology

| Layer | Implementation |
| --- | --- |
| Backend | Python · FastAPI · Pydantic |
| Persistence | SQLite · SQLAlchemy · Alembic |
| AI inference | Groq · structured outputs · provider abstraction |
| Automation | Self-hosted n8n Community Edition |
| Interface | Next.js · TypeScript · Tailwind CSS |
| Live updates | Server-Sent Events |
| Quality checks | pytest · Ruff · ESLint · production builds |

Designed for lightweight local development without a mandatory local LLM,
Redis deployment or Docker sandbox.

## Repository

```text
AgentSentinel/
├── backend/       API, agents, monitoring, repairs, migrations and tests
├── frontend/      War Room, incidents and operator controls
├── n8n/           Single primary importable master workflow
├── scripts/       Setup, diagnostics and maintenance utilities
└── docs/          Architecture, setup, security and verification
```

## Getting started

Start with the [Windows setup guide](docs/SETUP_WINDOWS.md).

Configure n8n and Groq credentials locally, apply database migrations, start
the API and console, then select the workflows to monitor.

Keep repair writes disabled until the workflow allowlist and safety settings
have been reviewed. Never commit `.env` files, API keys, operational databases
or backups.

## Verification

The Windows release passed:

- **118 backend tests**, with two opt-in live-provider tests skipped.
- Frontend lint and production build checks.
- A real controlled recovery through approved retry configuration.
- A real persistent-failure scenario with verified rollback.

See the [verification report](docs/PHASE_6_VERIFICATION.md) for test scope,
warnings and limitations. Dependency advisories and deployment boundaries are
documented rather than hidden.

## Documentation

| Guide | Purpose |
| --- | --- |
| [Setup](docs/SETUP_WINDOWS.md) | Run the application locally |
| [Architecture](docs/ARCHITECTURE.md) | Understand system components |
| [Investigation](docs/INVESTIGATION.md) | Understand the bounded AI pipeline |
| [Repairs](docs/REPAIRS.md) | Review approval, verification and rollback |
| [Security](docs/SECURITY.md) | Understand security controls |
| [Deployment](docs/DEPLOYMENT.md) | Operate, back up and restore |
| [Demo](docs/DEMO.md) | Run a controlled recovery scenario |
| [Release evidence](docs/RELEASE.md) | Inspect recorded acceptance results |

---

<div align="center">

**AgentSentinel — Automation recovery, backed by evidence.**

</div>
