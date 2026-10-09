"""Persist controlled fault sessions and actual probe responses."""

import sqlalchemy as sa
from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "chaos_targets",
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), primary_key=True
        ),
        sa.Column("designated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("session_id", sa.Integer()),
    )
    op.create_table(
        "chaos_sessions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), nullable=False
        ),
        sa.Column("mode", sa.String(16), nullable=False),
        sa.Column("revision", sa.String(64), nullable=False),
        sa.Column("investigation_id", sa.Integer()),
        sa.Column("baseline_execution", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_chaos_sessions_workflow_id", "chaos_sessions", ["workflow_id"])
    op.create_table(
        "chaos_attempts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), nullable=False
        ),
        sa.Column("execution_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chaos_sessions.id")),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("http_status", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    for field in ("workflow_id", "execution_id", "session_id"):
        op.create_index(f"ix_chaos_attempts_{field}", "chaos_attempts", [field])


def downgrade():
    op.drop_table("chaos_attempts")
    op.drop_table("chaos_sessions")
    op.drop_table("chaos_targets")
