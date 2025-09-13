from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

# Import the running FastAPI app so httpx can call it in-process
try:
    from app.main import app as _app
except Exception as e:
    _app = None

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Map assistant ops to your existing internal routes
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
    return {"ok": True, "actions": [{"op": k} for k in sorted(OP_MAP.keys())]}

@router.post("/exec")
async def assistant_exec(body: ExecBody):
    if body.op not in OP_MAP:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "detail": body.op, "op": body.op})

    if _app is None:
        raise HTTPException(status_code=500, detail={"ok": False, "error": "app_not_loaded"})

    spec = OP_MAP[body.op]
    method, path = spec["method"], spec["path"]

    # In-process ASGI call: no network, no PORT, no 502s
    async with httpx.AsyncClient(app=_app, base_url="http://internal") as client:
        if method == "GET":
            r = await client.get(path, params=(body.args or {}))
        elif method == "POST":
            r = await client.post(path, json=(body.args or {}))
        elif method == "DELETE":
            r = await client.delete(path, json=(body.args or {}))
        elif method == "PATCH":
            r = await client.patch(path, json=(body.args or {}))
        elif method == "PUT":
            r = await client.put(path, json=(body.args or {}))
        else:
            raise HTTPException(status_code=400, detail={"ok": False, "error": "bad_method", "detail": method})

    ct = (r.headers.get("content-type") or "")
    if "application/json" in ct:
        return r.json()
    return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text[:2000]}
