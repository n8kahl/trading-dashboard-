from __future__ import annotations
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass
import math

@dataclass
class ScoreWeights:
    delta_fit: float = 0.40
    spread_stability: float = 0.25
    liquidity: float = 0.20
    iv_percentile: float = 0.10
    age: float = 0.05

def _safe(v, default=None):
    return v if v is not None else default

def _delta_fit(delta: Optional[float], horizon: str) -> float:
    target = 0.50 if horizon == "scalp" else 0.40 if horizon == "intraday" else 0.30
    if delta is None:
        return 0.5
    d = abs(delta)
    return max(0.0, 1.0 - min(1.0, abs(d - target)))

def _spread_quality(spread_pct: Optional[float]) -> float:
    # <= 3% → ~1.0, 6% → ~0.5, 12% → ~0.0
    if spread_pct is None:
        return 0.5
    return max(0.0, 1.0 - min(1.0, spread_pct/12.0))

def _liquidity(oi: Optional[int], vol: Optional[int]) -> float:
    oi = oi or 0
    vol = vol or 0
    return min(1.0, (oi/1000.0 + vol/5000.0))

def _iv_bucket(iv: Optional[float]) -> float:
    # Prefer mid-range IV; neutral if unknown
    if iv is None:
        return 0.5
    return 1.0 - min(1.0, abs(iv - 0.25)/0.40)

def _age_score(age_secs: Optional[float]) -> float:
    # Favor fresher prints; if unknown, neutral
    if age_secs is None:
        return 0.5
    if age_secs <= 60:   # last minute
        return 1.0
    if age_secs <= 300:  # last 5 minutes
        return 0.8
    if age_secs <= 900:  # last 15 minutes
        return 0.6
    return 0.4

def tradeability_score(contract: Dict[str, Any], horizon: str = "intraday", weights: ScoreWeights = ScoreWeights()) -> Tuple[int, Dict[str, float]]:
    delta = _safe(contract.get("delta"))
    spread_pct = _safe(contract.get("spread_pct"))
    oi = _safe(contract.get("oi"), 0)
    vol = _safe(contract.get("volume"), 0)
    iv  = _safe(contract.get("iv"))
    # If you pass last_trade time into the contract later, compute age here. For now, neutral.
    age = None

    comps = {
        "delta_fit": _delta_fit(delta, horizon),
        "spread_stability": _spread_quality(spread_pct),
        "liquidity": _liquidity(oi, vol),
        "iv_percentile": _iv_bucket(iv),
        "age": _age_score(age)
    }
    score = (
        comps["delta_fit"]*weights.delta_fit +
        comps["spread_stability"]*weights.spread_stability +
        comps["liquidity"]*weights.liquidity +
        comps["iv_percentile"]*weights.iv_percentile +
        comps["age"]*weights.age
    )
    return int(round(score*100)), comps

def expected_move_from_straddle(last_price: float, candidates: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """
    Estimate EM from near-dated ATM straddle mid.
    Pass a small set of near-spot calls & puts (you already rank & filter).
    EM_abs ≈ (mid_call + mid_put). If only one side present, return None.
    """
    if not candidates or last_price is None:
        return None, None

    # Find nearest call and put by |strike - spot|
    calls = sorted([c for c in candidates if (c.get("type") or "").lower() == "call"], key=lambda r: abs((r.get("strike") or 0) - last_price))
    puts  = sorted([p for p in candidates if (p.get("type") or "").lower() == "put"],  key=lambda r: abs((r.get("strike") or 0) - last_price))

    if not calls or not puts:
        return None, None

    def _mid(x):
        b, a = x.get("bid"), x.get("ask")
        if b is None or a is None or a <= 0:
            # fallback to last if quotes are missing off-hours
            return x.get("last")
        return (b + a)/2.0

    c = calls[0]; p = puts[0]
    c_mid = _mid(c); p_mid = _mid(p)
    if c_mid is None or p_mid is None:
        return None, None

    em_abs = max(0.0, c_mid + p_mid)  # simple straddle mid
    em_rel = em_abs / last_price if last_price else None
    return em_abs, em_rel

def probability_of_touch(distance: float, sigma_abs: float, T_hours: float = 6.5) -> Optional[float]:
    """
    P(max W_T >= d) ≈ 2(1 - Φ(d / (σ * sqrt(T)))) for Brownian motion.
    distance: absolute price distance to target from spot
    sigma_abs: absolute expected move over the same horizon (proxy for σ*sqrt(T))
    """
    if distance is None or sigma_abs is None or sigma_abs <= 0:
        return None
    z = distance / sigma_abs
    # standard normal CDF via erf
    phi = 0.5*(1.0 + math.erf(z / math.sqrt(2)))
    p = 2.0 * (1.0 - phi)
    return max(0.0, min(1.0, p))
