from __future__ import annotations
import os, httpx

BASE = "https://api.tradier.com/v1"
TOKEN = os.getenv("TRADIER_ACCESS_TOKEN", "")
ACCOUNT_ID = os.getenv("TRADIER_ACCOUNT_ID", "")

def _hdrs():
    auth = TOKEN
    if auth and not auth.lower().startswith("bearer "):
        auth = f"Bearer {auth}"
    return {
        "Authorization": auth,
        "Accept": "application/json",
    }

class TradierClient:
    def __init__(self, timeout: float = 8.0):
        self.timeout = timeout

    async def account_balances(self) -> dict:
        if not ACCOUNT_ID:
            return {}
        url = f"{BASE}/accounts/{ACCOUNT_ID}/balances"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=_hdrs())
            r.raise_for_status()
            return r.json() or {}

    async def positions(self) -> dict:
        if not ACCOUNT_ID:
            return {"positions": []}
        url = f"{BASE}/accounts/{ACCOUNT_ID}/positions"
        async with httpx.AsyncClient(timeout=self.timeout) as c:
            r = await c.get(url, headers=_hdrs())
            r.raise_for_status()
            return r.json() or {}
