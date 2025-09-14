import sqlalchemy as sa

from .base import Base


class PlaybookEntry(Base):
    __tablename__ = "playbook_entries"

    id = sa.Column(sa.Integer, primary_key=True)
    t_ms = sa.Column(sa.BigInteger, index=True, nullable=False)
    symbol = sa.Column(sa.String(16), index=True, nullable=False)
    horizon = sa.Column(sa.String(16))
    plan = sa.Column(sa.JSON)
    why = sa.Column(sa.JSON)

