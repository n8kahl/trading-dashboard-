import os, httpx
from typing import Any, Dict

_BASE = "https://api.polygon.io"
_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()

class PolygonError(RuntimeError): ...


def _client() -> httpx.AsyncClient:
    """Return a configured async HTTP client for Polygon."""
    if not _API_KEY:
        raise PolygonError("POLYGON_API_KEY not set")
    headers = {"Authorization": f"Bearer " + _API_KEY}
    return httpx.AsyncClient(base_url=_BASE, headers=headers, timeout=10.0)


async def get_json(path: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    async with _client() as c:
        r = await c.get(path, params=params or {})
    if r.status_code >= 400:
        raise PolygonError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()


async def last_quote(symbol: str) -> Dict[str, Any]:
    """Return last trade price for symbol."""
    try:
        js = await get_json(f"/v2/last/trade/{symbol}")
        price = js.get("results", {}).get("p")
        ts = js.get("results", {}).get("t")
        return {"ok": True, "symbol": symbol, "last": price, "ts": ts}
    except Exception as e:
        return {"ok": False, "error": str(e)}
