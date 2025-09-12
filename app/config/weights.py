from __future__ import annotations

# Default weight multipliers by session bucket
# Open:    first 60m
# MidDay:  10:30–14:59
# Power:   15:00–16:00
SESSION_WEIGHTS = {
    "open": {"ema_stack": 1.2, "vwap_proximity": 1.1, "rvol": 1.3, "momentum": 1.2},
    "mid": {"ema_stack": 1.0, "vwap_proximity": 1.0, "rvol": 0.9, "momentum": 0.9},
    "power": {"ema_stack": 1.1, "vwap_proximity": 1.2, "rvol": 1.2, "momentum": 1.3},
    "default": {"ema_stack": 1.0, "vwap_proximity": 1.0, "rvol": 1.0, "momentum": 1.0},
}


def get_weights(bucket: str) -> dict:
    return SESSION_WEIGHTS.get(bucket, SESSION_WEIGHTS["default"])
