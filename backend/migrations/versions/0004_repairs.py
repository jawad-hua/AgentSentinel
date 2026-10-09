"""Encrypted snapshots, revision-bound approval, durable mutation intents and safety latch."""

import sqlalchemy as sa
from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "repairs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column(
            "investigation_id",
            sa.Integer(),
            sa.ForeignKey("investigations.id"),
            unique=True,
            nullable=False,
        ),
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), nullable=False
        ),
        sa.Column("active_workflow_id", sa.String(128), unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("approval", sa.String(32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decided_at", sa.DateTime(timezone=True)),
        sa.Column("applied_at", sa.DateTime(timezone=True)),
        sa.Column("deadline", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("snapshot", sa.Text(), nullable=False),
        sa.Column("before_hash", sa.String(64), nullable=False),
        sa.Column("after_hash", sa.String(64), nullable=False),
        sa.Column("approval_digest", sa.String(64), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=False),
        sa.Column("verification", sa.JSON(), nullable=False),
        sa.Column("message", sa.String(512)),
    )
    op.create_index("ix_repairs_incident_id", "repairs", ["incident_id"])
    op.create_table(
        "repair_safety",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("paused", sa.Boolean(), nullable=False),
    )


def downgrade():
    op.drop_table("repair_safety")
    op.drop_table("repairs")
