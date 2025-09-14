from __future__ import annotations
import os, httpx, time, math
from typing import Dict, Any, List, Optional

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

def _p(extra=None):
    d = {"apiKey": API_KEY}
    if extra: d.update(extra)
    return d

class PolygonMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def _get(self, url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, params=_p(params))
            r.raise_for_status()
            return r.json() or {}

    # -------- Underlying last-trade (kept as fallback; you now use Tradier for price) --------
    async def last_trade(self, symbol: str) -> Dict[str, Any]:
        try:
            j = await self._get(f"{BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}")
            lt = ((j.get("ticker") or {}).get("lastTrade")) or {}
            if lt:
                return {"symbol": symbol.upper(), "price": lt.get("p"), "t": lt.get("t")}
        except Exception:
            pass
        # Fallback to daily close (avoids 403 on some plans)
        now_ms = int(time.time()*1000)
        frm = now_ms - 15*86400_000
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
                            {"adjusted":"true","sort":"desc","limit":2})
        res = j.get("results") or []
        if res:
            return {"symbol": symbol.upper(), "price": res[0].get("c"), "t": res[0].get("t")}
        return {"symbol": symbol.upper(), "price": None, "t": None}

    # -------- Intraday bars (today) --------
    async def _today_bounds(self) -> tuple[int,int]:
        # UTC midnight to now
        now_ms = int(time.time()*1000)
        start_ms = (now_ms // 86_400_000) * 86_400_000
        return start_ms, now_ms

    async def minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        frm, to = await self._today_bounds()
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{frm}/{to}",
                            {"adjusted":"true","sort":"asc","limit":50000})
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    async def five_minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        frm, to = await self._today_bounds()
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/5/minute/{frm}/{to}",
                            {"adjusted":"true","sort":"asc","limit":50000})
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    async def daily_bars(self, symbol: str, lookback: int = 220) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        frm = now_ms - max(lookback, 220)*86400_000
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
                            {"adjusted":"true","sort":"asc","limit":50000})
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    # -------- Options snapshot (v3) with pagination (limit<=250) --------
    async def snapshot_option_chain(self, underlying: str, limit: int = 250, max_pages: int = 6) -> Dict[str, Any]:
        """
        Returns aggregated list across pages:
        { "results": [ ... up to (limit*max_pages) ... ] }
        """
        # Enforce Polygon page limit
        per_page = min(max(1, limit), 250)
        url = f"{BASE}/v3/snapshot/options/{underlying.upper()}"
        all_results: List[Dict[str, Any]] = []

        params = {"limit": per_page}
        page_count = 0
        next_url: Optional[str] = None

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            while page_count < max_pages:
                if next_url:
                    r = await c.get(next_url)
                else:
                    r = await c.get(url, params=_p(params))
                if r.status_code >= 400:
                    # surface body for debugging
                    raise httpx.HTTPStatusError(f"{r.status_code}: {r.text}", request=r.request, response=r)
                j = r.json() or {}
                results = j.get("results") or []
                all_results.extend(results)
                next_url = j.get("next_url")
                page_count += 1
                if not next_url:
                    break

        return {"results": all_results}
