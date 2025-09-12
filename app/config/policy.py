from __future__ import annotations

import os


def get_policy():
    # Configurable thresholds (0DTE allowed elsewhere in options picker; equity gates here)
    return {
        "gates": {
            "session_windows": [["09:40", "11:15"], ["14:15", "15:45"]],
            "equity": {
                "rvol_min": float(os.getenv("GATE_EQUITY_RVOL_MIN", "1.3")),
                "spread_pct_max": float(os.getenv("GATE_EQUITY_SPREAD_MAX", "0.0006")),  # 0.06%
                "dollar_vol_min": float(os.getenv("GATE_EQUITY_DOLLAR_VOL_MIN", "50000000")),
            },
        },
        "entries": {
            "distance_to_avwap_max": float(os.getenv("ENTRY_DIST_AVWAP_MAX", "0.0015"))  # 0.15%
        },
        "exits": {"time_stop_min": int(os.getenv("EXIT_TIME_STOP_MIN", "10"))},
        "decision": {
            "min_pr_win": float(os.getenv("DECISION_MIN_PR_WIN", "0.58")),
            "min_exp_R": float(os.getenv("DECISION_MIN_EXP_R", "0.25")),
        },
    }
