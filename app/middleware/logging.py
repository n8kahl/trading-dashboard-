import time
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import logging
log = logging.getLogger("uvicorn.access")

class RequestLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()
        rsp = await call_next(request)
        dur = int((time.time() - start)*1000)
        log.info("%s %s %s %dms", request.method, request.url.path, rsp.status_code, dur)
        return rsp
