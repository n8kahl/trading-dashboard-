from fastapi import Header, HTTPException
import os

def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")):
    expected = os.getenv("API_KEY")
    if not expected:
        raise HTTPException(status_code=401, detail="Server not configured with API_KEY")
    if x_api_key != expected:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return True
