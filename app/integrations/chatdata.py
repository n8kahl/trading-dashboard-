from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx


class ChatDataClient:
    """
    Minimal OpenAI-compatible client for chat-data.com.

    Environment:
      - CHATDATA_API_KEY: required
      - CHATDATA_BASE_URL: optional, defaults to https://api.chat-data.com
      - CHATDATA_MODEL: optional, defaults to provider default
      - CHATDATA_API_PATH: optional, defaults to /v1/chat/completions
    """

    def __init__(self) -> None:
        self.api_key = (os.getenv("CHATDATA_API_KEY") or "").strip()
        if not self.api_key:
            raise RuntimeError("CHATDATA_API_KEY not set")
        base = (os.getenv("CHATDATA_BASE_URL") or "https://api.chat-data.com").rstrip("/")
        path = (os.getenv("CHATDATA_API_PATH") or "/v1/chat/completions").lstrip("/")
        self.url = f"{base}/{path}"
        self.model = (os.getenv("CHATDATA_MODEL") or "").strip() or None

    async def chat(
        self,
        messages: List[Dict[str, Any]],
        *,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str | Dict[str, Any]] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "messages": messages,
        }
        if self.model:
            payload["model"] = self.model
        if tools:
            payload["tools"] = tools
        if tool_choice is not None:
            payload["tool_choice"] = tool_choice
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stream:
            payload["stream"] = True

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(self.url, json=payload, headers=headers)
        r.raise_for_status()
        return r.json()
