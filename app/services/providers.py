import os, asyncio, datetime as dt
from typing import Any, Dict, List, Optional, Tuple
import httpx
from app.integrations.tradier import TradierClient

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com")
TRADIER_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")
POLYGON_KEY = os.getenv("POLYGON_API_KEY")
APP_TZ = os.getenv("APP_TIMEZONE", "America/Chicago")

_http_timeout = httpx.Timeout(20.0, connect=10.0)
_headers_tradier = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json"} if TRADIER_TOKEN else {}

_tradier_client: Optional[TradierClient] = None


def _tradier(client: Optional[TradierClient] = None) -> TradierClient:
    """Return a Tradier client, optionally using the provided one."""
    global _tradier_client
    if client is not None:
        return client
    if _tradier_client is None:
        _tradier_client = TradierClient()
    return _tradier_client


async def close_tradier_client() -> None:
    """Close the module-level Tradier client, if any."""
    global _tradier_client
    if _tradier_client is not None:
        await _tradier_client.close()
        _tradier_client = None

async def _aget_json(url: str, headers: Dict[str,str] = None, params: Dict[str,Any] = None, method: str="GET", data: Any=None) -> Tuple[int, Any]:
    async with httpx.AsyncClient(timeout=_http_timeout) as client:
        if method == "GET":
            r = await client.get(url, headers=headers, params=params)
        else:
            r = await client.post(url, headers=headers, json=data)
    try:
        return r.status_code, r.json()
    except Exception:
        return r.status_code, {"raw": r.text}

# ----- Quotes (prefer Tradier; fallback Polygon daily close) -----
async def get_last_price(symbol: str, client: Optional[TradierClient] = None) -> Optional[float]:
    # Tradier real/15-min delayed last
    if TRADIER_TOKEN:
        quotes = await _tradier(client).get_quotes([symbol])
        q = quotes.get(symbol) or {}
        last = q.get("last") or q.get("close") or q.get("bid") or q.get("ask")
        if isinstance(last, (int, float)):
            return float(last)
    # Polygon daily fallback (yesterday/most recent)
    if POLYGON_KEY:
        today = dt.date.today().isoformat()
        code, js = await _aget_json(f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/1/day/2020-01-01/{today}",
                                    params={"adjusted":"true","sort":"desc","limit":"1","apiKey":POLYGON_KEY})
        res = (js or {}).get("results") or []
        if res:
            return float(res[0].get("c"))
    return None

# ----- Tradier option expirations & chains -----
async def get_tradier_expirations(symbol: str) -> List[str]:
    if not _headers_tradier:
        return []
    code, js = await _aget_json(f"{TRADIER_BASE}/v1/markets/options/expirations",
                                headers=_headers_tradier, params={"symbol": symbol, "includeAllRoots":"true"})
    exps = (((js or {}).get("expirations") or {}).get("date") or [])
    # Can be string or list of strings depending on count
    if isinstance(exps, str): return [exps]
    return [e for e in exps if isinstance(e, str)]

def _parse_date(s: str) -> dt.date:
    return dt.datetime.strptime(s, "%Y-%m-%d").date()

async def get_tradier_chain_by_exp(symbol: str, expiration: str, opt_type: str) -> List[Dict[str,Any]]:
    if not _headers_tradier:
        return []
    params = {"symbol": symbol, "expiration": expiration, "greeks":"true"}
    code, js = await _aget_json(f"{TRADIER_BASE}/v1/markets/options/chains", headers=_headers_tradier, params=params)
    opts = (((js or {}).get("options") or {}).get("option") or [])
    # Normalize list
    if isinstance(opts, dict): opts = [opts]
    side = "call" if opt_type.lower()=="call" else "put"
    out = []
    for o in opts:
        if (o.get("option_type") or "").lower() != side: continue
        bid = o.get("bid"); ask = o.get("ask")
        spread_pct = None
        if isinstance(bid,(int,float)) and isinstance(ask,(int,float)) and ask>0:
            spread_pct = max(0.0, (ask - bid)/ask)
        out.append({
            "symbol": o.get("symbol"),
            "strike": o.get("strike"),
            "bid": bid, "ask": ask, "last": o.get("last"),
            "open_interest": o.get("open_interest"),
            "volume": o.get("volume"),
            "expiration": o.get("expiration_date") or expiration,
            "spread_pct": spread_pct,
            "description": o.get("description"),
        })
    return out

# DTE helper
def compute_dte(expiration: str, ref_date: Optional[dt.date]=None) -> int:
    ref = ref_date or dt.date.today()
    try:
        return max(0, (_parse_date(expiration) - ref).days)
    except Exception:
        return 0
