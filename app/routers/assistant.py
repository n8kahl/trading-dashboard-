from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict

SUPPORTED_OPS = [
    "context.symbol",
    "context.account",
    "market.quote",
    "options.chain",
    "positions.list",
    "coach.guidance",
]

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

@router.get("/actions")
async def assistant_actions():
    return {"ok": True, "ops": SUPPORTED_OPS}

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op")
    args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use one of {SUPPORTED_OPS}")

    # Minimal stub results so API is live while providers are wired.
    if op == "context.symbol":
        sym = (args.get("symbol") or "").upper()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        return {"ok": True, "context": {
            "symbol": sym, "price": None, "vwap": None,
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "confidence": {"score": 50, "band": "mixed", "components": {}},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None, "stale": False
        }}

    if op == "context.account":
        return {"ok": True, "account": {
            "bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3},
            "positions": [], "open_orders": []
        }}

    if op == "market.quote":
        sym = (args.get("symbol") or "").upper()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        return {"ok": True, "quote": {"symbol": sym, "bid": None, "ask": None}}

    if op == "options.chain":
        sym = (args.get("symbol") or "").upper()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        return {"ok": True, "chain": {"symbol": sym, "items": []}}

    if op == "positions.list":
        return {"ok": True, "positions": []}

    if op == "coach.guidance":
        sym = (args.get("symbol") or "").upper()
        hz  = (args.get("horizon") or "intraday").lower()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        if hz not in {"scalp","intraday","swing"}:
            raise HTTPException(status_code=400, detail="args.horizon must be scalp|intraday|swing")
        return {"ok": True, "guidance": {
            "horizon": hz, "band": "mixed",
            "actionable": "If 1m closes above VWAP and spread acceptable, consider starter; else wait.",
            "rationale": ["Placeholder"],
            "if_then": [{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
            "levels": {"entry": None, "stop": None, "targets": []},
            "risk_notes": "Educational guidance only.",
            "confidence_delta": {"score": None, "delta_vs_prev": None}
        }}

    # Fallback safeguard
    raise HTTPException(status_code=500, detail="unhandled op")
