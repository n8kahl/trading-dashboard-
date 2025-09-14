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
    s = sum(vals[-period:]) / period
    return round(s, 4)

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

def session_vwap_and_sigma(minute_bars: List[Dict[str,Any]]) -> Tuple[Optional[float], Optional[float]]:
    if not minute_bars:
        return None, None
    tps, vols = [], []
    for b in minute_bars:
        tp = ((b.get("h") or 0) + (b.get("l") or 0) + (b.get("c") or 0)) / 3.0
        tps.append(tp); vols.append(b.get("v") or 0)
    s_vol = sum(vols) or 0
    vwap = sum(tps[i]*vols[i] for i in range(len(tps))) / s_vol if s_vol>0 else (sum(tps)/len(tps))
    mu = sum(tps)/len(tps)
    var = sum((x-mu)*(x-mu) for x in tps) / max(1,(len(tps)-1))
    sigma = math.sqrt(var)
    return round(vwap,4), round(sigma,4)

def pivots_classic(prev: Dict[str, float]) -> Dict[str, float]:
    H, L, C = prev.get("h"), prev.get("l"), prev.get("c")
    if None in (H,L,C):
        return {}
    P = (H+L+C)/3.0
    R1 = 2*P - L; S1 = 2*P - H
    R2 = P + (H-L); S2 = P - (H-L)
    return { "P": round(P,2), "R1": round(R1,2), "S1": round(S1,2), "R2": round(R2,2), "S2": round(S2,2) }

def rvol_5min(minute_bars: List[Dict[str,Any]]) -> Optional[float]:
    if len(minute_bars) < 10:
        return None
    vols = [b.get("v") or 0 for b in minute_bars]
    last5 = sum(vols[-5:])
    chunks = [sum(vols[i:i+5]) for i in range(max(0,len(vols)-35), len(vols)-5, 5)]
    base = median(chunks) if chunks else None
    if not base or base == 0:
        return None
    return round(last5 / base, 2)

def micro_spread_pct(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    try:
        if ask is None or ask <= 0 or bid is None:
            return None
        return round(((ask - bid)/ask)*100.0, 2)
    except Exception:
        return None
