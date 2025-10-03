from __future__ import annotations

from fastapi import APIRouter, Query
from typing import Any, Dict

from app.services.setup_scanner import scan_top_setups

router = APIRouter(prefix="/api/v1/market", tags=["market"], include_in_schema=False)


@router.get("/setups")
async def market_setups(
    limit: int = Query(10, ge=3, le=30),
    include_options: bool = Query(True),
    symbols: str | None = Query(None, description="Comma-separated tickers"),
    strict: bool = Query(True),
    min_confidence: int = Query(70, ge=0, le=100),
) -> Dict[str, Any]:
    sym_list = None
    if symbols:
        sym_list = [s.strip().upper() for s in symbols.split(',') if s.strip()]
    setups = await scan_top_setups(
        limit=limit,
        include_options=include_options,
        symbols=sym_list,
        strict=strict,
        min_confidence=min_confidence,
    )
    return {"ok": True, "count": len(setups), "setups": setups}
