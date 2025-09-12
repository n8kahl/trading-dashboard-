import asyncio
import datetime as dt
import logging
import os
from typing import Any, Dict

from .ws import manager
from app.services import tradier

logger = logging.getLogger(__name__)

RISK_MAX_DAILY_R = float(os.getenv("RISK_MAX_DAILY_R", "0"))
RISK_MAX_CONCURRENT = int(os.getenv("RISK_MAX_CONCURRENT", "0"))

class RiskEngine:
    def __init__(self) -> None:
        self.state: Dict[str, Any] = {
            "daily_r": 0.0,
            "concurrent": 0,
            "breach_daily_r": False,
            "breach_concurrent": False,
        }

    async def refresh(self) -> None:
        pos = await tradier.get_positions()
        items = pos.get("items", []) if isinstance(pos, dict) else []
        concurrent = len(items)
        self.state["concurrent"] = concurrent
        self.state["breach_concurrent"] = bool(
            RISK_MAX_CONCURRENT and concurrent > RISK_MAX_CONCURRENT
        )

        daily_r = 0.0
        try:
            orders = await tradier.get_orders(status="filled")
            trades = orders.get("items", []) if isinstance(orders, dict) else []
            today = dt.date.today()
            for tr in trades:
                try:
                    t = tr.get("timestamp") or tr.get("time") or tr.get("date")
                    if isinstance(t, dt.datetime):
                        trade_day = t.date()
                    elif isinstance(t, str):
                        trade_day = dt.date.fromisoformat(t[:10])
                    else:
                        trade_day = today
                    if trade_day != today:
                        continue
                    r = tr.get("risk_r") or tr.get("r") or tr.get("realized_r") or tr.get("risk")
                    if r is not None:
                        daily_r += float(r)
                except Exception:
                    logger.exception("error processing trade record")
        except Exception:
            logger.exception("error fetching trade history")

        self.state["daily_r"] = daily_r
        self.state["breach_daily_r"] = bool(
            RISK_MAX_DAILY_R and daily_r > RISK_MAX_DAILY_R
        )

    async def loop(self) -> None:
        while True:
            try:
                await self.refresh()
                await manager.broadcast_json({"type": "risk", "state": self.state})
            except Exception:
                logger.exception("risk engine loop error")
            await asyncio.sleep(15)

risk_engine = RiskEngine()

async def start_risk_engine() -> None:
    asyncio.create_task(risk_engine.loop())
