from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from app.services import store
from app.services.compose import build_context_from_polygon
from app.services.plan_engine import build_plan
from app.services.risk_engine import assess_risk
from app.services.scoring_engine import score_all, score_confluence

from .common import ok

router = APIRouter(prefix="/", tags=["compose"])


@router.post("/compose-and-analyze")
async def compose_and_analyze(body: dict):
    symbol = (body.get("symbol") or "").upper()
    the_day = body.get("date")
    strategy_id = body.get("strategy_id") or "auto"
    overrides = body.get("overrides", {}) or {}

    if not symbol:
        raise HTTPException(400, "symbol is required")
    if not the_day:
        the_day = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # 1) Build context
    ctx = await build_context_from_polygon(symbol, the_day)

    # If we failed to build a context, return diagnostics (no logging)
    if isinstance(ctx, dict) and ctx.get("_error"):
        warnings = ["Data fetch failed; see context_error._diag for details."]
        return ok(
            {
                "input": {"symbol": symbol, "date": the_day, "strategy_id": strategy_id},
                "context_error": ctx,
                "warnings": warnings,
            }
        )

    # 2) Merge optional overrides
    ctx.update({k: v for k, v in (overrides or {}).items() if v is not None})

    # 3) Non-realtime warning (daily fallback)
    warnings = []
    if not ctx.get("realtime", False):
        warnings.append(
            "Using daily fallback (not real-time). VWAP and intraday signals may be limited. "
            "For real-time intraday analysis, enable minute bars on your data plan."
        )

    # 4) Strategy selection
    leaderboard = None
    chosen_id = strategy_id
    if strategy_id.lower() == "auto":
        leaderboard = score_all(ctx)
        chosen_id = leaderboard[0]["strategy_id"] if leaderboard else "vwap_bounce"

    # 5) Score using chosen strategy
    analysis = score_confluence(ctx, chosen_id)

    # 6) Build plan
    plan = build_plan(chosen_id, ctx)

    # 7) Assess risk
    risk = assess_risk(chosen_id, ctx, analysis, plan)

    # 8) Auto-log analysis
    analysis_id = store.log_analysis(
        symbol=symbol, date=the_day, strategy_id=chosen_id, context=ctx, analysis=analysis, warnings=warnings
    )

    # 9) Return with leaderboard if auto
    payload = {
        "input": {"symbol": symbol, "date": the_day, "strategy_id": chosen_id},
        "analysis_id": analysis_id,
        "context": ctx,
        "analysis": analysis,
        "plan": plan,
        "risk": risk,
        "warnings": warnings,
    }
    if leaderboard is not None:
        payload["leaderboard"] = leaderboard
        payload["chosen_strategy"] = chosen_id
    return ok(payload)
