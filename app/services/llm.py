from __future__ import annotations
import os, json, httpx
from typing import Dict, Any

CHATDATA_URL = "https://api.chat-data.com/api/v2/chat"

SYSTEM = """You are Trade Narrator™, a veteran intraday options coach.
Use ONLY fields given in SITUATION JSON. Return STRICT JSON:
{
  "horizon": "scalp"|"intraday"|"swing",
  "band": "unfavorable"|"mixed"|"favorable",
  "actionable": "string (<=140 chars, imperative If/Then)",
  "rationale": ["...", "...", "..."],
  "if_then": [{"if":"...","then":"..."}],
  "levels": {"entry": number|null, "stop": number|null, "targets": [number,...]},
  "risk_notes": "string (<=100 chars)",
  "confidence_delta": {"score": number|null, "delta_vs_prev": number|null}
}
Guardrails:
- If risk breaches or data is stale, set band="unfavorable" and give risk-only guidance.
- Never invent prices; if unknown use null and state briefly.
- Prefer triggers based on VWAP/EMA, RVOL, spread thresholds.
"""

async def chatdata_guidance(situation: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("CHATDATA_API_KEY", "")
    bot_id = os.getenv("CHATDATA_CHATBOT_ID", "")
    if not (api_key and bot_id):
        return {
            "horizon":"intraday","band":"mixed",
            "actionable":"If VWAP is reclaimed on 1m close and spread is acceptable, consider starter; else wait.",
            "rationale":["Fallback: missing ChatData credentials.","Respect daily R; avoid adds during breaches."],
            "if_then":[{"if":"1m close > VWAP","then":"starter long; stop below prior HL"}],
            "levels":{"entry": None, "stop": None, "targets": []},
            "risk_notes":"Educational guidance only.",
            "confidence_delta":{"score": None, "delta_vs_prev": None}
        }
    payload = {
        "chatbotId": bot_id,
        "messages": [{
            "role": "user",
            "content": "SITUATION JSON:\n" + json.dumps(situation, separators=(",",":")) + "\n\nTask: Return ONE best guidance now."
        }],
        "basePrompt": SYSTEM,
        "openAIFormat": True,
        "stream": False,
        "appendMessages": False
    }
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=15.0) as c:
        r = await c.post(CHATDATA_URL, headers=headers, json=payload)
        r.raise_for_status()
        data = r.json() or {}
    content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or "{}"
    try:
        return json.loads(content)
    except Exception:
        return {
            "horizon":"intraday","band":"mixed",
            "actionable":"Wait for VWAP reclaim or 2-bar pullback; avoid chop.",
            "rationale":["Model returned non-JSON; fallback."],
            "if_then":[],
            "levels":{"entry": None, "stop": None, "targets": []},
            "risk_notes":"Check data freshness.",
            "confidence_delta":{"score": None, "delta_vs_prev": None}
        }
