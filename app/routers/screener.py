from fastapi import APIRouter

router = APIRouter(prefix="/screener", tags=["screener"])

_DEFAULT_WATCHLIST = ["SPY","QQQ","AAPL","NVDA","MSFT","TSLA","META","AMZN"]

@router.get("/watchlist/get", summary="Get default watchlist symbols")
def watchlist_get():
    return {"ok": True, "symbols": _DEFAULT_WATCHLIST}

@router.get("/watchlist/ranked", summary="Ranked picks (placeholder)")
def watchlist_ranked():
    # Minimal placeholder that keeps API contract stable.
    return {"ok": True, "env": "live", "note": "ranked placeholder", "count_considered": 0, "picks": []}
