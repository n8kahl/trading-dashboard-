from __future__ import annotations

import asyncio
from typing import Any, Dict, List, Optional
from datetime import date, datetime

from fastapi import APIRouter, Body
from pydantic import BaseModel, Field

from importlib import import_module as _im
from app.services.iv_surface import get_iv_surface
from app.engine.bs import greeks as bs_greeks
from app.utils.occ import build_occ

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant"])

# Providers (optional, non-fatal)
PolygonMarket = None
TradierMarket = None
TradierClient = None
try:
    PolygonMarket = getattr(_im("app.services.providers.polygon_market"), "PolygonMarket")
except Exception:
    PolygonMarket = None
try:
    TradierMarket = getattr(_im("app.services.providers.tradier"), "TradierMarket")
    TradierClient = getattr(_im("app.services.providers.tradier"), "TradierClient")
except Exception:
    TradierMarket = TradierClient = None


class Position(BaseModel):
    symbol: str
    type: str = Field(..., description="stock|call|put")
    side: str = Field(..., description="long|short")
    strike: Optional[float] = None
    expiry: Optional[str] = None
    qty: int = 1
    avg_price: Optional[float] = None

class HedgeRequest(BaseModel):
    objective: str = Field(
        "cap_loss",
        description="cap_loss|neutralize_delta|reduce_theta|protect_gap|custom|hold_upside|collect_theta|reduce_vega",
    )
    horizon: str = Field("intraday", description="intraday|swing|weekly|monthly")
    constraints: Optional[Dict[str, Any]] = None
    positions: List[Position]


async def _last_price(sym: str) -> Optional[float]:
    t = None
    if TradierMarket or TradierClient:
        try:
            t = (TradierMarket or TradierClient)()
            q = await t.quote_last(sym) if asyncio.iscoroutinefunction(t.quote_last) else t.quote_last(sym)
            if q and q.get("price") is not None:
                return float(q["price"])
        except Exception:
            pass
    if PolygonMarket:
        try:
            p = PolygonMarket()
            lt = await p.last_trade(sym) if asyncio.iscoroutinefunction(p.last_trade) else p.last_trade(sym)
            if lt and lt.get("price") is not None:
                return float(lt["price"])
        except Exception:
            pass
    return None


def _days_to_exp(expiry: Optional[str]) -> float:
    if not expiry:
        return 7.0
    try:
        ed = datetime.strptime(expiry, "%Y-%m-%d").date()
        return max(1.0, (ed - date.today()).days)
    except Exception:
        return 7.0


async def _nbbo(option_symbol: str) -> Dict[str, Any]:
    if not PolygonMarket:
        return {}
    try:
        p = PolygonMarket()
        q = await p.option_quote(option_symbol) if asyncio.iscoroutinefunction(p.option_quote) else p.option_quote(option_symbol)
        return q or {}
    except Exception:
        return {}


def _approx_iv_for_position(surface_map: Dict[str, Any], expiry: Optional[str], strike: Optional[float], last_price: Optional[float]) -> Optional[float]:
    if not expiry or last_price is None:
        return None
    exp_map = (surface_map or {}).get(str(expiry)) or {}
    if not exp_map:
        return None
    # choose bucket
    bucket = 'all'
    try:
        if strike is not None and last_price > 0:
            m = abs((float(strike) - float(last_price))/float(last_price))
            if m <= 0.01 and exp_map.get('atm'): bucket = 'atm'
            elif m <= 0.03 and exp_map.get('near'): bucket = 'near'
    except Exception:
        pass
    vals = exp_map.get(bucket) or exp_map.get('all') or []
    if not vals:
        return None
    try:
        return float(sum(vals)/len(vals))
    except Exception:
        return None


@router.post("/hedge")
async def hedge_plan(req: HedgeRequest = Body(...)) -> Dict[str, Any]:
    # Group positions by underlying symbol
    groups: Dict[str, List[Position]] = {}
    for p in req.positions:
        groups.setdefault(p.symbol.upper(), []).append(p)

    out: Dict[str, Any] = {"ok": True, "plans": {}}

    for sym, poss in groups.items():
        last = await _last_price(sym)
        poly = PolygonMarket() if PolygonMarket else None
        surface = {}
        try:
            if poly:
                s = await get_iv_surface(poly, sym, rows=None, ttl=180, last_price=last)
                surface = (s or {}).get("surface") or {}
        except Exception:
            surface = {}

        # Aggregate exposures (approx)
        net = {"delta": 0.0, "theta": 0.0, "vega": 0.0}
        pos_out: List[Dict[str, Any]] = []
        for p in poss:
            greeks = {"delta": 0.0, "theta": 0.0, "vega": 0.0}
            if p.type.lower() in ("call","put"):
                iv = _approx_iv_for_position(surface, p.expiry, p.strike, last) or 0.25
                days = _days_to_exp(p.expiry)
                d, th, v = bs_greeks(S=last or 0.0, K=float(p.strike or 0.0), iv=float(iv), days_to_exp=days, typ=p.type.lower())
                mult = (1 if p.side.lower()=="long" else -1) * int(p.qty or 1)
                greeks = {"delta": d*mult, "theta": th*mult, "vega": v*mult}
            elif p.type.lower() == "stock":
                mult = (1 if p.side.lower()=="long" else -1) * int(p.qty or 1)
                greeks = {"delta": 1.0 * mult, "theta": 0.0, "vega": 0.0}
            for k in net:
                net[k] += greeks[k]
            pos_out.append({"raw": p.dict(), "greeks": greeks})

        # Suggestions
        suggestions: List[Dict[str, Any]] = []

        # Rule: cap naked shorts with a vertical in same expiry
        for p in poss:
            if p.type.lower() in ("call","put") and p.side.lower()=="short" and p.expiry and p.strike and last:
                width = max(1.0, round(0.02 * float(last), 2))
                if p.type.lower()=="call":
                    prot_strike = float(p.strike) + width
                    cp = 'call'
                else:
                    prot_strike = max(0.5, float(p.strike) - width)
                    cp = 'put'
                occ = build_occ(sym, p.expiry, cp, prot_strike)
                q = await _nbbo(occ)
                suggestions.append({
                    "type": "vertical_cap",
                    "underlying": sym,
                    "legs": [
                        {"action": "BUY", "type": cp, "strike": round(prot_strike,2), "expiry": p.expiry, "symbol": occ, "nbbo": q}
                    ],
                    "rationale": "Cap max loss on naked short by buying farther OTM same-expiry to form a vertical.",
                    "pros_cons": [
                        "+ Defines max loss; reduces tail risk",
                        "- Costs premium; may reduce credit or add debit",
                        "- Liquidity must be acceptable (tight/stable spreads)"
                    ]
                })

        # Rule: long stock -> protective put (or collar if asked to collect theta)
        for p in poss:
            if p.type.lower()=="stock" and p.side.lower()=="long" and last:
                # protective put ~5% OTM, next weekly
                days = 7.0
                try:
                    ed = date.today().toordinal() + int(days)
                    exp = (date.fromordinal(ed)).isoformat()
                except Exception:
                    exp = None
                strike = round(float(last) * 0.95, 2)
                if exp:
                    occ = build_occ(sym, exp, 'put', strike)
                    q = await _nbbo(occ)
                    suggestions.append({
                        "type": "protective_put",
                        "underlying": sym,
                        "legs": [
                            {"action": "BUY", "type": "put", "strike": strike, "expiry": exp, "symbol": occ, "nbbo": q}
                        ],
                        "rationale": "Limit downside on stock via protective put (~5% OTM).",
                        "pros_cons": [
                            "+ Defines max loss for the covered period",
                            "- Costs premium; consider adding short call to finance (collar)"
                        ]
                    })

        out["plans"][sym] = {
            "last": last,
            "positions": pos_out,
            "net_greeks": {k: round(v,4) for k,v in net.items()},
            "suggestions": suggestions
        }

    return out
