from typing import Any, Dict, List


def _score_contract(c: Dict[str, Any]) -> float:
    # Simple heuristic: higher OI & volume, tighter spread, delta within 0.3–0.5
    oi = float(c.get("open_interest", 0))
    vol = float(c.get("volume", 0))
    spread = float(c.get("spread_pct", 0.05))
    delta = abs(float(c.get("delta", 0.0)))
    delta_score = 1.0 if 0.28 <= delta <= 0.52 else (0.6 if 0.2 <= delta <= 0.65 else 0.2)
    spread_score = max(0.1, 1 - min(spread, 0.1) * 6)  # tight spread → closer to 1
    flow_score = min(1.0, (oi / 5000) * 0.4 + (vol / 10000) * 0.6)
    return round(0.5 * flow_score + 0.3 * spread_score + 0.2 * delta_score, 4)


def get_ranked_picks(mode: str = "sandbox") -> Dict[str, Any]:
    # TODO: replace this mock with your real data pull (Polygon or cached)
    # Example picks skeleton
    picks: List[Dict[str, Any]] = [
        {
            "symbol": "AAPL250912C00240000",
            "expiration": "2025-09-12",
            "strike": 240.0,
            "option_type": "call",
            "delta": 0.49,
            "bid": 2.71,
            "ask": 2.75,
            "mark": 2.73,
            "spread_pct": 0.0145,
            "open_interest": 39019,
            "volume": 50900,
            "dte": 4,
        },
        {
            "symbol": "AAPL250912C00242500",
            "expiration": "2025-09-12",
            "strike": 242.5,
            "option_type": "call",
            "delta": 0.35,
            "bid": 1.64,
            "ask": 1.68,
            "mark": 1.66,
            "spread_pct": 0.0238,
            "open_interest": 8356,
            "volume": 28426,
            "dte": 4,
        },
    ]
    for p in picks:
        p["score"] = _score_contract(p)
    return {
        "ok": True,
        "env": mode,
        "note": f"{mode} ranked (heuristic)",
        "count_considered": len(picks),
        "picks": sorted(picks, key=lambda x: x["score"], reverse=True),
    }
