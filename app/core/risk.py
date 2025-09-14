import asyncio
import datetime as dt
import logging
import os
from typing import Any, Dict

from app.services import tradier
# Lazy imports in journaling block to avoid import-time coupling in tests

from .ws import manager

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
        self._last_alerts: Dict[str, bool] = {"daily": False, "concurrent": False}
        self._seen_exec_ids: set[str] = set()

    async def refresh(self) -> None:
        pos = await tradier.get_positions()
        items = pos.get("items", []) if isinstance(pos, dict) else []
        concurrent = len(items)
        self.state["concurrent"] = concurrent
        self.state["breach_concurrent"] = bool(RISK_MAX_CONCURRENT and concurrent > RISK_MAX_CONCURRENT)

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

                    # Best-effort execution journaling (dedupe by order id)
                    # Build a stable dedupe key using id|symbol|time|qty
                    oid = str(tr.get("id") or "")
                    sym = str(tr.get("symbol") or "").upper()
                    ts = tr.get("timestamp") or tr.get("time") or tr.get("date") or ""
                    qty = tr.get("qty") or tr.get("quantity") or ""
                    key = oid or f"{sym}|{ts}|{qty}"
                    if key and key not in self._seen_exec_ids:
                        self._seen_exec_ids.add(key)
                        try:
                            # local import to avoid import errors in test reloads
                            from app.db import db_session  # type: ignore
                            from app.models.misc import JournalEntry  # type: ignore
                            from app.models.execution_seen import ExecutionSeen  # type: ignore

                            with db_session() as s:
                                if s is not None:
                                    # persistent dedupe across restarts
                                    try:
                                        exists = (
                                            s.query(ExecutionSeen)
                                            .filter(ExecutionSeen.key == str(key))
                                            .first()
                                        )
                                        if exists:
                                            raise RuntimeError("dup")
                                        s.add(ExecutionSeen(key=str(key)))
                                        s.commit()
                                    except Exception:
                                        # either exists or insert failed — skip journaling
                                        pass

                                    side = (tr.get("side") or "").lower()
                                    j_side = "long" if side in ("buy", "long") else ("short" if side in ("sell", "short") else None)
                                    notes = f"Execution filled: {side or '?'} {tr.get('qty') or tr.get('quantity') or '?'} {tr.get('symbol') or ''}"
                                    entry = JournalEntry(
                                        symbol=(tr.get("symbol") or "").upper(),
                                        side=j_side,
                                        notes=notes,
                                        meta={"execution": tr},
                                    )
                                    s.add(entry)
                                    s.commit()
                        except Exception:
                            pass
                except Exception:
                    logger.exception("error processing trade record")
        except Exception:
            logger.exception("error fetching trade history")

        self.state["daily_r"] = daily_r
        self.state["breach_daily_r"] = bool(RISK_MAX_DAILY_R and daily_r > RISK_MAX_DAILY_R)

        # Emit alerts on state transitions
        try:
            if self.state["breach_daily_r"] and not self._last_alerts.get("daily"):
                await manager.broadcast_json({
                    "type": "alert",
                    "level": "critical",
                    "msg": f"Daily loss limit breached (R={daily_r:.2f} > {RISK_MAX_DAILY_R})",
                })
                self._last_alerts["daily"] = True
            if not self.state["breach_daily_r"] and self._last_alerts.get("daily"):
                self._last_alerts["daily"] = False

            if self.state["breach_concurrent"] and not self._last_alerts.get("concurrent"):
                await manager.broadcast_json({
                    "type": "alert",
                    "level": "warning",
                    "msg": f"Concurrent positions limit exceeded ({self.state['concurrent']} > {RISK_MAX_CONCURRENT})",
                })
                self._last_alerts["concurrent"] = True
            if not self.state["breach_concurrent"] and self._last_alerts.get("concurrent"):
                self._last_alerts["concurrent"] = False
        except Exception:
            logger.exception("risk alert broadcast failed")

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
