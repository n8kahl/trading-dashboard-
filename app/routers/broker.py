from __future__ import annotations
import os
from typing import Optional, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, HTTPException
import httpx

router = APIRouter(prefix="/api/v1/broker/tradier", tags=["broker"])

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com")
TRADIER_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")
TRADIER_ACCOUNT = os.getenv("TRADIER_ACCOUNT_ID")
ENV = os.getenv("ENVIRONMENT", "dev")
SAFE = os.getenv("SAFE_MODE", "1")
TRADIER_ENV = os.getenv("TRADIER_ENV", "sandbox")  # sandbox | live

def can_trade() -> bool:
    # allow in sandbox even if SAFE=1; for live require SAFE=0 & ENV=prod
    if TRADIER_ENV == "sandbox":
        return bool(TRADIER_TOKEN and TRADIER_ACCOUNT)
    return (TRADIER_TOKEN and TRADIER_ACCOUNT and ENV == "prod" and SAFE == "0" and TRADIER_ENV == "live")

class EquityOrderIn(BaseModel):
    symbol: str
    side: Literal["buy","sell"]
    quantity: int = Field(gt=0)
    type: Literal["market","limit"] = "market"
    limit_price: Optional[float] = None
    tif: Literal["day","gtc"] = "day"

class OptionOrderIn(BaseModel):
    option_symbol: str  # OCC sym, e.g., SPY250920C00500000
    side: Literal["buy_to_open","sell_to_close"]
    quantity: int = Field(gt=0)
    type: Literal["market","limit"] = "market"
    limit_price: Optional[float] = None
    tif: Literal["day","gtc"] = "day"

@router.post("/order/equity")
async def place_equity_order(body: EquityOrderIn):
    if not can_trade():
        raise HTTPException(412, detail="Trading disabled by safety policy or missing credentials")
    endpoint = f"{TRADIER_BASE}/v1/accounts/{TRADIER_ACCOUNT}/orders"
    payload = {
        "class": "equity",
        "symbol": body.symbol.upper(),
        "side": body.side,
        "quantity": body.quantity,
        "type": body.type,
        "duration": body.tif
    }
    if body.type == "limit":
        if body.limit_price is None:
            raise HTTPException(422, detail="limit_price required for limit orders")
        payload["price"] = body.limit_price
    headers = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.post(endpoint, data=payload, headers=headers)
    return {"ok": r.status_code in (200,201), "status_code": r.status_code, "body": r.json() if r.headers.get("content-type","").startswith("application/json") else r.text}

@router.post("/order/option")
async def place_option_order(body: OptionOrderIn):
    if not can_trade():
        raise HTTPException(412, detail="Trading disabled by safety policy or missing credentials")
    endpoint = f"{TRADIER_BASE}/v1/accounts/{TRADIER_ACCOUNT}/orders"
    payload = {
        "class": "option",
        "symbol": body.option_symbol.upper(),
        "side": body.side,
        "quantity": body.quantity,
        "type": body.type,
        "duration": body.tif
    }
    if body.type == "limit":
        if body.limit_price is None:
            raise HTTPException(422, detail="limit_price required for limit orders")
        payload["price"] = body.limit_price
    headers = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.post(endpoint, data=payload, headers=headers)
    return {"ok": r.status_code in (200,201), "status_code": r.status_code, "body": r.json() if r.headers.get("content-type","").startswith("application/json") else r.text}
