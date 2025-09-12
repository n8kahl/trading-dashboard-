import os, asyncio, datetime as dt
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
from app.models import Alert, AlertTrigger
from app.db import SessionLocal
from app.services.providers import get_last_price

POLL_SEC = int(os.getenv("ALERT_POLL_SEC","15"))

async def _check_once():
    # Each tick uses a fresh session
    db: Session = SessionLocal()
    try:
        now = dt.datetime.now(dt.timezone.utc)
        # Remove expired
        db.execute(delete(Alert).where(Alert.expires_at.is_not(None), Alert.expires_at < now))
        db.commit()

        alerts = db.execute(select(Alert).where(Alert.is_active == True)).scalars().all()
        if not alerts:
            return

        # Group by symbol to avoid duplicate quote calls (simple cache)
        symbols = sorted({a.symbol for a in alerts})
        last_prices = {}
        for sym in symbols:
            try:
                last = await get_last_price(sym)
            except Exception:
                last = None
            if last is not None:
                last_prices[sym] = float(last)

        for a in alerts:
            last = last_prices.get(a.symbol)
            if last is None:
                continue
            cond = a.condition or {}
            ctype = cond.get("type")
            value = cond.get("value")
            if ctype == "price_above" and value is not None and last >= float(value):
                trig = AlertTrigger(alert_id=a.id, symbol=a.symbol, payload={"price": last, "condition": a.condition})
                db.add(trig)
                db.execute(delete(Alert).where(Alert.id == a.id))
            elif ctype == "price_below" and value is not None and last <= float(value):
                trig = AlertTrigger(alert_id=a.id, symbol=a.symbol, payload={"price": last, "condition": a.condition})
                db.add(trig)
                db.execute(delete(Alert).where(Alert.id == a.id))
        db.commit()
    finally:
        db.close()

async def run_alert_poller():
    # Simple endless loop
    while True:
        try:
            await _check_once()
        except Exception:
            # swallow to keep the loop alive; logs handled by app logger if needed
            pass
        await asyncio.sleep(POLL_SEC)
