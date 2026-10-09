"""Persist reviewable repairs; operator approval never changes the deterministic allowlist."""

import asyncio
from datetime import UTC, datetime, timedelta
from secrets import compare_digest

from sqlalchemy import select

from app.chaos.models import ChaosSession, ChaosTarget
from app.integrations.n8n import IntegrationError
from app.investigation.evidence import fingerprint
from app.investigation.models import AgentRun, Investigation
from app.investigation.policy import assess
from app.investigation.review import reviewed_triage
from app.investigation.schemas import STAGES, validate_references
from app.monitoring.models import Incident, Workflow
from app.monitoring.service import event
from app.repairs.models import Repair, RepairSafety
from app.repairs.patches import Snapshots, digest, inactive, patch, revision
from app.repairs.verification import utc


class Approvals:
    def __init__(self, sessions, reader, writer, settings):
        self.sessions, self.reader, self.writer, self.settings = sessions, reader, writer, settings
        self.snapshots = Snapshots(settings.snapshot_encryption_key.get_secret_value())
        self.lock = asyncio.Lock()

    def paused(self) -> bool:
        with self.sessions() as session:
            state = session.get(RepairSafety, 1)
            return self.settings.kill_switch or bool(state and state.paused)

    def gate(self, workflow_id: str, write=False):
        if not self.settings.repairs_enabled or workflow_id not in self.settings.repair_targets:
            raise IntegrationError("Repairs are disabled or this workflow is not designated")
        if not self.snapshots.cipher or not self.settings.n8n_write_api_key.get_secret_value():
            raise IntegrationError("Configure snapshot encryption and a separate n8n write key")
        if write and self.paused():
            raise IntegrationError(
                "Kill switch is engaged; all repair and rollback writes are paused"
            )

    def source(self, session, investigation_id: int):
        run = session.get(Investigation, investigation_id)
        if run is None or run.status != "review_required" or not run.evidence:
            raise IntegrationError("A completed, eligible investigation is required")
        for fact in run.evidence.get("facts", []):
            if fact.get("id") != "controlled_fault":
                continue
            fault = session.get(ChaosSession, fact["value"]["session_id"])
            target = session.get(ChaosTarget, fault.workflow_id) if fault else None
            if (
                not fault
                or not target
                or target.session_id != fault.id
                or fault.stopped_at
                or utc(fault.expires_at) <= datetime.now(UTC)
            ):
                raise IntegrationError(
                    "Chaos conditions changed or expired; start a fresh experiment"
                )
        incident = session.get(Incident, run.incident_id)
        workflow = session.get(Workflow, incident.workflow_id)
        if not workflow or not workflow.enabled or not workflow.available:
            raise IntegrationError("Workflow must be available and monitored")
        latest = session.scalar(
            select(Investigation.id)
            .where(Investigation.incident_id == incident.id)
            .order_by(Investigation.id.desc())
            .limit(1)
        )
        if latest != run.id or incident.last_execution_id != run.execution_id:
            raise IntegrationError("Newer analysis or failure exists; request a fresh review")
        stages = {
            row.stage: row
            for row in session.scalars(select(AgentRun).where(AgentRun.investigation_id == run.id))
        }
        outputs = {}
        for name, schema in STAGES.items():
            row = stages.get(name)
            if name == "triage" and row is None and run.trigger == "operator_review":
                source_id = run.evidence.get("operator_review_of")
                source = session.get(Investigation, source_id) if type(source_id) is int else None
                if source is None or source.id >= run.id or source.incident_id != run.incident_id:
                    raise IntegrationError("Original triage source is unavailable")
                original_agents = list(
                    session.scalars(select(AgentRun).where(AgentRun.investigation_id == source.id))
                )
                original_output = reviewed_triage(source, incident, original_agents, run.evidence)
                outputs[name] = schema.model_validate(original_output)
                validate_references(outputs[name], source.evidence["facts"])
                continue
            if row is None or row.status != "completed":
                raise IntegrationError("All five agents must complete before approval")
            outputs[name] = schema.model_validate(row.output)
            validate_references(outputs[name], run.evidence["facts"])
        policy = assess(
            run.evidence,
            outputs["diagnosis"],
            outputs["fix"],
            outputs["validator"],
            outputs["risk"],
            incident.kind,
        )
        if policy["decision"] != "human_review_required":
            raise IntegrationError("Deterministic policy blocks this proposal")
        return run, incident, workflow, policy

    async def prepare(self, investigation_id: int) -> int:
        async with self.lock:
            with self.sessions() as session:
                old = session.scalar(
                    select(Repair).where(Repair.investigation_id == investigation_id)
                )
                if old:
                    return old.id
                run, incident, workflow, policy = self.source(session, investigation_id)
                self.gate(workflow.id)
                if session.scalar(
                    select(Repair.id).where(Repair.active_workflow_id == workflow.id)
                ):
                    raise IntegrationError("Another repair holds this workflow")
                current = await self.reader.workflow(workflow.id)
                if str(current.get("id")) != workflow.id:
                    raise IntegrationError("Workflow identity mismatch")
                inactive(current)
                if fingerprint(current) != run.evidence["current_revision"]:
                    raise IntegrationError("Workflow changed since investigation; reanalyze")
                expected = patch(current, policy["changes"])
                verification = {
                    "required_successes": 2,
                    "minimum_window_seconds": 60,
                    "timeout_seconds": 600,
                    "success_ids": [],
                    "checked_ids": [],
                    "failed_ids": [],
                    "strategy": "Observe operator-run full executions; no automatic replay",
                    "risk": policy["risk_level"],
                    "source_execution": run.execution_id,
                    "contract": {
                        k: getattr(workflow, k)
                        for k in ("require_output", "expect_json", "contract_node", "json_field")
                    },
                }
                row = Repair(
                    incident_id=incident.id,
                    investigation_id=run.id,
                    workflow_id=workflow.id,
                    active_workflow_id=workflow.id,
                    expires_at=datetime.now(UTC) + timedelta(minutes=30),
                    snapshot=self.snapshots.seal(current),
                    before_hash=revision(current),
                    after_hash=revision(expected),
                    changes=policy["changes"],
                    verification=verification,
                    approval_digest=digest(
                        [
                            run.id,
                            revision(current),
                            revision(expected),
                            policy["changes"],
                            verification,
                        ]
                    ),
                )
                session.add(row)
                incident.status = "awaiting_approval"
                event(
                    session,
                    "repair.snapshot_saved",
                    "Encrypted original workflow snapshot saved; minimal patch "
                    "structurally validated. No replay performed.",
                    workflow.id,
                    incident.id,
                )
                event(
                    session,
                    "approval.requested",
                    "Review the revision-bound diff and verification plan. Approval "
                    "includes conditional rollback.",
                    workflow.id,
                    incident.id,
                )
                session.commit()
                return row.id

    async def decide(self, repair_id: int, action: str, token: str, acknowledged: bool):
        async with self.lock:
            with self.sessions() as session:
                row = session.get(Repair, repair_id)
                if row is None:
                    raise IntegrationError("Repair not found")
                if not compare_digest(row.approval_digest, token):
                    raise IntegrationError("Review digest mismatch; refresh the repair")
                if row.status != "awaiting_approval":
                    raise IntegrationError("This approval is no longer pending")
                if datetime.now(UTC) >= utc(row.expires_at):
                    raise IntegrationError("Approval expired; request a new investigation")
                if action == "approve":
                    if not acknowledged:
                        raise IntegrationError(
                            "Exclusive maintenance and manual verification acknowledgement required"
                        )
                    self.gate(row.workflow_id, write=True)
                    _, _, _, policy = self.source(session, row.investigation_id)
                    if policy["changes"] != row.changes:
                        raise IntegrationError("Proposal changed; approval blocked")
                    current = await self.reader.workflow(row.workflow_id)
                    inactive(current)
                    original = self.snapshots.open(row.snapshot)
                    if revision(current) != row.before_hash or current.get(
                        "versionId"
                    ) != original.get("versionId"):
                        raise IntegrationError("Workflow revision changed; approval blocked")
                    row.status, row.approval = "approved", "approved"
                else:
                    row.status, row.approval, row.active_workflow_id = "rejected", "rejected", None
                    row.finished_at = datetime.now(UTC)
                row.decided_at = datetime.now(UTC)
                session.get(Incident, row.incident_id).status = (
                    "repairing" if action == "approve" else "escalated"
                )
                event(
                    session,
                    f"approval.{row.approval}",
                    "Operator approved this exact diff and conditional rollback."
                    if action == "approve"
                    else "Operator rejected this repair; no changes applied.",
                    row.workflow_id,
                    row.incident_id,
                )
                session.commit()

    async def safety(self, paused: bool):
        with self.sessions() as session:
            state = session.get(RepairSafety, 1)
            if state is None:
                state = RepairSafety(id=1)
                session.add(state)
            state.paused = paused
            event(
                session,
                "safety.paused" if paused else "safety.resumed",
                "Operator paused all mutation writes."
                if paused
                else "Operator released the runtime pause; configured kill switch still applies.",
            )
            session.commit()
