import asyncio
import functools
import os
from typing import Callable, Awaitable, Any, Dict

def _is_enabled() -> bool:
    # Enable fail-open by default; set TA_FAIL_OPEN=0 to disable
    return os.getenv("TA_FAIL_OPEN", "1") not in ("0", "false", "False")

def _maybe_await(x):
    return x if asyncio.iscoroutine(x) else asyncio.Future()

def fail_open(fallback_factory: Callable[[], Dict[str, Any]]):
    """
    Wrap a FastAPI endpoint so that on ANY exception, we return:
      - 200 OK
      - JSON object from fallback_factory(), plus {"ok": false, "note": "..."}
    """
    def decorator(fn):
        if asyncio.iscoroutinefunction(fn):
            @functools.wraps(fn)
            async def wrapper(*args, **kwargs):
                if not _is_enabled():
                    return await fn(*args, **kwargs)
                try:
                    return await fn(*args, **kwargs)
                except Exception as e:
                    fb = fallback_factory() or {}
                    fb.setdefault("ok", False)
                    fb["note"] = f"fallback due to error: {e.__class__.__name__}"
                    return fb
            return wrapper
        else:
            @functools.wraps(fn)
            def wrapper(*args, **kwargs):
                if not _is_enabled():
                    return fn(*args, **kwargs)
                try:
                    return fn(*args, **kwargs)
                except Exception as e:
                    fb = fallback_factory() or {}
                    fb.setdefault("ok", False)
                    fb["note"] = f"fallback due to error: {e.__class__.__name__}"
                    return fb
            return wrapper
    return decorator
