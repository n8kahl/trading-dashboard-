from fastapi import APIRouter
from pydantic import BaseModel

from app.core.failopen import fail_open

router = APIRouter(prefix="/alerts", tags=["alerts"])


def _alerts_list_fallback():
    return {"status": "ok", "data": {"alerts": []}}


@router.get("/list")
@fail_open(_alerts_list_fallback)
def alerts_list():
    # TODO: load from DB; fallback is empty
    return {"status": "ok", "data": {"alerts": []}}


def _alerts_set_fallback():
    return {"ok": True, "note": "fallback set (not persisted)"}


class AlertBody(BaseModel):
    # keep it permissive; tighten later if you want
    symbol: str | None = None
    level: float | None = None
    note: str | None = None


@router.post("/set")
@fail_open(_alerts_set_fallback)
def alerts_set(body: AlertBody):
    # TODO: persist to DB; for now, echo success
    return {"ok": True}
