from fastapi import APIRouter

from app.core.risk import risk_engine
from app.services import tradier

router = APIRouter(prefix="/stream", tags=["stream"])


@router.get("/state")
async def stream_state():
    pos = await tradier.get_positions()
    ords = await tradier.get_orders()
    return {
        "ok": True,
        "positions": pos.get("items", []),
        "orders": ords.get("items", []),
        "risk": risk_engine.state,
    }


@router.get("/risk/state")
async def risk_state():
    return {"ok": True, "state": risk_engine.state}
