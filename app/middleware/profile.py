from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

VALID = {"coach", "trade"}
DEFAULT = "coach"

class ProfileMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        profile = request.headers.get("X-Assistant-Profile", DEFAULT).lower()
        if profile not in VALID:
            profile = DEFAULT
        request.state.profile = profile
        response = await call_next(request)
        response.headers["X-Assistant-Profile"] = profile
        return response
