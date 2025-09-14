from __future__ import annotations
from typing import Dict, Any, Optional

def dynamic_trailing_stop(last: Optional[float], vwap: Optional[float], ema_fast: Optional[float] = None, base_r: float = 0.5) -> Dict[str, Any]:
    """
    Simple trailing logic:
    - If trend up and price above VWAP, trail at max(VWAP, ema_fast) - k*R
    - If trend down, mirror logic.
    """
    if last is None:
        return {"trail": None, "note": "no last price"}
    if vwap is None and ema_fast is None:
        return {"trail": None, "note": "no dynamic anchors"}
    anchor = None
    if vwap is not None and ema_fast is not None:
        anchor = max(vwap, ema_fast) if last >= vwap else min(vwap, ema_fast)
    else:
        anchor = (vwap or ema_fast)
    if anchor is None:
        return {"trail": None, "note": "no anchor"}
    # keep a small buffer (0.2R)
    return {"trail": round(anchor - 0.2*base_r, 4), "note": "trail vs dynamic anchor"}

def scale_plan(em_abs: Optional[float], tiers=(0.25, 0.50)) -> Dict[str, Any]:
    """Propose TP tiers relative to EM if available."""
    if em_abs is None:
        return {"tp": None, "note": "no EM"}
    return {
        "tp": [{"mult": t, "desc": f"TP at {int(t*100)}% of EM"} for t in tiers],
        "note": "EM-based TP scaffolding"
    }

def adjust_targets_for_em(entry: Optional[float], em_abs: Optional[float], direction: str = "long") -> Dict[str, Any]:
    """Clamp TP to within EM and ensure SL is reasonable."""
    if entry is None or em_abs is None:
        return {"tp1": None, "tp2": None, "sl_hint": None}
    if direction == "long":
        return {"tp1": round(entry + em_abs*0.25, 4), "tp2": round(entry + em_abs*0.50, 4), "sl_hint": round(entry - em_abs*0.25, 4)}
    else:
        return {"tp1": round(entry - em_abs*0.25, 4), "tp2": round(entry - em_abs*0.50, 4), "sl_hint": round(entry + em_abs*0.25, 4)}
