import asyncio
import os
import time
import urllib.parse
from typing import Any, Dict, List, Optional

import httpx

from app.config import OPTIONS_CACHE_TTL_SEC

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or os.getenv("POLYGON_APIKEY") or os.getenv("POLYGON_KEY")
CHAIN_URL_TMPL = "https://api.polygon.io/v3/snapshot/options/{underlying}"

# in-memory cache: key -> (ts, data)
_CACHE: Dict[str, Any] = {}


def _now() -> float:
    return time.time()


def _cache_get(key: str) -> Optional[Any]:
    v = _CACHE.get(key)
    if not v:
        return None
    ts, data = v
    if _now() - ts > OPTIONS_CACHE_TTL_SEC:
        return None
    return data


def _cache_set(key: str, data: Any) -> None:
    _CACHE[key] = (_now(), data)


def _norm_contract(rec: Dict[str, Any]) -> Dict[str, Any]:
    details = rec.get("details") or {}
    greeks = rec.get("greeks") or {}
    last_q = rec.get("last_quote") or {}
    day = rec.get("day") or {}
    out = {
        "symbol": details.get("ticker"),
        "type": (details.get("contract_type") or "").upper(),
        "strike": details.get("strike_price"),
        "expiration": details.get("expiration_date"),
        "bid": (last_q.get("bid") or 0.0),
        "ask": (last_q.get("ask") or 0.0),
        "delta": greeks.get("delta"),
        "iv": rec.get("implied_volatility"),
        "open_interest": rec.get("open_interest") or 0,
        "volume": day.get("volume") or 0,
    }
    for k in ("strike", "bid", "ask", "delta", "iv"):
        try:
            if out[k] is not None:
                out[k] = float(out[k])
        except Exception:
            out[k] = None
    try:
        out["open_interest"] = int(out["open_interest"])
    except Exception:
        out["open_interest"] = 0
    try:
        out["volume"] = int(out["volume"])
    except Exception:
        out["volume"] = 0
    return out


async def fetch_option_chain_snapshot(
    underlying: str, contract_type: Optional[str] = None, expiration_date: Optional[str] = None, limit: int = 250
) -> List[Dict[str, Any]]:
    """
    Fetch Polygon Option Chain Snapshot for an underlying (paginated).
    Uses Authorization header so pagination (next_url) never loses auth.
    """
    if not POLYGON_API_KEY:
        raise RuntimeError("POLYGON_API_KEY missing")
    underlying = (underlying or "").upper()
    cache_key = f"chain::{underlying}::{contract_type or ''}::{expiration_date or ''}"
    cached = _cache_get(cache_key)
    if cached is not None:
        return cached

    params = {"limit": min(250, max(1, limit))}
    if contract_type:
        params["contract_type"] = contract_type.lower()
    if expiration_date:
        params["expiration_date"] = expiration_date

    url = CHAIN_URL_TMPL.format(underlying=underlying)
    out: List[Dict[str, Any]] = []
    headers = {"Authorization": f"Bearer {POLYGON_API_KEY}"}

    async with httpx.AsyncClient(timeout=20.0, headers=headers) as client:
        next_url = url
        next_params = params
        for _ in range(20):
            r = await client.get(next_url, params=next_params)
            if r.status_code == 429:
                await asyncio.sleep(0.5)
                continue
            r.raise_for_status()
            data = r.json()
            results = data.get("results") or []
            for rec in results:
                out.append(_norm_contract(rec))
            next_url = data.get("next_url")
            if not next_url:
                break
            if next_url.startswith("/"):
                next_url = urllib.parse.urljoin("https://api.polygon.io", next_url)
            next_params = None  # subsequent calls use next_url, headers keep auth

    _cache_set(cache_key, out)
    return out
