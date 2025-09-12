from __future__ import annotations

from typing import Any, Dict, List, Optional

from app.services.gates import (
    entry_checks,
    gate_equity_liquidity,
    gate_regime,
    gate_session,
)
from app.services.ta import (
    atr_1m,
    avwaps_flexible,
    ema,
    resample_ohlcv_5m,
    resample_ohlcv_15m,
)
from app.services.tradier import get_timesales_1min


def _last_close(bars: List[Dict[str, Any]]) -> Optional[float]:
    for b in reversed(bars):
        c = b.get("c")
        if c is not None:
            try:
                return float(c)
            except Exception:
                continue
    return None


def _rvol_intraday(bars: List[Dict[str, Any]], look: int = 30) -> Optional[float]:
    if len(bars) < look * 2:
        return None
    recent = sum(float(b.get("v", 0) or 0) for b in bars[-look:])
    prior = sum(float(b.get("v", 0) or 0) for b in bars[-2 * look : -look])
    return (recent / prior) if prior > 0 else None


def _expected_r(score: float, a_plus: bool, rvol: Optional[float]) -> float:
    p = 0.35 + 0.30 * (max(0.0, min(100.0, score)) / 100.0)  # 0.35..0.65
    if a_plus:
        p += 0.05
    if rvol and rvol >= 1.5:
        p += 0.03
    p = max(0.30, min(0.75, p))
    r_win = 1.5
    r_loss = 1.0
    return p * r_win - (1 - p) * r_loss


async def score_intraday(symbol: str, minutes_back: int = 450) -> Dict[str, Any]:
    md = await get_timesales_1min(symbol, minutes_back=minutes_back)
    if not md.get("ok"):
        return {"ok": False, "symbol": symbol, "error": md.get("error"), "provider": "tradier"}

    bars: List[Dict[str, Any]] = md.get("bars") or []
    if not bars:
        return {"ok": False, "symbol": symbol, "error": "no_intraday_bars", "provider": "tradier"}

    closes = [float(b.get("c", 0) or 0) for b in bars if b.get("c") is not None]
    price = _last_close(bars)  # robust (never null if any bar has 'c')

    # Intraday features
    ema9 = ema(closes, 9) if len(closes) >= 9 else None
    ema21 = ema(closes, 21) if len(closes) >= 21 else None
    rvol_i = _rvol_intraday(bars, 30)

    # Anchored VWAPs (market day → open/prior-close; fallback → first bar)
    avwap_open, avwap_prevclose = avwaps_flexible(bars)

    # Liquidity proxies (simple dollar volume proxy from last 60 bars)
    spread_pct = None
    dollar_vol = None
    if price and any(b.get("v") for b in bars):
        vv = (
            sum(float(b.get("v", 0) or 0) for b in bars[-60:])
            if len(bars) >= 60
            else sum(float(b.get("v", 0) or 0) for b in bars)
        )
        dollar_vol = float(price) * float(vv)

    # Timeframe trend (5m/15m)
    bars5 = resample_ohlcv_5m(bars)
    bars15 = resample_ohlcv_15m(bars)
    closes5 = [b["c"] for b in bars5] if bars5 else []
    closes15 = [b["c"] for b in bars15] if bars15 else []

    # Confluence score (simple)
    score = 50.0
    rationale: List[str] = []
    if ema9 is not None and ema21 is not None and price is not None:
        if ema9 > ema21 and price > ema9:
            score += 15
            rationale.append("EMA stack bullish (1m)")
        elif ema9 < ema21 and price < ema9:
            score -= 15
            rationale.append("EMA stack bearish (1m)")
    if avwap_open is not None and price is not None:
        dv = (price / avwap_open - 1.0) * 100.0
        if abs(dv) < 0.5:
            score += 5
            rationale.append("Near aVWAP(anchor)")
        elif abs(dv) > 2.0:
            score -= 5
            rationale.append("Far from aVWAP(anchor)")
    if rvol_i is not None:
        if rvol_i >= 1.3:
            score += 6
            rationale.append(f"RVOL {rvol_i:.2f} >= 1.3")
        elif rvol_i <= 0.8:
            score -= 5
            rationale.append(f"RVOL {rvol_i:.2f} <= 0.8")

    # Gates
    session_ok, session_msg = gate_session()
    liq_ok, liq_msg = gate_equity_liquidity(
        {"rvol_intraday": rvol_i, "spread_pct": spread_pct, "dollar_vol": dollar_vol}
    )
    reg_ok, reg_msg, reg_meta = gate_regime(closes5, closes15)

    gates = {
        "session": {"ok": session_ok, "msg": session_msg},
        "liquidity": {"ok": liq_ok, "msg": liq_msg},
        "regime": {"ok": reg_ok, "msg": reg_msg, **reg_meta},
    }

    # Entry timing (use aVWAP open or prior-close as alternate anchor)
    entry_ok, entry_reasons, entry_ctx = entry_checks(
        bars, {"price": price, "rvol_intraday": rvol_i}, avwap_open=avwap_open, avwap_alt=avwap_prevclose
    )
    gates["entry"] = {"ok": entry_ok, "reasons": entry_reasons, **entry_ctx}

    a_plus = session_ok and liq_ok and reg_ok and entry_ok

    # Risk model (stops/targets via ATR)
    atr = atr_1m(bars, period=14)
    stop_dist = atr if (atr is not None and atr > 0) else None

    plan = None
    expected_R = None
    if price and stop_dist:
        expected_R = _expected_r(score, a_plus, rvol_i)
        if a_plus:
            entry = price
            R = stop_dist
            plan = {
                "entry": entry,
                "stop": entry - R,
                "tp1": entry + 1.0 * R,
                "tp2": entry + 2.0 * R,
                "tp1_size_pct": 50,
                "time_stop_min": 10,
                "trail_after_R": 1.5,
                "trail_method": "ema8_or_prev_bar",
                "expected_R": expected_R,
            }

    features = {
        "price": price,
        "ema9_1m": ema9,
        "ema21_1m": ema21,
        "avwap_open": avwap_open,
        "avwap_prior_close": avwap_prevclose,
        "rvol_intraday": rvol_i,
        "dollar_vol": dollar_vol,
        "spread_pct": spread_pct,
        "trend_5m": gates["regime"].get("trend_5m"),
        "trend_15m": gates["regime"].get("trend_15m"),
        "atr_1m": atr,
    }

    score = max(0.0, min(100.0, score))
    return {
        "ok": True,
        "symbol": symbol,
        "score": score,
        "a_plus": a_plus,
        "expected_R": expected_R,
        "features": features,
        "gates": gates,
        "plan_preview": plan,
        "rationale": rationale,
        "provider": "tradier",
        "data_status": "OK",
    }
