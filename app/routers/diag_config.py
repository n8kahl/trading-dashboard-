from fastapi import APIRouter, HTTPException
import os, httpx

# IMPORTANT: mount under /api/v1/diag
router = APIRouter(prefix="/diag", tags=["diag"])

@router.get("/config")
def config():
    # Show which relevant env vars are set (mask values)
    keys = [
        "TRADIER_BASE", "TRADIER_ENV",
        "TRADIER_TOKEN", "TRADIER_ACCESS_TOKEN",
        "POLYGON_API_KEY"
    ]
    env = {k: ("set" if os.getenv(k) else "") for k in keys}
    return {"ok": True, "env": env}

@router.get("/tradier")
async def tradier(symbol: str = "SPY"):
    base = (os.getenv("TRADIER_BASE") or "https://sandbox.tradier.com").rstrip("/")
    token = os.getenv("TRADIER_TOKEN") or os.getenv("TRADIER_ACCESS_TOKEN")
    if not token:
        raise HTTPException(status_code=400, detail="TRADIER token not set")

    url = f"{base}/v1/markets/options/expirations"
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(
            url,
            params={"symbol": symbol},
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/json",
                "User-Agent": "ta/diag/1.0",
            },
        )
    try:
        j = r.json()
    except Exception:
        j = {"raw": r.text}
    return {"status_code": r.status_code, "json": j}
