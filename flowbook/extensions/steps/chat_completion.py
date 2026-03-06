"""Chat completion step: single-turn OpenAI completion. Requires flowbook[ai] and OPENAI_API_KEY."""

from __future__ import annotations

import os
from typing import Any

from flowbook.core.registry.base_op import BaseOp
from flowbook.core.registry.spec import InputsBase, OutputsBase
from flowbook.core.registry.step_decorator import register_from_steps, step
from flowbook.core.runtime.store import RunStore


@step("chat_completion")
class ChatCompletionOp(BaseOp):
    """Single-turn OpenAI chat completion."""

    class Inputs(InputsBase):
        PROMPT = "prompt"
        MESSAGES = "messages"
        SYSTEM_PROMPT = "system_prompt"
        REQUIRED = (PROMPT,)
        OPTIONAL = (MESSAGES, SYSTEM_PROMPT)

    class Outputs(OutputsBase):
        RESPONSE = "response"

    def __call__(self, inputs: dict[str, Any], store: RunStore) -> dict[str, Any]:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise RuntimeError(
                "chat_completion requires openai. Install with: pip install flowbook[ai]"
            ) from e

        prompt = inputs[self.Inputs.PROMPT]
        if not isinstance(prompt, str):
            raise TypeError(f"prompt must be str, got {type(prompt).__name__}")

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY environment variable is not set")

        client = OpenAI(api_key=api_key)
        messages = []
        system = inputs.get(self.Inputs.SYSTEM_PROMPT)
        if isinstance(system, str) and system.strip():
            messages.append({"role": "system", "content": system.strip()})
        history = inputs.get(self.Inputs.MESSAGES)
        if isinstance(history, list):
            for m in history:
                if isinstance(m, dict) and m.get("role") and m.get("content") is not None:
                    messages.append({"role": m["role"], "content": str(m["content"])})
        messages.append({"role": "user", "content": prompt})
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=512,
        )
        content = resp.choices[0].message.content or ""
        return {self.Outputs.RESPONSE: content}


register = register_from_steps()
