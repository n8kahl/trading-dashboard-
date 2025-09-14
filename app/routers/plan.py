from typing import List, Literal, Optional

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field, ValidationError

router = APIRouter(prefix="/plan", tags=["plan"])


# ---- Models ----
class Plan(BaseModel):
    entry: float = Field(..., description="Proposed entry price")
    stop: float = Field(..., description="Proposed stop price")
    tp1: Optional[float] = Field(None, description="Take-profit 1")
    tp2: Optional[float] = Field(None, description="Take-profit 2")


class ValidateRequest(BaseModel):
    symbol: str
    side: Literal["long", "short", "CALL", "PUT", "LONG", "SHORT"]
    risk_R: float = 1.0
    # either nested plan or flattened fields:
    plan: Optional[Plan] = None
    entry: Optional[float] = None
    stop: Optional[float] = None
    tp1: Optional[float] = None
    tp2: Optional[float] = None


class ValidateResponse(BaseModel):
    ok: bool
    symbol: str
    side: str
    risk_R: float
    per_unit_risk: float
    rr_bands: List[float]
    targets: List[float]
    notes: List[str]
    summary: str


def _coerce_plan(req: ValidateRequest) -> Plan:
    """Allow both nested plan and flattened fields."""
    if req.plan:
        return req.plan
    if req.entry is None or req.stop is None:
        raise ValueError("entry and stop are required (either in plan{} or flattened).")
    return Plan(entry=req.entry, stop=req.stop, tp1=req.tp1, tp2=req.tp2)


def _validate_sanity(side: str, entry: float, stop: float) -> List[str]:
    side_l = side.lower()
    notes = []
    if side_l in ("long", "call"):
        if stop >= entry:
            notes.append("For LONG/CALL, stop should be below entry.")
    elif side_l in ("short", "put"):
        if stop <= entry:
            notes.append("For SHORT/PUT, stop should be above entry.")
    else:
        notes.append("Unknown side; expected long/short or CALL/PUT.")
    return notes


@router.post("/validate")
async def validate_plan(payload: dict = Body(...)):
    # Always return a JSON envelope; never raise to the client
    try:
        req = ValidateRequest(**payload)
        plan = _coerce_plan(req)

        side_l = req.side.lower()
        # basic per-unit risk (in price units)
        per_unit = abs(plan.entry - plan.stop)

        # default TPs if not provided (1R / 2R)
        if plan.tp1 is None or plan.tp2 is None:
            if side_l in ("long", "call"):
                tp1 = plan.entry + 1.0 * per_unit
                tp2 = plan.entry + 2.0 * per_unit
            else:
                tp1 = plan.entry - 1.0 * per_unit
                tp2 = plan.entry - 2.0 * per_unit
        else:
            tp1, tp2 = plan.tp1, plan.tp2

        notes = _validate_sanity(req.side, plan.entry, plan.stop)

        # RR bands (0.5R, 1R, 2R)
        rr_bands = [round(0.5 * per_unit, 6), round(1.0 * per_unit, 6), round(2.0 * per_unit, 6)]

        # NL summary
        direction = "LONG/CALL" if side_l in ("long", "call") else "SHORT/PUT"
        summary = (
            f"{req.symbol.upper()} {direction}: entry {plan.entry:.4f}, stop {plan.stop:.4f} (risk {per_unit:.4f}/unit). "
            f"Targets ~ {tp1:.4f} / {tp2:.4f} ({'+' if side_l in ('long','call') else '-'}1R / {'+' if side_l in ('long','call') else '-'}2R)."
        )

        return {
            "status": "ok",
            "data": ValidateResponse(
                ok=(len(notes) == 0),
                symbol=req.symbol,
                side=req.side,
                risk_R=req.risk_R,
                per_unit_risk=per_unit,
                rr_bands=rr_bands,
                targets=[tp1, tp2],
                notes=notes or ["Looks sane."],
                summary=summary,
            ).model_dump(),
        }
    except ValidationError as ve:
        return {"status": "error", "error": "validation_error", "data": ve.errors()}
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "data": {
                "hint": "Ensure body contains symbol, side, and (entry & stop) either nested in plan{} or flattened."
            },
        }
