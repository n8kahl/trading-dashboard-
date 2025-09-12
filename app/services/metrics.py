import threading
from collections import defaultdict
from typing import Dict

_lock = threading.Lock()
_counters = defaultdict(int)


def inc(key: str, n: int = 1):
    with _lock:
        _counters[key] += n


def snapshot() -> Dict[str, int]:
    with _lock:
        return dict(_counters)
