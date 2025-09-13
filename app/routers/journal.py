from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import and_, desc, select

from app.db import db_session
from app.models.misc import JournalEntry


router = APIRouter(prefix="/journal", tags=["journal"])


class JournalCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    r: Optional[float] = None
    side: Optional[str] = Field(None, pattern=r"^(long|short|CALL|PUT)$", description="long/short or CALL/PUT")
    notes: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


class JournalUpdate(BaseModel):
    r: Optional[float] = None
    side: Optional[str] = Field(None, pattern=r"^(long|short|CALL|PUT)$")
    notes: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None


@router.get("/list")
def list_entries(
    symbol: Optional[str] = Query(None),
    since: Optional[str] = Query(None, description="ISO timestamp"),
    limit: int = Query(100, ge=1, le=500),
):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        stmt = select(JournalEntry)
        if symbol:
            stmt = stmt.where(JournalEntry.symbol == symbol.upper())
        if since:
            try:
                ts = datetime.fromisoformat(since.replace("Z", "+00:00"))
                stmt = stmt.where(JournalEntry.created_at >= ts)
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid since timestamp")
        stmt = stmt.order_by(desc(JournalEntry.created_at)).limit(limit)
        rows = session.execute(stmt).scalars().all()
        items = [
            {
                "id": r.id,
                "symbol": r.symbol,
                "r": r.r,
                "side": r.side,
                "notes": r.notes,
                "meta": r.meta,
                "created_at": r.created_at.isoformat(),
            }
            for r in rows
        ]
        return {"ok": True, "items": items}


@router.post("/create")
def create_entry(body: JournalCreate):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = JournalEntry(
            symbol=body.symbol.upper(),
            r=body.r,
            side=body.side,
            notes=body.notes,
            meta=body.meta,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"ok": True, "id": row.id}


@router.post("/update/{entry_id}")
def update_entry(entry_id: int, body: JournalUpdate):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = session.get(JournalEntry, entry_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        session.add(row)
        session.commit()
        return {"ok": True}


@router.post("/delete/{entry_id}")
def delete_entry(entry_id: int):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = session.get(JournalEntry, entry_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        session.delete(row)
        session.commit()
        return {"ok": True}

