from __future__ import annotations
import os, httpx, time, re
from typing import Dict, Any, List, Optional
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from datetime import datetime, timedelta, timezone

API_KEY = os.getenv("POLYGON_API_KEY", "")
BASE = "https://api.polygon.io"

_CACHE: Dict[str, Dict[str, Any]] = {}
def _cache_get(key: str, ttl: int): 
    item=_CACHE.get(key); 
    return (None if not item or time.time()-item["t"]>ttl else item["v"])
def _cache_put(key: str, val: Dict[str, Any]): _CACHE[key]={"t":time.time(),"v":val}

def _p(extra=None): d={"apiKey":API_KEY}; d.update(extra or {}); return d
def _ensure_api_key(u: str) -> str:
    parts=urlparse(u); q=parse_qs(parts.query)
    if not q.get("apiKey"): q["apiKey"]=[API_KEY]
    return urlunparse((parts.scheme,parts.netloc,parts.path,parts.params,urlencode(q, doseq=True),parts.fragment))

# OCC helpers: SPY250915C00500000
_OCC_RE = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
def occ_parse(sym: str) -> Optional[Dict[str, Any]]:
    m=_OCC_RE.match(sym or "")
    if not m: return None
    und,yy,mm,dd,cp,strike8=m.groups()
    strike=float(int(strike8)/1000.0)
    ctype="call" if cp=="C" else "put"
    expiry=f"20{yy}-{mm}-{dd}"
    return {"underlying":und,"expiry":expiry,"type":ctype,"strike":strike}

class PolygonMarket:
    def __init__(self, timeout: float = 10.0): self.timeout=timeout

    async def _get(self, url: str, params: Dict[str, Any] | None = None, cache_ttl: int = 15) -> Dict[str, Any]:
        key=url+"?"+urlencode(params or {}, doseq=True)
        if cache_ttl:
            c=_cache_get(key, cache_ttl)
            if c is not None: return c
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            back=0.25
            for _ in range(5):
                r=await c.get(url, params=_p(params))
                if r.status_code==429 or 500<=r.status_code<600:
                    time.sleep(back); back*=2; continue
                r.raise_for_status()
                j=r.json() or {}
                if cache_ttl: _cache_put(key,j)
                return j
            r.raise_for_status(); return r.json() or {}

    # ... keep your last_trade/minute/daily methods as-is ...

    def _opt_symbol(self, r: Dict[str, Any], underlying: str) -> Optional[str]:
        sym = (r.get("ticker")
               or (r.get("options") or {}).get("symbol")
               or (r.get("details") or {}).get("symbol")
               or (r.get("details") or {}).get("option_symbol")
               or (r.get("contract") or {}).get("symbol"))
        return sym

    async def snapshot_option_chain(self, underlying: str, limit: int = 250, max_pages: int = 6) -> Dict[str, Any]:
        per=min(max(1,limit),250)
        url=f"{BASE}/v3/snapshot/options/{underlying.upper()}"
        params={"limit":per}; nxt=None; out=[]
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            for _ in range(max_pages):
                r=await c.get(_ensure_api_key(nxt) if nxt else url, params=None if nxt else _p(params))
                r.raise_for_status()
                j=r.json() or {}
                for x in (j.get("results") or []):
                    sym=self._opt_symbol(x, underlying)
                    if not sym:
                        # try to build from fields
                        meta=x.get("options") or {}; det=x.get("details") or {}
                        exp=meta.get("expiration_date") or det.get("expiration_date")
                        ctype=meta.get("contract_type") or det.get("contract_type")
                        strike=meta.get("strike_price") or det.get("strike_price")
                        # fallback makes occ if possible
                        if exp and ctype and strike is not None:
                            yy=exp[2:4]; sym=f"{underlying.upper()}{yy}{exp[5:7]}{exp[8:10]}{'C' if ctype=='call' else 'P'}{int(round(float(strike)*1000)):08d}"
                    # attach normalized symbol + parsed fields
                    if sym:
                        x.setdefault("options", {})["symbol"]=sym
                        parsed=occ_parse(sym)
                        if parsed:
                            x["_occ"]=parsed  # {expiry,type,strike}
                out.extend(j.get("results") or [])
                nxt=j.get("next_url")
                if not nxt: break
        return {"results": out}
