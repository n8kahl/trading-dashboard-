from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, Float, Integer, String, Text

from .base import Base


class AppSettings(Base):
    __tablename__ = "app_settings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    # Risk and execution
    risk_daily_r = Column(Float, nullable=True)  # daily loss cap in R
    risk_per_trade_r = Column(Float, nullable=True)  # max R per trade
    risk_max_concurrent = Column(Integer, nullable=True)
    rr_default = Column(String(16), nullable=True)  # e.g., "1:5"
    auto_execute_sandbox = Column(Boolean, default=False)

    # Universe
    top_symbols = Column(Text, nullable=True)  # comma-separated list, if provided

    # Integrations — Discord alerts
    discord_webhook_url = Column(Text, nullable=True)
    discord_alerts_enabled = Column(Boolean, default=False)
    # comma-separated types: e.g., "price_above,price_below,risk"
    discord_alert_types = Column(Text, nullable=True)

    # Audit
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
