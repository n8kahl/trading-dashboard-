from __future__ import annotations
from typing import List, Dict, Any, Optional
import math
import statistics as stats

def _rvol(bars: List[Dict[str, Any]], lookback: int = 60) -> Optional[float]:
    """Relative volume: current session avg 1m vol vs trailing avg (fallback inside session)."""
    vols = [b.get("v") or 0 for b in bars]
    if not vols:
        return None
    cur = sum(vols[:min(len(vols), lookback)]) / max(1, min(len(vols), lookback))
    base = sum(vols[-min(len(vols), lookback):]) / max(1, min(len(vols), lookback))
    if base <= 0:
        return None
    return cur / base

def _orb_metrics(bars: List[Dict[str, Any]], window: int = 30) -> Dict[str, float]:
    """Opening range breakout metrics from first N 1m bars."""
    w = min(window, len(bars))
    if w == 0:
        return {"orb_high": None, "orb_low": None, "orb_range": None}
    highs = [b.get("h") for b in bars[:w] if b.get("h") is not None]
    lows  = [b.get("l") for b in bars[:w] if b.get("l") is not None]
    if not highs or not lows:
        return {"orb_high": None, "orb_low": None, "orb_range": None}
    hi, lo = max(highs), min(lows)
    return {"orb_high": hi, "orb_low": lo, "orb_range": (hi - lo)}

def _sigma_of_returns(bars: List[Dict[str, Any]], window: int = 60) -> Optional[float]:
    """Std dev of 1m log returns (lightweight)."""
    closes = [b.get("c") for b in bars if b.get("c") is not None]
    if len(closes) < 3:
        return None
    rets = []
    for i in range(1, min(len(closes), window)):
        if closes[i-1] and closes[i]:
            rets.append(math.log(closes[i]/closes[i-1]))
    if len(rets) < 3:
        return None
    return stats.pstdev(rets)

def analyze(bars_1m: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Lightweight regime detector for intraday:
    - opening_type: 'opening_drive' | 'balanced' | 'reversal_risk' | None
    - regime: 'trend' | 'balance' | 'expansion' | None
    Returns metrics used downstream (rvol, orb_range, sigma).
    """
    if not bars_1m:
        return {"opening_type": None, "regime": None, "metrics": {}}

    m = _orb_metrics(bars_1m, window=30)  # first 30m
    sigma = _sigma_of_returns(bars_1m, window=60) or 0.0
    rvol = _rvol(bars_1m, lookback=60)

    # Opening type heuristic
    opening_type = None
    if m["orb_range"] is not None and rvol is not None:
        # Large ORB + >1.2 rVOL -> opening drive
        if m["orb_range"] > (0.0025 * (bars_1m[0].get("c") or 1)) and rvol >= 1.2:
            opening_type = "opening_drive"
        # Small ORB + ~1.0 rVOL -> balanced
        elif m["orb_range"] < (0.0015 * (bars_1m[0].get("c") or 1)) and 0.8 <= rvol <= 1.2:
            opening_type = "balanced"
        else:
            opening_type = "reversal_risk"

    # Regime heuristic using sigma (vol expansion), and simple drift
    regime = None
    if sigma > 0.003:
        regime = "expansion"
    else:
        # slope over last 20 bars
        last = bars_1m[-20:] if len(bars_1m) >= 20 else bars_1m
        closes = [b.get("c") for b in last if b.get("c") is not None]
        if len(closes) >= 3:
            up = sum(1 for i in range(1, len(closes)) if closes[i] > closes[i-1])
            dn = len(closes) - 1 - up
            regime = "trend" if abs(up - dn) >= len(closes)*0.35 else "balance"
        else:
            regime = "balance"

    return {"opening_type": opening_type, "regime": regime, "metrics": {"rvol": rvol, "orb_range": m["orb_range"], "sigma": sigma}}
