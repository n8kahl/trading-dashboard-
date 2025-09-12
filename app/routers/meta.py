from fastapi import APIRouter
from fastapi.routing import APIRoute
from .common import ok
from typing import List

router = APIRouter(tags=["meta"])

@router.get("/version")
async def version():
    try:
        with open("app/VERSION.txt","r") as f:
            v = f.read().strip()
    except Exception:
        v = "unknown"
    return ok({"git": v})

@router.get("/router-status")
async def router_status():
    # Return a compact list of mounted paths so we can debug mounts without logs
    from fastapi import FastAPI
    import sys
    app: FastAPI = sys.modules.get("app.main").app  # type: ignore
    paths: List[str] = []
    for r in app.router.routes:
        if isinstance(r, APIRoute):
            paths.append(r.path)
    paths.sort()
    return ok({"paths": paths})
