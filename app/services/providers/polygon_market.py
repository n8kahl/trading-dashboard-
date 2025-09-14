from __future__ import annotations
import os, httpx, time
from typing import Dict, Any, List, Optional

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

    async def _aggs_range(self, ticker: str, mult: int, timespan: str, frm: int, to: int) -> List[Dict[str, Any]]:
        url = f"{BASE}/v2/aggs/ticker/{ticker}/range/{mult}/{timespan}/{frm}/{to}"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=_params({"adjusted":"true","sort":"asc","limit":50000}))
            r.raise_for_status()
            j = r.json() or {}
        out = []
        for b in (j.get("results") or []):
            out.append({"t": b.get("t"), "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"), "v": b.get("v")})
        return out

    async def minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = (now_ms // 86_400_000) * 86_400_000
        return await self._aggs_range(symbol.upper(), 1, "minute", from_ms, now_ms)

    async def five_minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = (now_ms // 86_400_000) * 86_400_000
        return await self._aggs_range(symbol.upper(), 5, "minute", from_ms, now_ms)

    async def daily_bars(self, symbol: str, lookback: int = 220) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        from_ms = now_ms - lookback*86_400_000
        return await self._aggs_range(symbol.upper(), 1, "day", from_ms, now_ms)

    # ---------- Options Developer endpoints ----------
    async def snapshot_option_chain(self, underlying: str, limit: int = 1000) -> Dict[str, Any]:
        """/v3/snapshot/options/{underlying}"""
        url = f"{BASE}/v3/snapshot/options/{underlying.upper()}"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=_params({"limit": limit}))
            r.raise_for_status()
            return r.json() or {}

    async def option_custom_bars(self, option_ticker: str, mult: int = 1, timespan: str = "minute", lookback_minutes: int = 120) -> List[Dict[str, Any]]:
        """Custom bars for an OPTION contract (1m preferred; fallback to 5m)."""
        now_ms = int(time.time()*1000)
        from_ms = now_ms - lookback_minutes*60_000
        return await self._aggs_range(option_ticker, mult, timespan, from_ms, now_ms)
