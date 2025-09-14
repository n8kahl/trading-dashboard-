from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, Tuple

from app.services.providers.polygon import PolygonClient
from app.services.providers.tradier import TradierClient

# Try to use ChatData; safe fallback if not configured/import fails
try:
    from app.services.llm import chatdata_guidance
except Exception:
    async def chatdata_guidance(situation: Dict[str, Any]) -> Dict[str, Any]:
        price = situation.get("precalc_levels",{}).get("entry")
        return {
            "horizon": situation.get("horizon","intraday"),
            "band": "mixed",
            "actionable": "If 1m closes above VWAP and spread acceptable, consider starter; else wait.",
            "rationale": ["LLM offline fallback"],
            "if_then": [{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
            "levels": {
                "entry": price, "stop": situation.get("precalc_levels",{}).get("stop"),
                "targets": situation.get("precalc_levels",{}).get("targets",[])
            },
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
    score = 50
    price = ctx.get("price"); vwap = ctx.get("vwap")
    ema = ctx.get("ema") or {}; flow = ctx.get("flow") or {}
    e9, e20 = ema.get("ema9"), ema.get("ema20")
    if e9 is not None and e20 is not None: score += 10 if e9 > e20 else -10
    if price is not None and vwap is not None: score += 10 if price >= vwap else -10
    rvol = flow.get("rvol")
    if isinstance(rvol,(int,float)): score += 10 if rvol >= 1.5 else (-10 if rvol < 0.8 else 0)
    score = max(0, min(100, score))
    band = "favorable" if score >= 66 else "unfavorable" if score <= 34 else "mixed"
    return score, band

def _levels(price: float|None, horizon: str) -> Dict[str,Any]:
    if price is None: return {"entry": None, "stop": None, "targets": []}
    tick = 0.3 if horizon=="scalp" else 0.8 if horizon=="intraday" else 2.0
    entry = round(price,2); stop = round(price - tick,2)
    return {"entry": entry, "stop": stop, "targets": [round(price+tick,2), round(price+2*tick,2)]}

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op"); args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use one of {SUPPORTED_OPS}")

    poly = PolygonClient()
    trad = TradierClient()

    # --- Quotes ---------------------------------------------------------------
    if op == "market.quote":
        sym = (args.get("symbol") or "").upper()
        if not sym: raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            q = await poly.last_quote(sym)   # may 403 on some plans
        except Exception:
            # Fallback to last_trade which is widely available
            try:
                lt = await poly.last_trade(sym)
                q = {"symbol": sym, "bid": None, "ask": None, "last": lt.get("price"), "t": lt.get("t")}
            except Exception as e2:
                raise HTTPException(status_code=502, detail=f"quote fallback error: {e2}")
        return {"ok": True, "quote": q}

    # --- Symbol context (uses last_trade only) --------------------------------
    if op == "context.symbol":
        sym = (args.get("symbol") or "").upper()
        if not sym: raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            lt = await poly.last_trade(sym)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon last_trade error: {e}")

        ctx = {
            "symbol": lt.get("symbol") or sym,
            "t_ms": lt.get("t"),
            "price": lt.get("price"),
            "vwap": None,  # compute later if you add TA
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False,
        }
        score, band = _score_band(ctx)
        ctx["confidence"] = {"score": score, "band": band, "components": {}}
        return {"ok": True, "context": ctx}

    # --- Account context (Tradier) -------------------------------------------
    if op == "context.account":
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
            "open_orders": []
        }
        return {"ok": True, "account": out}

    # --- Raw positions (Tradier passthrough) ---------------------------------
    if op == "positions.list":
        try:
            pos = await trad.positions()
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"tradier error: {e}")
        return {"ok": True, "raw": pos}

    # --- Options chain (placeholder for now) ---------------------------------
    if op == "options.chain":
        sym = (args.get("symbol") or "").upper(); expiry = args.get("expiry")
        if not sym: raise HTTPException(status_code=400, detail="args.symbol required")
        try:
            chain = await poly.options_chain_light(sym, expiry)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon options error: {e}")
        return {"ok": True, "chain": chain}

    # --- Guidance (uses last_trade + ChatData) --------------------------------
    if op == "coach.guidance":
        sym = (args.get("symbol") or "").upper()
        hz  = (args.get("horizon") or "intraday").lower()
        if not sym: raise HTTPException(status_code=400, detail="args.symbol required")
        if hz not in {"scalp","intraday","swing"}:
            raise HTTPException(status_code=400, detail="args.horizon must be scalp|intraday|swing")

        try:
            lt = await poly.last_trade(sym)
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"polygon last_trade error: {e}")

        price = lt.get("price")
        ctx = {
            "symbol": sym,
            "t_ms": lt.get("t"),
            "price": price,
            "vwap": None,
            "ema": {"ema9": None, "ema20": None},
            "atr": {"atr14": None, "regime": "normal"},
            "flow": {"rvol": None, "liquidity": "unknown", "spread": None},
            "risk": {"day_r_used": None, "max_r": None, "breach_flags": {"max_day_loss": False}},
            "position": None,
            "stale": False
        }
        score, band = _score_band(ctx)
        ctx["confidence"] = {"score": score, "band": band, "components": {}}
        levels = _levels(price, hz)
        situation = ctx | {"horizon": hz, "precalc_levels": levels}
        try:
            guidance = await chatdata_guidance(situation)
        except Exception:
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
