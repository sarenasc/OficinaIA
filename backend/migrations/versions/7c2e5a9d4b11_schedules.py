"""Schedules: time triggers that start an agent's task"""

import sqlalchemy as sa
from alembic import op

revision = "7c2e5a9d4b11"
down_revision = "1619219d3efa"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "schedules",
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("office_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("request", sa.Text(), nullable=False),
        sa.Column("procedure_id", sa.String(length=36), nullable=True),
        sa.Column("inputs", sa.JSON(), nullable=False),
        sa.Column("time", sa.String(length=5), nullable=False),
        sa.Column("weekdays", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False),
        sa.Column("last_run_date", sa.String(length=10), nullable=False),
        sa.Column("last_task_id", sa.String(length=36), nullable=True),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["office_id"], ["offices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["procedure_id"], ["procedures.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade():
    op.drop_table("schedules")
