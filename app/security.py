import os

from fastapi import Header, HTTPException, status


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> bool:
    """Strict API key gate for sensitive routes.

    - If API_KEY is not configured in the environment, deny by default (401).
    - If provided key does not match, deny (401).
    - On success, return True for dependency chaining.
    """
    expected = (os.getenv("API_KEY") or "").strip()
    if not expected:
        # safer default: refuse when not configured
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Server not configured with API_KEY")
    if x_api_key != expected:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API Key")
    return True
