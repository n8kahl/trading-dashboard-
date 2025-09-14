from __future__ import annotations

def build_occ(underlying: str, expiry: str, opt_type: str, strike: float) -> str:
    """Build OCC symbol from parts.
    - underlying: e.g., 'SPY'
    - expiry: 'YYYY-MM-DD'
    - opt_type: 'call'|'put' or 'C'|'P'
    - strike: e.g., 450.0
    """
    und = (underlying or "").upper().strip()
    y, m, d = expiry.split("-")
    yy = y[-2:]
    cp = opt_type.strip().upper()[0]
    cp = 'C' if cp == 'C' else 'P'
    strike8 = f"{int(round(float(strike) * 1000)):08d}"
    return f"{und}{yy}{m}{d}{cp}{strike8}"

