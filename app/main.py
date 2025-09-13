import importlib
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI

from app.core.risk import start_risk_engine
from app.core.ws import start_ws, websocket_endpoint
from app.security import require_api_key
from app.services.providers import close_tradier_client


@asynccontextmanager
async def lifespan(app: FastAPI):
    # TODO: add startup code here if needed
    yield
    # TODO: add shutdown code here if needed


app = FastAPI(lifespan=lifespan, title="Trading Assistant", version="0.0.1")

# ---- safely mount routers (won't crash app if a router has issues) ----
try:
    diag = importlib.import_module("app.routers.diag")
    app.include_router(diag.router)
except Exception as e:
    logging.exception("Skipping diag router: %s", e)

try:
    sizing = importlib.import_module("app.routers.sizing")
    app.include_router(sizing.router)
except Exception as e:
    logging.exception("Skipping sizing router: %s", e)

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
_mount("app.routers.market_stream", secure=True)  # market stream control

# assistant router (simple)
_mount("app.routers.assistant_simple", secure=True)

# websocket endpoint
app.add_api_websocket_route("/ws", websocket_endpoint)


# @app.on_event("startup")  # replaced by lifespan
async def _startup_tasks():
    await start_ws()
    await start_risk_engine()


# @app.on_event("shutdown")  # replaced by lifespan
async def _shutdown_tradier():
    await close_tradier_client()

from app.routers import diag, sizing
