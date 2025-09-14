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
    include = set(args.get("include") or ["price","history","indicators","levels","micro","options","account"])

    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    lookback = int(hist_spec.get("lookback") or (30 if bars_kind=="1m" else 90 if bars_kind=="5m" else 120))

    opt_spec = args.get("options") or {}
    expiry = _normalize_expiry(opt_spec.get("expiry"), horizon)
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

        # PRICE (daily fallback)
        last_price = None; last_t = None
        if "price" in include:
            try:
                lt = await poly.last_trade(symU)
                last_price, last_t = lt.get("price"), lt.get("t")
            except Exception as e:
                errs["price.last_trade"] = f"{type(e).__name__}: {e}"
        out["price"] = {"last": last_price, "t": last_t}

        # HISTORY FETCH (1m → fallback 5m; daily always)
        minute_bars = []; fivem_bars = []; daily_bars = []
        if any(k in include for k in ("history","indicators","levels","micro")):
            if bars_kind in ("1m","5m"):
                try:
                    minute_bars = await poly.minute_bars_today(symU)
                except Exception as e:
                    errs["history.1m"] = f"{type(e).__name__}: {e}"
                if not minute_bars:
                    try:
                        fivem_bars = await poly.five_minute_bars_today(symU)
                    except Exception as e:
                        errs["history.5m"] = f"{type(e).__name__}: {e}"
            try:
                daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 220))
            except Exception as e:
                errs["history.1D"] = f"{type(e).__name__}: {e}"

        # fallback price from daily
        if last_price is None and daily_bars:
            out["price"]["last"] = daily_bars[-1].get("c")
            out["price"]["t"] = daily_bars[-1].get("t")
            errs.setdefault("price.fallback", "used last daily close")

        # INDICATORS (EMA1/5/9/20 from minute if present; else 5m; else daily)
        ind: Dict[str, Any] = {"ema1": None, "ema5": None, "ema9": None, "ema20": None, "ema50": None, "sma200": None, "atr14": None}
        try:
            if minute_bars:
                closes = [b["c"] for b in minute_bars if b.get("c") is not None]
            elif fivem_bars:
                closes = [b["c"] for b in fivem_bars if b.get("c") is not None]
            else:
                closes = []
            closes_d = [d["c"] for d in daily_bars if d.get("c") is not None]

            if closes:
                ind["ema1"]  = ema(closes, 1)
                ind["ema5"]  = ema(closes, 5)
                ind["ema9"]  = ema(closes, 9)
                ind["ema20"] = ema(closes, 20)
            elif closes_d:
                # last-resort from daily
                ind["ema1"]  = ema(closes_d, 1)
                ind["ema5"]  = ema(closes_d, 5)
                ind["ema9"]  = ema(closes_d, 9)
                ind["ema20"] = ema(closes_d, 20)

            if closes_d:
                ind["ema50"]  = ema(closes_d, 50)
                ind["sma200"] = sma(closes_d, 200)
                ind["atr14"]  = atr14(daily_bars)
        except Exception as e:
            errs["indicators"] = f"{type(e).__name__}: {e}"
        out["indicators"] = ind

        # LEVELS: VWAP from 1m; fallback to 5m aggregates for VWAP±σ; HOD/LOD from whichever we have
        levels: Dict[str, Any] = {}
        try:
            bars_for_vwap = minute_bars if minute_bars else fivem_bars
            vwap, sigma = session_vwap_and_sigma(bars_for_vwap) if bars_for_vwap else (None, None)
            levels["vwap_session"] = vwap
            if vwap is not None and sigma is not None:
                levels["vwap_bands"] = {"minus1": round(vwap - sigma, 4), "plus1": round(vwap + sigma, 4)}
                levels["basis"] = "session VWAP from aggregate bars; σ=std(tp), tp=(H+L+C)/3"
            use_bars = minute_bars if minute_bars else fivem_bars
            if use_bars:
                highs = [b.get("h") for b in use_bars if b.get("h") is not None]
                lows  = [b.get("l") for b in use_bars if b.get("l") is not None]
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
            base_for_rvol = minute_bars if minute_bars else []
            micro: Dict[str, Any] = {}
            micro["rvol_5"] = rvol_5min(base_for_rvol) if base_for_rvol else None
            micro["spread_pct"] = None
            rv = micro["rvol_5"]
            micro["liq_score"] = None if rv is None else round(min(1.0, rv/2.0), 2)
            out["micro"] = micro
        except Exception as e:
            errs["micro"] = f"{type(e).__name__}: {e}"
            out["micro"] = {}

        # HISTORY payload (respect requested bars; if 5m requested but we only have 5m, send it)
        if "history" in include:
            try:
                if bars_kind == "5m":
                    if fivem_bars:
                        items = [[b["t"],b["o"],b["h"],b["l"],b["c"],b["v"]] for b in fivem_bars][-90:]
                        out["history"] = {"bars": "5m", "items": items}
                    elif minute_bars:
                        # downsample from 1m if that’s what we have
                        items=[]; bucket=[]
                        for b in minute_bars:
                            bucket.append(b)
                            if len(bucket)==5:
                                o=bucket[0]["o"]; h=max(x["h"] for x in bucket)
                                l=min(x["l"] for x in bucket); c=bucket[-1]["c"]
                                v=sum((x.get("v") or 0) for x in bucket); t=bucket[-1]["t"]
                                items.append([t,o,h,l,c,v]); bucket=[]
                        out["history"] = {"bars": "5m", "items": items[-90:]}
                elif bars_kind == "1m" and minute_bars:
                    items = [[b["t"],b["o"],b["h"],b["l"],b["c"],b["v"]] for b in minute_bars[-30:]]
                    out["history"] = {"bars": "1m", "items": items}
                elif bars_kind == "1D" and daily_bars:
                    items = [[d["t"],d["o"],d["h"],d["l"],d["c"],d["v"]] for d in daily_bars[-120:]]
                    out["history"] = {"bars": "1D", "items": items}
            except Exception as e:
                errs["history"] = f"{type(e).__name__}: {e}"

        # OPTIONS
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
                errs["options"] = f"{type(e).__name__}: {e}"

        # REGIME
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
