import os
from datetime import datetime
from zoneinfo import ZoneInfo

_TZ = ZoneInfo(os.getenv("APP_TIMEZONE", "America/Chicago"))


def allow_0dte() -> bool:
    """
    Global switch for 0DTE contracts.
    Default: True (permit 0DTE).
    Set ALLOW_0DTE=false to disable.
    """
    val = os.getenv("ALLOW_0DTE", "true").strip().lower()
    return val in ("1", "true", "yes", "on")


def trading_session_now() -> dict:
    now = datetime.now(_TZ)
    return {
        "tz": str(_TZ),
        "now": now.isoformat(),
        "hour": now.hour,
        "minute": now.minute,
        "is_rth": 8 <= now.hour <= 15,  # rough CT RTH; refine later
    }
