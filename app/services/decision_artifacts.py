from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Dict


def build_artifact(
    symbol: str, strategy: str, score: float, expected_r: float, features: Dict[str, Any]
) -> Dict[str, Any]:
    return {
        "ts": datetime.now(UTC).isoformat() + "Z",
        "symbol": symbol.upper(),
        "strategy": strategy,
        "score": float(score),
        "expected_r": float(expected_r),
        "features": features or {},
    }
