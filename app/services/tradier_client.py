import os, httpx
from typing import Any, Dict

_BASE = os.getenv("TRADIER_BASE", "").rstrip("/")
_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN", "").strip()

class TradierError(RuntimeError): ...


def _client() -> httpx.AsyncClient:
    if not _BASE:
        raise TradierError("TRADIER_BASE not set")
    if not _TOKEN:
        raise TradierError("TRADIER_ACCESS_TOKEN not set")
    headers = {
        "Authorization": f"Bearer {_TOKEN}",
        "Accept": "application/json",
        "User-Agent": "ta/1.0",
    }
    return httpx.AsyncClient(base_url=_BASE, headers=headers, timeout=12.0)


async def get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with _client() as c:
        r = await c.get(path, params=params or {})
    if r.status_code >= 400:
        raise TradierError(f"HTTP {r.status_code}: {r.text[:400]}")
    return r.json()
