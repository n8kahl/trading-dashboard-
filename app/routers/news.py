from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import httpx
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/news", tags=["news"])

POLYGON_API_KEY = (os.getenv("POLYGON_API_KEY") or "").strip()

# simple in-memory cache: key -> (expires_at_ms, items)
_CACHE: Dict[Tuple[str, int], Tuple[int, List[Dict[str, Any]]]] = {}


async def _polygon_news(symbol: str, limit: int) -> List[Dict[str, Any]]:
    if not POLYGON_API_KEY:
        return []
    url = "https://api.polygon.io/v2/reference/news"
    params = {"ticker": symbol.upper(), "limit": max(1, min(limit, 50))}
    headers = {"Authorization": f"Bearer {POLYGON_API_KEY}"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params, headers=headers)
    if r.status_code >= 400:
        # treat provider errors as empty set to avoid breaking dashboards
        return []
    data = r.json()
    results = data.get("results") or []
    items: List[Dict[str, Any]] = []
    for it in results:
        items.append(
            {
                "symbol": symbol.upper(),
                "title": it.get("title"),
                "url": it.get("article_url") or it.get("url"),
                "source": it.get("publisher", {}).get("name") if isinstance(it.get("publisher"), dict) else None,
                "published_at": it.get("published_utc") or it.get("published_at"),
            }
        )
    return items


@router.get("")
async def get_news(symbols: str = Query("SPY"), limit: int = Query(10)) -> Dict[str, Any]:
    """Return recent news headlines for one or more symbols via Polygon.

    Query params:
      - symbols: comma-delimited list like "SPY,AAPL"
      - limit: max items per symbol (capped 50)

    Caches results for ~120s to reduce provider load.
    """
    syms = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    if not syms:
        raise HTTPException(status_code=400, detail="symbols required")

    now_ms = int(time.time() * 1000)
    ttl_ms = 120_000
    combined: List[Dict[str, Any]] = []
    seen_urls: set[str] = set()

    for s in syms:
        cache_key = (s, max(1, min(limit, 50)))
        expiry, items = _CACHE.get(cache_key, (0, []))
        if expiry > now_ms:
            data = items
        else:
            data = await _polygon_news(s, limit)
            _CACHE[cache_key] = (now_ms + ttl_ms, data)

        for it in data:
            url = it.get("url")
            if url and url in seen_urls:
                continue
            if url:
                seen_urls.add(url)
            combined.append(it)

    return {"ok": True, "items": combined}

