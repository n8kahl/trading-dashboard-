from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import httpx

# In-process ASGI call to avoid network/PORT issues
from app.main import app as _app

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Only non-stream ops are allowed here.
# diag.health is universal. options.pick is optional (we’ll probe it at runtime).
SAFE_OPS = {
    "diag.health": {"method": "GET", "path": "/api/v1/diag/health"},
    # We'll add "options.pick" dynamically if the endpoint exists
}

class ExecBody(BaseModel):
    op: str
    args: dict

async def _probe_options_pick():
    """Check if /api/v1/options/pick exists; cache result in SAFE_OPS."""
    if "options.pick" in SAFE_OPS:
        return True
    try:
        async with httpx.AsyncClient(app=_app, base_url="http://internal", timeout=4.0) as client:
            # HEAD may not be implemented; try GET without args and accept 400/405 as 'it exists'
            r = await client.get("/api/v1/options/pick")
            if r.status_code in (200, 400, 405, 422):
                SAFE_OPS["options.pick"] = {"method":"POST","path":"/api/v1/options/pick"}
                return True
    except Exception:
        pass
    return False

@router.get("/actions")
async def assistant_actions():
    ops = [{"op": "diag.health"}]
    if await _probe_options_pick():
        ops.append({"op": "options.pick"})
    # No streaming ops; intentionally stripped
    return {"ok": True, "actions": ops}

@router.post("/exec")
async def assistant_exec(body: ExecBody):
    # Block any stream.* op explicitly
    if body.op.startswith("stream."):
        raise HTTPException(status_code=400, detail={"ok": False, "error": "disabled_op", "detail": "streaming disabled", "op": body.op})

    if body.op == "options.pick":
        ok = await _probe_options_pick()
        if not ok:
            raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "detail": body.op, "op": body.op})

    spec = SAFE_OPS.get(body.op)
    if not spec:
        # Only diag.health and maybe options.pick are supported
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "detail": body.op, "op": body.op})

    method, path = spec["method"], spec["path"]
    async with httpx.AsyncClient(app=_app, base_url="http://internal", timeout=15.0) as client:
        if method == "GET":
            r = await client.get(path, params=(body.args or {}))
        else:
            r = await client.request(method, path, json=(body.args or {}))

    ct = (r.headers.get("content-type") or "")
    if "application/json" in ct:
        return r.json()
    return {"ok": r.status_code < 400, "status": r.status_code, "text": r.text[:2000]}
