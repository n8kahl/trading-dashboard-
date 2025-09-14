from __future__ import annotations

import time
from typing import Dict, Any, List, Optional, Tuple
from collections import defaultdict

_CACHE: Dict[str, Dict[str, Any]] = {}

def _key(symbol: str) -> str:
    return (symbol or "").upper()

def _cache_get(sym: str, ttl: int) -> Optional[Dict[str, Any]]:
    item = _CACHE.get(_key(sym))
    if not item:
        return None
    if (time.time() - item.get("t", 0)) > ttl:
        _CACHE.pop(_key(sym), None)
        return None
    return item

def _cache_put(sym: str, surface: Dict[str, List[float]]) -> None:
    _CACHE[_key(sym)] = {"t": time.time(), "surface": surface}

def _extract_expiry(rr: Dict[str, Any]) -> Optional[str]:
    meta = rr.get("options") or {}
    det  = rr.get("details") or {}
    return (
        rr.get("expiry") or rr.get("expiration") or rr.get("expiration_date") or
        meta.get("expiration_date") or det.get("expiration_date")
    )

def _extract_iv(rr: Dict[str, Any]) -> Optional[float]:
    g = rr.get("greeks") or {}
    iv = rr.get("iv") or rr.get("implied_volatility") or g.get("iv") or g.get("mid_iv")
    try:
        return float(iv) if iv is not None else None
    except Exception:
        return None

def _extract_strike(rr: Dict[str, Any]) -> Optional[float]:
    meta = rr.get("options") or {}
    det  = rr.get("details") or {}
    st = rr.get("strike") or meta.get("strike_price") or det.get("strike_price")
    try:
        return float(st) if st is not None else None
    except Exception:
        return None

def _mn_bucket(strike: Optional[float], last_price: Optional[float]) -> Optional[str]:
    if strike is None or last_price is None or last_price <= 0:
        return None
    m = abs((strike - last_price) / last_price)
    if m <= 0.01:
        return "atm"
    if m <= 0.03:
        return "near"
    return "far"

def build_iv_surface(rows: List[Dict[str, Any]], last_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Returns { expiry: { 'all': [iv], 'atm': [iv], 'near': [iv], 'far': [iv] } }
    If last_price is None, only 'all' is filled.
    """
    out: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: {"all": [], "atm": [], "near": [], "far": []})
    for rr in rows or []:
        exp = _extract_expiry(rr)
        iv = _extract_iv(rr)
        if not exp or iv is None:
            continue
        exp = str(exp)
        out[exp]["all"].append(iv)
        if last_price is not None:
            st = _extract_strike(rr)
            b = _mn_bucket(st, last_price)
            if b:
                out[exp][b].append(iv)
    # prune empties
    cleaned: Dict[str, Any] = {}
    for k, v in out.items():
        cleaned[k] = {bk: vals for bk, vals in v.items() if vals}
    return cleaned

async def get_iv_surface(poly, underlying: str, rows: Optional[List[Dict[str, Any]]] = None, ttl: int = 180, last_price: Optional[float] = None) -> Dict[str, Any]:
    """
    Returns { 'surface': { expiry: [iv,...], ... }, 'ts': <epoch_seconds> }.
    Uses in-memory cache by underlying for TTL seconds.
    If rows are provided, builds from rows and refreshes cache.
    """
    if rows:
        surface = build_iv_surface(rows, last_price=last_price)
        _cache_put(underlying, surface)
        return {"surface": surface, "ts": time.time(), "source": "rows"}
    cached = _cache_get(underlying, ttl)
    if cached:
        return {"surface": cached.get("surface", {}), "ts": cached.get("t"), "source": "cache"}
    # Fetch fresh snapshot from provider
    surface: Dict[str, List[float]] = {}
    try:
        if poly is not None:
            j = await poly.snapshot_option_chain(underlying)
            rows = (j or {}).get("results") or []
            surface = build_iv_surface(rows, last_price=last_price)
    except Exception:
        surface = {}
    _cache_put(underlying, surface)
    return {"surface": surface, "ts": time.time(), "source": "fetch"}

def percentile_rank(values: List[float], x: Optional[float]) -> Optional[float]:
    if x is None or not values:
        return None
    try:
        xs = sorted([float(v) for v in values if v is not None])
        if len(xs) < 5:
            return None
        # position of x within xs (right side for ties)
        import bisect
        i = bisect.bisect_right(xs, float(x))
        return round(100.0 * i / len(xs), 2)
    except Exception:
        return None
