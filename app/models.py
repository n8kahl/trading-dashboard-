import datetime as dt

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(20), index=True)
    timeframe: Mapped[str] = mapped_column(String(16), default="day")
    condition_type: Mapped[str] = mapped_column(String(32))  # price_above, price_below
    value: Mapped[float] = mapped_column(Float)
    minutes: Mapped[int] = mapped_column(Integer, default=0)
    threshold_pct: Mapped[float] = mapped_column(Float, default=0.0)
    expires_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class AlertTrigger(Base):
    __tablename__ = "alert_triggers"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, ForeignKey("alerts.id", ondelete="CASCADE"))
    symbol: Mapped[str] = mapped_column(String(20))
    price: Mapped[float] = mapped_column(Float)
    triggered_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
