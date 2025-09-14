from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from typing import Any, Dict

from app.security import require_api_key
from app.services.providers.polygon import PolygonClient
from app.services.providers.tradier import TradierClient

SUPPORTED_OPS = [
    "context.symbol",
    "context.account",
    "market.quote",
    "options.chain",
    "positions.list",
    "coach.guidance",
]

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

@router.get("/actions", dependencies=[Depends(require_api_key)])
async def assistant_actions():
    return {"ok": True, "ops": SUPPORTED_OPS}

@router.post("/exec", dependencies=[Depends(require_api_key)])
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op")
    args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(400, f"Unsupported op '{op}'. Use one of {SUPPORTED_OPS}")

    poly = PolygonClient()
    trad = TradierClient()

    if op == "market.quote":
        sym = (args.get("symbol") or "").upper()
        if not sym: raise HTTPException(400, "args.symbol required")
        return {"ok": True, "quote": await poly.last_quote(sym)}

    if op == "context.symbol":
        sym = (args.get("symbol") or "").upper()
        if not sym: raise HTTPException(400, "args.symbol required")
        snap = await poly.snapshot_stock(sym)
        ctx = {
            "symbol": snap.get("symbol") or sym,
            "t_ms": (snap.get("min") or {}).get("t") or (snap.get("day") or {}).get("t"),
            "price": snap.get("price"),
            "vwap": (snap.get("day") or {}).get("vw") or None,
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "confidence": {"score": 50, "band": "mixed", "components": {}},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        return {"ok": True, "context": ctx}

    if op == "context.account":
        bal = await trad.account_balances()
        pos = await trad.positions()
        positions = []
        raw = (pos.get("positions") or {})
        p = raw.get("position")
        if p:
            iterable = p if isinstance(p, list) else [p]
            for item in iterable:
                try:
                    positions.append({
                        "symbol": item.get("symbol"),
                        "side": "long" if float(item.get("quantity", 0) or 0) >= 0 else "short",
                        "qty": float(item.get("quantity") or 0),
                        "avg": float(item.get("cost_basis") or 0),
                        "upnl_r": None, "stop": None, "targets": []
                    })
                except Exception:
                    continue
        out = {
            "bp": (bal.get("balances") or {}).get("cash_available", None),
            "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3},
            "positions": positions,
            "open_orders": []
        }
        return {"ok": True, "account": out}

    if op == "positions.list":
        pos = await trad.positions()
        return {"ok": True, "raw": pos}

    if op == "options.chain":
        sym = (args.get("symbol") or "").upper()
        expiry = args.get("expiry")
        if not sym: raise HTTPException(400, "args.symbol required")
        chain = await poly.options_chain_light(sym, expiry)
        return {"ok": True, "chain": chain}

    if op == "coach.guidance":
        sym = (args.get("symbol") or "").upper()
        hz  = (args.get("horizon") or "intraday").lower()
        if not sym: raise HTTPException(400, "args.symbol required")
        if hz not in {"scalp","intraday","swing"}:
            raise HTTPException(400, "args.horizon must be scalp|intraday|swing")
        # Minimal placeholder guidance; server can call ChatData LLM later
        guidance = {
            "horizon": hz, "band": "mixed",
            "actionable": "If 1m closes above VWAP and spread acceptable, consider starter; else wait.",
            "rationale": ["Placeholder"],
            "if_then": [{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
            "levels": {"entry": None, "stop": None, "targets": []},
            "risk_notes": "Educational guidance only.",
            "confidence_delta": {"score": None, "delta_vs_prev": None}
        }
        return {"ok": True, "guidance": guidance}

    raise HTTPException(500, "unhandled op")
