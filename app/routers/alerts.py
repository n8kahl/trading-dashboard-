from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import desc, select

from app.db import db_session
from app.models.misc import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertBody(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=16)
    timeframe: Optional[str] = Field("day", pattern=r"^(minute|day)$")
    condition: Dict[str, Any] = Field(..., description="e.g., {type:'price_above', value:123.45, threshold_pct?:0.2}")
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = True


class AlertUpdate(BaseModel):
    timeframe: Optional[str] = Field(None, pattern=r"^(minute|day)$")
    condition: Optional[Dict[str, Any]] = None
    expires_at: Optional[datetime] = None
    is_active: Optional[bool] = None


@router.get("/list")
def alerts_list():
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        stmt = select(Alert).order_by(desc(Alert.id)).limit(200)
        rows = session.execute(stmt).scalars().all()
        items = [
            {
                "id": r.id,
                "symbol": r.symbol,
                "timeframe": r.timeframe,
                "condition": r.condition,
                "expires_at": r.expires_at.isoformat() if r.expires_at else None,
                "is_active": bool(r.is_active),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
        return {"ok": True, "items": items}


@router.post("/set")
def alerts_set(body: AlertBody):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = Alert(
            symbol=body.symbol.upper(),
            timeframe=body.timeframe or "day",
            condition=body.condition,
            expires_at=body.expires_at,
            is_active=bool(body.is_active) if body.is_active is not None else True,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return {"ok": True, "id": row.id}


@router.post("/delete/{alert_id}")
def alerts_delete(alert_id: int):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = session.get(Alert, alert_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        session.delete(row)
        session.commit()
        return {"ok": True}


@router.post("/update/{alert_id}")
def alerts_update(alert_id: int, body: AlertUpdate):
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = session.get(Alert, alert_id)
        if not row:
            raise HTTPException(status_code=404, detail="Not found")
        data = body.model_dump(exclude_unset=True)
        if "timeframe" in data and data["timeframe"] is not None:
            row.timeframe = data["timeframe"]
        if "condition" in data and data["condition"] is not None:
            row.condition = data["condition"]
        if "expires_at" in data:
            row.expires_at = data["expires_at"]
        if "is_active" in data and data["is_active"] is not None:
            row.is_active = bool(data["is_active"])  # explicit cast
        session.add(row)
        session.commit()
        return {"ok": True}
