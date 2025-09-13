from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Literal

router = APIRouter(prefix="/api/v1/sizing", tags=["sizing"])

class SizingRequest(BaseModel):
    symbol: str
    side: Literal["long", "short"]
    entry: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)
    # Optional tuning so we don't need broker lookups
    risk_R_dollars: Optional[float] = 100.0
    equity_override: Optional[float] = None
    buying_power_override: Optional[float] = None
    # Options support (kept simple for now)
    asset_class: Optional[Literal["equity", "option"]] = "equity"
    option_contract_price: Optional[float] = None
    option_multiplier: int = 100

@router.post("/suggest")
async def suggest(req: SizingRequest):
    # Basic risk-per-unit
    risk_per = (req.entry - req.stop) if req.side == "long" else (req.stop - req.entry)
    if risk_per <= 0:
        raise HTTPException(status_code=422, detail="For long: stop < entry. For short: stop > entry.")
    risk = req.risk_R_dollars or 100.0

    if req.asset_class == "option":
        # Size by option premium risk (entry/stop are premium values here)
        qty = max(int(risk / risk_per), 1)
        notional = (req.option_contract_price or req.entry) * req.option_multiplier * qty
        return {
            "symbol": req.symbol,
            "side": req.side,
            "asset_class": "option",
            "risk_per_unit": risk_per,
            "risk_R_dollars": risk,
            "qty": qty,
            "notional_estimate": notional,
        }
    else:
        # Equity sizing
        qty = max(int(risk / risk_per), 1)
        notional = req.entry * qty
        return {
            "symbol": req.symbol,
            "side": req.side,
            "asset_class": "equity",
            "risk_per_share": risk_per,
            "risk_R_dollars": risk,
            "qty": qty,
            "notional_estimate": notional,
        }
