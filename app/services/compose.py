from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

try:
    from zoneinfo import ZoneInfo

    try:
        NY = ZoneInfo("America/New_York")
    except Exception:
        NY = timezone.utc  # fallback if the IANA db isn't available
except Exception:
    # extremely defensive: if zoneinfo import itself fails, use UTC
    NY = timezone.utc

from app.services.mcp_bridge import mcp_run_tool


def _last(seq: List[dict]) -> dict | None:
    return seq[-1] if seq else None


def _vwap(results: List[dict]) -> float | None:
    pv = 0.0
    vol = 0.0
    for b in results:
        c = float(b.get("c", 0.0))
        v = float(b.get("v", 0.0))
        pv += c * v
        vol += v
    return (pv / vol) if vol > 0 else None


def _ema(values: List[float], window: int) -> float | None:
    if len(values) < window:
        return None
    k = 2.0 / (window + 1.0)
    ema = sum(values[:window]) / window
    for x in values[window:]:
        ema = x * k + ema * (1 - k)
    return ema


def _rsi(values: List[float], window: int = 14) -> List[float]:
    if len(values) <= window:
        return []
    gains, losses = [], []
    for i in range(1, len(values)):
        ch = values[i] - values[i - 1]
        gains.append(max(ch, 0.0))
        losses.append(max(-ch, 0.0))
    avg_gain = sum(gains[:window]) / window
    avg_loss = sum(losses[:window]) / window
    rsis = []
    for i in range(window, len(gains)):
        avg_gain = (avg_gain * (window - 1) + gains[i]) / window
        avg_loss = (avg_loss * (window - 1) + losses[i]) / window
        rsi = 100.0 if avg_loss == 0 else 100.0 - (100.0 / (1.0 + (avg_gain / avg_loss)))
        rsis.append(rsi)
    return rsis


def _bars_above_vwap(results: List[dict], vwap: float, cap: int = 3) -> int:
    if vwap is None:
        return 0
    n = 0
    for b in reversed(results):
        if float(b.get("c", 0.0)) > vwap:
            n += 1
            if n >= cap:
                break
        else:
            break
    return n


def _divergence_tag(results: List[dict], rsi_series: List[float]) -> str:
    if len(results) < 3 or len(rsi_series) < 3:
        return "weak"
    p1, p2, p3 = (float(results[-3]["c"]), float(results[-2]["c"]), float(results[-1]["c"]))
    r1, r2, r3 = (rsi_series[-3], rsi_series[-2], rsi_series[-1])
    price_hh = p3 > max(p1, p2)
    rsi_rising = r3 > r2 > r1
    return "bullish_confirmed" if price_hh and rsi_rising else "weak"


def _ymd(d: datetime) -> str:
    return d.strftime("%Y-%m-%d")


def _ts_to_eastern_str(ts_ms: int) -> str:
    dt = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(NY)
    return dt.strftime("%Y-%m-%d %H:%M:%S %Z")


def _is_rth_bar(ts_ms: int) -> bool:
    dt_et = datetime.fromtimestamp(ts_ms / 1000.0, tz=timezone.utc).astimezone(NY)
    # 09:30–16:00 in whatever NY resolves to (NY or UTC fallback)
    return (dt_et.hour > 9 or (dt_et.hour == 9 and dt_et.minute >= 30)) and (dt_et.hour < 16)


def _fetch_prev_day_hl(daily_bars: List[dict], the_day: str) -> Dict[str, float | None]:
    try:
        tgt = datetime.strptime(the_day, "%Y-%m-%d").date()
    except Exception:
        return {"prev_day_high": None, "prev_day_low": None}
    prev = None
    for b in daily_bars:
        ts = int(b.get("t"))
        dt_et = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).astimezone(NY).date()
        if dt_et < tgt:
            prev = b
    if not prev:
        return {"prev_day_high": None, "prev_day_low": None}
    return {"prev_day_high": float(prev.get("h")), "prev_day_low": float(prev.get("l"))}


async def _fetch_bars(symbol: str, the_day: str, timespan: str, lookback_days: int = 1) -> dict:
    end = datetime.strptime(the_day, "%Y-%m-%d")
    start = end - timedelta(days=lookback_days)
    return await mcp_run_tool(
        "get_aggs",
        {
            "ticker": symbol,
            "timespan": timespan,
            "multiplier": 1,
            "from_date": _ymd(start),
            "to_date": _ymd(end),
            "limit": 5000,
            "sort": "asc",
        },
    )


def _opening_range_hl(minute_bars: List[dict], minutes: int = 30) -> Dict[str, float | None]:
    rth = [b for b in minute_bars if _is_rth_bar(int(b.get("t", 0)))]
    rth30 = rth[:minutes] if len(rth) >= minutes else []
    if not rth30:
        return {"opening_range_high": None, "opening_range_low": None}
    highs = [float(b.get("h", 0.0)) for b in rth30]
    lows = [float(b.get("l", 0.0)) for b in rth30]
    return {"opening_range_high": max(highs), "opening_range_low": min(lows)}


def _rel_volume_5(minute_bars: List[dict]) -> float | None:
    if len(minute_bars) < 10:
        return None
    vols = [float(b.get("v", 0.0)) for b in minute_bars]
    last5 = sum(vols[-5:]) / 5.0
    med = sorted(vols)[len(vols) // 2]
    if med == 0:
        return None
    return last5 / med


def _is_power_hour(minute_bars: List[dict]) -> bool:
    if not minute_bars:
        return False
    ts = int(_last(minute_bars).get("t", 0))
    dt_et = datetime.fromtimestamp(ts / 1000.0, tz=timezone.utc).astimezone(NY)
    return (dt_et.hour == 15) or (dt_et.hour == 16 and dt_et.minute == 0)


async def build_context_from_polygon(symbol: str, the_day: str) -> Dict[str, Any]:
    # Try minute first
    minute = await _fetch_bars(symbol, the_day, "minute", lookback_days=1)
    minute_err = isinstance(minute, dict) and minute.get("_error")
    minute_bars = (minute or {}).get("results", [])

    # Always pull some daily history for PDH/PDL (60 days)
    daily = await _fetch_bars(symbol, the_day, "day", lookback_days=60)
    daily_bars = (daily or {}).get("results", [])
    pd_hl = _fetch_prev_day_hl(daily_bars, the_day)

    if (not minute_err) and minute_bars:
        closes = [float(b.get("c", 0.0)) for b in minute_bars]
        price = float(_last(minute_bars).get("c"))
        vwap = _vwap(minute_bars)
        bars_above = _bars_above_vwap(minute_bars, vwap)
        ema9_last = _ema(closes, 9)
        ema20_last = _ema(closes, 20)
        ema_posture = ema9_last is not None and ema20_last is not None and ema9_last > ema20_last
        rsi_series = _rsi(closes, 14)
        divergence = _divergence_tag(minute_bars, rsi_series)
        or_hl = _opening_range_hl(minute_bars, 30)
        relv5 = _rel_volume_5(minute_bars)
        last_ts_ms = int(_last(minute_bars).get("t"))
        return {
            "symbol": symbol.upper(),
            "price": price,
            "vwap": vwap,
            "bars_above_vwap": bars_above,
            "ema9_gt_ema20": bool(ema_posture),
            "divergence_5m": divergence,
            "prev_day_high": pd_hl.get("prev_day_high"),
            "prev_day_low": pd_hl.get("prev_day_low"),
            "opening_range_high": or_hl.get("opening_range_high"),
            "opening_range_low": or_hl.get("opening_range_low"),
            "rel_volume_5": relv5,
            "last_bar_time_eastern": _ts_to_eastern_str(last_ts_ms),
            "is_power_hour": _is_power_hour(minute_bars),
            "source": "minute",
            "realtime": True,
        }

    # Fallback: daily context
    if isinstance(daily, dict) and daily.get("_error"):
        return {"_error": daily.get("_error"), "_diag": daily, "symbol": symbol, "date": the_day}

    if not daily_bars:
        return {"_error": "no_bars_daily", "_diag": daily, "symbol": symbol, "date": the_day}

    price = float(_last(daily_bars).get("c"))
    closes = [float(b.get("c", 0.0)) for b in daily_bars]
    ema9_last = _ema(closes, 9)
    ema20_last = _ema(closes, 20)
    ema_posture = ema9_last is not None and ema20_last is not None and ema9_last > ema20_last
    rsi_series = _rsi(closes, 14)
    divergence = _divergence_tag(daily_bars, rsi_series)

    return {
        "symbol": symbol.upper(),
        "price": price,
        "vwap": None,
        "bars_above_vwap": 0,
        "ema9_gt_ema20": bool(ema_posture),
        "divergence_5m": divergence,
        "prev_day_high": pd_hl.get("prev_day_high"),
        "prev_day_low": pd_hl.get("prev_day_low"),
        "opening_range_high": None,
        "opening_range_low": None,
        "rel_volume_5": None,
        "last_bar_time_eastern": None,
        "is_power_hour": False,
        "source": "daily_fallback",
        "realtime": False,
    }
