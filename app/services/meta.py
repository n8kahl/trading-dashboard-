import os, psycopg2, statistics as stats
from typing import List, Dict, Any, Tuple
import math

DB_URL = os.getenv("DATABASE_URL") or os.getenv("POSTGRES_URL") or os.getenv("PG_URL")

def _conn():
    return psycopg2.connect(DB_URL)

def init():
    if not DB_URL: return
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        CREATE TABLE IF NOT EXISTS meta_perf (
          id SERIAL PRIMARY KEY,
          strategy_id TEXT NOT NULL,
          regime_key TEXT NOT NULL,
          plays INTEGER NOT NULL DEFAULT 0,
          wins INTEGER NOT NULL DEFAULT 0,
          sum_r NUMERIC NOT NULL DEFAULT 0,
          updated_at TIMESTAMP NOT NULL DEFAULT NOW(),
          UNIQUE(strategy_id, regime_key)
        );
        """)
        c.commit()

def _ema(values: List[float], span: int) -> List[float]:
    if not values: return []
    k = 2/(span+1)
    ema=[values[0]]
    for v in values[1:]:
        ema.append(ema[-1] + k*(v-ema[-1]))
    return ema

def _atr(bars: List[Dict[str,Any]], period: int = 14) -> List[float]:
    trs=[]
    for i,b in enumerate(bars):
        h,l,c = b["h"], b["l"], b["c"]
        if i==0:
            trs.append(h-l); continue
        prev_c = bars[i-1]["c"]
        tr = max(h-l, abs(h-prev_c), abs(l-prev_c))
        trs.append(tr)
    # simple EMA for ATR
    return _ema(trs, period)

def regime_features(bars: List[Dict[str,Any]]) -> Tuple[str,str,str]:
    closes = [b["c"] for b in bars[-120:]] if len(bars)>=120 else [b["c"] for b in bars]
    if len(closes) < 20:
        return ("side","low","side_low")  # default
    ema20 = _ema(closes, 20)
    # slope & R2 vs index
    n=len(ema20); xs=list(range(n))
    mean_x = sum(xs)/n; mean_y = sum(ema20)/n
    num=sum((x-mean_x)*(y-mean_y) for x,y in zip(xs,ema20))
    den=sum((x-mean_x)**2 for x in xs) or 1e-9
    slope=num/den
    # r^2
    y_hat=[mean_y + slope*(x-mean_x) for x in xs]
    ss_tot = sum((y-mean_y)**2 for y in ema20) or 1e-9
    ss_res = sum((y-yy)**2 for y,yy in zip(ema20,y_hat))
    r2 = 1 - (ss_res/ss_tot)

    trend = "up" if slope>0 and r2>0.2 else "down" if slope<0 and r2>0.2 else "side"

    atr = _atr(bars[-160:] if len(bars)>160 else bars, 14)
    if atr:
        p = atr[-1]
        # use quantiles of last 60 atr values
        window = atr[-60:] if len(atr)>60 else atr
        qs = sorted(window)
        q33 = qs[int(len(qs)*0.33)]
        q66 = qs[int(len(qs)*0.66)]
        if p <= q33: vol="low"
        elif p >= q66: vol="high"
        else: vol="medium"
    else:
        vol="low"

    key = f"{trend}_{vol}"
    return (trend, vol, key)

def record_outcome(strategy_id: str, regime_key: str, result_r: float):
    if not DB_URL: return
    win = 1 if result_r>0 else 0
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        INSERT INTO meta_perf(strategy_id, regime_key, plays, wins, sum_r)
        VALUES (%s,%s,1,%s,%s)
        ON CONFLICT (strategy_id, regime_key)
        DO UPDATE SET
          plays = meta_perf.plays + 1,
          wins  = meta_perf.wins + EXCLUDED.wins,
          sum_r = meta_perf.sum_r + EXCLUDED.sum_r,
          updated_at = NOW();
        """, (strategy_id, regime_key, win, result_r))
        c.commit()

def get_weight(strategy_id: str, regime_key: str) -> float:
    if not DB_URL: return 1.0
    with _conn() as c, c.cursor() as cur:
        cur.execute("""
        SELECT plays, wins, sum_r FROM meta_perf
        WHERE strategy_id=%s AND regime_key=%s;
        """, (strategy_id, regime_key))
        r = cur.fetchone()
        if not r:
            return 1.0
        plays, wins, sum_r = r
        plays = float(plays or 0); wins = float(wins or 0); sum_r = float(sum_r or 0.0)
        wr = (wins+1)/(plays+2)              # Laplace smoothing
        avgR = (sum_r/plays) if plays>0 else 0.0
        payoff_adj = max(0.5, 1.0 + avgR)    # avgR +1 floored at 0.5
        w = wr * payoff_adj
        return max(0.6, min(1.6, float(w)))

def apply_meta_weights(ranked: List[Dict[str,Any]], bars: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    _,_,key = regime_features(bars)
    out=[]
    for r in ranked:
        sid = r.get("id") or "unknown"
        w = get_weight(sid, key)
        adj = dict(r)
        adj["score_raw"] = r["score"]
        adj["meta_weight"] = w
        adj["score"] = r["score"] * w
        out.append(adj)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out
