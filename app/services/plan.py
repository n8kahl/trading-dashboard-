from typing import Any, Dict, List

from .ta import atr, ema


def build_plan_from_eval(bars: List[dict], best: Dict[str, Any], *, power_hour: bool = False) -> Dict[str, Any]:
    """
    Generate a trade plan from evaluation result and bars.

    Args:
        bars: list of OHLCV dicts [{t,o,h,l,c,v}, ...]
        best: the chosen best strategy dict
        power_hour: if True, tighten ATR-based stops by ~15%

    Returns:
        Dict with {entry, stop, tp1, tp2, side, notes}
    """
    if not bars or not best:
        return {"entry": None, "stop": None, "tp1": None, "tp2": None, "side": None, "notes": []}

    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    lows = [b["l"] for b in bars]

    e20_series = ema(closes, 20)
    e20_now = next((e for e in reversed(e20_series) if e is not None), None)

    atr_series = atr(highs, lows, closes, 14)
    atr_now = next((a for a in reversed(atr_series) if a is not None), None)

    last = closes[-1]
    side = (best.get("side") or "FLAT").upper()

    notes: List[str] = []
    if e20_now is not None and atr_now is not None:
        notes.append(f"EMA20={round(e20_now, 2)}, ATR14={round(atr_now, 2)}")

    # Fallbacks to keep robust
    if e20_now is None:
        e20_now = last
    if atr_now is None or atr_now <= 0:
        # safety fallback ~35 bps of price
        atr_now = max(0.5, abs(last) * 0.0035)

    tight = 0.85 if power_hour else 1.0  # tighten ATR by ~15% in power hour

    if side == "CALL":
        stop = min(e20_now, last - tight * atr_now)
        r = last - stop
        tp1 = last + 1.0 * r
        tp2 = last + 2.0 * r
    elif side == "PUT":
        stop = max(e20_now, last + tight * atr_now)
        r = stop - last
        tp1 = last - 1.0 * r
        tp2 = last - 2.0 * r
    else:
        stop, tp1, tp2 = None, None, None

    plan = {
        "side": side,
        "entry": round(last, 2),
        "stop": round(stop, 2) if stop is not None else None,
        "tp1": round(tp1, 2) if tp1 is not None else None,
        "tp2": round(tp2, 2) if tp2 is not None else None,
        "notes": notes,
        "power_hour": power_hour,
    }
    return plan
