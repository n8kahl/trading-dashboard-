import os, httpx
from typing import Any, Dict

_BASE = "https://api.polygon.io"
_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()

class PolygonError(RuntimeError): ...

def _client() -> httpx.Client:
    if not _API_KEY:
        raise PolygonError("POLYGON_API_KEY not set")
    headers = {"Authorization": f"Bearer " + _API_KEY}
    return httpx.Client(base_url=_BASE, headers=headers, timeout=10.0)

def get_json(path: str, params: Dict[str, Any] | None=None) -> Dict[str, Any]:
    with _client() as c:
        r = c.get(path, params=params or {})
    if r.status_code >= 400:
        raise PolygonError(f"HTTP {r.status_code}: {r.text[:300]}")
    return r.json()
