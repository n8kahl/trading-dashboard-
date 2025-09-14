from __future__ import annotations
import os, httpx

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

class PolygonClient:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def last_trade(self, symbol: str) -> dict:
        url = f"{BASE}/v2/last/trade/{symbol.upper()}"
        params = {"apiKey": API_KEY}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            j = r.json() or {}
        res = j.get("results") or {}
        return {
            "symbol": symbol.upper(),
            "price": res.get("p"),
            "t": res.get("t"),
            "exchange": res.get("x")
        }

    # Leave NBBO (may 403 for stocks; fine if unused)
    async def last_quote(self, symbol: str) -> dict:
        url = f"{BASE}/v2/last/nbbo/{symbol.upper()}"
        params = {"apiKey": API_KEY}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            j = r.json() or {}
        res = j.get("results") or {}
        return {"symbol": symbol.upper(), "bid": res.get("bP"), "ask": res.get("aP"), "t": res.get("t")}

    # Simple placeholder for options chain; wire real endpoint later
    async def options_chain_light(self, symbol: str, expiry: str | None = None) -> dict:
        return {"symbol": symbol.upper(), "expiry": expiry, "items": []}
