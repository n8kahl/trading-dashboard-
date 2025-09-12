import datetime as dt
from typing import Dict, Any, List, Optional
import httpx

from app.core.settings import settings


def _headers() -> Dict[str, str]:
    token = settings.TRADIER_ACCESS_TOKEN
    return {
        "Authorization": f"Bearer {token}" if token else "",
        "Accept": "application/json",
    }

async def _get(path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    base = settings.tradier_base_url or "https://sandbox.tradier.com"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(f"{base}{path}", headers=_headers(), params=params)
        r.raise_for_status()
        return r.json()

def _days_between(a: dt.date, b: dt.date) -> int:
    return (b - a).days

async def expirations(symbol: str) -> List[str]:
    js = await _get("/v1/markets/options/expirations", {"symbol": symbol, "includeAllRoots": "true", "strikes":"false"})
    exps = js.get("expirations", {}).get("date")
    if isinstance(exps, list):
        return exps
    if isinstance(exps, str):
        return [exps]
    return []

async def chains_for_exp(symbol: str, exp: str) -> List[Dict[str, Any]]:
    js = await _get("/v1/markets/options/chains", {"symbol": symbol, "expiration": exp})
    rows = js.get("options", {}).get("option")
    if isinstance(rows, list):
        return rows
    if isinstance(rows, dict):
        return [rows]
    return []

async def quotes_for_symbols(symbols: List[str]) -> Dict[str, Dict[str, Any]]:
    if not symbols:
        return {}
    sy = ",".join(symbols[:250])
    js = await _get("/v1/markets/options/quotes", {"symbols": sy, "greeks": "true"})
    q = js.get("quotes", {}).get("quote")
    out: Dict[str, Dict[str, Any]] = {}
    if isinstance(q, list):
        for row in q:
            out[row["symbol"]] = row
    elif isinstance(q, dict):
        out[q["symbol"]] = q
    return out

def tradier_batch_option_quotes(symbols: list[str]) -> dict[str, dict]:
    """
    Fetch option quotes (with greeks) from Tradier in batches using the correct endpoint:
      /v1/markets/options/quotes
    Fail-open: returns {} on any error.
    """
    out: dict[str, dict] = {}
    if not symbols:
        return out

    token = settings.TRADIER_ACCESS_TOKEN or ""
    if not token:
        return out

    import requests
    base = settings.tradier_base_url or "https://sandbox.tradier.com"
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "trading-assistant/greeks-enrichment"
    }

    CHUNK = 120  # Tradier handles large lists but we keep it safe
    for i in range(0, len(symbols), CHUNK):
        chunk = [c for c in symbols[i:i+CHUNK] if c]
        if not chunk:
            continue
        try:
            r = requests.get(
                f"{base}/v1/markets/options/quotes",
                headers=headers,
                params={"symbols": ",".join(chunk), "greeks": "true"},
                timeout=15
            )
            r.raise_for_status()
            data = r.json() or {}
            # Shape can be: {"quotes":{"quote":[{...},{...}]}} OR {"quotes":{"quote":{...}}}
            quotes = (data.get("quotes") or {}).get("quote")
            if not quotes:
                continue
            if isinstance(quotes, dict):
                quotes = [quotes]
            for q in quotes:
                sym = q.get("symbol")
                if not sym:
                    continue
                out[sym] = q  # includes "greeks": { delta, gamma, theta, vega, ... }
        except Exception:
            # fail-open: skip chunk on any error
            pass

    return out

async def get_positions() -> Dict[str, Any]:
    """Return open positions; fail-open to empty list."""
    try:
        js = await _get("/v1/accounts/positions", {})
        items = js.get("positions", {}).get("position", [])
        if isinstance(items, dict):
            items = [items]
        norm = []
        for p in items:
            norm.append({
                "symbol": p.get("symbol"),
                "qty": float(p.get("quantity", 0)),
                "avg_price": float(p.get("cost_basis", 0)),
                "side": "long" if float(p.get("quantity", 0)) >= 0 else "short",
                "market_price": float(p.get("last", 0)),
                "unrealized_r": 0.0,
            })
        return {"ok": True, "items": norm}
    except Exception as e:
        return {"ok": False, "error": str(e), "items": []}

async def get_orders(status: str = "all") -> Dict[str, Any]:
    try:
        js = await _get("/v1/accounts/orders", {"status": status})
        items = js.get("orders", {}).get("order", [])
        if isinstance(items, dict):
            items = [items]
        norm = []
        for o in items:
            norm.append({
                "id": o.get("id"),
                "symbol": o.get("symbol"),
                "side": o.get("side"),
                "qty": o.get("quantity"),
                "type": o.get("type"),
                "status": o.get("status"),
            })
        return {"ok": True, "items": norm}
    except Exception as e:
        return {"ok": False, "error": str(e), "items": []}

async def submit_order(symbol: str, side: str, qty: int, order_type: str,
                       limit_price: float | None = None, stop_price: float | None = None) -> Dict[str, Any]:
    body: Dict[str, Any] = {
        "symbol": symbol,
        "side": side,
        "quantity": qty,
        "type": order_type,
        "duration": "day",
    }
    if limit_price is not None:
        body["price"] = limit_price
    if stop_price is not None:
        body["stop"] = stop_price
    try:
        base = settings.tradier_base_url or "https://sandbox.tradier.com"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.post(f"{base}/v1/accounts/orders", headers=_headers(), data=body)
            r.raise_for_status()
            js = r.json().get("order", {})
            order = {
                "id": js.get("id"),
                "status": js.get("status"),
                "symbol": symbol,
                "side": side,
                "qty": qty,
            }
            return {"ok": True, "order": order}
    except Exception as e:
        return {"ok": False, "error": str(e)}

async def cancel_order(order_id: str) -> Dict[str, Any]:
    try:
        base = settings.tradier_base_url or "https://sandbox.tradier.com"
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.delete(f"{base}/v1/accounts/orders/{order_id}", headers=_headers())
            r.raise_for_status()
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}
