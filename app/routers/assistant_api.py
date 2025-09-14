from __future__ import annotations

import asyncio, inspect, math
from typing import Any, Dict, List, Optional, Tuple
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel

router = APIRouter()

# ---------- Dynamic provider imports (robust, non-fatal) ----------
from importlib import import_module as _im

PolygonMarket = None
TradierMarket = None
TradierClient = None
_prov_err: List[str] = []

for mod, cls in [
    ("app.services.providers.polygon_market", "PolygonMarket"),
    ("app.services.providers.polygon", "PolygonMarket"),
    ("app.services.providers.polygon_client", "PolygonClient"),
]:
    try:
        PolygonMarket = getattr(_im(mod), cls)
        break
    except Exception as e:
        _prov_err.append(f"{mod}.{cls}: {type(e).__name__}: {e}")

for mod, cls in [
    ("app.services.providers.tradier_market", "TradierMarket"),
    ("app.services.providers.tradier", "TradierMarket"),
    ("app.services.providers.tradier", "TradierClient"),
]:
    try:
        _klass = getattr(_im(mod), cls)
        TradierMarket = TradierMarket or _klass
        TradierClient = TradierClient or _klass
        break
    except Exception as e:
        _prov_err.append(f"{mod}.{cls}: {type(e).__name__}: {e}")

# ---------- Optional engine imports (safe fallbacks) ----------
expected_move_from_straddle = None
probability_of_touch = None
tradeability_score = None

try:
    em_mod = _im("app.engine.options_scoring")
    expected_move_from_straddle = getattr(em_mod, "expected_move_from_straddle", None)
    probability_of_touch = getattr(em_mod, "probability_of_touch", None)
    tradeability_score = getattr(em_mod, "tradeability_score", None)
except Exception as e:
    _prov_err.append(f"engine.options_scoring: {type(e).__name__}: {e}")

# ---------- Helpers ----------
async def _maybe_await(v):
    if inspect.isawaitable(v):
        return await v
    return v

def _near_atm_pairs(chain_rows: List[Dict[str, Any]], last_price: float, topK: int = 6) -> List[Dict[str, Any]]:
    """Pick a few near-ATM call & put rows from a generic chain list; normalize fields."""
    if not chain_rows or last_price is None:
        return []
    def keyer(r):
        try:
            return abs(float(r.get("strike", 0.0)) - float(last_price))
        except Exception:
            return 1e9
    def norm(r):
        g = r.get("greeks") or {}
        iv = r.get("iv") or r.get("implied_volatility") or g.get("iv")
        d  = r.get("delta") or g.get("delta")
        symbol = r.get("symbol") or r.get("contract") or r.get("id")
        typ = (r.get("type") or r.get("option_type") or "").lower()
        typ = "call" if typ.startswith("c") else ("put" if typ.startswith("p") else typ)
        bid = r.get("bid"); ask = r.get("ask")
        spread_pct = None
        try:
            if bid is not None and ask is not None and ask > 0:
                spread_pct = round((ask - bid)/ask*100, 2)
        except Exception:
            pass
        return {
            "symbol": symbol,
            "type": typ,
            "strike": r.get("strike"),
            "delta": d,
            "iv": iv,
            "oi": r.get("open_interest") or r.get("oi"),
            "volume": r.get("volume"),
            "bid": bid, "ask": ask,
            "spread_pct": spread_pct
        }

    calls = [r for r in chain_rows if (r.get("type") or r.get("option_type","")).lower().startswith("c")]
    puts  = [r for r in chain_rows if (r.get("type") or r.get("option_type","")).lower().startswith("p")]
    calls = list(map(norm, sorted(calls, key=keyer)[:max(1, topK//2)]))
    puts  = list(map(norm, sorted(puts,  key=keyer)[:max(1, topK//2)]))
    return calls + puts

def _simple_em_from_straddle(last_price: float, picks: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """Fallback EM if engine fn not available. Use average of top2 call/put mid prices."""
    if expected_move_from_straddle:
        try:
            em_abs, em_rel = expected_move_from_straddle(last_price=last_price, candidates=picks)
            return em_abs, em_rel
        except Exception:
            pass
    # fallback: compute mids and sum of nearest call+put ≈ straddle price; EM ≈ straddle / spot
    calls = [p for p in picks if p.get("type")=="call" and p.get("bid") is not None and p.get("ask") is not None]
    puts  = [p for p in picks if p.get("type")=="put"  and p.get("bid") is not None and p.get("ask") is not None]
    if not calls or not puts:
        return None, None
    def mid(x): return (x["bid"] + x["ask"])/2.0 if x["bid"] is not None and x["ask"] is not None else None
    cm = sorted([mid(c) for c in calls if mid(c) is not None])[:2]
    pm = sorted([mid(p) for p in puts  if mid(p) is not None])[:2]
    if not cm or not pm:
        return None, None
    straddle = (sum(cm)/len(cm)) + (sum(pm)/len(pm))
    em_abs = straddle  # crude fallback
    em_rel = (straddle/last_price) if last_price else None
    return em_abs, em_rel

def _p_touch(distance: float, sigma_abs: float) -> Optional[float]:
    """Fallback touch probability if engine fn not present."""
    if probability_of_touch:
        try:
            return probability_of_touch(distance=distance, sigma_abs=sigma_abs)
        except Exception:
            pass
    try:
        # Brownian max approx: 2*(1 - Phi(d/(sigma)))
        x = distance / max(1e-8, sigma_abs)
        # approx Phi via erf
        import math
        Phi = 0.5*(1.0 + math.erf(x/math.sqrt(2)))
        return max(0.0, min(1.0, 2.0*(1.0 - Phi)))
    except Exception:
        return None

# ---------- API Schemas ----------
class ExecRequest(BaseModel):
    op: str
    args: Dict[str, Any] = {}

@router.get("/assistant/actions")
async def assistant_actions() -> Dict[str, Any]:
    return {"ok": True, "ops": ["data.snapshot"], "providers": {"polygon": bool(PolygonMarket), "tradier": bool(TradierMarket or TradierClient)}, "import_errors": _prov_err}

@router.post("/assistant/exec")
async def assistant_exec(payload: ExecRequest = Body(...)) -> Dict[str, Any]:
    try:
        if payload.op != "data.snapshot":
            raise HTTPException(status_code=400, detail=f"Unsupported op: {payload.op}")
        result = await _handle_snapshot(payload.args)
        return result
    except HTTPException:
        raise
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}

# ---------- Core handler ----------
async def _handle_snapshot(args: Dict[str, Any]) -> Dict[str, Any]:
    symbols: List[str] = [str(s).upper() for s in (args.get("symbols") or [])]
    include: List[str] = args.get("include") or []
    options_req: Dict[str, Any] = args.get("options") or {}
    horizon: str = (args.get("horizon") or "intraday").lower()

    errs: Dict[str, Any] = {}
    snapshot: Dict[str, Any] = {"symbols": {}}

    # init providers (non-fatal)
    poly = PolygonMarket() if PolygonMarket else None
    tradier = (TradierMarket or TradierClient)() if (TradierMarket or TradierClient) else None

    async def last_price(sym: str) -> Optional[float]:
        # Try Tradier then Polygon (non-fatal)
        if tradier:
            try:
                q = await _maybe_await(tradier.quote_last(sym))
                if q and q.get("price") is not None:
                    return float(q["price"])
            except Exception as e:
                errs[f"{sym}.price.tradier"] = f"{type(e).__name__}: {e}"
        if poly:
            try:
                lt = await _maybe_await(poly.last_trade(sym))
                if lt and lt.get("price") is not None:
                    return float(lt["price"])
            except Exception as e:
                errs[f"{sym}.price.polygon"] = f"{type(e).__name__}: {e}"
        return None

    async def options_top(sym: str, lp: Optional[float]) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float]]:
        """Return (picks, EM_abs, EM_rel). Always tries to return *something*."""
        picks: List[Dict[str, Any]] = []
        em_abs = None; em_rel = None

        if "options" in include and poly:
            try:
                topK = int(options_req.get("topK", 6))
                maxSpreadPct = float(options_req.get("maxSpreadPct", 12))
                greeks = bool(options_req.get("greeks", True))
                expiry = options_req.get("expiry", "auto")
                req = {"topK": topK, "maxSpreadPct": maxSpreadPct, "greeks": greeks, "expiry": expiry}

                chain = await _maybe_await(poly.snapshot_chain(sym, req))
                # Try to read existing top; else make near-ATM picks from any rows we find
                opts = chain or {}
                raw_top = (opts.get("top") or [])
                if raw_top:
                    picks = raw_top[:topK]
                else:
                    # hunt for generic rows list buckets
                    chain_rows = None
                    for k in ("rows","contracts","chain","all","snapshot","data","results"):
                        v = opts.get(k)
                        if isinstance(v, list) and v:
                            chain_rows = v
                            break
                    if chain_rows and lp is not None:
                        picks = _near_atm_pairs(chain_rows, lp, topK=topK)

                # EM & probabilities if we have picks and last price
                if picks and lp is not None:
                    em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                    if em_abs:
                        for r in picks:
                            # tradeability may be missing; compute only if engine available
                            ta = None
                            comps = None
                            if tradeability_score:
                                try:
                                    ta, comps = tradeability_score(r, horizon=horizon), None
                                except Exception:
                                    pass
                            r["tradeability"] = ta
                            r["hit_probabilities"] = {
                                "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                            }
            except Exception as e:
                errs[f"{sym}.options"] = f"{type(e).__name__}: {e}"

        return picks, em_abs, em_rel

    for sym in symbols:
        out: Dict[str, Any] = {}
        lp = await last_price(sym)
        if lp is not None:
            out.setdefault("price", {})["last"] = lp

        picks, em_abs, em_rel = await options_top(sym, lp)
        if picks:
            out.setdefault("options", {})["top"] = picks
        if em_abs is not None:
            out.setdefault("context", {})["expected_move"] = {"abs": em_abs, "rel": em_rel}

        # If "levels" were requested but we don't have enough bars off-hours, return an empty object instead of null.
        if "levels" in include:
            out.setdefault("levels", {})

        snapshot["symbols"][sym] = out

    return {"ok": True, "snapshot": snapshot, "errors": errs}
