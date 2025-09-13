from fastapi import APIRouter
from app.services import stream_state as ss

router = APIRouter(prefix="/api/v1/stream", tags=["stream"])

@router.post("/track")
def track(payload: dict):
    symbols = payload.get("symbols") or []
    return ss.set_symbols(symbols)

@router.get("/state")
def state():
    return {"ok": True, "data": ss.get_state()}
