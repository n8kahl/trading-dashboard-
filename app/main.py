from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Routers (make sure assistant router exists in app/routers/assistant.py)
try:
    from app.routers.diag import router as diag_router
except Exception:
    from fastapi import APIRouter
    diag_router = APIRouter(prefix="/api/v1/diag", tags=["diag"])
    @diag_router.get("/health")
    async def health():
        return {"ok": True, "service": "coach-exec", "status": "healthy"}

from app.routers.assistant import router as assistant_router

app = FastAPI(title="Trading Assistant – Stable Exec Layer")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

app.include_router(diag_router)
app.include_router(assistant_router)
