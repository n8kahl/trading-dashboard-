from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, Query, Request
from starlette.responses import StreamingResponse

from app.services.llm import chatdata_narrative
from app.services.narrative import build_situation
from app.repositories.narratives import save_guidance
from app.core.settings import settings
from app.rate_limit import allow as rl_allow


router = APIRouter(prefix="/coach", tags=["coach"])


def _sig_delta(prev: Optional[Dict[str, Any]], cur: Dict[str, Any]) -> bool:
    """Return True if there is a significant delta between payloads.

    Heuristics:
      - Price moved by >= SSE_MIN_PRICE_DELTA_PCT
      - Risk breach flags changed or concurrent count changed
      - Guidance action/band changed OR confidence moved by >= SSE_MIN_CONFIDENCE_DELTA
    """
    if not prev:
        return True
    try:
        p_prev = (prev.get("situation") or {}).get("price")
        p_cur = (cur.get("situation") or {}).get("price")
        if isinstance(p_prev, (int, float)) and isinstance(p_cur, (int, float)) and p_prev and p_cur:
            if abs(p_cur - p_prev) / max(1e-9, abs(p_prev)) >= max(0.0, settings.SSE_MIN_PRICE_DELTA_PCT):
                return True
        r_prev = (prev.get("situation") or {}).get("risk") or {}
        r_cur = (cur.get("situation") or {}).get("risk") or {}
        if any((r_prev.get(k) != r_cur.get(k)) for k in ("breach_daily_r", "breach_concurrent", "concurrent")):
            return True
        g_prev = prev.get("guidance") or {}
        g_cur = cur.get("guidance") or {}
        if (g_prev.get("action") != g_cur.get("action")) or (g_prev.get("band") != g_cur.get("band")):
            return True
        c_prev = g_prev.get("confidence")
        c_cur = g_cur.get("confidence")
        if isinstance(c_prev, (int, float)) and isinstance(c_cur, (int, float)):
            if abs(float(c_cur) - float(c_prev)) >= max(0, settings.SSE_MIN_CONFIDENCE_DELTA):
                return True
    except Exception:
        return True
    return False


async def _event_stream(symbol: str, position_id: Optional[str]) -> AsyncGenerator[bytes, None]:
    last_payload: Optional[Dict[str, Any]] = None
    last_emit_ms: int = 0
    while True:
        try:
            situation = await build_situation(symbol, position_id)
            guidance = await chatdata_narrative(situation)
            payload: Dict[str, Any] = {
                "ok": True,
                "symbol": symbol.upper(),
                "t_ms": situation.get("t_ms"),
                "situation": situation,
                "guidance": guidance,
            }
            # best-effort persistence (non-fatal on failure)
            try:
                save_guidance(
                    t_ms=int(situation.get("t_ms") or 0),
                    symbol=symbol,
                    guidance=guidance if isinstance(guidance, dict) else {"data": guidance},
                    horizon=(guidance or {}).get("horizon") if isinstance(guidance, dict) else None,
                    band=(guidance or {}).get("band") if isinstance(guidance, dict) else None,
                    position_id=position_id,
                )
            except Exception:
                pass

            # Backpressure: significant-delta gating
            now_ms = int(time.time() * 1000)
            should_emit = _sig_delta(last_payload, {"situation": situation, "guidance": guidance})
            if should_emit:
                last_payload = {"situation": situation, "guidance": guidance}
                last_emit_ms = now_ms
                data = json.dumps(payload, separators=(",", ":"))
                yield f"data: {data}\n\n".encode("utf-8")
            else:
                # Heartbeat comment every SSE_HEARTBEAT_SEC to keep connection alive
                if (now_ms - last_emit_ms) >= max(3_000, settings.SSE_HEARTBEAT_SEC * 1000):
                    last_emit_ms = now_ms
                    yield b":\n\n"
        except asyncio.CancelledError:  # client disconnected
            break
        except Exception as e:
            err = json.dumps({"ok": False, "error": str(e)})
            yield f"data: {err}\n\n".encode("utf-8")
        await asyncio.sleep(3.0)


@router.get("/stream")
async def coach_stream(
    request: Request,
    symbol: str = Query(..., min_length=1),
    position_id: Optional[str] = Query(None),
) -> StreamingResponse:
    if not symbol or not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required")
    # Rate limit new stream connections per IP
    ip = request.client.host if request.client else "unknown"
    if not rl_allow(f"{ip}:coach_stream", settings.RATE_LIMIT_COACH_PER_MIN, 60):
        raise HTTPException(status_code=429, detail="Too Many Requests")
    generator = _event_stream(symbol.strip().upper(), position_id)
    return StreamingResponse(generator, media_type="text/event-stream")
