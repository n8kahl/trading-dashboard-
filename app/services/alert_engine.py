from __future__ import annotations
import os, asyncio, datetime as dt
from typing import Dict, Any, List, Optional
import httpx
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.services.db import ensure_db
from app.models import Alert, AlertTrigger

POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "30"))
POLY_KEY = os.getenv("POLYGON_API_KEY")


async def _last_minute_close_tradier(symbol: str) -> Optional[float]:
    try:
        from app.services.tradier import get_timesales_1min
        js = await get_timesales_1min(symbol, minutes_back=1)
        if js.get("ok") and js.get("bars"):
            return float(js["bars"][-1]["c"])
    except Exception:
        pass
    return None

async def _last_minute_close(symbol: str) -> Optional[float]:

    """Fetch the most recent 1-minute bar close for today."""
    if not POLY_KEY: return None
    today = dt.date.today()
    start = today.isoformat(); end = today.isoformat()
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/minute/{start}/{end}?adjusted=true&sort=desc&limit=1&apiKey={POLY_KEY}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url)
        if r.status_code != 200: return None
        js = r.json()
        if js.get("status") not in ("OK","DELAYED"): return None
        res = js.get("results") or []
        if not res: return None
        return float(res[0].get("c"))

def _condition_met(kind: str, value: float, price: float, cfg: Dict[str,Any]) -> bool:
    if kind == "price_above": return price >= value
    if kind == "price_below": return price <= value
    return False

async def poll_once():
    engine, SessionLocal = ensure_db()
    db: Session = SessionLocal()
    try:
        rows: List[Alert] = db.execute(select(Alert).where(Alert.is_active == True)).scalars().all()
        symbols = sorted({r.symbol for r in rows})
        prices: Dict[str, Optional[float]] = {}
        # fetch prices sequentially to respect free-tier
        for s in symbols:
            prices[s] = await _last_minute_close(s)
        for a in rows:
            p = prices.get(a.symbol)
            if p is None: continue
            cond = a.condition or {}
            k = cond.get("type"); v = cond.get("value")
            if k and isinstance(v,(int,float)) and _condition_met(k, float(v), float(p), cond):
                db.add(AlertTrigger(alert_id=a.id, symbol=a.symbol, payload={"price": p, "condition": a.condition}))
        db.commit()
    finally:
        db.close()

async def run_loop():
    while True:
        try:
            await poll_once()
        except Exception:
            pass
        await asyncio.sleep(POLL_SEC)
