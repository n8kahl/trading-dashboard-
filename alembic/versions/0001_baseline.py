"""baseline

Revision ID: 0001_baseline
Revises: 
Create Date: 2025-09-14

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "narratives",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("t_ms", sa.BigInteger(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("horizon", sa.String(length=16), nullable=True),
        sa.Column("band", sa.String(length=16), nullable=True),
        sa.Column("guidance_json", sa.JSON(), nullable=True),
        sa.Column("position_id", sa.String(length=64), nullable=True, index=True),
    )
    op.create_table(
        "playbook_entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("t_ms", sa.BigInteger(), nullable=False, index=True),
        sa.Column("symbol", sa.String(length=16), nullable=False, index=True),
        sa.Column("horizon", sa.String(length=16), nullable=True),
        sa.Column("plan", sa.JSON(), nullable=True),
        sa.Column("why", sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("playbook_entries")
    op.drop_table("narratives")

