from __future__ import annotations

from typing import Any, Dict, Optional

from app.db import db_session
from app.models.narrative import Narrative


def save_guidance(t_ms: int, symbol: str, guidance: Dict[str, Any], *, horizon: Optional[str] = None, band: Optional[str] = None, position_id: Optional[str] = None) -> bool:
    """Persist a narrator guidance JSON. Returns True on success; False if DB unavailable.

    This is a best-effort insert that should not raise for the caller.
    """
    try:
        with db_session() as s:
            if s is None:
                return False
            row = Narrative(
                t_ms=int(t_ms),
                symbol=symbol.upper(),
                horizon=horizon,
                band=band,
                guidance_json=guidance,
                position_id=position_id,
            )
            s.add(row)
            s.commit()
            return True
    except Exception:
        return False

