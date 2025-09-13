from fastapi import APIRouter, HTTPException
import os, httpx

router = APIRouter(prefix="/api/v1/assistant")

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
if not PUBLIC_BASE_URL:
    # allow same-origin when deployed behind one service
    PUBLIC_BASE_URL = ""

OPS = {
    "options.pick": {"method":"POST","path":"/options/pick","mode":"json"},
    # Alerts
    "alerts.set":      {"method":"POST","path":"/api/v1/alerts/set","mode":"json"},
    "alerts.list":     {"method":"GET", "path":"/api/v1/alerts/list","mode":None},

    # Stream (read-only status endpoints available)
    "stream.status":       {"method":"GET", "path":"/api/v1/stream/state","mode":None},
    "stream.risk_status":  {"method":"GET", "path":"/api/v1/stream/risk/state","mode":None},

    # Broker (Tradier)
    "broker.account":      {"method":"GET", "path":"/api/v1/broker/tradier/account","mode":None},
    "broker.positions":    {"method":"GET", "path":"/api/v1/broker/positions","mode":None},
    "broker.order.submit": {"method":"POST","path":"/api/v1/broker/orders/submit","mode":"form"},
    "broker.order.cancel": {"method":"POST","path":"/api/v1/broker/orders/cancel","mode":"form"},

    # Diagnostics
    "diag.health":         {"method":"GET","path":"/api/v1/diag/health","mode":None},
},
    "alerts.list":     {"method":"GET", "path":"/api/v1/alerts/list","mode":None},
    # Stream
    # "stream.start":    {"method":"POST","path":"/api/v1/market/stream/start","mode":"json"},
    "stream.status":   {"method":"GET", "path":"/api/v1/market/stream/status","mode":None},
    # "stream.snapshot": {"method":"GET", "path":"/api/v1/market/stream/snapshot","mode":None},
    # "stream.stop":     {"method":"POST","path":"/api/v1/market/stream/stop","mode":None},
    # Broker (Tradier)
    "broker.order.submit": {"method":"POST","path":"/api/v1/broker/orders/submit","mode":"form"},
    "broker.order.cancel": {"method":"POST","path":"/api/v1/broker/orders/cancel","mode":"form"},
    "broker.positions":    {"method":"GET", "path":"/api/v1/broker/positions","mode":None},
    "broker.account":      {"method":"GET", "path":"/api/v1/broker/tradier/account","mode":None},
    # Diagnostics
    "diag.health":     {"method":"GET","path":"/api/v1/diag/health","mode":None},
}

@router.get("/actions")
async def actions():
    return {"ok": True, "ops": sorted(list(OPS.keys()))}

@router.post("/exec")
async def exec(payload: dict):
    op = (payload or {}).get("op")
    args = (payload or {}).get("args") or {}
    if not op or op not in OPS:
        raise HTTPException(400, {"ok": False, "error": "unknown_op", "op": op})

    spec = OPS[op]
    url = (PUBLIC_BASE_URL + spec["path"]) if PUBLIC_BASE_URL else spec["path"]

    async with httpx.AsyncClient(timeout=20) as client:
        if spec["method"] == "GET":
            r = await client.get(url, params=args)
        elif spec["mode"] == "json":
            r = await client.post(url, json=args)
        elif spec["mode"] == "form":
            r = await client.post(url, data=args)
        else:
            r = await client.post(url)

    ct = r.headers.get("content-type","")
    data = r.json() if ct.startswith("application/json") else {"text": r.text}
    return {"ok": r.status_code < 400, "status_code": r.status_code, "data": data}
