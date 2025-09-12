from fastapi import APIRouter, Request

from .common import ok

router = APIRouter(prefix="/", tags=["webhooks"])


@router.post("/webhooks/chat-data")
async def chat_data_webhook(req: Request):
    payload = await req.json()
    return ok({"received": payload})
