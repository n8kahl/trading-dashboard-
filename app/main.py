from app.routers import plan, sizing
from app.routers import diag_config
from fastapi import FastAPI

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

app.include_router(sizing.router, prefix="/api/v1")
app.include_router(plan.router, prefix="/api/v1")
app.include_router(diag_config.router)

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.get("/api/v1/diag/health")
def diag_health():
    return {"ok": True, "status": "healthy"}

@app.get("/api/v1/diag/ready")
def diag_ready():
    return {"ok": True, "ready": True}

def _mount(module: str, attr: str = "router", prefix: str = "/api/v1"):
    try:
        mod = __import__(module, fromlist=[attr])
        r = getattr(mod, attr)
        app.include_router(r, prefix=prefix)
        print(f"[boot] mounted {module}")
    except Exception as e:
        print(f"[boot] skipping {module}: {e}")

# core routers (mount once)
_mount("app.routers.diag")           # if present in your repo
_mount("app.routers.diag_config")    # if present
_mount("app.routers.screener")       # if present
_mount("app.routers.options")        # we just created this
_mount("app.routers.alerts")         # if present
_mount("app.routers.plan")           # if present
_mount("app.routers.sizing")         # if present
_mount("app.routers.admin")          # if present

# assistant router (simple)
_mount("app.routers.assistant_simple")

from app.routers import screener as screener_router
app.include_router(screener_router.router, prefix="/api/v1")
