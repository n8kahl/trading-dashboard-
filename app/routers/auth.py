import base64
import hashlib
import hmac
import json
import os
import time
from typing import Dict

from fastapi import APIRouter

router = APIRouter(prefix="/auth", tags=["auth"])

SECRET = (os.getenv("WS_SECRET") or "dev-secret").encode()


def _sign(payload: Dict, exp: int = 300) -> str:
    data = dict(payload)
    data["exp"] = int(time.time()) + int(exp)
    raw = json.dumps(data, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(SECRET, raw, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(raw + b"." + sig).decode()


@router.get("/ws-token")
def ws_token() -> Dict[str, str | bool]:
    """Mint a short-lived token for websocket connections.

    The frontend should pass this token as `?token=...` or via
    `Authorization: Bearer <token>` when connecting to `/ws`.
    """
    return {"ok": True, "token": _sign({"sub": "single-tenant"})}

