import sys
import traceback

from fastapi import APIRouter, HTTPException

from .common import ok

router = APIRouter(prefix="/journal/debug", tags=["journal-debug"])


@router.post("/migrate")
async def migrate():
    try:
        from app.services import store

        store.migrate()
        return ok({"migrated": True})
    except Exception as e:
        traceback.print_exc(file=sys.stderr)
        raise HTTPException(500, f"migrate error: {e}")
