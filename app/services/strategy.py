from __future__ import annotations
from typing import Dict, Any

def score_band(ctx: Dict[str, Any]) -> tuple[int | None, str]:
    """
    Return (score, band) based on simple signals present in ctx.
    ctx keys: price, vwap, ema{9,20}, flow.rvol, flow.spread, risk.
    """
    score = 50
    ema = (ctx.get("ema") or {})
    flow = (ctx.get("flow") or {})
    vwap = ctx.get("vwap")
    price = ctx.get("price")

    # EMA posture
    if (ema.get("ema9") is not None) and (ema.get("ema20") is not None):
        if ema["ema9"] > ema["ema20"]:
            score += 10
        else:
            score -= 10

    # VWAP posture
    if vwap is not None and price is not None:
        if price >= vwap:
            score += 10
        else:
            score -= 10

    # RVOL
    rvol = flow.get("rvol")
    if isinstance(rvol, (int, float)):
        if rvol >= 1.5:
            score += 10
        elif rvol < 0.8:
            score -= 10

    # Spread (tighter is better)
    spread = flow.get("spread")
    if isinstance(spread, (int, float)):
        if spread <= 0.05:
            score += 5
        elif spread > 0.15:
            score -= 5

    # Clamp
    score = max(0, min(100, score))
    band = "favorable" if score >= 66 else "unfavorable" if score <= 34 else "mixed"
    return score, band

def default_levels(price: float | None, horizon: str) -> Dict[str, Any]:
    if price is None:
        return {"entry": None, "stop": None, "targets": []}
    # simplistic RR ladder for demo purposes
    tick = 0.3 if horizon == "scalp" else 0.8 if horizon == "intraday" else 2.0
    entry = price
    stop  = round(price - tick, 2)
    targets = [round(price + tick, 2), round(price + 2*tick, 2)]
    return {"entry": entry, "stop": stop, "targets": targets}
