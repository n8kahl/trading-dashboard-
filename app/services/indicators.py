from __future__ import annotations
from typing import List, Dict, Any, Tuple, Optional
import math
from statistics import median

def ema(values: List[float], period: int) -> Optional[float]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) < max(1, period): return None
    k = 2/(period+1)
    e = vals[0]
    for v in vals[1:]:
        e = v*k + e*(1-k)
    return round(e, 4)

def sma(values: List[float], period: int) -> Optional[float]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) < period or period <= 0: return None
    return round(sum(vals[-period:]) / period, 4)

def rsi(values: List[float], period: int = 14) -> Optional[float]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) <= period: return None
    gains, losses = [], []
    for i in range(1, len(vals)):
        ch = vals[i] - vals[i-1]
        gains.append(max(0.0, ch))
        losses.append(max(0.0, -ch))
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    for i in range(period, len(gains)):
        avg_gain = (avg_gain*(period-1) + gains[i]) / period
        avg_loss = (avg_loss*(period-1) + losses[i]) / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return round(100 - (100 / (1 + rs)), 2)

def macd(values: List[float], fast: int = 12, slow: int = 26, signal_p: int = 9) -> Optional[Dict[str, float]]:
    vals = [v for v in values if isinstance(v,(int,float))]
    if len(vals) < max(fast, slow, signal_p) + 10: return None
    def _ema(seq, p):
        k = 2/(p+1); e = seq[0]
        for x in seq[1:]:
            e = x*k + e*(1-k)
        return e
    ema_fast = []
    ema_slow = []
    e_f = vals[0]; e_s = vals[0]
    kf = 2/(fast+1); ks = 2/(slow+1)
    for x in vals:
        e_f = x*kf + e_f*(1-kf); ema_fast.append(e_f)
        e_s = x*ks + e_s*(1-ks); ema_slow.append(e_s)
    macd_line = [a-b for a,b in zip(ema_fast, ema_slow)]
    e_sig = macd_line[0]; ks2 = 2/(signal_p+1)
    signal = []
    for m in macd_line:
        e_sig = m*ks2 + e_sig*(1-ks2); signal.append(e_sig)
    hist = macd_line[-1] - signal[-1]
    return {"macd": round(macd_line[-1], 4), "signal": round(signal[-1], 4), "hist": round(hist, 4)}

def atr14(daily: List[Dict[str, Any]]) -> Optional[float]:
    if len(daily) < 15: return None
    trs = []
    prev_c = daily[0]["c"]
    for i in range(1,len(daily)):
        h,l,c = daily[i]["h"], daily[i]["l"], daily[i]["c"]
        tr = max(h-l, abs(h-prev_c), abs(l-prev_c))
        trs.append(tr); prev_c = c
    if len(trs) < 14: return None
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

def session_vwap_and_sigma(bars: List[Dict[str,Any]]) -> Tuple[Optional[float], Optional[float]]:
    if not bars: return None, None
    tps, vols = [], []
    for b in bars:
        h = b.get("h") or 0.0; l = b.get("l") or 0.0; c = b.get("c") or 0.0
        v = b.get("v") or 0.0
        tp = (h + l + c) / 3.0
        tps.append(tp); vols.append(v)
    s_vol = sum(vols)
    vwap = (sum(tps[i]*vols[i] for i in range(len(tps))) / s_vol) if s_vol>0 else (sum(tps)/len(tps))
    sig = _sigma(tps)
    return round(vwap, 4), (round(sig,4) if sig is not None else None)

def rvol_5min(minute_bars: List[Dict[str,Any]]) -> Optional[float]:
    if len(minute_bars) < 10: return None
    vols = [b.get("v") or 0 for b in minute_bars]
    last5 = sum(vols[-5:])
    chunks = [sum(vols[i:i+5]) for i in range(max(0,len(vols)-35), len(vols)-5, 5)]
    base = median(chunks) if chunks else None
    if not base or base == 0: return None
    return round(last5 / base, 2)

def spread_stability(bids: List[float], asks: List[float]) -> Optional[float]:
    """Heuristic 0..1 → lower variance of spread% = more stable."""
    pairs = [(b,a) for b,a in zip(bids,asks) if a and a>0 and b is not None]
    if len(pairs) < 5: return None
    sp = [((a-b)/a)*100.0 for b,a in pairs]
    mu = sum(sp)/len(sp)
    var = sum((x-mu)*(x-mu) for x in sp) / (len(sp)-1)
    score = max(0.0, 1.0 - min(1.0, (var/25.0)))  # 0 var → 1.0; var≈25 → 0
    return round(score, 2)
