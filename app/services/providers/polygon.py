from __future__ import annotations
import os, httpx

BASE = "https://api.polygon.io"
API_KEY = os.getenv("POLYGON_API_KEY", "")

class PolygonClient:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def last_quote(self, symbol: str) -> dict:
        url = f"{BASE}/v2/last/nbbo/{symbol.upper()}"
        params = {"apiKey": API_KEY}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            j = r.json() or {}
        res = j.get("results") or {}
        return {"symbol": symbol.upper(), "bid": res.get("bP"), "ask": res.get("aP"), "t": res.get("t")}

    async def snapshot_stock(self, symbol: str) -> dict:
        url = f"{BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}"
        params = {"apiKey": API_KEY}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=params)
            r.raise_for_status()
            j = r.json() or {}
        t = j.get("ticker") or {}
        day = t.get("day") or {}
        minute = t.get("min") or {}
        price = (minute.get("c") if minute else None) or day.get("c")
        return {"symbol": symbol.upper(), "price": price, "day": day, "min": minute}

    async def options_chain_light(self, symbol: str, expiry: str | None = None) -> dict:
        return {"symbol": symbol.upper(), "expiry": expiry, "items": []}
