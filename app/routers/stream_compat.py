from fastapi import APIRouter
from app.services import stream_state as ss

# Mirror endpoints WITHOUT /api/v1 prefix so legacy/buggy callers still work
router = APIRouter(prefix="/stream", tags=["stream-compat"])

@router.post("/track")
def track_compat(payload: dict):
    symbols = payload.get("symbols") or []
    return ss.set_symbols(symbols)

@router.get("/quotes")
def quotes_compat():
    return {"ok": True, "data": ss.get_state()}
