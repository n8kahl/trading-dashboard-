from typing import Dict, Any, List, Optional
import time
from statistics import fmean
from app.services import alerts_store

# in-memory cache to reduce DB hits (refresh every 10s)
_LAST_LOAD = 0.0
_CACHE: Dict[int, Dict[str,Any]] = {}
_LOAD_INTERVAL = 10.0

# recent triggers (in-memory mirror for fast API reads)
_RECENT: List[Dict[str,Any]] = []
_RECENT_MAX = 100

def _maybe_reload():
    global _LAST_LOAD, _CACHE
    if time.time() - _LAST_LOAD < _LOAD_INTERVAL:
        return
    active = alerts_store.list_active()
    _CACHE = {a["id"]: a for a in active}
    _LAST_LOAD = time.time()

def _vwap(bars: List[Dict[str,Any]], window: int = 30) -> Optional[float]:
    if not bars: return None
    w = bars[-window:] if len(bars) > window else bars
    num = 0.0; den = 0.0
    for b in w:
        p = (b["h"] + b["l"] + b["c"]) / 3.0
        v = b["v"] or 0.0
        num += p * v; den += v
    return (num/den) if den > 0 else None

def _pct_change(bars: List[Dict[str,Any]], minutes: int) -> Optional[float]:
    if len(bars) < minutes+1: return None
    a = bars[-minutes-1]["c"]; b = bars[-1]["c"]
    if a == 0: return None
    return (b - a) / a * 100.0

def _last_price(bars: List[Dict[str,Any]]) -> Optional[float]:
    return float(bars[-1]["c"]) if bars else None

def _fire(alert: Dict[str,Any], symbol: str, reason: str, ctx: Dict[str,Any]):
    alerts_store.mark_triggered(alert["id"])
    payload = {"reason": reason, "context": ctx}
    alerts_store.add_trigger(alert["id"], symbol, payload)
    _RECENT.insert(0, {"alert_id": alert["id"], "symbol": symbol, "reason": reason, "payload": payload, "ts": time.time()})
    del _RECENT[_RECENT_MAX:]

def evaluate_for_symbol(symbol: str, bars: List[Dict[str,Any]]):
    _maybe_reload()
    if not _CACHE: return
    lp = _last_price(bars)
    if lp is None: return
    vwap30 = _vwap(bars, 30)
    for alert in list(_CACHE.values()):
        if alert["symbol"].upper() != symbol.upper(): continue
        cond = alert["condition"] or {}
        t = (cond.get("type") or "").lower()
        if t == "price_above":
            x = float(cond.get("value", 0))
            if lp >= x: _fire(alert, symbol, f"price_above {x}", {"last": lp})
        elif t == "price_below":
            x = float(cond.get("value", 0))
            if lp <= x: _fire(alert, symbol, f"price_below {x}", {"last": lp})
        elif t == "cross_vwap_up":
            if vwap30 is not None and bars[-2:]:
                prev = bars[-2]["c"]
                if prev < vwap30 and lp >= vwap30:
                    _fire(alert, symbol, "cross_vwap_up", {"last": lp, "vwap30": vwap30})
        elif t == "cross_vwap_down":
            if vwap30 is not None and bars[-2:]:
                prev = bars[-2]["c"]
                if prev > vwap30 and lp <= vwap30:
                    _fire(alert, symbol, "cross_vwap_down", {"last": lp, "vwap30": vwap30})
        elif t == "percent_change_ge":
            mins = int(cond.get("minutes", 5))
            th   = float(cond.get("threshold_pct", 1.0))
            pc = _pct_change(bars, mins)
            if pc is not None and abs(pc) >= th:
                _fire(alert, symbol, f"percent_change_ge {th}% ({pc:.2f}%)", {"pct": pc, "minutes": mins})

def recent_triggers(limit: int = 50) -> List[Dict[str,Any]]:
    # prefer DB for durability; fall back to memory
    try:
        rows = alerts_store.recent_triggers(limit)
        if rows: return rows
    except Exception:
        pass
    return _RECENT[:limit]
