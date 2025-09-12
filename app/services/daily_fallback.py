from __future__ import annotations
from typing import Dict, Any, List, Optional
import httpx, os, datetime as dt

# --- Tradier daily history ---
TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com")
TRADIER_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")

async def tradier_daily_close(symbol: str) -> Optional[float]:
    if not TRADIER_TOKEN:
        return None
    url = f"{TRADIER_BASE}/v1/markets/history"
    params = {"symbol": symbol.upper()}
    hdrs = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params=params, headers=hdrs)
        if r.status_code != 200:
            return None
        js = r.json()
        bars = (((js or {}).get("history") or {}).get("day")) or []
        if isinstance(bars, dict):  # single day
            bars = [bars]
        if not bars:
            return None
        return float(bars[-1].get("close"))

# --- Polygon daily fallback ---
POLY_KEY = os.getenv("POLYGON_API_KEY")

async def polygon_daily_close(symbol: str) -> Optional[float]:
    if not POLY_KEY:
        return None
    end = dt.date.today()
    start = end - dt.timedelta(days=10)
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}?adjusted=true&sort=asc&limit=50000&apiKey={POLY_KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return None
        js = r.json()
        res = js.get("results") or []
        if not res:
            return None
        return float(res[-1].get("c"))

async def daily_price(symbol: str) -> Dict[str, Any]:
    p = await tradier_daily_close(symbol)
    if p is not None:
        return {"ok": True, "price": p, "provider": "tradier"}
    p = await polygon_daily_close(symbol)
    if p is not None:
        return {"ok": True, "price": p, "provider": "polygon"}
    return {"ok": False, "error": "daily_unavailable"}
