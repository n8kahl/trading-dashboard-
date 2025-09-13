from typing import Any, Dict

from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.services.stream import POLYGON_API_KEY, STREAM

router = from pydantic import BaseModel

APIRouter(prefix="/market/stream", tags=["market-stream"])


class StreamStart(BaseModel):
    symbols: list[str]

@router.post('/start')
async def start(body: Dict[str, Any]):
    if not POLYGON_API_KEY:
        return JSONResponse({"status": "error", "error": "POLYGON_API_KEY missing in server env"}, status_code=400)
    symbols = body.get("symbols") or []
    if not isinstance(symbols, list) or not symbols:
        return JSONResponse({"status": "error", "error": 'Provide symbols: ["SPY","QQQ","I:SPX"]'}, status_code=400)
    out = await STREAM.start([str(s).upper() for s in symbols])
    if not out.get("started"):
        return JSONResponse({"status": "error", "error": out.get("error", "failed")}, status_code=400)
    return JSONResponse({"status": "ok", "data": out})


@router.get("/status")
async def status():
    out = await STREAM.status()
    return JSONResponse({"status": "ok", "data": out})


@router.get("/snapshot")
async def snapshot(n: int = 20):
    out = await STREAM.snapshot(n=n)
    return JSONResponse({"status": "ok", "data": out})


@router.post("/stop")
async def stop():
    out = await STREAM.stop()
    return JSONResponse({"status": "ok", "data": out})
