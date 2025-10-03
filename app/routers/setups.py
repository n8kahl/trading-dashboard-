from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Any, Dict

from app.services.setup_scanner import scan_top_setups

router = APIRouter(prefix="/api/v1/market", tags=["market"], include_in_schema=False)


@router.get("/setups")
async def market_setups(limit: int = Query(10, ge=3, le=30), include_options: bool = Query(True)) -> Dict[str, Any]:
    setups = await scan_top_setups(limit=limit, include_options=include_options)
    return {"ok": True, "count": len(setups), "setups": setups}
