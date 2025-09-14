from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/diag", tags=["diag"])

@router.get("/health")
async def health():
    return {"ok": True, "service": "coach-exec", "status": "healthy"}
