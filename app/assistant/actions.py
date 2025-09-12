from __future__ import annotations

from typing import Any, Callable, Dict, List, Literal, Optional
from pydantic import BaseModel, Field, ValidationError
from datetime import date

# Import your domain functions directly (no HTTP roundtrips)
from app.services.options_live_tradier import (
    pick_live_contracts_tradier,
    fetch_expirations as _fetch_expirations,
    fetch_chain as _fetch_chain,
)

# ---------- Request models ----------
Side = Literal["long_call","long_put","short_call","short_put"]
Horizon = Literal["intra","day","week"]

class OptionsPickArgs(BaseModel):
    symbol: str = Field(..., description="Underlying ticker, e.g. SPY, AAPL")
    side: Side
    horizon: Horizon = "intra"
    n: int = Field(5, ge=1, le=10)

class OptionsExpirationsArgs(BaseModel):
    symbol: str

class OptionsChainArgs(BaseModel):
    symbol: str
    expiration: date
    side: Optional[Literal["call","put"]] = None
    limit: int = Field(1000, ge=1, le=2000)

# ---------- Exec handlers ----------
def _op_options_pick(args: OptionsPickArgs) -> Dict[str, Any]:
    return pick_live_contracts_tradier(args.symbol, args.side, args.horizon, args.n)

def _op_options_expirations(args: OptionsExpirationsArgs) -> Dict[str, Any]:
    exps = _fetch_expirations(args.symbol)
    return {"ok": True, "symbol": args.symbol.upper(), "expirations": [d.isoformat() for d in exps]}

def _op_options_chain(args: OptionsChainArgs) -> Dict[str, Any]:
    items = _fetch_chain(args.symbol, args.expiration)
    # normalize + filter + cap
    items = items if isinstance(items, list) else []
    if args.side:
        items = [o for o in items if (o.get("option_type") or "").lower() == args.side]
    if len(items) > args.limit:
        items = items[:args.limit]
    norm = []
    for o in items:
        strike = o.get("strike")
        try:
            strike = float(strike) if strike not in (None, "na") else None
        except Exception:
            strike = None
        norm.append({
            "symbol": o.get("symbol"),
            "option_type": (o.get("option_type") or "").lower() or None,
            "strike": strike,
            "expiration": args.expiration.isoformat(),
            "volume": o.get("volume"),
            "open_interest": o.get("open_interest"),
        })
    return {"ok": True, "symbol": args.symbol.upper(), "expiration": args.expiration.isoformat(), "count": len(norm), "items": norm}

# ---------- Registry ----------
class ActionSpec(BaseModel):
    op: str
    title: str
    description: str
    args_model: type[BaseModel]

REGISTRY: Dict[str, ActionSpec] = {
    "options.pick": ActionSpec(
        op="options.pick",
        title="Pick closest-to-ATM options (delayed)",
        description="Return N contracts nearest to ATM for a ticker/side/horizon using Tradier Sandbox.",
        args_model=OptionsPickArgs,
    ),
    "options.expirations": ActionSpec(
        op="options.expirations",
        title="List option expirations (delayed)",
        description="Return available expirations for a ticker using Tradier Sandbox.",
        args_model=OptionsExpirationsArgs,
    ),
    "options.chain": ActionSpec(
        op="options.chain",
        title="Get options chain (delayed)",
        description="Return option contracts for a ticker+expiration (optionally filtered by call/put) using Tradier Sandbox.",
        args_model=OptionsChainArgs,
    ),
}

# ---------- Public API for router ----------
def list_actions() -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for op, spec in REGISTRY.items():
        schema = spec.args_model.model_json_schema()
        out.append({
            "op": op,
            "title": spec.title,
            "description": spec.description,
            "args_schema": schema,
            "stable": True,  # marker for GPT prompts
            "id": op,       # duplicate key for convenience
        })
    return out

def execute_action(op: str, args: Dict[str, Any]) -> Dict[str, Any]:
    if op not in REGISTRY:
        return {"ok": False, "error": "unknown_op", "detail": f"Unknown op '{op}'"}
    spec = REGISTRY[op]
    # validate args with pydantic
    try:
        parsed = spec.args_model.model_validate(args)
    except ValidationError as ve:
        return {"ok": False, "error": "validation_error", "detail": ve.errors()}
    # dispatch
    if op == "options.pick":
        return _op_options_pick(parsed)
    if op == "options.expirations":
        return _op_options_expirations(parsed)
    if op == "options.chain":
        return _op_options_chain(parsed)
    return {"ok": False, "error": "unimplemented", "detail": op}
# === Assistant adapters for core endpoints (HTTP loopback) ===
import os, json, urllib.request
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

# NOTE: REGISTRY and ActionSpec are already defined earlier in this file by your options.* code.

def _http_json(method: str, path: str, body: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Minimal HTTP JSON helper that calls this same app via 127.0.0.1 and returns parsed JSON.
    Keeps behavior consistent with your existing REST responses.
    """
    base = f"http://127.0.0.1:{os.environ.get('PORT','8000')}"
    url = base + path
    headers = {"content-type":"application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return json.loads(resp.read().decode("utf-8"))

# -------- plan.validate --------
class PlanValidateArgs(BaseModel):
    symbol: str
    side: str = Field(pattern="^(long|short)$")
    entry: float
    stop: float
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    time_stop_min: Optional[int] = 10

def _plan_validate_handler(**kw) -> Dict[str, Any]:
    args = PlanValidateArgs(**kw).model_dump()
    return _http_json("POST","/api/v1/plan/validate", args)

REGISTRY["plan.validate"] = ActionSpec(
    op="plan.validate",
    title="Validate a trade plan",
    description="Risk, targets, sanity notes",
    args_model=PlanValidateArgs,
    handler=_plan_validate_handler,
)

# -------- sizing.suggest --------
class SizingSuggestArgs(BaseModel):
    symbol: str
    side: str = Field(pattern="^(long|short)$")
    risk_R: float
    per_unit_risk: Optional[float] = None

def _sizing_suggest_handler(**kw) -> Dict[str, Any]:
    args = SizingSuggestArgs(**kw).model_dump()
    return _http_json("POST","/api/v1/sizing/suggest", args)

REGISTRY["sizing.suggest"] = ActionSpec(
    op="sizing.suggest",
    title="Suggest position size",
    description="Position size given risk constraints",
    args_model=SizingSuggestArgs,
    handler=_sizing_suggest_handler,
)

# -------- screener.watchlist_get --------
class ScreenerNoneArgs(BaseModel):
    pass


def _screener_watchlist_get_handler(**kw) -> Dict[str, Any]:
    return _http_json("GET","/api/v1/screener/watchlist/get")

REGISTRY["screener.watchlist_get"] = ActionSpec(
    op="screener.watchlist_get",
    title="Get watchlist symbols",
    description="Default symbols universe",
    args_model=ScreenerNoneArgs,
    handler=_screener_watchlist_get_handler,
)

# -------- screener.watchlist_ranked --------
def _screener_watchlist_ranked_handler(**kw) -> Dict[str, Any]:
    return _http_json("GET","/api/v1/screener/watchlist/ranked")

REGISTRY["screener.watchlist_ranked"] = ActionSpec(
    op="screener.watchlist_ranked",
    title="Get ranked picks",
    description="Ranked watchlist (context-aware)",
    args_model=ScreenerNoneArgs,
    handler=_screener_watchlist_ranked_handler,
)

# --- Registry-driven dispatcher override (placed at end of this file) ---
# This definition replaces any earlier execute_action imported by the router.

from typing import Any, Dict
from pydantic import ValidationError

def execute_action(op: str, raw_args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generic executor:
      - looks up REGISTRY[op]
      - validates raw_args with args_model (if present)
      - calls handler(**validated_args)
    Falls back to explicit 400-style validation errors so GPT can self-correct.
    """
    spec = REGISTRY.get(op)
    if not spec:
        # Keep prior behavior explicit for unknown ops
        return {"ok": False, "error": "unknown_op", "detail": op}

    model = getattr(spec, "args_model", None)
    try:
        args = raw_args or {}
        if model:
            parsed = model(**args)
            args = parsed.model_dump()
        handler = getattr(spec, "handler", None)
        if not handler:
            return {"ok": False, "error": "missing_handler", "detail": op}
        out = handler(**args) if args else handler()
        # Normalize simple truthy responses
        if isinstance(out, dict):
            return out
        return {"ok": True, "data": out}
    except ValidationError as ve:
        return {"ok": False, "error": "validation_error", "detail": ve.errors()}
    except TypeError as te:
        # arg name mismatch or stray kwargs
        return {"ok": False, "error": "type_error", "detail": str(te)}
    except Exception as e:
        return {"ok": False, "error": "exec_error", "detail": str(e)}

# ===== Assistant Adapter Layer (non-destructive overlay) =====
# This block keeps the legacy behavior and augments it with additional ops
# without relying on ActionSpec having a 'handler' field.

import os, json, urllib.request, urllib.parse
from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field, ValidationError

# --- Capture legacy hooks if present (so we can delegate) ---
try:
    _LEGACY_LIST_ACTIONS = list_actions   # type: ignore[name-defined]
except Exception:
    _LEGACY_LIST_ACTIONS = None

try:
    _LEGACY_EXECUTE_ACTION = execute_action  # type: ignore[name-defined]
except Exception:
    _LEGACY_EXECUTE_ACTION = None

# --- Small HTTP helper to call our own REST endpoints (loopback) ---
def _http_json(method: str, path: str, body: Optional[Dict[str, Any]] = None, query: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    base = f"http://127.0.0.1:{os.environ.get('PORT','8000')}"
    if query:
        q = urllib.parse.urlencode({k:v for k,v in query.items() if v is not None})
        path = f"{path}?{q}"
    url = base + path
    headers = {"content-type":"application/json"}
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))

# --- Args Models for new ops ---
class PlanValidateArgs(BaseModel):
    symbol: str
    side: str = Field(pattern="^(long|short)$")
    entry: float
    stop: float
    tp1: Optional[float] = None
    tp2: Optional[float] = None
    time_stop_min: Optional[int] = 10

class SizingSuggestArgs(BaseModel):
    symbol: str
    side: str = Field(pattern="^(long|short)$")
    risk_R: float
    per_unit_risk: Optional[float] = None

class ScreenerNoneArgs(BaseModel):
    pass


class PlaceOrderArgs(BaseModel):
    symbol: str
    quantity: int = Field(gt=0)
    side: Literal["buy", "sell"]
    order_type: Literal["market", "limit"] = "market"
    limit_price: Optional[float] = None
    preview: bool = True

# --- Handlers using loopback to your current REST routes ---
def _h_plan_validate(**kw) -> Dict[str, Any]:
    args = PlanValidateArgs(**kw).model_dump()
    return _http_json("POST", "/api/v1/plan/validate", body=args)

def _h_sizing_suggest(**kw) -> Dict[str, Any]:
    args = SizingSuggestArgs(**kw).model_dump()
    return _http_json("POST", "/api/v1/sizing/suggest", body=args)

def _h_screener_watchlist_get(**kw) -> Dict[str, Any]:
    _ = ScreenerNoneArgs(**(kw or {}))
    return _http_json("GET", "/api/v1/screener/watchlist/get")

def _h_screener_watchlist_ranked(**kw) -> Dict[str, Any]:
    _ = ScreenerNoneArgs(**(kw or {}))
    return _http_json("GET", "/api/v1/screener/watchlist/ranked")

def _h_broker_place_order(**kw) -> Dict[str, Any]:
    args = PlaceOrderArgs(**kw).model_dump()
    return _http_json("POST", "/api/v1/broker/tradier/order", body=args)

# Registry for new ops (independent of ActionSpec)
_ASSISTANT_EXTRA_OPS: Dict[str, Dict[str, Any]] = {
    "plan.validate": {
        "title": "Validate a trade plan",
        "description": "Risk, targets, sanity notes",
        "args_model": PlanValidateArgs,
        "handler": _h_plan_validate,
    },
    "sizing.suggest": {
        "title": "Suggest position size",
        "description": "Position size given risk constraints",
        "args_model": SizingSuggestArgs,
        "handler": _h_sizing_suggest,
    },
    "screener.watchlist_get": {
        "title": "Get watchlist symbols",
        "description": "Default symbols universe",
        "args_model": ScreenerNoneArgs,
        "handler": _h_screener_watchlist_get,
    },
    "screener.watchlist_ranked": {
        "title": "Get ranked picks",
        "description": "Ranked watchlist (context-aware)",
        "args_model": ScreenerNoneArgs,
        "handler": _h_screener_watchlist_ranked,
    },
    "broker.place_order": {
        "title": "Place order via Tradier sandbox",
        "description": "Preview or place an order using Tradier",
        "args_model": PlaceOrderArgs,
        "handler": _h_broker_place_order,
    },
}

def _extra_actions_schema() -> List[Dict[str, Any]]:
    out = []
    for op, meta in _ASSISTANT_EXTRA_OPS.items():
        model = meta["args_model"]
        schema = model.model_json_schema()
        out.append({
            "op": op,
            "title": meta["title"],
            "description": meta.get("description",""),
            "args_schema": schema,
            "stable": True,
            "id": op,
        })
    return out

# --- Merge discovery: legacy + extra ---
def list_actions() -> Dict[str, Any]:
    legacy = []
    try:
        if callable(_LEGACY_LIST_ACTIONS):
            lr = _LEGACY_LIST_ACTIONS()
            if isinstance(lr, dict) and "actions" in lr:
                legacy = lr["actions"]
    except Exception:
        legacy = []
    return {"ok": True, "actions": legacy + _extra_actions_schema()}

# --- Unified executor: try extra first, then legacy ---
def execute_action(op: str, raw_args: Dict[str, Any]) -> Dict[str, Any]:
    meta = _ASSISTANT_EXTRA_OPS.get(op)
    if meta:
        model = meta["args_model"]
        try:
            parsed = model(**(raw_args or {}))
            args = parsed.model_dump()
            out = meta["handler"](**args)
            if isinstance(out, dict):
                return out
            return {"ok": True, "data": out}
        except ValidationError as ve:
            return {"ok": False, "error": "validation_error", "detail": ve.errors()}
        except Exception as e:
            return {"ok": False, "error": "exec_error", "detail": str(e)}

    # fallback to legacy behavior (options.* and whatever else existed before)
    if callable(_LEGACY_EXECUTE_ACTION):
        try:
            return _LEGACY_EXECUTE_ACTION(op, raw_args or {})
        except Exception as e:
            return {"ok": False, "error": "exec_error", "detail": str(e)}

    return {"ok": False, "error": "unknown_op", "detail": op}
