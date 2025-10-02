from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.routers.assistant import router as assistant_router
from app.routers.diag import router as diag_router  # <-- make sure this exists

app = FastAPI(title="Trading Assistant – Stable Exec Layer")

@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": type(exc).__name__, "detail": str(exc)})

@app.get("/api/v1/diag/health")
async def health():
    return {"ok": True}

# Mount diag FIRST so it doesn't get lost on merges
app.include_router(diag_router)
app.include_router(assistant_router)
