from typing import Any, Dict, List, Tuple


def band_for(score: int) -> str:
    if score >= 70:
        return "favorable"
    if score >= 50:
        return "mixed"
    return "unfavorable"


def _safe_num(x, default=None):
    try:
        return float(x)
    except Exception:
        return default


# ------- Strategy scorers -------


def score_vwap_bounce(c: Dict[str, Any]) -> Dict[str, int | float]:
    score = 0
    comp = {}
    price, vwap = c.get("price"), c.get("vwap")
    bars = int(c.get("bars_above_vwap", 0) or 0)
    if vwap is not None and price is not None:
        if price > vwap:
            pts = min(15, 5 + 3 * bars)
            comp["vwap_posture"] = pts
            score += pts
        else:
            comp["vwap_posture"] = -10
            score -= 10
    if c.get("ema9_gt_ema20") is True:
        comp["ema_stack"] = 12
        score += 12
    elif c.get("ema9_gt_ema20") is False:
        comp["ema_stack"] = -8
        score -= 8
    div = (c.get("divergence_5m") or "").lower()
    if "bullish_confirmed" in div:
        comp["divergence"] = 10
        score += 10
    elif "bearish_confirmed" in div:
        comp["divergence"] = -10
        score -= 10
    else:
        comp["divergence"] = 0
    sp = _safe_num(c.get("spread_pct"))
    if sp is not None:
        if sp <= 5:
            comp["liquidity"] = 10
            score += 10
        elif sp <= 8:
            comp["liquidity"] = 4
            score += 4
        else:
            comp["liquidity"] = -8
            score -= 8
    ivp = _safe_num(c.get("iv_percentile"))
    if ivp is not None:
        if 30 <= ivp <= 70:
            comp["vol_context"] = 4
            score += 4
        elif ivp > 80:
            comp["vol_context"] = -4
            score -= 4
        else:
            comp["vol_context"] = 0
    if c.get("is_macro_window") is True:
        comp["macro"] = -5
        score -= 5
    # ATR regime (1m pct)
    atrp = _safe_num(c.get("atr_1m_pct"))
    if atrp is not None:
        if 1.0 <= atrp <= 4.0:
            comp["atr_regime"] = 2
            score += 2
        elif atrp < 1.0:
            comp["atr_regime"] = -5
            score -= 5
        elif atrp > 8.0:
            comp["atr_regime"] = -3
            score -= 3
        else:
            comp["atr_regime"] = 0
    # Distance to EMA20
    d20 = _safe_num(c.get("dist_ema20_pct"))
    if d20 is not None:
        adj = max(-10, min(10, d20)) / 2  # clamp ±10 → ±5 pts
        comp["dist_ema20"] = adj
        score += adj
    # Order flow proxies
    flow = 0
    cvd = _safe_num(c.get("cvd_approx_20"))
    if cvd is not None:
        flow += 4 if cvd > 0 else (-4 if cvd < 0 else 0)
    obv = _safe_num(c.get("obv_slope_10"))
    if obv is not None:
        flow += 4 if obv > 0 else (-4 if obv < 0 else 0)
    if flow:
        comp["flow"] = flow
        score += flow
    return {"score": max(0, min(100, score)), "components": comp}


def score_ema_crossover(c: Dict[str, Any]) -> Dict[str, int | float]:
    score = 0
    comp = {}
    if c.get("ema9_gt_ema20") is True:
        comp["ema_stack"] = 25
        score += 25
    elif c.get("ema9_gt_ema20") is False:
        comp["ema_stack"] = -15
        score -= 15
    rsi_hint = (c.get("divergence_5m") or "").lower()
    if "bullish" in rsi_hint:
        comp["momentum_hint"] = 5
        score += 5
    vwap = c.get("vwap")
    price = c.get("price")
    if vwap is not None and price is not None:
        comp["vwap_support"] = 5 if price > vwap else -3
        score += comp["vwap_support"]
    sp = _safe_num(c.get("spread_pct"))
    if sp is not None:
        comp["liquidity"] = 8 if sp <= 6 else (2 if sp <= 8 else -8)
        score += comp["liquidity"]
    ivp = _safe_num(c.get("iv_percentile"))
    if ivp is not None:
        comp["vol_context"] = 4 if 20 <= ivp <= 75 else (-4 if ivp > 85 else 0)
        score += comp["vol_context"]
    # ATR regime and flow light touch here
    atrp = _safe_num(c.get("atr_1m_pct"))
    if atrp is not None:
        if 1.0 <= atrp <= 4.5:
            comp["atr_regime"] = 2
            score += 2
        elif atrp < 1.0:
            comp["atr_regime"] = -4
            score -= 4
    flow = 0
    cvd = _safe_num(c.get("cvd_approx_20"))
    if cvd is not None:
        flow += 3 if cvd > 0 else (-3 if cvd < 0 else 0)
    obv = _safe_num(c.get("obv_slope_10"))
    if obv is not None:
        flow += 3 if obv > 0 else (-3 if obv < 0 else 0)
    if flow:
        comp["flow"] = flow
        score += flow
    return {"score": max(0, min(100, score)), "components": comp}


def score_opening_range_breakout(c: Dict[str, Any]) -> Dict[str, int | float]:
    score = 0
    comp = {}
    orh = _safe_num(c.get("opening_range_high"))
    orl = _safe_num(c.get("opening_range_low"))
    price = _safe_num(c.get("price"))
    if orh is None or orl is None or price is None:
        comp["or_availability"] = -10
        score -= 10
        return {"score": max(0, min(100, score)), "components": comp}
    if price > orh:
        comp["breakout"] = 25
        score += 25
    elif price < orl:
        comp["breakout"] = -20
        score -= 20
    else:
        comp["breakout"] = -5
        score -= 5
    rv5 = _safe_num(c.get("rel_volume_5"))
    if rv5 is not None:
        if rv5 >= 1.5:
            comp["volume_conf"] = 15
            score += 15
        elif rv5 >= 1.1:
            comp["volume_conf"] = 7
            score += 7
        else:
            comp["volume_conf"] = -5
            score -= 5
    if c.get("ema9_gt_ema20") is True:
        comp["ema_stack"] = 10
        score += 10
    vwap = _safe_num(c.get("vwap"))
    if vwap is not None and price is not None:
        comp["vwap_posture"] = 8 if price > vwap else -6
        score += comp["vwap_posture"]
    # ATR regime small influence
    atrp = _safe_num(c.get("atr_1m_pct"))
    if atrp is not None:
        if 1.0 <= atrp <= 5.0:
            comp["atr_regime"] = 2
            score += 2
        elif atrp < 1.0:
            comp["atr_regime"] = -3
            score -= 3
    return {"score": max(0, min(100, score)), "components": comp}


def score_power_hour_spx(c: Dict[str, Any]) -> Dict[str, int | float]:
    score = 0
    comp = {}
    sym = (c.get("symbol") or "").upper()
    if not c.get("is_power_hour", False) or sym not in {"SPX", "SPY", "ES", "MES"}:
        comp["window_check"] = -10
        score -= 10
        return {"score": max(0, min(100, score)), "components": comp}
    price = _safe_num(c.get("price"))
    vwap = _safe_num(c.get("vwap"))
    if price is not None and vwap is not None:
        comp["vwap_posture"] = 15 if price > vwap else -10
        score += comp["vwap_posture"]
    if c.get("ema9_gt_ema20") is True:
        comp["ema_stack"] = 15
        score += 15
    rv5 = _safe_num(c.get("rel_volume_5"))
    if rv5 is not None:
        comp["rel_volume_5"] = 10 if rv5 >= 1.2 else 0
        score += comp["rel_volume_5"]
    p = price
    pdh = _safe_num(c.get("prev_day_high"))
    pdl = _safe_num(c.get("prev_day_low"))
    if p is not None and pdh is not None and pdl is not None and pdh > pdl:
        pos = (p - pdl) / (pdh - pdl)
        adj = 10 if pos >= 0.6 else (-5 if pos <= 0.4 else 0)
        comp["range_pos"] = adj
        score += adj
    return {"score": max(0, min(100, score)), "components": comp}


# ------- Dispatcher -------


def _dispatch(sid: str, context: Dict[str, Any]) -> Dict[str, Any]:
    sid = (sid or "").lower()
    if sid in {"vwap_bounce", "vwap"}:
        return score_vwap_bounce(context)
    if sid in {"ema_crossover", "ema"}:
        return score_ema_crossover(context)
    if sid in {"opening_range_breakout", "orb"}:
        return score_opening_range_breakout(context)
    if sid in {"power_hour_spx", "power_hour"}:
        return score_power_hour_spx(context)
    return score_vwap_bounce(context)  # default


STRATEGIES: List[Tuple[str, str]] = [
    ("vwap_bounce", "VWAP Bounce"),
    ("ema_crossover", "EMA 9/20 Crossover"),
    ("opening_range_breakout", "Opening Range Breakout (30m)"),
    ("power_hour_spx", "Power Hour (SPX/SPY)"),
]


def score_confluence(context: Dict[str, Any], strategy_id: str) -> Dict[str, Any]:
    sid = (strategy_id or "").lower()
    out = _dispatch(sid, context)
    score = int(max(0, min(100, out["score"])))
    band = band_for(score)
    rationale = f"Strategy={sid or 'vwap_bounce'}. Score {score}/100 ({band}). Weighted components: {', '.join(out['components'].keys()) or 'n/a'}."
    return {"score": score, "band": band, "components": out["components"], "rationale": rationale}


def score_all(context: Dict[str, Any]) -> List[Dict[str, Any]]:
    results = []
    for sid, name in STRATEGIES:
        out = _dispatch(sid, context)
        score = int(max(0, min(100, out["score"])))
        band = band_for(score)
        results.append(
            {
                "strategy_id": sid,
                "name": name,
                "score": score,
                "band": band,
                "components": out["components"],
            }
        )
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
