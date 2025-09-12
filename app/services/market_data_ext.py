from __future__ import annotations
import os, datetime as dt, math
import httpx
from typing import List, Dict, Any, Optional, Tuple

POLY_KEY = os.getenv("POLYGON_API_KEY")

async def fetch_daily_bars(symbol: str, lookback: int = 120) -> Dict[str, Any]:
    if not POLY_KEY:
        return {"ok": False, "error": "POLYGON_API_KEY not set"}
    end = dt.date.today()
    start = end - dt.timedelta(days=max(lookback*2, lookback+30))
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start.isoformat()}/{end.isoformat()}?adjusted=true&sort=asc&limit=50000&apiKey={POLY_KEY}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return {"ok": False, "error": f"polygon {r.status_code}", "body": r.text}
        js = r.json()
        if js.get("status") != "OK":
            return {"ok": False, "error": f"polygon status {js.get('status')}", "body": js}
        results = js.get("results") or []
        return {"ok": True, "bars": results}

def _ema(vals: List[float], length: int) -> List[Optional[float]]:
    if len(vals) < length: return [None]*len(vals)
    k = 2/(length+1)
    out, ema_val = [], None
    for i,v in enumerate(vals):
        if v is None: out.append(None); continue
        if ema_val is None:
            if i < length-1: out.append(None); continue
            seed = sum(vals[i-length+1:i+1])/length
            ema_val = seed
        ema_val = v*k + ema_val*(1-k)
        out.append(ema_val)
    return out

def _atr_percent(bars: List[Dict[str,Any]], length: int=14) -> Optional[float]:
    if len(bars) < length+1: return None
    trs = []
    prev_close = bars[-length-1]["c"]
    for b in bars[-length:]:
        h,l,c_prev = b["h"], b["l"], prev_close
        tr = max(h-l, abs(h-c_prev), abs(l-c_prev))
        trs.append(tr)
        prev_close = b["c"]
    atr = sum(trs)/length
    last_c = bars[-1]["c"]
    return (atr/last_c)*100 if last_c else None

def _rvol20(bars: List[Dict[str,Any]]) -> Optional[float]:
    if len(bars) < 21: return None
    vols = [b["v"] for b in bars]
    v20 = sum(vols[-21:-1])/20
    v_today = vols[-1]
    return (v_today / v20) if v20 else None

def _pct_change(bars: List[Dict[str,Any]], days: int=5) -> Optional[float]:
    if len(bars) < days+1: return None
    c_now = bars[-1]["c"]; c_ago = bars[-days-1]["c"]
    return ((c_now - c_ago)/c_ago)*100 if c_ago else None

def _trend_features(closes: List[float]) -> Tuple[Optional[float],Optional[float],Optional[float]]:
    ema20 = _ema(closes,20)
    ema50 = _ema(closes,50)
    if not ema20 or not ema50 or ema20[-1] is None or ema50[-1] is None:
        return None, None, None
    price = closes[-1]
    dist20 = ((price - ema20[-1])/ema20[-1])*100 if ema20[-1] else None
    uptrend = 1.0 if ema20[-1] > ema50[-1] else 0.0
    return uptrend, dist20, price

async def score_symbol(symbol: str) -> Dict[str,Any]:
    md = await fetch_daily_bars(symbol, lookback=150)
    if not md.get("ok"):
        return {"symbol": symbol.upper(), "ok": False, "error": md.get("error","bars fetch failed")}
    bars = md["bars"]
    # filter out malformed
    bars = [b for b in bars if all(k in b for k in ("o","h","l","c","v"))]
    if len(bars) < 60:
        return {"symbol": symbol.upper(), "ok": False, "error": "insufficient bars"}

    closes = [b["c"] for b in bars]
    uptrend, dist20, price = _trend_features(closes)
    pct5 = _pct_change(bars, 5)
    rvol = _rvol20(bars)
    atrp = _atr_percent(bars, 14)

    # --- ConfluenceRank (0..100) ---
    score = 50.0
    notes = []

    if uptrend is not None:
        if uptrend >= 0.5: score += 12; notes.append("EMA20>EMA50")
        else: score -= 12; notes.append("EMA20<EMA50")

    if dist20 is not None:
        score += max(-10, min(10, dist20/1.5))
        notes.append(f"dist20={dist20:.2f}%")

    if pct5 is not None:
        score += max(-10, min(10, pct5/2.0))
        notes.append(f"5d%={pct5:.2f}")

    if rvol is not None:
        # prefer rvol in 1.2–3.0 range
        if rvol >= 1.2: score += min(10, (rvol-1.2)*5); notes.append(f"RVOL={rvol:.2f}")
        else: score -= min(8, (1.2-rvol)*6); notes.append(f"RVOL={rvol:.2f}")

    if atrp is not None:
        # penalize extreme low volatility (<1%) and extreme high (>8%) modestly
        if atrp < 1.0: score -= 5; notes.append(f"ATR% low {atrp:.2f}")
        elif atrp > 8.0: score -= 3; notes.append(f"ATR% high {atrp:.2f}")
        else: score += 2; notes.append(f"ATR% ok {atrp:.2f}")

    score = round(max(0, min(100, score))), 
    return {
        "symbol": symbol.upper(), "ok": True,
        "score": float(score[0]),
        "features": {"price": price, "dist20": dist20, "pct5": pct5, "rvol20": rvol, "atr_percent": atrp},
        "rationale": notes
    }
