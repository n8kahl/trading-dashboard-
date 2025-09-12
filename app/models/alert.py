from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text

from .base import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(32), index=True, nullable=False)
    timeframe = Column(String(16), nullable=False)  # 'minute','day', etc.
    condition = Column(Text, nullable=False)  # JSON string (type/value/etc)
    expires_at = Column(DateTime, nullable=True)

    # IMPORTANT: the DB column is named is_active (not active)
    is_active = Column("is_active", Boolean, default=True, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    triggered_at = Column(DateTime, nullable=True)
