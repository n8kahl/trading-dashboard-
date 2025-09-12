from fastapi import APIRouter
from starlette.responses import JSONResponse

from app.services import alerts_store

router = APIRouter(prefix="/diag/db", tags=["diag-db"])


@router.post("/init")
def db_init():
    try:
        alerts_store.init()
        return {"ok": True, "init": "done"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/ping")
def db_ping():
    try:
        alerts_store.list_active()
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.get("/count")
def db_count():
    try:
        n = len(alerts_store.list_active())
        return {"ok": True, "alerts": n}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)


@router.post("/insert-demo")
def db_insert_demo():
    try:
        _id = alerts_store.add("DEMO", "day", {"type": "price_above", "value": 123}, None)
        return {"ok": True, "id": _id}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
