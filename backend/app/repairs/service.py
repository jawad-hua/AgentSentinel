"""Durable single-worker write intents, conservative read-back and revision-safe rollback."""

import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from app.integrations.n8n import IntegrationError
from app.monitoring.models import Incident, Workflow
from app.monitoring.service import event
from app.repairs.approval import Approvals
from app.repairs.models import Repair
from app.repairs.patches import inactive, patch, payload, revision
from app.repairs.verification import evaluate, utc

logger = logging.getLogger("agentsentinel")
ACTIVE = {"approved", "applying", "verifying", "rolling_back", "rollback_pending"}


class Repairer(Approvals):
    def save_state(self, rid: int, status: str, message: str, *, terminal=False, **fields):
        with self.sessions() as session:
            row = session.get(Repair, rid)
            row.status, row.message = status, message
            for key, value in fields.items():
                setattr(row, key, value)
            if terminal:
                row.finished_at = datetime.now(UTC)
                # Uncertain post-write state holds the workflow until operator investigation.
                if status != "escalated" or row.applied_at is None:
                    row.active_workflow_id = None
            incident = session.get(Incident, row.incident_id)
            incident.status = {
                "healed": "healed",
                "verifying": "verifying",
                "applying": "repairing",
                "rolling_back": "rolling_back",
            }.get(status, "escalated")
            event(session, f"repair.{status}", message, row.workflow_id, row.incident_id)
            session.commit()

    def record_write_error(self, row, exc: IntegrationError):
        # Persist only a status code, never upstream bodies, credentials or URLs.
        message = (
            f"n8n update returned HTTP {exc.status_code}; reconciling actual configuration."
            if exc.status_code is not None
            else "n8n update transport outcome uncertain; reconciling actual configuration."
        )
        with self.sessions() as session:
            event(session, "repair.write_error", message, row.workflow_id, row.incident_id)
            session.commit()

    async def idle_workflow(self, workflow_id: str):
        cursor = None
        for _ in range(20):
            page = await self.reader.executions(cursor, workflow_id)
            if not isinstance(page.get("data"), list):
                raise IntegrationError("n8n execution listing is unavailable")
            for item in page["data"]:
                if item.get("status") in {"new", "running", "waiting"}:
                    raise IntegrationError("Workflow has an in-flight execution; no write allowed")
            cursor = page.get("nextCursor")
            if not cursor:
                return
        raise IntegrationError("Execution history exceeds the bounded pre-write scan")

    async def apply(self, row: Repair):
        self.gate(row.workflow_id, write=True)
        if datetime.now(UTC) >= utc(row.expires_at):
            raise IntegrationError("Approved repair expired before execution")
        with self.sessions() as session:
            _, _, _, policy = self.source(session, row.investigation_id)
            if policy["changes"] != row.changes:
                raise IntegrationError("Stored diff no longer matches validated proposal")
        await self.idle_workflow(row.workflow_id)
        current = await self.reader.workflow(row.workflow_id)
        inactive(current)
        original = self.snapshots.open(row.snapshot)
        if (
            str(current.get("id")) != row.workflow_id
            or revision(current) != row.before_hash
            or current.get("versionId") != original.get("versionId")
        ):
            raise IntegrationError("Revision changed before write; no patch applied")
        expected = patch(original, row.changes)
        if revision(expected) != row.after_hash:
            raise IntegrationError("Snapshot/diff integrity check failed")
        self.gate(row.workflow_id, write=True)
        now = datetime.now(UTC)
        self.save_state(
            row.id,
            "applying",
            "Write intent persisted before the n8n update.",
            applied_at=now,
            deadline=now + timedelta(seconds=row.verification["timeout_seconds"]),
        )
        try:
            await self.writer.update_workflow(row.workflow_id, payload(expected))
        except IntegrationError as exc:
            # Never blindly repeat a timed-out write. The following GET resolves its outcome.
            self.record_write_error(row, exc)
        await self.reconcile_apply(row.id)

    async def reconcile_apply(self, rid: int):
        with self.sessions() as session:
            row = session.get(Repair, rid)
        current = await self.reader.workflow(row.workflow_id)
        inactive(current)
        if revision(current) == row.after_hash:
            self.save_state(
                rid,
                "verifying",
                "Patched configuration confirmed by n8n read-back. Run two full "
                "executions in n8n; automatic replay is disabled.",
            )
        elif revision(current) == row.before_hash:
            self.save_state(
                rid,
                "failed",
                "n8n still has the original configuration; no successful application was observed.",
                terminal=True,
            )
        else:
            self.save_state(
                rid,
                "escalated",
                "Unexpected revision after write; snapshot retained. Automatic overwrite blocked.",
                terminal=True,
            )

    async def verify(self, row: Repair):
        current = await self.reader.workflow(row.workflow_id)
        inactive(current)
        if revision(current) != row.after_hash:
            raise IntegrationError(
                "Workflow changed during verification; automatic overwrite blocked"
            )
        original = self.snapshots.open(row.snapshot)
        expected = patch(original, row.changes)
        with self.sessions() as session:
            workflow = session.get(Workflow, row.workflow_id)
        if any(getattr(workflow, k) != v for k, v in row.verification["contract"].items()):
            await self.rollback(row, "Output contract changed during verification")
            return
        evidence = dict(row.verification)
        success = set(evidence["success_ids"])
        checked = set(evidence["checked_ids"])
        pending = False
        cursor = None
        for _ in range(20):
            page = await self.reader.executions(cursor, row.workflow_id)
            if not isinstance(page.get("data"), list):
                raise IntegrationError("n8n execution listing is unavailable")
            for item in page["data"]:
                eid = str(item["id"])
                if eid in checked:
                    continue
                detail = await self.reader.execution(eid)
                outcome = evaluate(
                    detail, expected, workflow, row.applied_at, row.changes[0]["node"]
                )
                if outcome == "failed":
                    evidence["failed_ids"] = [*evidence["failed_ids"], eid]
                    self.record_evidence(row.id, evidence)
                    await self.rollback(
                        row, "Patched execution failed or violated the output contract"
                    )
                    return
                if outcome == "success":
                    success.add(eid)
                    checked.add(eid)
                elif outcome in {"pending", "unproven"}:
                    pending = True
                else:
                    checked.add(eid)
                if len(checked) > 1000:
                    raise IntegrationError(
                        "Verification evidence exceeds its bounded history budget"
                    )
            cursor = page.get("nextCursor")
            if not cursor:
                break
        if cursor:
            raise IntegrationError("Verification history is incomplete; recovery cannot be claimed")
        evidence.update(success_ids=sorted(success), checked_ids=sorted(checked))
        self.record_evidence(row.id, evidence)
        now = datetime.now(UTC)
        if now >= utc(row.deadline):
            await self.rollback(row, "Verification deadline expired without confirmed recovery")
        elif (
            len(success) >= evidence["required_successes"]
            and not pending
            and (now - utc(row.applied_at)).total_seconds() >= evidence["minimum_window_seconds"]
        ):
            # Recheck revision after evidence collection before declaring a bounded recovery.
            final = await self.reader.workflow(row.workflow_id)
            inactive(final)
            if revision(final) != row.after_hash:
                raise IntegrationError("Workflow changed before recovery confirmation")
            self.save_state(
                row.id,
                "healed",
                "Recovery verified from two or more full executions of the patched "
                "revision during the observation window.",
                terminal=True,
            )

    def record_evidence(self, rid: int, evidence: dict):
        with self.sessions() as session:
            row = session.get(Repair, rid)
            if row.verification.get("success_ids") != evidence.get("success_ids"):
                event(
                    session,
                    "verification.execution",
                    f"Verified {len(evidence['success_ids'])} successful patched executions.",
                    row.workflow_id,
                    row.incident_id,
                )
            row.verification = evidence
            session.commit()

    async def rollback(self, row: Repair, reason: str):
        try:
            self.gate(row.workflow_id, write=True)
        except IntegrationError:
            if row.status != "rollback_pending":
                self.save_state(
                    row.id,
                    "rollback_pending",
                    reason + "; writes paused. Snapshot retained; release the safety gate "
                    "to resume rollback.",
                )
            return
        await self.idle_workflow(row.workflow_id)
        current = await self.reader.workflow(row.workflow_id)
        inactive(current)
        if revision(current) == row.before_hash:
            self.save_state(
                row.id,
                "rolled_back",
                "Original configuration confirmed. Incident remains escalated; "
                "recovery was not proved.",
                terminal=True,
            )
            return
        if revision(current) != row.after_hash:
            raise IntegrationError(
                "Concurrent change detected; rollback cannot safely overwrite it"
            )
        original = self.snapshots.open(row.snapshot)
        if revision(original) != row.before_hash:
            raise IntegrationError("Snapshot integrity check failed")
        self.gate(row.workflow_id, write=True)
        self.save_state(
            row.id, "rolling_back", reason + "; restoring the encrypted original configuration."
        )
        try:
            await self.writer.update_workflow(row.workflow_id, payload(original))
        except IntegrationError as exc:
            self.record_write_error(row, exc)
        # Rollback intents are reconciled once, never replayed after uncertain writes.
        await self.reconcile_rollback(row.id)

    async def reconcile_rollback(self, rid: int):
        with self.sessions() as session:
            row = session.get(Repair, rid)
        current = await self.reader.workflow(row.workflow_id)
        inactive(current)
        if revision(current) == row.before_hash:
            self.save_state(
                rid,
                "rolled_back",
                "Original configuration restored and read-back verified; incident escalated.",
                terminal=True,
            )
        else:
            self.save_state(
                rid,
                "escalated",
                "Rollback could not be confirmed; snapshot retained for operator recovery.",
                terminal=True,
            )

    async def recover(self, rid: int):
        """Operator-triggered read reconciliation; never clears an unknown revision."""
        async with self.lock:
            with self.sessions() as session:
                row = session.get(Repair, rid)
                if row is None or row.status != "escalated" or not row.active_workflow_id:
                    raise IntegrationError("No unresolved write is held by this repair")
            await self.idle_workflow(row.workflow_id)
            current = await self.reader.workflow(row.workflow_id)
            inactive(current)
            if revision(current) == row.before_hash:
                self.save_state(
                    rid,
                    "rolled_back",
                    "Operator reconciliation confirmed the original configuration; "
                    "workflow claim released.",
                    terminal=True,
                )
            elif revision(current) == row.after_hash and row.approval == "approved":
                self.save_state(
                    rid,
                    "rollback_pending",
                    "Operator reconciliation found the patched revision; resuming "
                    "the previously authorized conditional rollback.",
                    finished_at=None,
                )
            else:
                raise IntegrationError(
                    "Revision remains unknown; restore the original safely in n8n before rechecking"
                )

    async def tick(self):
        async with self.lock:
            with self.sessions() as session:
                rows = list(
                    session.scalars(select(Repair).where(Repair.active_workflow_id.is_not(None)))
                )
            for row in rows:
                if row.status == "awaiting_approval" and datetime.now(UTC) >= utc(row.expires_at):
                    self.save_state(
                        row.id,
                        "expired",
                        "Unapproved review expired; no changes applied.",
                        terminal=True,
                        approval="expired",
                    )
                if row.status not in ACTIVE:
                    continue
                try:
                    await asyncio.wait_for(self.step(row), timeout=45)
                except TimeoutError:
                    with self.sessions() as session:
                        current = session.get(Repair, row.id)
                        status = current.status
                    if status in {"applying", "rolling_back"}:
                        self.save_state(
                            row.id,
                            status,
                            "Write stage timed out; persisted intent will be reconciled "
                            "before any further action.",
                        )
                    else:
                        self.save_state(
                            row.id,
                            "escalated",
                            "Safety/evidence scan exceeded its time budget; "
                            "operator reconciliation required.",
                            terminal=True,
                        )
                except IntegrationError as exc:
                    self.save_state(row.id, "escalated", str(exc), terminal=True)
                except (ValueError, TypeError, KeyError, IndexError, AttributeError):
                    self.save_state(
                        row.id,
                        "escalated",
                        "Safety or evidence validation failed; snapshot retained for "
                        "operator review.",
                        terminal=True,
                    )

    async def step(self, row: Repair):
        if row.status == "approved":
            # Pause, rather than discard approvals, while a runtime kill switch is set.
            if not self.paused():
                await self.apply(row)
        elif row.status == "applying":
            await self.reconcile_apply(row.id)
        elif row.status == "verifying":
            await self.verify(row)
        elif row.status == "rolling_back":
            await self.reconcile_rollback(row.id)
        elif row.status == "rollback_pending":
            await self.rollback(row, "Resuming previously authorized rollback")

    async def run(self):
        while True:
            try:
                await self.tick()
            except SQLAlchemyError:
                logger.warning(
                    "Repair database unavailable; persisted write intents will be reconciled"
                )
            await asyncio.sleep(5)
