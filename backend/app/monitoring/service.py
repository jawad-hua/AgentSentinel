import asyncio
import logging
import re
from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.integrations.n8n import IntegrationError
from app.monitoring.models import Event, Execution, Incident, Occurrence, Workflow
from app.monitoring.normalize import (
    STATUSES,
    TERMINAL,
    detect,
    latency_finding,
    safe_label,
    timestamp,
)

logger = logging.getLogger("agentsentinel")


def utc(value):
    return value.replace(tzinfo=UTC) if value and value.tzinfo is None else value


def valid_id(value):
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,128}", value):
        raise IntegrationError("n8n returned an invalid identifier")
    return value


def event(session, kind, message, workflow_id=None, incident_id=None):
    session.add(Event(kind=kind, message=message, workflow_id=workflow_id, incident_id=incident_id))


class Monitor:
    def __init__(self, sessions, n8n, settings):
        self.sessions, self.n8n, self.settings = sessions, n8n, settings
        self.wake = asyncio.Event()
        self.poll_lock = asyncio.Lock()
        self.sync_lock = asyncio.Lock()
        self.secrets = tuple(
            value.get_secret_value()
            for value in (
                settings.admin_api_token,
                settings.ingest_api_token,
                settings.n8n_api_key,
                settings.groq_api_key,
            )
        )

    async def sync(self):
        if self.sync_lock.locked():
            raise IntegrationError("Workflow sync is already running")
        async with self.sync_lock:
            catalog, cursor, seen = [], None, set()
            try:
                async with asyncio.timeout(45):
                    for _ in range(10):
                        page = await self.n8n.workflows(cursor)
                        rows = page.get("data")
                        if not isinstance(rows, list):
                            raise IntegrationError("Invalid n8n workflow list")
                        for row in rows:
                            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                                raise IntegrationError("Invalid n8n workflow metadata")
                            valid_id(row.get("id"))
                        catalog.extend(rows)
                        cursor = page.get("nextCursor")
                        if not cursor:
                            break
                        if not isinstance(cursor, str) or cursor in seen:
                            raise IntegrationError("Invalid n8n pagination cursor")
                        seen.add(cursor)
                    else:
                        raise IntegrationError(
                            "Catalog exceeds 1,000 workflows; sync was not applied"
                        )
            except TimeoutError:
                raise IntegrationError(
                    "Workflow catalog sync timed out; existing catalog retained"
                ) from None
            # Commit only after the entire catalog has been fetched successfully.
            with self.sessions() as session:
                existing = {row.id: row for row in session.scalars(select(Workflow))}
                found = set()
                for row in catalog:
                    found.add(row["id"])
                    current = existing.get(row["id"])
                    if current is None:
                        current = Workflow(id=row["id"], name=safe_label(row["name"], self.secrets))
                        session.add(current)
                    current.name = safe_label(row["name"], self.secrets)
                    current.active = row.get("active") is True
                    current.available = True
                    current.synced_at = datetime.now(UTC)
                for key, current in existing.items():
                    if key not in found:
                        current.available = False
                        current.enabled = False
                        current.last_error = (
                            "Workflow no longer appears in the accessible n8n catalog"
                        )
                event(
                    session, "catalog.synced", f"Synced {len(found)} accessible workflows from n8n."
                )
                session.commit()
            return {"synced": len(found)}

    async def run(self):
        while True:
            self.wake.clear()
            try:
                await self.poll()
            except asyncio.CancelledError:
                raise
            except Exception:
                # Do not log upstream payloads, exception strings or credentials.
                logger.error('{"event":"monitor.cycle_failed"}')
            try:
                await asyncio.wait_for(
                    self.wake.wait(), timeout=self.settings.poll_interval_seconds
                )
            except TimeoutError:
                pass

    async def poll(self):
        if self.poll_lock.locked() or not self.settings.monitoring_enabled:
            return
        async with self.poll_lock:
            with self.sessions() as session:
                ids = list(
                    session.scalars(
                        select(Workflow.id)
                        .where(Workflow.enabled.is_(True), Workflow.available.is_(True))
                        .order_by(Workflow.id)
                    )
                )
            for workflow_id in ids:
                try:
                    async with asyncio.timeout(45):
                        await self.poll_workflow(workflow_id)
                except asyncio.CancelledError:
                    raise
                except Exception as exc:
                    message = (
                        str(exc)
                        if isinstance(exc, IntegrationError)
                        else "Execution check reached its time budget; will resume"
                        if isinstance(exc, TimeoutError)
                        else "Execution evidence could not be processed safely"
                    )
                    with self.sessions() as session:
                        workflow = session.get(Workflow, workflow_id)
                        if workflow and workflow.last_error != message:
                            event(session, "monitor.failed", message, workflow_id)
                        if workflow:
                            workflow.last_error = message
                            session.commit()

    async def poll_workflow(self, workflow_id):
        with self.sessions() as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow or not workflow.enabled:
                return
            cursor, since = workflow.backfill_cursor, utc(workflow.monitor_since)
            pending = list(
                session.scalars(
                    select(Execution.id)
                    .where(
                        Execution.workflow_id == workflow_id,
                        Execution.inspected.is_(False),
                        (
                            Execution.next_check_at.is_(None)
                            | (Execution.next_check_at <= datetime.now(UTC))
                        ),
                    )
                    .order_by(Execution.next_check_at, Execution.observed_at)
                    .limit(10)
                )
            )
        # Inspect the head page during backfill so new failures are not starved.
        head = await self.n8n.executions(workflow_id=workflow_id)
        pages = [head]
        next_cursor = head.get("nextCursor")
        if cursor:
            try:
                older = await self.n8n.executions(cursor, workflow_id)
            except IntegrationError:
                with self.sessions() as session:
                    session.get(Workflow, workflow_id).backfill_cursor = None
                    session.commit()
                raise
            pages.append(older)
            next_cursor = older.get("nextCursor")
        if next_cursor is not None and (not isinstance(next_cursor, str) or next_cursor == cursor):
            raise IntegrationError("n8n execution cursor did not advance")
        candidates = {key: datetime.min.replace(tzinfo=UTC) for key in pending}
        for page in pages:
            if not isinstance(page.get("data"), list):
                raise IntegrationError("Invalid n8n execution list")
            for row in page["data"]:
                if not isinstance(row, dict) or row.get("workflowId") != workflow_id:
                    raise IntegrationError("Execution workflow mismatch")
                execution_id = valid_id(row.get("id"))
                started = timestamp(row.get("startedAt"))
                if not started or since and started < since:
                    continue
                with self.sessions() as session:
                    existing = session.get(Execution, execution_id)
                    if existing and (
                        existing.inspected
                        or utc(existing.next_check_at)
                        and utc(existing.next_check_at) > datetime.now(UTC)
                    ):
                        continue
                candidates[execution_id] = started
        missing = False
        # Hold only one bounded trace at a time; never accumulate payloads on a 4 GB host.
        for execution_id in sorted(candidates, key=lambda key: candidates[key]):
            try:
                detail = await self.n8n.execution(execution_id)
            except IntegrationError as exc:
                if exc.status_code != 404:
                    raise
                missing = True
                with self.sessions() as session:
                    old = session.get(Execution, execution_id)
                    if old:
                        old.next_check_at = datetime.now(UTC) + timedelta(hours=1)
                    event(
                        session,
                        "evidence.unavailable",
                        "n8n no longer retains a requested execution.",
                        workflow_id,
                    )
                    session.commit()
                continue
            if detail.get("id") != execution_id or detail.get("workflowId") != workflow_id:
                raise IntegrationError("Execution detail identity mismatch")
            self.record(workflow_id, detail)
        with self.sessions() as session:
            workflow = session.get(Workflow, workflow_id)
            if workflow and workflow.enabled:
                workflow.last_polled_at = datetime.now(UTC)
                workflow.last_error = (
                    "Some requested execution evidence is no longer retained by n8n"
                    if missing
                    else None
                )
                workflow.backfill_cursor = next_cursor
                event(session, "monitor.polled", "Read execution evidence from n8n.", workflow_id)
                session.commit()

    def record(self, workflow_id, detail):
        execution_id = valid_id(detail.get("id"))
        if detail.get("workflowId") != workflow_id:
            raise IntegrationError("Execution workflow mismatch")
        with self.sessions() as session:
            workflow = session.get(Workflow, workflow_id)
            if not workflow or not workflow.enabled:
                return
            row = session.get(Execution, execution_id)
            if row and row.workflow_id != workflow_id:
                raise IntegrationError("Stored execution belongs to another workflow")
            if row and row.inspected:
                return
            if row is None:
                row = Execution(id=execution_id, workflow_id=workflow_id)
                session.add(row)
            row.inspected = False
            row.has_findings = False
            row.evidence_available = False
            row.status = detail.get("status") if detail.get("status") in STATUSES else "unknown"
            row.mode = str(detail.get("mode", "unknown"))[:32]
            row.started_at, row.stopped_at = (
                timestamp(detail.get("startedAt")),
                timestamp(detail.get("stoppedAt")),
            )
            row.duration_ms = None
            if row.started_at and row.stopped_at and row.stopped_at >= row.started_at:
                row.duration_ms = round((row.stopped_at - row.started_at).total_seconds() * 1000)
            row.next_check_at = datetime.now(UTC) + timedelta(
                seconds=self.settings.poll_interval_seconds
            )
            if row.status not in TERMINAL:
                session.commit()
                return
            findings, row.evidence_available = detect(detail, workflow, self.secrets)
            if row.status == "success" and row.duration_ms is not None and row.started_at:
                baseline = list(
                    session.scalars(
                        select(Execution.duration_ms)
                        .where(
                            Execution.workflow_id == workflow_id,
                            Execution.mode == row.mode,
                            Execution.status == "success",
                            Execution.has_findings.is_(False),
                            Execution.inspected.is_(True),
                            Execution.duration_ms.is_not(None),
                            Execution.started_at < row.started_at,
                        )
                        .order_by(Execution.started_at.desc())
                        .limit(50)
                    )
                )
                latency = latency_finding(row.duration_ms, baseline)
                if latency:
                    findings.append(latency)
            row.inspected = True
            row.inspected_at = datetime.now(UTC)
            row.has_findings = bool(findings)
            session.flush()
            for finding in findings:
                fingerprint = finding.fingerprint(workflow_id)
                incident = session.scalar(
                    select(Incident).where(Incident.fingerprint == fingerprint)
                )
                evidence = {
                    **finding.evidence,
                    "execution_id": execution_id,
                    "execution_status": row.status,
                }
                if incident is None:
                    incident = Incident(
                        workflow_id=workflow_id,
                        fingerprint=fingerprint,
                        kind=finding.kind,
                        node=finding.node,
                        severity=finding.severity,
                        summary=finding.summary,
                        first_execution_id=execution_id,
                        last_execution_id=execution_id,
                        evidence=evidence,
                    )
                    session.add(incident)
                    session.flush()
                    event(session, "incident.detected", finding.summary, workflow_id, incident.id)
                elif session.get(Occurrence, (incident.id, execution_id)):
                    continue
                else:
                    if incident.status == "healed":
                        incident.status = "detected"
                        event(
                            session,
                            "incident.reopened",
                            "A new observed failure reopened this incident.",
                            workflow_id,
                            incident.id,
                        )
                    incident.occurrences += 1
                    incident.last_execution_id = execution_id
                    incident.last_seen_at = datetime.now(UTC)
                    incident.evidence = evidence
                    event(
                        session,
                        "incident.repeated",
                        "Same failure signature observed in another execution.",
                        workflow_id,
                        incident.id,
                    )
                session.add(
                    Occurrence(
                        incident_id=incident.id, execution_id=execution_id, evidence=evidence
                    )
                )
            event(
                session,
                "execution.observed",
                f"Recorded an actual n8n execution with status {row.status}.",
                workflow_id,
            )
            session.commit()
