import os, asyncio
from typing import Dict, Any

from app.services import alerts_store
from app.services.providers import get_last_price

POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "15"))

async def _check_once() -> None:
    alerts = alerts_store.list_active()
    if not alerts:
        return

    # Group by symbol to avoid duplicate quote calls (simple cache)
    symbols = sorted({a["symbol"] for a in alerts})
    last_prices: Dict[str, float] = {}
    for sym in symbols:
        try:
            last = await get_last_price(sym)
        except Exception:
            last = None
        if last is not None:
            last_prices[sym] = float(last)

    for a in alerts:
        last = last_prices.get(a["symbol"])
        if last is None:
            continue
        cond: Dict[str, Any] = a.get("condition") or {}
        ctype = cond.get("type")
        value = cond.get("value")
        if ctype == "price_above" and value is not None and last >= float(value):
            payload = {"price": last, "condition": a.get("condition")}
            alerts_store.mark_triggered(a["id"])
            alerts_store.add_trigger(a["id"], a["symbol"], payload)
            alerts_store.delete(a["id"])
        elif ctype == "price_below" and value is not None and last <= float(value):
            payload = {"price": last, "condition": a.get("condition")}
            alerts_store.mark_triggered(a["id"])
            alerts_store.add_trigger(a["id"], a["symbol"], payload)
            alerts_store.delete(a["id"])

async def run_alert_poller():
    # Simple endless loop
    while True:
        try:
            await _check_once()
        except Exception:
            # swallow to keep the loop alive; logs handled by app logger if needed
            pass
        await asyncio.sleep(POLL_SEC)
