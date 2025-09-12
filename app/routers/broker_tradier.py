from fastapi import APIRouter, HTTPException
import httpx

from app.core.settings import settings
from app.services.tradier_trading import (
    StrategyOrder,
    place_order as tradier_place_order,
)

router = APIRouter(prefix="/broker/tradier", tags=["broker-tradier"])

def _headers():
    token = settings.TRADIER_ACCESS_TOKEN
    if not token:
        raise HTTPException(status_code=500, detail="TRADIER_ACCESS_TOKEN not set")
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "User-Agent": "trading-assistant/1.0"
    }

@router.get("/account")
async def account_overview():
    """
    Returns balances + positions for sizing guidance.
    """
    if not settings.TRADIER_ACCOUNT_ID:
        raise HTTPException(status_code=500, detail="TRADIER_ACCOUNT_ID not set")

    async with httpx.AsyncClient(timeout=15.0) as client:
        # Balances
        bal_url = f"{settings.tradier_base_url}/v1/accounts/{settings.TRADIER_ACCOUNT_ID}/balances"
        r1 = await client.get(bal_url, headers=_headers())
        if r1.status_code >= 300:
            raise HTTPException(status_code=r1.status_code, detail=f"Tradier balances error: {r1.text}")
        balances = r1.json().get("balances", {})

        # Positions (ok if empty)
        pos_url = f"{settings.tradier_base_url}/v1/accounts/{settings.TRADIER_ACCOUNT_ID}/positions"
        r2 = await client.get(pos_url, headers=_headers())
        if r2.status_code >= 300:
            # Some sandbox/envs have no positions API — don’t fail the whole call
            positions = {"warning": f"positions fetch returned {r2.status_code}", "raw": r2.text}
        else:
            positions = r2.json().get("positions", {})

        # Buying power is in balances; pick common fields
        sizing = {
            "cash": balances.get("cash"),
            "equity": balances.get("equity"),
            "market_value": balances.get("market_value"),
            "buying_power": balances.get("buying_power"),
            "maintenance_margin": balances.get("maintenance_requirement"),
            "day_trade_buying_power": balances.get("day_trade_buying_power"),
        }

        return {
            "ok": True,
            "env": "sandbox" if "sandbox" in settings.tradier_base_url else "live",
            "account_id": settings.TRADIER_ACCOUNT_ID,
            "sizing": sizing,
            "positions": positions,
            "raw": {"balances": balances}  # keep full balances for now (easy debugging)
        }


class OrderRequest(StrategyOrder):
    preview: bool = True


@router.post("/order")
async def place_order_endpoint(req: OrderRequest):
    """Place or preview an order via Tradier sandbox."""
    try:
        order = StrategyOrder.model_validate(req.model_dump())
        res = await tradier_place_order(order, preview=req.preview)
        return {"ok": True, "preview": req.preview, "result": res}
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:  # pragma: no cover - unexpected
        raise HTTPException(status_code=500, detail=str(e))
