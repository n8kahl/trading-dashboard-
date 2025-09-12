from __future__ import annotations
from typing import Any, Dict
from datetime import datetime

def build_artifact(symbol: str, strategy: str, score: float, expected_r: float, features: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ts": datetime.utcnow().isoformat() + "Z",
        "symbol": symbol.upper(),
        "strategy": strategy,
        "score": float(score),
        "expected_r": float(expected_r),
        "features": features or {},
    }
