"""Opt-in monitoring, normalized execution evidence and incident events."""

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "monitored_workflows",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("available", sa.Boolean(), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("require_output", sa.Boolean(), nullable=False),
        sa.Column("expect_json", sa.Boolean(), nullable=False),
        sa.Column("contract_node", sa.String(256)),
        sa.Column("json_field", sa.String(256)),
        sa.Column("monitor_since", sa.DateTime(timezone=True)),
        sa.Column("synced_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_polled_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.String(512)),
        sa.Column("backfill_cursor", sa.Text()),
    )
    op.create_table(
        "observed_executions",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), nullable=False
        ),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("mode", sa.String(32), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("stopped_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.Integer()),
        sa.Column("evidence_available", sa.Boolean(), nullable=False),
        sa.Column("inspected", sa.Boolean(), nullable=False),
        sa.Column("has_findings", sa.Boolean(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("inspected_at", sa.DateTime(timezone=True)),
        sa.Column("next_check_at", sa.DateTime(timezone=True)),
    )
    op.create_index("ix_observed_executions_workflow_id", "observed_executions", ["workflow_id"])
    op.create_index("ix_observed_executions_started_at", "observed_executions", ["started_at"])
    op.create_index(
        "ix_execution_baseline", "observed_executions", ["workflow_id", "mode", "started_at"]
    )
    op.create_table(
        "incidents",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "workflow_id", sa.String(128), sa.ForeignKey("monitored_workflows.id"), nullable=False
        ),
        sa.Column("fingerprint", sa.String(64), nullable=False, unique=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("node", sa.String(256)),
        sa.Column("severity", sa.String(16), nullable=False),
        sa.Column("status", sa.String(32), nullable=False),
        sa.Column("summary", sa.String(512), nullable=False),
        sa.Column(
            "first_execution_id",
            sa.String(128),
            sa.ForeignKey("observed_executions.id"),
            nullable=False,
        ),
        sa.Column(
            "last_execution_id",
            sa.String(128),
            sa.ForeignKey("observed_executions.id"),
            nullable=False,
        ),
        sa.Column("occurrences", sa.Integer(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("evidence", sa.JSON(), nullable=False),
    )
    op.create_index("ix_incidents_workflow_id", "incidents", ["workflow_id"])
    op.create_table(
        "incident_occurrences",
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id"), primary_key=True),
        sa.Column(
            "execution_id",
            sa.String(128),
            sa.ForeignKey("observed_executions.id"),
            primary_key=True,
        ),
        sa.Column("evidence", sa.JSON(), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "system_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("workflow_id", sa.String(128)),
        sa.Column("incident_id", sa.Integer(), sa.ForeignKey("incidents.id")),
        sa.Column("message", sa.String(512), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_system_events_incident_id", "system_events", ["incident_id"])


def downgrade():
    for table in [
        "system_events",
        "incident_occurrences",
        "incidents",
        "observed_executions",
        "monitored_workflows",
    ]:
        op.drop_table(table)
