from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from ..db import models
from ..db.db import SessionLocal

router = APIRouter(prefix="/", tags=["trades"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class TradeIn(BaseModel):
    symbol: str
    side: str = Field(..., examples=["CALL", "PUT", "LONG", "SHORT"])
    strike: Optional[float] = None
    expiry: Optional[str] = None
    avg_entry: Optional[float] = None
    size: int = 1
    notes: Optional[str] = None
    plan_json: Optional[dict] = None
    confluence_json: Optional[dict] = None


class TradeOut(BaseModel):
    id: int
    symbol: str
    side: str
    strike: Optional[float]
    expiry: Optional[str]
    avg_entry: Optional[float]
    size: int
    status: str
    notes: Optional[str]

    class Config:
        from_attributes = True


@router.post("/trades", response_model=TradeOut)
def create_trade(t: TradeIn, db: Session = Depends(get_db)):
    obj = models.Trade(
        symbol=t.symbol,
        side=t.side,
        strike=t.strike,
        expiry=t.expiry,
        avg_entry=t.avg_entry,
        size=t.size,
        notes=t.notes,
        plan_json=t.plan_json or {},
        confluence_json=t.confluence_json or {},
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/trades", response_model=List[TradeOut])
def list_trades(db: Session = Depends(get_db)):
    return db.query(models.Trade).order_by(models.Trade.id.desc()).all()


@router.get("/trades/{trade_id}", response_model=TradeOut)
def get_trade(trade_id: int, db: Session = Depends(get_db)):
    obj = db.get(models.Trade, trade_id)
    if not obj:
        raise HTTPException(404, "not found")
    return obj
