"""alert_events table

Revision ID: 8fca11fbe235
Revises: 3a63aa63e188
Create Date: 2025-09-12 21:04:55.844099

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '8fca11fbe235'
down_revision: Union[str, None] = '3a63aa63e188'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



from alembic import op
import sqlalchemy as sa

def upgrade() -> None:
    op.create_table(
        "alert_events",
        sa.Column("id", sa.BigInteger, primary_key=True),
        sa.Column("alert_id", sa.BigInteger, nullable=False),
        sa.Column("symbol", sa.Text, nullable=False),
        sa.Column("price", sa.Numeric(12,4), nullable=False),
        sa.Column("trigger", sa.Text, nullable=False), # e.g., 'cross_up', 'cross_down'
        sa.Column("triggered_at", sa.TIMESTAMP(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("note", sa.Text, nullable=True),
    )
    op.create_index("idx_alert_events_symbol_ts", "alert_events", ["symbol","triggered_at"])
    op.create_foreign_key(None, "alert_events", "alerts", ["alert_id"], ["id"])

def downgrade() -> None:
    op.drop_table("alert_events")
