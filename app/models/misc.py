from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


class Alert(Base):
    __tablename__ = "alerts"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    timeframe: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)  # minute/day
    condition: Mapped[Dict[str, Any]] = mapped_column(JSON)  # e.g., {"type":"price_above","value":190,...}
    expires_at: Mapped[Optional[DateTime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)


class AlertTrigger(Base):
    __tablename__ = "alert_triggers"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    alert_id: Mapped[int] = mapped_column(Integer, index=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    triggered_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default={})


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    added_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class JournalEntry(Base):
    __tablename__ = "journal_entries"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    symbol: Mapped[str] = mapped_column(String(16), index=True)
    r: Mapped[Optional[float]] = mapped_column(Float, nullable=True)  # realized R for the trade
    side: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)  # long/short
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    meta: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
