"""
Route: POST /chat

Single-turn chat: prompt -> chat_completion step -> response.
"""

from __future__ import annotations

from typing import cast

from fastapi import APIRouter, HTTPException

from flowbook.core.artifacts.store import JsonValue
from flowbook.extensions.api.deps import get_engine
from flowbook.extensions.api.errors import to_http_error
from flowbook.extensions.api.schemas import ChatRequest, ChatResponse
from flowbook.extensions.steps.chat_completion import ChatCompletionOp

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(body: ChatRequest) -> ChatResponse:
    """Single-turn chat via chat_completion step. Requires OPENAI_API_KEY."""
    prompt = body.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail={"reason": "prompt must be non-empty"})

    engine = get_engine()
    history = [{"role": m.role, "content": m.content} for m in body.messages]
    inputs = {
        ChatCompletionOp.Inputs.PROMPT: "@prompt",
        ChatCompletionOp.Inputs.MESSAGES: "@messages",
    }
    if body.system_prompt is not None:
        inputs[ChatCompletionOp.Inputs.SYSTEM_PROMPT] = "@system_prompt"

    try:
        with engine.create_run() as session:
            session.put_input("prompt", prompt)
            session.put_input("messages", cast(JsonValue, history))
            if body.system_prompt is not None:
                session.put_input("system_prompt", body.system_prompt)
            plan_config = {
                "steps": [
                    {
                        "name": "ai",
                        "op": "chat_completion",
                        "inputs": inputs,
                    }
                ]
            }
            info = session.exec_plan(plan_config=plan_config)

            if info.status != "succeeded":
                err = info.errors[0] if info.errors else "Unknown error"
                raise HTTPException(status_code=500, detail={"reason": err})

            step_info = info.steps[0]
            response_key = step_info.outputs.get(ChatCompletionOp.Outputs.RESPONSE)
            if not response_key:
                raise HTTPException(status_code=500, detail={"reason": "No response from step"})

            response = session.get(response_key)
            return ChatResponse(response=str(response) if response is not None else "")
    except HTTPException:
        raise
    except Exception as e:
        raise to_http_error(e) from e
