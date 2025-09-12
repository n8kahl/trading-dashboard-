import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.db import db_session
from app.models import Alert

POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "30"))
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_BASE = "https://api.polygon.io"

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)

async def _latest_price(symbol: str, timeframe: str) -> Optional[float]:
    """
    Returns the most recent close/price for the symbol.
    Supports timeframe 'minute' and 'day' via Polygon aggregates.
    """
    if not POLYGON_API_KEY:
        return None

    # choose span and window
    if timeframe == "minute":
        timespan = "minute"
        # last 2 days window to ensure we catch late sessions / weekends
        start = (_now_utc() - timedelta(days=2)).date().isoformat()
        end = _now_utc().date().isoformat()
    else:
        # fallback to daily
        timespan = "day"
        start = (_now_utc() - timedelta(days=30)).date().isoformat()
        end = _now_utc().date().isoformat()

    url = f"{POLYGON_BASE}/v2/aggs/ticker/{symbol.upper()}/range/1/{timespan}/{start}/{end}"
    params = {
        "limit": 1,
        "sort": "desc",
        "apiKey": POLYGON_API_KEY,
    }
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, params=params)
        if r.status_code != 200:
            return None
        data = r.json()
        # standard Polygon aggregates response
        # { results: [ { c: close, ... } ], resultsCount: N, status: "OK" }
        results = data.get("results") or []
        if not results:
            return None
        last = results[0]
        # try 'c' (close), fallback to 'p' (price), else None
        if "c" in last:
            return float(last["c"])
        if "p" in last:
            return float(last["p"])
        return None

def _passes_condition(price: float, cond: Dict[str, Any]) -> bool:
    ctype = (cond.get("type") or "").lower()
    value = cond.get("value")
    thr = cond.get("threshold_pct")  # optional, interpret as percent
    if value is None:
        return False
    try:
        value = float(value)
    except Exception:
        return False

    # apply optional threshold tolerance
    # if price_above with threshold_pct=0.5, require price >= value*(1-0.005) (a little slack)
    # if price_below with threshold_pct=0.5, require price <= value*(1+0.005)
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

    # Unknown condition types are treated as false
    return False

async def alerts_poller(loop_forever: bool = True):
    if not POLYGON_API_KEY:
        print("[poller] POLYGON_API_KEY missing; poller idle.")
        return

    print(f"[poller] starting (interval={POLL_SEC}s)")
    try:
        while True:
            # one pass
            try:
                utcnow = _now_utc()
                with db_session() as db:
                    # disable expired
                    db.execute(
                        "UPDATE alerts SET is_active = FALSE WHERE expires_at IS NOT NULL AND expires_at < NOW()"
                    )

                    # fetch a batch of active alerts
                    rows = db.execute(
                        "SELECT id, symbol, timeframe, condition, is_active FROM alerts WHERE is_active = TRUE ORDER BY id DESC LIMIT 200"
                    ).fetchall()

                    for r in rows:
                        alert_id = r[0]
                        symbol = r[1]
                        timeframe = r[2] or "day"
                        raw_condition = r[3]
                        try:
                            import json
                            cond = json.loads(raw_condition) if isinstance(raw_condition, str) else (raw_condition or {})
                        except Exception:
                            cond = {"raw": raw_condition}

                        price = await _latest_price(symbol, timeframe)
                        if price is None:
                            continue

                        if _passes_condition(price, cond):
                            # set triggered_at if not already set; keep active (or disable if you prefer)
                            db.execute(
                                "UPDATE alerts SET triggered_at = COALESCE(triggered_at, NOW()) WHERE id = %s",
                                (alert_id,)
                            )
                # commit happens via session context manager
            except Exception as e:
                print(f"[poller] pass error: {e}")

            if not loop_forever:
                break
            await asyncio.sleep(POLL_SEC)
    except asyncio.CancelledError:
        print("[poller] cancelled; exiting")
