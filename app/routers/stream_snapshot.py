from fastapi import APIRouter
from typing import List, Optional
from app.services import polygon_client as pg

# Try to use shared state if present
try:
    from app.services import stream_state as ss
except Exception:
    ss = None  # type: ignore

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

@router.post("/snapshot")
def snapshot(payload: dict | None = None):
    payload = payload or {}
    symbols: Optional[List[str]] = None

    # default to tracked symbols in shared state
    if ss and hasattr(ss, "get_state"):
        try:
            st = ss.get_state()
            symbols = list(st.get("symbols") or [])
        except Exception:
            symbols = None

    # allow override via payload
    if not symbols:
        symbols = payload.get("symbols") or []

    if not symbols:
        return {"ok": False, "error": "no_symbols"}

    quotes = pg.multi_last_trades(symbols)

    # push into shared state if available
    if ss:
        set_one = getattr(ss, "set_quote", None)
        if callable(set_one):
            for sym, q in quotes.items():
                if q.get("price") is not None:
                    try:
                        set_one(sym, q)
                    except Exception:
                        pass
        get_state = getattr(ss, "get_state", None)
        if callable(get_state):
            try:
                st = get_state()
                st_quotes = st.setdefault("quotes", {})
                st_quotes.update({k: v for k, v in quotes.items() if v.get("price") is not None})
            except Exception:
                pass

    return {"ok": True, "data": {"symbols": symbols, "quotes": quotes}}
