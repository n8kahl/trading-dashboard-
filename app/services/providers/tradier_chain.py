from __future__ import annotations
import os, httpx
try:
    from app.services.rate_limiter import get_tradier_limiter
    _trad_rl = get_tradier_limiter()
except Exception:
    _trad_rl = None
from typing import List, Dict, Any

ENV = (os.getenv("TRADIER_ENV") or "prod").lower()  # "prod" or "sandbox"
BASE = "https://api.tradier.com/v1" if ENV=="prod" else "https://sandbox.tradier.com/v1"

def _hdrs():
    token = os.getenv("TRADIER_ACCESS_TOKEN") or os.getenv("TRADIER_API_KEY") or ""
    auth = token or ""
    if auth and not auth.lower().startswith("bearer "):
        auth = f"Bearer {auth}"
    return {"Authorization": auth, "Accept": "application/json"}

async def options_chain(symbol: str, expiry: str, greeks: bool=True) -> List[Dict[str, Any]]:
    url = f"{BASE}/markets/options/chains"
    params = {"symbol": symbol.upper(), "expiration": expiry, "greeks": "true" if greeks else "false"}
    async with httpx.AsyncClient(timeout=12.0) as c:
        if _trad_rl is not None:
            await _trad_rl.wait(1.0)
        r = await c.get(url, headers=_hdrs(), params=params)
        r.raise_for_status()
        j = r.json() or {}
    items = ((j.get("options") or {}).get("option") or [])
    if not isinstance(items, list): items = [items]
    out: List[Dict[str, Any]] = []
    for o in items:
        g = o.get("greeks") or {}
        out.append({
            "symbol": o.get("symbol"),
            "type": o.get("option_type"),
            "strike": o.get("strike"),
            "expiry": o.get("expiration_date"),
            "bid": o.get("bid"), "ask": o.get("ask"), "last": o.get("last"),
            "delta": g.get("delta"), "gamma": g.get("gamma"), "theta": g.get("theta"),
            "iv": g.get("mid_iv") or g.get("iv"),
            "oi": o.get("open_interest"), "volume": o.get("volume")
        })
    return out
