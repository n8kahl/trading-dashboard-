import asyncio
import os

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import models
from app.db.db import SessionLocal

BASE = "https://api.polygon.io"
API_KEY = os.getenv("POLYGON_API_KEY", "").strip()


async def last_price(symbol: str) -> float | None:
    # get most recent minute bar today
    from datetime import datetime, timezone

    start = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    url = f"{BASE}/v2/aggs/ticker/{symbol}/range/1/minute/{start}/{start}"
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(url, params={"apiKey": API_KEY, "adjusted": "true", "sort": "desc", "limit": 1})
        r.raise_for_status()
        res = r.json().get("results", [])
        if not res:
            return None
        return float(res[0]["c"])


async def monitor_loop(interval_sec: int = 20):
    if not API_KEY:
        print("[monitor] POLYGON_API_KEY not set; monitor disabled")
        return
    print(f"[monitor] started (every {interval_sec}s)")
    while True:
        try:
            with SessionLocal() as db:
                await check_trades_once(db)
        except Exception as e:
            print("[monitor] error:", e)
        await asyncio.sleep(interval_sec)


async def check_trades_once(db: Session):
    open_trades = db.execute(select(models.Trade).where(models.Trade.status == "open")).scalars().all()
    for t in open_trades:
        px = await last_price(t.symbol)
        if px is None:
            continue
        plan = t.plan_json or {}
        stop = plan.get("stop")
        tps = plan.get("tp", [])
        hit_tp = (
            next((tp for tp in tps if px >= tp), None)
            if t.side in ("CALL", "LONG")
            else next((tp for tp in tps if px <= tp), None)
        )
        hit_stop = (
            (px <= stop)
            if stop is not None and t.side in ("CALL", "LONG")
            else (px >= stop)
            if stop is not None
            else False
        )

        if hit_tp:
            print(f"[monitor] TP hit for trade {t.id} {t.symbol}: price={px} ≥ tp={hit_tp} — consider trimming/closing")
        if hit_stop:
            print(f"[monitor] STOP hit for trade {t.id} {t.symbol}: price={px} crossed stop={stop} — consider exit")

        # you can auto-close or just log; we log for MVP
        # to auto-close:
        # if hit_stop or hit_tp:
        #     t.status = "closed"
        #     db.add(t); db.commit()
