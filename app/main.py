from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Trading Assistant – Stable Exec Layer (Snapshot)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

@app.get("/api/v1/diag/health")
async def health():
    return {"ok": True, "service": "coach-exec", "status": "healthy"}

# Try to import the assistant router; if it fails, register a safe fallback
try:
    from app.routers.assistant import router as assistant_router
    app.include_router(assistant_router)
    ROUTER_OK = True
except Exception as e:
    ROUTER_OK = False
    from fastapi import APIRouter, HTTPException
    fallback = APIRouter(prefix="/api/v1/assistant", tags=["assistant-fallback"])

    @fallback.get("/actions")
    async def assistant_actions():
        # minimal list so GPT tooling can proceed
        return {"ok": True, "ops": ["data.snapshot"], "warning": "running fallback router", "error": str(e)}

    @fallback.post("/exec")
    async def assistant_exec(_payload: dict):
        raise HTTPException(status_code=503, detail="assistant router failed to load; check logs")

    app.include_router(fallback)

@app.get("/api/v1/diag/env")
async def env_check():
    import os
    # Do NOT return secrets; just presence flags
    keys = ["POLYGON_API_KEY","TRADIER_ACCESS_TOKEN","TRADIER_ENV","PORT"]
    present = {k: bool(os.getenv(k)) for k in keys}
    return {"ok": True, "router_loaded": ROUTER_OK, "env_present": present}
