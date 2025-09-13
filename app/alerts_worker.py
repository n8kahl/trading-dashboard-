from __future__ import annotations
import os, asyncio, math
from typing import Dict, List, Any, Tuple
import httpx
from sqlalchemy import create_engine, text

DB_URL = os.environ["DATABASE_URL"]
ENGINE = create_engine(DB_URL, future=True)
POLL_SEC = int(os.getenv("ALERT_POLL_SEC", "15"))
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY")
NOTIFY_WEBHOOK = os.getenv("ALERT_WEBHOOK_URL")  # optional

async def fetch_last_prices(symbols: List[str]) -> Dict[str, float]:
    prices: Dict[str, float] = {}
    if not POLYGON_API_KEY or not symbols:
        return prices
    async with httpx.AsyncClient(timeout=8.0) as client:
        for sym in symbols:
            try:
                r = await client.get(f"https://api.polygon.io/v2/last/trade/{sym}",
                                     params={"apiKey": POLYGON_API_KEY})
                if r.status_code == 200 and (res := r.json().get("results")):
                    prices[sym] = float(res.get("p"))
            except Exception:
                pass
    return prices

async def notify(event: Dict[str, Any]) -> None:
    if not NOTIFY_WEBHOOK:
        return
    try:
        async with httpx.AsyncClient(timeout=6.0) as client:
            await client.post(NOTIFY_WEBHOOK, json=event)
    except Exception:
        pass

async def run_poller():
    while True:
        try:
            # 1) pull active alerts + unique symbols
            with ENGINE.begin() as conn:
                rows = conn.execute(text("""
                    SELECT id, symbol, level
                    FROM alerts
                    WHERE (is_active = true OR is_active IS NULL)
                """)).mappings().all()
            if not rows:
                await asyncio.sleep(POLL_SEC); continue
            symbols = sorted({r["symbol"].upper() for r in rows if r["symbol"]})

            # 2) get last prices
            prices = await fetch_last_prices(symbols)

            # 3) evaluate triggers
            for r in rows:
                sym, lvl = r["symbol"].upper(), float(r["level"]) if r["level"] is not None else None
                if lvl is None or sym not in prices: 
                    continue
                px = prices[sym]
                trig = None
                if math.isfinite(px) and math.isfinite(lvl):
                    if px >= lvl: trig = "cross_up"
                    # (add more logic as needed: cross_down, %distance, etc.)

                if trig:
                    evt = {"alert_id": r["id"], "symbol": sym, "price": round(px,4), "trigger": trig}
                    with ENGINE.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO alert_events (alert_id, symbol, price, trigger, note)
                            VALUES (:aid, :sym, :px, :trig, :note)
                        """), {"aid": r["id"], "sym": sym, "px": px, "trig": trig, "note": "bg_poller"})
                    await notify(evt)
        except Exception as e:
            print("[poller] error:", e, flush=True)
        await asyncio.sleep(POLL_SEC)
