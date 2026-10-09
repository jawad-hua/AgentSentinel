from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base
from app.monitoring.models import now


class Repair(Base):
    __tablename__ = "repairs"
    id: Mapped[int] = mapped_column(primary_key=True)
    incident_id: Mapped[int] = mapped_column(ForeignKey("incidents.id"), index=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id"), unique=True)
    workflow_id: Mapped[str] = mapped_column(ForeignKey("monitored_workflows.id"))
    active_workflow_id: Mapped[str | None] = mapped_column(String(128), unique=True)
    status: Mapped[str] = mapped_column(String(32), default="awaiting_approval")
    approval: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    snapshot: Mapped[str] = mapped_column(Text)
    before_hash: Mapped[str] = mapped_column(String(64))
    after_hash: Mapped[str] = mapped_column(String(64))
    approval_digest: Mapped[str] = mapped_column(String(64))
    changes: Mapped[list] = mapped_column(JSON)
    verification: Mapped[dict] = mapped_column(JSON)
    message: Mapped[str | None] = mapped_column(String(512))


class RepairSafety(Base):
    __tablename__ = "repair_safety"
    id: Mapped[int] = mapped_column(primary_key=True)
    paused: Mapped[bool] = mapped_column(Boolean, default=False)
