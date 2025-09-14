from __future__ import annotations

import time
from typing import Any, Dict, Optional

from app.core.risk import risk_engine
from app.services.providers import get_last_price


async def build_situation(symbol: str, position_id: Optional[str] = None) -> Dict[str, Any]:
    """Assemble a compact situation snapshot for the narrator.

    Includes: t_ms, symbol, price, risk snapshot, position_id (optional),
    data staleness (placeholder), and simple pace indicator (placeholder).
    """
    t_ms = int(time.time() * 1000)
    price = await get_last_price(symbol)
    risk = dict(risk_engine.state or {})
    situation: Dict[str, Any] = {
        "t_ms": t_ms,
        "symbol": symbol.upper(),
        "price": price,
        "risk": {
            "daily_r": risk.get("daily_r"),
            "concurrent": risk.get("concurrent"),
            "breach_daily_r": risk.get("breach_daily_r"),
            "breach_concurrent": risk.get("breach_concurrent"),
        },
        "pace": "steady",  # TODO: derive from recent tick interval/volume
        "staleness_ms": 0,  # TODO: track last tick timestamp
    }
    if position_id:
        situation["position_id"] = str(position_id)
    return situation

