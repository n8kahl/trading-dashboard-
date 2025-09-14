from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from datetime import datetime, timedelta

from app.services.providers.polygon_market import PolygonMarket
from app.services.indicators import (
    ema, sma, rsi, macd, atr14,
    session_vwap_and_sigma, pivots_classic, rvol_5min, spread_stability
)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
SUPPORTED_OPS = ["data.snapshot"]

@router.get("/actions")
async def assistant_actions():
    # Do NOT touch any providers here; just return static ops
    return {"ok": True, "ops": SUPPORTED_OPS}

def _auto_expiry(hz: str) -> str:
    today = datetime.utcnow().date()
    if hz in ("scalp","intraday"):
        days = (4 - today.weekday()) % 7 or 7
        return str(today + timedelta(days=days))
    return str(today + timedelta(days=14))

def _normalize_expiry(raw, hz: str) -> str:
    if raw is None: return _auto_expiry(hz)
    if isinstance(raw, bool) and raw: return _auto_expiry(hz)
    if isinstance(raw, str) and raw.strip().lower() == "auto": return _auto_expiry(hz)
    return str(raw)

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op"); args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use {SUPPORTED_OPS}")

    symbols: List[str] = args.get("symbols") or []
    if not symbols:
        raise HTTPException(status_code=400, detail="args.symbols (array) required")
    horizon: str = (args.get("horizon") or "intraday").lower()
    include = set(args.get("include") or ["price","history","indicators","levels","micro","options","account","market"])

    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    lookback = int(hist_spec.get("lookback") or (30 if bars_kind=="1m" else 90 if bars_kind=="5m" else 120))

    opt_spec = args.get("options") or {}
    expiry = _normalize_expiry(opt_spec.get("expiry"), horizon)
    topK = int(opt_spec.get("topK") or 6)
    max_spread = float(opt_spec.get("maxSpreadPct") or 8.0)

    poly = PolygonMarket()
    snapshot: Dict[str, Any] = {"symbols": {}, "account": {}, "errors": {}}

    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str, Any] = {}
        errs: Dict[str, Any] = {}

        # PRICE
        try:
            lt = await poly.last_trade(symU)
            out["price"] = {"last": lt.get("price"), "t": lt.get("t")}
        except Exception as e:
            out["price"] = {"last": None, "t": None}
            errs["price.last_trade"] = f"{type(e).__name__}: {e}"

        # HISTORY + INDICATORS + LEVELS + MICRO (same as before; omitted here for brevity)
        # NOTE: keep your working version that computes ema stack, vwap±σ, pivots, rvol, etc.

        snapshot["symbols"][symU] = out
        if errs: snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
