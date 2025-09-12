import httpx
from typing import Any, Dict

from app.core.settings import settings

class TradierError(RuntimeError): ...


def _client() -> httpx.AsyncClient:
    base = settings.tradier_base_url
    token = settings.TRADIER_ACCESS_TOKEN or ""
    if not base:
        raise TradierError("TRADIER_BASE not set")
    if not token:
        raise TradierError("TRADIER_ACCESS_TOKEN not set")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "ta/1.0",
    }
    return httpx.AsyncClient(base_url=base, headers=headers, timeout=12.0)


async def get(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with _client() as c:
        r = await c.get(path, params=params or {})
    if r.status_code >= 400:
        raise TradierError(f"HTTP {r.status_code}: {r.text[:400]}")
    return r.json()
