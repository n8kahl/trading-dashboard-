from fastapi import APIRouter, Body

from app.core.ws import manager
from app.services import tradier

router = APIRouter(prefix="/broker", tags=["broker"])


@router.get("/positions")
async def get_positions():
    return await tradier.get_positions()


@router.get("/orders")
async def get_orders():
    return await tradier.get_orders()


@router.post("/orders/submit")
async def submit_order(body: dict = Body(...)):
    res = await tradier.submit_order(
        body.get("symbol"),
        body.get("side"),
        int(body.get("qty", 0)),
        body.get("order_type"),
        body.get("limit_price"),
        body.get("stop_price"),
    )
    if res.get("ok"):
        pos = await tradier.get_positions()
        ords = await tradier.get_orders()
        await manager.broadcast_json({"type": "positions", "items": pos.get("items", [])})
        await manager.broadcast_json({"type": "orders", "items": ords.get("items", [])})
        await manager.broadcast_json({
            "type": "alert",
            "level": "info",
            "msg": f"Order submitted: {body.get('side')} {body.get('qty')} {body.get('symbol')} ({body.get('order_type')})",
        })
    return res


@router.post("/orders/cancel")
async def cancel_order(body: dict = Body(...)):
    res = await tradier.cancel_order(body.get("order_id"))
    if res.get("ok"):
        ords = await tradier.get_orders()
        await manager.broadcast_json({"type": "orders", "items": ords.get("items", [])})
    return res


@router.post("/webhook")
async def broker_webhook(body: dict = Body(...)):
    # For now we simply log and acknowledge
    print("broker webhook", body)
    return {"ok": True}
