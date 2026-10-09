import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.chaos.models import ChaosSession, ProbeAttempt
from app.chaos.service import collect_chaos_context
from app.integrations.n8n import IntegrationError
from app.integrations.rate_limits import RateLimited, RetryBudget
from app.investigation.comparisons import collect_comparisons
from app.investigation.evidence import collect
from app.investigation.models import AgentRun, Investigation
from app.investigation.policy import assess
from app.investigation.prompts import BASE, PROMPTS
from app.investigation.repair_history import collect_repair_history
from app.investigation.review import reviewed_triage, triage_review_eligible
from app.investigation.schemas import STAGES, validate_references
from app.investigation.test_context import collect_test_context
from app.monitoring.models import Incident, Occurrence, Workflow
from app.monitoring.service import event
from app.repairs.models import Repair

logger = logging.getLogger("agentsentinel")


class Investigator:
    def __init__(self, sessions, n8n, provider, settings):
        self.sessions, self.n8n, self.provider, self.settings = sessions, n8n, provider, settings
        self.wake = asyncio.Event()
        self.started_at = datetime.now(UTC)

    def enqueue(self, incident_id: int, trigger="operator", review_of: int | None = None) -> int:
        if not self.settings.analysis_enabled:
            raise IntegrationError("Analysis is disabled in server configuration")
        if not self.settings.groq_api_key.get_secret_value():
            raise IntegrationError("Groq API key is not configured")
        with self.sessions() as session:
            incident = session.get(Incident, incident_id)
            if incident is None:
                raise IntegrationError("Incident not found")
            if session.scalar(
                select(Repair.id).where(Repair.active_workflow_id == incident.workflow_id)
            ):
                raise IntegrationError(
                    "An active repair holds this workflow; finish its review first"
                )
            existing = session.scalar(
                select(Investigation).where(Investigation.active_incident_id == incident_id)
            )
            if existing:
                if (
                    review_of is not None
                    and (existing.evidence or {}).get("operator_review_of") != review_of
                ):
                    raise IntegrationError("Another investigation is already active")
                return existing.id
            if review_of is not None:
                source = session.scalar(
                    select(Investigation)
                    .where(Investigation.incident_id == incident_id)
                    .order_by(Investigation.id.desc())
                    .limit(1)
                )
                agents = list(
                    session.scalars(select(AgentRun).where(AgentRun.investigation_id == review_of))
                )
                if (
                    source is None
                    or source.id != review_of
                    or not triage_review_eligible(source, incident, agents)
                ):
                    raise IntegrationError("Only the latest triage-only escalation can be reviewed")
                trigger = "operator_review"
            elif trigger == "operator_review":
                raise IntegrationError("An explicit source investigation is required")
            pending = session.scalar(
                select(func.count())
                .select_from(Investigation)
                .where(Investigation.active_incident_id.is_not(None))
            )
            recent = session.scalar(
                select(func.count())
                .select_from(Investigation)
                .where(Investigation.created_at >= datetime.now(UTC) - timedelta(days=1))
            )
            if pending >= 5 or recent >= self.settings.analysis_daily_limit:
                raise IntegrationError("Analysis queue or rolling 24-hour budget reached")
            row = Investigation(
                incident_id=incident_id,
                execution_id=incident.last_execution_id,
                active_incident_id=incident_id,
                trigger=trigger,
                model=self.settings.groq_model,
                evidence={"operator_review_of": review_of} if review_of is not None else None,
            )
            session.add(row)
            incident.status = "queued"
            event(
                session,
                "investigation.queued",
                "Read-only AI investigation queued.",
                incident.workflow_id,
                incident.id,
            )
            if review_of is not None:
                event(
                    session,
                    "investigation.operator_review_requested",
                    f"Operator requested read-only repair assessment after "
                    f"triage in investigation #{review_of}. No repair authorized.",
                    incident.workflow_id,
                    incident.id,
                )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                existing = session.scalar(
                    select(Investigation).where(Investigation.active_incident_id == incident_id)
                )
                if existing:
                    return existing.id
                raise
            self.wake.set()
            return row.id

    def finish(self, run_id: int, status: str, error: str | None = None, policy=None):
        with self.sessions() as session:
            run = session.get(Investigation, run_id)
            if run is None:
                return
            run.status, run.error, run.policy = status, error, policy
            run.finished_at, run.active_incident_id = datetime.now(UTC), None
            incident = session.get(Incident, run.incident_id)
            incident.status = "review_required" if status == "review_required" else "escalated"
            for agent in session.scalars(
                select(AgentRun).where(
                    AgentRun.investigation_id == run_id, AgentRun.status.in_(["running", "waiting"])
                )
            ):
                agent.status, agent.finished_at = (
                    "interrupted" if status == "interrupted" else "failed",
                    datetime.now(UTC),
                )
            event(
                session,
                f"investigation.{status}",
                error or "Analysis complete. No workflow changes were applied.",
                incident.workflow_id,
                incident.id,
            )
            session.commit()

    async def analyze(self, run_id: int):
        with self.sessions() as session:
            run = session.get(Investigation, run_id)
            incident = session.get(Incident, run.incident_id)
            workflow_id, kind = incident.workflow_id, incident.kind
            review_of = (
                (run.evidence or {}).get("operator_review_of")
                if run.trigger == "operator_review"
                else None
            )
            workflow = session.get(Workflow, workflow_id)
            affected_node = incident.node
            occurrence = session.get(Occurrence, (incident.id, run.execution_id))
            if occurrence is None:
                raise IntegrationError("Persisted execution evidence is unavailable")
            observed = dict(occurrence.evidence)
            history = [
                {"incident_id": row.id, "kind": row.kind, "occurrences": row.occurrences}
                for row in session.scalars(
                    select(Incident)
                    .where(Incident.workflow_id == workflow_id, Incident.id != incident.id)
                    .order_by(Incident.id.desc())
                    .limit(5)
                )
            ]
            run.status, run.stage = "running", "evidence"
            run.model = self.settings.groq_model
            incident.status = "investigating"
            event(
                session,
                "evidence.started",
                "Collecting minimized execution evidence.",
                workflow_id,
                incident.id,
            )
            session.commit()
        detail = await self.n8n.execution(run.execution_id)
        current = await self.n8n.workflow(workflow_id)
        if str(current.get("id")) != workflow_id:
            raise IntegrationError("Current workflow identity mismatch")
        secret_values = tuple(
            getattr(self.settings, key).get_secret_value()
            for key in ("admin_api_token", "ingest_api_token", "n8n_api_key", "groq_api_key")
        )
        bundle = collect(detail, current, run, observed, history, affected_node, secret_values)
        await collect_comparisons(self.n8n, workflow, bundle, detail)
        await collect_chaos_context(self.sessions, self.settings, detail, current, bundle)
        await collect_test_context(
            self.n8n, self.sessions, self.settings, incident.id, workflow, current, detail, bundle
        )
        await collect_repair_history(
            self.n8n, self.sessions, self.settings, incident.id, workflow, current, bundle
        )
        inherited_triage = None
        if review_of is not None:
            with self.sessions() as session:
                source = session.get(Investigation, review_of)
                latest_incident = session.get(Incident, run.incident_id)
                agents = list(
                    session.scalars(select(AgentRun).where(AgentRun.investigation_id == review_of))
                )
                if source is None or source.incident_id != run.incident_id:
                    raise IntegrationError("Source investigation unavailable")
                inherited_triage = reviewed_triage(source, latest_incident, agents, bundle)
            bundle["operator_review_of"] = review_of
            bundle["limits"].append(
                f"Operator requested a read-only assessment after investigation #{review_of}. "
                "Its original triage is referenced unchanged as "
                "interpretation of its historical evidence; "
                "it is not a new agent run or a repair authorization. "
                "Current facts were recollected."
            )
        bundle["detection_kind"] = kind
        del detail, current
        with self.sessions() as session:
            row = session.get(Investigation, run_id)
            row.evidence = bundle
            event(
                session,
                "evidence.collected",
                "Execution facts, aliased configuration and "
                f"{bundle['comparison_scope']['included']} comparable saved executions and "
                f"{bundle['repair_history_scope']['included']} historical repair records captured.",
                workflow_id,
                row.incident_id,
            )
            session.commit()
        outputs = {"triage": inherited_triage} if inherited_triage is not None else {}
        retry_budget = RetryBudget()
        for stage, schema in STAGES.items():
            if stage == "triage" and inherited_triage is not None:
                with self.sessions() as session:
                    event(
                        session,
                        "agent.triage.referenced",
                        f"Original triage from investigation #{review_of} "
                        f"retained. Operator requested remaining read-only assessment stages.",
                        workflow_id,
                        run.incident_id,
                    )
                    session.commit()
                continue
            if not self.settings.analysis_enabled:
                raise IntegrationError("Analysis disabled")
            with self.sessions() as session:
                row = session.get(Investigation, run_id)
                row.stage = stage
                agent = AgentRun(investigation_id=run_id, stage=stage)
                session.add(agent)
                event(
                    session,
                    f"agent.{stage}.started",
                    f"{stage.title()} analysis started.",
                    workflow_id,
                    row.incident_id,
                )
                session.commit()
                agent_id = agent.id
            required_context = {
                "triage": (),
                "diagnosis": ("triage",),
                "fix": ("diagnosis",),
                "validator": ("diagnosis", "fix"),
                "risk": ("diagnosis", "fix", "validator"),
            }
            context = {key: outputs[key] for key in required_context[stage]}
            stage_retried = False
            while True:
                try:
                    output = await self.provider.generate(
                        BASE
                        + PROMPTS[stage]
                        + (
                            "\nThe operator requested assessment of candidate configuration "
                            "changes after a prior triage stop. This analysis is read-only: it"
                            " cannot APPLY workflow changes. That execution restriction does "
                            "not prohibit PROPOSING a candidate change for later independent "
                            "validation, risk review and explicit approval. Evaluate the "
                            "recorded operator objective against the observed facts. "
                            "Historical triage is interpretation, not a binding replacement "
                            "for that objective. A proposal is data, not authorization to "
                            "write. Do not assume a repair is needed; no_safe_fix remains "
                            "valid when justified by the evidence and allowed actions."
                            if inherited_triage is not None
                            else ""
                        ),
                        {
                            "facts": bundle["facts"],
                            "detection_kind": kind,
                            "revision_matches": bundle["revision_matches"],
                            "limitations": bundle["limits"],
                            "previous_stages": context,
                        },
                        schema,
                    )
                    break
                except RateLimited as exc:
                    delay = retry_budget.reserve(exc.retry_after_seconds, stage_retried)
                    stage_retried = True
                    self.rate_event(
                        agent_id,
                        "waiting",
                        workflow_id,
                        run.incident_id,
                        f"Groq returned HTTP 429. Waiting {delay} seconds before "
                        f"retrying {stage}; completed stages are retained.",
                    )
                    # Non-blocking, cancellable wait: API, monitoring and SSE remain responsive.
                    await asyncio.sleep(delay)
                    if not self.settings.analysis_enabled:
                        raise IntegrationError("Analysis disabled during rate-limit wait") from None
                    self.rate_event(
                        agent_id,
                        "running",
                        workflow_id,
                        run.incident_id,
                        f"Rate-limit wait ended; retrying {stage} once.",
                    )
            validate_references(output, bundle["facts"])
            if stage == "triage" and output.affected_node is not None:
                if output.affected_node not in {n["node"] for n in bundle["nodes"]}:
                    raise ValueError("Unknown triage node")
            if stage == "validator":
                supported = output.supported_hypotheses
                if len(supported) != len(set(supported)) or any(
                    i < 0 or i >= len(outputs["diagnosis"]["hypotheses"]) for i in supported
                ):
                    raise ValueError("Validator cited an unknown or duplicate hypothesis")
            outputs[stage] = output.model_dump()
            with self.sessions() as session:
                agent = session.get(AgentRun, agent_id)
                agent.output, agent.status, agent.finished_at = (
                    outputs[stage],
                    "completed",
                    datetime.now(UTC),
                )
                event(
                    session,
                    f"agent.{stage}.completed",
                    f"{stage.title()} structured output validated.",
                    workflow_id,
                    run.incident_id,
                )
                session.commit()
            if stage == "triage" and not output.investigate:
                self.finish(
                    run_id,
                    "escalated",
                    "Triage requested operator review; deeper analysis skipped.",
                )
                return
        policy = assess(
            bundle,
            STAGES["diagnosis"](**outputs["diagnosis"]),
            STAGES["fix"](**outputs["fix"]),
            STAGES["validator"](**outputs["validator"]),
            STAGES["risk"](**outputs["risk"]),
            kind,
        )
        self.finish(
            run_id,
            "blocked" if policy["decision"] == "blocked" else "review_required",
            policy=policy,
        )

    def rate_event(
        self, agent_id: int, status: str, workflow_id: str, incident_id: int, message: str
    ):
        with self.sessions() as session:
            agent = session.get(AgentRun, agent_id)
            agent.status = status
            event(
                session,
                f"agent.{agent.stage}.{'rate_limited' if status == 'waiting' else 'retrying'}",
                message,
                workflow_id,
                incident_id,
            )
            session.commit()

    def recover_interrupted(self):
        # Called only between jobs by the single worker, never during a provider call.
        with self.sessions() as session:
            ids = list(
                session.scalars(select(Investigation.id).where(Investigation.status == "running"))
            )
        for run_id in ids:
            self.finish(
                run_id,
                "interrupted",
                "Analysis interrupted by service or database restart; request another analysis.",
            )

    def enqueue_chaos(self):
        # One automatic investigation per experiment, even when incidents deduplicate.
        with self.sessions() as session:
            rows = list(
                session.execute(
                    select(ChaosSession.id, Incident.id, Incident.last_execution_id)
                    .join(ProbeAttempt, ProbeAttempt.session_id == ChaosSession.id)
                    .join(Occurrence, Occurrence.execution_id == ProbeAttempt.execution_id)
                    .join(Incident, Incident.id == Occurrence.incident_id)
                    .where(
                        ChaosSession.investigation_id.is_(None),
                        ChaosSession.stopped_at.is_(None),
                        ChaosSession.expires_at > datetime.now(UTC),
                        ProbeAttempt.http_status == 503,
                        Incident.last_execution_id == ProbeAttempt.execution_id,
                    )
                    .distinct()
                    .limit(5)
                )
            )
        for experiment_id, incident_id, execution_id in rows:
            with self.sessions() as session:
                existing = session.scalar(
                    select(Investigation.id)
                    .where(
                        Investigation.incident_id == incident_id,
                        Investigation.execution_id == execution_id,
                    )
                    .order_by(Investigation.id.desc())
                )
            try:
                run_id = existing or self.enqueue(incident_id, "automatic")
            except IntegrationError:
                continue
            with self.sessions() as session:
                session.get(ChaosSession, experiment_id).investigation_id = run_id
                session.commit()

    async def run(self):
        while True:
            try:
                self.wake.clear()
                self.recover_interrupted()
                if self.settings.analysis_enabled:
                    if (
                        self.settings.analysis_auto_new
                        and self.settings.groq_api_key.get_secret_value()
                    ):
                        self.enqueue_chaos()
                        with self.sessions() as session:
                            incident_ids = list(
                                session.scalars(
                                    select(Incident.id)
                                    .join(Workflow)
                                    .where(
                                        Workflow.enabled.is_(True),
                                        Incident.detected_at >= self.started_at,
                                        ~select(Investigation.id)
                                        .where(Investigation.incident_id == Incident.id)
                                        .exists(),
                                    )
                                    .order_by(Incident.id)
                                    .limit(5)
                                )
                            )
                        for incident_id in incident_ids:
                            try:
                                self.enqueue(incident_id, "automatic")
                            except IntegrationError:
                                break
                    with self.sessions() as session:
                        run_id = session.scalar(
                            select(Investigation.id)
                            .where(Investigation.status == "queued")
                            .order_by(Investigation.id)
                            .limit(1)
                        )
                    if run_id:
                        try:
                            await asyncio.wait_for(self.analyze(run_id), timeout=720)
                        except asyncio.CancelledError:
                            self.finish(
                                run_id,
                                "interrupted",
                                "Service stopped during analysis; request another analysis.",
                            )
                            raise
                        except IntegrationError as exc:
                            self.finish(run_id, "failed", str(exc))
                        except (ValueError, TypeError, KeyError, AttributeError):
                            self.finish(
                                run_id,
                                "failed",
                                "Evidence or structured agent output failed validation.",
                            )
                        except TimeoutError:
                            self.finish(
                                run_id,
                                "failed",
                                "Investigation exceeded its twelve-minute time budget.",
                            )
                        continue
                try:
                    await asyncio.wait_for(self.wake.wait(), timeout=5)
                except TimeoutError:
                    pass
            except SQLAlchemyError:
                logger.warning("Investigation database unavailable; worker will retry")
                await asyncio.sleep(5)
