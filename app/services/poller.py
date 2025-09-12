import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.services import alerts_store

POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "30"))
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_BASE = "https://api.polygon.io"

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

async def _latest_price(symbol: str, timeframe: str) -> Optional[float]:
    """Return the most recent close/price for the symbol."""
    if not POLYGON_API_KEY:
        return None

    if timeframe == "minute":
        timespan = "minute"
        start = (_now_utc() - timedelta(days=2)).date().isoformat()
        end = _now_utc().date().isoformat()
    else:
        timespan = "day"
        start = (_now_utc() - timedelta(days=30)).date().isoformat()
        end = _now_utc().date().isoformat()

    url = f"{POLYGON_BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/{timespan}/{start}/{end}"
    params = {"limit": 1, "sort": "desc", "apiKey": POLYGON_API_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            return None
        data = r.json()
        results = data.get("results") or []
        if not results:
            return None
        last = results[0]
        if "c" in last:
            return float(last["c"])
        if "p" in last:
            return float(last["p"])
        return None

def _passes_condition(price: float, cond: Dict[str, Any]) -> bool:
    ctype = (cond.get("type") or "").lower()
    value = cond.get("value")
    thr = cond.get("threshold_pct")
    if value is None:
        return False
    try:
        value = float(value)
    except Exception:
        return False

    tol = 0.0
    try:
        if thr is not None:
            tol = float(thr) / 100.0
    except Exception:
        tol = 0.0

    if ctype == "price_above":
        return price >= value * (1.0 - tol)
    if ctype == "price_below":
        return price <= value * (1.0 + tol)
    return False

async def alerts_poller(loop_forever: bool = True):
    if not POLYGON_API_KEY:
        print("[poller] POLYGON_API_KEY missing; poller idle.")
        return

    print(f"[poller] starting (interval={POLL_SEC}s)")
    try:
        while True:
            try:
                rows = alerts_store.list_active()
                for a in rows:
                    symbol = a["symbol"]
                    timeframe = a.get("timeframe", "day")
                    cond = a.get("condition") or {}
                    price = await _latest_price(symbol, timeframe)
                    if price is None:
                        continue
                    if _passes_condition(price, cond):
                        alerts_store.mark_triggered(a["id"])
                        alerts_store.add_trigger(a["id"], symbol, {"price": price, "condition": cond})
            except Exception as e:
                print(f"[poller] pass error: {e}")

            if not loop_forever:
                break
            await asyncio.sleep(POLL_SEC)
    except asyncio.CancelledError:
        print("[poller] cancelled; exiting")
