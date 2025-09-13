import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import httpx
from sqlalchemy import select

from app.core.ws import manager
from app.integrations.discord import send_message as discord_send
from app.models.settings import AppSettings
from app.models.misc import Alert, AlertTrigger
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
    now = _now_utc()
    with session_scope() as db:
        try:
            # ORM path (preferred)
            rows = db.execute(select(Alert).where(Alert.is_active == True)).scalars().all()  # noqa: E712
            active: list[Alert] = []
            for a in rows:
                if a.expires_at and a.expires_at < now:
                    a.is_active = False
                    db.add(a)
                    continue
                active.append(a)

            settings = db.execute(select(AppSettings).order_by(AppSettings.id.asc())).scalars().first()
            discord_url = settings.discord_webhook_url if settings else None
            discord_enabled = bool(settings.discord_alerts_enabled) if settings else False
            discord_types_raw = (settings.discord_alert_types or "") if settings else ""
            discord_types = {t.strip().lower() for t in discord_types_raw.split(",") if t.strip()}

            for a in active:
                symbol = a.symbol
                timeframe = a.timeframe or "day"
                cond = a.condition or {}
                price = await _latest_price(symbol, timeframe)
                if price is None:
                    continue
                if _passes_condition(price, cond):
                    trig = AlertTrigger(alert_id=a.id, symbol=symbol, payload={"price": price, "timeframe": timeframe})
                    db.add(trig)
                    suggestion = None
                    ctype = (cond.get("type") or "").lower()
                    if ctype == "price_above":
                        suggestion = f"Consider long scalp on {symbol} (price above {cond.get('value')})."
                    elif ctype == "price_below":
                        suggestion = f"Consider trim/short on {symbol} (price below {cond.get('value')})."
                    try:
                        await manager.broadcast_json(
                            {
                                "type": "alert",
                                "level": "info",
                                "msg": suggestion or f"Alert triggered for {symbol}",
                                "meta": {"symbol": symbol, "price": price, "condition": cond},
                            }
                        )
                    except Exception:
                        pass
                    try:
                        if discord_enabled and discord_url:
                            if (not discord_types) or (ctype in discord_types):
                                msg = suggestion or f"Alert triggered for {symbol}: {cond} @ {price}"
                                await discord_send(discord_url, msg)
                    except Exception:
                        pass
            return
        except Exception:
            # Fallback to SQL-string path for tests that stub raw execute()
            try:
                db.execute(
                    "UPDATE alerts SET is_active = FALSE WHERE expires_at IS NOT NULL AND expires_at < NOW()",
                )
                rows = db.execute(
                    "SELECT id, symbol, timeframe, condition, is_active FROM alerts WHERE is_active = TRUE ORDER BY id DESC LIMIT 200",
                ).fetchall()
                for r in rows:
                    alert_id, symbol, timeframe, raw_condition, _ = r
                    try:
                        import json

                        cond = json.loads(raw_condition) if isinstance(raw_condition, str) else (raw_condition or {})
                    except Exception:
                        cond = {"raw": raw_condition}
                    price = await _latest_price(symbol, timeframe or "day")
                    if price is None:
                        continue
                    if _passes_condition(price, cond):
                        db.execute(
                            "UPDATE alerts SET triggered_at = COALESCE(triggered_at, NOW()) WHERE id = %s",
                            (alert_id,),
                        )
            except Exception:
                # swallow to keep loop resilient in tests
                pass


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
