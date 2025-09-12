from typing import Dict
from collections import defaultdict
import threading, time

_lock = threading.Lock()
_counters = defaultdict(int)

def inc(key: str, n: int = 1):
    with _lock:
        _counters[key] += n

def snapshot() -> Dict[str,int]:
    with _lock:
        return dict(_counters)
