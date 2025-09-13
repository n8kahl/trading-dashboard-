import os, time, threading, logging
from typing import Dict, List, Any
import httpx

log = logging.getLogger(__name__)
POLYGON_API_KEY = os.getenv("POLYGON_API_KEY", "")

_state: Dict[str, Any] = {"symbols": [], "quotes": {}, "started_at": None}
_lock = threading.Lock()
_thread = None
_stop = threading.Event()
_interval = float(os.getenv("STREAM_POLL_SEC", "2"))

def get_state() -> Dict[str, Any]:
    with _lock:
        return {
            "symbols": list(_state["symbols"]),
            "quotes": dict(_state["quotes"]),
            "started_at": _state["started_at"],
            "interval_sec": _interval,
        }

def set_symbols(symbols: List[str]) -> Dict[str, Any]:
    symbols = sorted({s.upper() for s in symbols if s})
    with _lock:
        _state["symbols"] = symbols
    return {"ok": True, "symbols": symbols}

def _fetch_quotes(symbols: List[str]) -> Dict[str, Any]:
    if not symbols or not POLYGON_API_KEY:
        return {}
    # Polygon snapshot (delayed). Pick your endpoint; this one is stable.
    # https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers?tickers=AAPL,MSFT&apiKey=...
    url = "https://api.polygon.io/v2/snapshot/locale/us/markets/stocks/tickers"
    params = {"tickers": ",".join(symbols), "apiKey": POLYGON_API_KEY}
    with httpx.Client(timeout=5.0) as cx:
        r = cx.get(url, params=params)
        r.raise_for_status()
        data = r.json().get("tickers", [])
    quotes = {}
    for t in data:
        sym = t.get("ticker")
        last = (t.get("lastTrade") or {}).get("p") or (t.get("lastQuote") or {}).get("ap") or (t.get("lastQuote") or {}).get("bp")
        quotes[sym] = {"symbol": sym, "price": last, "raw": t}
    return quotes

def _loop():
    log.info("[stream] poller starting interval=%ss", _interval)
    with _lock:
        _state["started_at"] = time.time()
    while not _stop.is_set():
        try:
            with _lock:
                syms = list(_state["symbols"])
            quotes = _fetch_quotes(syms)
            if quotes:
                with _lock:
                    _state["quotes"] = quotes
        except Exception as e:
            log.warning("[stream] poll error: %s", e)
        _stop.wait(_interval)
    log.info("[stream] poller stopped")

def start():
    global _thread
    if _thread and _thread.is_alive():
        return
    _stop.clear()
    _thread = threading.Thread(target=_loop, name="stream-poller", daemon=True)
    _thread.start()

def stop():
    _stop.set()
