from fastapi import APIRouter, HTTPException
from .common import ok
from app.services.scoring_engine import score_confluence

router = APIRouter(prefix="/", tags=["analyze"])

@router.post("/analyze")
async def analyze(body: dict):
    strategy_id = body.get("strategy_id")
    context = body.get("context")
    if not strategy_id or not isinstance(context, dict):
        raise HTTPException(400, "Body must include 'strategy_id' and 'context' object")
    result = score_confluence(context, strategy_id)
    return ok(result)
