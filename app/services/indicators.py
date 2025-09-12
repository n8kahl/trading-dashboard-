from __future__ import annotations
from typing import List, Dict
import math

def avwap_from_bars(bars: List[Dict]) -> float:
    if not bars:
        return math.nan
    num = 0.0; den = 0.0
    for b in bars:
        price = float(b.get("c", 0.0))
        vol   = float(b.get("v", 0.0))
        num += price * vol; den += vol
    return num/den if den > 0 else math.nan

def atr1m(bars: List[Dict], period: int = 14) -> float:
    if len(bars) < period + 1:
        return math.nan
    trs = []
    prev_c = float(bars[0]["c"])
    for b in bars[1:]:
        h = float(b["h"]); l = float(b["l"]); c = float(b["c"])
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        trs.append(tr); prev_c = c
    if len(trs) < period:
        return math.nan
    return sum(trs[-period:]) / period

def rvol_proxy(bars: List[Dict], fast:int=5, slow:int=60) -> float:
    if len(bars) < slow:
        return float("nan")
    fv = sum(float(b["v"]) for b in bars[-fast:]) / fast
    sv = sum(float(b["v"]) for b in bars[-slow:]) / slow
    return fv/sv if sv > 0 else float("nan")

def avg_dollar_vol(bars: List[Dict], window:int=60) -> float:
    if not bars:
        return 0.0
    take = bars[-window:] if len(bars) >= window else bars
    s = sum(float(b["c"]) * float(b["v"]) for b in take)
    return s / max(len(take),1)
