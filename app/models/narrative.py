import sqlalchemy as sa

from .base import Base


class Narrative(Base):
    __tablename__ = "narratives"

    id = sa.Column(sa.Integer, primary_key=True)
    t_ms = sa.Column(sa.BigInteger, index=True, nullable=False)
    symbol = sa.Column(sa.String(16), index=True, nullable=False)
    horizon = sa.Column(sa.String(16))
    band = sa.Column(sa.String(16))
    guidance_json = sa.Column(sa.JSON)
    position_id = sa.Column(sa.String(64), index=True, nullable=True)

