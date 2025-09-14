from __future__ import annotations
from fastapi import APIRouter, Depends, HTTPException
from app.security import require_api_key
from typing import Any, Dict

from app.services.providers.polygon import PolygonClient
from app.services.providers.tradier import TradierClient
from app.services.strategy import score_band, default_levels
from app.services.llm import chatdata_guidance

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

SUPPORTED_OPS = [
    "context.symbol",
    "context.account",
    "market.quote",
    "options.chain",
    "positions.list",
    "coach.guidance",   # guidance via exec (keeps API surface small)
]

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
        # Compose a minimal, LLM-friendly context (expand with EMA/VWAP from your pipeline as desired)
        ctx = {
            "symbol": snap.get("symbol") or sym,
            "t_ms": (snap.get("min") or {}).get("t") or (snap.get("day") or {}).get("t"),
            "price": snap.get("price"),
            "vwap": (snap.get("day") or {}).get("vw") or None,
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "confidence": {},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        score, band = score_band(ctx)
        ctx["confidence"] = {
            "score": score, "band": band,
            "components": {"atr": None, "vwap": None, "ema": None, "flow": None, "liq": None, "vol": None}
        }
        return {"ok": True, "context": ctx}

    if op == "context.account":
        bal = await trad.account_balances()
        pos = await trad.positions()
        positions = []
        # Normalize Tradier positions if present
        for p in (pos.get("positions") or {}).get("position", []) if isinstance((pos.get("positions") or {}).get("position", []), list) else ([] if not (pos.get("positions") or {}).get("position") else [(pos.get("positions") or {}).get("position")]):
            try:
                positions.append({
                    "symbol": p.get("symbol"),
                    "side": "long" if (p.get("quantity", 0) or 0) >= 0 else "short",
                    "qty": float(p.get("quantity") or 0),
                    "avg": float(p.get("cost_basis") or 0),
                    "upnl_r": None,
                    "stop": None,
                    "targets": []
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
        chain = await PolygonClient().options_chain_light(sym, expiry)
        return {"ok": True, "chain": chain}

    if op == "coach.guidance":
        # Build a compact situation by reusing context.symbol + optional account snippets
        sym = (args.get("symbol") or "").upper()
        horizon = (args.get("horizon") or "intraday").lower()
        if not sym: raise HTTPException(400, "args.symbol required")
        if horizon not in {"scalp","intraday","swing"}:
            raise HTTPException(400, "args.horizon must be scalp|intraday|swing")

        # Reuse the same internal composition used by context.symbol
        snap = await poly.snapshot_stock(sym)
        ctx = {
            "symbol": sym,
            "t_ms": (snap.get("min") or {}).get("t") or (snap.get("day") or {}).get("t"),
            "price": snap.get("price"),
            "vwap": (snap.get("day") or {}).get("vw") or None,
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        score, band = score_band(ctx)
        ctx["confidence"] = {"score": score, "band": band, "components": {}}

        # Provide default numeric levels so LLM doesn't invent numbers
        levels = default_levels(ctx.get("price"), horizon)
        situation = ctx | {"horizon": horizon, "precalc_levels": levels}

        guidance = await chatdata_guidance(situation)
        return {"ok": True, "guidance": guidance}

    raise HTTPException(500, "unhandled op")
