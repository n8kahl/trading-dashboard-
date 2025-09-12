from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from typing import Optional, Dict
from app.services.intents import add_intent, list_intents

router = APIRouter(prefix="/admin", tags=["intents"])

class IntentIn(BaseModel):
    type: str = Field(..., examples=["plan_suggestion","explain_request"])
    signal_id: Optional[str] = None
    payload: Optional[Dict] = None

@router.post("/intents")
async def create_intent(request: Request, body: IntentIn):
    rec = {
      "id": f"intent_{len(list_intents(999999))+1}",
      "profile": getattr(request.state, "profile", "coach"),
      "type": body.type,
      "signal_id": body.signal_id,
      "payload": body.payload
    }
    return {"ok": True, "intent": add_intent(rec)}

@router.get("/intents")
async def get_intents(limit: int = 50):
    return {"ok": True, "items": list_intents(limit)}
