from __future__ import annotations

import os
from typing import List, Optional

from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter(prefix="/diag", tags=["diag"])


@router.get("/env")
async def env(name: str = Query(..., description="Env var name")):
    val = os.getenv(name)
    return {"name": name, "exists": val is not None, "preview": (val[:4] + "…" if val else None)}


class FMPTestReq(BaseModel):
    watchlist: Optional[List[str]] = None  # if omitted, we'll fetch all from FMP window


@router.post("/test-fmp")
async def test_fmp(req: FMPTestReq):
    """
    Run the provider AND also hit FMP directly to surface status/body for debugging.
    """
    out = {"ok": True}
    # 1) Provider result
    try:
        from app.services.earnings_provider_fmp import fetch_earnings_ahead_fmp

        out["provider"] = await fetch_earnings_ahead_fmp(req.watchlist or [])
    except Exception as e:
        out["provider_error"] = f"import/provider error: {e}"

    # 2) Raw HTTP check (no symbol filter) for next 7 days
    import os
    from datetime import datetime, timedelta, timezone

    import httpx

    FMP_KEY = os.getenv("FMP_API_KEY", "")
    today = datetime.now(timezone.utc).date().strftime("%Y-%m-%d")
    end = (datetime.now(timezone.utc).date() + timedelta(days=7)).strftime("%Y-%m-%d")
    url = "https://financialmodelingprep.com/api/v3/earning_calendar"
    params = {"from": today, "to": end, "apikey": FMP_KEY}
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            r = await client.get(url, params=params)
            out["http_status"] = r.status_code
            try:
                js = r.json()
                out["http_json_preview"] = js[:3] if isinstance(js, list) else js
            except Exception:
                out["http_text_preview"] = r.text[:400] if r.text else None
    except Exception as e:
        out["http_error"] = str(e)
    return out


class TETestReq(BaseModel):
    country: str = "united states"
    severity: Optional[List[str]] = ["high", "medium"]


@router.post("/test-te")
async def test_te(req: TETestReq):
    try:
        from app.services.macro_provider import fetch_week_ahead_macro

        data = await fetch_week_ahead_macro(country=req.country, severity=req.severity)
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class YHTestReq(BaseModel):
    watchlist: Optional[List[str]] = None


@router.post("/test-yahoo")
async def test_yahoo(req: YHTestReq):
    try:
        from app.services.earnings_provider_yahoo import fetch_earnings_ahead_yahoo

        data = await fetch_earnings_ahead_yahoo(req.watchlist or ["AAPL", "NVDA", "MSFT"])
        return {"ok": True, "data": data}
    except Exception as e:
        return {"ok": False, "error": str(e)}


class YHRawReq(BaseModel):
    symbol: str


@router.post("/test-yahoo-raw")
async def test_yahoo_raw(req: YHRawReq):
    # Return both parsed and raw previews for a single symbol
    try:
        from app.services.earnings_provider_yahoo import _fetch_next_earnings

        parsed = await _fetch_next_earnings(req.symbol)
    except Exception as e:
        parsed = {"error": f"parse error: {e}"}

    import httpx

    url = f"https://query2.finance.yahoo.com/v10/finance/quoteSummary/{req.symbol}"
    params = {"modules": "calendarEvents"}
    headers = {"User-Agent": "Mozilla/5.0", "Accept": "application/json"}
    try:
        async with httpx.AsyncClient(timeout=15, headers=headers) as client:
            r = await client.get(url, params=params)
            status = r.status_code
            try:
                js = r.json()
                raw_preview = js.get("quoteSummary", {}).get("result", [{}])[0].get("calendarEvents", {})
            except Exception:
                raw_preview = r.text[:500]
    except Exception as e:
        status = "error"
        raw_preview = str(e)

    return {"symbol": req.symbol, "parsed": parsed, "http_status": status, "raw_preview": raw_preview}
