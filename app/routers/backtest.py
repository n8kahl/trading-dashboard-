from fastapi import APIRouter
router = APIRouter(prefix="/backtest", tags=["backtest"])

@router.get("/health")
def health(): return {"ok": True, "router": "backtest"}

@router.post("/quick")
def quick(payload: dict): return {"ok": False, "error": "backtest quick not implemented yet", "echo": payload}
