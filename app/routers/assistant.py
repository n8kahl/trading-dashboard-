from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from datetime import datetime, timedelta

from app.services.providers.polygon_market import PolygonMarket
from app.services.providers.tradier_chain import options_chain
from app.services.indicators import ema, sma, atr14, session_vwap_and_sigma, pivots_classic, rvol_5min

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

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op"); args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use {SUPPORTED_OPS}")

    symbols: List[str] = args.get("symbols") or []
    if not symbols:
        raise HTTPException(status_code=400, detail="args.symbols (array) required")
    horizon: str = (args.get("horizon") or "intraday").lower()
    include = set(args.get("include") or ["price","history","indicators","levels","micro","options","account"])

    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    lookback = int(hist_spec.get("lookback") or (30 if bars_kind=="1m" else 90 if bars_kind=="5m" else 120))

    opt_spec = args.get("options") or {}
    expiry = opt_spec.get("expiry") or _auto_expiry(horizon)
    topK = int(opt_spec.get("topK") or 6)
    max_spread = float(opt_spec.get("maxSpreadPct") or 8.0)
    greeks = bool(opt_spec.get("greeks") if opt_spec.get("greeks") is not None else True)

    poly = PolygonMarket()
    snapshot: Dict[str, Any] = {"symbols": {}, "account": {}, "errors": {}}

    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str, Any] = {}
        errs: Dict[str, Any] = {}

        # PRICE
        if "price" in include:
            try:
                lt = await poly.last_trade(symU)
                out["price"] = {"last": lt.get("price"), "t": lt.get("t")}
            except Exception as e:
                out["price"] = {"last": None, "t": None}
                errs["price"] = f"{type(e).__name__}: {e}"

        # HISTORY FETCH
        minute_bars = []; daily_bars = []
        if any(k in include for k in ("history","indicators","levels","micro")):
            if bars_kind in ("1m","5m"):
                try:
                    minute_bars = await poly.minute_bars_today(symU)
                except Exception as e:
                    errs["minute_bars"] = f"{type(e).__name__}: {e}"
            if bars_kind == "1D" or "indicators" in include or "levels" in include:
                try:
                    daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 220))
                except Exception as e:
                    errs["daily_bars"] = f"{type(e).__name__}: {e}"

        # INDICATORS
        ind: Dict[str, Any] = {"ema1": None, "ema5": None, "ema9": None, "ema20": None, "ema50": None, "sma200": None, "atr14": None}
        try:
            # intraday EMAs (1,5,9,20) computed off minute/5m closes
            if minute_bars:
                closes_m = [b["c"] for b in minute_bars if b.get("c") is not None]
                ind["ema1"]  = ema(closes_m, 1)   # equals last close; explicit for clarity
                ind["ema5"]  = ema(closes_m, 5)
                ind["ema9"]  = ema(closes_m, 9)
                ind["ema20"] = ema(closes_m, 20)
            else:
                # fallback to daily closes for ema9/20 if no intraday history
                if daily_bars:
                    closes_d = [d["c"] for d in daily_bars if d.get("c") is not None]
                    ind["ema9"]  = ema(closes_d, 9)
                    ind["ema20"] = ema(closes_d, 20)
            # daily trend EMAs/SMAs
            if daily_bars:
                closes_d = [d["c"] for d in daily_bars if d.get("c") is not None]
                ind["ema50"]  = ema(closes_d, 50)
                ind["sma200"] = sma(closes_d, 200)
                ind["atr14"]  = atr14(daily_bars)
        except Exception as e:
            errs["indicators"] = f"{type(e).__name__}: {e}"
        out["indicators"] = ind

        # LEVELS (VWAP, ±1σ, HOD/LOD, prev day pivots)
        levels: Dict[str, Any] = {}
        try:
            vwap, sigma = session_vwap_and_sigma(minute_bars) if minute_bars else (None, None)
            levels["vwap_session"] = vwap
            if vwap is not None and sigma is not None:
                levels["vwap_bands"] = {"minus1": round(vwap - sigma, 4), "plus1": round(vwap + sigma, 4)}
                levels["basis"] = "session VWAP from 1m bars; σ=std(tp), tp=(H+L+C)/3"
            if minute_bars:
                highs = [b.get("h") for b in minute_bars if b.get("h") is not None]
                lows  = [b.get("l") for b in minute_bars if b.get("l") is not None]
                if highs: levels["hod"] = round(max(highs), 4)
                if lows:  levels["lod"] = round(min(lows), 4)
            if len(daily_bars) >= 2:
                prev = daily_bars[-2]
                prev_day = {"o": prev["o"], "h": prev["h"], "l": prev["l"], "c": prev["c"]}
                levels["prev_day"] = prev_day
                levels["pivots"] = pivots_classic(prev_day)
        except Exception as e:
            errs["levels"] = f"{type(e).__name__}: {e}"
        out["levels"] = levels

        # MICRO
        try:
            micro: Dict[str, Any] = {}
            micro["rvol_5"] = rvol_5min(minute_bars) if minute_bars else None
            micro["spread_pct"] = None
            rv = micro["rvol_5"]
            micro["liq_score"] = None if rv is None else round(min(1.0, rv/2.0), 2)
            out["micro"] = micro
        except Exception as e:
            errs["micro"] = f"{type(e).__name__}: {e}"
            out["micro"] = {}

        # HISTORY payload
        if "history" in include:
            try:
                if bars_kind == "5m" and minute_bars:
                    items = []
                    bucket = []
                    for b in minute_bars:
                        bucket.append(b)
                        if len(bucket) == 5:
                            o = bucket[0]["o"]; h = max(x["h"] for x in bucket)
                            l = min(x["l"] for x in bucket); c = bucket[-1]["c"]
                            v = sum((x.get("v") or 0) for x in bucket); t = bucket[-1]["t"]
                            items.append([t,o,h,l,c,v]); bucket = []
                    out["history"] = {"bars": "5m", "items": items[-90:]}
                elif bars_kind == "1m" and minute_bars:
                    items = [[b["t"],b["o"],b["h"],b["l"],b["c"],b["v"]] for b in minute_bars[-30:]]
                    out["history"] = {"bars": "1m", "items": items}
                elif bars_kind == "1D" and daily_bars:
                    items = [[d["t"],d["o"],d["h"],d["l"],d["c"],d["v"]] for d in daily_bars[-120:]]
                    out["history"] = {"bars": "1D", "items": items}
            except Exception as e:
                errs["history"] = f"{type(e).__name__}: {e}"

        # OPTIONS topK
        if "options" in include:
            try:
                chain = await options_chain(symU, expiry, greeks=greeks)
                for c in chain:
                    bid, ask = c.get("bid"), c.get("ask")
                    sp = None
                    try:
                        if ask and ask > 0 and bid is not None:
                            sp = round(((ask - bid)/ask)*100.0, 2)
                    except Exception:
                        sp = None
                    pop = int(round(abs(c["delta"])*100)) if c.get("delta") is not None else None
                    c["spread_pct"] = sp; c["pop_pct"] = pop
                def _score(c):
                    target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
                    d = c.get("delta")
                    if d is None: return -1e9
                    penalty = 1.0 if (c.get("spread_pct") is not None and c["spread_pct"] > max_spread) else 0.0
                    oi_bonus = min(c.get("oi") or 0, 3000)/30000.0
                    return -(abs(abs(d)-target)) - penalty + oi_bonus
                top = sorted(chain, key=_score, reverse=True)[:topK]
                out["options"] = {"expiry": expiry, "top": top}
            except Exception as e:
                out["options"] = {"expiry": expiry, "top": []}
                snapshot["errors"].setdefault(symU, {})["options"] = f"{type(e).__name__}: {e}"

        # REGIME (can use new MAs later)
        trend = None
        try:
            e9 = out.get("indicators",{}).get("ema9")
            e20= out.get("indicators",{}).get("ema20")
            if e9 is not None and e20 is not None:
                trend = "up" if e9 > e20 else "down"
        except Exception:
            pass
        out["regime"] = {"trend": trend, "volatility": None}

        snapshot["symbols"][symU] = out
        if errs:
            snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
