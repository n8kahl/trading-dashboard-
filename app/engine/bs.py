from __future__ import annotations

import math
from typing import Literal, Tuple, Optional

def _phi(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2)))

def _norm_pdf(x: float) -> float:
    return (1.0 / math.sqrt(2*math.pi)) * math.exp(-0.5 * x * x)

def _to_T_years(days_to_exp: float) -> float:
    # Convert calendar days to trading years approx
    return max(1.0/365.0, float(days_to_exp) / 365.0)

def greeks(S: float, K: float, iv: float, days_to_exp: float, typ: Literal['call','put'], r: float = 0.0) -> Tuple[float, float, float]:
    """
    Return (delta, theta, vega) per contract (not scaled by quantity).
    S: spot, K: strike, iv: annualized volatility (0.0–2.0), T in calendar days.
    theta is returned per day (approx), vega per 1.0 change in IV (absolute).
    """
    T = _to_T_years(days_to_exp)
    iv = max(1e-6, float(iv))
    if S <= 0 or K <= 0:
        return 0.0, 0.0, 0.0
    try:
        d1 = (math.log(S/K) + (r + 0.5*iv*iv)*T) / (iv*math.sqrt(T))
        d2 = d1 - iv*math.sqrt(T)
        if typ == 'call':
            delta = _phi(d1)
            theta = (-(S*_norm_pdf(d1)*iv)/(2*math.sqrt(T)) - r*K*math.exp(-r*T)*_phi(d2)) / 365.0
        else:
            delta = _phi(d1) - 1.0
            theta = (-(S*_norm_pdf(d1)*iv)/(2*math.sqrt(T)) + r*K*math.exp(-r*T)*_phi(-d2)) / 365.0
        vega = (S * _norm_pdf(d1) * math.sqrt(T)) / 100.0  # per 1% change in IV
        return float(delta), float(theta), float(vega)
    except Exception:
        return 0.0, 0.0, 0.0

