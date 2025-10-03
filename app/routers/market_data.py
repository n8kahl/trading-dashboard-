from __future__ import annotations

from datetime import datetime, timedelta, timezone, time
from typing import Dict, Any, List, Optional, Tuple

from fastapi import APIRouter, Query
from importlib import import_module as _im
from zoneinfo import ZoneInfo

from app.services.indicators import pivots_classic, fibonacci_levels

router = APIRouter(prefix="/api/v1/market", tags=["market"])

PolygonMarket = None
try:
    PolygonMarket = getattr(_im("app.services.providers.polygon_market"), "PolygonMarket")
except Exception:
    PolygonMarket = None


@router.get("/bars")
async def bars(
    symbol: str,
    interval: str = Query("1m", pattern="^(1m|5m|1d)$"),
    lookback: int = 390,
) -> Dict[str, Any]:
    if not PolygonMarket:
        return {"ok": False, "error": "Polygon provider unavailable"}
    sym = (symbol or "").upper()
    poly = PolygonMarket()
    data: List[Dict[str, Any]] = []
    try:
        if interval == "1m":
            data = await poly.minute_bars_today(sym)
        elif interval == "5m":
            data = await poly.five_minute_bars_today(sym)
        else:
            # 1d
            data = await poly.daily_bars(sym, lookback=max(lookback, 30))
        if lookback and isinstance(lookback, int) and lookback > 0:
            data = data[-lookback:]
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
    return {"ok": True, "symbol": sym, "interval": interval, "bars": data}


_EASTERN = ZoneInfo("America/New_York")
_PREMARKET_START = time(hour=4, minute=0)
_REGULAR_START = time(hour=9, minute=30)
_REGULAR_END = time(hour=16, minute=0)


async def _previous_session_minutes(poly, symbol: str, max_back: int = 7) -> Tuple[Optional[List[Dict[str, Any]]], Optional[datetime]]:
    """Fetch minute bars for the most recent trading session (1-minute granularity)."""
    day = datetime.now(timezone.utc).date() - timedelta(days=1)
    for _ in range(max_back):
        dt = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        bars = await poly.minute_bars_for_day(symbol, dt)
        if bars:
            return bars, dt
        day -= timedelta(days=1)
    return None, None


def _session_extremes(minute_bars: List[Dict[str, Any]]) -> Dict[str, Optional[float]]:
    pre_high = pre_low = None
    reg_high = reg_low = None
    for bar in minute_bars:
        ts = bar.get("t")
        if ts is None:
            continue
        dt = datetime.fromtimestamp(ts / 1000, tz=timezone.utc).astimezone(_EASTERN)
        price_high = bar.get("h")
        price_low = bar.get("l")
        if price_high is None or price_low is None:
            continue
        if _PREMARKET_START <= dt.time() < _REGULAR_START:
            pre_high = price_high if pre_high is None else max(pre_high, price_high)
            pre_low = price_low if pre_low is None else min(pre_low, price_low)
        elif _REGULAR_START <= dt.time() <= _REGULAR_END:
            reg_high = price_high if reg_high is None else max(reg_high, price_high)
            reg_low = price_low if reg_low is None else min(reg_low, price_low)
    return {
        "premarket_high": round(pre_high, 2) if pre_high is not None else None,
        "premarket_low": round(pre_low, 2) if pre_low is not None else None,
        "session_high": round(reg_high, 2) if reg_high is not None else None,
        "session_low": round(reg_low, 2) if reg_low is not None else None,
    }


async def compute_levels(poly, symbol: str) -> Dict[str, Any]:
    sym = (symbol or "").upper()
    # Map index underlyings to ETF proxies for reliable intraday levels
    level_sym = 'SPY' if sym in {"SPX","SPXW","^SPX"} else ('QQQ' if sym in {"NDX","^NDX"} else sym)
    daily = await poly.daily_bars(level_sym, lookback=4)
    if len(daily) < 2:
        return {"ok": False, "error": "insufficient_daily"}

    prev = daily[-2]
    ohlc = {
        "o": prev.get("o"),
        "h": prev.get("h"),
        "l": prev.get("l"),
        "c": prev.get("c"),
    }
    piv = pivots_classic(ohlc)
    fibs = fibonacci_levels(ohlc.get("h"), ohlc.get("l"))

    minute_bars, session_day = await _previous_session_minutes(poly, level_sym)
    key_levels = {
        "prev_high": round(ohlc.get("h"), 2) if ohlc.get("h") is not None else None,
        "prev_low": round(ohlc.get("l"), 2) if ohlc.get("l") is not None else None,
        "prev_close": round(ohlc.get("c"), 2) if ohlc.get("c") is not None else None,
    }

    if minute_bars:
        extremes = _session_extremes(minute_bars)
        key_levels.update(extremes)
    else:
        key_levels.update({
            "premarket_high": None,
            "premarket_low": None,
            "session_high": None,
            "session_low": None,
        })

    return {
        "ok": True,
        "symbol": sym,
        "levels_source": level_sym,
        "prev_day": ohlc,
        "pivots": piv,
        "key_levels": key_levels,
        "fibonacci": fibs,
        "session_date_utc": session_day.isoformat() if session_day else None,
    }


@router.get("/levels")
async def levels(symbol: str) -> Dict[str, Any]:
    """Return previous day's OHLC, pivots, key levels, and Fibonacci markers."""
    if not PolygonMarket:
        return {"ok": False, "error": "Polygon provider unavailable"}
    sym = (symbol or "").upper()
    poly = PolygonMarket()
    try:
        result = await compute_levels(poly, sym)
        return result
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}
