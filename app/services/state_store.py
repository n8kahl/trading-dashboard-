from __future__ import annotations

import os, json, time
from typing import Dict, Any, List, Optional
from datetime import date

_DEFAULT_PATH = os.getenv("STATE_STORE_PATH") or os.path.join("app", "data", "state.json")

def _ensure_dir(path: str) -> None:
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def _load(path: str = _DEFAULT_PATH) -> Dict[str, Any]:
    try:
        with open(path, "r") as f:
            return json.load(f) or {}
    except Exception:
        return {}

def _save(obj: Dict[str, Any], path: str = _DEFAULT_PATH) -> None:
    try:
        _ensure_dir(path)
        with open(path, "w") as f:
            json.dump(obj, f)
    except Exception:
        pass

def _trim_days(daily: Dict[str, Any], keep: int = 10) -> Dict[str, Any]:
    keys = sorted(daily.keys())
    if len(keys) <= keep:
        return daily
    for k in keys[:-keep]:
        daily.pop(k, None)
    return daily

def record_chain_aggregates(underlying: str, expiry: str, rows: List[Dict[str, Any]], path: str = _DEFAULT_PATH) -> Dict[str, Any]:
    """
    Aggregate OI and volume for an underlying+expiry on the current date.
    Persist last ~10 days in a tiny JSON store. Returns trend metrics.
    """
    und = (underlying or "").upper()
    exp = str(expiry)
    today = date.today().isoformat()

    tot_oi = 0.0
    tot_vol = 0.0
    for rr in rows or []:
        if str(rr.get("expiry") or rr.get("expiration") or rr.get("expiration_date") or (rr.get("options") or {}).get("expiration_date")) != exp:
            continue
        oi = rr.get("open_interest")
        if isinstance(oi, dict):
            oi = oi.get("oi")
        vol = rr.get("volume") or (rr.get("day") or {}).get("volume")
        try:
            if oi is not None:
                tot_oi += float(oi)
        except Exception:
            pass
        try:
            if vol is not None:
                tot_vol += float(vol)
        except Exception:
            pass

    state = _load(path)
    state.setdefault("liquidity", {})
    key = f"{und}:{exp}"
    book = state["liquidity"].setdefault(key, {})
    book[today] = {"oi": tot_oi, "volume": tot_vol, "t": int(time.time())}
    state["liquidity"][key] = _trim_days(book)
    _save(state, path)

    # Compute simple 1d change and 3d averages
    days = sorted(state["liquidity"][key].keys())
    prev = days[-2] if len(days) >= 2 else None
    prev2 = days[-3] if len(days) >= 3 else None
    out: Dict[str, Any] = {"aggregates": {"oi": tot_oi, "volume": tot_vol}}
    if prev:
        p = state["liquidity"][key][prev]
        try:
            out["oi_change_1d"] = round((tot_oi - float(p.get("oi") or 0.0)) / max(1.0, float(p.get("oi") or 1.0)), 3)
        except Exception:
            pass
        try:
            out["vol_change_1d"] = round((tot_vol - float(p.get("volume") or 0.0)) / max(1.0, float(p.get("volume") or 1.0)), 3)
        except Exception:
            pass
    # Rolling averages
    try:
        vals = [float(state["liquidity"][key][d]["oi"]) for d in days[-3:]]
        out["oi_avg_3d"] = sum(vals)/len(vals)
    except Exception:
        pass
    try:
        vals = [float(state["liquidity"][key][d]["volume"]) for d in days[-3:]]
        out["vol_avg_3d"] = sum(vals)/len(vals)
    except Exception:
        pass
    return out

