from __future__ import annotations

import datetime as dt
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class TradeCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    side: str = Field(..., min_length=3, max_length=16)
    quantity: int = Field(..., gt=0)
    trade_type: str = Field(default="equity", max_length=16)
    avg_price: Optional[float] = None
    pnl: Optional[float] = None
    executed_at: Optional[dt.datetime] = None
    tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class TradeRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    executed_at: dt.datetime
    symbol: str
    side: str
    trade_type: str
    quantity: int
    avg_price: Optional[float] = None
    pnl: Optional[float] = None
    tags: Optional[List[str]] = None
    context: Optional[Dict[str, Any]] = None


class TradeEnvelope(BaseModel):
    ok: bool = True
    trade: TradeRead


class TradeListEnvelope(BaseModel):
    ok: bool = True
    trades: List[TradeRead]


class FeatureCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=32)
    horizon: str = Field(..., min_length=1, max_length=32)
    created_at: Optional[dt.datetime] = None
    payload: Dict[str, Any]


class FeatureRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime
    symbol: str
    horizon: str
    payload: Dict[str, Any]


class FeatureEnvelope(BaseModel):
    ok: bool = True
    feature: FeatureRead


class FeatureListEnvelope(BaseModel):
    ok: bool = True
    features: List[FeatureRead]


class LogCreate(BaseModel):
    level: str = Field(..., min_length=3, max_length=16)
    source: Optional[str] = Field(default=None, max_length=64)
    message: str = Field(..., min_length=1, max_length=512)
    payload: Optional[Dict[str, Any]] = None
    created_at: Optional[dt.datetime] = None


class LogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: dt.datetime
    level: str
    source: Optional[str]
    message: str
    payload: Optional[Dict[str, Any]] = None


class LogEnvelope(BaseModel):
    ok: bool = True
    log: LogRead


class LogListEnvelope(BaseModel):
    ok: bool = True
    logs: List[LogRead]
