from __future__ import annotations

import datetime as dt
import os
from typing import Any, Dict, Literal, Tuple

import httpx

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")


class DataError(Exception): ...


def _date(d: dt.date) -> str:
    return d.strftime("%Y-%m-%d")


def _range_for(timeframe: Literal["day", "minute"], lookback: int) -> Tuple[str, str]:
    today = dt.date.today()
    if timeframe == "day":
        start = today - dt.timedelta(days=max(lookback + 10, 200))
        return _date(start), _date(today)
    else:
        # minute data: ask ~20 days (Polygon will cap as per plan)
        start = today - dt.timedelta(days=max(10, min(lookback // 300 + 20, 60)))
        return _date(start), _date(today)


async def fetch_aggregates(symbol: str, timeframe: Literal["day", "minute"], lookback: int) -> Dict[str, Any]:
    if not POLYGON_API_KEY:
        raise DataError("Missing POLYGON_API_KEY in environment.")
    mult = 1
    timespan = "day" if timeframe == "day" else "minute"
    start, end = _range_for(timeframe, lookback)

    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol}/range/{mult}/{timespan}/{start}/{end}"
    params = {"adjusted": "true", "sort": "asc", "limit": "50000", "apiKey": POLYGON_API_KEY}

    async with httpx.AsyncClient(timeout=30.0) as client:
        r = await client.get(url, params=params)
        if r.status_code == 403:
            raise DataError("Polygon plan does not allow this timeframe or endpoint (403).")
        if r.status_code >= 400:
            raise DataError(f"Polygon error {r.status_code}: {r.text[:200]}")
        data = r.json()
    results = data.get("results", []) or []
    if not results:
        raise DataError("No bars returned (empty results).")
    # Normalize to arrays
    o, h, l, c, v, t = [], [], [], [], [], []
    for row in results:
        o.append(float(row.get("o", 0)))
        h.append(float(row.get("h", 0)))
        l.append(float(row.get("l", 0)))
        c.append(float(row.get("c", 0)))
        v.append(float(row.get("v", 0)))
        t.append(int(row.get("t", 0)))  # ms since epoch
    # Keep only last `lookback` bars
    if len(c) > lookback:
        o, h, l, c, v, t = o[-lookback:], h[-lookback:], l[-lookback:], c[-lookback:], v[-lookback:], t[-lookback:]
    return {
        "open": o,
        "high": h,
        "low": l,
        "close": c,
        "volume": v,
        "ts": t,
        "meta": {"timeframe": timeframe, "count": len(c)},
    }
