from fastapi import APIRouter

from app.services.levels import get_intraday_vwap, get_opening_range, get_prev_day_hl

from .common import ok

router = APIRouter(prefix="/", tags=["levels"])


@router.get("/levels/{symbol}")
async def levels(symbol: str, or_minutes: int = 5):
    prev = await get_prev_day_hl(symbol)
    opening = await get_opening_range(symbol, minutes=or_minutes)
    vwap = await get_intraday_vwap(symbol)
    # Always return JSON; allow nulls when market closed or API restricted
    return ok({"symbol": symbol.upper(), "prev_day": prev, "opening_range": opening, "intraday_vwap": vwap})
