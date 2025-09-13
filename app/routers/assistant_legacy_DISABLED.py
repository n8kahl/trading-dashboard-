from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError

# Import your actions module (already has your registry/overlay)
from app.assistant import actions as actions_mod

router = APIRouter(prefix="/assistant", tags=["assistant"])


class ExecBody(BaseModel):
    op: str = Field(..., description="Operation id (e.g. options.pick)")
    args: Dict[str, Any] | None = None
    model_config = {"extra": "allow"}  # accept top-level kwargs too


def _fold_args(payload: Dict[str, Any]) -> Dict[str, Any]:
    op = payload.get("op")
    args = payload.get("args") or {}
    for k, v in payload.items():
        if k not in ("op", "args") and k not in args:
            args[k] = v
    return {"op": op, "args": args}


@router.get("/actions")
def assistant_actions():
    try:
        data = actions_mod.list_actions()
        if isinstance(data, dict) and "actions" in data:
            return {"ok": True, **data}
        # fallback if list is returned
        if isinstance(data, list):
            return {"ok": True, "actions": data}
        return {"ok": True, "actions": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail={"ok": False, "error": "actions_list_error", "detail": str(e)})


@router.post("/exec")
async def assistant_exec(req: Request):
    try:
        raw = await req.json()
        folded = _fold_args(raw if isinstance(raw, dict) else {})
        body = ExecBody(**folded)
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "validation_error", "detail": ve.errors()})
    except Exception as e:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "bad_request", "detail": str(e)})

    try:
        result = await actions_mod.execute_action(body.op, body.args or {})
    except ValidationError as ve:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "validation_error", "detail": ve.errors()})
    except Exception as e:
        raise HTTPException(status_code=500, detail={"ok": False, "error": "exec_error", "detail": str(e)})

    if isinstance(result, dict) and result.get("ok") is False and result.get("error") == "validation_error":
        raise HTTPException(status_code=400, detail=result)
    return result
