"""Durable bounded investigations and individual agent runs."""

import sqlalchemy as sa
from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "investigations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id"), nullable=False),
        sa.Column(
            "execution_id", sa.String(128), sa.ForeignKey("observed_executions.id"), nullable=False
        ),
        sa.Column("active_incident_id", sa.Integer(), sa.ForeignKey("incidents.id"), unique=True),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("stage", sa.String(32)),
        sa.Column("trigger", sa.String(16), nullable=False),
        sa.Column("model", sa.String(128), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("evidence", sa.JSON()),
        sa.Column("policy", sa.JSON()),
        sa.Column("error", sa.String(512)),
    )
    op.create_index("ix_investigations_incident_id", "investigations", ["incident_id"])
    op.create_table(
        "agent_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "investigation_id", sa.Integer(), sa.ForeignKey("investigations.id"), nullable=False
        ),
        sa.Column("stage", sa.String(32), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("output", sa.JSON()),
    )
    op.create_index("ix_agent_runs_investigation_id", "agent_runs", ["investigation_id"])


def downgrade():
    op.drop_table("agent_runs")
    op.drop_table("investigations")
