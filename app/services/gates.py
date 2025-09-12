from __future__ import annotations

from datetime import datetime, time
from typing import Any, Dict
from zoneinfo import ZoneInfo

from app.config.policy import POLICY

# We treat windows in ET (New York)
_ET = ZoneInfo("America/New_York")


def gate_session(now: datetime | None = None) -> bool:
    """
    True if now (ET) is inside any configured session window.
    """
    if now is None:
        now = datetime.now(_ET)
    local_t = now.astimezone(_ET).time()
    for start_s, end_s in POLICY.session_windows_et:
        sh, sm = map(int, start_s.split(":"))
        eh, em = map(int, end_s.split(":"))
        if time(sh, sm) <= local_t <= time(eh, em):
            return True
    return False


def gate_equity_liquidity(metrics: Dict[str, Any]) -> bool:
    """
    metrics expects:
      {
        "rvol": float,
        "spread_pct": float (e.g. 0.0004),
        "dollar_vol": float
      }
    """
    rvol = float(metrics.get("rvol", 0.0))
    spread = float(metrics.get("spread_pct", 1.0))
    dvol = float(metrics.get("dollar_vol", 0.0))
    g = POLICY.equities
    return (rvol >= g.rvol_min) and (spread <= g.spread_pct_max) and (dvol >= g.dollar_vol_min)


def gate_options_quality(metrics: Dict[str, Any]) -> bool:
    """
    metrics expects:
      {
        "spread_pct": float (0.08 = 8%),
        "oi": int,
        "vol": int,
        "dte": int
      }
    """
    spread = float(metrics.get("spread_pct", 1.0))
    oi = int(metrics.get("oi", 0))
    vol = int(metrics.get("vol", 0))
    dte = int(metrics.get("dte", 0))
    g = POLICY.options
    return spread <= g.spread_pct_max and oi >= g.oi_min and vol >= g.vol_min and g.dte_min <= dte <= g.dte_max


def entry_checks(metrics: Dict[str, Any]) -> bool:
    """
    Basic entry timing checks.
    metrics can include:
      { "retest_hold_pass": bool, "dist_to_avwap_pct": float }
    """
    e = POLICY.entry
    if e.require_retest_hold and not bool(metrics.get("retest_hold_pass", False)):
        return False
    dist = float(metrics.get("dist_to_avwap_pct", 999.0))
    return dist <= e.dist_to_avwap_max_pct
