from fastapi import APIRouter, HTTPException
from typing import Any, Dict

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Advertised actions
ACTIONS = [
    {
        "id": "options.pick",
        "op": "options.pick",
        "title": "Pick closest-to-ATM options",
        "description": "Returns N near-ATM contracts for a ticker/side/horizon.",
        "args_schema": {
            "type": "object",
            "title": "OptionsPickArgs",
            "required": ["symbol", "side"],
            "properties": {
                "symbol": {"title": "Symbol", "type": "string"},
                "side": {
                    "title": "Side", "type": "string",
                    "enum": ["long_call", "long_put", "short_call", "short_put"]
                },
                "horizon": {
                    "title": "Horizon", "type": "string",
                    "enum": ["intra","day","week"], "default": "intra"
                },
                "n": {"title": "N", "type": "integer", "minimum": 1, "maximum": 10, "default": 5}
            }
        },
        "stable": True,
    },
    {
        "id": "diag.health",
        "op": "diag.health",
        "title": "Server health",
        "description": "Lightweight readiness/health via assistant layer.",
        "args_schema": {"type": "object", "properties": {}},
        "stable": True,
    },
]

@router.get("/actions")
def assistant_actions() -> Dict[str, Any]:
    return {"ok": True, "actions": ACTIONS}

# Try to locate a real options picker in your codebase.
_pick_impl = None
try:
    # Adjust this import if your picker lives elsewhere.
    # e.g., from app.services.options_picker import pick as _pick_impl
    from app.routers import options as _opts  # type: ignore
    _pick_impl = getattr(_opts, "pick", None)
except Exception:
    _pick_impl = None

@router.post("/exec")
async def assistant_exec(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic exec: { "op": "<op>", "args": {...} }
    Supports:
      - diag.health
      - options.pick  (delegates to your real implementation if present)
    """
    op = (payload or {}).get("op")
    args = (payload or {}).get("args") or {}

    if not op:
        raise HTTPException(status_code=400, detail={"ok": False, "error": "missing_op"})

    if op == "diag.health":
        return {"ok": True, "status": "ok", "via": "assistant_bridge"}

    if op == "options.pick":
        if _pick_impl is None:
            raise HTTPException(
                status_code=501,
                detail={"ok": False, "error": "not_implemented", "hint": "Wire a real options.pick and expose it here."},
            )
        try:
            res = _pick_impl(**args) if hasattr(_pick_impl, "__call__") else None
            # handle async
            if hasattr(res, "__await__"):
                res = await res
            return res if isinstance(res, dict) else {"ok": True, "result": res}
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=500, detail={"ok": False, "error": "options_pick_failed", "message": str(e)})

    raise HTTPException(status_code=400, detail={"ok": False, "error": "unknown_op", "op": op})
