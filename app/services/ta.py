from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict, List, Optional, Tuple
from zoneinfo import ZoneInfo

NY = ZoneInfo("America/New_York")


# ---------- Basic TA ----------
def ema(values: List[float], period: int) -> Optional[float]:
    if not values or len(values) < period:
        return None
    k = 2 / (period + 1)
    e = values[0]
    for v in values[1:]:
        e = v * k + e * (1 - k)
    return e


def atr_1m(bars: List[Dict[str, Any]], period: int = 14) -> Optional[float]:
    if not bars or len(bars) < period + 1:
        return None
    trs = []
    prev_close = float(bars[0].get("c", 0) or 0)
    for b in bars[1:]:
        h, low, c = map(lambda k: float(b.get(k, 0) or 0), ("h", "l", "c"))
        tr = max(h - low, abs(h - prev_close), abs(low - prev_close))
        trs.append(tr)
        prev_close = c
    if len(trs) < period:
        return None
    return sum(trs[-period:]) / period


def anchored_vwap(bars: List[Dict[str, Any]], start_idx: int) -> Optional[float]:
    if not bars or start_idx is None or start_idx < 0 or start_idx >= len(bars):
        return None
    num = den = 0.0
    for b in bars[start_idx:]:
        h = float(b.get("h", 0) or 0)
        low = float(b.get("l", 0) or 0)
        c = float(b.get("c", 0) or 0)
        v = float(b.get("v", 0) or 0)
        tp = (h + low + c) / 3.0
        num += tp * v
        den += v
    return (num / den) if den > 0 else None


def resample_ohlcv_5m(bars_1m: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _resample_n(bars_1m, 5)


def resample_ohlcv_15m(bars_1m: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return _resample_n(bars_1m, 15)


def _resample_n(bars_1m: List[Dict[str, Any]], n: int) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    bucket = []
    for b in bars_1m:
        bucket.append(b)
        if len(bucket) == n:
            o = float(bucket[0]["o"])
            h = max(float(x["h"]) for x in bucket)
            low = min(float(x["l"]) for x in bucket)
            c = float(bucket[-1]["c"])
            v = sum(float(x.get("v", 0) or 0) for x in bucket)
            out.append({"o": o, "h": h, "l": low, "c": c, "v": v})
            bucket = []
    return out


def ema_stack_state(closes: List[float]) -> Optional[str]:
    e9 = ema(closes, 9)
    e20 = ema(closes, 20)
    e50 = ema(closes, 50)
    if any(x is None for x in (e9, e20, e50)):
        return None
    if e9 > e20 > e50:
        return "up"
    if e9 < e20 < e50:
        return "down"
    return "mixed"


# ---------- Time helpers ----------
def _to_ny(dt_s_or_ms: int | float) -> datetime:
    # Epoch seconds or ms → NY-local datetime
    ts = float(dt_s_or_ms)
    if ts > 1e12:  # ms
        ts /= 1000.0
    return datetime.fromtimestamp(ts, NY)


def find_today_open_index(bars: List[Dict[str, Any]]) -> Optional[int]:
    """Index of first bar at/after 09:30 ET of *today* in NY."""
    if not bars:
        return None
    today = datetime.now(NY).date()
    for i, b in enumerate(bars):
        t = b.get("t")
        if t is None:
            return None
        ny = _to_ny(t)
        if ny.date() == today and ny.time() >= time(9, 30):
            return i
    return None


def find_prior_close_anchor_index(bars: List[Dict[str, Any]]) -> Optional[int]:
    """Index of the bar just before today's open (approx prior close)."""
    if not bars:
        return None
    today = datetime.now(NY).date()
    for i, b in enumerate(bars):
        t = b.get("t")
        if t is None:
            return None
        ny = _to_ny(t)
        if ny.date() == today and ny.time() >= time(9, 30):
            return i - 1 if i > 0 else None
    return None


def avwaps_for_today(bars: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """(aVWAP_open, aVWAP_prior_close) on a market day; else (None, None)."""
    i_open = find_today_open_index(bars)
    i_prev = find_prior_close_anchor_index(bars)
    avwap_open = anchored_vwap(bars, i_open) if i_open is not None else None
    avwap_prev = anchored_vwap(bars, i_prev) if i_prev is not None else None
    return avwap_open, avwap_prev


def avwaps_flexible(bars: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """
    Flexible anchors:
      - Market day: aVWAP(open) + prior-close when available.
      - Weekend/holiday fallback: anchor to FIRST bar of returned session.
    """
    if not bars:
        return None, None
    open_today_idx = find_today_open_index(bars)
    if open_today_idx is not None:
        avwap_open = anchored_vwap(bars, open_today_idx)
        avwap_prev = anchored_vwap(bars, find_prior_close_anchor_index(bars)) if avwap_open is not None else None
        return avwap_open, avwap_prev
    # Fallback: anchor to start of returned series (e.g., last session’s open)
    return anchored_vwap(bars, 0), None
