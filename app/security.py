import os
from fastapi import Header, HTTPException, status

API_KEY = os.getenv("API_KEY", "").strip()


def require_api_key(x_api_key: str | None = Header(None, alias="X-API-Key")):
    if not API_KEY:
        return
    if x_api_key != API_KEY:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

