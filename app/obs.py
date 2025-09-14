from __future__ import annotations

import json
import logging
import time
import uuid
from contextvars import ContextVar
from typing import Any, Dict, Optional

_logger = logging.getLogger("obs")

# Per-request correlation id
_rid_var: ContextVar[Optional[str]] = ContextVar("request_id", default=None)


def new_request_id() -> str:
    rid = uuid.uuid4().hex[:16]
    _rid_var.set(rid)
    return rid


def get_request_id() -> Optional[str]:
    return _rid_var.get()


def log_event(event: str, level: str = "info", **fields: Any) -> None:
    """Emit a one-line JSON log with standard fields.

    Fields: ts (ms), level, event, rid, and any extra provided fields.
    """
    payload: Dict[str, Any] = {
        "ts": int(time.time() * 1000),
        "level": level,
        "event": event,
    }
    rid = get_request_id()
    if rid:
        payload["rid"] = rid
    # Merge extras, excluding None for cleanliness
    for k, v in fields.items():
        if v is not None:
            payload[k] = v

    line = json.dumps(payload, ensure_ascii=False)
    if level == "error":
        _logger.error(line)
    elif level == "warning":
        _logger.warning(line)
    else:
        _logger.info(line)

