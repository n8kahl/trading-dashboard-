from __future__ import annotations

import asyncio
import math
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

try:
    from app.services.providers.polygon_market import PolygonMarket
except Exception:  # pragma: no cover - optional import guard for startup
    PolygonMarket = None  # type: ignore


@dataclass
class _TimeframeState:
    last_close: Optional[float]
    last_high: Optional[float]
    last_low: Optional[float]
    prev_high: Optional[float]
    prev_low: Optional[float]
    prev_close: Optional[float]
    breakout: bool
    retest: bool
    distance: Optional[float]


_CACHE: Dict[str, Tuple[float, List[Dict[str, Any]]]] = {}
_CACHE_TTL = 45  # seconds


def _tf_state(bars: List[Dict[str, Any]], current: Optional[float], breakout_buffer: float = 0.0025) -> _TimeframeState:
    if not bars or len(bars) < 2:
        return _TimeframeState(None, None, None, None, None, None, False, False, None)
    last = bars[-1]
    prev = bars[-2]
    last_close = _safe_float(last.get("c"))
    prev_high = _safe_float(prev.get("h"))
    breakout = False
    retest = False
    distance = None
    if current is not None and prev_high:
        distance = (current - prev_high) / prev_high if prev_high else None
        if last_close is not None and last_close > prev_high * (1.0 + breakout_buffer):
            breakout = True
        elif abs(current - prev_high) <= prev_high * breakout_buffer:
            retest = True
    return _TimeframeState(
        last_close=last_close,
        last_high=_safe_float(last.get("h")),
        last_low=_safe_float(last.get("l")),
        prev_high=prev_high,
        prev_low=_safe_float(prev.get("l")),
        prev_close=_safe_float(prev.get("c")),
        breakout=breakout,
        retest=retest,
        distance=distance,
    )


def _safe_float(val: Any) -> Optional[float]:
    try:
        if val is None:
            return None
        return float(val)
    except Exception:
        return None


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def _round(val: Optional[float], decimals: int = 2) -> Optional[float]:
    if val is None or math.isnan(val):
        return None
    return round(val, decimals)


async def _symbol_snapshot(poly: PolygonMarket, sym: str, mover_meta: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    try:
        last_trade = await poly.last_trade(sym)
        last_price = _safe_float(last_trade.get("price"))
    except Exception:
        last_trade = {}
        last_price = None

    daily_bars, h4_bars, h1_bars, intraday_minutes = await asyncio.gather(
        poly.daily_bars(sym, lookback=8),
        poly.aggregate_bars(sym, multiplier=240, timespan="minute", lookback_days=10),
        poly.aggregate_bars(sym, multiplier=60, timespan="minute", lookback_days=5),
        poly.minute_bars_today(sym),
    )

    if not last_price and intraday_minutes:
        last_price = _safe_float(intraday_minutes[-1].get("c"))

    tf_daily = _tf_state(daily_bars, last_price, breakout_buffer=0.003)
    tf_h4 = _tf_state(h4_bars, last_price, breakout_buffer=0.0025)
    tf_h1 = _tf_state(h1_bars, last_price, breakout_buffer=0.0020)

    if last_price is None:
        return None

    # Daily trend via simple slope between latest closes
    daily_trend = 0.0
    if len(daily_bars) >= 3:
        closes = [b.get("c") for b in daily_bars[-5:] if _safe_float(b.get("c")) is not None]
        if len(closes) >= 2:
            daily_trend = (_safe_float(closes[-1]) - _safe_float(closes[0])) / max(1e-6, _safe_float(closes[0]))

    # Relative intraday volume vs 5-day average
    intraday_volume = sum((_safe_float(b.get("v")) or 0.0) for b in intraday_minutes)
    avg_daily_vol = 0.0
    if daily_bars:
        vols = [_safe_float(b.get("v")) or 0.0 for b in daily_bars[-6:-1]]
        if vols:
            avg_daily_vol = sum(vols) / len(vols)
    intraday_rvol = None
    if avg_daily_vol > 0:
        # Scale intraday volume to full-day equivalent (~390 minutes)
        minutes_count = max(1, len(intraday_minutes))
        scaled = intraday_volume * (390 / minutes_count)
        intraday_rvol = scaled / avg_daily_vol

    score = 50.0
    setup_tags: List[str] = []
    if tf_h1.breakout:
        score += 15
        setup_tags.append("1h breakout")
    elif tf_h1.retest:
        score += 10
        setup_tags.append("1h retest")

    if tf_h4.breakout:
        score += 20
        setup_tags.append("4h breakout")
    elif tf_h4.retest:
        score += 12
        setup_tags.append("4h retest")

    if tf_daily.breakout:
        score += 8
        setup_tags.append("Daily breakout")
    elif tf_daily.retest:
        score += 5
        setup_tags.append("Daily retest")

    if daily_trend > 0:
        score += 5
    elif daily_trend < 0:
        score -= 5

    change_pct = _safe_float(mover_meta.get("change_pct"))
    if change_pct is not None:
        if abs(change_pct) >= 5:
            score += 4
        if change_pct < -2 and tf_h1.breakout:
            score -= 6  # breakout against bearish move

    if intraday_rvol and intraday_rvol >= 1.5:
        score += 6
    elif intraday_rvol and intraday_rvol < 0.7:
        score -= 6

    score = _clamp(score)
    setup = ", ".join(setup_tags) if setup_tags else "Range watch"

    timeframes: Dict[str, Any] = {
        "daily": {
            "last_close": _round(tf_daily.last_close),
            "prev_high": _round(tf_daily.prev_high),
            "prev_low": _round(tf_daily.prev_low),
            "signal": "breakout" if tf_daily.breakout else ("retest" if tf_daily.retest else None),
        },
        "h4": {
            "last_close": _round(tf_h4.last_close),
            "prev_high": _round(tf_h4.prev_high),
            "prev_low": _round(tf_h4.prev_low),
            "signal": "breakout" if tf_h4.breakout else ("retest" if tf_h4.retest else None),
            "distance": _round(tf_h4.distance, 4),
        },
        "h1": {
            "last_close": _round(tf_h1.last_close),
            "prev_high": _round(tf_h1.prev_high),
            "prev_low": _round(tf_h1.prev_low),
            "signal": "breakout" if tf_h1.breakout else ("retest" if tf_h1.retest else None),
            "distance": _round(tf_h1.distance, 4),
        },
    }

    return {
        "symbol": sym,
        "score": int(round(score)),
        "setup": setup,
        "price": _round(last_price),
        "change_pct": _round(change_pct, 2) if change_pct is not None else None,
        "rvol": _round(intraday_rvol, 2) if intraday_rvol is not None else None,
        "timeframes": timeframes,
        "trend": {
            "daily_slope_pct": _round(daily_trend * 100.0, 2) if daily_trend else None,
        },
        "mover": mover_meta,
    }


async def scan_top_setups(limit: int = 10) -> List[Dict[str, Any]]:
    if PolygonMarket is None:
        return []
    cache_key = f"top:{limit}"
    now = time.time()
    cached = _CACHE.get(cache_key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1]

    poly = PolygonMarket()
    try:
        movers = await poly.top_movers(limit=max(10, limit * 2))
    except Exception:
        movers = []
    symbols = [m.get("symbol") for m in movers if m.get("symbol")]
    unique_symbols = []
    for s in symbols:
        if s not in unique_symbols:
            unique_symbols.append(s)
    unique_symbols = unique_symbols[: max(5, limit + 3)]

    results: List[Dict[str, Any]] = []
    sem = asyncio.Semaphore(5)

    async def _worker(sym: str, meta: Dict[str, Any]):
        async with sem:
            try:
                data = await _symbol_snapshot(poly, sym, meta)
                if data:
                    results.append(data)
            except Exception:
                return

    await asyncio.gather(*[_worker(sym, next((m for m in movers if m.get("symbol") == sym), {})) for sym in unique_symbols])
    ranked = sorted(results, key=lambda x: x.get("score", 0), reverse=True)[:limit]
    _CACHE[cache_key] = (now, ranked)
    return ranked
