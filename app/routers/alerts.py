from __future__ import annotations

import json
import os
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, text

router = APIRouter(prefix="/api/v1/alerts", tags=["alerts"])

ENGINE = create_engine(os.environ["DATABASE_URL"], future=True)

class AlertIn(BaseModel):
    symbol: str = Field(min_length=1)
    level: float
    note: Optional[str] = None

@router.get("/list")
def alerts_list():
    with ENGINE.begin() as conn:
        rows = conn.execute(text(
            "SELECT id, symbol, level, note, created_at "
            "FROM alerts ORDER BY created_at DESC"
        )).mappings().all()
    return {
        "status": "ok",
        "data": {"alerts": [
            {
                "id": r["id"],
                "symbol": r["symbol"],
                "level": float(r["level"]),
                "note": r["note"],
                "created_at": r["created_at"].isoformat(),
            } for r in rows
        ]}
    }

@router.post("/set")
def alerts_set(payload: AlertIn):
    # Provide defaults required by your table constraints
    condition_json = json.dumps({"type": "manual"})  # works for TEXT or JSON columns
    is_active = True

    with ENGINE.begin() as conn:
        row = conn.execute(
            text(
                "INSERT INTO alerts (symbol, level, note, condition, is_active) "
                "VALUES (:s, :l, :n, :c, :a) "
                "RETURNING id, created_at"
            ),
            {
                "s": payload.symbol,
                "l": float(payload.level),
                "n": payload.note,
                "c": condition_json,
                "a": is_active,
            },
        ).mappings().first()

    return {
        "ok": True,
        "alert": {
            "id": row["id"],
            "symbol": payload.symbol,
            "level": float(payload.level),
            "note": payload.note,
            "created_at": row["created_at"].isoformat(),
        },
    }
