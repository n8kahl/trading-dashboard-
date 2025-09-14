from fastapi import APIRouter
import os

def _has(name: str) -> bool:
    return bool(os.getenv(name))

def _resolve_base() -> str:
    base = os.getenv("TRADIER_BASE")
    env = (os.getenv("TRADIER_ENV") or "").lower()
    if not base:
        base = "https://sandbox.tradier.com" if env == "sandbox" else "https://api.tradier.com"
    if not base.rstrip("/").endswith("/v1"):
        base = base.rstrip("/") + "/v1"
    return base

router = APIRouter(prefix="/api/v1/diag", tags=["diag"])

@router.get("/providers")
async def providers():
    token_name = "TRADIER_API_KEY" if _has("TRADIER_API_KEY") else ("TRADIER_ACCESS_TOKEN" if _has("TRADIER_ACCESS_TOKEN") else None)
    return {
        "polygon_key_present": _has("POLYGON_API_KEY"),
        "tradier_token_var": token_name,
        "tradier_token_present": bool(token_name),
        "tradier_env": os.getenv("TRADIER_ENV", "").lower() or None,
        "tradier_base_resolved": _resolve_base()
    }
