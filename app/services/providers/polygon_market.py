from __future__ import annotations
import os, time, httpx, re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

# ---------- tiny cache to avoid spamming Polygon ----------
_CACHE: Dict[str, Dict[str, Any]] = {}
def _cache_get(key: str, ttl: int) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(key)
    if not item: return None
    if time.time() - item["t"] > ttl:
        _CACHE.pop(key, None)
        return None
    return item["v"]

def _cache_put(key: str, value: Dict[str, Any]) -> None:
    _CACHE[key] = {"t": time.time(), "v": value}

def _p(extra=None) -> Dict[str, Any]:
    d = {"apiKey": API_KEY}
    if extra: d.update(extra)
    return d

def _ensure_api_key(u: str) -> str:
    parts = urlparse(u)
    q = parse_qs(parts.query)
    if "apiKey" not in q or not q["apiKey"]:
        q["apiKey"] = [API_KEY]
        new_q = urlencode(q, doseq=True)
        u = urlunparse((parts.scheme, parts.netloc, parts.path, parts.params, new_q, parts.fragment))
    return u

# ---------- OCC helpers ----------
_OCC_RE = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
def occ_parse(sym: str) -> Optional[Dict[str, Any]]:
    m = _OCC_RE.match(sym or "")
    if not m:
        return None
    und, yy, mm, dd, cp, strike8 = m.groups()
    strike = float(int(strike8)/1000.0)
    return {
        "underlying": und,
        "expiry": f"20{yy}-{mm}-{dd}",
        "type": "call" if cp == "C" else "put",
        "strike": strike
    }

class PolygonMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    # ---------- HTTP GET with retry/backoff ----------
    async def _get(self, url: str, params: Dict[str, Any] | None = None, cache_ttl: int = 10) -> Dict[str, Any]:
        key = url + "?" + urlencode(params or {}, doseq=True)
        if cache_ttl:
            cached = _cache_get(key, cache_ttl)
            if cached is not None:
                return cached
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            backoff = 0.25
            for _ in range(5):
                r = await c.get(url, params=_p(params))
                if r.status_code in (429,) or 500 <= r.status_code < 600:
                    time.sleep(backoff)
                    backoff = min(2.0, backoff * 2)
                    continue
                r.raise_for_status()
                j = r.json() or {}
                if cache_ttl:
                    _cache_put(key, j)
                return j
            r.raise_for_status()
            return r.json() or {}

    # ---------- Prices ----------
    async def last_trade(self, symbol: str) -> Dict[str, Any]:
        # Try snapshot (fast); fallback to recent daily close
        try:
            j = await self._get(f"{BASE}/v2/snapshot/locale/us/markets/stocks/tickers/{symbol.upper()}", None, cache_ttl=8)
            lt = ((j.get("ticker") or {}).get("lastTrade")) or {}
            if lt:
                return {"symbol": symbol.upper(), "price": lt.get("p"), "t": lt.get("t")}
        except Exception:
            pass
        now_ms = int(time.time() * 1000)
        frm = now_ms - 15 * 86_400_000
        j = await self._get(
            f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
            {"adjusted": "true", "sort": "desc", "limit": 2},
            cache_ttl=30,
        )
        res = j.get("results") or []
        if res:
            return {"symbol": symbol.upper(), "price": res[0].get("c"), "t": res[0].get("t")}
        return {"symbol": symbol.upper(), "price": None, "t": None}

    # ---------- Session bounds helpers ----------
    def _utc_day_bounds(self, dt: Optional[datetime] = None) -> Tuple[int, int]:
        now = dt or datetime.now(timezone.utc)
        start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        return int(start.timestamp() * 1000), int(now.timestamp() * 1000)

    async def _minute_bars_range(self, symbol: str, start_ms: int, end_ms: int, mult: int = 1) -> List[Dict[str, Any]]:
        j = await self._get(
            f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/{mult}/minute/{start_ms}/{end_ms}",
            {"adjusted": "true", "sort": "asc", "limit": 50000},
            cache_ttl=8,
        )
        return [
            {"t": b.get("t"), "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"), "v": b.get("v")}
            for b in (j.get("results") or [])
        ]

    # ---------- 1m/5m for today ----------
    async def minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        start_ms, end_ms = self._utc_day_bounds()
        return await self._minute_bars_range(symbol, start_ms, end_ms, mult=1)

    async def five_minute_bars_today(self, symbol: str) -> List[Dict[str, Any]]:
        start_ms, end_ms = self._utc_day_bounds()
        return await self._minute_bars_range(symbol, start_ms, end_ms, mult=5)

    # ---------- 1m for a specific UTC date ----------
    async def minute_bars_for_day(self, symbol: str, day: datetime) -> List[Dict[str, Any]]:
        start_ms = int(day.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc).timestamp() * 1000)
        end_ms = start_ms + 86_400_000
        return await self._minute_bars_range(symbol, start_ms, end_ms, mult=1)

    # ---------- 5m for previous trading session (aggregating 1m if needed) ----------
    async def five_minute_bars_prev_session(self, symbol: str, max_lookback_days: int = 10) -> List[Dict[str, Any]]:
        day = datetime.now(timezone.utc).date() - timedelta(days=1)
        for _ in range(max_lookback_days):
            bars_1m = await self.minute_bars_for_day(symbol, datetime(day.year, day.month, day.day, tzinfo=timezone.utc))
            if bars_1m:
                # aggregate to 5m
                out, acc = [], []
                for b in bars_1m:
                    acc.append(b)
                    if len(acc) == 5:
                        out.append({
                            "t": acc[-1]["t"],
                            "o": acc[0]["o"],
                            "h": max(x["h"] for x in acc),
                            "l": min(x["l"] for x in acc),
                            "c": acc[-1]["c"],
                            "v": sum((x["v"] or 0) for x in acc),
                        })
                        acc = []
                if acc:
                    out.append({
                        "t": acc[-1]["t"],
                        "o": acc[0]["o"],
                        "h": max(x["h"] for x in acc),
                        "l": min(x["l"] for x in acc),
                        "c": acc[-1]["c"],
                        "v": sum((x["v"] or 0) for x in acc),
                    })
                return out
            day = day - timedelta(days=1)
        return []

    # ---------- Daily bars ----------
    async def daily_bars(self, symbol: str, lookback: int = 220) -> List[Dict[str, Any]]:
        now_ms = int(time.time() * 1000)
        frm = now_ms - max(lookback, 220) * 86_400_000
        j = await self._get(
            f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{frm}/{now_ms}",
            {"adjusted": "true", "sort": "asc", "limit": 1000},
            cache_ttl=30,
        )
        return [
            {"t": b.get("t"), "o": b.get("o"), "h": b.get("h"), "l": b.get("l"), "c": b.get("c"), "v": b.get("v")}
            for b in (j.get("results") or [])
        ]

    # ---------- Options snapshot (v3) with pagination + OCC normalization ----------
    def _opt_symbol(self, r: Dict[str, Any], underlying: str) -> Optional[str]:
        sym = (r.get("ticker")
               or (r.get("options") or {}).get("symbol")
               or (r.get("details") or {}).get("symbol")
               or (r.get("details") or {}).get("option_symbol")
               or (r.get("contract") or {}).get("symbol"))
        if sym:
            return sym
        # Try to compose OCC if fields exist
        meta = r.get("options") or {}
        det = r.get("details") or {}
        exp = meta.get("expiration_date") or det.get("expiration_date")
        ctype = (meta.get("contract_type") or det.get("contract_type") or "").lower()
        strike = meta.get("strike_price") or det.get("strike_price")
        if exp and ctype and strike is not None:
            yy = exp[2:4]
            return f"{underlying.upper()}{yy}{exp[5:7]}{exp[8:10]}{'C' if ctype=='call' else 'P'}{int(round(float(strike)*1000)):08d}"
        return None

    async def snapshot_option_chain(self, underlying: str, limit: int = 250, max_pages: int = 6) -> Dict[str, Any]:
        per = min(max(1, limit), 250)
        url = f"{BASE}/v3/snapshot/options/{underlying.upper()}"
        params = {"limit": per}
        next_url: Optional[str] = None
        out: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(timeout=self.timeout) as c:
            for _ in range(max_pages):
                r = await c.get(_ensure_api_key(next_url) if next_url else url, params=None if next_url else _p(params))
                r.raise_for_status()
                j = r.json() or {}
                for x in (j.get("results") or []):
                    sym = self._opt_symbol(x, underlying)
                    if sym:
                        x.setdefault("options", {})["symbol"] = sym
                        parsed = occ_parse(sym)
                        if parsed:
                            x["_occ"] = parsed  # parsed OCC: type/strike/expiry
                out.extend(j.get("results") or [])
                next_url = j.get("next_url")
                if not next_url:
                    break

        return {"results": out}
