from __future__ import annotations
from typing import List, Dict, Any
from datetime import datetime, timezone
import os
import httpx

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

def _iso_today() -> str:
    return datetime.now(timezone.utc).date().isoformat()

async def _news_for_symbol(client: httpx.AsyncClient, symbol: str, published_utc_gte: str) -> List[Dict[str, Any]]:
    # Polygon News: https://polygon.io/docs/stocks/get_v2_reference_news
    # Example: /v2/reference/news?ticker=AAPL&published_utc.gte=YYYY-MM-DD&limit=50
    url = "https://api.polygon.io/v2/reference/news"
    params = {
        "ticker": symbol.upper(),
        "published_utc.gte": published_utc_gte,
        "limit": 50,
        "apiKey": POLYGON_API_KEY,
    }
    try:
        r = await client.get(url, params=params, timeout=15)
        r.raise_for_status()
        j = r.json()
        results = j.get("results", [])
        out = []
        for it in results:
            out.append({
                "symbol": symbol.upper(),
                "headline": it.get("title") or it.get("headline") or "",
                "source": (it.get("publisher", {}) or {}).get("name") or "",
                "url": it.get("article_url") or it.get("url") or "",
                "published_utc": it.get("published_utc") or "",
            })
        return out
    except Exception:
        return []

async def fetch_today_events_polygon(watchlist: List[str]) -> Dict[str, Any]:
    """
    Returns { 'as_of': 'YYYY-MM-DD', 'earnings': [...], 'news': [...] }
    We wire NEWS now (official endpoint); earnings will be added via MCP tool later.
    """
    today = _iso_today()
    news_agg: List[Dict[str, Any]] = []

    if not POLYGON_API_KEY:
        return {"as_of": today, "earnings": [], "news": []}

    # Pull news per symbol (keeps the payload relevant and fast)
    async with httpx.AsyncClient() as client:
        for sym in (watchlist or []):
            news_agg.extend(await _news_for_symbol(client, sym, today))

    # De-dup headlines (same headline for multiple sources)
    seen = set()
    deduped = []
    for n in news_agg:
        key = (n.get("symbol",""), n.get("headline",""))
        if key in seen: continue
        seen.add(key)
        deduped.append(n)

    return {
        "as_of": today,
        "earnings": [],   # TODO: add via MCP tool (or Polygon earnings if plan supports it)
        "news": deduped
    }
