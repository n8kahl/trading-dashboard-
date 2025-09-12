from typing import Any, Dict, Optional, Literal
import os, httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/assistant", tags=["assistant"])

class ExecBody(BaseModel):
    op: str
    args: Optional[Dict[str, Any]] = {}

class OptionsPickArgs(BaseModel):
    symbol: str
    side: Literal["long_call", "long_put", "short_call", "short_put"]
    horizon: Literal["intra","day","week"] = "intra"
    n: int = Field(default=5, ge=1, le=10)

@router.get("/actions")
def assistant_actions():
    return {"ok": True, "actions": [{
        "op": "options.pick",
        "title": "Pick closest-to-ATM options (stub)",
        "description": "Returns N near-ATM contracts for a ticker/side/horizon.",
        "args_schema": OptionsPickArgs.model_json_schema(),
        "stable": True,
        "id": "options.pick"
    }]}

def _local_base() -> str:
    # When running inside the same app container, call our own server on PORT
    return f"http://127.0.0.1:{os.getenv('PORT','8000')}"

async def _proxy_options_pick(payload: Dict[str, Any]) -> Dict[str, Any]:
    url = _local_base() + "/api/v1/options/pick"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.post(url, json=payload)
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=r.text)
    return r.json()


EXEC_HANDLERS = {
    "options.pick": _proxy_options_pick,
}

@router.post("/exec")
async def assistant_exec(body: ExecBody):
    merged_args = {**(body.args or {}), **{k: v for k, v in body.model_dump().items() if k not in ("op","args") and v is not None}}

    handler = EXEC_HANDLERS.get(body.op)
    if handler is None:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "op": body.op})
    return await handler(merged_args)
