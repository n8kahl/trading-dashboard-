from __future__ import annotations

from typing import Any, Dict, List

def compute_risk_flags(picks: List[Dict[str, Any]] | None, liquidity_trend: Dict[str, Any] | None, providers: Dict[str, bool] | None) -> List[str]:
    flags: List[str] = []
    prov = providers or {}
    if prov and (not prov.get('polygon') or not prov.get('tradier')):
        flags.append('data_degraded')
    if picks:
        # microstructure caution if many picks are wide
        wide = [p for p in picks if (p.get('spread_pct') or 0) > 12]
        if len(wide) >= max(1, len(picks)//2):
            flags.append('microstructure_poor')
    if liquidity_trend:
        try:
            oi_ch = liquidity_trend.get('oi_change_1d')
            vol_avg = liquidity_trend.get('vol_avg_3d')
            if isinstance(oi_ch, (int, float)) and oi_ch < -0.10:
                flags.append('liquidity_soft')
            if isinstance(vol_avg, (int, float)) and vol_avg < 1000:  # tiny flows overall
                flags.append('low_activity')
        except Exception:
            pass
    return flags

