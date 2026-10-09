from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.monitoring.models import now


class ChaosTarget(Base):
    __tablename__ = "chaos_targets"
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"), primary_key=True)
    designated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    session_id: Mapped[int | None] = mapped_column(nullable=True)


class ChaosSession(Base):
    __tablename__ = "chaos_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"), index=True)
    mode: Mapped[str] = mapped_column(String(16))
    revision: Mapped[str] = mapped_column(String(64))
    investigation_id: Mapped[int | None] = mapped_column(nullable=True)
    baseline_execution: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ProbeAttempt(Base):
    __tablename__ = "chaos_attempts"
    id: Mapped[int] = mapped_column(primary_key=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"), index=True)
    execution_id: Mapped[str] = mapped_column(String(128), index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chaos_sessions.id"), index=True)
    attempt: Mapped[int]
    http_status: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
