import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx

from app.services.utils import RateLimiter, run_periodic, session_scope

POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "30"))
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "").strip()
POLYGON_BASE = "https://api.polygon.io"
API_RATE = int(os.getenv("POLL_API_RATE", "5"))

_rate_limiter = RateLimiter(API_RATE)


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

    async with _rate_limiter:
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


async def _poll_once() -> None:
    with session_scope() as db:
        db.execute(
            "UPDATE alerts SET is_active = FALSE WHERE expires_at IS NOT NULL AND expires_at < NOW()",
        )

        rows = db.execute(
            "SELECT id, symbol, timeframe, condition, is_active FROM alerts WHERE is_active = TRUE ORDER BY id DESC LIMIT 200",
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
                db.execute(
                    "UPDATE alerts SET triggered_at = COALESCE(triggered_at, NOW()) WHERE id = %s",
                    (alert_id,),
                )


async def alerts_poller(loop_forever: bool = True) -> None:
    if not POLYGON_API_KEY:
        print("[poller] POLYGON_API_KEY missing; poller idle.")
        return

    print(f"[poller] starting (interval={POLL_SEC}s)")
    try:
        await run_periodic(
            _poll_once,
            POLL_SEC,
            on_error=lambda e: print(f"[poller] pass error: {e}"),
            loop_forever=loop_forever,
        )
    except asyncio.CancelledError:  # pragma: no cover
        print("[poller] cancelled; exiting")
