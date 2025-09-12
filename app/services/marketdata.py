import asyncio
import datetime as dt
import os
from typing import Any, Dict, List, Optional

import httpx

POLY_KEY = os.getenv("POLYGON_API_KEY")

BASE = "https://api.polygon.io"


async def _get_json(url: str, params: Dict[str, Any]) -> Dict[str, Any]:
    params = dict(params or {})
    params["apiKey"] = POLY_KEY
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()


async def daily_bars(symbol: str, lookback_days: int = 21) -> List[Dict[str, Any]]:
    """Most-recent (up to) 21 daily bars including current day if session open.
    Uses aggregates v2: 1 day range."""
    end = dt.date.today()
    start = end - dt.timedelta(days=lookback_days + 5)  # pad weekends
    url = f"{BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start}/{end}"
    js = await _get_json(url, {"adjusted": "true", "sort": "asc", "limit": 5000})
    return js.get("results", []) or []


def compute_rvol(bars: List[Dict[str, Any]], window: int = 20) -> Optional[float]:
    """RVOL = today_volume / avg(volume[-window:]) if enough history; else None."""
    if not bars:
        return None
    vols = [b.get("v") for b in bars if "v" in b]
    if len(vols) < 2:
        return None
    today = vols[-1]
    hist = vols[-(window + 1) : -1]
    if len(hist) < 5:
        return None
    avg = sum(hist[-window:]) / min(len(hist), window)
    if avg <= 0:
        return None
    return today / avg


def in_session_now(tz_name: str = "America/New_York") -> bool:
    # Trading windows you prefer: 09:40–11:15, 14:15–15:45 ET (Mon–Fri)
    import datetime as dt

    import pytz

    et = pytz.timezone(tz_name)
    now = dt.datetime.now(et)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    t = now.time()
    w1 = (dt.time(9, 40), dt.time(11, 15))
    w2 = (dt.time(14, 15), dt.time(15, 45))

    def within(w):
        return w[0] <= t <= w[1]

    return within(w1) or within(w2)


async def ranked_by_rvol(symbols: List[str], limit: int = 10) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    symbols = symbols[:50]
    batch_size = 10
    for i in range(0, len(symbols), batch_size):
        batch = symbols[i : i + batch_size]
        tasks = [daily_bars(s, 21) for s in batch]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for s, bars in zip(batch, results):
            if isinstance(bars, Exception):
                bars = []
            rvol = compute_rvol(bars, 20)
            last_close = bars[-1]["c"] if bars else None
            out.append({"symbol": s, "rvol": rvol, "last": last_close})
    out.sort(key=lambda x: (x["rvol"] is None, -(x["rvol"] or 0.0)))
    return out[:limit]
