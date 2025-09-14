from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from datetime import datetime, timedelta

from app.services.providers.polygon_market import PolygonMarket
from app.services.providers.tradier import TradierMarket
from app.services.indicators import (
    ema, sma, rsi, macd, atr14,
    session_vwap_and_sigma, pivots_classic, rvol_5min, spread_stability
)

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
SUPPORTED_OPS = ["data.snapshot"]

@router.get("/actions")
async def assistant_actions():
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

def _conf_score(features: Dict[str, Any], horizon: str) -> Dict[str, Any]:
    score = 50
    details = []
    if features.get("ema_stack_ok"):
        score += 20; details.append("EMA stack (1>5>9) & price≥VWAP")
    if features.get("vwap_plus1_reclaim"):
        score += 10; details.append("VWAP+1σ reclaim")
    rv = features.get("rvol_ok")
    if rv:
        score += 5; details.append(f"RVOL_5 {rv}")
    if features.get("rsi_mid"):
        score += 5; details.append(f"RSI14 ~ {features.get('rsi_val')}")
    if features.get("macd_up"):
        score += 5; details.append("MACD hist rising")
    if features.get("contract_ema_up"):
        score += 5; details.append("Contract EMA1>EMA5")
    if features.get("spread_stable"):
        score += 3; details.append("Spread stability ok")
    if features.get("spread_bad"):
        score -= 10; details.append("Spread too wide")
    score = max(0, min(100, score))
    return {"score": score, "details": details}

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
    tradier = TradierMarket()
    snapshot: Dict[str, Any] = {"symbols": {}, "account": {}, "errors": {}}

    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str, Any] = {}
        errs: Dict[str, Any] = {}

        # ---------- PRICE (Tradier first, then Polygon fallback) ----------
        last_price = None; last_t = None
        try:
            tq = await tradier.quote_last(symU)
            last_price, last_t = tq.get("price"), tq.get("t")
        except Exception as e:
            errs["price.tradier"] = f"{type(e).__name__}: {e}"

        if last_price is None:
            try:
                lt = await poly.last_trade(symU)
                last_price, last_t = lt.get("price"), lt.get("t")
            except Exception as e:
                errs["price.polygon"] = f"{type(e).__name__}: {e}"

        out["price"] = {"last": last_price, "t": last_t}

        # ---------- HISTORY / INDICATORS / LEVELS / MICRO / OPTIONS ----------
        # (Keep your current logic here — unchanged)
        # ... your existing code that computes minute/5m/day bars, VWAP ± σ, pivots, rvol, options.top, confidence, etc.

        snapshot["symbols"][symU] = out
        if errs:
            snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
