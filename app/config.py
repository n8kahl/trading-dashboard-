import os

APP_ENV = os.getenv("APP_ENV", "production").lower()

# ----- Market clock (US equities; America/Chicago per your project) -----
MARKET_TZ = os.getenv("MARKET_TZ", "America/Chicago")
# Regular hours (CT): 8:30–15:00
REG_OPEN_HOUR = int(os.getenv("REG_OPEN_HOUR", "8"))
REG_OPEN_MIN = int(os.getenv("REG_OPEN_MIN", "30"))
REG_CLOSE_HOUR = int(os.getenv("REG_CLOSE_HOUR", "15"))
REG_CLOSE_MIN = int(os.getenv("REG_CLOSE_MIN", "0"))

# Warn if live data lags beyond this during market hours (seconds)
LAG_WARN_SEC = int(os.getenv("LAG_WARN_SEC", "120"))

# ----- Options picker defaults by liquidity class -----
PROD_OPTIONS_DEFAULTS = {
    "ultra_liquid": {
        "short": {"delta_range": (0.60, 0.80), "max_spread_pct": 2.0, "min_oi": 1000, "min_vol": 500},
        "swing": {"delta_range": (0.35, 0.55), "max_spread_pct": 3.0, "min_oi": 800, "min_vol": 300},
    },
    "liquid": {
        "short": {"delta_range": (0.55, 0.75), "max_spread_pct": 3.0, "min_oi": 500, "min_vol": 250},
        "swing": {"delta_range": (0.30, 0.50), "max_spread_pct": 4.0, "min_oi": 400, "min_vol": 200},
    },
    "default": {
        "short": {"delta_range": (0.50, 0.70), "max_spread_pct": 5.0, "min_oi": 150, "min_vol": 100},
        "swing": {"delta_range": (0.25, 0.45), "max_spread_pct": 6.0, "min_oi": 120, "min_vol": 80},
    },
}

ULTRA_LIQUID = {"SPY", "QQQ", "I:SPX", "AAPL", "MSFT", "NVDA", "META", "AMZN", "TSLA"}
LIQUID = {"AMD", "GOOGL", "NFLX", "SMH", "IWM", "XLF", "XLE", "XLP", "XLC", "XLI", "XLU"}


def symbol_class(symbol: str) -> str:
    s = (symbol or "").upper()
    if s in ULTRA_LIQUID:
        return "ultra_liquid"
    if s in LIQUID:
        return "liquid"
    return "default"


def prod_defaults_for(symbol: str, horizon: str):
    klass = symbol_class(symbol)
    horizon = (horizon or "short").lower()
    base = PROD_OPTIONS_DEFAULTS.get(klass, PROD_OPTIONS_DEFAULTS["default"])
    return base.get(horizon, base["short"])


# ----- Caching knobs for options fetcher -----
OPTIONS_CACHE_TTL_SEC = int(os.getenv("OPTIONS_CACHE_TTL_SEC", "20"))
# Include dropped contracts in options responses for diagnostics?
OPTIONS_INCLUDE_DROPPED = os.getenv("OPTIONS_INCLUDE_DROPPED", "false").lower() in ("1", "true", "yes")
