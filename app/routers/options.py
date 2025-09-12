from __future__ import annotations
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Dict, Any, AsyncIterator
import os, math, asyncio, datetime as dt
import logging
from app.integrations.tradier import TradierClient
import httpx

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/options", tags=["options"])

# ---------- Models ----------
class OptionsPickRequest(BaseModel):
    symbol: str
    side: Literal["long_call","long_put","short_call","short_put"]
    horizon: Literal["intra","day","week"] = "intra"
    n: int = Field(default=5, ge=1, le=10)
    max_dte: Optional[int] = None
    prefer: Optional[Literal["tradier","auto"]] = "auto"  # NEW: force Tradier if desired

class OptionContract(BaseModel):
    symbol: str
    expiration: str
    strike: float
    option_type: Literal["call","put"]
    delta: Optional[float] = None
    bid: Optional[float] = None
    ask: Optional[float] = None
    mark: Optional[float] = None
    spread_pct: Optional[float] = None
    open_interest: Optional[int] = None
    volume: Optional[int] = None
    dte: Optional[int] = None
    score: Optional[float] = None

class OptionsPickResponse(BaseModel):
    ok: bool
    env: str
    note: Optional[str] = None
    count_considered: int
    picks: List[OptionContract]
    source: Optional[str] = None  # NEW: "tradier" or "polygon"

# ---------- Config ----------
TRADIER_ACCESS_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN", "").strip()
POLYGON_KEY = os.getenv("POLYGON_API_KEY", "").strip()
ENV_NOTE = "delayed via Tradier Sandbox; Polygon fallback only if Tradier empty/unavailable"


async def get_tradier_client() -> AsyncIterator[TradierClient]:
    """FastAPI dependency providing a Tradier client per request."""
    client = TradierClient()
    try:
        yield client
    finally:
        await client.close()

# ---------- Helpers ----------
def _today_utc() -> dt.date:
    return dt.datetime.utcnow().date()

def _dte(expiration: str) -> Optional[int]:
    try:
        d = dt.datetime.strptime(expiration, "%Y-%m-%d").date()
        return (d - _today_utc()).days
    except Exception:
        return None

def _safe_float(x: Any) -> Optional[float]:
    try:
        f = float(x)
        if math.isfinite(f):
            return f
    except Exception:
        logger.exception("failed to parse float")
    return None

def _safe_int(x: Any) -> Optional[int]:
    try:
        return int(x)
    except Exception:
        return None

def _calc_mark(bid: Optional[float], ask: Optional[float], last: Optional[float]=None) -> Optional[float]:
    if bid is not None and ask is not None:
        return round((bid + ask) / 2, 4)
    return last

def _calc_spread_pct(bid: Optional[float], ask: Optional[float]) -> Optional[float]:
    if bid is not None and ask is not None and ask > 0:
        return round((ask - bid) / ask, 6)
    return None

def _horizon_dte_cap(horizon: str, max_dte_param: Optional[int]) -> int:
    if max_dte_param is not None:
        return max_dte_param
    return {"intra":2, "day":3, "week":7}.get(horizon, 5)

def _wanted_type(side: str) -> str:
    return "call" if side.endswith("call") else "put"


# ---------- Tradier (primary) ----------
async def _tradier_json(client: TradierClient, path: str, params: Dict[str, Any]) -> Dict[str, Any]:
    s = await client._session()
    r = await s.get(path, params=params, timeout=20.0)
    if r.status_code >= 400:
        raise HTTPException(status_code=r.status_code, detail=f"tradier_http_{r.status_code}: {r.text}")
    try:
        return r.json()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"tradier_json_error: {e}")

async def _tradier_quote(client: TradierClient, symbol: str) -> Optional[float]:
    data = await client.get_quotes([symbol])
    q = data.get(symbol) or {}
    return _safe_float(q.get("last")) or _safe_float(q.get("close"))

async def _tradier_expirations(client: TradierClient, symbol: str) -> List[str]:
    data = await _tradier_json(client, "/markets/options/expirations", {"symbol": symbol})
    exps = (data or {}).get("expirations", {}).get("date")
    if not exps:
        return []
    return [str(x) for x in (exps if isinstance(exps, list) else [exps])]

async def _tradier_chain(client: TradierClient, symbol: str, expiration: str, opt_type: Optional[str]) -> List[Dict[str, Any]]:
    params = {"symbol": symbol, "expiration": expiration, "greeks": "true"}
    if opt_type in ("call", "put"):
        params["type"] = opt_type
    data = await _tradier_json(client, "/markets/options/chains", params)
    items = (data or {}).get("options", {}).get("option")
    if not items:
        return []
    return list(items if isinstance(items, list) else [items])
# ---------- Polygon (fallback) ----------
async def _polygon_chain(symbol: str, max_count: int = 500) -> List[Dict[str, Any]]:
    if not POLYGON_KEY:
        return []
    url = "https://api.polygon.io/v3/reference/options/contracts"
    params = {"underlying_ticker": symbol.upper(), "limit": max_count, "apiKey": POLYGON_KEY}
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, params=params)
    if r.status_code >= 400:
        return []
    try:
        j = r.json()
    except Exception:
        return []
    results = j.get("results") or []
    out = []
    for it in results:
        out.append({
            "symbol": it.get("ticker") or it.get("symbol"),
            "expiration_date": it.get("expiration_date"),
            "strike": _safe_float(it.get("strike_price")),
            "option_type": it.get("contract_type"),
            "bid": None, "ask": None, "last": None,
            "volume": None, "open_interest": None
        })
    return out

# ---------- Picker ----------
async def _pick_from_tradier(client: TradierClient, symbol: str, side: str, horizon: str, n: int) -> OptionsPickResponse:
    opt_type = "call" if side.endswith("call") else "put"
    dte_cap = _horizon_dte_cap(horizon, None)
    tc = client
    last = await _tradier_quote(client, symbol)
    expirations = await _tradier_expirations(client, symbol)

    candidates = []
    for exp in expirations:
        dte = _dte(exp)
        if dte is not None and dte >= 0 and dte <= dte_cap:
            candidates.append((exp, dte))
    if not candidates and expirations:
        exp0 = sorted(expirations)[0]
        candidates = [(exp0, _dte(exp0))]

    # Build fast list first from chains
    prelim: List[OptionContract] = []
    for exp, _d in candidates[:5]:
        chain = await _tradier_chain(client, symbol, exp, opt_type)
        for row in chain:
            strike = _safe_float(row.get("strike"))
            bid = _safe_float(row.get("bid"))
            ask = _safe_float(row.get("ask"))
            last_px = _safe_float(row.get("last"))
            oi = _safe_int(row.get("open_interest"))
            vol = _safe_int(row.get("volume"))
            g = (row.get("greeks") or {})
            delta = _safe_float(g.get("delta"))
            mark = _calc_mark(bid, ask, last_px)
            spread = _calc_spread_pct(bid, ask)
            prelim.append(OptionContract(
                symbol=str(row.get("symbol", "")),
                expiration=str(row.get("expiration_date", exp)),
                strike=strike or 0.0,
                option_type=opt_type,
                delta=delta,
                bid=bid, ask=ask, mark=mark, spread_pct=spread,
                open_interest=oi, volume=vol,
                dte=_dte(exp)
            ))

    # Enrich any missing values with batch quotes
    need_symbols = [x.symbol for x in prelim if (x.bid is None or x.ask is None or x.mark is None or x.volume is None or x.open_interest is None or x.delta is None)]
    if need_symbols:
        quotes = await tc.get_quotes(need_symbols)
        for oc in prelim:
            if oc.symbol in quotes:
                q = quotes[oc.symbol]
                bid = _safe_float(q.get("bid"))
                ask = _safe_float(q.get("ask"))
                last_px = _safe_float(q.get("last"))
                vol = _safe_int(q.get("volume"))
                oi = _safe_int(q.get("open_interest"))
                g = (q.get("greeks") or {})
                delta = _safe_float(g.get("delta"))
                oc.bid = oc.bid if oc.bid is not None else bid
                oc.ask = oc.ask if oc.ask is not None else ask
                oc.mark = oc.mark if oc.mark is not None else _calc_mark(bid, ask, last_px)
                oc.spread_pct = oc.spread_pct if oc.spread_pct is not None else _calc_spread_pct(bid, ask)
                oc.volume = oc.volume if oc.volume is not None else vol
                oc.open_interest = oc.open_interest if oc.open_interest is not None else oi
                oc.delta = oc.delta if oc.delta is not None else delta

    missing_delta = [oc for oc in prelim if oc.delta is None]
    if missing_delta:
        tasks = [
            tc.get_option_greeks(
                symbol, oc.expiration, oc.strike, option_type=oc.option_type
            )
            for oc in missing_delta
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for oc, res in zip(missing_delta, results):
            if isinstance(res, Exception):
                continue
            g = (res.get("greeks") if isinstance(res, dict) else {}) or {}
            oc.delta = _safe_float(g.get("delta"))

    # Rank ATM + spread + volume
    def score_item(oc: OptionContract, last_px_underlying: Optional[float]) -> float:
        if last_px_underlying is not None and oc.strike:
            dist = abs(oc.strike - last_px_underlying)
        else:
            dist = 10.0
        spread_pen = (oc.spread_pct if oc.spread_pct is not None else 0.05)
        vol = oc.volume or 0
        return (dist) + (spread_pen * 5.0) - (min(vol, 50000) / 100000.0)

    filtered = [x for x in prelim if x.option_type == opt_type and x.strike is not None]
    filtered.sort(key=lambda oc: score_item(oc, last))
    top = filtered[:n]

    # Quality score (0..1)
    picks: List[OptionContract] = []
    for oc in top:
        s = score_item(oc, last)
        quality = max(0.0, 1.0 - min(s / 10.0, 1.0))
        oc.score = round(quality, 4)
        picks.append(oc)

    return OptionsPickResponse(
        ok=True, env="tradier_sandbox", note=ENV_NOTE,
        count_considered=len(filtered), picks=picks, source="tradier"
    )

async def _fallback_polygon(symbol: str, side: str, horizon: str, n: int) -> OptionsPickResponse:
    opt_type = "call" if side.endswith("call") else "put"
    items = await _polygon_chain(symbol, max_count=500)
    if not items:
        raise HTTPException(status_code=502, detail="polygon_fallback_empty")
    # Nearest DTE then strike (no quotes available here)
    def _dte_local(exp: str) -> int:
        v = _dte(exp)
        return v if v is not None else 999
    filtered = []
    for it in items:
        if (it.get("option_type")) != opt_type:
            continue
        exp = str(it.get("expiration_date"))
        strike = _safe_float(it.get("strike"))
        if exp and strike is not None:
            filtered.append((exp, _dte_local(exp), strike, it))
    filtered.sort(key=lambda x: (x[1], abs(x[2])))
    out: List[OptionContract] = []
    for exp, dte, strike, it in filtered[:n]:
        out.append(OptionContract(
            symbol=str(it.get("symbol") or it.get("ticker")),
            expiration=exp, strike=strike, option_type=opt_type,
            dte=dte, bid=None, ask=None, mark=None, spread_pct=None,
            open_interest=None, volume=None, score=None
        ))
    return OptionsPickResponse(
        ok=True, env="polygon_fallback", note="polygon reference contracts (no quotes)",
        count_considered=len(filtered), picks=out, source="polygon"
    )

# ---------- Route ----------
@router.post("/pick", response_model=OptionsPickResponse)
async def options_pick(
    req: OptionsPickRequest,
    client: TradierClient = Depends(get_tradier_client),
):
    """
    Primary: Tradier Sandbox delayed chain + quotes enrichment.
    Fallback: Polygon reference when Tradier is unavailable or empty (unless prefer='tradier').
    """
    force_tradier = (req.prefer == "tradier")
    if not TRADIER_ACCESS_TOKEN and not force_tradier:
        if POLYGON_KEY:
            return await _fallback_polygon(req.symbol, req.side, req.horizon, req.n)
        raise HTTPException(status_code=400, detail="tradier_error: TRADIER_ACCESS_TOKEN not set")

    # Try Tradier first (or force it)
    try:
        res = await _pick_from_tradier(client, req.symbol, req.side, req.horizon, req.n)
        if res and res.ok and res.picks:
            return res
        if force_tradier:
            # No fallback when forcing
            return OptionsPickResponse(ok=True, env="tradier_sandbox", note="no contracts found", count_considered=0, picks=[], source="tradier")
    except HTTPException as he:
        if not force_tradier and POLYGON_KEY:
            return await _fallback_polygon(req.symbol, req.side, req.horizon, req.n)
        raise he
    except Exception as e:
        if not force_tradier and POLYGON_KEY:
            return await _fallback_polygon(req.symbol, req.side, req.horizon, req.n)
        raise HTTPException(status_code=500, detail=f"tradier_unknown_error: {e}")

    if not force_tradier and POLYGON_KEY:
        return await _fallback_polygon(req.symbol, req.side, req.horizon, req.n)
    return OptionsPickResponse(ok=True, env="tradier_sandbox", note="no contracts found", count_considered=0, picks=[], source="tradier")
