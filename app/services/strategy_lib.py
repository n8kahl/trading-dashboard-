from typing import Any, Dict, List, Optional

from .ta import ema, rsi, vwap


def _latest(vals: List[Optional[float]]) -> Optional[float]:
    return next((vals[i] for i in range(len(vals) - 1, -1, -1) if vals[i] is not None), None)


# -------- Strategies --------


def strategy_scalp_momentum(bars: List[dict]) -> Dict[str, Any]:
    closes = [b["c"] for b in bars]
    ema9 = ema(closes, 9)
    ema20 = ema(closes, 20)
    r14 = rsi(closes, 14)
    e9, e20, r = _latest(ema9), _latest(ema20), _latest(r14)
    score = 0
    rationale = []
    if e9 and e20 and e9 > e20:
        score += 25
        rationale.append("EMA9 > EMA20 (uptrend)")
    if r and 52 <= r <= 70:
        score += 20
        rationale.append(f"RSI healthy {r:.1f}")
    if closes[-1] > (e9 or closes[-1]):
        score += 15
        rationale.append("Price above EMA9 (momentum intact)")
    side = "CALL" if e9 and e20 and e9 > e20 else "PUT" if e9 and e20 and e9 < e20 else "FLAT"
    return {"id": "scalp_momo", "name": "Scalp Momentum", "score": score, "side": side, "notes": rationale}


def strategy_breakout_retest(bars: List[dict]) -> Dict[str, Any]:
    closes = [b["c"] for b in bars]
    highs = [b["h"] for b in bars]
    ema50 = ema(closes, 50)
    e50 = _latest(ema50)
    recent_high = max(highs[-20:]) if len(highs) >= 20 else max(highs)
    last = closes[-1]
    score = 0
    rationale = []
    if e50 and last > e50:
        score += 20
        rationale.append("Above EMA50 (trend filter)")
    if last >= recent_high * 0.995:
        score += 25
        rationale.append("Near 20-bar high (breakout zone)")
    if bars[-1]["l"] <= recent_high and last > recent_high:
        score += 15
        rationale.append("Retest and reclaim of breakout")
    return {
        "id": "breakout_retest",
        "name": "Breakout Retest",
        "score": score,
        "side": "CALL" if last >= recent_high else "FLAT",
        "notes": rationale,
        "level": recent_high,
    }


def strategy_reversal_divergence(bars: List[dict]) -> Dict[str, Any]:
    closes = [b["c"] for b in bars]
    r14 = rsi(closes, 14)
    score = 0
    rationale = []
    if len(closes) >= 20:
        p1, p2 = closes[-10], closes[-1]
        r1, r2 = r14[-10], r14[-1]
        if p2 < p1 and r1 is not None and r2 is not None and r2 > r1:
            score += 30
            rationale.append("Bullish divergence (price ↓, RSI ↑)")
    if r14[-1] is not None and r14[-1] < 35:
        score += 20
        rationale.append(f"RSI oversold {r14[-1]:.1f}")
    return {
        "id": "rev_div",
        "name": "Reversal Divergence",
        "score": score,
        "side": "CALL" if score >= 30 else "FLAT",
        "notes": rationale,
    }


def strategy_vwap_fade(bars: List[dict]) -> Dict[str, Any]:
    v = vwap(bars)
    v_now = v[-1]
    last = bars[-1]["c"]
    score = 0
    rationale = []
    if v_now is None:
        return {"id": "vwap_fade", "name": "VWAP Fade", "score": 0, "side": "FLAT", "notes": ["No VWAP computed"]}
    ext = (last - v_now) / v_now
    if ext > 0.02:
        score += 25
        rationale.append(f"Price {ext * 100:.1f}% above VWAP (overextension)")
    return {
        "id": "vwap_fade",
        "name": "VWAP Fade",
        "score": score,
        "side": "PUT" if score >= 25 else "FLAT",
        "notes": rationale,
    }


LIBRARY = [
    strategy_scalp_momentum,
    strategy_breakout_retest,
    strategy_reversal_divergence,
    strategy_vwap_fade,
]


def evaluate_strategies(bars: List[dict]) -> Dict[str, Any]:
    results = [fn(bars) for fn in LIBRARY]
    ranked = sorted(results, key=lambda x: x["score"], reverse=True)
    best = ranked[0]
    confluence = {
        "trend": any("EMA" in n or "trend" in n.lower() for n in best.get("notes", [])),
        "momentum": any("RSI" in n or "momentum" in n.lower() for n in best.get("notes", [])),
        "levels": any("high" in n.lower() or "retest" in n.lower() for n in best.get("notes", [])),
        "mean_revert": any("VWAP" in n or "overextension" in n.lower() for n in best.get("notes", [])),
    }
    plan_stub = {
        "side": best["side"],
        "entry_hint": bars[-1]["c"],
        "risk_hint": "use structure-based stop (e.g., below EMA20 or below retest level)",
        "tp_hints": ["scale at +1R", "trail after first TP", "leave a runner if trend strong"],
    }
    return {"best": best, "ranked": ranked, "confluence": confluence, "plan": plan_stub}


# ---- Power Hour score bias ----
def apply_power_hour_bias(results: List[Dict[str, Any]], symbol: str) -> List[Dict[str, Any]]:
    """
    For SPX/QQQ/SPY during 2–3pm CT:
      - +10 to Scalp Momentum if trend/momentum noted
      - +7 to Breakout Retest if near highs
      - -5 to VWAP Fade (reduce counter-trend)
    """
    s = symbol.upper()
    is_focus = s in ("I:SPX", "SPX", "SPY", "QQQ")
    if not is_focus:
        return results
    out: List[Dict[str, Any]] = []
    for r in results:
        rr = dict(r)
        name = (r.get("name") or "").lower()
        notes = " ".join(r.get("notes") or []).lower()
        if "scalp momentum" in name and any(k in notes for k in ["ema", "uptrend", "momentum"]):
            rr["score"] = rr.get("score", 0) + 10
        if "breakout retest" in name and any(k in notes for k in ["high", "breakout", "retest"]):
            rr["score"] = rr.get("score", 0) + 7
        if "vwap fade" in name:
            rr["score"] = rr.get("score", 0) - 5
        out.append(rr)
    return out
