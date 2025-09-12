from fastapi import FastAPI, Request
app = FastAPI(title="Safe Probe App", version="0.0.1")

@app.get("/")
def root(): return {"ok": True, "service": "safe", "version": "0.0.1"}

@app.get("/healthz")
def healthz(): return {"status": "ok"}

@app.get("/api/v1/diag/health")
def diag_health(): return {"ok": True, "status": "healthy"}

@app.get("/api/v1/diag/ready")
def diag_ready(): return {"ok": True, "ready": True}

@app.api_route("/api/v1/diag/echo", methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS","HEAD"])
async def echo(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = None
    return {
        "method": request.method,
        "url_path": request.url.path,
        "query": dict(request.query_params),
        "headers_subset": {"user-agent": request.headers.get("user-agent","")},
        "body": body,
    }
