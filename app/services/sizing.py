from typing import Dict, Any, Optional
import math

def equity_size(buying_power: float, entry: float, stop: float, risk_pct: float = 0.005) -> Dict[str, Any]:
    """Risk % of buying power; shares from R = entry - stop."""
    if entry <= 0 or stop <= 0 or buying_power <= 0:
        return {"ok": False, "error": "invalid inputs"}
    r = abs(entry - stop)
    if r <= 0:
        return {"ok": False, "error": "stop equals entry"}
    risk_cash = buying_power * max(0.0001, risk_pct)
    shares = max(0, math.floor(risk_cash / r))
    return {
        "ok": True,
        "risk_cash": risk_cash,
        "per_share_r": r,
        "quantity": shares,
        "notes": f"Risk {risk_pct*100:.2f}% of buying power; stop distance {r:.4f}",
    }

def option_size(buying_power: float, premium_entry: float, premium_stop: Optional[float] = None,
                risk_pct: float = 0.005, contract_multiplier: int = 100) -> Dict[str, Any]:
    """
    If no premium_stop provided, assume 50% premium stop.
    Risk per contract = (entry - stop) * multiplier
    """
    if premium_entry <= 0 or buying_power <= 0:
        return {"ok": False, "error": "invalid inputs"}
    stop = premium_stop if (premium_stop and premium_stop > 0) else premium_entry * 0.5
    r_per_contract = max(0.0, premium_entry - stop) * contract_multiplier
    if r_per_contract <= 0:
        return {"ok": False, "error": "non-positive per-contract risk"}
    risk_cash = buying_power * max(0.0001, risk_pct)
    contracts = max(0, math.floor(risk_cash / r_per_contract))
    return {
        "ok": True,
        "risk_cash": risk_cash,
        "per_contract_r": r_per_contract,
        "quantity": contracts,
        "assumed_stop": stop,
        "notes": f"Risk {risk_pct*100:.2f}% of buying power; {contract_multiplier}x multiplier.",
    }
