from typing import Dict, Any
import os
import math

DEFAULTS = {
    "block_unfavorable": True,     # block trades when band == "unfavorable"
    "min_score": 50,               # warn/block if score below this
    "max_dollar_risk": 500.0,      # total risk budget per trade (USD)
}

def _num(x, default=None):
    try:
        return float(x)
    except Exception:
        return default

def get_settings() -> Dict[str, Any]:
    return {
        "block_unfavorable": (os.getenv("RISK_BLOCK_UNFAVORABLE", "true").lower() != "false"),
        "min_score": _num(os.getenv("RISK_MIN_SCORE"), DEFAULTS["min_score"]) or DEFAULTS["min_score"],
        "max_dollar_risk": _num(os.getenv("RISK_MAX_DOLLARS"), DEFAULTS["max_dollar_risk"]) or DEFAULTS["max_dollar_risk"],
    }

def assess_risk(strategy_id: str, context: Dict[str, Any], analysis: Dict[str, Any], plan: Dict[str, Any]) -> Dict[str, Any]:
    """
    Compute risk guardrails and hints.
    Returns: {
      band, score, block_reasons: [..],
      per_unit_risk, max_size_hint, settings: {...}, notes
    }
    """
    settings = get_settings()
    band = (analysis or {}).get("band")
    score = int((analysis or {}).get("score") or 0)

    entry = _num((plan or {}).get("entry_hint"))
    stop  = _num((plan or {}).get("stop_loss"))
    per_unit_risk = _num(entry - stop, None) if (entry is not None and stop is not None) else None

    block_reasons = []
    notes = []

    if band == "unfavorable" and settings["block_unfavorable"]:
        block_reasons.append("band_unfavorable")

    if score < settings["min_score"]:
        # Usually a warning; if also unfavorable we already block; otherwise we warn
        notes.append(f"Score {score} below min_score {settings['min_score']}")

    max_size_hint = None
    if per_unit_risk is not None and per_unit_risk > 0:
        max_size_hint = int(math.floor(settings["max_dollar_risk"] / per_unit_risk))
        if max_size_hint < 1:
            max_size_hint = 1  # still allow tiny size if user forces

    if per_unit_risk is None:
        notes.append("Per-unit risk indeterminate (missing entry or stop); sizing hint may be inaccurate.")

    return {
        "band": band,
        "score": score,
        "per_unit_risk": per_unit_risk,
        "max_size_hint": max_size_hint,
        "block_reasons": block_reasons,
        "settings": settings,
        "notes": notes,
    }
