from typing import Any, Dict, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.assistant.actions import execute_action, list_actions

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])


class ExecBody(BaseModel):
    op: str
    args: Optional[Dict[str, Any]] = None


# allow tests to monkeypatch handlers
EXEC_HANDLERS: Dict[str, Any] = {}


@router.get("/actions")
async def assistant_actions() -> Dict[str, Any]:
    return list_actions()


@router.post("/exec")
async def assistant_exec(body: ExecBody) -> Dict[str, Any]:
    args = body.args or {}
    handler = EXEC_HANDLERS.get(body.op)
    if handler:
        return await handler(args)
    result = await execute_action(body.op, args)
    if not result.get("ok"):
        err = dict(result)
        if err.get("error") == "unknown_op":
            err["op"] = body.op
        raise HTTPException(status_code=400, detail=err)
    return result
