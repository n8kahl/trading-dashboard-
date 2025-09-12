from __future__ import annotations
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Float, DateTime, JSON, Text, ForeignKey
from datetime import datetime, timezone

class Base(DeclarativeBase):
    pass

class Trade(Base):
    __tablename__ = "trades"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    side: Mapped[str] = mapped_column(String(8))           # CALL/PUT/LONG/SHORT
    strike: Mapped[float] = mapped_column(Float, nullable=True)
    expiry: Mapped[str] = mapped_column(String(16), nullable=True)  # YYYY-MM-DD
    avg_entry: Mapped[float] = mapped_column(Float, nullable=True)
    size: Mapped[int] = mapped_column(Integer, default=1)
    status: Mapped[str] = mapped_column(String(16), default="open")
    notes: Mapped[str] = mapped_column(Text, nullable=True)
    plan_json: Mapped[dict] = mapped_column(JSON, default=dict)
    confluence_json: Mapped[dict] = mapped_column(JSON, default=dict)

class ConfluenceScore(Base):
    __tablename__ = "confluence_scores"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    user_id: Mapped[str] = mapped_column(String(64), nullable=True)
    symbol: Mapped[str] = mapped_column(String(32), index=True)
    strategy_id: Mapped[str] = mapped_column(String(64))
    score_total: Mapped[int] = mapped_column(Integer)
    score_band: Mapped[str] = mapped_column(String(16))
    version: Mapped[str] = mapped_column(String(16))
    context: Mapped[dict] = mapped_column(JSON)

class ConfluenceComponent(Base):
    __tablename__ = "confluence_score_components"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    score_id: Mapped[int] = mapped_column(Integer, ForeignKey("confluence_scores.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(64))
    points: Mapped[int] = mapped_column(Integer)
    explain: Mapped[str] = mapped_column(Text)
