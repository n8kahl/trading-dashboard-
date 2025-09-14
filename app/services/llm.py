from __future__ import annotations

import json
from typing import Any, Dict

from app.integrations.chatdata import ChatDataClient


BASE_PROMPT = (
    "You are Trade Narrator. Respond ONLY with compact JSON. "
    "Given a situation snapshot (symbol, price, risk, pace, staleness, position), "
    "emit guidance with fields: {horizon, band, action, stops:{sl,tp1?,tp2?}, confidence:0-100, why:[short strings]}. "
    "Prefer clear, risk-aware actions. No prose, no markdown, JSON only."
)


async def chatdata_narrative(situation: Dict[str, Any]) -> Dict[str, Any]:
    """Call Chat Data to produce a JSON guidance object for a trading situation.

    Returns a dict. On parse failure, returns a fallback object with ok=False and raw text.
    """
    messages = [
        {"role": "system", "content": BASE_PROMPT},
        {"role": "user", "content": json.dumps(situation, separators=(",", ":"))},
    ]
    client = ChatDataClient()
    resp = await client.chat(messages, stream=False)
    try:
        choice = (resp.get("choices") or [{}])[0]
        content = (choice.get("message") or {}).get("content") or "{}"
        out = json.loads(content)
        if isinstance(out, dict):
            out.setdefault("ok", True)
            return out
        return {"ok": True, "data": out}
    except Exception:
        return {"ok": False, "error": "parse_error", "raw": (resp or {})}

