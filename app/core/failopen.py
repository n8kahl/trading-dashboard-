import asyncio
import functools
import os
from typing import Callable, Any, Dict

def _is_enabled() -> bool:
    # Enable fail-open by default; set TA_FAIL_OPEN=0 to disable
    return os.getenv("TA_FAIL_OPEN", "1") not in ("0", "false", "False")

def fail_open(fallback_factory: Callable[[], Dict[str, Any]]):
    """Decorate FastAPI endpoints to gracefully handle unexpected errors.

    Any exception raised by the wrapped endpoint results in:

    * HTTP 200 response
    * JSON from ``fallback_factory`` plus ``{"ok": False, "note": "..."}``

    Examples
    --------
    Synchronous endpoint::

        @fail_open(lambda: {"data": "stale"})
        def get_data():
            raise RuntimeError("boom")

        get_data()

    Asynchronous endpoint::

        @fail_open(lambda: {"data": "stale"})
        async def get_data_async():
            raise RuntimeError("boom")

        asyncio.run(get_data_async())

    Set ``TA_FAIL_OPEN=0`` to disable this behavior.
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
