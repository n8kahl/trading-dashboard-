from datetime import datetime, timezone
def ok(data): return {"status":"ok","data":data}
def now_ts(): return datetime.now(timezone.utc).isoformat()+"Z"
