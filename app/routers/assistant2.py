from typing import Any, Dict, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import os, httpx

router = APIRouter(prefix="/assistant2", tags=["assistant2"])

class OptionsPickArgs(BaseModel):
    symbol: str = Field(..., description="Ticker, e.g. SPY")
    side: str = Field(..., description="long_call|long_put|short_call|short_put")
    horizon: Optional[str] = Field("intra", description="intra|day|week")
    n: Optional[int] = Field(5, ge=1, le=10)

class ExecBody(BaseModel):
    op: str
    args: Optional[Dict[str, Any]] = None
    symbol: Optional[str] = None
    side: Optional[str] = None
    horizon: Optional[str] = None
    n: Optional[int] = None

_ACTIONS = [{
    "op": "options.pick",
    "title": "Pick closest-to-ATM options (delayed)",
    "description": "Return N contracts nearest to ATM for a ticker/side/horizon.",
    "args_schema": OptionsPickArgs.model_json_schema(),
    "stable": True,
    "id": "options.pick",
}]

@router.get("/actions", summary="List assistant operations")
async def assistant_actions() -> Dict[str, Any]:
    return {"ok": True, "version": "__ASSISTANT2__", "actions": _ACTIONS}

@router.post("/exec", summary="Execute an assistant operation")
async def assistant_exec(body: ExecBody) -> Dict[str, Any]:
    args: Dict[str, Any] = dict(body.args or {})
    for k in ("symbol", "side", "horizon", "n"):
        v = getattr(body, k, None)
        if v is not None and k not in args:
            args[k] = v

    if body.op != "options.pick":
        raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "op": body.op})

    # Validate args
    OptionsPickArgs(**args)

    port = os.getenv("PORT", "8000")
    url = f"http://127.0.0.1:{port}/api/v1/options/pick"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(url, json=args)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"ok": False, "error": "upstream_unreachable", "detail": str(e)})

    if resp.status_code >= 400:
        try:
            payload = resp.json()
        except Exception:
            payload = {"raw": resp.text}
        raise HTTPException(status_code=resp.status_code, detail=payload)

    try:
        return resp.json()
    except Exception:
        return {"ok": False, "error": "bad_json", "raw": resp.text}
