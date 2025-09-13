from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.db import db_session
from app.models.settings import AppSettings


router = APIRouter(prefix="/settings", tags=["settings"])


class SettingsBody(BaseModel):
    # Risk and execution
    risk_daily_r: Optional[float] = Field(None, ge=0)
    risk_per_trade_r: Optional[float] = Field(None, ge=0)
    risk_max_concurrent: Optional[int] = Field(None, ge=0)
    rr_default: Optional[str] = Field(None, pattern=r"^\d+\s*:\s*\d+$")
    auto_execute_sandbox: Optional[bool] = None

    # Universe
    top_symbols: Optional[str] = Field(None, description="comma-separated symbols")

    # Integrations — Discord alerts
    discord_webhook_url: Optional[str] = Field(None, description="Discord webhook URL for alerts")
    discord_alerts_enabled: Optional[bool] = None
    discord_alert_types: Optional[str] = Field(None, description="comma-separated types: price_above,price_below,risk")


def _load_or_create(session) -> AppSettings:
    row = session.execute(select(AppSettings).order_by(AppSettings.id.asc())).scalars().first()
    if row:
        return row
    row = AppSettings(
        risk_daily_r=None,
        risk_per_trade_r=None,
        risk_max_concurrent=None,
        rr_default="1:5",
        auto_execute_sandbox=False,
        top_symbols=None,
        discord_webhook_url=None,
        discord_alerts_enabled=False,
        discord_alert_types=None,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


@router.get("/get")
def get_settings() -> Dict[str, Any]:
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = _load_or_create(session)
        return {
            "ok": True,
            "settings": {
                "risk_daily_r": row.risk_daily_r,
                "risk_per_trade_r": row.risk_per_trade_r,
                "risk_max_concurrent": row.risk_max_concurrent,
                "rr_default": row.rr_default,
                "auto_execute_sandbox": row.auto_execute_sandbox,
                "top_symbols": row.top_symbols,
                "discord_webhook_url": row.discord_webhook_url,
                "discord_alerts_enabled": row.discord_alerts_enabled,
                "discord_alert_types": row.discord_alert_types,
            },
        }


@router.post("/set")
def set_settings(body: SettingsBody) -> Dict[str, Any]:
    with db_session() as session:
        if session is None:
            raise HTTPException(status_code=500, detail="Database not configured")
        row = _load_or_create(session)
        for k, v in body.model_dump(exclude_unset=True).items():
            setattr(row, k, v)
        row.updated_at = datetime.utcnow()
        session.add(row)
        session.commit()
        return {"ok": True}
