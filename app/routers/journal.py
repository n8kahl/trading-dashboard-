from __future__ import annotations
from fastapi import APIRouter, Depends
from typing import Optional, Dict, Any
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from app.services.db import get_db
from app.models import JournalEntry

router = APIRouter(prefix="/journal", tags=["journal"])

@router.get("/health")
def health(): return {"ok": True, "router": "journal"}

class JournalReq(BaseModel):
    symbol: str
    r: Optional[float] = None
    side: Optional[str] = None
    notes: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None

@router.post("/trade")
def journal_trade(req: JournalReq, db: Session = Depends(get_db)):
    row = JournalEntry(symbol=req.symbol.upper(), r=req.r, side=req.side, notes=req.notes, meta=req.meta)
    db.add(row); db.commit()
    return {"ok": True, "id": row.id}

@router.get("/summary")
def journal_summary(db: Session = Depends(get_db)):
    tot = db.execute(select(func.count()).select_from(JournalEntry)).scalar_one()
    win = db.execute(select(func.count()).select_from(JournalEntry).where(JournalEntry.r != None).where(JournalEntry.r > 0)).scalar_one()
    rsum = db.execute(select(func.coalesce(func.sum(JournalEntry.r), 0.0))).scalar_one()
    win_rate = (win / tot) if tot else None
    return {"ok": True, "summary": {"trades": tot, "win_rate": win_rate, "total_R": rsum}}
