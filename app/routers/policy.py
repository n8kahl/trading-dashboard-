from __future__ import annotations

from datetime import datetime
from typing import Any, Dict
from zoneinfo import ZoneInfo

from fastapi import APIRouter

from app.config.policy import POLICY

router = APIRouter(prefix="/policy", tags=["policy"])


@router.get("/get")
def get_policy() -> Dict[str, Any]:
    """Return active POLICY with a little context (current NY time & window status)."""
    ny = ZoneInfo("America/New_York")
    now_ny = datetime.now(ny).strftime("%Y-%m-%d %H:%M:%S %Z")
    return {"ok": True, "now_ny": now_ny, "policy": POLICY}
