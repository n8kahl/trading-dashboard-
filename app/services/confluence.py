from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime, UTC

BANDS = [(0,"weak"),(40,"mixed"),(60,"favorable"),(80,"high")]

DEFAULT_WEIGHTS = {
  "vwap_posture":15, "ema_stack":10, "divergence":12,
  "volume_confluence":10, "levels_breakout":8,
  "liquidity":10, "vol_context":5, "macro":15
}

STRATEGY_WEIGHTS = {
  "vwap_bounce": {**DEFAULT_WEIGHTS, "levels_breakout":6},
  "or_breakout_retest_long": {**DEFAULT_WEIGHTS, "levels_breakout":10, "divergence":6},
  "ema9_reclaim_long": {**DEFAULT_WEIGHTS, "divergence":8},
  "range_fade_short": {**DEFAULT_WEIGHTS, "vwap_posture":8, "ema_stack":6},
  "spx_power_hour_squeeze_long": {**DEFAULT_WEIGHTS, "macro":10, "levels_breakout":10},
  "spx_power_hour_fade_short":   {**DEFAULT_WEIGHTS, "macro":10, "levels_breakout":8}
}

@dataclass
class Component:
    name: str; points: int; explain: str

def clip(n,lo,hi): return max(lo,min(hi,n))

def evaluate_components(cx:Dict,w:Dict)->List[Component]:
    comps: List[Component] = []
    if cx.get("price") is not None and cx.get("vwap") is not None:
        above = cx["price"] >= cx["vwap"]
        bars = int(cx.get("bars_above_vwap",0))
        pts = (w["vwap_posture"] if above else -w["vwap_posture"]) + clip(bars,0,3)
        comps.append(Component("vwap_posture",pts,f"{'Above' if above else 'Below'} VWAP; held {bars} bars"))
    ema9_gt = bool(cx.get("ema9_gt_ema20",False))
    comps.append(Component("ema_stack", w["ema_stack"] if ema9_gt else -w["ema_stack"],
                           "EMA9 > EMA20" if ema9_gt else "EMA9 < EMA20"))
    div = cx.get("divergence_5m")
    if div in ("bullish_confirmed","bearish_confirmed"):
        comps.append(Component("divergence", w["divergence"], div.replace("_"," ")))
    elif div == "weak":
        comps.append(Component("divergence", int(w["divergence"]*0.4),"weak divergence context"))
    elif div == "invalid":
        comps.append(Component("divergence", -int(w["divergence"]*0.7),"divergence invalidated"))
    vol_ok = bool(cx.get("rising_volume_retest", False))
    comps.append(Component("volume_confluence", w["volume_confluence"] if vol_ok else -int(w["volume_confluence"]*0.8),
                           "Rising volume on retest" if vol_ok else "Weak volume on retest"))
    if cx.get("resistance_dist_bp") is not None:
        dist = int(cx["resistance_dist_bp"])
        if dist >= 0:
            penalty = 0 if dist>40 else -int(w["levels_breakout"]*(1-dist/40))
            comps.append(Component("levels_breakout", penalty, f"Resistance {abs(dist)/100:.2f}% overhead"))
        else:
            comps.append(Component("levels_breakout", int(w["levels_breakout"]*0.8),"Through resistance / ORH"))
    if cx.get("spread_pct") is not None:
        s = float(cx["spread_pct"])
        if s <= 6: pts,ex = int(w["liquidity"]*0.5), f"Spread {s:.1f}% (tight)"
        elif s <= 8: pts,ex = int(w["liquidity"]*0.2), f"Spread {s:.1f}% (acceptable)"
        elif s <=10: pts,ex = -int(w["liquidity"]*0.6), f"Spread {s:.1f}% (wide)"
        else: pts,ex = -w["liquidity"], f"Spread {s:.1f}% (too wide)"
        comps.append(Component("liquidity", pts, ex))
    if cx.get("iv_percentile") is not None:
        ivp = int(cx["iv_percentile"])
        if 20<=ivp<=70: comps.append(Component("vol_context", int(w["vol_context"]*0.6), f"IVP {ivp} (mid)"))
        elif ivp<20: comps.append(Component("vol_context", int(w["vol_context"]*0.3), f"IVP {ivp} (low)"))
        else: comps.append(Component("vol_context", -w["vol_context"], f"IVP {ivp} (high)"))
    macro = bool(cx.get("is_macro_window", False))
    comps.append(Component("macro", -w["macro"] if macro else 0, "Macro window ±5m" if macro else "No macro in ±5m"))
    return comps

def band(total:int)->str:
    b="weak"
    for th,name in BANDS:
        if total>=th: b=name
    return b

def compute_confluence_score(context:Dict, strategy_id:str)->Dict:
    w = STRATEGY_WEIGHTS.get(strategy_id, DEFAULT_WEIGHTS)
    comps = evaluate_components(context,w)
    total = int(clip(sum(c.points for c in comps),0,100))
    return {
      "version":"cs.v1",
      "timestamp": datetime.now(UTC).isoformat()+"Z",
      "symbol": context.get("symbol"),
      "strategy_id": strategy_id,
      "price_ref": context.get("price"),
      "inputs": context,
      "score": {
        "total": total,
        "band": band(total),
        "components": [c.__dict__ for c in comps]
      }
    }
