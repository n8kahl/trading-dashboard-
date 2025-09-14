from __future__ import annotations
import os, httpx
from typing import Dict, Any, Optional

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://api.tradier.com/v1")
TRADIER_TOKEN = os.getenv("TRADIER_API_KEY", "")

class TradierMarket:
    def __init__(self, timeout: float = 10.0):
        self.timeout = timeout
        if not TRADIER_TOKEN:
            # We don't raise here; caller should handle empty token gracefully.
            pass

    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {TRADIER_TOKEN}",
            "Accept": "application/json",
        }

    async def quote_last(self, symbol: str) -> Dict[str, Any]:
        """
        Get the underlying's last price via Tradier.
        Returns: {"symbol": "SPY", "price": 123.45, "t": ISO-or-epoch-or-null}
        """
        if not TRADIER_TOKEN:
            return {"symbol": symbol.upper(), "price": None, "t": None}

        url = f"{TRADIER_BASE}/markets/quotes"
        params = {"symbols": symbol.upper()}
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=self._headers(), params=params)
            r.raise_for_status()
            j = r.json() or {}
            # Tradier returns either a dict or a list under quotes.quote
            q = (j.get("quotes") or {}).get("quote")
            if isinstance(q, list):
                q = q[0] if q else {}
            last = (q or {}).get("last")
            # Tradier's "trade_date" can be a unix sec, or "2025-09-12T15:59:59Z" depending on plan
            t = (q or {}).get("trade_date") or (q or {}).get("timestamp") or None
            return {"symbol": symbol.upper(), "price": last, "t": t}
