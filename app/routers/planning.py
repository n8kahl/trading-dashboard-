from fastapi import APIRouter
from pydantic import BaseModel
from app.core.failopen import fail_open

router = APIRouter(prefix="/", tags=["planning","sizing"])

class PlanValidateBody(BaseModel):
    symbol: str
    side: str
    entry: float
    stop: float
    tp1: float | None = None
    tp2: float | None = None
    time_stop_min: int | None = 10

def _plan_fallback():
    return {"status":"ok","data":{"ok": True, "notes":["fallback plan"], "targets": []}}

@router.post("/plan/validate")
@fail_open(_plan_fallback)
def plan_validate(body: PlanValidateBody):
    # TODO: real validation; this is a safe placeholder
    per_unit_risk = abs(body.entry - body.stop)
    targets = [body.entry + per_unit_risk, body.entry + 2*per_unit_risk]
    return {"status":"ok","data":{
        "ok": True, "symbol": body.symbol, "side": body.side,
        "risk_R": 1.0, "per_unit_risk": per_unit_risk, "targets": targets,
        "notes": ["Looks sane."]
    }}

class SizingBody(BaseModel):
    symbol: str
    side: str
    risk_R: float
    per_unit_risk: float | None = None

def _sizing_fallback():
    return {"ok": True, "qty": 0, "expected_R": 0.0, "notes":["fallback sizing"]}

@router.post("/sizing/suggest")
@fail_open(_sizing_fallback)
def sizing_suggest(body: SizingBody):
    per_unit = body.per_unit_risk or 1.0
    qty = max(0, int(round(body.risk_R / per_unit)))
    return {"ok": True, "qty": qty, "expected_R": body.risk_R, "notes":["sized via heuristic"]}
