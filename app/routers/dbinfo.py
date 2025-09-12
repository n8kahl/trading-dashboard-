from fastapi import APIRouter
from .common import ok
import os

router = APIRouter(prefix="/journal/debug", tags=["journal-debug"])

@router.get("/db-kind")
async def db_kind():
    pg = os.getenv("DATABASE_URL")
    return ok({"postgres": bool(pg)})
