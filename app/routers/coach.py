from __future__ import annotations

import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.integrations.chatdata import ChatDataClient
from app.assistant import actions as actions_mod
from app.services.compose import build_context_from_polygon
from app.services.plan_engine import build_plan
from app.services.risk_engine import assess_risk
from app.services.scoring_engine import score_confluence


router = APIRouter(prefix="/coach", tags=["coach"])


class ChatMessage(BaseModel):
    role: str
    content: str
    tool_call_id: Optional[str] = None  # for tool responses
    name: Optional[str] = None


class ChatBody(BaseModel):
    messages: List[ChatMessage] = Field(default_factory=list)
    stream: bool = False
    max_tool_hops: int = Field(default=3, ge=0, le=6)


def _system_prompt() -> str:
    p = Path(__file__).resolve().parents[1] / "assistant" / "system_prompt.md"
    try:
        return p.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are Trading Coach, an expert day-trading copilot. Be concise, risk-aware, "
            "and use tools as needed. Propose then confirm before live execution."
        )


def _actions_tooling() -> List[Dict[str, Any]]:
    """Build OpenAI-compatible tool list from assistant actions registry."""
    actions: List[Dict[str, Any]] = []
    try:
        data = actions_mod.list_actions()
        if isinstance(data, dict) and "actions" in data:
            actions = list(data.get("actions") or [])
        elif isinstance(data, list):
            actions = data
    except Exception:
        actions = []

    tools: List[Dict[str, Any]] = []
    for a in actions:
        name = a.get("op") or a.get("id")
        if not name:
            continue
        schema = a.get("args_schema") or {"type": "object", "properties": {}}
        desc = a.get("description") or a.get("title") or ""
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": str(name),
                    "description": str(desc)[:512],
                    "parameters": schema,
                },
            }
        )
    return tools


async def _execute_tool_call(name: str, arguments_json: str) -> Dict[str, Any]:
    try:
        args = json.loads(arguments_json or "{}") if isinstance(arguments_json, str) else (arguments_json or {})
    except Exception:
        args = {}
    # Delegate to assistant actions executor directly
    try:
        res = await actions_mod.execute_action(name, args)
        if isinstance(res, dict):
            return res
        return {"ok": True, "data": res}
    except Exception as e:
        return {"ok": False, "error": "exec_error", "detail": str(e)}


@router.post("/chat")
async def chat(body: ChatBody) -> Dict[str, Any]:
    """
    Chat endpoint that proxies to chat-data.com using an OpenAI-compatible API.
    Supports function/tool calling against the app's assistant actions.
    """
    # Compose messages with system prompt
    sys = {"role": "system", "content": _system_prompt()}
    messages: List[Dict[str, Any]] = [sys] + [m.model_dump(exclude_none=True) for m in body.messages]

    client = ChatDataClient()
    tools = _actions_tooling()

    # Pre-analysis: detect a likely symbol in the last user message and inject compose.analyze result
    try:
        last_user = next((m for m in reversed(body.messages) if (m.role or "").lower() == "user"), None)
        detected: Optional[str] = None
        if last_user and last_user.content:
            txt = last_user.content
            # find uppercase 1-5 letter tokens that look like tickers and are in default watchlist
            from app.routers.screener import _DEFAULT_WATCHLIST  # type: ignore
            cands = re.findall(r"\b[A-Z]{1,5}\b", txt)
            for c in cands:
                if c in _DEFAULT_WATCHLIST:
                    detected = c
                    break
        if detected:
            # Compose and analyze quickly (auto strategy) and inject as a system context message
            ctx = await build_context_from_polygon(detected, None)
            # If fetch failed, skip
            if not (isinstance(ctx, dict) and ctx.get("_error")):
                analysis = score_confluence(ctx, "auto")
                plan = build_plan("auto", ctx)
                risk = assess_risk("auto", ctx, analysis, plan)
                primer = {
                    "compose": {
                        "symbol": detected,
                        "analysis": analysis,
                        "plan": plan,
                        "risk": risk,
                    }
                }
                messages.append({"role": "system", "content": json.dumps(primer, separators=(",", ":"))})
    except Exception:
        # non-fatal if any precompose step fails
        pass

    hops = 0
    last_response: Dict[str, Any] = {}
    while True:
        resp = await client.chat(messages, tools=tools, stream=False)
        last_response = resp

        # Try to extract assistant message and potential tool calls
        choice = (resp.get("choices") or [{}])[0]
        msg = (choice.get("message") or {})
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            # No tools – return assistant message content
            content = (msg.get("content") or "").strip()
            return {"ok": True, "content": content, "raw": resp}

        # Execute tool calls then continue loop (up to max_tool_hops)
        hops += 1
        if hops > body.max_tool_hops:
            return {
                "ok": True,
                "content": (msg.get("content") or "").strip(),
                "raw": resp,
                "note": f"tool hop limit {body.max_tool_hops} reached",
            }

        # Push the original assistant message with tool calls into the transcript
        messages.append({"role": "assistant", **msg})

        # For each tool call, execute and append a tool result message
        for call in tool_calls:
            fn = (call.get("function") or {})
            name = fn.get("name") or ""
            arguments = fn.get("arguments") or "{}"
            tool_id = call.get("id") or ""
            result = await _execute_tool_call(name, arguments)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_id,
                    "name": name,
                    "content": json.dumps(result, separators=(",", ":")),
                }
            )

        # loop and let the model observe tool results

    # fallback (should not reach)
    raise HTTPException(status_code=500, detail={"ok": False, "error": "no_response", "raw": last_response})
