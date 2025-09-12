from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"ok": True, "service": "watchdog"}


@router.get("/api/v1/diag/health")
def diag_health():
    return {"ok": True, "status": "healthy"}


@router.get("/api/v1/diag/ready")
def diag_ready():
    return {"ok": True, "ready": True}
