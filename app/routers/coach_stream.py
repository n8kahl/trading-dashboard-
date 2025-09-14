from __future__ import annotations

import asyncio
import json
from typing import Any, AsyncGenerator, Dict, Optional

from fastapi import APIRouter, HTTPException, Query
from starlette.responses import StreamingResponse

from app.services.llm import chatdata_narrative
from app.services.narrative import build_situation
from app.repositories.narratives import save_guidance


router = APIRouter(prefix="/coach", tags=["coach"])


async def _event_stream(symbol: str, position_id: Optional[str]) -> AsyncGenerator[bytes, None]:
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

            data = json.dumps(payload, separators=(",", ":"))
            yield f"data: {data}\n\n".encode("utf-8")
        except asyncio.CancelledError:  # client disconnected
            break
        except Exception as e:
            err = json.dumps({"ok": False, "error": str(e)})
            yield f"data: {err}\n\n".encode("utf-8")
        await asyncio.sleep(3.0)


@router.get("/stream")
async def coach_stream(symbol: str = Query(..., min_length=1), position_id: Optional[str] = Query(None)) -> StreamingResponse:
    if not symbol or not symbol.strip():
        raise HTTPException(status_code=400, detail="symbol is required")
    generator = _event_stream(symbol.strip().upper(), position_id)
    return StreamingResponse(generator, media_type="text/event-stream")

