from __future__ import annotations
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, JSON

class Base(DeclarativeBase):
    pass

class PaperTrade(Base):
    __tablename__ = "paper_trades"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    side: Mapped[str] = mapped_column(String(4))  # buy/sell
    qty: Mapped[int] = mapped_column(Integer)
    entry_px: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    exit_px: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    open_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    close_time: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    session: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # open/mid/power
    strategy_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    expected_r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    slippage_bps: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fees: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    outcome_r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

class PaperPosition(Base):
    __tablename__ = "paper_positions"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    qty: Mapped[int] = mapped_column(Integer)
    avg_px: Mapped[float] = mapped_column(Float)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class PaperFill(Base):
    __tablename__ = "paper_fills"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    trade_id: Mapped[int] = mapped_column(Integer, index=True)
    px: Mapped[float] = mapped_column(Float)
    qty: Mapped[int] = mapped_column(Integer)
    time: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    liquidity_bucket: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # open/mid/power
    spread_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
