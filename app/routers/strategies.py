from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.services.intraday import score_intraday
from app.services.coach import explain

router = APIRouter(prefix="/strategies", tags=["strategies"])

class EvalRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g., AAPL")
    minutes_back: Optional[int] = Field(450, ge=60, le=2000)

@router.post("/evaluate")
async def evaluate(req: EvalRequest) -> Dict[str, Any]:
    try:
        res = await score_intraday(req.symbol.upper(), minutes_back=req.minutes_back or 450)
        if not isinstance(res, dict):
            raise HTTPException(status_code=500, detail="invalid_evaluation_payload")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"evaluation_error: {e}")

class PlanRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g., AAPL")
    minutes_back: Optional[int] = Field(450, ge=60, le=2000)

@router.post("/plan")
async def plan(req: PlanRequest) -> Dict[str, Any]:
    try:
        res = await score_intraday(req.symbol.upper(), minutes_back=req.minutes_back or 450)
        if not isinstance(res, dict):
            raise HTTPException(status_code=500, detail="invalid_plan_payload")
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"plan_error: {e}")

class ExplainRequest(BaseModel):
    symbol: str = Field(..., description="Ticker symbol, e.g., AAPL")
    minutes_back: Optional[int] = Field(450, ge=60, le=2000)

@router.post("/explain")
async def explain_view(req: ExplainRequest) -> Dict[str, Any]:
    """
    Returns a coaching narrative for the current evaluation:
    human-readable reasons for pass/fail, and next steps to make it actionable.
    """
    try:
        ev = await score_intraday(req.symbol.upper(), minutes_back=req.minutes_back or 450)
        if not ev.get("ok"):
            return {"ok": False, "summary": f"Data error: {ev.get('error') or 'unavailable'}", "raw": ev}
        return explain(ev) | {"raw": {"symbol": ev.get("symbol"), "decision": ev.get("decision"), "gates": ev.get("gates")}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"explain_error: {e}")
\n

from app.config.policy import POLICY

@router.get("/policy")
def get_policy():
    # return a JSON-serializable view of gate thresholds
    return {
        "session_windows_et": POLICY.session_windows_et,
        "equities": vars(POLICY.equities),
        "options": vars(POLICY.options),
        "risk": vars(POLICY.risk),
        "entry": vars(POLICY.entry),
    }
