from fastapi import APIRouter, Request, Query
from typing import Optional, List, Dict

router = APIRouter(prefix="/admin", tags=["admin"])

def with_profile(request: Request, payload: Dict) -> Dict:
    payload.setdefault("profile", getattr(request.state, "profile", "coach"))
    return payload

@router.get("/signals")
async def list_signals(
    request: Request,
    symbol: Optional[str] = None,
    since: Optional[str] = Query(None, description="ISO timestamp"),
    limit: int = 50
):
    # TODO: replace with real signal store
    rows = [{
      "id": "sig_123",
      "symbol": symbol or "AAPL",
      "time": "2025-09-07T14:10:00Z",
      "strategy": "vwap_bounce",
      "gates": {"session": True, "rvol": True, "spread": True, "retest": False},
      "pr_win": 0.58,
      "expected_r": 0.32,
      "actionability": "wait"  # actionable | wait | skip
    }]
    return with_profile(request, {"ok": True, "items": rows[:limit]})

@router.get("/signal/{sid}")
async def get_signal(request: Request, sid: str):
    # TODO: replace with real fetch by ID
    data = {
      "id": sid,
      "symbol": "AAPL",
      "time": "2025-09-07T14:10:00Z",
      "features": {"dist_to_avwap": 0.0018, "rvol": 1.45, "spread_pct": 0.0005},
      "gates": {"session": True, "rvol": True, "spread": True, "retest": False},
      "pr_win": 0.58,
      "expected_r": 0.32,
      "actionability": "wait",
      "plan": {"entry": 230.12, "stop": 229.00, "tp1_r": 1, "tp2_r": 2, "time_stop_min": 10}
    }
    return with_profile(request, {"ok": True, "signal": data})

@router.get("/positions")
async def positions(request: Request, limit: int = 20):
    # TODO: wire to paper/live positions
    pos = [{
      "id":"pos_001","symbol":"AAPL","side":"long",
      "avg_price":229.9,"qty":100,"unrealized_r":0.42,
      "timer_sec": 240, "risk_state":"OK"
    }]
    return with_profile(request, {"ok": True, "items": pos[:limit]})

@router.get("/diag/calibration")
async def calib(request: Request, strategy: str = "vwap_bounce", period: str = "30d"):
    bins = [{"decile":i,"pr_pred":0.50+i*0.03,"pr_real":0.49+i*0.028} for i in range(1,10)]
    return with_profile(request, {"ok": True, "strategy": strategy, "period": period, "bins": bins})

@router.get("/diag/expectancy-heatmap")
async def heatmap(request: Request):
    grid = [
      {"session":"open","rvol_bin":"hi","spread_bin":"tight","E_R":0.42},
      {"session":"mid","rvol_bin":"lo","spread_bin":"wide","E_R":-0.08},
    ]
    return with_profile(request, {"ok": True, "grid": grid})
