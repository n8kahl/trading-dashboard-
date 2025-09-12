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

        alerts = db.execute(select(Alert)).scalars().all()
        if not alerts: return

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
            tripped = False
            if a.condition_type == "price_above" and last >= a.value:
                tripped = True
            elif a.condition_type == "price_below" and last <= a.value:
                tripped = True

            if tripped:
                trig = AlertTrigger(alert_id=a.id, symbol=a.symbol, price=last)
                db.add(trig)
                # one-shot alert: delete it after trigger (simple)
                db.execute(delete(Alert).where(Alert.id==a.id))
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
