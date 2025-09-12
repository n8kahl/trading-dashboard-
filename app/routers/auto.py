from fastapi import APIRouter, Body
from app.services import tradier
from app.core.risk import risk_engine
from app.core.ws import manager

router = APIRouter(prefix="/auto", tags=["auto"])

@router.post("/execute")
async def auto_execute(body: dict = Body(...)):
    confirm = body.get("confirm", False)
    symbol = body.get("symbol")
    side = body.get("side")
    entry = body.get("entry")
    stop = body.get("stop")
    risk_r = body.get("risk_R", 1)

    if risk_engine.state.get("breach_concurrent") or risk_engine.state.get("breach_daily_r"):
        await manager.broadcast_json({"type": "alert", "level": "danger", "msg": "risk_blocked"})
        return {"ok": False, "error": "risk_blocked", "state": risk_engine.state}

    size = 1  # placeholder sizing
    review = {"symbol": symbol, "side": side, "qty": size, "entry": entry, "stop": stop, "risk_R": risk_r}
    if not confirm:
        return {"ok": True, "pending": True, "review": review}

    res = await tradier.submit_order(symbol, side, size, "market")
    if res.get("ok"):
        ords = await tradier.get_orders()
        await manager.broadcast_json({"type": "orders", "items": ords.get("items", [])})
        await manager.broadcast_json({"type": "alert", "level": "info", "msg": f"Order submitted for {symbol}"})
    return res
