from __future__ import annotations

import datetime as dt
import os
from typing import Dict, Optional

import httpx

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
POLYGON_BASE = "https://api.polygon.io"


class PolygonClient:
    def __init__(self, api_key: Optional[str] = None, base: str = POLYGON_BASE):
        self.api_key = api_key or POLYGON_API_KEY
        self.base = base
        if not self.api_key:
            raise RuntimeError("POLYGON_API_KEY not set")

    async def _get(self, path: str, params: Dict) -> Optional[dict]:
        # Always add key
        p = dict(params or {})
        p.setdefault("apiKey", self.api_key)
        try:
            async with httpx.AsyncClient(timeout=20.0) as s:
                r = await s.get(self.base + path, params=p)
                # Return JSON even on non-200 to avoid HTML errors upstream
                content_type = r.headers.get("content-type", "")
                data = None
                try:
                    data = r.json()
                except Exception:
                    data = {"status_code": r.status_code, "text": r.text[:500]}
                if r.status_code != 200:
                    return {"error": {"status_code": r.status_code, "data": data}}
                return data
        except httpx.RequestError as e:
            return {"error": {"request_error": str(e)}}

    async def get_minute_bars(self, symbol: str, start: dt.datetime, end: dt.datetime, limit: int = 5000) -> Dict:
        path = (
            f"/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{start.strftime('%Y-%m-%d')}/{end.strftime('%Y-%m-%d')}"
        )
        params = {"adjusted": "true", "sort": "asc", "limit": str(limit)}
        return await self._get(path, params)

    async def latest_nbbo(self, symbol: str) -> Dict:
        path = f"/v3/quotes/{symbol.upper()}/nbbo/latest"
        return await self._get(path, params={})
