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
    # Underlying signal gates
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
    # Option micro
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
    greeks = True if opt_spec.get("greeks") is None else bool(opt_spec.get("greeks"))

    poly = PolygonMarket()
    snapshot: Dict[str, Any] = {"symbols": {}, "account": {}, "errors": {}}

    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    # TODO: optionally add market VIX fetch if you have it wired elsewhere
    # snapshot["market"] = {"vix": None, "vix_d": None}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str, Any] = {}
        errs: Dict[str, Any] = {}

        # PRICE
        last_price = None; last_t = None
        try:
            lt = await poly.last_trade(symU)
            last_price, last_t = lt.get("price"), lt.get("t")
        except Exception as e:
            errs["price.last_trade"] = f"{type(e).__name__}: {e}"
        out["price"] = {"last": last_price, "t": last_t}

        # HISTORY: 1m→5m fallback; daily always
        minute_bars = []; fivem_bars = []; daily_bars = []
        try:
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
            daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 220))
        except Exception as e:
            errs["history"] = f"{type(e).__name__}: {e}"

        if last_price is None and daily_bars:
            out["price"]["last"] = daily_bars[-1].get("c"); out["price"]["t"] = daily_bars[-1].get("t")
            errs.setdefault("price.fallback", "used last daily close")

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
            elif closes_d:
                ind["ema1"]  = ema(closes_d, 1)
                ind["ema5"]  = ema(closes_d, 5)
                ind["ema9"]  = ema(closes_d, 9)
                ind["ema20"] = ema(closes_d, 20)
            if closes_d:
                ind["ema50"]  = ema(closes_d, 50)
                ind["sma200"] = sma(closes_d, 200)
                ind["atr14"]  = atr14(daily_bars)
                ind["rsi14"]  = rsi(closes_d)
                ind["macd"]   = macd(closes_d)
        except Exception as e:
            errs["indicators"] = f"{type(e).__name__}: {e}"
        out["indicators"] = ind

        # LEVELS: VWAP from 1m→5m; debug info
        levels: Dict[str, Any] = {}
        try:
            bars_for_vwap = minute_bars if minute_bars else fivem_bars
            src = "1m" if minute_bars else ("5m" if fivem_bars else None)
            vwap, sigma = session_vwap_and_sigma(bars_for_vwap) if bars_for_vwap else (None, None)
            if vwap is not None: levels["vwap_session"] = vwap
            if vwap is not None and sigma is not None:
                levels["vwap_bands"] = {"minus1": round(vwap - sigma, 4), "plus1": round(vwap + sigma, 4)}
            if src: levels["debug"] = {"source": src, "bar_count": len(bars_for_vwap)}
            use_bars = minute_bars if minute_bars else fivem_bars
            if use_bars:
                highs = [b.get("h") for b in use_bars if b.get("h") is not None]
                lows  = [b.get("l") for b in use_bars if b.get("l") is not None]
                if highs: levels["hod"] = round(max(highs), 4)
                if lows:  levels["lod"] = round(min(lows), 4)
            if len(daily_bars) >= 2:
                prev = daily_bars[-2]; prev_day = {"o": prev["o"], "h": prev["h"], "l": prev["l"], "c": prev["c"]}
                levels["prev_day"] = prev_day
                levels["pivots"] = pivots_classic(prev_day)
        except Exception as e:
            errs["levels"] = f"{type(e).__name__}: {e}"
        out["levels"] = levels

        # MICRO (underlying)
        try:
            micro = {}
            micro["rvol_5"] = rvol_5min(minute_bars) if minute_bars else None
            micro["liq_score"] = None if micro["rvol_5"] is None else round(min(1.0, micro["rvol_5"]/2.0), 2)
            out["micro"] = micro
        except Exception as e:
            errs["micro"] = f"{type(e).__name__}: {e}"
            out["micro"] = {}

        # OPTIONS — Snapshot + contract custom bars for topK scoring
        out["options"] = {"expiry": expiry, "top": []}
        try:
            snap = await poly.snapshot_option_chain(symU, limit=2000)
            results = snap.get("results") or []
            # Basic filter: same expiry if provided; otherwise let GPT choose later
            candidates = []
            for r in results:
                o = r.get("details") or {}
                q = r.get("last_quote") or {}
                t = r.get("last_trade") or {}
                g = r.get("greeks") or {}
                oi = r.get("open_interest") or {}
                iv = r.get("implied_volatility") or {}
                meta = r.get("options") or {}
                symbol_opt = meta.get("symbol") or o.get("symbol") or r.get("ticker")
                a, b = q.get("ask"), q.get("bid")
                sp = (round(((a-b)/a)*100, 2) if (a and a>0 and b is not None) else None)
                item = {
                    "symbol": symbol_opt,
                    "type": ("call" if meta.get("contract_type")=="call" else "put"),
                    "strike": meta.get("strike_price") or o.get("strike_price"),
                    "expiry": meta.get("expiration_date") or o.get("expiration_date"),
                    "bid": b, "ask": a, "last": (t.get("price") or r.get("day",{}).get("close")),
                    "delta": g.get("delta"), "gamma": g.get("gamma"), "theta": g.get("theta"),
                    "iv": iv.get("iv") if isinstance(iv, dict) else iv,  # handles shape variance
                    "oi": (oi.get("oi") if isinstance(oi, dict) else oi),
                    "volume": r.get("day",{}).get("volume"),
                    "spread_pct": sp,
                    "pop_pct": (int(round(abs(g.get("delta") or 0)*100)) if g.get("delta") is not None else None)
                }
                candidates.append(item)

            # keep only reasonable spread and OI first pass
            prelim = [c for c in candidates if (c["spread_pct"] is None or c["spread_pct"] <= max_spread)]
            prelim = [c for c in prelim if (c["oi"] is None or c["oi"] >= 100)]  # loose floor for snapshot

            # For top 12 by |delta| proximity to target, fetch contract bars & add micro
            delta_target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
            prelim = sorted(prelim, key=lambda c: (1e9 if c["delta"] is None else abs(abs(c["delta"])-delta_target)))[:12]

            enriched = []
            for c in prelim:
                try:
                    bars = await poly.option_custom_bars(c["symbol"], mult=1, timespan="minute", lookback_minutes=120)
                    if not bars:
                        bars = await poly.option_custom_bars(c["symbol"], mult=5, timespan="minute", lookback_minutes=240)
                    closes = [b["c"] for b in bars if b.get("c") is not None]
                    bids = [c["bid"]] * len(bars)  # if no historical quotes, approximate stability w/ current
                    asks = [c["ask"]] * len(bars)
                    vwap_c, sig_c = session_vwap_and_sigma(bars) if bars else (None, None)
                    ema1_c = ema(closes, 1) if closes else None
                    ema5_c = ema(closes, 5) if closes else None
                    stab = spread_stability(bids, asks)
                    c.update({
                        "bars": {"tf": "1m" if bars and len(bars)>0 else None, "count": len(bars)},
                        "contract_vwap": vwap_c,
                        "contract_sigma": sig_c,
                        "contract_indicators": {"ema1": ema1_c, "ema5": ema5_c},
                        "micro": {"spread_stability": stab}
                    })
                    enriched.append(c)
                except Exception as e:
                    c.update({"bars": {"tf": None, "count": 0}})
                    enriched.append(c)

            def _score(c):
                d = c.get("delta")
                if d is None: return -1e9
                target = delta_target
                spread = c.get("spread_pct")
                penalty = 0.0
                if spread is not None and spread > max_spread: penalty += 4.0
                oi_bonus = min(c.get("oi") or 0, 3000)/30000.0
                stab = (c.get("micro",{}).get("spread_stability") or 0.5) - 0.5  # -0.5..+0.5
                align = 0.0
                last = c.get("last")
                vwapc = c.get("contract_vwap")
                typ = c.get("type")
                if last and vwapc:
                    if typ=="call" and last>=vwapc: align = 0.5
                    if typ=="put"  and last<=vwapc: align = 0.5
                return -(abs(abs(d)-target))*2.0 - penalty + oi_bonus + stab + align

            top = sorted(enriched, key=_score, reverse=True)[:topK]
            out["options"] = {"expiry": expiry, "top": top}
        except Exception as e:
            errs["options"] = f"{type(e).__name__}: {e}"

        # REGIME + confidence
        features = {}
        e1,e5,e9,e20 = (out["indicators"].get("ema1"), out["indicators"].get("ema5"),
                        out["indicators"].get("ema9"), out["indicators"].get("ema20"))
        vwap = out.get("levels",{}).get("vwap_session")
        features["ema_stack_ok"] = (e1 is not None and e5 is not None and e9 is not None and vwap is not None and (e1>e5>e9) and (out["price"]["last"] or 0) >= vwap)
        bands = out.get("levels",{}).get("vwap_bands") or {}
        plus1 = bands.get("plus1")
        features["vwap_plus1_reclaim"] = (plus1 is not None and (out["price"]["last"] or 0) >= plus1)
        rv = out.get("micro",{}).get("rvol_5")
        features["rvol_ok"] = rv if (rv is not None and rv >= 1.3) else None
        rsi_v = out["indicators"].get("rsi14")
        features["rsi_mid"] = (rsi_v is not None and 45 <= rsi_v <= 65); features["rsi_val"] = rsi_v
        mac = out["indicators"].get("macd")
        features["macd_up"] = (mac is not None and mac.get("hist",0) > 0)
        # Option micro from top[0] if exists
        if out.get("options",{}).get("top"):
            c0 = out["options"]["top"][0]
            ce1 = (c0.get("contract_indicators",{}).get("ema1"))
            ce5 = (c0.get("contract_indicators",{}).get("ema5"))
            features["contract_ema_up"] = (ce1 is not None and ce5 is not None and ce1 > ce5)
            stab = c0.get("micro",{}).get("spread_stability")
            features["spread_stable"] = (stab is not None and stab >= 0.7)
            spread = c0.get("spread_pct")
            features["spread_bad"] = (spread is not None and spread > max_spread)

        conf = _conf_score(features, horizon)
        out["regime"] = {"trend": ("up" if (e9 is not None and e20 is not None and e9>e20) else "down" if (e9 is not None and e20 is not None) else None)}
        out["confidence"] = conf

        snapshot["symbols"][symU] = out
        if errs: snapshot["errors"][symU] = errs

    return {"ok": True, "snapshot": snapshot}
