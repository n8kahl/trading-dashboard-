from __future__ import annotations

import datetime as dt
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feature, LogEntry, Trade
from app.db.session import get_session
from app.schemas.storage import (
    FeatureCreate,
    FeatureEnvelope,
    FeatureListEnvelope,
    FeatureRead,
    LogCreate,
    LogEnvelope,
    LogListEnvelope,
    LogRead,
    TradeCreate,
    TradeEnvelope,
    TradeListEnvelope,
    TradeRead,
)
from app.services import discord

router = APIRouter(prefix="/api/v1", tags=["storage"])


def _coerce_symbol(sym: str | None) -> Optional[str]:
    if not sym:
        return None
    return sym.upper().strip()


@router.post("/trades", response_model=TradeEnvelope)
async def create_trade(
    body: TradeCreate,
    session: AsyncSession = Depends(get_session),
) -> TradeEnvelope:
    trade = Trade(
        symbol=_coerce_symbol(body.symbol) or body.symbol,
        side=body.side.lower(),
        trade_type=body.trade_type.lower(),
        quantity=body.quantity,
        avg_price=body.avg_price,
        pnl=body.pnl,
        tags=body.tags or [],
        context=body.context or {},
    )
    if body.executed_at is not None:
        trade.executed_at = body.executed_at
    session.add(trade)
    await session.commit()
    await session.refresh(trade)

    trade_out = TradeRead.model_validate(trade)

    discord.notify_trade(trade_out.model_dump())

    return TradeEnvelope(trade=trade_out)


@router.get("/trades", response_model=TradeListEnvelope)
async def list_trades(
    symbol: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    since: Optional[dt.datetime] = Query(default=None),
    session: AsyncSession = Depends(get_session),
) -> TradeListEnvelope:
    stmt = select(Trade).order_by(Trade.executed_at.desc()).limit(limit)
    sym = _coerce_symbol(symbol)
    if sym:
        stmt = stmt.where(Trade.symbol == sym)
    if since:
        stmt = stmt.where(Trade.executed_at >= since)

    result = await session.execute(stmt)
    trades = [TradeRead.model_validate(row) for row in result.scalars().all()]
    return TradeListEnvelope(trades=trades)


@router.get("/trades/{trade_id}", response_model=TradeEnvelope)
async def get_trade(
    trade_id: int,
    session: AsyncSession = Depends(get_session),
) -> TradeEnvelope:
    trade = await session.get(Trade, trade_id)
    if not trade:
        raise HTTPException(status_code=404, detail="Trade not found")
    trade_out = TradeRead.model_validate(trade)
    return TradeEnvelope(trade=trade_out)


@router.post("/features", response_model=FeatureEnvelope)
async def create_feature(
    body: FeatureCreate,
    session: AsyncSession = Depends(get_session),
) -> FeatureEnvelope:
    feature = Feature(
        symbol=_coerce_symbol(body.symbol) or body.symbol,
        horizon=body.horizon.lower(),
        payload=body.payload,
    )
    if body.created_at is not None:
        feature.created_at = body.created_at
    session.add(feature)
    await session.commit()
    await session.refresh(feature)

    data = FeatureRead.model_validate(feature)
    return FeatureEnvelope(feature=data)


@router.get("/features", response_model=FeatureListEnvelope)
async def list_features(
    symbol: Optional[str] = Query(default=None),
    horizon: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    session: AsyncSession = Depends(get_session),
) -> FeatureListEnvelope:
    stmt = select(Feature).order_by(Feature.created_at.desc()).limit(limit)
    sym = _coerce_symbol(symbol)
    if sym:
        stmt = stmt.where(Feature.symbol == sym)
    if horizon:
        stmt = stmt.where(Feature.horizon == horizon.lower())

    result = await session.execute(stmt)
    features = [FeatureRead.model_validate(row) for row in result.scalars().all()]
    return FeatureListEnvelope(features=features)


@router.post("/logs", response_model=LogEnvelope)
async def create_log(
    body: LogCreate,
    session: AsyncSession = Depends(get_session),
) -> LogEnvelope:
    log = LogEntry(
        level=body.level.lower(),
        source=(body.source or "").strip() or None,
        message=body.message,
        payload=body.payload or {},
    )
    if body.created_at is not None:
        log.created_at = body.created_at
    session.add(log)
    await session.commit()
    await session.refresh(log)

    data = LogRead.model_validate(log)

    if log.level in {"error", "critical"}:
        discord.notify_log(data.model_dump())

    return LogEnvelope(log=data)


@router.get("/logs", response_model=LogListEnvelope)
async def list_logs(
    level: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    since: Optional[dt.datetime] = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> LogListEnvelope:
    stmt = select(LogEntry).order_by(LogEntry.created_at.desc()).limit(limit)
    if level:
        stmt = stmt.where(LogEntry.level == level.lower())
    if source:
        stmt = stmt.where(LogEntry.source == source)
    if since:
        stmt = stmt.where(LogEntry.created_at >= since)

    result = await session.execute(stmt)
    logs = [LogRead.model_validate(row) for row in result.scalars().all()]
    return LogListEnvelope(logs=logs)
