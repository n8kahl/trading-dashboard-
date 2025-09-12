import os
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple
from datetime import datetime, timezone, date

import httpx

from app.utils.timebox import parse_expiration, days_to

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com").rstrip("/")
TRADIER_ACCESS_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")
TRADIER_ACCOUNT_ID = os.getenv("TRADIER_ACCOUNT_ID")

HEADERS = {
    "Authorization": f"Bearer {TRADIER_ACCESS_TOKEN}" if TRADIER_ACCESS_TOKEN else "",
    "Accept": "application/json",
    "User-Agent": "trading-assistant/1.0"
}

@dataclass
class PickerConfig:
    # hard gates (defaults; you can tune later)
    max_spread_pct: float = 0.08     # 8%
    min_oi: int = 500
    min_vol: int = 200
    dte_min: int = 0                 # allow 0DTE
    dte_max: int = 10
    side: str = "call"               # "call" | "put"
    limit: int = 3

    # scoring weights
    w_delta_band: float = 0.35
    w_inv_spread: float = 0.30
    w_oi_rank: float = 0.20
    w_v_over_oi: float = 0.15

def _safe_div(a: float, b: float, default: float = 0.0) -> float:
    try:
        if b == 0:
            return default
        return a / b
    except Exception:
        return default

def _spread_pct(bid: float | None, ask: float | None) -> float:
    if not bid or not ask or bid <= 0 or ask <= 0 or ask < bid:
        return 1.0  # effectively horrible spread
    mid = (bid + ask) / 2.0
    return (ask - bid) / mid if mid > 0 else 1.0

def _delta_band_score(opt: Dict[str, Any], side: str) -> float:
    """
    Prefer ~0.35-0.45 delta for directional intraday contracts.
    If greeks missing, try to infer approximate delta by moneyness if available; otherwise 0.
    """
    delta = None
    g = opt.get("greeks") or {}
    if isinstance(g, dict):
        delta = g.get("delta")
        # Tradier greeks may be strings
        try:
            delta = float(delta) if delta is not None else None
        except Exception:
            delta = None

    if delta is None:
        # Fallback: 0
        return 0.0

    d = abs(delta)  # calls positive, puts negative
    target_low, target_high = 0.35, 0.45
    if target_low <= d <= target_high:
        return 1.0
    # linear decay outside band, clamped to 0
    if d < target_low:
        return max(0.0, (d / target_low) * 0.7)
    else:
        # d > target_high
        return max(0.0, (1.0 - (d - target_high) / (0.6 - target_high)) * 0.7) if d < 0.6 else 0.1

async def _tradier_json(client: httpx.AsyncClient, url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    r = await client.get(url, headers=HEADERS, params=params or {}, timeout=20.0)
    if r.status_code >= 300:
        raise RuntimeError(f"Tradier GET {url} {r.status_code}: {r.text}")
    return r.json()

async def _expirations(client: httpx.AsyncClient, symbol: str) -> List[date]:
    url = f"{TRADIER_BASE}/v1/markets/options/expirations"
    js = await _tradier_json(client, url, {"symbol": symbol, "includeAllRoots": "true", "strikes": "false"})
    exps = js.get("expirations", {}).get("date", [])
    # result may be list or single string
    if isinstance(exps, str):
        exps = [exps]
    return [parse_expiration(s) for s in exps]

async def _chains_for_expiry(client: httpx.AsyncClient, symbol: str, expiry: date) -> List[Dict[str, Any]]:
    url = f"{TRADIER_BASE}/v1/markets/options/chains"
    js = await _tradier_json(client, url, {"symbol": symbol, "expiration": expiry.isoformat(), "greeks": "true"})
    # Tradier shape: {"options": {"option": [...]}}
    opts = js.get("options", {}).get("option", [])
    if isinstance(opts, dict):
        opts = [opts]
    return opts

def _pick_side(options: List[Dict[str, Any]], side: str) -> List[Dict[str, Any]]:
    # Tradier key often = "option_type": "call"/"put"
    side_key = side.lower()
    return [o for o in options if (o.get("option_type") or o.get("type", "")).lower() == side_key]

def _rank_contracts(options: List[Dict[str, Any]], cfg: PickerConfig, dte_map: Dict[str, int]) -> List[Dict[str, Any]]:
    # Build ranks (OI rank) and compute score
    oi_vals = [int(o.get("open_interest") or 0) for o in options]
    max_oi = max(oi_vals) if oi_vals else 1

    ranked: List[Tuple[float, Dict[str, Any]]] = []
    for o in options:
        bid = float(o.get("bid") or 0.0)
        ask = float(o.get("ask") or 0.0)
        vol = int(o.get("volume") or 0)
        oi = int(o.get("open_interest") or 0)
        sym = o.get("symbol") or o.get("option_symbol") or ""
        dte = dte_map.get(sym, None)

        sp = _spread_pct(bid, ask)

        # Hard gates
        if dte is None or dte < cfg.dte_min or dte > cfg.dte_max:
            continue
        if sp > cfg.max_spread_pct:
            continue
        if oi < cfg.min_oi:
            continue
        if vol < cfg.min_vol:
            continue

        # Components
        s_delta = _delta_band_score(o, cfg.side)
        s_inv_spread = 1.0 / (sp + 1e-6)  # larger when tighter
        s_oi_rank = oi / max_oi if max_oi > 0 else 0.0
        s_v_over_oi = _safe_div(vol, max(oi, 1))

        score = (
            cfg.w_delta_band * s_delta +
            cfg.w_inv_spread * s_inv_spread +
            cfg.w_oi_rank * s_oi_rank +
            cfg.w_v_over_oi * s_v_over_oi
        )

        ranked.append((score, {
            "symbol": sym,
            "bid": bid,
            "ask": ask,
            "mid": (bid + ask) / 2.0 if bid > 0 and ask > 0 else None,
            "spread_pct": sp,
            "volume": vol,
            "open_interest": oi,
            "dte": dte,
            "greeks": o.get("greeks"),
            "desc": o.get("description"),
            "last": o.get("last"),
            "strike": o.get("strike"),
            "expiration_date": o.get("expiration_date") or o.get("expiration")
        }))

    ranked.sort(key=lambda t: t[0], reverse=True)
    return [{"score": round(s, 6), **item} for s, item in ranked]
    
async def pick_options(symbol: str, side: str, dte_min: int, dte_max: int, limit: int, overrides: Dict[str, float] | None = None) -> Dict[str, Any]:
    if not TRADIER_ACCESS_TOKEN:
        return {"ok": False, "error": "TRADIER_ACCESS_TOKEN not set"}

    cfg = PickerConfig(side=side, dte_min=dte_min, dte_max=dte_max, limit=limit)
    if overrides:
        for k, v in overrides.items():
            if hasattr(cfg, k):
                setattr(cfg, k, v)

    today = datetime.now(timezone.utc).date()

    async with httpx.AsyncClient(timeout=25.0) as client:
        # 1) expirations
        exps = await _expirations(client, symbol)
        if not exps:
            return {"ok": False, "error": "No expirations returned"}

        # filter by DTE window quickly to cut API pressure
        window_exps = [e for e in exps if cfg.dte_min <= days_to(e, today) <= cfg.dte_max or (cfg.dte_min == 0 and days_to(e, today) == 0)]
        if not window_exps:
            return {"ok": True, "candidates": [], "note": "No expirations in requested DTE window"}

        candidates: List[Dict[str, Any]] = []
        dte_map: Dict[str, int] = {}

        # 2) chains per expiry (paginate naturally by expiries)
        for exp in sorted(window_exps)[:8]:  # pragmatic cap
            dte_val = days_to(exp, today)
            opts = await _chains_for_expiry(client, symbol, exp)
            side_filtered = _pick_side(opts, cfg.side)

            # map each contract to DTE
            for o in side_filtered:
                sym = o.get("symbol") or o.get("option_symbol")
                if sym:
                    dte_map[sym] = dte_val
            candidates.extend(side_filtered)

        # 3) rank & filter
        ranked = _rank_contracts(candidates, cfg, dte_map)
        topn = ranked[: cfg.limit]

        return {
            "ok": True,
            "policy": {
                "max_spread_pct": cfg.max_spread_pct,
                "min_oi": cfg.min_oi,
                "min_vol": cfg.min_vol,
                "dte_min": cfg.dte_min,
                "dte_max": cfg.dte_max,
                "side": cfg.side
            },
            "symbol": symbol.upper(),
            "today": today.isoformat(),
            "count_scored": len(ranked),
            "returned": len(topn),
            "contracts": topn
        }
