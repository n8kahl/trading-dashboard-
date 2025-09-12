import asyncio
import os
from typing import Any, Dict
from .ws import manager
from app.services import tradier

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
        self.state["breach_concurrent"] = bool(RISK_MAX_CONCURRENT and concurrent > RISK_MAX_CONCURRENT)
        self.state["breach_daily_r"] = bool(RISK_MAX_DAILY_R and self.state["daily_r"] > RISK_MAX_DAILY_R)

    async def loop(self) -> None:
        while True:
            try:
                await self.refresh()
                await manager.broadcast_json({"type": "risk", "state": self.state})
            except Exception:
                pass
            await asyncio.sleep(15)

risk_engine = RiskEngine()

async def start_risk_engine() -> None:
    asyncio.create_task(risk_engine.loop())
