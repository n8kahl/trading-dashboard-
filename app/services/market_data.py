from __future__ import annotations
import os, time, math, datetime as dt
import httpx

POLY_KEY = os.getenv("POLYGON_API_KEY")

async def fetch_daily_bars(symbol: str, lookback: int = 120):
    if not POLY_KEY:
        return {"ok": False, "error": "POLYGON_API_KEY not set"}
    end = dt.date.today()
    start = end - dt.timedelta(days=max(lookback*2, lookback+30))  # buffer for weekends/holidays
    url = f"https://api.polygon.io/v2/aggs/ticker/{symbol.upper()}/range/1/day/{start.isoformat()}/{end.isoformat()}?adjusted=true&sort=asc&limit=50000&apiKey={POLY_KEY}"
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.get(url)
        if r.status_code != 200:
            return {"ok": False, "error": f"polygon {r.status_code}", "body": r.text}
        js = r.json()
        if js.get("status") != "OK":
            return {"ok": False, "error": f"polygon status {js.get('status')}", "body": js}
        results = js.get("results") or []
        # keep last N
        results = results[-lookback:]
        bars = [{"t": x["t"], "o": x["o"], "h": x["h"], "l": x["l"], "c": x["c"], "v": x["v"]} for x in results]
        return {"ok": True, "bars": bars}

def ema(values, length):
    if not values or len(values) < length:
        return [None]*len(values)
    k = 2/(length+1)
    out = []
    ema_val = None
    for i, v in enumerate(values):
        if v is None:
            out.append(None); continue
        if ema_val is None:
            if i < length-1: 
                out.append(None); 
                continue
            # seed with SMA
            seed = sum([x for x in values[i-length+1:i+1] if x is not None])/length
            ema_val = seed
        ema_val = v*k + ema_val*(1-k)
        out.append(ema_val)
    return out

def rsi(values, length=14):
    if not values or len(values) < length+1: 
        return [None]*len(values)
    gains = [0]; losses = [0]
    for i in range(1, len(values)):
        ch = (values[i] - values[i-1]) if values[i] is not None and values[i-1] is not None else 0
        gains.append(max(ch,0)); losses.append(abs(min(ch,0)))
    rsis = [None]*len(values)
    avg_gain = sum(gains[1:length+1])/length
    avg_loss = sum(losses[1:length+1])/length
    if avg_loss == 0: 
        rsis[length] = 100.0
    else:
        rs = avg_gain/avg_loss
        rsis[length] = 100 - (100/(1+rs))
    for i in range(length+1, len(values)):
        avg_gain = (avg_gain*(length-1) + gains[i]) / length
        avg_loss = (avg_loss*(length-1) + losses[i]) / length
        if avg_loss == 0: 
            rsis[i] = 100.0
        else:
            rs = avg_gain/avg_loss
            rsis[i] = 100 - (100/(1+rs))
    return rsis

def vwap_lite(bars):
    # daily VWAP-lite: typical price * volume / total volume over lookback
    if not bars:
        return None
    vols = [b["v"] for b in bars]
    tps = [(b["h"]+b["l"]+b["c"])/3 for b in bars]
    num = sum(tp*v for tp,v in zip(tps,vols))
    den = sum(vols) or 1.0
    return num/den
