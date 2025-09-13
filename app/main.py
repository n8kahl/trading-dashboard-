from app.routers import assistant_bridge
import importlib
import logging
import asyncio
import os
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.core.risk import start_risk_engine
from app.core.ws import start_ws, websocket_endpoint
from app.security import require_api_key
from app.services.providers import close_tradier_client
from app.services.poller import alerts_poller
from app.services.stream import STREAM
from app.db import db_session
from app.models.settings import AppSettings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Background tasks (opt-in via env to avoid test interference)
    bg_enabled = (os.getenv("ENABLE_BACKGROUND_LOOPS", "0").strip() == "1")
    tasks: list[asyncio.Task] = []
    if bg_enabled:
        # WS ping + risk engine loop
        try:
            await start_ws()
            await start_risk_engine()
        except Exception:
            pass
        # Alerts poller (optional)
        if os.getenv("ENABLE_ALERTS_POLLER", "0").strip() == "1":
            try:
                tasks.append(asyncio.create_task(alerts_poller(loop_forever=True)))
            except Exception:
                pass
        # Polygon price stream (optional; auto-start from top_symbols if key present)
        try:
            symbols: list[str] = []
            with db_session() as s:
                if s is not None:
                    row = s.query(AppSettings).order_by(AppSettings.id.asc()).first()
                    if row and row.top_symbols:
                        symbols = [t.strip().upper() for t in row.top_symbols.split(",") if t.strip()]
            if symbols:
                await STREAM.start(symbols)
        except Exception:
            pass
    try:
        yield
    finally:
        for t in tasks:
            t.cancel()


app = FastAPI(lifespan=lifespan, title="Trading Assistant", version="0.0.1")

# --- CORS (allow dashboard & localhost) ---
from fastapi.middleware.cors import CORSMiddleware

ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "https://tradingassistantmcpready-production.up.railway.app",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS if ALLOWED_ORIGINS else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# --- end CORS ---


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/api/v1/diag/health")
def diag_health():
    return {"ok": True, "status": "healthy"}


@app.get("/api/v1/diag/ready")
def diag_ready():
    return {"ok": True, "ready": True}


_mounted_modules = set()
logger = logging.getLogger(__name__)


def _mount(module: str, attr: str = "router", prefix: str = "/api/v1", secure: bool = False):
    if module in _mounted_modules:
        logger.warning("[boot] %s already mounted, skipping", module)
        return
    try:
        mod = importlib.import_module(module)
        r = getattr(mod, attr)
        if secure:
            r.dependencies = [Depends(require_api_key), *(r.dependencies or [])]
        app.include_router(r, prefix=prefix)
        _mounted_modules.add(module)
        logger.info("[boot] mounted %s", module)
    except Exception as e:
        logger.warning("[boot] skipping %s: %s", module, e)


# core routers (mount once)
_mount("app.routers.diag")  # if present in your repo
_mount("app.routers.diag_config")  # if present
_mount("app.routers.screener")  # if present
_mount("app.routers.options", secure=True)  # we just created this
_mount("app.routers.alerts")  # if present
_mount("app.routers.plan")  # if present
_mount("app.routers.sizing")  # if present
_mount("app.routers.admin")  # if present
_mount("app.routers.broker", secure=True)  # new broker routes
_mount("app.routers.broker_tradier", secure=True)  # tradier broker routes
_mount("app.routers.auto", secure=True)  # auto-trade
_mount("app.routers.stream")  # stream snapshot
_mount("app.routers.coach")  # chat-data.com coach chat
_mount("app.routers.journal")  # journal CRUD
_mount("app.routers.settings", secure=True)  # admin settings CRUD

# assistant router (simple)
_mount("app.routers.assistant_simple", secure=True)

# websocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)


# Legacy hooks (kept for ref but now handled in lifespan)
async def _startup_tasks():
    await start_ws()
    await start_risk_engine()


async def _shutdown_tradier():
    await close_tradier_client()
app.include_router(assistant_bridge.router)
