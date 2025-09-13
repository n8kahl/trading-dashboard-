from fastapi import APIRouter
from typing import List, Optional
from app.services import polygon_client as pg

# Try to use shared state if present
try:
    from app.services import stream_state as ss
except Exception:
    ss = None  # type: ignore

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

def _do_snapshot(symbols: Optional[List[str]]):
    if not symbols:
        return {"ok": False, "error": "no_symbols"}

    try:
        quotes = pg.multi_last_trades(symbols)
    except Exception as e:
        # e.g., POLYGON_API_KEY not set or network error
        return {"ok": False, "error": f"snapshot_failed: {e}"}

    # push into shared state if available
    if ss:
        set_one = getattr(ss, "set_quote", None)
        if callable(set_one):
            for sym, q in quotes.items():
                if q.get("price") is not None:
                    try: set_one(sym, q)
                    except Exception: pass
        get_state = getattr(ss, "get_state", None)
        if callable(get_state):
            try:
                st = get_state()
                st_quotes = st.setdefault("quotes", {})
                st_quotes.update({k: v for k, v in quotes.items() if v.get("price") is not None})
            except Exception:
                pass

    return {"ok": True, "data": {"symbols": symbols, "quotes": quotes}}

def _resolve_symbols(payload: dict | None):
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

    return symbols

@router.post("/snapshot")
def snapshot_post(payload: dict | None = None):
    return _do_snapshot(_resolve_symbols(payload))

@router.get("/snapshot")
def snapshot_get(symbols: Optional[str] = None):
    # allow GET /snapshot?symbols=AAPL,NVDA
    syms = [s.strip().upper() for s in (symbols or "").split(",") if s.strip()] if symbols else None
    return _do_snapshot(syms)
