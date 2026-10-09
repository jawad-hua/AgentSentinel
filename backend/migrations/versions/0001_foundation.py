"""Foundation heartbeat records; no seeded operational data."""

import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "heartbeats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("workflow_id", sa.String(128), nullable=False),
        sa.Column("execution_id", sa.String(128), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("workflow_id", "execution_id"),
    )


def downgrade():
    op.drop_table("heartbeats")
