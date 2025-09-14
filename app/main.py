from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.assistant import router as assistant_router

app = FastAPI(title="Trading Assistant – Stable Exec Layer (Reboot)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

@app.get("/api/v1/diag/health")
async def health():
    return {"ok": True, "service": "coach-exec", "status": "healthy"}

app.include_router(assistant_router)
