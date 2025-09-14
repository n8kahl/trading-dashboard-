from fastapi import APIRouter

from app.core.risk import risk_engine
from app.services import tradier
from app.services.stream import STREAM

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/state")
async def stream_state():
    pos = await tradier.get_positions()
    ords = await tradier.get_orders()
    # derive last price per watched symbol from recent snapshot (if running)
    prices = {}
    try:
        snap = await STREAM.snapshot(1)
        for sym, bars in (snap or {}).items():
            if bars:
                prices[sym] = bars[-1].get("c")
    except Exception:
        prices = {}
    status = await STREAM.status()
    return {
        "ok": True,
        "positions": pos.get("items", []),
        "orders": ords.get("items", []),
        "risk": risk_engine.state,
        "prices": prices,
        "stream": status,
    }


@router.get("/risk/state")
async def risk_state():
    return {"ok": True, "state": risk_engine.state}
