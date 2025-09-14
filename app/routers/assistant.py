from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import re as _re

from app.services.providers.polygon_market import PolygonMarket
from app.services.providers.tradier import TradierMarket, TradierAuthError, TradierHTTPError
from app.services.indicators import (ema, sma, rsi, macd, atr14, session_vwap_and_sigma, pivots_classic, rvol_5min)
from app.engine.regime import analyze as regime_analyze
from app.engine.options_scoring import tradeability_score, ScoreWeights, expected_move_from_straddle, probability_of_touch
from app.engine.position_guidance import dynamic_trailing_stop, scale_plan, adjust_targets_for_em
    ema, sma, rsi, macd, atr14,
    session_vwap_and_sigma, pivots_classic, rvol_5min
router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])
SUPPORTED_OPS = ["data.snapshot"]

@router.get("/actions")
async def assistant_actions():
    return {"ok": True, "ops": SUPPORTED_OPS}

# -------- helpers --------
_OCC_RE = _re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")
def occ_parse(sym: str) -> Optional[Dict[str, Any]]:
    m = _OCC_RE.match(sym or "")
    if not m: return None
    und, yy, mm, dd, cp, strike8 = m.groups()
    strike = float(int(strike8)/1000.0)
    return {"underlying": und, "expiry": f"20{yy}-{mm}-{dd}", "type": ("call" if cp=='C' else "put"), "strike": strike}

def auto_expiry(hz: str) -> str:
    today = datetime.utcnow().date()
    if hz in ("scalp","intraday"):
        days = (4 - today.weekday()) % 7 or 7  # to Friday
        return str(today + timedelta(days=days))
    return str(today + timedelta(days=14))

def normalize_expiry(raw, hz: str) -> str:
    if raw is None: return auto_expiry(hz)
    if isinstance(raw, bool) and raw: return auto_expiry(hz)
    if isinstance(raw, str) and raw.strip().lower() == "auto": return auto_expiry(hz)
    return str(raw)

# -------- options filter/rank with strict+relaxed --------
def filter_and_rank_options(rows: List[Dict[str, Any]], expiry: str, horizon: str, max_spread: float, topK: int) -> List[Dict[str, Any]]:
    MIN_OI = 50
    MIN_VOL = 1
    MIN_IV, MAX_IV = 0.05, 5.0
    MIN_ABS_DELTA, MAX_ABS_DELTA = 0.05, 0.85

    def norm_row(r):
        meta   = r.get("options") or {}
        det    = r.get("details") or {}
        q      = r.get("last_quote") or {}
        t      = r.get("last_trade") or {}
        g      = r.get("greeks") or {}
        iv_raw = r.get("implied_volatility")
        iv     = (iv_raw.get("iv") if isinstance(iv_raw, dict) else iv_raw)

        sym = meta.get("symbol") or r.get("ticker") or (det.get("symbol") if isinstance(det, dict) else None)
        occ = r.get("_occ") or (occ_parse(sym) if sym else None)

        typ    = (occ and occ["type"])    or (meta.get("contract_type") or det.get("contract_type"))
        strike = (occ and occ["strike"])  or (meta.get("strike_price") or det.get("strike_price"))
        exp    = (occ and occ["expiry"])  or (meta.get("expiration_date") or det.get("expiration_date"))

        bid, ask = q.get("bid"), q.get("ask")
        last     = t.get("price") or (r.get("day") or {}).get("close")
        delta    = g.get("delta")

        return {
            "symbol": sym,
            "type": (typ.lower() if isinstance(typ, str) else typ),
            "strike": strike,
            "expiry": exp,
            "bid": bid, "ask": ask, "last": last,
            "delta": delta, "gamma": g.get("gamma"), "theta": g.get("theta"),
            "iv": iv,
            "oi": ((r.get("open_interest") or {}).get("oi") if isinstance(r.get("open_interest"), dict) else r.get("open_interest")),
            "volume": (r.get("day") or {}).get("volume"),
        }

    normed = [norm_row(r) for r in rows]

    # ---------- STRICT (market hours: require bid/ask) ----------
    strict = []
    for x in normed:
        if not x["symbol"] or not x["type"] or x["strike"] is None or not x["expiry"]: continue
        if str(x["expiry"]) != str(expiry): continue
        if x["bid"] is None or x["ask"] is None or x["ask"] <= 0: continue

        sp = ((x["ask"] - x["bid"]) / x["ask"]) * 100.0
        x["spread_pct"] = round(sp, 2)
        if sp > max_spread: continue

        iv = x["iv"]
        if iv is None or iv < MIN_IV or iv > MAX_IV: continue

        try: d = float(x["delta"])
        except (TypeError, ValueError): continue
        d = abs(d) if x["type"] == "call" else -abs(d)
        if not (MIN_ABS_DELTA <= abs(d) <= MAX_ABS_DELTA): continue
        x["delta"] = d

        oi = int(x.get("oi") or 0); vol = int(x.get("volume") or 0)
        if oi < MIN_OI and vol < MIN_VOL: continue

        strict.append(x)

    def rank(items):
        target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
        def score(x):
            d  = x["delta"]; sp = x.get("spread_pct"); iv = x["iv"] or 0.0
            oi = int(x.get("oi") or 0); vol = int(x.get("volume") or 0)
            dc = 1.0 - min(1.0, abs(abs(d) - target))
            st = (1.0 - min(1.0, (sp or 12.0)/12.0))  # neutral if unknown
            li = min(1.0, (oi/1000.0 + vol/5000.0))
            ivp= 1.0 - min(1.0, abs(iv-0.25)/0.40)
            return dc*0.45 + st*0.25 + li*0.20 + ivp*0.10
        ranked = sorted(items, key=score, reverse=True)[:topK]
        return [{
            "symbol": r["symbol"], "type": r["type"], "strike": r["strike"], "expiry": r["expiry"],
            "bid": r.get("bid"), "ask": r.get("ask"), "last": r.get("last"),
            "delta": round(r["delta"], 4),
            "iv": (round(r["iv"], 4) if r["iv"] else None),
            "spread_pct": (None if r.get("spread_pct") is None else r["spread_pct"]),
            "oi": int(r.get("oi") or 0), "volume": int(r.get("volume") or 0)
        } for r in ranked]

    if strict:
        return rank(strict)

    # ---------- RELAXED (off-hours: allow last+liquidity) ----------
    MIN_OI_RELAX = 100
    MIN_VOL_RELAX = 50
    relaxed = []
    for x in normed:
        if not x["symbol"] or not x["type"] or x["strike"] is None or not x["expiry"]: continue
        if str(x["expiry"]) != str(expiry): continue
        if x.get("last") is None: continue

        iv = x["iv"]
        if iv is None or iv < MIN_IV or iv > MAX_IV: continue

        try: d = float(x["delta"])
        except (TypeError, ValueError): continue
        d = abs(d) if x["type"] == "call" else -abs(d)
        if not (MIN_ABS_DELTA <= abs(d) <= 0.95): continue
        x["delta"] = d

        oi = int(x.get("oi") or 0); vol = int(x.get("volume") or 0)
        if oi < MIN_OI_RELAX and vol < MIN_VOL_RELAX: continue

        if x.get("bid") is not None and x.get("ask"):
            sp = ((x["ask"] - x["bid"]) / x["ask"]) * 100.0
            x["spread_pct"] = round(sp, 2)
        else:
            x["spread_pct"] = None

        relaxed.append(x)

    return rank(relaxed) if relaxed else []

# -------- main exec --------
@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op"); args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use {SUPPORTED_OPS}")

    symbols: List[str] = args.get("symbols") or []
    if not symbols: raise HTTPException(status_code=400, detail="args.symbols (array) required")
    horizon: str = (args.get("horizon") or "intraday").lower()

    include = set(args.get("include") or ["price","history","indicators","levels","micro","options","account"])

    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    session_mode = (hist_spec.get("session") or "today").lower()
    lookback = int(hist_spec.get("lookback") or (30 if bars_kind=="1m" else 90 if bars_kind=="5m" else 120))

    opt_spec = args.get("options") or {}
    expiry = normalize_expiry(opt_spec.get("expiry"), horizon)
    topK = int(opt_spec.get("topK") or 6)
    max_spread = float(opt_spec.get("maxSpreadPct") or 8.0)

    poly = PolygonMarket()
    tradier = TradierMarket()
    snapshot: Dict[str, Any] = {"symbols": {}, "account": {}, "errors": {}}

    # ACCOUNT (only if asked)
    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str, Any] = {}
        errs: Dict[str, Any] = {}

        # PRICE (only if asked or implied by indicators/levels)
        if "price" in include or "indicators" in include or "levels" in include:
            last_price = None; last_t = None
            try:
                tq = await tradier.quote_last(symU)
                last_price, last_t = tq.get("price"), tq.get("t")
            except (TradierAuthError, TradierHTTPError) as e:
                errs["price.tradier"] = str(e)
            except Exception as e:
                errs["price.tradier.unknown"] = f"{type(e).__name__}: {e}"
            if last_price is None:
                try:
                    lt = await poly.last_trade(symU)
                    last_price, last_t = lt.get("price"), lt.get("t")
                except Exception as e:
                    errs["price.polygon"] = f"{type(e).__name__}: {e}"
            out["price"] = {"last": last_price, "t": last_t}

        # HISTORY + LEVELS (only if requested)
        minute_bars = []; fivem_bars = []; daily_bars = []
        if "history" in include or "levels" in include or "indicators" in include or "micro" in include:
            try:
                if bars_kind in ("1m","5m"):
                    if session_mode != "prev":
                        try:
                            if bars_kind == "1m":
                                minute_bars = await poly.minute_bars_today(symU)
                            else:
                                fivem_bars  = await poly.five_minute_bars_today(symU)
                        except Exception as e:
                            errs[f"history.{bars_kind}"] = f"{type(e).__name__}: {e}"
                    # fallback or explicit prev
                    if session_mode == "prev" or (not minute_bars and not fivem_bars):
                        try:
                            fivem_prev = await poly.five_minute_bars_prev_session(symU)
                            if fivem_prev and not fivem_bars:
                                fivem_bars = fivem_prev
                        except Exception as e:
                            errs["history.prev"] = f"{type(e).__name__}: {e}"
                if "indicators" in include or "levels" in include:
                    # daily only if we need indicator context or pivots
                    daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 220))
            except Exception as e:
                errs["history"] = f"{type(e).__name__}: {e}"

        # INDICATORS (only if requested)
        if "indicators" in include:
            ind: Dict[str, Any] = {"ema1": None, "ema5": None, "ema9": None, "ema20": None, "ema50": None, "sma200": None, "atr14": None, "rsi14": None, "macd": None}
            try:
                closes_intra = [b["c"] for b in (minute_bars or fivem_bars) if b.get("c") is not None]
                closes_d = [d["c"] for d in daily_bars if d.get("c") is not None]
                if closes_intra:
                    ind["ema1"]  = ema(closes_intra, 1)
                    ind["ema5"]  = ema(closes_intra, 5)
                    ind["ema9"]  = ema(closes_intra, 9)
                    ind["ema20"] = ema(closes_intra, 20)
                if closes_d:
                    ind["ema50"]  = ema(closes_d, 50)
                    ind["sma200"] = sma(closes_d, 200)
                    ind["atr14"]  = atr14(daily_bars)
                    ind["rsi14"]  = rsi(closes_d)
                    ind["macd"]   = macd(closes_d)
            except Exception as e:
                errs["indicators"] = f"{type(e).__name__}: {e}"
            out["indicators"] = ind

        # LEVELS (only if requested)
        if "levels" in include:
            levels: Dict[str, Any] = {}
            try:
                bars_for_vwap = minute_bars if minute_bars else fivem_bars
                src = "1m" if minute_bars else ("5m" if fivem_bars else None)
                vwap, sigma = session_vwap_and_sigma(bars_for_vwap) if bars_for_vwap else (None, None)
                if vwap is not None: levels["vwap_session"] = vwap
                if vwap is not None and sigma is not None:
                    levels["vwap_bands"] = {"minus1": round(vwap - sigma, 4), "plus1": round(vwap + sigma, 4)}
                if src: levels["debug"] = {"source": src, "bar_count": len(bars_for_vwap or [])}
                if bars_for_vwap:
                    highs = [b["h"] for b in bars_for_vwap if b.get("h") is not None]
                    lows  = [b["l"] for b in bars_for_vwap if b.get("l") is not None]
                    if highs: levels["hod"] = round(max(highs), 4)
                    if lows:  levels["lod"] = round(min(lows), 4)
                if len(daily_bars) >= 2:
                    prev = daily_bars[-2]; prev_day = {"o": prev["o"], "h": prev["h"], "l": prev["l"], "c": prev["c"]}
                    levels["prev_day"] = prev_day
                    levels["pivots"] = pivots_classic(prev_day)
            except Exception as e:
                errs["levels"] = f"{type(e).__name__}: {e}"
            out["levels"] = levels

        # MICRO (only if requested)
        if "micro" in include:
            try:
                micro = {"rvol_5": rvol_5min(minute_bars) if minute_bars else None}
                micro["liq_score"] = None if micro["rvol_5"] is None else round(min(1.0, (micro["rvol_5"]/2.0)), 2)
                out["micro"] = micro
            except Exception as e:
                errs["micro"] = f"{type(e).__name__}: {e}"; out["micro"] = {}

        # OPTIONS (only if requested)
        if "options" in include:
            out["options"] = {"expiry": expiry, "top": []}
            try:
                snap = await poly.snapshot_option_chain(symU, limit=250, max_pages=6)
                out["options"]["top"] = filter_and_rank_options(
                    rows=(snap.get("results") or []),
                    expiry=expiry, horizon=horizon, max_spread=max_spread, topK=topK
                )
            except Exception as e:
                errs["options"] = f"{type(e).__name__}: {e}"

        # CONFIDENCE baseline (so GPT can modulate)
        out["confidence"] = {"score": 50, "details": []}
        out["regime"] = {"trend": None}

        
        # --- Enrichment: ensure price exists when options-only so EM can compute ---
        try:
            if ("options" in include):
                _last = (out.get("price") or {}).get("last")
                if _last is None:
                    try:
                        tq = await tradier.quote_last(symU)
                        if tq.get("price") is not None:
                            out.setdefault("price", {})["last"] = tq.get("price")
                            out["price"]["t"] = tq.get("t")
                    except Exception:
                        try:
                            lt = await poly.last_trade(symU)
                            if lt.get("price") is not None:
                                out.setdefault("price", {})["last"] = lt.get("price")
                                out["price"]["t"] = lt.get("t")
                        except Exception as _e:
                            errs["price.enrich"] = f"{type(_e).__name__}: {_e}"
        except Exception as e:
            errs["price.enrich.outer"] = f"{type(e).__name__}: {e}"

        # --- Regime / Opening (safe when minute_bars absent) ---
        try:
            if "minute_bars" in locals() and minute_bars:
                regime_info = regime_analyze(minute_bars)
                out.setdefault("context", {})
                out["context"]["opening_type"] = regime_info.get("opening_type")
                out["context"]["regime"] = regime_info.get("regime")
        except Exception as e:
            errs["regime"] = f"{type(e).__name__}: {e}"

        # --- Expected Move from near-ATM straddle and hit probabilities ---
        try:
            opts = (out.get("options") or {}).get("top") or []
            _last = (out.get("price") or {}).get("last")
            if opts and _last is not None:
                em_abs, em_rel = expected_move_from_straddle(last_price=float(_last), candidates=opts[:8])
                if em_abs:
                    out.setdefault("context", {})
                    out["context"]["expected_move"] = {"abs": em_abs, "rel": em_rel}
                    for r in opts:
                        r["tradeability"], r["components"] = tradeability_score(r, horizon=horizon)
                        r["hit_probabilities"] = {
                            "tp1": probability_of_touch(distance=em_abs*0.25, sigma_abs=em_abs),
                            "tp2": probability_of_touch(distance=em_abs*0.50, sigma_abs=em_abs)
                        }
        except Exception as e:
            errs["expected_move"] = f"{type(e).__name__}: {e}"
    
        snapshot["symbols"][symU] = out
        if errs: snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
