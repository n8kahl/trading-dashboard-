"""add broker_orders audit table

Revision ID: 0002_broker_orders
Revises: 0001_baseline
Create Date: 2025-09-14

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0002_broker_orders"
down_revision = "0001_baseline"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "broker_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("limit_price", sa.Float(), nullable=True),
        sa.Column("duration", sa.String(length=8), nullable=True),
        sa.Column("bracket_stop", sa.Float(), nullable=True),
        sa.Column("bracket_target", sa.Float(), nullable=True),
        sa.Column("preview", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("request_id", sa.String(length=32), nullable=True, index=True),
        sa.Column("status", sa.String(length=32), nullable=True),
        sa.Column("broker_response", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("broker_orders")

