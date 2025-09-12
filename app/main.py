from fastapi import FastAPI
import logging

app = FastAPI(title="Trading Assistant", version="0.0.1")

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


logger = logging.getLogger(__name__)


def _mount(module: str, attr: str = "router", prefix: str = "/api/v1"):
    try:
        mod = __import__(module, fromlist=[attr])
        r = getattr(mod, attr)
        app.include_router(r, prefix=prefix)
        logger.info("[boot] mounted %s", module)
    except Exception as e:
        logger.exception("[boot] skipping %s: %s", module, e)


ROUTER_MODULES = [
    "app.routers.diag",
    "app.routers.diag_config",
    "app.routers.screener",
    "app.routers.options",
    "app.routers.alerts",
    "app.routers.plan",
    "app.routers.sizing",
    "app.routers.admin",
    "app.routers.assistant_simple",
]

for module_path in ROUTER_MODULES:
    _mount(module_path)
