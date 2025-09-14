# tiny memo cache with TTL (sync-only wrapper)
import time
from typing import Any, Tuple, Dict

_CACHE: Dict[Tuple[str, Tuple[Any,...]], Tuple[float, Any]] = {}

def memo(ttl: float = 30.0):
    def deco(fn):
        def wrap(*a, **kw):
            key = (fn.__name__, a + tuple(sorted(kw.items())))
            now = time.time()
            hit = _CACHE.get(key)
            if hit and now - hit[0] < ttl:
                return hit[1]
            val = fn(*a, **kw)
            _CACHE[key] = (now, val)
            return val
        return wrap
    return deco
