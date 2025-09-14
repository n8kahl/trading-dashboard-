from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers.diag import router as diag_router
from app.routers.assistant import router as assistant_router

app = FastAPI(title="Trading Assistant – Stable Exec Layer")

# CORS (tighten as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET","POST","OPTIONS"],
    allow_headers=["*"],
)

app.include_router(diag_router)
app.include_router(assistant_router)
