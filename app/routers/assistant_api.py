from __future__ import annotations

import asyncio, inspect, math
from typing import Any, Dict, List, Optional, Tuple
from app.services.indicators import spread_stability as _spread_stability
from app.services.iv_surface import get_iv_surface, percentile_rank as _pct_rank_surface
from app.services.state_store import record_chain_aggregates
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
expected_value_intraday = None

try:
    em_mod = _im("app.engine.options_scoring")
    expected_move_from_straddle = getattr(em_mod, "expected_move_from_straddle", None)
    probability_of_touch = getattr(em_mod, "probability_of_touch", None)
    tradeability_score = getattr(em_mod, "tradeability_score", None)
    expected_value_intraday = getattr(em_mod, "expected_value_intraday", None)
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

# Expiry helper
def _auto_expiry(hz: str) -> str:
    from datetime import date, timedelta
    today = date.today()
    if hz in ("scalp", "intraday"):
        # Next Friday (incl. today if Friday -> next week)
        days = (4 - today.weekday()) % 7 or 7
        return str(today + timedelta(days=days))
    # swing default ~2 weeks
    return str(today + timedelta(days=14))

def _normalize_expiry(raw: Any, hz: str) -> str:
    if raw is None:
        return _auto_expiry(hz)
    if isinstance(raw, bool) and raw:
        return _auto_expiry(hz)
    if isinstance(raw, str) and raw.strip().lower() == "auto":
        return _auto_expiry(hz)
    return str(raw)

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

    async def options_top(sym: str, lp: Optional[float]) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float], Dict[str, Any]]:
        """Return (picks, EM_abs, EM_rel). Always tries to return *something*."""
        picks: List[Dict[str, Any]] = []
        em_abs = None; em_rel = None
        ctx: Dict[str, Any] = {}

        if "options" in include and poly:
            try:
                topK = int(options_req.get("topK", 6))
                maxSpreadPct = float(options_req.get("maxSpreadPct", 12))
                greeks = bool(options_req.get("greeks", True))
                expiry = _normalize_expiry(options_req.get("expiry", "auto"), horizon)
                req = {"topK": topK, "maxSpreadPct": maxSpreadPct, "greeks": greeks, "expiry": expiry}

                # Use Polygon snapshot; provider now supports snapshot_chain alias
                chain = await _maybe_await(poly.snapshot_chain(sym, req))
                # Try to read existing top; else make near-ATM picks from any rows we find
                opts = chain or {}
                raw_top = (opts.get("top") or [])
                # Locate a generic rows list from the response for percentile calcs
                chain_rows = None
                for k in ("rows","contracts","chain","all","snapshot","data","results"):
                    v = opts.get(k)
                    if isinstance(v, list) and v:
                        chain_rows = v
                        break
                # Cache/update IV surface and record liquidity aggregates
                if chain_rows:
                    try:
                        surf = await get_iv_surface(poly, sym, rows=chain_rows, ttl=180, last_price=lp)
                        ctx.setdefault("iv_surface", {"ts": surf.get("ts")})
                    except Exception:
                        pass
                    try:
                        liq = record_chain_aggregates(sym, expiry, chain_rows)
                        if liq:
                            ctx.setdefault("liquidity_trend", liq)
                    except Exception:
                        pass

                if raw_top:
                    picks = raw_top[:topK]
                else:
                        if chain_rows and lp is not None:
                            picks = _near_atm_pairs(chain_rows, lp, topK=topK)
                            # Enforce spread filter when quoted
                            picks = [p for p in picks if (p.get("spread_pct") is None) or (p.get("spread_pct") <= maxSpreadPct)]

                # EM & probabilities if we have picks and last price
                if picks and lp is not None:
                    em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                    if em_abs:
                        # Percentiles from chain rows (IV/OI/Volume) if available
                        def _extract_fields(rows: List[Dict[str, Any]]):
                            ivs: List[float] = []
                            ois: List[float] = []
                            vols: List[float] = []
                            for rr in rows:
                                meta = rr.get("options") or {}
                                det  = rr.get("details") or {}
                                g    = rr.get("greeks") or {}
                                exp_r = rr.get("expiry") or rr.get("expiration") or rr.get("expiration_date") or meta.get("expiration_date") or det.get("expiration_date")
                                if str(exp_r) != str(expiry):
                                    continue
                                iv = rr.get("iv") or rr.get("implied_volatility") or g.get("iv") or g.get("mid_iv")
                                oi = rr.get("open_interest")
                                if isinstance(oi, dict):
                                    oi = oi.get("oi")
                                vol = rr.get("volume") or (rr.get("day") or {}).get("volume")
                                try:
                                    if iv is not None: ivs.append(float(iv))
                                except Exception:
                                    pass
                                try:
                                    if oi is not None: ois.append(float(oi))
                                except Exception:
                                    pass
                                try:
                                    if vol is not None: vols.append(float(vol))
                                except Exception:
                                    pass
                            return ivs, ois, vols

                        def _pct_rank(vals: List[float], x: Optional[float]) -> Optional[float]:
                            if x is None or not vals:
                                return None
                            try:
                                xs = sorted([float(v) for v in vals if v is not None])
                                if len(xs) < 5:
                                    return None
                                import bisect
                                i = bisect.bisect_right(xs, float(x))
                                return round(100.0 * i / len(xs), 2)
                            except Exception:
                                return None

                        ivs: List[float] = []
                        ois: List[float] = []
                        vols: List[float] = []
                        def _pick_bucket_iv_list(surface_map, expiry: str, strike: Optional[float], last: Optional[float]) -> List[float]:
                            if not isinstance(surface_map, dict):
                                return []
                            exp_map = surface_map.get(str(expiry)) or {}
                            if not exp_map:
                                return []
                            # choose bucket based on moneyness
                            try:
                                if strike is not None and last is not None and last > 0:
                                    m = abs((float(strike) - float(last))/float(last))
                                    if m <= 0.01 and exp_map.get('atm'): return exp_map['atm']
                                    if m <= 0.03 and exp_map.get('near'): return exp_map['near']
                            except Exception:
                                pass
                            return exp_map.get('all') or []

                        if chain_rows:
                            ivs, ois, vols = _extract_fields(chain_rows)
                            surface_map = None
                            try:
                                # Prefer surface cache when available
                                surf2 = await get_iv_surface(poly, sym, rows=None, ttl=180, last_price=lp)
                                surface_map = (surf2 or {}).get("surface") or {}
                            except Exception:
                                surface_map = None

                        for r in picks:
                            # tradeability may be missing; compute only if engine available
                            ta = None
                            comps = None
                            if tradeability_score:
                                try:
                                    # Add percentiles if possible
                                    bucket_ivs = []
                                    if surface_map is not None:
                                        bucket_ivs = _pick_bucket_iv_list(surface_map, expiry, r.get("strike"), lp)
                                    if bucket_ivs:
                                        r["iv_percentile"] = _pct_rank(bucket_ivs, r.get("iv"))
                                    elif ivs:
                                        r["iv_percentile"] = _pct_rank(ivs, r.get("iv"))
                                    if ois:
                                        r["oi_percentile"] = _pct_rank(ois, r.get("oi"))
                                    if vols:
                                        r["vol_percentile"] = _pct_rank(vols, r.get("volume"))
                                    # ratio proxy
                                    try:
                                        if r.get("oi"):
                                            r["vol_oi_ratio"] = (float(r.get("volume") or 0.0) / float(r.get("oi") or 1.0))
                                    except Exception:
                                        pass
                                    ta, comps = tradeability_score(r, horizon=horizon), None
                                except Exception:
                                    pass
                            r["tradeability"] = ta
                            r["hit_probabilities"] = {
                                "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                            }
                # EM & probabilities if we have picks and last price
                if picks and lp is not None:
                    em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                    # Horizon scaling: convert EM at expiry to EM for the horizon via sqrt(time) rule
                    if em_abs:
                        try:
                            from datetime import date
                            exp_d = date.fromisoformat(str(expiry))
                            today = date.today()
                            days_to_exp = max(0.25, (exp_d - today).days or 0.25)  # at least ~quarter day
                            hours_to_exp = max(1.0, days_to_exp * 6.5)
                            horizon_hours = 2.0 if horizon == "scalp" else 6.5 if horizon == "intraday" else None
                            if horizon_hours and hours_to_exp > 0:
                                scale = (horizon_hours / hours_to_exp) ** 0.5
                                em_abs = em_abs * scale
                                em_rel = em_abs / lp if lp else em_rel
                        except Exception:
                            pass
                        for r in picks:
                            # tradeability may be missing; compute only if engine available
                            ta = None
                            if tradeability_score:
                                try:
                                    # Percentiles from chain rows already computed above
                                    ta = tradeability_score(r, horizon=horizon)
                                except Exception:
                                    pass
                            r["tradeability"] = ta
                            r["hit_probabilities"] = {
                                "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                            }
                            # EV estimate for ranking (optional)
                            if expected_value_intraday:
                                try:
                                    ev, bd = expected_value_intraday(r, lp, em_abs, horizon=horizon)
                                    r["ev"] = {"dollars": ev, "pct": (ev/(max(1e-6, ((r.get('bid') or 0)+(r.get('ask') or 0))/2.0)) if (r.get('bid') is not None and r.get('ask') is not None) else None)}
                                    r["ev_detail"] = bd
                                except Exception:
                                    pass

                        # Short NBBO sampling to estimate spread stability and refresh quotes
                        async def _nbbo_sample(picks: List[Dict[str, Any]], samples: int = 2, interval: float = 0.35):
                            symbols = [p.get("symbol") for p in picks if p.get("symbol")]
                            if not symbols:
                                return
                            # Build symbol -> index mapping and storage
                            idx = {p.get("symbol"): i for i, p in enumerate(picks) if p.get("symbol")}
                            bids: Dict[str, List[float]] = {s: [] for s in symbols}
                            asks: Dict[str, List[float]] = {s: [] for s in symbols}
                            for _ in range(samples):
                                qs = await asyncio.gather(*[
                                    _maybe_await(poly.option_quote(s)) for s in symbols
                                ], return_exceptions=True)
                                for s, q in zip(symbols, qs):
                                    if isinstance(q, dict):
                                        b = q.get("bid"); a = q.get("ask")
                                        if b is not None: bids[s].append(b)
                                        if a is not None: asks[s].append(a)
                                        # refresh latest nbbo fields on pick
                                        i = idx.get(s)
                                        if i is not None:
                                            if q.get("bid") is not None: picks[i]["bid"] = q.get("bid")
                                            if q.get("ask") is not None: picks[i]["ask"] = q.get("ask")
                                            sp = q.get("spread_pct")
                                            if sp is not None: picks[i]["spread_pct"] = sp
                                await asyncio.sleep(interval)
                            # Compute spread stability and update tradeability again
                            for s in symbols:
                                i = idx.get(s)
                                if i is None:
                                    continue
                                st = _spread_stability(bids[s], asks[s]) if bids.get(s) and asks.get(s) else None
                                picks[i]["spread_stability"] = st
                                if tradeability_score:
                                    try:
                                        picks[i]["tradeability"] = tradeability_score(picks[i], horizon=horizon)
                                    except Exception:
                                        pass

                        # Limit sampling scope to avoid latency explosion
                        try:
                            await _nbbo_sample(picks[:min(len(picks), max(4, int(topK)))], samples=2, interval=0.35)
                        except Exception:
                            pass
            except Exception as e:
                errs[f"{sym}.options"] = f"{type(e).__name__}: {e}"

            # Fallback: if no picks from Polygon, try Tradier options chain
            if not picks and "options" in include:
                try:
                    # Import lazily to avoid hard dependency
                    from importlib import import_module as _im2
                    tc_mod = _im2("app.services.providers.tradier_chain")
                    tc_fn = getattr(tc_mod, "options_chain", None)
                    if callable(tc_fn):
                        trows = await _maybe_await(tc_fn(sym, expiry=expiry, greeks=greeks))
                        if trows and lp is not None:
                            picks = _near_atm_pairs(trows, lp, topK=topK)
                            picks = [p for p in picks if (p.get("spread_pct") is None) or (p.get("spread_pct") <= maxSpreadPct)]
                            if picks:
                                # Percentiles for Tradier rows
                                def _vals(rows, key):
                                    out = []
                                    for rr in rows:
                                        try:
                                            v = rr.get(key)
                                            if key == 'iv':
                                                v = v or (rr.get('greeks') or {}).get('mid_iv') or (rr.get('greeks') or {}).get('iv')
                                            if v is not None: out.append(float(v))
                                        except Exception:
                                            pass
                                    return out
                                tivs = _vals(trows, 'iv'); tois = _vals(trows, 'open_interest'); tvols = _vals(trows, 'volume')
                                def _pct_rank2(vals: List[float], x: Optional[float]) -> Optional[float]:
                                    try:
                                        return _pct_rank_surface(vals, x)
                                    except Exception:
                                        return None
                                em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                                if em_abs:
                                    # Apply same horizon scaling to fallback EM
                                    try:
                                        from datetime import date
                                        exp_d = date.fromisoformat(str(expiry))
                                        today = date.today()
                                        days_to_exp = max(0.25, (exp_d - today).days or 0.25)
                                        hours_to_exp = max(1.0, days_to_exp * 6.5)
                                        horizon_hours = 2.0 if horizon == "scalp" else 6.5 if horizon == "intraday" else None
                                        if horizon_hours and hours_to_exp > 0:
                                            scale = (horizon_hours / hours_to_exp) ** 0.5
                                            em_abs = em_abs * scale
                                            em_rel = em_abs / lp if lp else em_rel
                                    except Exception:
                                        pass
                                    for r in picks:
                                        # Attach percentiles + ratio for scoring
                                        if tivs:
                                            r["iv_percentile"] = _pct_rank2(tivs, r.get("iv"))
                                        if tois:
                                            r["oi_percentile"] = _pct_rank2(tois, r.get("oi"))
                                        if tvols:
                                            r["vol_percentile"] = _pct_rank2(tvols, r.get("volume"))
                                        try:
                                            if r.get("oi"):
                                                r["vol_oi_ratio"] = (float(r.get("volume") or 0.0) / float(r.get("oi") or 1.0))
                                        except Exception:
                                            pass
                                        ta = None
                                        if tradeability_score:
                                            try:
                                                ta = tradeability_score(r, horizon=horizon)
                                            except Exception:
                                                pass
                                        r["tradeability"] = ta
                                        r["hit_probabilities"] = {
                                            "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                            "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                                        }
                                        if expected_value_intraday:
                                            try:
                                                ev, bd = expected_value_intraday(r, lp, em_abs, horizon=horizon)
                                                r["ev"] = {"dollars": ev, "pct": (ev/(max(1e-6, ((r.get('bid') or 0)+(r.get('ask') or 0))/2.0)) if (r.get('bid') is not None and r.get('ask') is not None) else None)}
                                                r["ev_detail"] = bd
                                            except Exception:
                                                pass
                                    # NBBO sampling on fallback too
                                    try:
                                        await _nbbo_sample(picks[:min(len(picks), max(4, int(topK)))], samples=2, interval=0.35)
                                    except Exception:
                                        pass
                except Exception as e:
                    errs[f"{sym}.options.tradier_fallback"] = f"{type(e).__name__}: {e}"

        return picks, em_abs, em_rel

    for sym in symbols:
        out: Dict[str, Any] = {}
        lp = await last_price(sym)
        if lp is not None:
            out.setdefault("price", {})["last"] = lp

        picks, em_abs, em_rel, opt_ctx = await options_top(sym, lp)
        if picks:
            out.setdefault("options", {})["top"] = picks
        if em_abs is not None:
            out.setdefault("context", {})["expected_move"] = {"abs": em_abs, "rel": em_rel}
        if opt_ctx:
            out.setdefault("context", {}).update(opt_ctx)

        # If "levels" were requested but we don't have enough bars off-hours, return an empty object instead of null.
        if "levels" in include:
            out.setdefault("levels", {})

        snapshot["symbols"][sym] = out

    return {"ok": True, "snapshot": snapshot, "errors": errs}
