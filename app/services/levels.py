import os, httpx
from datetime import datetime, timedelta, timezone

BASE = "https://api.polygon.io"
API_KEY = os.getenv("POLYGON_API_KEY","").strip()

def _params(extra=None):
    if not API_KEY:
        raise RuntimeError("POLYGON_API_KEY not set")
    p = {"apiKey": API_KEY}
    if extra: p.update(extra)
    return p

async def _safe_get(client: httpx.AsyncClient, url: str, params: dict):
    try:
        r = await client.get(url, params=params)
        r.raise_for_status()
        return r.json()
    except httpx.HTTPStatusError as e:
        # Return a consistent shape so callers can handle gracefully
        return {"_error": f"http {e.response.status_code}", "_url": url}
    except Exception as e:
        return {"_error": str(e), "_url": url}

async def get_prev_day_hl(symbol: str):
    now = datetime.now(timezone.utc)
    start = (now - timedelta(days=14)).strftime("%Y-%m-%d")
    end   = now.strftime("%Y-%m-%d")
    url = f"{BASE}/v2/aggs/ticker/{symbol}/range/1/day/{start}/{end}"
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _safe_get(client, url, _params({"adjusted":"true","sort":"desc","limit":14}))
        results = (data or {}).get("results", [])
        if not results:
            return None
        today = now.date()
        for bar in results:  # results likely in desc order
            ts = bar.get("t")
            if ts is None: continue
            dt = datetime.fromtimestamp(ts/1000, tz=timezone.utc).date()
            if dt != today:
                return {"high": bar.get("h"), "low": bar.get("l"), "date": dt.isoformat()}
        return None

async def get_opening_range(symbol: str, minutes: int = 5):
    now = datetime.now(timezone.utc)
    the_day = now.strftime("%Y-%m-%d")
    url = f"{BASE}/v2/aggs/ticker/{symbol}/range/1/minute/{the_day}/{the_day}"
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _safe_get(client, url, _params({"adjusted":"true","sort":"asc","limit":1000}))
        bars = (data or {}).get("results", [])
        if not bars:
            return None
        first = bars[:max(1, minutes)]
        orh = max(b.get("h", 0) for b in first)
        orl = min(b.get("l", 0) for b in first)
        return {"minutes": minutes, "high": orh, "low": orl}

async def get_intraday_vwap(symbol: str):
    now = datetime.now(timezone.utc)
    the_day = now.strftime("%Y-%m-%d")
    url = f"{BASE}/v2/aggs/ticker/{symbol}/range/1/minute/{the_day}/{the_day}"
    async with httpx.AsyncClient(timeout=20) as client:
        data = await _safe_get(client, url, _params({"adjusted":"true","sort":"asc","limit":5000}))
        bars = (data or {}).get("results", [])
        if not bars:
            return None
        pv = 0.0; vol = 0.0
        for b in bars:
            c = float(b.get("c", 0.0))
            v = float(b.get("v", 0.0))
            pv += c * v; vol += v
        return (pv/vol) if vol > 0 else None
