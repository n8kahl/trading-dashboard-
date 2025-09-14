from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/market", tags=["market"])

POLYGON_API_KEY = (os.getenv("POLYGON_API_KEY") or "").strip()
POLYGON_BASE = "https://api.polygon.io"


@router.get("/bars")
async def get_bars(symbol: str = Query(..., min_length=1), tf: str = Query("1m")) -> Dict[str, Any]:
    """Return recent OHLCV bars for a symbol.

    Query params:
      - symbol: ticker symbol
      - tf: timeframe: "1m" or "5m" or "day"
    """
    if not POLYGON_API_KEY:
        raise HTTPException(status_code=500, detail="POLYGON_API_KEY not configured")
    tf = (tf or "1m").lower()
    if tf not in {"1m", "5m", "day"}:
        raise HTTPException(status_code=400, detail="invalid tf (1m|5m|day)")
    timespan = "minute" if tf in {"1m", "5m"} else "day"
    mult = 1 if tf in {"1m", "day"} else 5

    # choose a reasonable lookback
    now = datetime.now(timezone.utc)
    start = now - (timedelta(days=7) if timespan == "minute" else timedelta(days=200))
    url = f"{POLYGON_BASE}/v2/aggs/ticker/{symbol.upper()}/range/{mult}/{timespan}/{start.date()}/{now.date()}"
    params = {"sort": "asc", "limit": 5000, "apiKey": POLYGON_API_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            raise HTTPException(status_code=r.status_code, detail=r.text)
        data = r.json() or {}
        items: List[Dict[str, Any]] = []
        for b in (data.get("results") or []):
            items.append({
                "t": b.get("t"),
                "o": b.get("o"),
                "h": b.get("h"),
                "l": b.get("l"),
                "c": b.get("c"),
                "v": b.get("v"),
            })
        return {"ok": True, "symbol": symbol.upper(), "tf": tf, "items": items[-500:]}

