from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

OP_MAP = {
    "stream.track": {"method": "POST", "path": "/api/v1/stream/track"},
    "stream.state": {"method": "GET",  "path": "/api/v1/stream/quotes"},
    "diag.health":  {"method": "GET",  "path": "/api/v1/diag/health"},
}

class ExecBody(BaseModel):
    op: str
    args: dict

@router.get("/actions")
async def assistant_actions():
    return {"ops": sorted(OP_MAP.keys())}

@router.post("/exec")
async def assistant_exec(body: ExecBody):
    spec = OP_MAP.get(body.op)
    if not spec:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "detail": body.op, "op": body.op})

    method, url = spec["method"], spec["path"]

    async with httpx.AsyncClient(timeout=10.0) as client:
        if method == "GET":
            r = await client.get(url, params=body.args or {})
        else:
            r = await client.request(method, url, json=body.args or {})

    if "application/json" in (r.headers.get("content-type") or ""):
        return r.json()
    return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text[:500]}
