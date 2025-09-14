from __future__ import annotations
import os, httpx, time
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

# --- tiny cache ---
_CACHE: Dict[str, Dict[str, Any]] = {}
def _cache_get(key: str, ttl: int) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(key)
    if not item: return None
    if time.time() - item["t"] > ttl:
        _CACHE.pop(key, None); return None
    return item["v"]
def _cache_put(key: str, value: Dict[str, Any]):
    _CACHE[key] = {"t": time.time(), "v": value}

def _p(extra=None):
    d = {"apiKey": API_KEY}
    if extra: d.update(extra)
    return d

def _ensure_api_key(u: str) -> str:
    parts = urlparse(u)
    q = parse_qs(parts.query)
    if "apiKey" not in q or not q["apiKey"]:
        q["apiKey"] = [API_KEY]
        new_query = urlencode(q, doseq=True)
        u = urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_query, parts.fragment))
    return u

def _occ_symbol(underlying: str, expiry_iso: Optional[str], ctype: Optional[str], strike: Optional[float]) -> Optional[str]:
    try:
        if not (underlying and expiry_iso and ctype and strike is not None):
            return None
        # expiry like "2025-09-15" -> YYMMDD
        y,m,d = expiry_iso.split("-")
        y2 = y[-2:]
        mmdd = f"{m}{d}"
        # type
        cp = "C" if str(ctype).lower() == "call" else "P"
        # strike * 1000, 8 digits zero-padded
        strike1000 = int(round(float(strike) * 1000))
        strike_str = f"{strike1000:08d}"
        return f"{underlying.upper()}{y2}{mmdd}{cp}{strike_str}"
    except Exception:
        return None

class PolygonMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    async def _get(self, url: str, params: Dict[str, Any] | None = None, cache_ttl: int = 15) -> Dict[str, Any]:
        key = url + "?" + urlencode(params or {}, doseq=True)
        if cache_ttl:
            cached = _cache_get(key, cache_ttl)
            if cached is not None:
                return cached
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            backoff = 0.25
            for _ in range(5):
                r = await c.get(url, params=_p(params))
                if r.status_code == 429 or 500 <= r.status_code < 600:
                    time.sleep(backoff); backoff *= 2; continue
                r.raise_for_status()
                j = r.json() or {}
                if cache_ttl: _cache_put(key, j)
                return j
            r.raise_for_status()
            return r.json() or {}

    async def last_trade(self, symbol: str) -> Dict[str, Any]:
        try:
            j = await self._get(f"{BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}", None, cache_ttl=10)
            lt = ((j.get("ticker") or {}).get("lastTrade")) or {}
            if lt:
                return {"symbol": symbol.upper(), "price": lt.get("p"), "t": lt.get("t")}
        except Exception:
            pass
        now_ms = int(time.time()*1000)
        frm = now_ms - 15*86400_000
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
                            {"adjusted":"true","sort":"desc","limit":2}, cache_ttl=30)
        res = j.get("results") or []
        if res:
            return {"symbol": symbol.upper(), "price": res[0].get("c"), "t": res[0].get("t")}
        return {"symbol": symbol.upper(), "price": None, "t": None}

    def _utc_midnight_bounds(self, dt: Optional[datetime] = None) -> tuple[int,int]:
        now = dt or datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp()*1000), int(now.timestamp()*1000)

    async def minute_bars_for_day(self, symbol: str, day: datetime) -> List[Dict[str, Any]]:
        start_ms = int(day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp()*1000)
        end_ms   = start_ms + 86_400_000
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{start_ms}/{end_ms}",
                            {"adjusted":"true","sort":"asc","limit":50000}, cache_ttl=15)
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    async def minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        start_ms, end_ms = self._utc_midnight_bounds()
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{start_ms}/{end_ms}",
                            {"adjusted":"true","sort":"asc","limit":50000}, cache_ttl=8)
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    async def five_minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        start_ms, end_ms = self._utc_midnight_bounds()
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/5/minute/{start_ms}/{end_ms}",
                            {"adjusted":"true","sort":"asc","limit":50000}, cache_ttl=8)
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    async def five_minute_bars_prev_session(self, symbol: str, max_lookback_days: int = 10) -> List[Dict[str, Any]]:
        day = datetime.now(timezone.utc).date() - timedelta(days=1)
        for _ in range(max_lookback_days):
            bars = await self.minute_bars_for_day(symbol, datetime(day.year, day.month, day.day, tzinfo=timezone.utc))
            if bars:
                if len(bars) >= 5:
                    out, acc = [], []
                    for b in bars:
                        acc.append(b)
                        if len(acc) == 5:
                            out.append({"t": acc[-1]["t"], "o": acc[0]["o"], "h": max(x["h"] for x in acc),
                                        "l": min(x["l"] for x in acc), "c": acc[-1]["c"], "v": sum(x["v"] or 0 for x in acc)})
                            acc = []
                    if acc:
                        out.append({"t": acc[-1]["t"], "o": acc[0]["o"], "h": max(x["h"] for x in acc),
                                    "l": min(x["l"] for x in acc), "c": acc[-1]["c"], "v": sum(x["v"] or 0 for x in acc)})
                    return out
                return bars
            day = day - timedelta(days=1)
        return []

    async def daily_bars(self, symbol: str, lookback: int = 220) -> List[Dict[str, Any]]:
        now_ms = int(time.time()*1000)
        frm = now_ms - max(lookback, 220)*86400_000
        j = await self._get(f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
                            {"adjusted":"true","sort":"asc","limit":1000}, cache_ttl=30)
        return [{"t":b.get("t"),"o":b.get("o"),"h":b.get("h"),"l":b.get("l"),"c":b.get("c"),"v":b.get("v")}
                for b in (j.get("results") or [])]

    def _opt_symbol(self, r: Dict[str, Any], underlying: str) -> Optional[str]:
        # Try multiple locations
        sym = (r.get("ticker")
               or (r.get("options") or {}).get("symbol")
               or (r.get("details") or {}).get("symbol")
               or (r.get("details") or {}).get("option_symbol")
               or (r.get("contract") or {}).get("symbol"))
        if sym: return sym
        # Compose OCC symbol fall-back
        meta = r.get("options") or {}
        details = r.get("details") or {}
        expiry = meta.get("expiration_date") or details.get("expiration_date")
        ctype  = meta.get("contract_type") or details.get("contract_type")
        strike = meta.get("strike_price") or details.get("strike_price")
        return _occ_symbol(underlying, expiry, ctype, strike)

    async def snapshot_option_chain(self, underlying: str, limit: int = 250, max_pages: int = 6) -> Dict[str, Any]:
        per_page = min(max(1, limit), 250)
        url = f"{BASE}/v3/snapshot/options/{underlying.upper()}"
        all_results: List[Dict[str, Any]] = []
        params = {"limit": per_page}
        page_count = 0
        next_url: Optional[str] = None

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            while page_count < max_pages:
                if next_url:
                    r = await c.get(_ensure_api_key(next_url))
                else:
                    r = await c.get(url, params=_p(params))
                r.raise_for_status()
                j = r.json() or {}
                results = j.get("results") or []
                for x in results:
                    sym = self._opt_symbol(x, underlying)
                    if sym:
                        x.setdefault("options", {})["symbol"] = sym
                all_results.extend(results)
                next_url = j.get("next_url")
                page_count += 1
                if not next_url:
                    break

        return {"results": all_results}
