from __future__ import annotations
from typing import Dict, Any, List
from app.config.policy import POLICY

def _ok(b: Dict[str,Any], key: str) -> bool:
    g = b.get("gates", {})
    return isinstance(g.get(key), dict) and g[key].get("ok") is True

def _msg(b: Dict[str,Any], key: str) -> str:
    g = b.get("gates", {})
    return (g.get(key) or {}).get("msg") or ""

def _entry_reasons(b: Dict[str,Any]) -> List[str]:
    g = b.get("gates", {})
    return (g.get("entry") or {}).get("reasons") or []

def explain(e: Dict[str,Any]) -> Dict[str,Any]:
    """
    Turn an evaluation payload into a clear coaching narrative.
    """
    if not e.get("ok"):
        return {"ok": False, "summary": f"Data error: {e.get('error') or 'unknown'}"}

    sym = e.get("symbol")
    decision = e.get("decision") or {}
    take = bool(decision.get("take"))

    gates = e.get("gates") or {}
    session_ok = gates.get("session", {}).get("ok")
    liq_ok     = gates.get("liquidity", {}).get("ok")
    regime_ok  = gates.get("regime", {}).get("ok")
    entry_ok   = gates.get("entry", {}).get("ok")

    pr_win = e.get("pr_win")
    expR   = e.get("expected_R")
    score  = e.get("score")

    lines: List[str] = []
    # Header
    lines.append(f"**{sym} — Coach View**")
    lines.append(f"Confluence score: {score:.1f}" if isinstance(score, (int,float)) else "Confluence score: n/a")

    # Gate by gate
    if not session_ok:
        lines.append(f"• Session gate: ❌ ({_msg(e,'session')}). Windows: {POLICY['windows']['trade_windows']}")
    else:
        lines.append("• Session gate: ✅ within prime windows")

    if not liq_ok:
        lines.append(f"• Liquidity: ❌ ({_msg(e,'liquidity')}) — need RVOL≥{POLICY['equities']['rvol_min']}, "
                     f"spread≤{POLICY['equities']['spread_pct_max']*100:.2f}%, $vol≥${POLICY['equities']['dollar_vol_min']:,}")
    else:
        lines.append("• Liquidity: ✅ passes RVOL/spread/$volume thresholds")

    # Regime is soft-information; show trend states
    trend5  = gates.get("regime", {}).get("trend_5m", "na")
    trend15 = gates.get("regime", {}).get("trend_15m", "na")
    lines.append(f"• Regime (5m/15m): {trend5}/{trend15}")

    # Entry timing
    if not entry_ok:
        reasons = _entry_reasons(e)
        if reasons:
            lines.append(f"• Entry timing: ❌ ({', '.join(reasons)}) — require retest+1-bar hold "
                         f"and distance≤{POLICY['entry']['dist_to_avwap_max']*100:.2f}% of aVWAP.")
        else:
            lines.append("• Entry timing: ❌ fails checks")
    else:
        lines.append("• Entry timing: ✅ retest/hold & distance OK")

    # Decision thresholds
    if pr_win is not None and expR is not None:
        lines.append(f"• Thresholds: need Pr(win)≥{POLICY['decision']['min_pr_win']:.2f} "
                     f"& E[R]≥{POLICY['decision']['min_expected_R']:.2f} — got "
                     f"{pr_win:.2f} & {expR:.2f}")
    else:
        lines.append("• Thresholds: insufficient data to estimate Pr(win)/E[R]")

    # Verdict
    if take:
        lines.append("**Verdict: ✅ Candidate meets all gates & thresholds.**")
        plan = e.get("plan_preview") or {}
        if plan:
            lines.append(f"Plan: entry {plan.get('entry')}, stop {plan.get('stop')}, TP1 {plan.get('tp1')} "
                         f"(50%), TP2 {plan.get('tp2')}, time-stop {plan.get('time_stop_min')}m.")
    else:
        lines.append("**Verdict: ⛔ Not actionable yet.**")
        # Helpful nudge
        if not session_ok:
            lines.append("→ Wait for prime window.")
        elif not liq_ok:
            lines.append("→ Skip until RVOL/spread/$volume improve.")
        elif not entry_ok:
            lines.append("→ Wait for a pullback/retest near aVWAP and a one-bar reclaim.")

    return {"ok": True, "summary": "\n".join(lines)}
