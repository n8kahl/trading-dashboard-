"""add executions_seen dedupe table

Revision ID: 0003_executions_seen
Revises: 0002_broker_orders
Create Date: 2025-09-14

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0003_executions_seen"
down_revision = "0002_broker_orders"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "executions_seen",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("key", sa.String(length=200), nullable=False),
    )
    op.create_index("ix_executions_seen_key", "executions_seen", ["key"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_executions_seen_key", table_name="executions_seen")
    op.drop_table("executions_seen")

