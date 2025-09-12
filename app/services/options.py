from typing import List, Dict, Any, Tuple
from datetime import datetime, timezone

def _days_to_exp(exp: str) -> int:
    try:
        if str(exp).isdigit():
            dt = datetime.fromtimestamp(int(exp)/1000.0, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(exp))
        return max(0, (dt.date() - datetime.now(tz=timezone.utc).date()).days)
    except Exception:
        return 9999

def _spread_pct(ask: float, bid: float) -> float:
    mid = (ask + bid)/2.0 if (ask>0 and bid>0) else max(ask,bid,1e-9)
    if mid <= 0: return 999.0
    return max(0.0, (ask - bid)/mid * 100.0)

def filter_and_score_contracts(contracts: List[Dict[str, Any]], *,
                               side: str, horizon: str,
                               delta_range: Tuple[float,float],
                               max_spread_pct: float,
                               min_oi: int, min_vol: int) -> Dict[str, Any]:
    picks: List[Dict[str, Any]] = []
    dropped: List[Dict[str, Any]] = []

    for c in contracts or []:
        rec = {
            "symbol": c.get("symbol") or c.get("contract_symbol"),
            "type": (c.get("type") or c.get("option_type") or "").upper(),
            "strike": float(c.get("strike") or 0.0),
            "expiration": c.get("expiration") or c.get("exp_date"),
            "bid": float(c.get("bid") or 0.0),
            "ask": float(c.get("ask") or 0.0),
            "delta": float(c.get("delta") or 0.0),
            "iv": float(c.get("iv") or c.get("implied_volatility") or 0.0),
            "oi": int(c.get("open_interest") or c.get("oi") or 0),
            "volume": int(c.get("volume") or 0),
        }
        rec["expiration_days"] = _days_to_exp(rec["expiration"])
        rec["spread_pct"] = round(_spread_pct(rec["ask"], rec["bid"]), 2)

        # filters
        reasons = []
        if (side == "CALL" and rec["type"] != "CALL") or (side == "PUT" and rec["type"] != "PUT"):
            reasons.append("wrong_type")
        if not (delta_range[0] <= abs(rec["delta"]) <= delta_range[1]):
            reasons.append("delta_out_of_range")
        if horizon == "short" and not (0 <= rec["expiration_days"] <= 7):
            reasons.append("expiry_not_short_0_7d")
        if horizon == "swing" and not (14 <= rec["expiration_days"] <= 21):
            reasons.append("expiry_not_swing_14_21d")
        if rec["spread_pct"] > max_spread_pct:
            reasons.append("spread_too_wide")
        if rec["oi"] < min_oi:
            reasons.append("oi_too_low")
        if rec["volume"] < min_vol:
            reasons.append("vol_too_low")

        if reasons:
            rec["excluded_reasons"] = reasons
            dropped.append(rec)
            continue

        # scoring
        target = sum(delta_range)/2.0
        delta_score = max(0, 45 - 90*abs(abs(rec["delta"])-target))  # sharp peak near target
        spread_score = max(0, 30 - 8*rec["spread_pct"])               # tighter is better
        liq_score = min(15, (rec["oi"]/1000)*7 + (rec["volume"]/600)*8)
        iv_penalty = max(0, (rec["iv"]-0.7)*20) if rec["iv"]>0 else 0 # penalize extreme IV
        score = delta_score + spread_score + liq_score - iv_penalty

        rec["score"] = round(score,1)
        picks.append(rec)

    picks.sort(key=lambda x: x["score"], reverse=True)
    return {"picks": picks, "dropped": dropped}
