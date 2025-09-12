import os, asyncio, json, time, datetime as dt
from typing import Dict, List, Any, Optional
from zoneinfo import ZoneInfo
import websockets

POLYGON_API_KEY = os.getenv("POLYGON_API_KEY") or os.getenv("POLYGON_APIKEY") or os.getenv("POLYGON_KEY")
WS_URL = "wss://socket.polygon.io/stocks"

CT = ZoneInfo("America/Chicago")

class _Stream:
    def __init__(self):
        self._symbols: List[str] = []
        self._bars: Dict[str, List[Dict[str, Any]]] = {}
        self._connected: bool = False
        self._task: Optional[asyncio.Task] = None
        self._reconnects: int = 0
        self._last_event_ts: Optional[float] = None
        self._lock = asyncio.Lock()

    async def start(self, symbols: List[str]) -> Dict[str, Any]:
        async with self._lock:
            self._symbols = [s.upper() for s in symbols or []]
            if self._task and not self._task.done():
                # already running; resubscribe
                await self._send({"action":"unsubscribe","params":",".join(f"AM.{s}" for s in self._bars.keys())})
                await self._send({"action":"subscribe","params":",".join(f"AM.{s}" for s in self._symbols)})
                return {"started": True, "subscriptions": self._symbols}
            self._task = asyncio.create_task(self._run())
            return {"started": True, "subscriptions": self._symbols}

    async def stop(self) -> Dict[str, Any]:
        async with self._lock:
            if self._task:
                self._task.cancel()
                self._task = None
            self._connected = False
            return {"stopped": True}

    async def snapshot(self, n: int = 120) -> Dict[str, List[Dict[str, Any]]]:
        # return a copy of the last n bars per symbol
        out: Dict[str, List[Dict[str, Any]]] = {}
        for s, bars in self._bars.items():
            out[s] = bars[-n:] if len(bars) > n else list(bars)
        return out

    async def status(self) -> Dict[str, Any]:
        return {
            "connected": self._connected,
            "watching": list(self._symbols),
            "reconnects": self._reconnects,
            "last_event_iso": self.iso_time(self._last_event_ts*1000 if self._last_event_ts else None),
            "age_sec": self.age_seconds(self._last_event_ts*1000 if self._last_event_ts else None),
        }

    # ---- helpers exposed to routers ----
    @staticmethod
    def iso_time(epoch_ms: Optional[float]) -> Optional[str]:
        if not epoch_ms: return None
        try:
            return dt.datetime.fromtimestamp(float(epoch_ms)/1000.0, tz=CT).isoformat()
        except Exception:
            return None

    @staticmethod
    def age_seconds(epoch_ms: Optional[float]) -> Optional[int]:
        if not epoch_ms: return None
        try:
            last = dt.datetime.fromtimestamp(float(epoch_ms)/1000.0, tz=CT)
            now = dt.datetime.now(tz=CT)
            return max(0, int((now - last).total_seconds()))
        except Exception:
            return None

    # ---- internal loop ----
    async def _run(self):
        backoff = 0.5
        while True:
            try:
                async with websockets.connect(f"{WS_URL}?apiKey={POLYGON_API_KEY}", ping_interval=20, ping_timeout=20) as ws:
                    self._connected = True
                    self._reconnects += 1
                    backoff = 0.5  # reset on success
                    # subscribe aggregate-minute channels for symbols
                    if self._symbols:
                        await ws.send(json.dumps({"action":"subscribe","params":",".join(f"AM.{s}" for s in self._symbols)}))
                    async for msg in ws:
                        self._handle_msg(msg)
            except asyncio.CancelledError:
                break
            except Exception:
                self._connected = False
                await asyncio.sleep(backoff)
                backoff = min(8.0, backoff * 1.8)

    def _handle_msg(self, msg: Any):
        try:
            data = json.loads(msg)
        except Exception:
            return
        # Polygon aggregates → list of events
        events = data if isinstance(data, list) else [data]
        for ev in events:
            if ev.get("ev") not in ("AM","A"):  # aggregate minute
                continue
            sym = ev.get("sym")
            if not sym: continue
            bar = {
                "t": int(ev.get("s")) if ev.get("s") else None,  # epoch ms start of bar
                "o": float(ev.get("o") or 0.0),
                "h": float(ev.get("h") or 0.0),
                "l": float(ev.get("l") or 0.0),
                "c": float(ev.get("c") or 0.0),
                "v": float(ev.get("v") or 0.0),
            }
            arr = self._bars.setdefault(sym, [])
            arr.append(bar)
            # cap memory
            if len(arr) > 3000:
                del arr[:len(arr)-3000]
            self._last_event_ts = time.time()

    async def _send(self, payload: Dict[str, Any]):
        # This placeholder keeps API shape consistent if we later add direct ws handle
        pass

STREAM = _Stream()
