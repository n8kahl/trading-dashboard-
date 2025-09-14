from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from datetime import datetime, timedelta

from app.services.providers.polygon_market import PolygonMarket
from app.services.providers.tradier import TradierMarket, TradierAuthError, TradierHTTPError
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
    score = 50; details = []
    if features.get("ema_stack_ok"): score += 20; details.append("EMA stack (1>5>9) & price≥VWAP")
    if features.get("vwap_plus1_reclaim"): score += 10; details.append("VWAP+1σ reclaim")
    rv = features.get("rvol_ok")
    if rv: score += 5; details.append(f"RVOL_5 {rv}")
    if features.get("rsi_mid"): score += 5; details.append(f"RSI14 ~ {features.get('rsi_val')}")
    if features.get("macd_up"): score += 5; details.append("MACD hist rising")
    if features.get("contract_ema_up"): score += 5; details.append("Contract EMA1>EMA5")
    if features.get("spread_stable"): score += 3; details.append("Spread stability ok")
    if features.get("spread_bad"): score -= 10; details.append("Spread too wide")
    return {"score": max(0, min(100, score)), "details": details}

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op"); args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use {SUPPORTED_OPS}")

    symbols: List[str] = args.get("symbols") or []
    if not symbols: raise HTTPException(status_code=400, detail="args.symbols (array) required")
    horizon: str = (args.get("horizon") or "intraday").lower()
    include = set(args.get("include") or ["price","history","indicators","levels","micro","options","account","market"])

    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    session_mode = (hist_spec.get("session") or "today").lower()  # NEW: "today" | "prev"
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

        # PRICE (Tradier -> Polygon fallback)
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

        # HISTORY & INDICATORS
        minute_bars = []; fivem_bars = []; daily_bars = []
        try:
            # intraday
            if bars_kind in ("1m","5m"):
                # today first
                try:
                    if bars_kind == "1m":
                        minute_bars = await poly.minute_bars_today(symU)
                    else:
                        fivem_bars = await poly.five_minute_bars_today(symU)
                except Exception as e:
                    errs[f"history.{bars_kind}"] = f"{type(e).__name__}: {e}"

                # if session=prev or nothing today, get previous session 5m as fallback
                if session_mode == "prev" or (not minute_bars and not fivem_bars):
                    try:
                        fivem_prev = await poly.five_minute_bars_prev_session(symU)
                        if fivem_prev and not fivem_bars:
                            fivem_bars = fivem_prev
                    except Exception as e:
                        errs["history.prev"] = f"{type(e).__name__}: {e}"

            # daily (with cache/backoff)
            try:
                daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 220))
            except Exception as e:
                errs["history.daily"] = f"{type(e).__name__}: {e}"
        except Exception as e:
            errs["history"] = f"{type(e).__name__}: {e}"

        # INDICATORS (underlying)
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

        # LEVELS (VWAP ± σ, pivots, hod/lod)
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

        # MICRO
        try:
            micro = {"rvol_5": rvol_5min(minute_bars) if minute_bars else None}
            micro["liq_score"] = None if micro["rvol_5"] is None else round(min(1.0, (micro["rvol_5"]/2.0)), 2)
            out["micro"] = micro
        except Exception as e:
            errs["micro"] = f"{type(e).__name__}: {e}"; out["micro"] = {}

        # OPTIONS (unchanged server scoring; symbol now filled by provider)
        out["options"] = {"expiry": expiry, "top": []}
        try:
            snap = await poly.snapshot_option_chain(symU, limit=250, max_pages=6)
            out["options"]["top"] = []
            for r in (snap.get("results") or []):
                o = r.get("details") or {}
                q = r.get("last_quote") or {}
                t = r.get("last_trade") or {}
                g = r.get("greeks") or {}
                oi = r.get("open_interest") or {}
                iv = r.get("implied_volatility") or {}
                meta = r.get("options") or {}
                symbol_opt = meta.get("symbol")
                a, b = q.get("ask"), q.get("bid")
                sp = (round(((a-b)/a)*100, 2) if (a and a>0 and b is not None) else None)
                out["options"]["top"].append({
                    "symbol": symbol_opt,
                    "type": ("call" if meta.get("contract_type")=="call" else "put"),
                    "strike": meta.get("strike_price") or o.get("strike_price"),
                    "expiry": meta.get("expiration_date") or o.get("expiration_date"),
                    "bid": b, "ask": a, "last": (t.get("price") or r.get("day",{}).get("close")),
                    "delta": g.get("delta"), "gamma": g.get("gamma"), "theta": g.get("theta"),
                    "iv": iv.get("iv") if isinstance(iv, dict) else iv,
                    "oi": (oi.get("oi") if isinstance(oi, dict) else oi),
                    "volume": r.get("day",{}).get("volume"),
                    "spread_pct": sp,
                    "bars": {"tf": None, "count": 0}
                })
            # Keep your sorting/scoring if you want; this returns raw top list
            out["options"]["top"] = out["options"]["top"][:6]
        except Exception as e:
            errs["options"] = f"{type(e).__name__}: {e}"

        # CONFIDENCE stub (kept as-is)
        out["regime"] = {"trend": None}
        out["confidence"] = {"score": 50, "details": []}

        snapshot["symbols"][symU] = out
        if errs: snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
