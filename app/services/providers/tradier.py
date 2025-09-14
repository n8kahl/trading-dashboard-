from __future__ import annotations
import os, httpx
from typing import Dict, Any

def _resolve_base() -> str:
    # Priority: explicit TRADIER_BASE, else TRADIER_ENV
    base = os.getenv("TRADIER_BASE")
    env = (os.getenv("TRADIER_ENV") or "").lower()
    if not base:
        if env == "sandbox":
            base = "https://sandbox.tradier.com"
        else:
            base = "https://api.tradier.com"
    # Ensure we have the /v1 suffix
    if not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return base

def _resolve_token() -> str:
    # Accept either variable name
    return os.getenv("TRADIER_API_KEY") or os.getenv("TRADIER_ACCESS_TOKEN") or ""

TRADIER_BASE = _resolve_base()
TRADIER_TOKEN = _resolve_token()

class TradierAuthError(Exception): ...
class TradierHTTPError(Exception): ...

class TradierMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {TRADIER_TOKEN}",
            "Accept": "application/json",
        }

    async def quote_last(self, symbol: str) -> Dict[str, Any]:
        token = _resolve_token()
        if not token:
            raise TradierAuthError("Missing TRADIER_API_KEY / TRADIER_ACCESS_TOKEN")
        url = f"{_resolve_base()}/markets/quotes"
        params = {"symbols": symbol.upper()}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=self._headers(), params=params)
            if r.status_code >= 400:
                raise TradierHTTPError(f"{r.status_code}: {r.text}")
            j = r.json() or {}
            q = (j.get("quotes") or {}).get("quote")
            if isinstance(q, list):
                q = q[0] if q else {}
            last = (q or {}).get("last")
            t = (q or {}).get("trade_date") or (q or {}).get("timestamp") or None
            return {"symbol": symbol.upper(), "price": last, "t": t}
