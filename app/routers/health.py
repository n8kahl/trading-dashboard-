from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz")
def healthz():
    return {"status": "ok"}


@router.get("/router-status")
def router_status():
    # kept simple to avoid importing app state at import time
    return {"status": "ok"}
