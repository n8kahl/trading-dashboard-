from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from sqlalchemy import DateTime, Float, Integer, JSON, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Declarative base for all ORM models."""


class Trade(Base):
    __tablename__ = "trades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    executed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(16))
    trade_type: Mapped[str] = mapped_column(String(16), default="equity")
    quantity: Mapped[int] = mapped_column(Integer)
    avg_price: Mapped[Optional[float]] = mapped_column(Float)
    pnl: Mapped[Optional[float]] = mapped_column(Float)
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, default=list)
    context: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)


class Feature(Base):
    __tablename__ = "features"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    horizon: Mapped[str] = mapped_column(String(32), index=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON)


class LogEntry(Base):
    __tablename__ = "logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )
    level: Mapped[str] = mapped_column(String(16), index=True)
    source: Mapped[Optional[str]] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(String(512))
    payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, default=dict)
