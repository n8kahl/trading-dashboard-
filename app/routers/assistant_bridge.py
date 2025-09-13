from fastapi import APIRouter, HTTPException, Request
import os, httpx

router = APIRouter(prefix="/api/v1/assistant")

# If myGPT calls a different Railway URL, set this to *your* public URL.
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
if not PUBLIC_BASE_URL:
    # default to same origin (works when myGPT and API share domain or you call internally)
    PUBLIC_BASE_URL = ""

# --- Manifest for myGPT (what ops exist) ---
OPS = {
    # Alerts
    "alerts.set":     {"method": "POST", "path": "/api/v1/alerts/set", "mode": "json"},
    "alerts.list":    {"method": "GET",  "path": "/api/v1/alerts/list", "mode": None},

    # Market stream
    "stream.start":   {"method": "POST", "path": "/api/v1/market/stream/start", "mode": "json"},
    "stream.status":  {"method": "GET",  "path": "/api/v1/market/stream/status", "mode": None},
    "stream.snapshot":{"method": "GET",  "path": "/api/v1/market/stream/snapshot", "mode": None},
    "stream.stop":    {"method": "POST", "path": "/api/v1/market/stream/stop", "mode": None},

    # Broker (Tradier)
    # NOTE: your submit/cancel endpoints expect form-encoded
    "broker.order.submit": {"method": "POST", "path": "/api/v1/broker/orders/submit", "mode": "form"},
    "broker.order.cancel": {"method": "POST", "path": "/api/v1/broker/orders/cancel", "mode": "form"},
    "broker.positions":    {"method": "GET",  "path": "/api/v1/broker/positions", "mode": None},
    "broker.account":      {"method": "GET",  "path": "/api/v1/broker/tradier/account", "mode": None},

    # Diagnostics
    "diag.health":    {"method": "GET",  "path": "/api/v1/diag/health", "mode": None},
    "diag.actions":   {"method": "GET",  "path": "/api/v1/assistant/actions", "mode": None},
}

@router.get("/actions")
async def assistant_actions():
    """Tell myGPT which operations are supported."""
    return {"ok": True, "ops": sorted(list(OPS.keys()))}

@router.post("/exec")
async def assistant_exec(payload: dict, request: Request):
    """
    Accepts: { "op": "<namespace.name>", "args": { ... } }
    Forwards to your internal API with correct method and encoding.
    """
    op = (payload or {}).get("op")
    args = (payload or {}).get("args") or {}
    if not op or op not in OPS:
        raise HTTPException(400, f"Unknown op '{op}'. Call /api/v1/assistant/actions to list ops.")

    spec = OPS[op]
    path = spec["path"]
    url = (PUBLIC_BASE_URL + path) if PUBLIC_BASE_URL else path

    async with httpx.AsyncClient(timeout=20) as client:
        if spec["method"] == "GET":
            resp = await client.get(url, params=args)
        elif spec["mode"] == "json":
            resp = await client.post(url, json=args)
        elif spec["mode"] == "form":
            # pass-through as x-www-form-urlencoded (your broker endpoints expect this)
            resp = await client.post(url, data=args)
        else:
            resp = await client.post(url)

    # bubble up JSON if present
    content_type = resp.headers.get("content-type", "")
    out = resp.json() if content_type.startswith("application/json") else {"text": resp.text}
    return {"ok": resp.status_code < 400, "status_code": resp.status_code, "data": out}
