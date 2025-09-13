from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

OP_MAP = {
    "stream.track":    {"method": "POST", "path": "/api/v1/stream/track"},
    "stream.state":    {"method": "GET",  "path": "/api/v1/stream/quotes"},
    "stream.snapshot": {"method": "GET",  "path": "/api/v1/stream/snapshot"},
    "diag.health":     {"method": "GET",  "path": "/api/v1/diag/health"},
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

    method = spec["method"].upper()
    url    = spec["path"]  # absolute /api/v1/... path

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                r = await client.get(url, params=(body.args or {}))
            elif method == "POST":
                r = await client.post(url, json=(body.args or {}))
            elif method == "DELETE":
                r = await client.delete(url, json=(body.args or {}))
            elif method == "PATCH":
                r = await client.patch(url, json=(body.args or {}))
            elif method == "PUT":
                r = await client.put(url, json=(body.args or {}))
            else:
                raise HTTPException(status_code=400, detail={"ok": False, "error": "bad_method", "detail": method})
        if "application/json" in (r.headers.get("content-type","")):
            return r.json()
        return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text[:2000]}
    except httpx.RequestError as e:
        raise HTTPException(status_code=502, detail={"ok": False, "error": "upstream_error", "detail": str(e)})
