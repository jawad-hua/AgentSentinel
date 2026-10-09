from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


def now():
    return datetime.now(UTC)


class Workflow(Base):
    __tablename__ = "monitored_workflows"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    name: Mapped[str] = mapped_column(String(256))
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    available: Mapped[bool] = mapped_column(Boolean, default=True)
    enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    require_output: Mapped[bool] = mapped_column(Boolean, default=False)
    expect_json: Mapped[bool] = mapped_column(Boolean, default=False)
    contract_node: Mapped[str | None] = mapped_column(String(256))
    json_field: Mapped[str | None] = mapped_column(String(256))
    monitor_since: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_polled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str | None] = mapped_column(String(512))
    backfill_cursor: Mapped[str | None] = mapped_column(Text)


class Execution(Base):
    __tablename__ = "observed_executions"
    id: Mapped[str] = mapped_column(String(128), primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"), index=True)
    status: Mapped[str] = mapped_column(String(32))
    mode: Mapped[str] = mapped_column(String(32))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), index=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
    evidence_available: Mapped[bool] = mapped_column(Boolean, default=False)
    inspected: Mapped[bool] = mapped_column(Boolean, default=False)
    has_findings: Mapped[bool] = mapped_column(Boolean, default=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    inspected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_check_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Incident(Base):
    __tablename__ = "incidents"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"), index=True)
    fingerprint: Mapped[str] = mapped_column(String(64), unique=True)
    kind: Mapped[str] = mapped_column(String(64))
    node: Mapped[str | None] = mapped_column(String(256))
    severity: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(32), default="detected")
    summary: Mapped[str] = mapped_column(String(512))
    first_execution_id: Mapped[str] = mapped_column(ForeignKey("observed_executions.id"))
    last_execution_id: Mapped[str] = mapped_column(ForeignKey("observed_executions.id"))
    occurrences: Mapped[int] = mapped_column(Integer, default=1)
    detected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    evidence: Mapped[dict] = mapped_column(JSON)


class Occurrence(Base):
    __tablename__ = "incident_occurrences"
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    execution_id: Mapped[str] = mapped_column(
        ForeignKey("observed_executions.id"), primary_key=True
    )
    evidence: Mapped[dict] = mapped_column(JSON)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Event(Base):
    __tablename__ = "system_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(64))
    workflow_id: Mapped[str | None] = mapped_column(String(128))
    incident_id: Mapped[int | None] = mapped_column(ForeignKey("incidents.id"), index=True)
    message: Mapped[str] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


Index("ix_execution_baseline", Execution.workflow_id, Execution.mode, Execution.started_at)
