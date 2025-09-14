from __future__ import annotations
import os, httpx, time
from typing import Dict, Any, List

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

def _params(extra: Dict[str, Any] | None=None):
    p = {"apiKey": API_KEY}
    if extra: p.update(extra)
    return p

class PolygonMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def last_trade(self, symbol: str) -> Dict[str, Any]:
        url = f"{BASE}/v2/last/trade/{symbol.upper()}"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=_params())
            r.raise_for_status()
            j = r.json() or {}
        res = j.get("results") or {}
        return {"symbol": symbol.upper(), "price": res.get("p"), "t": res.get("t")}

    async def _aggs_range(self, symbol: str, mult: int, timespan: str, frm: int, to: int) -> List[Dict[str, Any]]:
        url = f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/{mult}/{timespan}/{frm}/{to}"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=_params({"adjusted":"true","sort":"asc","limit":50000}))
            r.raise_for_status()
            j = r.json() or {}
        results = j.get("results") or []
        return [{"t": b.get("t"), "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"), "v": b.get("v")} for b in results]

    async def minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = (now_ms // 86_400_000) * 86_400_000  # 00:00 UTC today
        return await self._aggs_range(symbol, 1, "minute", from_ms, now_ms)

    async def five_minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = (now_ms // 86_400_000) * 86_400_000  # 00:00 UTC today
        return await self._aggs_range(symbol, 5, "minute", from_ms, now_ms)

    async def daily_bars(self, symbol: str, lookback: int = 60) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = now_ms - lookback*86_400_000
        return await self._aggs_range(symbol, 1, "day", from_ms, now_ms)
