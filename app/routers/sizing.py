from __future__ import annotations

from math import floor
from typing import Any, Dict, Literal, Optional

from fastapi import APIRouter
from fastapi.responses import JSONResponse
import os, HTTPException

def _tradier_env():
    try:
        from app.services import tradier_client as _tc
        val = getattr(_tc, 'TRADIER_ENV', None)
    except Exception:
        val = None
    import os as _os
    return (val or _os.getenv('TRADIER_ENV') or _os.getenv('TRADIER_MODE') or 'prod')

from pydantic import BaseModel, Field

from app.services import tradier_client as tc

router = APIRouter(prefix="/sizing", tags=["sizing"])


class SizingRequest(BaseModel):
    symbol: str
    side: Literal["long", "short"]
    entry: float = Field(..., gt=0)
    stop: float = Field(..., gt=0)

    # Risk budgeting
    risk_R_dollars: Optional[float] = None  # flat $ risk per trade (overrides pct if provided)
    risk_pct_of_equity: Optional[float] = 0.005  # default 0.5% if equity known
    min_risk_dollars_if_unknown: float = 100.0  # fallback if balances unavailable

    # Notional guard (cap % of buying power)
    notional_cap_pct_of_bp: Optional[float] = 0.33
    min_qty: int = 1

    # Asset class
    asset_class: Literal["equity", "option"] = "equity"
    option_contract_price: Optional[float] = None
    option_multiplier: int = 100

    # Optional overrides (useful in sandbox or if Tradier balances lag)
    equity_override: Optional[float] = None
    buying_power_override: Optional[float] = None


class SizingResponse(BaseModel):
    ok: bool
    env: str
    note: Optional[str] = None
    account_snapshot: Dict[str, Any]
    risk_budget_R: float
    per_unit_risk: float
    quantity: int
    notional_estimate: float
    checks: Dict[str, Any]


@router.post("/suggest", response_model=SizingResponse)
async def suggest(body: SizingRequest) -> SizingResponse:
    try:
        # 1) per-unit risk
    per_unit_risk = abs(body.entry - body.stop)
    if per_unit_risk <= 0:
        raise HTTPException(status_code=400, detail="entry and stop must differ")

    # 2) balances
    balances: Dict[str, Any] = {}
    note_parts = []
    try:
        balances = await tc.account_balances()
    except Exception as e:
        note_parts.append(f"balances unavailable: {e}")

    # Extract with overrides
    equity = (body.equity_override if body.equity_override is not None else None) or (
        balances.get("total_equity") or balances.get("account_value") or 0.0
    )
    buying_power = (body.buying_power_override if body.buying_power_override is not None else None) or (
        balances.get("buying_power") or balances.get("day_trading_buying_power") or 0.0
    )
    try:
        equity = float(equity)
    except Exception:
        equity = 0.0
    try:
        buying_power = float(buying_power)
    except Exception:
        buying_power = 0.0

    # 3) risk budget logic (flat $ risk takes precedence)
    if body.risk_R_dollars is not None and body.risk_R_dollars > 0:
        risk_budget = float(body.risk_R_dollars)
        note_parts.append("risk budget: using flat dollars (risk_R_dollars)")
    else:
        # if equity is known and > 0, use % of equity; else use fallback dollars
        if equity > 0 and (body.risk_pct_of_equity or 0) > 0:
            risk_budget = (body.risk_pct_of_equity or 0.0) * equity
            note_parts.append("risk budget: pct of equity")
        else:
            risk_budget = max(body.min_risk_dollars_if_unknown, 1.0)
            note_parts.append("risk budget: fallback (balances unknown)")

    # 4) sizing calc
    if body.asset_class == "equity":
        qty_risk = floor(risk_budget / max(per_unit_risk, 1e-9))
        # apply notional cap if buying power available
        if buying_power > 0 and (body.notional_cap_pct_of_bp or 0) > 0:
            notional_cap = (body.notional_cap_pct_of_bp or 0.0) * buying_power
            qty_notional = floor(notional_cap / max(body.entry, 1e-9))
            qty = max(body.min_qty, min(qty_risk, qty_notional))
            note_parts.append("notional cap applied")
        else:
            qty = max(body.min_qty, qty_risk)
            note_parts.append("no notional cap (buying power unknown)")
        notional = qty * body.entry

    else:
        # options: need contract price
        if not body.option_contract_price or body.option_contract_price <= 0:
            raise HTTPException(status_code=400, detail="option_contract_price required for option sizing")
        per_contract_risk = body.option_contract_price * body.option_multiplier
        qty_risk = floor(risk_budget / max(per_contract_risk, 1e-9))
        if buying_power > 0 and (body.notional_cap_pct_of_bp or 0) > 0:
            notional_cap = (body.notional_cap_pct_of_bp or 0.0) * buying_power
            qty_notional = floor(notional_cap / max(per_contract_risk, 1e-9))
            qty = max(body.min_qty, min(qty_risk, qty_notional))
            note_parts.append("notional cap applied")
        else:
            qty = max(body.min_qty, qty_risk)
            note_parts.append("no notional cap (buying power unknown)")
        notional = qty * per_contract_risk
    if _tradier_env().lower().startswith('sand'):
        note_parts.append("Sandbox data delayed ~15m; balances/quotes may be stale")

    return SizingResponse(
    except Exception as e:
        import logging, traceback
        logging.exception('sizing.suggest failed')
        return JSONResponse(status_code=422, content={'error': str(e)})
        ok=True,
        env=_tradier_env(),
        note="; ".join(note_parts) or None,
        account_snapshot=balances,
        risk_budget_R=risk_budget,
        per_unit_risk=per_unit_risk,
        quantity=qty,
        notional_estimate=notional,
        checks={
            "equity": equity,
            "buying_power": buying_power,
            "qty_risk_limited": qty_risk,
        },
    )
