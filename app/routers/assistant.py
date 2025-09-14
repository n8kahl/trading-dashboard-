from __future__ import annotations
from fastapi import APIRouter, HTTPException
from typing import Any, Dict, List
from datetime import datetime, timedelta

from app.services.providers.polygon_market import PolygonMarket
from app.services.providers.tradier_chain import options_chain
from app.services.indicators import ema, atr14, session_vwap_and_sigma, pivots_classic, rvol_5min

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

SUPPORTED_OPS = ["data.snapshot"]  # single op; GPT builds strategies from the snapshot

@router.get("/actions")
async def assistant_actions():
    return {"ok": True, "ops": SUPPORTED_OPS}

def _auto_expiry(hz: str) -> str:
    today = datetime.utcnow().date()
    if hz in ("scalp","intraday"):
        # nearest Fri (weekly). If today is Fri, use next Fri
        days = (4 - today.weekday()) % 7 or 7
        return str(today + timedelta(days=days))
    # swing: ~2 weeks out
    return str(today + timedelta(days=14))

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]):
    op = payload.get("op")
    args = payload.get("args") or {}
    if op not in SUPPORTED_OPS:
        raise HTTPException(status_code=400, detail=f"Unsupported op '{op}'. Use {SUPPORTED_OPS}")

    symbols: List[str] = args.get("symbols") or []
    if not symbols: raise HTTPException(status_code=400, detail="args.symbols (array) required")
    horizon: str = (args.get("horizon") or "intraday").lower()

    include = set((args.get("include") or ["price","history","indicators","levels","micro","options","account"]))
    hist_spec = args.get("history") or {}
    bars_kind = hist_spec.get("bars") or ("1m" if horizon=="scalp" else "5m" if horizon=="intraday" else "1D")
    lookback = int(hist_spec.get("lookback") or (30 if bars_kind=="1m" else 90 if bars_kind=="5m" else 120))

    opt_spec = args.get("options") or {}
    expiry = opt_spec.get("expiry") or _auto_expiry(horizon)
    topK = int(opt_spec.get("topK") or 6)
    side = (opt_spec.get("side") or "long").lower()
    max_spread = float(opt_spec.get("maxSpreadPct") or 8.0)
    greeks = bool(opt_spec.get("greeks") if opt_spec.get("greeks") is not None else True)

    # helpers
    def _score_contract(c: Dict[str,Any]) -> float:
        # target deltas per horizon (calls positive, puts negative if short side later)
        target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
        d = c.get("delta")
        if d is None: return -1e9
        spread = None
        try:
            if c.get("ask"): spread = ((c["ask"] - (c.get("bid") or 0)) / c["ask"]) * 100.0
        except Exception:
            spread = None
        penalty = 1.0 if (spread is not None and spread > max_spread) else 0.0
        oi_bonus = min(c.get("oi") or 0, 3000)/30000.0
        return -(abs(abs(d) - target)) - penalty + oi_bonus

    poly = PolygonMarket()
    snapshot: Dict[str,Any] = {"symbols": {}, "account": {}}

    # NOTE: account redacted/omitted here unless you wire Tradier account
    if "account" in include:
        snapshot["account"] = {"bp": None, "risk_rules": {"max_day_r": -2.0, "max_concurrent": 3}, "positions": []}

    for sym in symbols:
        symU = sym.upper()
        out: Dict[str,Any] = {}

        # PRICE + HISTORY
        last = await poly.last_trade(symU) if "price" in include else {"price": None, "t": None}
        out["price"] = {"last": last.get("price"), "t": last.get("t")}

        # History: minute or daily
        minute_bars = []
        daily_bars = []
        if "history" in include or "indicators" in include or "levels" in include or "micro" in include:
            if bars_kind in ("1m","5m"):  # we only fetch 1m; GPT asked for 5m but we’ll downsample in-place
                minute_bars = await poly.minute_bars_today(symU)
            if bars_kind == "1D" or "indicators" in include:
                daily_bars = await poly.daily_bars(symU, lookback=max(lookback, 60))

        # INDICATORS
        em9 = em20 = atr = None
        if "indicators" in include:
            closes = [b["c"] for b in minute_bars[-max(60,lookback):]] if bars_kind in ("1m","5m") else [d["c"] for d in daily_bars[-60:]]
            em9  = ema(closes, 9) if closes else None
            em20 = ema(closes, 20) if closes else None
            atr  = atr14(daily_bars) if daily_bars else None
        out["indicators"] = {"ema9": em9, "ema20": em20, "atr14": atr}

        # LEVELS (VWAP, VWAP ± 1σ bands, HOD/LOD, prev day, pivots)
        levels: Dict[str,Any] = {}
        if "levels" in include:
            vwap, sigma = session_vwap_and_sigma(minute_bars)
            levels["vwap_session"] = vwap
            if vwap is not None and sigma is not None:
                levels["vwap_bands"] = {
                    "minus1": round(vwap - sigma, 4),
                    "plus1":  round(vwap + sigma, 4)
                }
                levels["basis"] = "session VWAP from 1m bars; σ = std(tp), tp=(H+L+C)/3"
            if minute_bars:
                highs = [b["h"] for b in minute_bars if b["h"] is not None]
                lows  = [b["l"] for b in minute_bars if b["l"] is not None]
                if highs: levels["hod"] = round(max(highs), 4)
                if lows:  levels["lod"] = round(min(lows), 4)
            prev = daily_bars[-2] if len(daily_bars) >= 2 else None
            if prev:
                prev_day = {"o": prev["o"], "h": prev["h"], "l": prev["l"], "c": prev["c"]}
                levels["prev_day"] = prev_day
                levels["pivots"] = pivots_classic(prev_day)
        out["levels"] = levels

        # MICRO (RVOL, spread on stock if you later wire NBBO)
        micro: Dict[str,Any] = {}
        if "micro" in include:
            micro["rvol_5"] = rvol_5min(minute_bars)
            micro["spread_pct"] = None  # placeholder (wire NBBO if desired)
            # crude liquidity score (use RVOL only for now)
            rv = micro["rvol_5"]
            micro["liq_score"] = None if rv is None else round(min(1.0, rv/2.0), 2)
        out["micro"] = micro

        # HISTORY payload (downsample if user asked 5m)
        if "history" in include:
            if bars_kind == "5m" and minute_bars:
                # downsample: sum V, O/H/L/C from 5x1m groups
                items = []
                bucket = []
                for b in minute_bars:
                    bucket.append(b)
                    if len(bucket) == 5:
                        o = bucket[0]["o"]; h = max(x["h"] for x in bucket)
                        l = min(x["l"] for x in bucket); c = bucket[-1]["c"]
                        v = sum((x["v"] or 0) for x in bucket); t = bucket[-1]["t"]
                        items.append([t,o,h,l,c,v]); bucket = []
                out["history"] = {"bars": "5m", "items": items[-90:]}
            elif bars_kind == "1m" and minute_bars:
                items = [[b["t"],b["o"],b["h"],b["l"],b["c"],b["v"]] for b in minute_bars[-30:]]
                out["history"] = {"bars": "1m", "items": items}
            elif bars_kind == "1D" and daily_bars:
                items = [[d["t"],d["o"],d["h"],d["l"],d["c"],d["v"]] for d in daily_bars[-120:]]
                out["history"] = {"bars": "1D", "items": items}

        # OPTIONS topK (Tradier)
        if "options" in include:
            contracts: List[Dict[str,Any]] = []
            try:
                chain = await options_chain(symU, expiry, greeks=greeks)
                # annotate + score + trim
                for c in chain:
                    bid, ask = c.get("bid"), c.get("ask")
                    sp = None
                    try:
                        if ask and ask > 0 and bid is not None:
                            sp = round(((ask - bid)/ask)*100.0, 2)
                    except Exception:
                        sp = None
                    pop = None
                    if c.get("delta") is not None:
                        pop = int(round(abs(c["delta"])*100))
                    c["spread_pct"] = sp
                    c["pop_pct"] = pop
                # simple ranking
                def _score(c):
                    target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
                    d = c.get("delta")
                    if d is None: return -1e9
                    penalty = 1.0 if (c.get("spread_pct") is not None and c["spread_pct"] > max_spread) else 0.0
                    oi_bonus = min(c.get("oi") or 0, 3000)/30000.0
                    return -(abs(abs(d)-target)) - penalty + oi_bonus
                contracts = sorted(chain, key=_score, reverse=True)[:topK]
            except Exception:
                contracts = []
            out["options"] = {"expiry": expiry, "top": contracts} if contracts else {"expiry": expiry, "top": []}

        # REGIME (very light, GPT can augment)
        trend = None
        if out["indicators"]["ema9"] is not None and out["indicators"]["ema20"] is not None:
            trend = "up" if out["indicators"]["ema9"] > out["indicators"]["ema20"] else "down"
        out["regime"] = {"trend": trend, "volatility": None}

        # Done
        snapshot["symbols"][symU] = out

    return {"ok": True, "snapshot": snapshot}
