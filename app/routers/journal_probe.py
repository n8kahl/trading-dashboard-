from fastapi import APIRouter
from .common import ok

router = APIRouter(prefix="/journal", tags=["journal-probe"])

@router.get("/ping")
async def ping():
    return ok({"hello":"world"})
