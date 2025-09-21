from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator

from app.db.session import init_db
from app.routers.assistant_api import router as assistant_router
from app.routers.charts import router as charts_router
from app.routers.diag import router as diag_router  # <-- make sure this exists
from app.routers.hedge import router as hedge_router
from app.routers.market import router as market_router
from app.routers.market_data import router as market_data_router
from app.routers.storage import router as storage_router

app = FastAPI(title="Trading Assistant – Stable Exec Layer")


@app.exception_handler(Exception)
async def all_exception_handler(request: Request, exc: Exception):
    return JSONResponse(status_code=500, content={"ok": False, "error": type(exc).__name__, "detail": str(exc)})


@app.on_event("startup")
async def on_startup() -> None:
    await init_db()


@app.get("/api/v1/diag/health")
async def health():
    return {"ok": True}


# Mount diag FIRST so it doesn't get lost on merges
app.include_router(diag_router)
app.include_router(assistant_router)
app.include_router(hedge_router)
app.include_router(market_router)
app.include_router(market_data_router)
app.include_router(charts_router)
app.include_router(storage_router)

# Expose /metrics for Prometheus (scraped by prometheus service in docker-compose)
Instrumentator().instrument(app).expose(app)
