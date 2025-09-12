from fastapi import APIRouter
from starlette.responses import JSONResponse
from sqlalchemy import text
from app.db import init_db, db_session
from app.models import Alert

router = APIRouter(prefix="/diag/db", tags=["diag-db"])

@router.post("/init")
def db_init():
    init_db()
    return {"ok": True, "init": "done"}

@router.get("/ping")
def db_ping():
    try:
        with db_session() as db:
            if db is None:
                return JSONResponse({"ok": False, "error": "DB not configured"}, status_code=503)
            db.execute(text("SELECT 1"))
            return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@router.get("/count")
def db_count():
    try:
        with db_session() as db:
            if db is None:
                return JSONResponse({"ok": False, "error": "DB not configured"}, status_code=503)
            n = db.query(Alert).count()
            return {"ok": True, "alerts": n}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)

@router.post("/insert-demo")
def db_insert_demo():
    try:
        with db_session() as db:
            if db is None:
                return JSONResponse({"ok": False, "error": "DB not configured"}, status_code=503)
            a = Alert(
                symbol="DEMO",
                timeframe="day",
                condition={"type": "price_above", "value": 123},
                is_active=True,
            )
            db.add(a)
            db.flush()
            return {"ok": True, "id": a.id}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, status_code=500)
