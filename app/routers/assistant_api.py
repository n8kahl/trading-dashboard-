from __future__ import annotations

import asyncio, inspect, math
from typing import Any, Dict, List, Optional, Tuple, Literal
from app.services.indicators import spread_stability as _spread_stability
from app.services.iv_surface import get_iv_surface, percentile_rank as _pct_rank_surface
from app.services.state_store import record_chain_aggregates
from fastapi import APIRouter, Body, HTTPException
from pydantic import BaseModel, Field, ValidationError

from app.routers.diag import providers as diag_providers
from app.routers.market import market_overview as market_overview_route
try:
    from app.services.setup_scanner import scan_top_setups as _scan_top_setups
except Exception:
    _scan_top_setups = None  # type: ignore
from app.routers.hedge import HedgeRequest, hedge_plan
from app.routers.market_data import compute_levels as market_compute_levels
from sqlalchemy import select, desc
from app.db.session import SessionLocal
from app.db.models import Feature

router = APIRouter(prefix="/api/v1")

# ---------- Dynamic provider imports (robust, non-fatal) ----------
from importlib import import_module as _im
import os, re
from urllib.parse import urlencode
from datetime import datetime
from app.engine.risk_flags import compute_risk_flags

PolygonMarket = None
TradierMarket = None
TradierClient = None
_prov_err: List[str] = []

for mod, cls in [
    ("app.services.providers.polygon_market", "PolygonMarket"),
    ("app.services.providers.polygon", "PolygonMarket"),
    ("app.services.providers.polygon_client", "PolygonClient"),
]:
    try:
        PolygonMarket = getattr(_im(mod), cls)
        break
    except Exception as e:
        _prov_err.append(f"{mod}.{cls}: {type(e).__name__}: {e}")

for mod, cls in [
    ("app.services.providers.tradier_market", "TradierMarket"),
    ("app.services.providers.tradier", "TradierMarket"),
    ("app.services.providers.tradier", "TradierClient"),
]:
    try:
        _klass = getattr(_im(mod), cls)
        TradierMarket = TradierMarket or _klass
        TradierClient = TradierClient or _klass
        break
    except Exception as e:
        _prov_err.append(f"{mod}.{cls}: {type(e).__name__}: {e}")

# ---------- Optional engine imports (safe fallbacks) ----------
expected_move_from_straddle = None
probability_of_touch = None
tradeability_score = None
expected_value_intraday = None

try:
    em_mod = _im("app.engine.options_scoring")
    expected_move_from_straddle = getattr(em_mod, "expected_move_from_straddle", None)
    probability_of_touch = getattr(em_mod, "probability_of_touch", None)
    tradeability_score = getattr(em_mod, "tradeability_score", None)
    expected_value_intraday = getattr(em_mod, "expected_value_intraday", None)
except Exception as e:
    _prov_err.append(f"engine.options_scoring: {type(e).__name__}: {e}")

# ---------- Helpers ----------
async def _maybe_await(v):
    if inspect.isawaitable(v):
        return await v
    return v

_OCC_RE = re.compile(r"^([A-Z]+)(\d{2})(\d{2})(\d{2})([CP])(\d{8})$")

def _occ_parse(sym: str):
    m = _OCC_RE.match(sym or "")
    if not m:
        return None
    und, yy, mm, dd, cp, strike8 = m.groups()
    strike = float(int(strike8) / 1000.0)
    expiry = f"20{yy}-{mm}-{dd}"
    otype = "call" if cp == "C" else "put"
    return {"underlying": und, "expiry": expiry, "type": otype, "strike": strike}

def _fmt_expiry(expiry: str) -> str:
    try:
        dt = datetime.strptime(str(expiry), "%Y-%m-%d")
        return dt.strftime("%b %d, %Y")
    except Exception:
        return str(expiry)

def _attach_display_fields(underlying: str, pick: Dict[str, Any]) -> None:
    occ = None
    if isinstance(pick.get("symbol"), str):
        occ = _occ_parse(pick["symbol"]) or None
    expiry = pick.get("expiry") or (occ and occ.get("expiry"))
    strike = pick.get("strike") or (occ and occ.get("strike"))
    otype = (pick.get("type") or pick.get("option_type") or (occ and occ.get("type")) or "").lower()
    otype = "call" if otype.startswith("c") else ("put" if otype.startswith("p") else otype)
    und = (underlying or occ and occ.get("underlying") or "").upper() or underlying
    if expiry:
        pick["expiry_display"] = _fmt_expiry(str(expiry))
        pick["expiry"] = str(expiry)
    if strike is not None:
        try:
            pick["strike"] = float(strike)
        except Exception:
            pass
    if und and expiry and pick.get("strike") is not None and otype in ("call", "put"):
        pick["contract_display"] = f"{und} {pick['expiry_display']} {pick['strike']:.0f} {otype.capitalize()}"
    for k in ("bid", "ask", "last"):
        if pick.get(k) is not None:
            try:
                pick[f"{k}_display"] = f"${float(pick[k]):.2f}"
            except Exception:
                pass

def _near_atm_pairs(chain_rows: List[Dict[str, Any]], last_price: float, topK: int = 6) -> List[Dict[str, Any]]:
    """Pick a few near-ATM call & put rows from a generic chain list; normalize fields."""
    if not chain_rows or last_price is None:
        return []
    def keyer(r):
        try:
            return abs(float(r.get("strike", 0.0)) - float(last_price))
        except Exception:
            return 1e9
    def norm(r):
        g = r.get("greeks") or {}
        iv = r.get("iv") or r.get("implied_volatility") or g.get("iv")
        d  = r.get("delta") or g.get("delta")
        symbol = r.get("symbol") or r.get("contract") or r.get("id")
        typ = (r.get("type") or r.get("option_type") or "").lower()
        typ = "call" if typ.startswith("c") else ("put" if typ.startswith("p") else typ)
        bid = r.get("bid"); ask = r.get("ask")
        spread_pct = None
        try:
            if bid is not None and ask is not None and ask > 0:
                spread_pct = round((ask - bid)/ask*100, 2)
        except Exception:
            pass
        return {
            "symbol": symbol,
            "type": typ,
            "strike": r.get("strike"),
            "delta": d,
            "iv": iv,
            "oi": r.get("open_interest") or r.get("oi"),
            "volume": r.get("volume"),
            "bid": bid, "ask": ask,
            "spread_pct": spread_pct
        }

    calls = [r for r in chain_rows if (r.get("type") or r.get("option_type","")).lower().startswith("c")]
    puts  = [r for r in chain_rows if (r.get("type") or r.get("option_type","")).lower().startswith("p")]
    calls = list(map(norm, sorted(calls, key=keyer)[:max(1, topK//2)]))
    puts  = list(map(norm, sorted(puts,  key=keyer)[:max(1, topK//2)]))
    return calls + puts

def _simple_em_from_straddle(last_price: float, picks: List[Dict[str, Any]]) -> Tuple[Optional[float], Optional[float]]:
    """Fallback EM if engine fn not available. Use average of top2 call/put mid prices."""
    if expected_move_from_straddle:
        try:
            em_abs, em_rel = expected_move_from_straddle(last_price=last_price, candidates=picks)
            return em_abs, em_rel
        except Exception:
            pass
    # fallback: compute mids and sum of nearest call+put ≈ straddle price; EM ≈ straddle / spot
    calls = [p for p in picks if p.get("type")=="call" and p.get("bid") is not None and p.get("ask") is not None]
    puts  = [p for p in picks if p.get("type")=="put"  and p.get("bid") is not None and p.get("ask") is not None]
    if not calls or not puts:
        return None, None
    def mid(x): return (x["bid"] + x["ask"])/2.0 if x["bid"] is not None and x["ask"] is not None else None
    cm = sorted([mid(c) for c in calls if mid(c) is not None])[:2]
    pm = sorted([mid(p) for p in puts  if mid(p) is not None])[:2]
    if not cm or not pm:
        return None, None
    straddle = (sum(cm)/len(cm)) + (sum(pm)/len(pm))
    em_abs = straddle  # crude fallback
    em_rel = (straddle/last_price) if last_price else None
    return em_abs, em_rel

def _p_touch(distance: float, sigma_abs: float) -> Optional[float]:
    """Fallback touch probability if engine fn not present."""
    if probability_of_touch:
        try:
            return probability_of_touch(distance=distance, sigma_abs=sigma_abs)
        except Exception:
            pass
    try:
        # Brownian max approx: 2*(1 - Phi(d/(sigma)))
        x = distance / max(1e-8, sigma_abs)
        # approx Phi via erf
        import math
        Phi = 0.5*(1.0 + math.erf(x/math.sqrt(2)))
        return max(0.0, min(1.0, 2.0*(1.0 - Phi)))
    except Exception:
        return None

# ---------- Chart link helper ----------
_PUBLIC_BASE = os.getenv("PUBLIC_BASE_URL", "") or "https://web-production-a9084.up.railway.app"

def _confluence_tags(r: Dict[str, Any], horizon: str) -> List[str]:
    tags: List[str] = []
    sp = r.get("spread_pct")
    if sp is not None:
        tags.append("spread_tight" if sp <= 10 else "spread_wide")
    st = r.get("spread_stability")
    if isinstance(st, (int, float)):
        if st >= 0.6:
            tags.append("stability_ok")
    ivp = r.get("iv_percentile")
    if isinstance(ivp, (int, float)):
        if 25 <= ivp <= 75:
            tags.append("iv_mid")
        else:
            tags.append("iv_extreme")
    evd = (r.get("ev") or {}).get("dollars")
    if isinstance(evd, (int, float)):
        tags.append("ev_positive" if evd > 0 else "ev_negative")
    oi = r.get("oi") or 0; vol = r.get("volume") or 0
    try:
        if int(oi) >= 500 or int(vol) >= 100:
            tags.append("liquidity_ok")
        else:
            tags.append("liquidity_light")
    except Exception:
        pass
    d = r.get("delta")
    try:
        if d is not None:
            target = 0.50 if horizon=="scalp" else 0.40 if horizon=="intraday" else 0.30
            if abs(abs(float(d)) - target) <= 0.1:
                tags.append("delta_fit")
    except Exception:
        pass
    return tags

def _chart_url(
    sym: str,
    last: Optional[float],
    em_abs: Optional[float],
    em_rel: Optional[float],
    r: Dict[str, Any],
    horizon: str,
    hits: Dict[str, Any],
    key_levels: Optional[Dict[str, Any]] = None,
    fibs: Optional[Dict[str, Any]] = None,
) -> Optional[str]:
    try:
        if last is None or em_abs is None:
            return None
        direction = "long" if (r.get("type") == "call") else "short"
        entry = float(last)
        if direction == "long":
            sl = entry - 0.25 * em_abs
            tp1 = entry + 0.25 * em_abs
            tp2 = entry + 0.50 * em_abs
        else:
            sl = entry + 0.25 * em_abs
            tp1 = entry - 0.25 * em_abs
            tp2 = entry - 0.50 * em_abs
        conf = ",".join(_confluence_tags(r, horizon))
        # Simple beginner-friendly plan text (pipe-separated bullets)
        plan = []
        if direction == "long":
            plan.append("Wait for breakout above Entry, then a quick retest that holds")
        else:
            plan.append("Wait for breakdown below Entry, then a quick retest that fails")
        plan.append("If invalidation hits, exit quickly and reassess")
        plan.append("Take Target 1 near 0.25×EM; consider Target 2 near 0.50×EM")

        level_candidates = _collect_level_candidates(key_levels, fibs)
        window = max(0.15, (em_abs or 1.0) * 0.15)
        if level_candidates:
            if tp1 is not None:
                tp1_note = _nearest_level(tp1, entry, direction, level_candidates, window)
                if tp1_note:
                    plan.append(f"TP1 aligns with {tp1_note[0]} @ {tp1_note[1]:.2f}")
                    r.setdefault("level_confluence", {})["tp1"] = {"label": tp1_note[0], "price": round(tp1_note[1], 2)}
            if tp2 is not None:
                tp2_note = _nearest_level(tp2, entry, direction, level_candidates, window * 1.5)
                if tp2_note:
                    plan.append(f"TP2 mindful of {tp2_note[0]} @ {tp2_note[1]:.2f}")
                    r.setdefault("level_confluence", {})["tp2"] = {"label": tp2_note[0], "price": round(tp2_note[1], 2)}
            stop_note = _stop_near(entry, sl, direction, level_candidates, window)
            if stop_note:
                plan.append(f"Stop sits near {stop_note[0]} @ {stop_note[1]:.2f}")
                r.setdefault("level_confluence", {})["stop"] = {"label": stop_note[0], "price": round(stop_note[1], 2)}

        if em_abs:
            if em_rel:
                plan.append(f"Expected move ±{em_abs:.2f} (~{em_rel*100:.1f}% of spot)")
            else:
                plan.append(f"Expected move ±{em_abs:.2f}")

        chart_sym = 'SPY' if _is_spx(sym) else ('QQQ' if _is_ndx(sym) else sym)
        # Determine state label for chart
        state_label = "Scalp (0DTE)" if horizon == "scalp" else ("Intraday" if horizon == "intraday" else horizon.title())
        q = {
            "symbol": chart_sym,
            "interval": "1m",
            "lookback": 390,
            "overlays": "vwap,ema20,ema50,pivots",
            "entry": round(entry, 4),
            "sl": round(sl, 4),
            "tp1": round(tp1, 4),
            "tp2": round(tp2, 4),
            "direction": direction,
            "confluence": conf,
            "em_abs": round(em_abs, 4),
            "em_rel": (round(em_rel, 6) if isinstance(em_rel, (int, float)) else None),
            "anchor": "entry",
            "hit_tp1": hits.get("tp1"),
            "hit_tp2": hits.get("tp2"),
            "state": state_label,
            "plan": " | ".join(plan),
            "theme": "dark",
        }
        # drop None values
        q = {k:v for k,v in q.items() if v is not None}
        return f"{_PUBLIC_BASE}/charts/proposal?" + urlencode(q)
    except Exception:
        return None

# Expiry helper
def _auto_expiry(hz: str) -> str:
    from datetime import date, timedelta
    today = date.today()
    if hz in ("scalp", "intraday"):
        # Next Friday (incl. today if Friday -> next week)
        days = (4 - today.weekday()) % 7 or 7
        return str(today + timedelta(days=days))
    # swing default ~2 weeks
    return str(today + timedelta(days=14))

def _normalize_expiry(raw: Any, hz: str) -> str:
    if raw is None:
        return _auto_expiry(hz)
    if isinstance(raw, bool) and raw:
        return _auto_expiry(hz)
    if isinstance(raw, str) and raw.strip().lower() == "auto":
        return _auto_expiry(hz)
    if isinstance(raw, str) and raw.strip().lower() in ("today", "0dte", "odte"):
        from datetime import date
        return str(date.today())
    return str(raw)

def _is_spx(sym: str) -> bool:
    s = (sym or "").upper()
    return s in ("SPX", "SPXW", "^SPX")

def _is_ndx(sym: str) -> bool:
    s = (sym or "").upper()
    return s in ("NDX", "^NDX")


_LEVEL_LABELS = {
    "prev_high": "Yesterday High",
    "prev_low": "Yesterday Low",
    "prev_close": "Yesterday Close",
    "premarket_high": "Pre-market High",
    "premarket_low": "Pre-market Low",
    "session_high": "Prior Session High",
    "session_low": "Prior Session Low",
}


def _collect_level_candidates(key_levels: Optional[Dict[str, Any]], fibs: Optional[Dict[str, Any]]) -> List[Tuple[str, float]]:
    levels: List[Tuple[str, float]] = []
    if isinstance(key_levels, dict):
        for key, label in _LEVEL_LABELS.items():
            value = key_levels.get(key)
            try:
                if value is not None:
                    levels.append((label, float(value)))
            except (TypeError, ValueError):
                continue
    if isinstance(fibs, dict):
        for group_name in ("retracements", "extensions"):
            group = fibs.get(group_name) or {}
            if not isinstance(group, dict):
                continue
            for tag, value in group.items():
                try:
                    if value is not None:
                        prefix = "Fib" if group_name == "retracements" else "Fib Ext"
                        levels.append((f"{prefix} {tag}", float(value)))
                except (TypeError, ValueError):
                    continue
    return levels


def _nearest_level(target: float, entry: float, direction: str, levels: List[Tuple[str, float]], window: float) -> Optional[Tuple[str, float]]:
    candidates: List[Tuple[str, float, float]] = []
    for label, price in levels:
        if direction == "long" and price < min(entry, target):
            continue
        if direction == "short" and price > max(entry, target):
            continue
        diff = abs(price - target)
        if diff <= window:
            candidates.append((label, price, diff))
    if not candidates:
        return None
    label, price, _ = min(candidates, key=lambda x: x[2])
    return label, price


def _stop_near(entry: float, stop: float, direction: str, levels: List[Tuple[str, float]], window: float) -> Optional[Tuple[str, float]]:
    candidates: List[Tuple[str, float, float]] = []
    for label, price in levels:
        if direction == "long" and price > entry:
            continue
        if direction == "short" and price < entry:
            continue
        diff = abs(price - stop)
        if diff <= window:
            candidates.append((label, price, diff))
    if not candidates:
        return None
    label, price, _ = min(candidates, key=lambda x: x[2])
    return label, price


async def _market_internals_summary(poly) -> Optional[Dict[str, Any]]:
    """Fetch a few market-internals proxies (advancers/decliners, TICK, ADD) and distil a signal."""
    if not poly:
        return None

    symbol_map = {
        "advancers": "ADVN",
        "decliners": "DECL",
        "tick": "TICK",
        "add": "ADD",
    }

    async def _safe_last(sym: str):
        try:
            lt = await poly.last_trade(sym)
            if lt and lt.get("price") is not None:
                return float(lt.get("price"))
        except Exception:
            return None
        return None

    results = await asyncio.gather(*[_safe_last(ticker) for ticker in symbol_map.values()], return_exceptions=True)
    internals: Dict[str, Any] = {}
    for (label, _), value in zip(symbol_map.items(), results):
        if isinstance(value, Exception):
            internals[label] = {"value": None, "error": f"{type(value).__name__}: {value}"}
        else:
            internals[label] = {"value": value}

    def _val(name: str) -> Optional[float]:
        entry = internals.get(name) or {}
        v = entry.get("value")
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

    adv = _val("advancers")
    dec = _val("decliners")
    tick_val = _val("tick")
    add_line = _val("add")

    notes: List[str] = []
    score = 0

    if adv is not None and dec is not None and (adv + dec) > 0:
        breadth_ratio = adv / (adv + dec)
        internals["breadth_ratio"] = round(breadth_ratio, 3)
        adv_minus_dec = adv - dec
        internals["adv_minus_decliners"] = round(adv_minus_dec, 0)
        if breadth_ratio >= 0.62:
            score += 1
            notes.append("Breadth > 0.62 (buyers broadly participating)")
        elif breadth_ratio <= 0.38:
            score -= 1
            notes.append("Breadth < 0.38 (decliners dominating)")
        if abs(adv_minus_dec) >= 1200:
            if adv_minus_dec > 0:
                score += 1
                notes.append("Advancers outpacing decliners by >1.2k")
            else:
                score -= 1
                notes.append("Decliners outpacing advancers by >1.2k")
    else:
        internals["breadth_ratio"] = None

    if tick_val is not None:
        internals["tick"] = round(tick_val, 0)
        if tick_val >= 600:
            score += 1
            notes.append("TICK > +600 (aggressive buying pressure)")
        elif tick_val <= -600:
            score -= 1
            notes.append("TICK < -600 (aggressive selling pressure)")
        elif tick_val <= -300:
            score -= 0.5
            notes.append("TICK < -300 (selling bias)")
        elif tick_val >= 300:
            score += 0.5
            notes.append("TICK > +300 (buying bias)")
    else:
        internals["tick"] = None

    if add_line is not None:
        internals["add_line"] = round(add_line, 0)

    # Sector breadth via overview (best-effort)
    try:
        overview = await market_overview_route(indices="SPY,QQQ", sectors="XLK,XLV,XLF,XLE,XLY,XLP,XLI,XLB,XLRE,XLU,XLC")
        sectors = (overview or {}).get("sectors") or {}
        up = [sym for sym, payload in sectors.items() if isinstance(payload, dict) and isinstance(payload.get("change_pct"), (int, float)) and payload.get("change_pct", 0) > 0]
        down = [sym for sym, payload in sectors.items() if isinstance(payload, dict) and isinstance(payload.get("change_pct"), (int, float)) and payload.get("change_pct", 0) < 0]
        internals["sectors_up"] = len(up)
        internals["sectors_down"] = len(down)
        if len(up) + len(down) >= 6:
            breadth_diff = len(up) - len(down)
            if breadth_diff >= 4:
                score += 1
                notes.append("Major sectors tilting risk-on")
            elif breadth_diff <= -4:
                score -= 1
                notes.append("Major sectors tilting risk-off")
    except Exception:
        pass

    bias = "balanced"
    if score >= 2:
        bias = "risk_on"
    elif score <= -2:
        bias = "risk_off"
    elif score > 0:
        bias = "slight_risk_on"
    elif score < 0:
        bias = "slight_risk_off"

    internals["score"] = round(score, 2)
    internals["bias"] = bias
    if notes:
        internals["notes"] = notes

    return internals


# ---------- API Schemas ----------
PRIMARY_OPS: Tuple[str, ...] = (
    "diag.health",
    "diag.providers",
    "assistant.actions",
    "market.overview",
    "market.setups",
    "assistant.hedge",
    "premarket.context",
)

LEGACY_OPS: Tuple[str, ...] = ("data.snapshot",)


class ExecRequest(BaseModel):
    op: Literal[
        "diag.health",
        "diag.providers",
        "assistant.actions",
        "market.overview",
        "market.setups",
        "assistant.hedge",
        "premarket.context",
        "positions.manage",
        "data.snapshot",
    ]
    args: Dict[str, Any] = Field(default_factory=dict)


class PositionSpec(BaseModel):
    symbol: str
    type: Literal["call", "put"]
    side: Literal["long", "short"]
    strike: float
    expiry: str
    qty: int = 1
    avg_price: Optional[float] = None


class PositionsManageRequest(BaseModel):
    positions: List[PositionSpec]
    horizon: str = Field(default="swing")


class ArgsMarketOverview(BaseModel):
    indices: Optional[List[str]] = None
    sectors: Optional[List[str]] = None


class ArgsMarketSetups(BaseModel):
    limit: int = Field(default=10, ge=3, le=30)
    include_options: bool = Field(default=True)
    symbols: Optional[List[str]] = None
    strict: bool = Field(default=True)
    min_confidence: int = Field(default=70, ge=0, le=100)


def _bad_request(op: str, message: str, details: Optional[Dict[str, Any]] = None) -> HTTPException:
    payload: Dict[str, Any] = {
        "ok": False,
        "error": {
            "code": "BAD_REQUEST",
            "message": message,
        },
    }
    if details:
        payload["error"]["details"] = details
    return HTTPException(status_code=400, detail=payload)


@router.get("/assistant/actions")
async def assistant_actions() -> Dict[str, Any]:
    return {
        "ok": True,
        "ops": list(PRIMARY_OPS),
        "legacy_ops": list(LEGACY_OPS),
        "providers": {"polygon": bool(PolygonMarket), "tradier": bool(TradierMarket or TradierClient)},
        "import_errors": _prov_err,
    }


@router.post("/assistant/exec")
async def assistant_exec(payload: ExecRequest = Body(...)) -> Dict[str, Any]:
    op = payload.op

    if op == "diag.health":
        return {"ok": True, "op": op, "data": {"status": "ok"}}

    if op == "diag.providers":
        providers = await diag_providers()
        return {"ok": True, "op": op, "data": providers}

    if op == "assistant.actions":
        actions = await assistant_actions()
        ok = bool(actions.get("ok", True))
        data = {k: v for k, v in actions.items() if k != "ok"}
        return {"ok": ok, "op": op, "data": data}

    if op == "market.overview":
        try:
            args = ArgsMarketOverview.model_validate(payload.args or {})
        except ValidationError as exc:
            raise _bad_request(op, "Invalid args", {"errors": exc.errors()}) from exc
        indices_list = args.indices or ["SPY", "QQQ"]
        sectors_list = args.sectors or [
            "XLK",
            "XLV",
            "XLF",
            "XLE",
            "XLI",
            "XLY",
            "XLP",
            "XLU",
            "XLRE",
            "XLB",
        ]
        indices = ",".join(sorted({s.upper() for s in indices_list if s}))
        sectors = ",".join(sorted({s.upper() for s in sectors_list if s}))
        overview = await market_overview_route(indices=indices, sectors=sectors)
        ok = bool(overview.get("ok", True))
        data = {k: v for k, v in overview.items() if k != "ok"}
        return {"ok": ok, "op": op, "data": data}

    if op == "market.setups":
        try:
            args = ArgsMarketSetups.model_validate(payload.args or {})
        except ValidationError as exc:
            raise _bad_request(op, "Invalid args", {"errors": exc.errors()}) from exc
        if _scan_top_setups is None:
            raise _bad_request(op, "Setups scanner unavailable", {"import": "app.services.setup_scanner"})
        try:
            symbols_list = [str(s).upper() for s in (getattr(args, 'symbols', None) or [])]
            strict_flag = bool(getattr(args, 'strict', True))
            min_conf = int(getattr(args, 'min_confidence', 70))
            setups = await _scan_top_setups(
                limit=args.limit,
                include_options=bool(getattr(args, 'include_options', False)),
                symbols=symbols_list,
                strict=strict_flag,
                min_confidence=min_conf,
            )
            fallback_used = False
            # Automatic second pass for broad scans (no symbols) when strict returns empty
            if not setups and strict_flag and not symbols_list:
                setups = await _scan_top_setups(
                    limit=args.limit,
                    include_options=bool(getattr(args, 'include_options', False)),
                    symbols=None,
                    strict=False,
                    min_confidence=max(0, min_conf - 5 if min_conf else 65) or 65,
                )
                fallback_used = True

            data = {"count": len(setups), "setups": setups}
            if fallback_used:
                data["fallback"] = True

            if not setups and symbols_list:
                try:
                    snap_args = {
                        "symbols": [symbols_list[0]],
                        "horizon": "intraday",
                        "include": ["options"],
                    }
                    snapshot = await _handle_snapshot(snap_args)
                    data["snapshot"] = snapshot
                    data["snapshot_args"] = snap_args
                except Exception:
                    data["snapshot"] = None

            return {"ok": True, "op": op, "data": data}
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"ok": False, "error": {"code": type(exc).__name__, "message": str(exc)}})

    if op == "assistant.hedge":
        try:
            hedge_req = HedgeRequest.model_validate(payload.args or {})
        except ValidationError as exc:
            raise _bad_request(op, "Invalid args", {"errors": exc.errors()}) from exc
        hedge_resp = await hedge_plan(hedge_req)
        ok = bool(hedge_resp.get("ok", True))
        data = {k: v for k, v in hedge_resp.items() if k != "ok"}
        return {"ok": ok, "op": op, "data": data}

    if op == "premarket.context":
        # Return the most recent premarket Feature payload (symbol-specific takes precedence, then wildcard "*")
        symbols_req = []
        try:
            symbols_req = [str(s).upper() for s in (payload.args or {}).get("symbols") or []]
        except Exception:
            symbols_req = []
        try:
            async with SessionLocal() as s:
                # If a specific symbol list is provided, try the first symbol, else wildcard
                where_symbols = symbols_req[:1] if symbols_req else []
                # Build ordered search: first provided symbol if any, then wildcard
                search_syms = where_symbols + (["*"] if "*" not in where_symbols else [])
                pre: Optional[Dict[str, Any]] = None
                for symq in search_syms or ["*"]:
                    stmt = (
                        select(Feature)
                        .where(Feature.horizon == "premarket")
                        .where(Feature.symbol == symq)
                        .order_by(desc(Feature.created_at))
                        .limit(1)
                    )
                    res = await s.execute(stmt)
                    feat = res.scalars().first()
                    if feat and isinstance(feat.payload, dict):
                        pre = feat.payload
                        break
                # Enrich with advisory if missing basics
                advisory: Dict[str, Any] = {}
                try:
                    # sentiment fallback based on market overview if absent
                    if pre is None:
                        pre = {}
                    if not pre.get("sentiment"):
                        mo = await market_overview_route(indices="SPY,QQQ", sectors="XLK,XLV,XLF,XLE,XLY,XLP,XLI,XLB,XLRE,XLU,XLC")
                        spy = ((mo or {}).get("indices") or {}).get("SPY") or {}
                        qqq = ((mo or {}).get("indices") or {}).get("QQQ") or {}
                        chg = [x for x in [spy.get("change_pct"), qqq.get("change_pct")] if isinstance(x, (int, float))]
                        if chg and sum(1 for x in chg if x > 0.2) >= 1:
                            pre["sentiment"] = "bullish"
                        elif chg and sum(1 for x in chg if x < -0.2) >= 1:
                            pre["sentiment"] = "bearish"
                        else:
                            pre["sentiment"] = pre.get("sentiment") or "neutral"
                    # ensure tickers list
                    tickers = pre.get("watchlist") or ["SPY","QQQ","AAPL","NVDA"]
                    pre["watchlist"] = tickers
                    # top three things to watch (levels + events)
                    try:
                        lv = await market_compute_levels(PolygonMarket(), "SPY") if PolygonMarket else None
                    except Exception:
                        lv = None
                    top_watch: List[str] = []
                    if lv and lv.get("ok"):
                        kl = (lv.get("key_levels") or {})
                        if kl.get("premarket_high"):
                            top_watch.append(f"SPY premarket high {kl['premarket_high']}: reclaim/reject test")
                        if kl.get("prev_high") and kl.get("prev_low"):
                            top_watch.append(f"Yesterday range {kl['prev_low']}–{kl['prev_high']}: respect breakouts/fakeouts")
                    evs = pre.get("events") or []
                    if isinstance(evs, list) and evs:
                        names = ", ".join(str(e.get("name") or "") for e in evs if isinstance(e, dict))
                        if names.strip():
                            top_watch.append(f"Scheduled events: {names}")
                    if not top_watch:
                        top_watch = ["Watch SPY premarket extremes and yesterday range", "Monitor spreads/liquidity on open", "Reassess bias after first 15 minutes"]
                    pre["top_watch"] = pre.get("top_watch") or top_watch[:3]
                    # attribution removed per request
                except Exception:
                    pass
                return {"ok": True, "op": op, "data": {"premarket": pre}}
        except Exception as exc:
            raise HTTPException(status_code=500, detail={"ok": False, "error": {"code": type(exc).__name__, "message": str(exc)}})

    if op == "positions.manage":
        try:
            req = PositionsManageRequest.model_validate(payload.args or {})
        except ValidationError as exc:
            raise _bad_request(op, "Invalid args", {"errors": exc.errors()}) from exc

        if not req.positions:
            raise _bad_request(op, "At least one position required")

        pos = req.positions[0]
        sym = pos.symbol.upper()
        horizon = (req.horizon or "swing").lower()

        snap_args = {
            "symbols": [sym],
            "horizon": horizon,
            "include": ["options"],
            "options": {
                "expiry": str(pos.expiry),
                "topK": 8,
                "maxSpreadPct": 12,
                "greeks": True,
            },
        }

        snapshot = await _handle_snapshot(snap_args)
        sym_data = (snapshot.get("snapshot", {}) or {}).get("symbols", {}).get(sym) or {}
        errors = snapshot.get("errors") or {}

        options_block = (sym_data.get("options") or {})
        picks: List[Dict[str, Any]] = options_block.get("top") or []
        for p in picks:
            try:
                _attach_display_fields(sym, p)
            except Exception:
                pass

        match = None
        if picks:
            same_type = [r for r in picks if str(r.get("type")).lower() == pos.type]
            same_exp = [r for r in same_type if str(r.get("expiry")) == str(pos.expiry)]
            candidates = same_exp or same_type
            if candidates:
                try:
                    match = min(candidates, key=lambda r: abs(float(r.get("strike", 0.0)) - float(pos.strike)))
                except Exception:
                    match = candidates[0]

        context = sym_data.get("context") or {}
        expected_move = context.get("expected_move") or {}
        key_levels = context.get("key_levels") or {}
        fibs = context.get("fibonacci") or {}
        chart_url = None
        if match:
            chart_url = match.get("chart_url")

        # Position analytics
        curr_bid = match.get("bid") if match else None
        curr_ask = match.get("ask") if match else None
        mid = None
        try:
            if curr_bid is not None and curr_ask is not None:
                mid = round((float(curr_bid) + float(curr_ask)) / 2.0, 2)
        except Exception:
            mid = None
        pl_dollars = None
        pl_percent = None
        if pos.avg_price is not None and curr_bid is not None:
            try:
                pl_dollars = round((float(curr_bid) - float(pos.avg_price)) * 100 * int(pos.qty or 1), 2)
                pl_percent = round((float(curr_bid) - float(pos.avg_price)) / float(pos.avg_price) * 100.0, 2)
            except Exception:
                pl_dollars = pl_percent = None

        breakeven = None
        try:
            if pos.avg_price is not None:
                if pos.type == "call":
                    breakeven = round(float(pos.strike) + float(pos.avg_price), 2)
                else:
                    breakeven = round(float(pos.strike) - float(pos.avg_price), 2)
        except Exception:
            breakeven = None

        tradeability = match.get("tradeability") if match else None
        confidence = None
        if tradeability is not None:
            try:
                confidence = int(max(20.0, min(90.0, float(tradeability))))
            except Exception:
                confidence = None

        # Recommendations & actions
        recommendation = "review"
        actions: Dict[str, Any] = {}

        if match:
            prob = match.get("hit_probabilities") or {}
            tp1_prob = prob.get("tp1")
            try:
                loss_pct = float(pl_percent) if pl_percent is not None else None
                if loss_pct is not None and loss_pct <= -15 and (tp1_prob is not None and float(tp1_prob) < 0.5):
                    recommendation = "trim"
                else:
                    recommendation = "hold"
            except Exception:
                recommendation = "hold"

            if mid is not None:
                actions["trim"] = {"limit": mid, "qty": max(1, int(pos.qty or 1) // 2)}
            if expected_move and expected_move.get("abs") and sym_data.get("price", {}).get("last"):
                try:
                    last_px = float(sym_data["price"]["last"])
                    em_abs = float(expected_move["abs"])
                    stop = round((last_px - 0.25 * em_abs) if pos.type == "call" else (last_px + 0.25 * em_abs), 2)
                    actions["cut"] = {"underlying_stop": stop}
                except Exception:
                    pass
            try:
                from datetime import date, timedelta
                exp_dt = date.fromisoformat(str(pos.expiry))
                target_exp = exp_dt + timedelta(days=28)
                actions["roll"] = {
                    "strike": float(pos.strike),
                    "type": pos.type,
                    "target_expiry": target_exp.isoformat(),
                }
            except Exception:
                pass
            if sym_data.get("price", {}).get("last"):
                try:
                    last_px = float(sym_data["price"]["last"])
                    hedge_strike = round(last_px * (0.95 if pos.type == "call" else 1.05), 2)
                    actions["hedge"] = {
                        "type": "put" if pos.type == "call" else "call",
                        "strike": hedge_strike,
                        "expiry": str(pos.expiry),
                    }
                except Exception:
                    pass

        result = {
            "position": {
                "symbol": sym,
                "type": pos.type,
                "side": pos.side,
                "strike": pos.strike,
                "expiry": pos.expiry,
                "qty": pos.qty,
                "avg_price": pos.avg_price,
                "breakeven": breakeven,
                "pl_dollars": pl_dollars,
                "pl_percent": pl_percent,
            },
            "contract": match or {},
            "market": {
                "price": sym_data.get("price"),
                "expected_move": expected_move,
                "key_levels": key_levels,
                "fibonacci": fibs,
                "chart_url": chart_url,
            },
            "actions": actions,
            "recommendation": recommendation,
            "confidence": confidence,
            "snapshot_errors": errors,
        }

        return {"ok": True, "op": op, "data": result}

    if op == "data.snapshot":
        try:
            result = await _handle_snapshot(payload.args or {})
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail={
                    "ok": False,
                    "error": {
                        "code": type(exc).__name__,
                        "message": str(exc),
                    },
                },
            ) from exc
        ok = bool(result.get("ok", True))
        data = {k: v for k, v in result.items() if k != "ok"}
        return {"ok": ok, "op": op, "data": data}

    raise _bad_request(op, f"Unknown op '{op}' or invalid args.")

# ---------- Core handler ----------
async def _handle_snapshot(args: Dict[str, Any]) -> Dict[str, Any]:
    symbols: List[str] = [str(s).upper() for s in (args.get("symbols") or [])]
    include: List[str] = args.get("include") or []
    options_req: Dict[str, Any] = args.get("options") or {}
    horizon: str = (args.get("horizon") or "intraday").lower()

    errs: Dict[str, Any] = {}
    snapshot: Dict[str, Any] = {"symbols": {}}

    # init providers (non-fatal)
    poly = PolygonMarket() if PolygonMarket else None
    tradier = (TradierMarket or TradierClient)() if (TradierMarket or TradierClient) else None
    market_internals_cache: Optional[Dict[str, Any]] = None

    async def last_price(sym: str) -> Optional[float]:
        # Try Tradier then Polygon (non-fatal)
        if tradier:
            try:
                q = await _maybe_await(tradier.quote_last(sym))
                if q and q.get("price") is not None:
                    return float(q["price"])
            except Exception as e:
                errs[f"{sym}.price.tradier"] = f"{type(e).__name__}: {e}"
        if poly:
            try:
                lt = await _maybe_await(poly.last_trade(sym))
                if lt and lt.get("price") is not None:
                    return float(lt["price"])
            except Exception as e:
                errs[f"{sym}.price.polygon"] = f"{type(e).__name__}: {e}"
        return None

    async def options_top(sym: str, lp: Optional[float]) -> Tuple[List[Dict[str, Any]], Optional[float], Optional[float], Dict[str, Any]]:
        """Return (picks, EM_abs, EM_rel). Always tries to return *something*."""
        picks: List[Dict[str, Any]] = []
        em_abs = None; em_rel = None
        ctx: Dict[str, Any] = {}

        # Normalize options request knobs once for both Polygon and Tradier paths
        odte_flag = bool(options_req.get("odte"))
        try:
            topK = int(options_req.get("topK", 6))
        except Exception:
            topK = 6
        try:
            maxSpreadPct = float(options_req.get("maxSpreadPct", 8 if odte_flag else 12))
        except Exception:
            maxSpreadPct = 12.0
        greeks = bool(options_req.get("greeks", True))
        # Base expiry selection
        expiry = _normalize_expiry(options_req.get("expiry", ("today" if odte_flag else "auto")), horizon)
        # Indices mode: bias to ODTE for intraday when no explicit expiry was provided
        try:
            if (_is_spx(sym) or _is_ndx(sym)) and horizon == "intraday" and not options_req.get("expiry"):
                expiry = _normalize_expiry("today", horizon)
                odte_flag = True
        except Exception:
            pass

        if "options" in include and poly and (not (_is_spx(sym) or _is_ndx(sym))):
            try:
                req = {"topK": topK, "maxSpreadPct": maxSpreadPct, "greeks": greeks, "expiry": expiry}

                # Use Polygon snapshot; provider now supports snapshot_chain alias
                chain = await _maybe_await(poly.snapshot_chain(sym, req))
                # Try to read existing top; else make near-ATM picks from any rows we find
                opts = chain or {}
                raw_top = (opts.get("top") or [])
                # Locate a generic rows list from the response for percentile calcs
                chain_rows = None
                for k in ("rows","contracts","chain","all","snapshot","data","results"):
                    v = opts.get(k)
                    if isinstance(v, list) and v:
                        chain_rows = v
                        break
                # Cache/update IV surface and record liquidity aggregates
                if chain_rows:
                    try:
                        surf = await get_iv_surface(poly, sym, rows=chain_rows, ttl=180, last_price=lp)
                        ctx.setdefault("iv_surface", {"ts": surf.get("ts")})
                    except Exception:
                        pass
                    try:
                        liq = record_chain_aggregates(sym, expiry, chain_rows)
                        if liq:
                            ctx.setdefault("liquidity_trend", liq)
                    except Exception:
                        pass

                if raw_top:
                    picks = raw_top[:topK]
                else:
                        if chain_rows and lp is not None:
                            picks = _near_atm_pairs(chain_rows, lp, topK=topK)
                            # Enforce spread filter when quoted
                            picks = [p for p in picks if (p.get("spread_pct") is None) or (p.get("spread_pct") <= maxSpreadPct)]

                # EM & probabilities if we have picks and last price
                if picks and lp is not None:
                    em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                    if em_abs:
                        # Composite ODTE scoring helper
                        def _odte_composite(r: Dict[str, Any]) -> Optional[float]:
                            try:
                                st = r.get("spread_stability")
                                st_s = float(st) if isinstance(st,(int,float)) else 0.5
                                sp = r.get("spread_pct")
                                sp_s = 1.0 - min(1.0, float(sp or 0.0)/12.0)
                                d = r.get("delta")
                                target = 0.50 if horizon in ("scalp","intraday") else 0.35
                                d_s = 1.0 - min(1.0, abs(abs(float(d or 0.0)) - target))
                                ivp = r.get("iv_percentile")
                                iv_s = 1.0 - min(1.0, abs(float((ivp or 50.0))-50.0)/50.0)
                                oi = float(r.get("oi") or 0.0); vol = float(r.get("volume") or 0.0)
                                liq_s = min(1.0, oi/2000.0 + vol/5000.0)
                                score = st_s*0.30 + d_s*0.30 + iv_s*0.15 + liq_s*0.15 + sp_s*0.10
                                return max(0.0, min(1.0, score))
                            except Exception:
                                return None
                        # Percentiles from chain rows (IV/OI/Volume) if available
                        def _extract_fields(rows: List[Dict[str, Any]]):
                            ivs: List[float] = []
                            ois: List[float] = []
                            vols: List[float] = []
                            for rr in rows:
                                meta = rr.get("options") or {}
                                det  = rr.get("details") or {}
                                g    = rr.get("greeks") or {}
                                exp_r = rr.get("expiry") or rr.get("expiration") or rr.get("expiration_date") or meta.get("expiration_date") or det.get("expiration_date")
                                if str(exp_r) != str(expiry):
                                    continue
                                iv = rr.get("iv") or rr.get("implied_volatility") or g.get("iv") or g.get("mid_iv")
                                oi = rr.get("open_interest")
                                if isinstance(oi, dict):
                                    oi = oi.get("oi")
                                vol = rr.get("volume") or (rr.get("day") or {}).get("volume")
                                try:
                                    if iv is not None: ivs.append(float(iv))
                                except Exception:
                                    pass
                                try:
                                    if oi is not None: ois.append(float(oi))
                                except Exception:
                                    pass
                                try:
                                    if vol is not None: vols.append(float(vol))
                                except Exception:
                                    pass
                            return ivs, ois, vols

                        def _pct_rank(vals: List[float], x: Optional[float]) -> Optional[float]:
                            if x is None or not vals:
                                return None
                            try:
                                xs = sorted([float(v) for v in vals if v is not None])
                                if len(xs) < 5:
                                    return None
                                import bisect
                                i = bisect.bisect_right(xs, float(x))
                                return round(100.0 * i / len(xs), 2)
                            except Exception:
                                return None

                        ivs: List[float] = []
                        ois: List[float] = []
                        vols: List[float] = []
                        def _pick_bucket_iv_list(surface_map, expiry: str, strike: Optional[float], last: Optional[float]) -> List[float]:
                            if not isinstance(surface_map, dict):
                                return []
                            exp_map = surface_map.get(str(expiry)) or {}
                            if not exp_map:
                                return []
                            # choose bucket based on moneyness
                            try:
                                if strike is not None and last is not None and last > 0:
                                    m = abs((float(strike) - float(last))/float(last))
                                    if m <= 0.01 and exp_map.get('atm'): return exp_map['atm']
                                    if m <= 0.03 and exp_map.get('near'): return exp_map['near']
                            except Exception:
                                pass
                            return exp_map.get('all') or []

                        if chain_rows:
                            ivs, ois, vols = _extract_fields(chain_rows)
                            surface_map = None
                            try:
                                # Prefer surface cache when available
                                surf2 = await get_iv_surface(poly, sym, rows=None, ttl=180, last_price=lp)
                                surface_map = (surf2 or {}).get("surface") or {}
                            except Exception:
                                surface_map = None

                        for r in picks:
                            # tradeability may be missing; compute only if engine available
                            ta = None
                            comps = None
                            if tradeability_score:
                                try:
                                    # Add percentiles if possible
                                    bucket_ivs = []
                                    if surface_map is not None:
                                        bucket_ivs = _pick_bucket_iv_list(surface_map, expiry, r.get("strike"), lp)
                                    if bucket_ivs:
                                        r["iv_percentile"] = _pct_rank(bucket_ivs, r.get("iv"))
                                    elif ivs:
                                        r["iv_percentile"] = _pct_rank(ivs, r.get("iv"))
                                    if ois:
                                        r["oi_percentile"] = _pct_rank(ois, r.get("oi"))
                                    if vols:
                                        r["vol_percentile"] = _pct_rank(vols, r.get("volume"))
                                    # ratio proxy
                                    try:
                                        if r.get("oi"):
                                            r["vol_oi_ratio"] = (float(r.get("volume") or 0.0) / float(r.get("oi") or 1.0))
                                    except Exception:
                                        pass
                                    ta, comps = tradeability_score(r, horizon=horizon), None
                                except Exception:
                                    pass
                            try:
                                _attach_display_fields(sym, r)
                            except Exception:
                                pass
                            r["tradeability"] = ta
                            r["hit_probabilities"] = {
                                "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                            }
                            sc = _odte_composite(r)
                            if sc is not None:
                                r["odte_score"] = round(sc*100.0, 1)
                # EM & probabilities if we have picks and last price
                if picks and lp is not None:
                    em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                    # Horizon scaling: convert EM at expiry to EM for the horizon via sqrt(time) rule
                    if em_abs:
                        try:
                            from datetime import date
                            exp_d = date.fromisoformat(str(expiry))
                            today = date.today()
                            days_to_exp = max(0.25, (exp_d - today).days or 0.25)  # at least ~quarter day
                            hours_to_exp = max(1.0, days_to_exp * 6.5)
                            horizon_hours = 2.0 if horizon == "scalp" else 6.5 if horizon == "intraday" else None
                            if horizon_hours and hours_to_exp > 0:
                                scale = (horizon_hours / hours_to_exp) ** 0.5
                                em_abs = em_abs * scale
                                em_rel = em_abs / lp if lp else em_rel
                        except Exception:
                            pass
                        for r in picks:
                            # tradeability may be missing; compute only if engine available
                            ta = None
                            if tradeability_score:
                                try:
                                    # Percentiles from chain rows already computed above
                                    ta = tradeability_score(r, horizon=horizon)
                                except Exception:
                                    pass
                            r["tradeability"] = ta
                            r["hit_probabilities"] = {
                                "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                            }
                            # EV estimate for ranking (optional)
                            if expected_value_intraday:
                                try:
                                    ev, bd = expected_value_intraday(r, lp, em_abs, horizon=horizon)
                                    r["ev"] = {"dollars": ev, "pct": (ev/(max(1e-6, ((r.get('bid') or 0)+(r.get('ask') or 0))/2.0)) if (r.get('bid') is not None and r.get('ask') is not None) else None)}
                                    r["ev_detail"] = bd
                                except Exception:
                                    pass
                            # Attach chart URL for quick visualization
                            try:
                                r["chart_url"] = _chart_url(
                                    sym,
                                    lp,
                                    em_abs,
                                    em_rel,
                                    r,
                                    horizon,
                                    r.get("hit_probabilities") or {},
                                    key_levels=key_levels_data,
                                    fibs=fib_data,
                                )
                            except Exception:
                                pass

                        # Short NBBO sampling to estimate spread stability and refresh quotes
                        async def _nbbo_sample(picks: List[Dict[str, Any]], samples: int = 2, interval: float = 0.35) -> Optional[Dict[str, Any]]:
                            symbols = [p.get("symbol") for p in picks if p.get("symbol")]
                            if not symbols:
                                return None
                            # Build symbol -> index mapping and storage
                            idx = {p.get("symbol"): i for i, p in enumerate(picks) if p.get("symbol")}
                            bids: Dict[str, List[float]] = {s: [] for s in symbols}
                            asks: Dict[str, List[float]] = {s: [] for s in symbols}
                            mids: Dict[str, List[float]] = {s: [] for s in symbols}
                            spreads: Dict[str, List[float]] = {s: [] for s in symbols}
                            for _ in range(samples):
                                qs = await asyncio.gather(*[
                                    _maybe_await(poly.option_quote(s)) for s in symbols
                                ], return_exceptions=True)
                                for s, q in zip(symbols, qs):
                                    if isinstance(q, dict):
                                        b = q.get("bid"); a = q.get("ask")
                                        if b is not None: bids[s].append(b)
                                        if a is not None: asks[s].append(a)
                                        if b is not None and a is not None and a > 0:
                                            try:
                                                mids[s].append((float(b) + float(a)) / 2.0)
                                                spreads[s].append(max(0.0, float(a) - float(b)))
                                            except Exception:
                                                pass
                                        # refresh latest nbbo fields on pick
                                        i = idx.get(s)
                                        if i is not None:
                                            if q.get("bid") is not None: picks[i]["bid"] = q.get("bid")
                                            if q.get("ask") is not None: picks[i]["ask"] = q.get("ask")
                                            sp = q.get("spread_pct")
                                            if sp is not None: picks[i]["spread_pct"] = sp
                                await asyncio.sleep(interval)
                            # Compute spread stability, tradeability, and distilled order-flow
                            summary: Dict[str, Any] = {
                                "symbols": {},
                                "bias_counts": {"buyers": 0, "sellers": 0, "neutral": 0},
                                "avg_score": None,
                                "dominant_bias": None,
                            }
                            scores: List[float] = []
                            for s in symbols:
                                i = idx.get(s)
                                if i is None:
                                    continue
                                st = _spread_stability(bids[s], asks[s]) if bids.get(s) and asks.get(s) else None
                                picks[i]["spread_stability"] = st
                                if tradeability_score:
                                    try:
                                        picks[i]["tradeability"] = tradeability_score(picks[i], horizon=horizon)
                                    except Exception:
                                        pass
                                bid_vals = bids.get(s) or []
                                ask_vals = asks.get(s) or []
                                mid_vals = mids.get(s) or []
                                spread_vals = spreads.get(s) or []
                                def _first_last(vals: List[float]) -> Tuple[Optional[float], Optional[float]]:
                                    if not vals:
                                        return None, None
                                    return vals[0], vals[-1]
                                bid_start, bid_end = _first_last(bid_vals)
                                ask_start, ask_end = _first_last(ask_vals)
                                mid_start, mid_end = _first_last(mid_vals)
                                spread_start, spread_end = _first_last(spread_vals)
                                mid_diff = None
                                rel_mid = None
                                if mid_start is not None and mid_end is not None:
                                    mid_diff = mid_end - mid_start
                                    base = abs(mid_start) if abs(mid_start) > 1e-4 else 1.0
                                    rel_mid = mid_diff / base
                                bid_delta = None
                                if bid_start is not None and bid_end is not None:
                                    bid_delta = bid_end - bid_start
                                ask_delta = None
                                if ask_start is not None and ask_end is not None:
                                    ask_delta = ask_start - ask_end  # ask coming in (lower) helps buyers
                                spread_delta = None
                                if spread_start is not None and spread_end is not None:
                                    spread_delta = spread_end - spread_start

                                score = 0.0
                                components: List[float] = []
                                if rel_mid is not None:
                                    components.append(max(-1.0, min(1.0, rel_mid)))
                                if bid_delta is not None and bid_start not in (None, 0):
                                    try:
                                        components.append(max(-1.0, min(1.0, (bid_delta / max(0.05, abs(bid_start))) * 0.5)))
                                    except Exception:
                                        pass
                                if ask_delta is not None and ask_start not in (None, 0):
                                    try:
                                        components.append(max(-1.0, min(1.0, (ask_delta / max(0.05, abs(ask_start))) * 0.5)))
                                    except Exception:
                                        pass
                                if spread_delta is not None and spread_start is not None:
                                    try:
                                        components.append(max(-1.0, min(1.0, (-(spread_delta) / max(0.05, spread_start + 0.01)) * 0.3)))
                                    except Exception:
                                        pass
                                if components:
                                    score = sum(components) / len(components)
                                score = max(-1.0, min(1.0, score))
                                bias = "neutral"
                                if score >= 0.18:
                                    bias = "buyers"
                                elif score <= -0.18:
                                    bias = "sellers"
                                summary["bias_counts"][bias] += 1
                                scores.append(score)
                                picks[i]["order_flow_score"] = round(score, 3)
                                picks[i]["order_flow_bias"] = bias
                                if mid_diff is not None:
                                    picks[i]["order_flow_mid_change"] = round(mid_diff, 4)
                                if bid_delta is not None:
                                    picks[i]["order_flow_bid_change"] = round(bid_delta, 4)
                                if ask_delta is not None:
                                    picks[i]["order_flow_ask_change"] = round(ask_delta, 4)
                                if spread_delta is not None:
                                    picks[i]["order_flow_spread_change"] = round(spread_delta, 4)
                                summary["symbols"][s] = {
                                    "score": round(score, 3),
                                    "bias": bias,
                                    "mid_change": round(mid_diff, 4) if mid_diff is not None else None,
                                    "bid_change": round(bid_delta, 4) if bid_delta is not None else None,
                                    "ask_change": round(ask_delta, 4) if ask_delta is not None else None,
                                    "spread_change": round(spread_delta, 4) if spread_delta is not None else None,
                                    "samples": len(mid_vals) or len(bid_vals) or len(ask_vals),
                                }
                            if scores:
                                avg_score = sum(scores) / len(scores)
                                summary["avg_score"] = round(avg_score, 3)
                                try:
                                    dominant_bias = max(summary["bias_counts"].items(), key=lambda kv: kv[1])
                                    if dominant_bias[1] and dominant_bias[1] >= max(2, len(scores) // 2 + 1):
                                        summary["dominant_bias"] = dominant_bias[0]
                                except Exception:
                                    pass
                            return summary

                        # Limit sampling scope to avoid latency explosion
                        try:
                            nbbo_snapshot = await _nbbo_sample(picks[:min(len(picks), max(4, int(topK)))], samples=2, interval=0.35)
                            if nbbo_snapshot:
                                ctx.setdefault("order_flow", {}).update(nbbo_snapshot)
                        except Exception:
                            pass
                        # Tighten gates and rank for ODTE/scalp
                        try:
                            if odte_flag or horizon == "scalp":
                                picks = [p for p in picks if (p.get("spread_stability") is None) or (p.get("spread_stability") >= 0.6)]
                                picks.sort(key=lambda x: x.get("odte_score", -1), reverse=True)
                        except Exception:
                            pass
                        # Tighten quality gates for ODTE/scalp: require spread stability ≥ 0.6 when available
                        try:
                            if odte_flag or horizon == "scalp":
                                picks = [p for p in picks if (p.get("spread_stability") is None) or (p.get("spread_stability") >= 0.6)]
                        except Exception:
                            pass
            except Exception as e:
                errs[f"{sym}.options"] = f"{type(e).__name__}: {e}"

            # Fallback: if no picks from Polygon, try Tradier options chain
            if not picks and "options" in include:
                try:
                    # Import lazily to avoid hard dependency
                    from importlib import import_module as _im2
                    tc_mod = _im2("app.services.providers.tradier_chain")
                    tc_fn = getattr(tc_mod, "options_chain", None)
                    if callable(tc_fn):
                        trows = await _maybe_await(tc_fn(sym, expiry=expiry, greeks=greeks))
                        if trows and lp is not None:
                            picks = _near_atm_pairs(trows, lp, topK=topK)
                            picks = [p for p in picks if (p.get("spread_pct") is None) or (p.get("spread_pct") <= maxSpreadPct)]
                            if picks:
                                # Percentiles for Tradier rows
                                def _vals(rows, key):
                                    out = []
                                    for rr in rows:
                                        try:
                                            v = rr.get(key)
                                            if key == 'iv':
                                                v = v or (rr.get('greeks') or {}).get('mid_iv') or (rr.get('greeks') or {}).get('iv')
                                            if v is not None:
                                                out.append(float(v))
                                        except Exception:
                                            pass
                                    return out
                                tivs = _vals(trows, 'iv'); tois = _vals(trows, 'open_interest'); tvols = _vals(trows, 'volume')
                                def _pct_rank2(vals: List[float], x: Optional[float]) -> Optional[float]:
                                    try:
                                        return _pct_rank_surface(vals, x)
                                    except Exception:
                                        return None
                                em_abs, em_rel = _simple_em_from_straddle(lp, picks)
                                if em_abs:
                                    # Apply same horizon scaling to fallback EM
                                    try:
                                        from datetime import date
                                        exp_d = date.fromisoformat(str(expiry))
                                        today = date.today()
                                        days_to_exp = max(0.25, (exp_d - today).days or 0.25)
                                        hours_to_exp = max(1.0, days_to_exp * 6.5)
                                        horizon_hours = 2.0 if horizon == "scalp" else 6.5 if horizon == "intraday" else None
                                        if horizon_hours and hours_to_exp > 0:
                                            scale = (horizon_hours / hours_to_exp) ** 0.5
                                            em_abs = em_abs * scale
                                            em_rel = em_abs / lp if lp else em_rel
                                    except Exception:
                                        pass
                                    for r in picks:
                                        # Attach percentiles + ratio for scoring
                                        if tivs:
                                            r["iv_percentile"] = _pct_rank2(tivs, r.get("iv"))
                                        if tois:
                                            r["oi_percentile"] = _pct_rank2(tois, r.get("oi"))
                                        if tvols:
                                            r["vol_percentile"] = _pct_rank2(tvols, r.get("volume"))
                                        try:
                                            if r.get("oi"):
                                                r["vol_oi_ratio"] = (float(r.get("volume") or 0.0) / float(r.get("oi") or 1.0))
                                        except Exception:
                                            pass
                                        ta = None
                                        if tradeability_score:
                                            try:
                                                ta = tradeability_score(r, horizon=horizon)
                                            except Exception:
                                                pass
                                        try:
                                            _attach_display_fields(sym, r)
                                        except Exception:
                                            pass
                                        r["tradeability"] = ta
                                        r["hit_probabilities"] = {
                                            "tp1": _p_touch(em_abs*0.25, em_abs) if em_abs else None,
                                            "tp2": _p_touch(em_abs*0.50, em_abs) if em_abs else None,
                                        }
                                        if expected_value_intraday:
                                            try:
                                                ev, bd = expected_value_intraday(r, lp, em_abs, horizon=horizon)
                                                r["ev"] = {"dollars": ev, "pct": (ev/(max(1e-6, ((r.get('bid') or 0)+(r.get('ask') or 0))/2.0)) if (r.get('bid') is not None and r.get('ask') is not None) else None)}
                                                r["ev_detail"] = bd
                                            except Exception:
                                                pass
                                        # Attach chart URL as well (fallback path)
                                        try:
                                            r["chart_url"] = _chart_url(
                                                sym,
                                                lp,
                                                em_abs,
                                                em_rel,
                                                r,
                                                horizon,
                                                r.get("hit_probabilities") or {},
                                                key_levels=key_levels_data,
                                                fibs=fib_data,
                                            )
                                        except Exception:
                                            pass
                                # NBBO sampling on fallback too
                                try:
                                    nbbo_snapshot = await _nbbo_sample(picks[:min(len(picks), max(4, int(topK)))], samples=2, interval=0.35)
                                    if nbbo_snapshot:
                                        ctx.setdefault("order_flow", {}).update(nbbo_snapshot)
                                except Exception:
                                    pass
                                # Tighten quality gates for ODTE/scalp
                                try:
                                    if options_req.get("odte") or horizon == "scalp":
                                        picks = [p for p in picks if (p.get("spread_stability") is None) or (p.get("spread_stability") >= 0.6)]
                                except Exception:
                                    pass
                except Exception as e:
                    errs[f"{sym}.options.tradier_fallback"] = f"{type(e).__name__}: {e}"
            # For index underlyings, prefer Tradier and emit a clear limitation if still empty
            if (_is_spx(sym) or _is_ndx(sym)) and not picks:
                ctx["index_note"] = "Index options depend on brokerage provider; no chain returned."

        return picks, em_abs, em_rel, ctx

    def _odte_strategies(sym: str, picks: List[Dict[str, Any]], em_abs: Optional[float], expiry: str) -> List[Dict[str, Any]]:
        """Compose simple 0DTE debit spread scalps from high-quality picks.
        - Buy near-ATM (~0.5Δ) call/put and sell the next strike OTM to reduce cost.
        - Only include when spreads are tight and liquidity is healthy.
        """
        if not picks or em_abs is None:
            return []
        def mid(x):
            b, a = x.get("bid"), x.get("ask")
            if b is None or a is None or a <= 0:
                return None
            return (b + a)/2.0
        out: List[Dict[str, Any]] = []
        def select_leg(kind: str):
            # filter by type and iv/liquidity/spread
            side = [p for p in picks if p.get("type") == kind]
            best = []
            for p in side:
                sp = p.get("spread_pct")
                if sp is None or sp > 8.0:
                    continue
                ivp = p.get("iv_percentile")
                if ivp is not None and (ivp < 10 or ivp > 90):
                    continue
                if (p.get("oi") or 0) < 200 and (p.get("volume") or 0) < 200:
                    continue
                d = p.get("delta")
                try:
                    if d is None:
                        continue
                    if kind == "call":
                        score = 1.0 - abs(abs(float(d)) - 0.5)
                    else:
                        score = 1.0 - abs(abs(float(d)) - 0.5)
                except Exception:
                    score = 0.0
                best.append((score, p))
            best.sort(key=lambda x: x[0], reverse=True)
            return best[0][1] if best else None
        def next_strike(kind: str, base_strike: float):
            # Choose nearest OTM strike from picks
            cands = [p for p in picks if p.get("type") == kind and isinstance(p.get("strike"),(int,float))]
            if kind == "call":
                cands = [p for p in cands if p["strike"] > base_strike]
                cands.sort(key=lambda p: p["strike"])  # nearest above
            else:
                cands = [p for p in cands if p["strike"] < base_strike]
                cands.sort(key=lambda p: p["strike"], reverse=True)  # nearest below
            return cands[0] if cands else None

        for kind in ("call", "put"):
            buy = select_leg(kind)
            if not buy:
                continue
            sell = next_strike(kind, float(buy.get("strike") or 0))
            if not sell:
                continue
            buy_mid = mid(buy); sell_mid = mid(sell)
            if buy_mid is None or sell_mid is None:
                continue
            width = abs(float(sell["strike"]) - float(buy["strike"]))
            debit = max(0.0, buy_mid - sell_mid)
            max_profit = max(0.0, width - debit)
            strat = {
                "name": f"0DTE {kind.capitalize()} Debit Spread",
                "underlying": sym,
                "expiry": expiry,
                "legs": [
                    {"action": "BUY",  "type": kind, "strike": buy.get("strike"),  "symbol": buy.get("symbol")},
                    {"action": "SELL", "type": kind, "strike": sell.get("strike"), "symbol": sell.get("symbol")},
                ],
                "est_entry": round(debit, 2),
                "est_width": round(width, 2),
                "max_loss_est": round(debit, 2),
                "max_profit_est": round(max_profit, 2),
            }
            out.append(strat)
        return out

    for sym in symbols:
        out: Dict[str, Any] = {}
        lp = await last_price(sym)
        if lp is not None:
            out.setdefault("price", {})["last"] = lp

        levels_payload: Optional[Dict[str, Any]] = None
        key_levels_data: Optional[Dict[str, Any]] = None
        fib_data: Optional[Dict[str, Any]] = None
        pivots_data: Optional[Dict[str, Any]] = None
        prev_day_data: Optional[Dict[str, Any]] = None
        levels_session: Optional[str] = None

        picks, em_abs, em_rel, opt_ctx = await options_top(sym, lp)
        if picks:
            out.setdefault("options", {})["top"] = picks
            # 0DTE strategies for scalp horizon (A+ only)
            try:
                if horizon == "scalp":
                    # Build strategies using normalized expiry 'today' if user asked; else use detected expiry from options request or context
                    # Try to infer expiry from first pick symbol if available
                    first_exp = None
                    try:
                        for p in picks:
                            if p.get("symbol"):
                                # OCC parse exists in providers; quick parse here for YYMMDD
                                import re
                                m = re.search(r"\d{6}", p["symbol"]) if isinstance(p["symbol"], str) else None
                                if m:
                                    s = m.group(0)
                                    first_exp = f"20{s[0:2]}-{s[2:4]}-{s[4:6]}"; break
                    except Exception:
                        first_exp = None
                    ex = first_exp or _normalize_expiry("today", horizon)
                    strats = _odte_strategies(sym, picks, em_abs, ex)
                    if strats:
                        out.setdefault("options", {})["strategies"] = strats
            except Exception:
                pass
        providers_info = {"polygon": bool(PolygonMarket), "tradier": bool(TradierMarket or TradierClient)}
        if em_abs is not None:
            out.setdefault("context", {})["expected_move"] = {"abs": em_abs, "rel": em_rel}
        if opt_ctx:
            out.setdefault("context", {}).update(opt_ctx)

        if poly:
            try:
                # Intraday metrics (VWAP, sigma, RVOL)
                try:
                    mins = await poly.minute_bars_today(sym)
                    vwap, sig_tp = _vwap_sig(mins)
                    rvol5 = _rvol5(mins)
                    out.setdefault("context", {}).setdefault("intraday", {})
                    intr = out["context"]["intraday"]
                    if vwap is not None:
                        intr["vwap"] = vwap
                    if sig_tp is not None:
                        intr["sigma_tp"] = sig_tp
                    if rvol5 is not None:
                        intr["rvol5"] = rvol5
                except Exception:
                    pass
                lpayload = await market_compute_levels(poly, sym)
                if lpayload and lpayload.get("ok"):
                    levels_payload = lpayload
                    key_levels_data = lpayload.get("key_levels")
                    fib_data = lpayload.get("fibonacci")
                    pivots_data = lpayload.get("pivots")
                    prev_day_data = lpayload.get("prev_day")
                    levels_session = lpayload.get("session_date_utc")
                    levels_source = lpayload.get("levels_source")
            except Exception:
                levels_payload = None

        ctx_ref = out.setdefault("context", {})
        if key_levels_data:
            ctx_ref["key_levels"] = key_levels_data
        if fib_data:
            ctx_ref["fibonacci"] = fib_data
        if pivots_data:
            ctx_ref["pivots"] = pivots_data
        if prev_day_data:
            ctx_ref["prev_day_levels"] = prev_day_data
        if levels_session:
            ctx_ref["levels_session_utc"] = levels_session
        if poly:
            try:
                if market_internals_cache is None:
                    market_internals_cache = await _market_internals_summary(poly)
            except Exception:
                pass
        if market_internals_cache:
            try:
                ctx_ref["market_internals"] = dict(market_internals_cache)
            except Exception:
                ctx_ref["market_internals"] = market_internals_cache
        try:
            if levels_payload:
                src = levels_payload.get("levels_source")
                if src and str(src).upper() != sym.upper():
                    ctx_ref["levels_source"] = src
                    ctx_ref["index_proxy_note"] = f"Levels computed via {src} proxy"
        except Exception:
            pass

        # Attach premarket webinar context (if a Feature row exists for today)
        try:
            async with SessionLocal() as s:
                # Prefer per-symbol feature, then wildcard "*"
                stmt = (
                    select(Feature)
                    .where(Feature.horizon == "premarket")
                    .where(Feature.symbol.in_([sym, "*"]))
                    .order_by(desc(Feature.created_at))
                    .limit(1)
                )
                res = await s.execute(stmt)
                feat = res.scalars().first()
                if feat and isinstance(feat.payload, dict):
                    ctx_ref["premarket"] = feat.payload
        except Exception:
            pass
        # Phase 5: simple risk flags
        picks_local = (out.get("options") or {}).get("top") or []
        liq_trend = (out.get("context") or {}).get("liquidity_trend")
        out.setdefault("context", {})["risk_flags"] = compute_risk_flags(picks_local, liq_trend, providers_info)

        if "levels" in include:
            if levels_payload and levels_payload.get("ok"):
                levels_obj = {
                    k: levels_payload.get(k)
                    for k in ("prev_day", "pivots", "key_levels", "fibonacci", "session_date_utc")
                    if levels_payload.get(k) is not None
                }
                out["levels"] = levels_obj
            else:
                out.setdefault("levels", {})

        snapshot["symbols"][sym] = out

    return {"ok": True, "snapshot": snapshot, "errors": errs}
