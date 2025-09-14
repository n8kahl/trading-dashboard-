from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Tuple

# Providers
from app.services.providers.polygon import PolygonClient
from app.services.providers.tradier import TradierClient
# LLM (ChatData). If creds missing, this safely falls back.
try:
    from app.services.llm import chatdata_guidance
except Exception:  # pragma: no cover
    async def chatdata_guidance(situation: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "horizon": situation.get("horizon","intraday"),
            "band": "mixed",
            "actionable": "If 1m closes above VWAP and spread acceptable, consider starter; else wait.",
            "rationale": ["LLM offline fallback"],
            "if_then": [{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
            "levels": {"entry": situation.get("precalc_levels",{}).get("entry"),
                       "stop":  situation.get("precalc_levels",{}).get("stop"),
                       "targets": situation.get("precalc_levels",{}).get("targets",[])},
            "risk_notes": "Educational guidance only.",
            "confidence_delta": {"score": None, "delta_vs_prev": None}
        }

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

SUPPORTED_OPS = [
    "context.symbol",
    "context.account",
    "market.quote",
    "options.chain",
    "positions.list",
    "coach.guidance",
]

@router.get("/actions")
async def assistant_actions():
    return {"ok": True, "ops": SUPPORTED_OPS}

def _score_band(ctx: Dict[str, Any]) -> Tuple[int,str]:
    """Tiny, explainable score from available fields."""
    score = 50
    price = ctx.get("price")
    vwap  = ctx.get("vwap")
    ema   = ctx.get("ema") or {}
    flow  = ctx.get("flow") or {}
    # EMA posture
    e9, e20 = ema.get("ema9"), ema.get("ema20")
    if e9 is not None and e20 is not None:
        score += 10 if e9 > e20 else -10
    # VWAP posture
    if price is not None and vwap is not None:
        score += 10 if price >= vwap else -10
    # RVOL
    rvol = flow.get("rvol")
    if isinstance(rvol,(int,float)):
        score += 10 if rvol >= 1.5 else (-10 if rvol < 0.8 else 0)
    score = max(0, min(100, score))
    band = "favorable" if score >= 66 else "unfavorable" if score <= 34 else "mixed"
    return score, band

def _default_levels(price: float|None, horizon: str) -> Dict[str,Any]:
    if price is None:
        return {"entry": None, "stop": None, "targets": []}
    tick = 0.3 if horizon=="scalp" else 0.8 if horizon=="intraday" else 2.0
    entry = round(price, 2)
    stop  = round(price - tick, 2)
    targets = [round(price + tick, 2), round(price + 2*tick, 2)]
    return {"entry": entry, "stop": stop, "targets": targets}

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op")
    args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use one of {SUPPORTED_OPS}")

    poly = PolygonClient()
    trad = TradierClient()

    if op == "market.quote":
        sym = (args.get("symbol") or "").upper()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            return {"ok": True, "quote": await poly.last_quote(sym)}
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"quote error: {e}")

    if op == "context.symbol":
        sym = (args.get("symbol") or "").upper()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            snap = await poly.snapshot_stock(sym)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon snapshot error: {e}")

        ctx = {
            "symbol": snap.get("symbol") or sym,
            "t_ms": (snap.get("min") or {}).get("t") or (snap.get("day") or {}).get("t"),
            "price": snap.get("price"),
            # Polygon snapshot exposes day.vw (volume-weighted avg price for the day)
            "vwap": (snap.get("day") or {}).get("vw"),
            "ema": {"ema9": None, "ema20": None},  # compute later if you add TA
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        score, band = _score_band(ctx)
        ctx["confidence"] = {"score": score, "band": band, "components": {}}
        return {"ok": True, "context": ctx}

    if op == "context.account":
        # Read-only balances + positions
        try:
            bal = await trad.account_balances()
            pos = await trad.positions()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"tradier error: {e}")

        positions = []
        raw = (pos.get("positions") or {})
        p = raw.get("position")
        if p:
            iterable = p if isinstance(p, list) else [p]
            for item in iterable:
                try:
                    qty = float(item.get("quantity") or 0)
                    positions.append({
                        "symbol": item.get("symbol"),
                        "side": "long" if qty >= 0 else "short",
                        "qty": qty,
                        "avg": float(item.get("cost_basis") or 0),
                        "upnl_r": None, "stop": None, "targets": []
                    })
                except Exception:
                    continue
        out = {
            "bp": (bal.get("balances") or {}).get("cash_available"),
            "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3},
            "positions": positions,
            "open_orders": []  # read-only app; orders not exposed
        }
        return {"ok": True, "account": out}

    if op == "positions.list":
        try:
            pos = await trad.positions()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"tradier error: {e}")
        return {"ok": True, "raw": pos}

    if op == "options.chain":
        # Placeholder: wire real Polygon Options endpoints when ready
        sym = (args.get("symbol") or "").upper()
        expiry = args.get("expiry")
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            chain = await poly.options_chain_light(sym, expiry)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon options error: {e}")
        return {"ok": True, "chain": chain}

    if op == "coach.guidance":
        sym = (args.get("symbol") or "").upper()
        hz  = (args.get("horizon") or "intraday").lower()
        if not sym:
            raise HTTPException(status_code=400, detail="args.symbol required")
        if hz not in {"scalp","intraday","swing"}:
            raise HTTPException(status_code=400, detail="args.horizon must be scalp|intraday|swing")

        # Build a compact SITUATION using the same context as context.symbol
        try:
            snap = await poly.snapshot_stock(sym)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon snapshot error: {e}")

        price = snap.get("price")
        ctx = {
            "symbol": sym,
            "t_ms": (snap.get("min") or {}).get("t") or (snap.get("day") or {}).get("t"),
            "price": price,
            "vwap": (snap.get("day") or {}).get("vw"),
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        score, band = _score_band(ctx)
        ctx["confidence"] = {"score": score, "band": band, "components": {}}
        levels = _default_levels(price, hz)

        situation = ctx | {"horizon": hz, "precalc_levels": levels}
        try:
            guidance = await chatdata_guidance(situation)
        except Exception:
            # Hard fallback if LLM call fails
            guidance = {
                "horizon": hz, "band": band,
                "actionable": "If 1m closes above VWAP and spread acceptable, consider starter; else wait.",
                "rationale": ["LLM error; using fallback"],
                "if_then": [{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
                "levels": levels,
                "risk_notes": "Educational guidance only.",
                "confidence_delta": {"score": score, "delta_vs_prev": None}
            }
        return {"ok": True, "guidance": guidance}

    # Should not reach here
    raise HTTPException(status_code=500, detail="unhandled op")
