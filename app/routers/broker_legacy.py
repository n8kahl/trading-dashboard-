from __future__ import annotations
import os, json
from typing import Optional, Dict, Any
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel, Field
import httpx

router = APIRouter(prefix="/api/v1/broker", tags=["broker-legacy"])

TRADIER_BASE = os.getenv("TRADIER_BASE", "https://sandbox.tradier.com")
TRADIER_TOKEN = os.getenv("TRADIER_ACCESS_TOKEN")
TRADIER_ACCOUNT = os.getenv("TRADIER_ACCOUNT_ID")
TRADIER_ENV = os.getenv("TRADIER_ENV", "sandbox")  # sandbox|live
ENV = os.getenv("ENVIRONMENT", "dev")
SAFE = os.getenv("SAFE_MODE", "1")

def can_trade() -> bool:
    # sandbox: allow if creds present
    if TRADIER_ENV == "sandbox":
        return bool(TRADIER_TOKEN and TRADIER_ACCOUNT)
    # live: must be prod + SAFE=0
    return (TRADIER_TOKEN and TRADIER_ACCOUNT and ENV == "prod" and SAFE == "0" and TRADIER_ENV == "live")

async def tradier_get(path: str, params: Optional[Dict[str, Any]] = None):
    headers = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json"}
    url = f"{TRADIER_BASE}{path}"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url, headers=headers, params=params or {})
    return r

async def tradier_post_form(path: str, form: Dict[str, Any]):
    headers = {"Authorization": f"Bearer {TRADIER_TOKEN}", "Accept": "application/json", "Content-Type": "application/x-www-form-urlencoded"}
    url = f"{TRADIER_BASE}{path}"
    async with httpx.AsyncClient(timeout=12.0) as client:
        r = await client.post(url, headers=headers, data=form)
    return r

@router.get("/tradier/account")
async def tradier_account():
    if not TRADIER_TOKEN or not TRADIER_ACCOUNT:
        raise HTTPException(412, "Missing TRADIER credentials")
    try:
        r = await tradier_get(f"/v1/accounts/{TRADIER_ACCOUNT}/profile")
        ok = r.status_code == 200
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"ok": ok, "status_code": r.status_code, "body": body}
    except Exception as e:
        raise HTTPException(502, f"Upstream error: {e}")

# Submit order (equity/option) — expects JSON or x-www-form-urlencoded
@router.post("/orders/submit")
async def orders_submit(request: Request):
    if not can_trade():
        raise HTTPException(412, "Trading disabled by safety policy or missing credentials")

    # accept both JSON and form data
    payload: Dict[str, Any] = {}
    ctype = request.headers.get("content-type","")
    if "application/json" in ctype:
        payload = await request.json()
    else:
        form = await request.form()
        payload = {k: form.get(k) for k in form.keys()}

    # normalize field names to Tradier expectations
    # expected keys: class, symbol, side, quantity, type, duration, price (for limit)
    for k in ("quantity", "price"):
        if k in payload and payload[k] is not None:
            try:
                payload[k] = float(payload[k]) if k == "price" else int(payload[k])
            except Exception:
                pass

    if payload.get("type") == "limit" and not payload.get("price"):
        raise HTTPException(422, "limit_price/price required for limit orders")

    try:
        r = await tradier_post_form(f"/v1/accounts/{TRADIER_ACCOUNT}/orders", payload)
        ok = r.status_code in (200,201)
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"ok": ok, "status_code": r.status_code, "body": body}
    except Exception as e:
        raise HTTPException(502, f"Upstream error: {e}")

@router.get("/positions")
async def positions():
    if not TRADIER_TOKEN or not TRADIER_ACCOUNT:
        raise HTTPException(412, "Missing TRADIER credentials")
    try:
        r = await tradier_get(f"/v1/accounts/{TRADIER_ACCOUNT}/positions")
        ok = r.status_code == 200
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"ok": ok, "status_code": r.status_code, "body": body}
    except Exception as e:
        raise HTTPException(502, f"Upstream error: {e}")

@router.post("/orders/cancel")
async def orders_cancel(request: Request):
    if not TRADIER_TOKEN or not TRADIER_ACCOUNT:
        raise HTTPException(412, "Missing TRADIER credentials")
    ctype = request.headers.get("content-type","")
    payload = await (request.json() if "application/json" in ctype else request.form())
    order_id = (payload.get("order_id") or payload.get("id"))
    if not order_id:
        raise HTTPException(422, "order_id is required")
    try:
        r = await tradier_post_form(f"/v1/accounts/{TRADIER_ACCOUNT}/orders/{order_id}/cancel", {})
        ok = r.status_code in (200,201,204)
        body = r.json() if r.headers.get("content-type","").startswith("application/json") else r.text
        return {"ok": ok, "status_code": r.status_code, "body": body}
    except Exception as e:
        raise HTTPException(502, f"Upstream error: {e}")


@router.get("/ping")
async def ping():
    # No network, just prove router is mounted and app responds
    return {"ok": True, "router": "broker-legacy"}

@router.get("/envcheck")
async def envcheck():
    # DO NOT include secrets; just presence booleans
    import os
    return {
        "ok": True,
        "TRADIER_ENV": os.getenv("TRADIER_ENV"),
        "has_TOKEN": bool(os.getenv("TRADIER_ACCESS_TOKEN")),
        "has_ACCOUNT": bool(os.getenv("TRADIER_ACCOUNT_ID")),
        "TRADIER_BASE": os.getenv("TRADIER_BASE"),
        "ENVIRONMENT": os.getenv("ENVIRONMENT"),
        "SAFE_MODE": os.getenv("SAFE_MODE"),
    }
