from typing import Any, Dict


def _safe(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


def plan_vwap_bounce(c: Dict[str, Any]) -> Dict[str, Any]:
    price, vwap = _safe(c.get("price")), _safe(c.get("vwap"))
    pdh, pdl = _safe(c.get("prev_day_high")), _safe(c.get("prev_day_low"))
    if price is None:
        return {
            "entry_hint": None,
            "stop_loss": None,
            "take_profits": [],
            "sizing_hint": "small",
            "notes": "Price unavailable",
        }
    entry = max(price, vwap * 1.001) if vwap is not None else price
    stop = (vwap * 0.997) if vwap is not None else ((pdl * 0.995) if pdl is not None else (price * 0.995))
    tp1 = (vwap * 1.003) if vwap is not None else (price * 1.003)
    tp2 = pdh if pdh is not None else (price * 1.007)
    return {
        "entry_hint": entry,
        "stop_loss": stop,
        "take_profits": [tp1, tp2],
        "sizing_hint": "normal" if c.get("ema9_gt_ema20") else "light",
        "notes": "Enter on VWAP hold/reclaim; trim at TP1, trail under VWAP/EMA9.",
    }


def plan_ema_crossover(c: Dict[str, Any]) -> Dict[str, Any]:
    price = _safe(c.get("price"))
    if price is None:
        return {
            "entry_hint": None,
            "stop_loss": None,
            "take_profits": [],
            "sizing_hint": "small",
            "notes": "Price unavailable",
        }
    entry = price * 1.0015
    stop = price * 0.992
    tps = [price * 1.004, price * 1.008]
    return {
        "entry_hint": entry,
        "stop_loss": stop,
        "take_profits": tps,
        "sizing_hint": "normal" if c.get("ema9_gt_ema20") else "light",
        "notes": "Ride momentum while EMA9>EMA20; cut if momentum fades.",
    }


def plan_opening_range_breakout(c: Dict[str, Any]) -> Dict[str, Any]:
    price = _safe(c.get("price"))
    orh = _safe(c.get("opening_range_high"))
    orl = _safe(c.get("opening_range_low"))
    if price is None or orh is None or orl is None:
        return {
            "entry_hint": None,
            "stop_loss": None,
            "take_profits": [],
            "sizing_hint": "small",
            "notes": "Opening range not available; plan disabled",
        }
    entry = max(price, orh * 1.0005)
    stop = max(orl, orh * 0.997)
    rng = max(0.01, orh - orl)
    tp1 = orh + 0.5 * rng
    pdh = _safe(c.get("prev_day_high"))
    tp2 = pdh if (pdh is not None and pdh > tp1) else (entry + 2 * (entry - stop))
    sizing = "normal"
    rv5 = _safe(c.get("rel_volume_5"))
    if rv5 is not None and rv5 < 1.1:
        sizing = "light"
    return {
        "entry_hint": entry,
        "stop_loss": stop,
        "take_profits": [tp1, tp2],
        "sizing_hint": sizing,
        "notes": "Breakout play: confirm with volume; if failure back inside OR, cut quickly.",
    }


def plan_power_hour_spx(c: Dict[str, Any]) -> Dict[str, Any]:
    price = _safe(c.get("price"))
    vwap = _safe(c.get("vwap"))
    if not c.get("is_power_hour", False) or price is None:
        return {
            "entry_hint": None,
            "stop_loss": None,
            "take_profits": [],
            "sizing_hint": "small",
            "notes": "Not in power hour or price unavailable",
        }
    entry = price * 1.0005 if (vwap is not None and price > vwap) else price
    stop = (vwap * 0.997) if vwap is not None else (price * 0.995)
    tp1 = price * 1.003
    tp2 = price * 1.006
    return {
        "entry_hint": entry,
        "stop_loss": stop,
        "take_profits": [tp1, tp2],
        "sizing_hint": "normal" if c.get("ema9_gt_ema20") else "light",
        "notes": "Late-day follow-through; avoid if reversal signs show (VWAP loss).",
    }


def build_plan(strategy_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
    sid = (strategy_id or "").lower()
    if sid in {"vwap_bounce", "vwap"}:
        return plan_vwap_bounce(context)
    if sid in {"ema_crossover", "ema"}:
        return plan_ema_crossover(context)
    if sid in {"opening_range_breakout", "orb"}:
        return plan_opening_range_breakout(context)
    if sid in {"power_hour_spx", "power_hour"}:
        return plan_power_hour_spx(context)
    return plan_vwap_bounce(context)
