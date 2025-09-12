from fastapi import APIRouter, Request

router = APIRouter(prefix="/diag", tags=["diag"])

@router.get("/health")
async def health():
    return {"ok": True, "status": "healthy"}

@router.get("/ready")
async def ready():
    # If you want to check DB/polygon later, add here — keep it fast
    return {"ok": True, "ready": True}

@router.get("/routes")
async def list_routes(request: Request):
    app = request.app
    items = []
    for rt in app.router.routes:
        try:
            items.append({"path": rt.path, "methods": sorted(list(rt.methods or []))})
        except Exception:
            pass
    return {"ok": True, "routes": items}

@router.api_route("/echo", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def echo(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = None
    return {
        "method": request.method,
        "url_path": request.url.path,
        "query": dict(request.query_params),
        "headers_subset": {k:v for k,v in request.headers.items()
                           if k.lower() in ["content-type","user-agent"]},
        "body": body
    }
