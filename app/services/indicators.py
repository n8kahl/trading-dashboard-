from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import math
from statistics import median

def ema(values: List[float], period: int) -> Optional[float]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) < period or period <= 0:
        return None
    k = 2/(period+1)
    e = vals[0]
    for v in vals[1:]:
        e = v*k + e*(1-k)
    return round(e, 4)

def sma(values: List[float], period: int) -> Optional[float]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) < period or period <= 0:
        return None
    return round(sum(vals[-period:]) / period, 4)

def atr14(daily: List[Dict[str, Any]]) -> Optional[float]:
    if len(daily) < 15:
        return None
    trs = []
    prev_c = daily[0]["c"]
    for i in range(1,len(daily)):
        h,l,c = daily[i]["h"], daily[i]["l"], daily[i]["c"]
        tr = max(h-l, abs(h-prev_c), abs(l-prev_c))
        trs.append(tr)
        prev_c = c
    if len(trs) < 14:
        return None
    a = sum(trs[:14]) / 14
    for tr in trs[14:]:
        a = (a*13 + tr)/14
    return round(a, 4)

def _sigma(values: List[float]) -> Optional[float]:
    n = len(values)
    if n < 2: return None
    mu = sum(values)/n
    var = sum((x-mu)*(x-mu) for x in values) / (n-1)
    return math.sqrt(var)

def session_vwap_and_sigma(minute_like_bars: List[Dict[str,Any]]) -> Tuple[Optional[float], Optional[float]]:
    """
    VWAP & σ from any intraday bar list (1m or 5m). 
    VWAP uses volume weight if available; otherwise price-only average of tp.
    σ is stddev of tp (unweighted).
    """
    bars = minute_like_bars or []
    if not bars:
        return None, None
    tps, vols = [], []
    for b in bars:
        h = b.get("h") or 0.0
        l = b.get("l") or 0.0
        c = b.get("c") or 0.0
        v = b.get("v") or 0.0
        tp = (h + l + c) / 3.0
        tps.append(tp); vols.append(v)
    s_vol = sum(vols)
    if s_vol and s_vol > 0:
        vwap = sum(tps[i]*vols[i] for i in range(len(tps))) / s_vol
    else:
        vwap = sum(tps)/len(tps)
    sig = _sigma(tps)
    return round(vwap, 4), (round(sig,4) if sig is not None else None)
